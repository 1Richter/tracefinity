"""Every generated bin gets a 3MF, with or without embossed labels.

3MF is the only export that carries the unit, so a CAD import keeps the mm
scale an STL import can get wrong. Before, it was written only for bins that
had embossed text, which is also why a missing trimesh dependency could break
it without any test noticing.
"""
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from app.models.schemas import GenerateRequest, TextLabel
from app.services.stl_generator_manifold import ManifoldSTLGenerator

MODEL_NS = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"


def _generate(tmp_path: Path, **overrides) -> Path:
    config = GenerateRequest(
        grid_x=2,
        grid_y=2,
        height_units=3,
        magnets=False,
        stacking_lip=False,
        **overrides,
    )
    threemf = tmp_path / "bin.3mf"
    ManifoldSTLGenerator().generate_bin(
        [], config, str(tmp_path / "bin.stl"), str(threemf)
    )
    return threemf


def _model_root(threemf: Path) -> ET.Element:
    with zipfile.ZipFile(threemf) as zf:
        return ET.fromstring(zf.read("3D/3dmodel.model"))


def test_bin_without_labels_still_exports_a_3mf(tmp_path: Path):
    threemf = _generate(tmp_path)

    assert threemf.exists()
    assert zipfile.is_zipfile(threemf)


def test_3mf_declares_millimetres(tmp_path: Path):
    root = _model_root(_generate(tmp_path))

    assert root.get("unit") == "millimeter"


def test_bin_without_labels_is_a_single_body(tmp_path: Path):
    root = _model_root(_generate(tmp_path))

    objects = root.findall(f"{MODEL_NS}resources/{MODEL_NS}object")
    assert len(objects) == 1
    assert objects[0].find(f"{MODEL_NS}mesh") is not None


def test_embossed_labels_stay_a_separate_body(tmp_path: Path):
    root = _model_root(
        _generate(
            tmp_path,
            text_labels=[TextLabel(id="lbl", text="HELLO", x=42, y=42, emboss=True)],
        )
    )

    # bin and text stay separate objects so a slicer can print them in two colours
    objects = root.findall(f"{MODEL_NS}resources/{MODEL_NS}object")
    assert len(objects) == 2
