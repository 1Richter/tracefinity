"""The parametric cutout line: one continuous trench across several tools.

A line is a stadium (a rectangle with half-round ends) cut down from the floor
face, sized by length x trench width, positioned and rotated freely. Unlike a
tool pocket it is not bound to one tool outline, so a single line can span a
whole row of tools.
"""
from pathlib import Path

import pytest

from app.models.schemas import GenerateRequest
from app.services.polygon_scaler import ScaledFingerHole, ScaledPolygon
from app.services.stl_generator_manifold import (
    GF_HEIGHT_UNIT,
    ManifoldSTLGenerator,
    _line_cutter_parts,
    _make_finger_hole_chamfers,
    _make_finger_holes,
    _make_line_cutter,
)

WALL_TOP_Z = 4 * GF_HEIGHT_UNIT


def _line_hole(x=0.0, y=0.0, length=60.0, trench=8.0, rotation=0.0, depth_override=None):
    return ScaledFingerHole(
        id="l1", x_mm=x, y_mm=y, radius_mm=max(length, trench) / 2,
        shape="line", width_mm=length, height_mm=trench,
        rotation=rotation, depth_override=depth_override,
    )


def _tool(points, holes, poly_id="p1"):
    return ScaledPolygon(id=poly_id, points_mm=points, label="test", finger_holes=holes)


def _square_tool(cx, holes=(), half=25.0):
    return _tool(
        [(cx - half, -half), (cx + half, -half), (cx + half, half), (cx - half, half)],
        list(holes),
        poly_id=f"p{int(cx)}",
    )


def _config(**kwargs) -> GenerateRequest:
    return GenerateRequest(
        grid_x=4, grid_y=2, height_units=4,
        magnets=False, stacking_lip=False, bed_size=0,
        cutout_depth=10, cutout_clearance=0,
        **kwargs,
    )


# ── footprint ────────────────────────────────────────────────────────────────

def test_line_footprint_is_length_by_trench():
    body_len, r = _line_cutter_parts(60, 8)

    assert body_len == pytest.approx(52)
    assert r == pytest.approx(4)
    assert body_len + 2 * r == pytest.approx(60)


def test_line_shorter_than_its_width_becomes_a_round_pocket():
    body_len, r = _line_cutter_parts(3, 8)

    assert body_len == 0
    assert r == pytest.approx(4)


def test_line_cutter_matches_its_parameters():
    cutter = _make_line_cutter(60, 8, 10, WALL_TOP_Z, 0.0, 0.0, 0.0)
    min_x, min_y, min_z, max_x, max_y, max_z = cutter.bounding_box()

    assert max_x - min_x == pytest.approx(60, abs=0.2)
    assert max_y - min_y == pytest.approx(8, abs=0.2)
    # cuts from just above the floor face down by the pocket depth
    assert max_z == pytest.approx(WALL_TOP_Z + 0.005, abs=0.01)
    assert min_z == pytest.approx(WALL_TOP_Z - 10 - 0.005, abs=0.01)


def test_rotating_a_line_swaps_its_extents():
    cutter = _make_line_cutter(60, 8, 10, WALL_TOP_Z, 90.0, 0.0, 0.0)
    min_x, min_y, _, max_x, max_y, _ = cutter.bounding_box()

    assert max_x - min_x == pytest.approx(8, abs=0.2)
    assert max_y - min_y == pytest.approx(60, abs=0.2)


def test_line_is_positioned_at_its_centre():
    cutter = _make_line_cutter(60, 8, 10, WALL_TOP_Z, 0.0, 25.0, -15.0)
    min_x, min_y, _, max_x, max_y, _ = cutter.bounding_box()

    assert (min_x + max_x) / 2 == pytest.approx(25.0, abs=0.01)
    assert (min_y + max_y) / 2 == pytest.approx(-15.0, abs=0.01)


def test_a_line_removes_less_than_the_rectangle_around_it():
    """The rounded ends are what makes it a line and not a slot cut."""
    line = _make_line_cutter(60, 8, 10, WALL_TOP_Z, 0.0, 0.0, 0.0)

    assert line.volume() < 60 * 8 * 10
    assert line.volume() > 0.9 * (52 * 8 * 10)


# ── cutter pipeline ──────────────────────────────────────────────────────────

def test_line_becomes_a_finger_hole_cutter():
    polygons = [_square_tool(0, [_line_hole(length=60, trench=8)])]

    cutter = _make_finger_holes(polygons, _config(), WALL_TOP_Z, 20.0, 0.0, 0.0)

    assert cutter is not None
    min_x, _, _, max_x, _, _ = cutter.bounding_box()
    assert max_x - min_x == pytest.approx(60, abs=0.2)


def test_line_uses_its_depth_override():
    polygons = [_square_tool(0, [_line_hole(depth_override=6.0)])]
    deep = [_square_tool(0, [_line_hole(depth_override=18.0)])]
    config = _config()

    shallow_cutter = _make_finger_holes(polygons, config, WALL_TOP_Z, 20.0, 0.0, 0.0)
    deep_cutter = _make_finger_holes(deep, config, WALL_TOP_Z, 20.0, 0.0, 0.0)

    assert shallow_cutter.bounding_box()[2] > deep_cutter.bounding_box()[2]


def test_line_depth_is_clamped_to_what_the_bin_allows():
    polygons = [_square_tool(0, [_line_hole(depth_override=500.0)])]

    cutter = _make_finger_holes(polygons, _config(), WALL_TOP_Z, 12.0, 0.0, 0.0)

    assert cutter.bounding_box()[2] == pytest.approx(WALL_TOP_Z - 12.0 - 0.005, abs=0.01)


def test_one_line_spans_a_row_of_tools():
    """The line belongs to a placement but is not clipped to that tool."""
    polygons = [
        _square_tool(-60, [_line_hole(length=180, trench=8)]),
        _square_tool(0),
        _square_tool(60),
    ]

    cutter = _make_finger_holes(polygons, _config(), WALL_TOP_Z, 20.0, 0.0, 0.0)

    min_x, _, _, max_x, _, _ = cutter.bounding_box()
    # centred on the first tool, reaching past the far edge of the last one
    assert min_x < -85
    assert max_x > 25


def test_line_gets_a_chamfer_cutter():
    polygons = [_square_tool(0, [_line_hole(length=60, trench=8)])]

    chamfers = _make_finger_hole_chamfers(
        polygons, _config(cutout_chamfer=1.0), WALL_TOP_Z, 1.0, 20.0, 0.0, 0.0
    )

    assert chamfers is not None
    min_x, min_y, _, max_x, max_y, _ = chamfers.bounding_box()
    # the chamfer flares outward from the trench footprint
    assert max_x - min_x > 60
    assert max_y - min_y > 8


# ── full bin ─────────────────────────────────────────────────────────────────

def test_bin_with_a_line_generates_and_keeps_its_floor(tmp_path: Path):
    config = _config()
    generator = ManifoldSTLGenerator()

    plain = generator.generate_bin(
        [_square_tool(0)], config, str(tmp_path / "plain.stl")
    )[0]
    with_line = generator.generate_bin(
        [_square_tool(0, [_line_hole(length=120, trench=8, depth_override=500.0)])],
        config,
        str(tmp_path / "line.stl"),
    )[0]

    assert not with_line.is_empty()
    assert with_line.volume() < plain.volume()
    # the clamped pocket never punches through the base
    assert with_line.bounding_box()[2] == pytest.approx(plain.bounding_box()[2], abs=0.01)


def test_longer_lines_remove_more_material(tmp_path: Path):
    config = _config()
    generator = ManifoldSTLGenerator()

    def volume(length: float, name: str) -> float:
        polygons = [_square_tool(0, [_line_hole(length=length, trench=8)])]
        return generator.generate_bin(polygons, config, str(tmp_path / name))[0].volume()

    assert volume(120, "long.stl") < volume(40, "short.stl")
