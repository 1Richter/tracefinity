"""Bins larger than twice the bed have to split into more than two parts."""
from pathlib import Path

import pytest

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


def test_split_parts_cover_the_whole_bin(tmp_path: Path):
    generator = ManifoldSTLGenerator()
    config = _config(10, 150)

    body, text = generator.generate_bin([], config, str(tmp_path / "bin.stl"))
    pieces = generator._split_along_axis(body, [-70.0, 70.0], axis="x")

    assert len(pieces) == 3
    assert abs(sum(p.volume() for p in pieces) - body.volume()) < 1.0
