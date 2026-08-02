"""Tests for AITracer saliency dispatch (local vs remote)."""

import asyncio

import numpy as np
from PIL import Image

from app.services.ai_tracer import AITracer


def test_no_saliency_tracer_is_gemini_path():
    t = AITracer(model="gemini-x")
    assert t.uses_saliency is False
    assert t._saliency_backend is None


def test_local_tracer_defers_the_weight_load(monkeypatch):
    import app.services.onnx_check as onnx_check
    from app.services.model_slot import ModelSlot

    monkeypatch.setattr(onnx_check, "is_onnx_available", lambda: True)

    t = AITracer(saliency_tracer="isnet")
    kind, handle = t._saliency_backend

    assert kind == "rembg"
    assert isinstance(handle, ModelSlot)
    assert handle.loaded is False


def test_local_saliency_runs_off_the_event_loop():
    # a cold trace loads the model, which takes tens of seconds for the larger
    # tracers. On the event loop that stalls every other request, /health
    # included, which reads as a dead instance to a liveness probe.
    import threading

    from app.services.model_slot import ModelSlot

    t = AITracer(model="gemini-x")
    t._saliency_backend = ("rembg", ModelSlot(lambda: "session", "test", idle_seconds=0))

    ran_on = {}

    def fake_local(pil_img, kind, slot):
        ran_on["thread"] = threading.get_ident()
        slot.get()
        return np.zeros((4, 4), np.uint8)

    t._saliency_local = fake_local

    asyncio.run(t._saliency_on_image(Image.new("RGB", (4, 4))))

    assert ran_on["thread"] != threading.get_ident()


def test_remote_tracer_builds_config_and_calls_module(monkeypatch):
    import app.services.remote_saliency as rs

    called = {}

    async def fake(cfg, image_png, target_size, **kw):
        called["cfg"] = cfg
        called["target"] = target_size
        return np.full((target_size[1], target_size[0]), 255, np.uint8)

    monkeypatch.setattr(rs, "remote_saliency_mask", fake)

    t = AITracer(saliency_tracer="fal", remote_model="fal-ai/birefnet/v2", remote_token="x")
    assert t.uses_saliency is True
    assert t._saliency_backend[0] == "fal"

    out = asyncio.run(t._saliency_on_image(Image.new("RGB", (12, 9))))
    assert out.shape == (9, 12)  # (h, w)
    assert called["cfg"].provider == "fal"
    assert called["cfg"].model == "fal-ai/birefnet/v2"
    assert called["target"] == (12, 9)  # (w, h)
