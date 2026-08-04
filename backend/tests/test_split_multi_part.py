"""Bins larger than twice the bed have to split into more than two parts."""
from pathlib import Path

import pytest
import trimesh
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
    split = generator.export_split_parts(body, text, config, bed_size, str(tmp_path), "split")

    assert len(split.paths) == expected
    assert all(Path(p).exists() for p in split.paths)


@pytest.mark.parametrize("grid,bed_size", [(10, 256), (10, 150)])
def test_every_part_fits_the_bed(tmp_path: Path, grid: float, bed_size: float):
    # the point of the split, and the thing the old two-piece cap silently
    # broke: it reported a successful split of pieces wider than the bed
    generator = ManifoldSTLGenerator()
    config = _config(grid, bed_size)

    body, text = generator.generate_bin([], config, str(tmp_path / "bin.stl"))
    split = generator.export_split_parts(body, text, config, bed_size, str(tmp_path), "split")

    assert split.paths
    for path in split.paths:
        mesh = trimesh.load(path)
        width, depth = mesh.extents[0], mesh.extents[1]
        assert width <= bed_size, f"{Path(path).name} is {width:.1f}mm wide"
        assert depth <= bed_size, f"{Path(path).name} is {depth:.1f}mm deep"


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
    split = generator.export_split_parts(body, text, config, bed_size, str(tmp_path), "split")

    assert (split.cols, split.rows) == expected
    assert split.cols * split.rows == len(split.paths)
    # the pre-generation estimate has to agree, or the part-count guard would
    # refuse work the export would happily do (and vice versa)
    assert generator.split_field(config, bed_size) == expected


def test_part_files_sort_in_the_order_they_were_written(tmp_path: Path):
    # the cached response reads parts back with a sorted glob, so an unpadded
    # _part10 would come before _part2
    generator = ManifoldSTLGenerator()
    config = _config(10, 150)
    body, text = generator.generate_bin([], config, str(tmp_path / "bin.stl"))
    written = generator.export_split_parts(body, text, config, 150, str(tmp_path), "split").paths

    assert [Path(p).name for p in sorted(written)] == [Path(p).name for p in written]


def test_bed_size_outside_the_supported_range_is_rejected():
    # a 1mm bed on a 10u grid would cut 400 parts and zip them, in one request
    with pytest.raises(ValidationError):
        GenerateRequest(bed_size=1)
    with pytest.raises(ValidationError):
        GenerateRequest(bed_size=5000)

    assert GenerateRequest(bed_size=0).bed_size == 0  # 0 means "do not split"
    assert GenerateRequest(bed_size=100).bed_size == 100  # small printers exist


def test_an_absurd_part_count_is_refused_before_anything_is_written(tmp_path: Path):
    # both values are individually legal, so only the product catches this
    from fastapi import HTTPException

    from app.api import routes

    outputs = tmp_path / "outputs"
    outputs.mkdir()

    with pytest.raises(HTTPException) as raised:
        routes._run_generate(
            [], _config(10, 50), "bin", tmp_path, "hash", "user", _OpenStore()
        )

    assert raised.value.status_code == 400
    assert "100 parts" in raised.value.detail
    assert list(outputs.iterdir()) == []


class _OpenStore:
    def ensure_open(self) -> None:
        pass


def test_a_bin_that_fits_the_bed_diagonally_reports_no_field(tmp_path: Path):
    """split_bin refuses to cut a bin that fits corner to corner. split_field
    has to agree, or the preview is handed a field for parts that do not exist
    and the part-count guard counts pieces nobody will print."""
    generator = ManifoldSTLGenerator()
    # 294 x 42mm: (294 + 42) / sqrt(2) = 237.6, inside a 256mm bed, even though
    # 294mm on its own is wider than the bed
    config = GenerateRequest(grid_x=7, grid_y=1, height_units=3, bed_size=256)

    body, text = generator.generate_bin([], config, str(tmp_path / "bin.stl"))
    split = generator.export_split_parts(body, text, config, 256, str(tmp_path), "split")

    assert split.paths == []
    assert generator.split_field(config, 256) == (0, 0)


def test_separated_islands_report_no_field(tmp_path: Path):
    """A partial bin in cut mode exports islands that keep their own positions,
    not a grid of slabs. Reporting a field for them lays them out as a cut plan
    they never had -- and the island count can coincide with the field size."""
    generator = ManifoldSTLGenerator()
    # four isolated corner cells of a 10x10 bin. A 420mm bin on a 256mm bed
    # cuts 2x2, so the island count matches the field size exactly -- a count
    # check cannot tell them apart, which is why the export has to say.
    cells = [False] * 100
    for corner in (0, 9, 90, 99):
        cells[corner] = True
    config = GenerateRequest(
        grid_x=10,
        grid_y=10,
        height_units=3,
        bed_size=256,
        partial_bins=True,
        partial_bins_values=cells,
    )

    body, text = generator.generate_bin([], config, str(tmp_path / "bin.stl"))
    split = generator.export_split_parts(body, text, config, 256, str(tmp_path), "split")

    assert len(split.paths) == 4
    assert generator.split_field(config, 256) == (2, 2)  # the tempting wrong answer
    assert (split.cols, split.rows) == (0, 0)


def test_the_cached_response_reports_the_field_it_was_generated_with(tmp_path: Path):
    """A cache hit cannot re-derive the field: only the export knows whether it
    cut slabs or decomposed islands. It comes back off the hash file."""
    from app.api import routes

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "bin.stl").write_bytes(b"solid\nendsolid\n")
    (outputs / "bin.3mf").write_bytes(b"PK")
    routes._write_hash(outputs / "bin.hash", "same-hash", 3, 3)
    for i in range(1, 10):
        (outputs / f"bin_part{i:02d}.stl").write_bytes(b"solid\nendsolid\n")

    response = routes._run_generate(
        [], _config(10, 150), "bin", tmp_path, "same-hash", "user", _OpenStore()
    )

    assert (response.split_cols, response.split_rows) == (3, 3)
    assert response.split_count == 9


def test_a_hash_file_from_before_the_field_was_recorded_still_loads(tmp_path: Path):
    from app.api import routes

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "bin.stl").write_bytes(b"solid\nendsolid\n")
    (outputs / "bin.3mf").write_bytes(b"PK")
    (outputs / "bin.hash").write_text("same-hash")  # the old one-line format

    response = routes._run_generate(
        [], _config(3, 256), "bin", tmp_path, "same-hash", "user", _OpenStore()
    )

    # no field on record, so the preview falls back to a plain row
    assert (response.split_cols, response.split_rows) == (0, 0)


def test_parts_written_before_zero_padding_still_come_back_in_order(tmp_path: Path):
    from app.api import routes

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    for i in range(1, 13):
        (outputs / f"bin_part{i}.stl").write_bytes(b"solid\nendsolid\n")

    names = [p.name for p in routes._sorted_part_paths(tmp_path, "bin")]

    assert names[:3] == ["bin_part1.stl", "bin_part2.stl", "bin_part3.stl"]
    assert names[-1] == "bin_part12.stl"


def test_split_parts_cover_the_whole_bin(tmp_path: Path):
    generator = ManifoldSTLGenerator()
    config = _config(10, 150)

    body, text = generator.generate_bin([], config, str(tmp_path / "bin.stl"))
    pieces = generator._split_along_axis(body, [-70.0, 70.0], axis="x")

    assert len(pieces) == 3
    assert abs(sum(p.volume() for p in pieces) - body.volume()) < 1.0
