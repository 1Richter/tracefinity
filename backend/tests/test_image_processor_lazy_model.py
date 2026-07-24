import sys
from types import ModuleType

from app.services import onnx_check, ort_runtime
from app.services.image_processor import ImageProcessor


def test_image_processor_defers_u2net_session_until_first_use(monkeypatch):
    calls = []
    fake_session = "u2net-session"
    fake_rembg = ModuleType("rembg")

    def new_session(model_name, providers):
        calls.append((model_name, providers))
        return fake_session

    fake_rembg.new_session = new_session
    monkeypatch.setitem(sys.modules, "rembg", fake_rembg)
    monkeypatch.setattr(onnx_check, "is_onnx_available", lambda: True)
    monkeypatch.setattr(ort_runtime, "get_onnx_providers", lambda: ["CPUExecutionProvider"])

    # Given the application creates its shared image processor at startup
    processor = ImageProcessor()

    # Then startup must not allocate the U2-Net session
    assert calls == [], "ImageProcessor eagerly loaded U2-Net during construction"

    # When paper masking first needs the model
    first = processor._get_tool_mask_session()
    second = processor._get_tool_mask_session()

    # Then one session is loaded and reused
    assert first == fake_session
    assert second == fake_session
    assert calls == [("u2netp", ["CPUExecutionProvider"])]
