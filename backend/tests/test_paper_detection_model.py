"""PAPER_DETECTION_MODEL selects the rembg model used for paper detection."""
import pytest

from app.config import settings
from app.services.image_processor import ImageProcessor


def test_defaults_to_u2netp():
    processor = ImageProcessor()

    assert processor._tool_mask_model._label == "u2netp (paper detection)"


def test_configured_model_is_the_one_loaded(monkeypatch):
    loaded = []
    monkeypatch.setattr(settings, "paper_detection_model", "silueta")
    monkeypatch.setattr(
        "app.services.image_processor._load_paper_model",
        lambda name: loaded.append(name) or object(),
    )

    processor = ImageProcessor()
    processor._tool_mask_model.get()

    assert loaded == ["silueta"]


def test_unsupported_model_is_rejected_at_construction(monkeypatch):
    monkeypatch.setattr(settings, "paper_detection_model", "birefnet-general")

    with pytest.raises(ValueError, match="birefnet-general"):
        ImageProcessor()
