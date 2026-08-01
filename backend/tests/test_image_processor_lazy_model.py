"""Paper detection must not load U2-Net before it is actually needed."""
from app.services.image_processor import ImageProcessor


def test_construction_does_not_load_the_model():
    processor = ImageProcessor()

    assert processor._tool_mask_model.loaded is False


def test_missing_onnx_skips_the_tool_mask(monkeypatch, tmp_path):
    import cv2
    import numpy as np

    processor = ImageProcessor()
    processor._onnx_available = False

    def fail(_path):
        raise AssertionError("tool mask must not run without ONNX")

    monkeypatch.setattr(processor, "_get_tool_mask", fail)

    image_path = tmp_path / "blank.png"
    cv2.imwrite(str(image_path), np.zeros((40, 40, 3), np.uint8))

    # no paper in a black image, but the call has to get that far
    assert processor.detect_paper_corners(str(image_path)) is None
