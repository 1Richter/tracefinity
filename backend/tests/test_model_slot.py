"""Tests for the idle-unload model slot."""
import threading
import time

from app.services.model_slot import ModelSlot


def _wait_until(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_slot_loads_lazily_and_reuses_the_model():
    calls = []

    slot = ModelSlot(lambda: calls.append(1) or "model", "test", idle_seconds=0)

    assert slot.loaded is False
    assert calls == []

    assert slot.get() == "model"
    assert slot.get() == "model"
    assert calls == [1]
    assert slot.loaded is True


def test_slot_unloads_after_idle_and_reloads_on_next_use():
    loads = []

    slot = ModelSlot(lambda: loads.append(1) or object(), "test", idle_seconds=0.05)

    first = slot.get()
    assert _wait_until(lambda: not slot.loaded), "slot did not unload while idle"

    second = slot.get()
    assert second is not first
    assert len(loads) == 2

    slot.unload()


def test_zero_timeout_keeps_the_model_resident():
    slot = ModelSlot(lambda: "model", "test", idle_seconds=0)

    slot.get()
    time.sleep(0.1)

    assert slot.loaded is True


def test_use_resets_the_idle_timer():
    slot = ModelSlot(lambda: "model", "test", idle_seconds=0.2)

    slot.get()
    for _ in range(4):
        time.sleep(0.05)
        slot.get()

    assert slot.loaded is True
    slot.unload()


def test_unload_during_use_leaves_the_handed_out_model_usable():
    slot = ModelSlot(lambda: ["weights"], "test", idle_seconds=0)

    model = slot.get()
    slot.unload()

    assert slot.loaded is False
    assert model == ["weights"]


def test_a_use_that_beats_a_fired_timer_keeps_the_model():
    # Timer.cancel() does nothing once the timer thread has entered the
    # callback, so a get() landing in that window arms a fresh timer that the
    # in-flight callback then cancels on its way to unloading. Calling the
    # callback by hand right after a use reproduces exactly that interleaving.
    slot = ModelSlot(lambda: object(), "test", idle_seconds=5)

    model = slot.get()
    slot._unload_if_idle()

    assert slot.loaded is True
    assert slot.get() is model

    slot.unload()


def test_the_timer_callback_unloads_once_the_model_is_really_idle():
    # a long idle_seconds keeps a real timer from racing this: the callback is
    # driven by hand against a backdated last-use, so the assertion can only
    # come from the callback itself
    slot = ModelSlot(lambda: "model", "test", idle_seconds=60)

    slot.get()
    slot._last_used = time.monotonic() - 120
    slot._unload_if_idle()

    assert slot.loaded is False


def test_a_use_cannot_land_between_the_idle_check_and_the_drop():
    """The idle check and the drop have to share one critical section. When
    they did not, a get() in the gap reloaded the model and the in-flight
    callback then dropped it again, leaving the slot empty right after a use."""
    loads = []
    slot = ModelSlot(lambda: loads.append(1) or object(), "test", idle_seconds=60)

    slot.get()
    slot._last_used = time.monotonic() - 120

    inside_drop = threading.Event()
    let_drop_finish = threading.Event()
    original_cancel = slot._cancel_timer

    def slow_cancel():
        inside_drop.set()
        let_drop_finish.wait(5)
        original_cancel()

    slot._cancel_timer = slow_cancel
    unloader = threading.Thread(target=slot._unload_if_idle)
    unloader.start()
    assert inside_drop.wait(5), "callback never reached the drop"

    got: list = []
    user = threading.Thread(target=lambda: got.append(slot.get()))
    user.start()
    # the get() must be blocked on the lock, not racing inside the drop
    user.join(0.2)
    assert user.is_alive(), "get() got into the slot while the drop held the lock"

    let_drop_finish.set()
    unloader.join(5)
    user.join(5)

    # the get() ran after the drop completed, so it reloaded and the slot ends
    # loaded with the model it handed out -- never empty right after a use
    assert len(loads) == 2
    assert slot.loaded is True
    assert got[0] is not None

    slot.unload()


def test_use_bounds_how_many_callers_are_in_the_model_at_once():
    # inference runs in a threadpool now, so without the gate the peak memory
    # is the model plus one set of activations per worker thread
    slot = ModelSlot(lambda: "model", "test", idle_seconds=0)
    inside = []
    peak = []
    counter_lock = threading.Lock()
    release = threading.Event()

    def call():
        with slot.use():
            with counter_lock:
                inside.append(1)
                peak.append(len(inside))
            release.wait(5)
            with counter_lock:
                inside.pop()

    threads = [threading.Thread(target=call) for _ in range(4)]
    for t in threads:
        t.start()
    time.sleep(0.1)
    release.set()
    for t in threads:
        t.join(5)

    assert max(peak) == 1


def test_use_hands_out_the_same_model_as_get():
    slot = ModelSlot(lambda: ["weights"], "test", idle_seconds=0)

    with slot.use() as model:
        assert model is slot.get()

    slot.unload()


def test_unload_runs_the_release_hook_only_when_something_was_loaded():
    released = []
    slot = ModelSlot(
        lambda: "model", "test", idle_seconds=0, on_unload=lambda: released.append(1)
    )

    slot.unload()
    assert released == []

    slot.get()
    slot.unload()
    assert released == [1]


def test_unload_is_idempotent():
    slot = ModelSlot(lambda: "model", "test", idle_seconds=0)

    slot.unload()
    slot.get()
    slot.unload()
    slot.unload()

    assert slot.loaded is False
