"""Bins larger than twice the bed have to split into more than two parts."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.schemas import GenerateRequest
from app.services.stl_generator_manifold import ManifoldSTLGenerator


def _config(grid: float, bed_size: float) -> GenerateRequest:
    return GenerateRequest(
        grid_x=grid,
        grid_y=grid,
        height_units=3,
        magnets=False,
        stacking_lip=False,
        bed_size=bed_size,
    )


@pytest.mark.parametrize(
    "grid,bed_size,expected",
    [
        (3, 256, 0),  # fits the bed, no split
        (10, 256, 4),  # 420mm on 256mm: 2x2
        (10, 150, 9),  # 420mm on 150mm: 3x3
    ],
)
def test_split_part_count(tmp_path: Path, grid: float, bed_size: float, expected: int):
    generator = ManifoldSTLGenerator()
    config = _config(grid, bed_size)

    body, text = generator.generate_bin([], config, str(tmp_path / "bin.stl"))
    paths = generator.export_split_parts(body, text, config, bed_size, str(tmp_path), "split")

    assert len(paths) == expected
    assert all(Path(p).exists() for p in paths)


@pytest.mark.parametrize("grid,bed_size", [(10, 256), (10, 150)])
def test_every_part_fits_the_bed(tmp_path: Path, grid: float, bed_size: float):
    # the point of the split, and the thing the old two-piece cap silently
    # broke: it reported a successful split of pieces wider than the bed
    generator = ManifoldSTLGenerator()
    config = _config(grid, bed_size)

    body, text = generator.generate_bin([], config, str(tmp_path / "bin.stl"))
    generator.export_split_parts(body, text, config, bed_size, str(tmp_path), "split")

    x_cuts = generator._compute_split_points(grid * 42.0, grid, bed_size)
    y_cuts = generator._compute_split_points(grid * 42.0, grid, bed_size)
    for piece in (
        p
        for xp in generator._split_along_axis(body, x_cuts, axis="x")
        for p in generator._split_along_axis(xp, y_cuts, axis="y")
    ):
        lo, hi = piece.bounding_box()[:3], piece.bounding_box()[3:]
        assert hi[0] - lo[0] <= bed_size
        assert hi[1] - lo[1] <= bed_size


@pytest.mark.parametrize(
    "grid,bed_size,expected",
    [
        (3, 256, (0, 0)),  # fits the bed
        (10, 256, (2, 2)),
        (10, 150, (3, 3)),
    ],
)
def test_split_field_matches_the_part_count(
    tmp_path: Path, grid: float, bed_size: float, expected: tuple[int, int]
):
    generator = ManifoldSTLGenerator()
    config = _config(grid, bed_size)

    body, text = generator.generate_bin([], config, str(tmp_path / "bin.stl"))
    paths = generator.export_split_parts(body, text, config, bed_size, str(tmp_path), "split")

    cols, rows = generator.split_field(config, bed_size)
    assert (cols, rows) == expected
    assert cols * rows == len(paths)


def test_part_files_sort_in_the_order_they_were_written(tmp_path: Path):
    # the cached response reads parts back with a sorted glob, so an unpadded
    # _part10 would come before _part2
    generator = ManifoldSTLGenerator()
    config = _config(10, 150)
    body, text = generator.generate_bin([], config, str(tmp_path / "bin.stl"))
    written = generator.export_split_parts(body, text, config, 150, str(tmp_path), "split")

    assert [Path(p).name for p in sorted(written)] == [Path(p).name for p in written]


def test_bed_size_outside_the_supported_range_is_rejected():
    # a 1mm bed on a 10u grid would cut 400 parts and zip them, in one request
    with pytest.raises(ValidationError):
        GenerateRequest(bed_size=1)
    with pytest.raises(ValidationError):
        GenerateRequest(bed_size=5000)

    assert GenerateRequest(bed_size=0).bed_size == 0  # 0 means "do not split"
    assert GenerateRequest(bed_size=100).bed_size == 100  # small printers exist


def test_an_absurd_part_count_is_caught_before_anything_is_written():
    # both values are individually legal, so only the product catches this
    generator = ManifoldSTLGenerator()
    cols, rows = generator.split_field(_config(10, 50), 50)

    assert cols * rows > generator.MAX_SPLIT_PARTS


def test_split_parts_cover_the_whole_bin(tmp_path: Path):
    generator = ManifoldSTLGenerator()
    config = _config(10, 150)

    body, text = generator.generate_bin([], config, str(tmp_path / "bin.stl"))
    pieces = generator._split_along_axis(body, [-70.0, 70.0], axis="x")

    assert len(pieces) == 3
    assert abs(sum(p.volume() for p in pieces) - body.volume()) < 1.0
