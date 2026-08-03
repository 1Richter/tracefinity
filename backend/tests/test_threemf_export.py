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


def test_a_missing_3mf_is_reported_on_the_cached_path_too(tmp_path: Path, monkeypatch):
    """The hash is written even when the export failed, so the second request
    for the same config hits the cache. It has to explain the missing download
    the same way the first one did."""
    from app.api import routes

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "bin.stl").write_bytes(b"solid\nendsolid\n")
    (outputs / "bin.hash").write_text("same-hash")
    # no bin.3mf: this is what a failed export leaves behind

    response = routes._run_generate(
        [],
        GenerateRequest(grid_x=2, grid_y=2),
        "bin",
        tmp_path,
        "same-hash",
        "user",
        _OpenStore(),
    )

    assert response.threemf_url is None
    assert response.warning == routes.THREEMF_FAILED_WARNING


class _OpenStore:
    def ensure_open(self) -> None:
        pass


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


def test_a_split_bin_gets_a_3mf_per_piece_not_one_for_the_whole_bin(tmp_path: Path):
    """Before this, split_bin only wrote STLs -- the 3MF stayed the pre-cut
    whole bin, too large for the bed it was just split to fit, and silently
    the wrong download for anyone who picked 3MF over the STL parts zip."""
    generator = ManifoldSTLGenerator()
    config = GenerateRequest(
        grid_x=10, grid_y=1, height_units=3, magnets=False, stacking_lip=False,
        bed_size=150,
    )
    body, text_body = generator.generate_bin([], config, str(tmp_path / "bin.stl"))

    stl_paths = generator.split_bin(body, text_body, config, config.bed_size, str(tmp_path), "part")

    assert len(stl_paths) >= 2
    threemf_paths = sorted(tmp_path.glob("part_part*.3mf"))
    assert len(threemf_paths) == len(stl_paths)
    for threemf in threemf_paths:
        assert zipfile.is_zipfile(threemf)
        assert _model_root(threemf).get("unit") == "millimeter"


def test_a_split_bin_3mf_piece_is_a_single_body(tmp_path: Path):
    """Each split STL is already the bin+text union (split_bin merges them
    before cutting), so its 3MF sibling has nothing left to keep separate."""
    generator = ManifoldSTLGenerator()
    config = GenerateRequest(
        grid_x=10, grid_y=1, height_units=3, magnets=False, stacking_lip=False,
        bed_size=150,
    )
    body, text_body = generator.generate_bin([], config, str(tmp_path / "bin.stl"))
    generator.split_bin(body, text_body, config, config.bed_size, str(tmp_path), "part")

    threemf = sorted(tmp_path.glob("part_part*.3mf"))[0]
    objects = _model_root(threemf).findall(f"{MODEL_NS}resources/{MODEL_NS}object")
    assert len(objects) == 1


def test_the_parts_zip_from_a_full_generate_holds_stl_and_3mf_per_piece(tmp_path: Path):
    """End to end through _run_generate: the ZIP a user downloads for a split
    bin has to carry the 3MF pieces, not just the whole-bin one at the top
    level -- that top-level file is the pre-cut reference, per 'Full 3MF' in
    the export menu, not a substitute for the split parts."""
    from app.api import routes

    outputs = tmp_path / "outputs"
    outputs.mkdir()

    response = routes._run_generate(
        [],
        GenerateRequest(
            grid_x=10, grid_y=1, height_units=3, magnets=False, stacking_lip=False,
            bed_size=150,
        ),
        "bin",
        tmp_path,
        "hash-1",
        "user",
        _OpenStore(),
    )

    assert response.zip_url is not None
    with zipfile.ZipFile(outputs / "bin_parts.zip") as zf:
        names = zf.namelist()
    stl_names = [n for n in names if n.endswith(".stl")]
    threemf_names = [n for n in names if n.endswith(".3mf")]
    assert len(stl_names) >= 2
    assert len(threemf_names) == len(stl_names)
