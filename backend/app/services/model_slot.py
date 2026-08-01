"""Lazily loaded models that give their memory back while nobody uses them."""
import gc
import logging
import threading
from collections.abc import Callable
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ModelSlot(Generic[T]):
    """Holds one heavy model: loads it on first use, drops it again after
    idle_seconds without a call, reloads it on the next one.

    get() hands out a strong reference, so an unload firing during inference
    only drops the slot's own reference -- the caller finishes with the model
    it already holds and the memory is released when it returns.

    idle_seconds <= 0 keeps the model loaded for the lifetime of the process.
    """

    def __init__(self, loader: Callable[[], T], label: str, idle_seconds: float):
        self._loader = loader
        self._label = label
        self._idle_seconds = idle_seconds
        self._lock = threading.Lock()
        self._model: T | None = None
        self._timer: threading.Timer | None = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def get(self) -> T:
        with self._lock:
            if self._model is None:
                logger.info("loading %s", self._label)
                self._model = self._loader()
            model = self._model
            self._arm_timer()
        return model

    def unload(self) -> None:
        """Drop the model. Safe to call at any time, including while it runs."""
        with self._lock:
            self._cancel_timer()
            if self._model is None:
                return
            self._model = None
        logger.info("unloaded %s after %.0fs idle", self._label, self._idle_seconds)
        # ONNX and torch hand their arenas back once the last reference goes
        gc.collect()

    def _arm_timer(self) -> None:
        """caller holds the lock"""
        self._cancel_timer()
        if self._idle_seconds <= 0:
            return
        self._timer = threading.Timer(self._idle_seconds, self.unload)
        self._timer.daemon = True
        self._timer.start()

    def _cancel_timer(self) -> None:
        """caller holds the lock"""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
