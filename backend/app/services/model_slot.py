"""Lazily loaded models that give their memory back while nobody uses them."""
import gc
import logging
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ModelSlot(Generic[T]):
    """Holds one heavy model: loads it on first use, drops it again after
    idle_seconds without a call, reloads it on the next one.

    get() hands out a strong reference, so an unload firing during inference
    only drops the slot's own reference -- the caller finishes with the model
    it already holds and the memory is released when it returns.

    use() is get() plus a gate that bounds how many callers may be inside the
    model at once. Callers run in a threadpool, so without it the peak memory
    is the model plus one set of activations per worker thread rather than the
    single figure docs/resource-requirements.md quotes.

    idle_seconds <= 0 keeps the model loaded for the lifetime of the process.
    """

    def __init__(
        self,
        loader: Callable[[], T],
        label: str,
        idle_seconds: float,
        on_unload: Callable[[], None] | None = None,
        max_concurrent: int = 1,
    ):
        self._loader = loader
        self._label = label
        self._idle_seconds = idle_seconds
        self._on_unload = on_unload
        self._lock = threading.Lock()
        self._gate = threading.BoundedSemaphore(max_concurrent)
        self._model: T | None = None
        self._timer: threading.Timer | None = None
        self._last_used = 0.0

    @property
    def loaded(self) -> bool:
        # advisory only: an unload can land between this read and its use
        return self._model is not None

    def get(self) -> T:
        with self._lock:
            if self._model is None:
                logger.info("loading %s", self._label)
                self._model = self._loader()
            model = self._model
            self._last_used = time.monotonic()
            self._arm_timer()
        return model

    @contextmanager
    def use(self) -> Iterator[T]:
        """Hold the model for one call, waiting if the gate is full."""
        with self._gate:
            yield self.get()

    def unload(self) -> None:
        """Drop the model. Safe to call at any time, including while it runs."""
        with self._lock:
            dropped = self._drop_locked()
        if dropped:
            self._release()

    def _unload_if_idle(self) -> None:
        """Timer callback.

        Timer.cancel() does nothing once the timer thread has entered this
        method, so a get() landing in that window arms a timer that this call
        would otherwise cancel on its way to dropping a model that was just
        used. Compare against the last use instead and re-arm for the time that
        is left -- in the same critical section as the drop, because releasing
        the lock in between lets that same get() slip past the check.
        """
        with self._lock:
            if self._idle_seconds <= 0:
                return
            idle_for = time.monotonic() - self._last_used
            if self._model is not None and idle_for < self._idle_seconds:
                self._arm_timer(self._idle_seconds - idle_for)
                return
            dropped = self._drop_locked()
        if dropped:
            self._release()

    def _drop_locked(self) -> bool:
        """caller holds the lock; returns whether a model went away"""
        self._cancel_timer()
        if self._model is None:
            return False
        self._model = None
        logger.info("unloaded %s", self._label)
        return True

    def _release(self) -> None:
        """Give the dropped model's memory back.

        Collect first: ONNX Runtime hands its arena back as soon as the last
        reference goes, but torch keeps freed CUDA blocks in its caching
        allocator, and empty_cache() only returns blocks that are already free.
        A model still held by a reference cycle -- routine for nn.Module graphs
        -- would survive a hook that ran before the collection.
        """
        gc.collect()
        if self._on_unload is not None:
            self._on_unload()

    def _arm_timer(self, delay: float | None = None) -> None:
        """caller holds the lock"""
        self._cancel_timer()
        if self._idle_seconds <= 0:
            return
        self._timer = threading.Timer(
            self._idle_seconds if delay is None else delay, self._unload_if_idle
        )
        self._timer.daemon = True
        self._timer.start()

    def _cancel_timer(self) -> None:
        """caller holds the lock"""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
