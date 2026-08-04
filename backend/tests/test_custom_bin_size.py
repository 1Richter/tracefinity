"""Custom mm bin sizes (size_mode="custom").

Unit mode keeps the 42mm grid; custom mode sizes the bin in exact outer mm
and derives the gridfinity unit count from it.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.api.routes as routes
from app.config import ensure_user_dirs, settings
from app.constants import CUSTOM_SIZE_MAX_MM, CUSTOM_SIZE_MIN_MM, GF_GRID
from app.main import app
from app.models.schemas import BinConfig, BinParams, GenerateRequest
from app.services.stl_generator_manifold import (
    ManifoldSTLGenerator,
    _base_cell_layout,
    _outer_dims,
)


def _custom(width: float, depth: float, **kwargs) -> GenerateRequest:
    return GenerateRequest(
        size_mode="custom",
        custom_width_mm=width,
        custom_depth_mm=depth,
        **kwargs,
    )


# ── schema ───────────────────────────────────────────────────────────────────

def test_defaults_to_unit_mode():
    params = BinParams()
    assert params.size_mode == "units"
    assert params.custom_width_mm is None
    assert params.grid_x == 2


def test_bins_written_before_custom_sizing_load_unchanged():
    # no size_mode key at all, as stored by earlier versions
    config = BinConfig(**{"grid_x": 3, "grid_y": 2.5, "height_units": 6})
    assert config.size_mode == "units"
    assert (config.grid_x, config.grid_y) == (3, 2.5)


def test_custom_size_derives_grid_units():
    params = BinParams(size_mode="custom", custom_width_mm=480, custom_depth_mm=300)
    assert params.grid_x == pytest.approx(480 / GF_GRID)
    assert params.grid_y == pytest.approx(300 / GF_GRID)


def test_custom_size_overrides_supplied_grid_units():
    params = BinParams(
        size_mode="custom", custom_width_mm=480, custom_depth_mm=300, grid_x=2, grid_y=2
    )
    assert params.grid_x == pytest.approx(480 / GF_GRID)


def test_custom_size_round_trips_through_validation():
    """The derived grid breaks the 1-10 / half-unit rules, so re-validating a
    saved custom bin must not fail."""
    params = BinParams(size_mode="custom", custom_width_mm=480, custom_depth_mm=300)
    reloaded = BinParams(**params.model_dump())
    assert reloaded.grid_x == pytest.approx(params.grid_x)
    assert reloaded.custom_width_mm == 480


def test_custom_mode_requires_both_dimensions():
    with pytest.raises(ValidationError):
        BinParams(size_mode="custom", custom_width_mm=480)


def test_custom_size_rejects_below_minimum():
    with pytest.raises(ValidationError):
        BinParams(
            size_mode="custom", custom_width_mm=CUSTOM_SIZE_MIN_MM - 1, custom_depth_mm=300
        )


def test_custom_size_rejects_above_maximum():
    with pytest.raises(ValidationError):
        BinParams(
            size_mode="custom", custom_width_mm=CUSTOM_SIZE_MAX_MM + 1, custom_depth_mm=300
        )


def test_unit_mode_still_rejects_off_grid_sizes():
    with pytest.raises(ValidationError):
        BinParams(grid_x=2.3)
    with pytest.raises(ValidationError):
        BinParams(grid_x=10.5)


def test_partial_bins_values_sized_from_derived_grid():
    params = BinParams(size_mode="custom", custom_width_mm=210, custom_depth_mm=126)
    # ceil(210/42) = 5 columns, ceil(126/42) = 3 rows
    assert len(params.partial_bins_values) == 15


# ── geometry ─────────────────────────────────────────────────────────────────

def test_outer_dims_unit_mode_keeps_gridfinity_gap():
    assert _outer_dims(GenerateRequest(grid_x=2, grid_y=3)) == (2 * 42 - 0.5, 3 * 42 - 0.5)


def test_outer_dims_custom_mode_is_exact():
    assert _outer_dims(_custom(480, 300)) == (480.0, 300.0)


def test_base_cells_fold_a_tiny_remainder_into_the_previous_cell():
    # 130mm = 3 full cells + a 4mm sliver that cannot form a base unit
    cells = _base_cell_layout(130 / GF_GRID, GF_GRID)
    widths = [w for _, w in cells]
    assert len(cells) == 3
    assert widths[-1] == pytest.approx(46.0)
    assert sum(widths) == pytest.approx(130.0)
    # cells still span the full footprint, centred on the origin
    assert cells[0][0] - widths[0] / 2 == pytest.approx(-65.0)
    assert cells[-1][0] + widths[-1] / 2 == pytest.approx(65.0)


def test_base_cells_keep_a_usable_remainder(tmp_path: Path):
    # 210mm = 5 full cells exactly; 231mm keeps its 21mm half cell
    widths = [w for _, w in _base_cell_layout(231 / GF_GRID, GF_GRID)]
    assert len(widths) == 6
    assert widths[-1] == pytest.approx(21.0)


def test_generated_bin_matches_requested_mm(tmp_path: Path):
    config = _custom(200, 130, height_units=3, magnets=False, stacking_lip=True, bed_size=0)
    body, _ = ManifoldSTLGenerator().generate_bin([], config, str(tmp_path / "custom.stl"))

    min_x, min_y, _, max_x, max_y, _ = body.bounding_box()
    assert max_x - min_x == pytest.approx(200.0, abs=0.01)
    assert max_y - min_y == pytest.approx(130.0, abs=0.01)


def test_generated_bin_is_centred_on_origin(tmp_path: Path):
    config = _custom(200, 130, height_units=3, magnets=False, bed_size=0)
    body, _ = ManifoldSTLGenerator().generate_bin([], config, str(tmp_path / "custom.stl"))

    min_x, min_y, _, max_x, max_y, _ = body.bounding_box()
    assert (min_x + max_x) / 2 == pytest.approx(0.0, abs=0.01)
    assert (min_y + max_y) / 2 == pytest.approx(0.0, abs=0.01)


def test_unit_mode_geometry_unchanged(tmp_path: Path):
    config = GenerateRequest(grid_x=2, grid_y=1, height_units=3, magnets=False, bed_size=0)
    body, _ = ManifoldSTLGenerator().generate_bin([], config, str(tmp_path / "units.stl"))

    min_x, _, _, max_x, _, _ = body.bounding_box()
    assert max_x - min_x == pytest.approx(2 * 42 - 0.5, abs=0.01)


def test_magnet_holes_follow_the_42mm_cells(tmp_path: Path):
    """Magnets stay on the gridfinity cell grid; the trailing partial cell of a
    custom size gets none, so a 130mm depth has the same magnet count as 126mm."""
    generator = ManifoldSTLGenerator()
    solid = generator.generate_bin(
        [], _custom(210, 126, magnets=False, bed_size=0), str(tmp_path / "solid.stl")
    )[0]
    drilled = generator.generate_bin(
        [], _custom(210, 126, magnets=True, bed_size=0), str(tmp_path / "drilled.stl")
    )[0]
    assert drilled.volume() < solid.volume()


# ── api ──────────────────────────────────────────────────────────────────────

def _api_client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_path", tmp_path)
    monkeypatch.setattr(routes.settings, "storage_path", tmp_path)
    routes._store_cache.clear()
    routes._project_store_cache.clear()
    ensure_user_dirs(tmp_path / "default")
    return TestClient(app)


def test_create_bin_accepts_a_custom_mm_size(tmp_path, monkeypatch):
    client = _api_client(tmp_path, monkeypatch)

    resp = client.post("/api/bins", json={
        "name": "Shelf",
        "bin_config": {
            "size_mode": "custom",
            "custom_width_mm": 480,
            "custom_depth_mm": 300,
        },
    })

    assert resp.status_code == 200
    bin_id = resp.json()["id"]
    bin_config = resp.json()["bin_config"]
    assert bin_config["size_mode"] == "custom"
    assert bin_config["custom_width_mm"] == 480
    assert bin_config["grid_x"] == pytest.approx(480 / GF_GRID)

    # the derived grid must survive a reload through the store and the summary
    reloaded = client.get(f"/api/bins/{bin_id}").json()
    assert reloaded["bin_config"]["custom_depth_mm"] == 300
    summary = next(b for b in client.get("/api/bins").json()["bins"] if b["id"] == bin_id)
    assert summary["size_mode"] == "custom"
    assert summary["custom_width_mm"] == 480


def test_create_bin_rejects_an_out_of_range_custom_size(tmp_path, monkeypatch):
    client = _api_client(tmp_path, monkeypatch)

    resp = client.post("/api/bins", json={
        "bin_config": {
            "size_mode": "custom",
            "custom_width_mm": CUSTOM_SIZE_MAX_MM + 500,
            "custom_depth_mm": 300,
        },
    })

    assert resp.status_code == 422


# ── splitting ────────────────────────────────────────────────────────────────

def _piece_sizes(total: float, cuts: list[float]) -> list[float]:
    edges = [-total / 2, *cuts, total / 2]
    return [b - a for a, b in zip(edges, edges[1:])]


def test_split_pieces_of_a_custom_size_fit_the_bed():
    bed = 210.0
    total = 430.0
    cuts = ManifoldSTLGenerator._compute_split_points(total, total / GF_GRID, bed)
    assert cuts
    assert all(size <= bed for size in _piece_sizes(total, cuts))


def test_a_custom_bin_that_fits_diagonally_is_not_split(tmp_path: Path):
    """The derived unit count rounds up to whole 42mm cells; that must not make
    the bin look bigger than it is when deciding whether to split."""
    generator = ManifoldSTLGenerator()
    config = _custom(380, 42, height_units=3, magnets=False, bed_size=300)
    body, _ = generator.generate_bin([], config, str(tmp_path / "bin.stl"))

    # the bin is wider than the bed, so only the diagonal check can save it
    assert generator._compute_split_points(380, 380 / GF_GRID, 300)

    parts = generator.split_bin(body, None, config, config.bed_size, str(tmp_path), "bin")

    # (380 + 42) / sqrt(2) = 298mm fits the 300mm bed on the diagonal; rounding
    # the width up to 10 whole cells (420mm) would have forced a needless split
    assert parts.paths == []


def test_split_points_unchanged_for_unit_sizes():
    cuts = ManifoldSTLGenerator._compute_split_points(10 * GF_GRID, 10, 256.0)
    assert cuts == [0.0]
