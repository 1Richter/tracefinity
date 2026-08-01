"""Tests for the idle-unload model slot."""
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


def test_unload_is_idempotent():
    slot = ModelSlot(lambda: "model", "test", idle_seconds=0)

    slot.unload()
    slot.get()
    slot.unload()
    slot.unload()

    assert slot.loaded is False
