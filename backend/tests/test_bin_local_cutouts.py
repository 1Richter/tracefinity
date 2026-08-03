"""Cutouts edited inside the bin editor survive sync_placed_tools.

Moving, resizing, adding or deleting a cutout on a placed tool only affects
that placement. Without the custom/removed id lists, GET /bins/{id} rebuilt
finger_holes from the library tool and reverted every bin-local edit.
"""
from app.models.schemas import BinConfig, BinModel, FingerHole, PlacedTool, Point, Tool
from app.services.bin_service import sync_placed_tools


class _Store:
    def __init__(self, items):
        self._d = {item.id: item for item in items}

    def get(self, key):
        return self._d.get(key)


def _source_tool(hole_ids=("h1",)):
    return Tool(
        id="tool1",
        name="hammer",
        points=[Point(x=0, y=0), Point(x=10, y=0), Point(x=10, y=10), Point(x=0, y=10)],
        finger_holes=[FingerHole(id=hid, x=5, y=5, radius=2.0, shape="circle") for hid in hole_ids],
        interior_rings=[],
    )


def _bin_with(holes, **placed_kwargs):
    placed = PlacedTool(
        id="placement1",
        tool_id="tool1",
        name="hammer",
        points=[Point(x=20, y=20), Point(x=30, y=20), Point(x=30, y=30), Point(x=20, y=30)],
        finger_holes=holes,
        interior_rings=[],
        **placed_kwargs,
    )
    return BinModel(id="bin1", bin_config=BinConfig(), placed_tools=[placed])


def _holes(bin_data):
    return {fh.id: fh for fh in bin_data.placed_tools[0].finger_holes}


def test_placed_tools_default_to_no_custom_cutouts():
    placed = PlacedTool(id="p1", tool_id="tool1", name="hammer", points=[Point(x=0, y=0)])

    assert placed.custom_hole_ids == []
    assert placed.removed_hole_ids == []


def test_moved_cutout_keeps_its_bin_position():
    moved = FingerHole(id="h1", x=28, y=22, radius=2.0, shape="circle")
    bin_data = _bin_with([moved], custom_hole_ids=["h1"])

    sync_placed_tools(bin_data, _Store([_source_tool()]))

    assert (_holes(bin_data)["h1"].x, _holes(bin_data)["h1"].y) == (28, 22)


def test_resized_and_rotated_cutout_keeps_its_bin_geometry():
    edited = FingerHole(id="h1", x=25, y=25, radius=6.0, width=9, height=4,
                        rotation=30, shape="rectangle")
    bin_data = _bin_with([edited], custom_hole_ids=["h1"])

    sync_placed_tools(bin_data, _Store([_source_tool()]))

    hole = _holes(bin_data)["h1"]
    assert (hole.radius, hole.width, hole.height, hole.rotation, hole.shape) == (
        6.0, 9, 4, 30, "rectangle",
    )


def test_uncustomised_cutout_still_follows_the_library_tool():
    bin_data = _bin_with([FingerHole(id="h1", x=99, y=99, radius=2.0, shape="circle")])

    sync_placed_tools(bin_data, _Store([_source_tool()]))

    # library hole sits at the tool centre, so it lands on the placement centre
    assert (_holes(bin_data)["h1"].x, _holes(bin_data)["h1"].y) == (25, 25)


def test_deleted_cutout_does_not_come_back():
    bin_data = _bin_with([], removed_hole_ids=["h1"])

    sync_placed_tools(bin_data, _Store([_source_tool()]))

    assert bin_data.placed_tools[0].finger_holes == []


def test_deleting_one_cutout_keeps_the_others():
    bin_data = _bin_with(
        [FingerHole(id="h2", x=25, y=25, radius=2.0, shape="circle")],
        removed_hole_ids=["h1"],
    )

    sync_placed_tools(bin_data, _Store([_source_tool(("h1", "h2"))]))

    assert list(_holes(bin_data)) == ["h2"]


def test_cutout_added_in_the_bin_survives():
    added = FingerHole(id="bfh-1", x=27, y=23, radius=3.0, shape="cylinder")
    bin_data = _bin_with([FingerHole(id="h1", x=25, y=25, radius=2.0, shape="circle"), added])

    sync_placed_tools(bin_data, _Store([_source_tool()]))

    holes = _holes(bin_data)
    assert set(holes) == {"h1", "bfh-1"}
    assert (holes["bfh-1"].x, holes["bfh-1"].y, holes["bfh-1"].shape) == (27, 23, "cylinder")


def test_bin_local_edits_do_not_touch_the_library_tool():
    tool = _source_tool()
    bin_data = _bin_with(
        [FingerHole(id="h1", x=28, y=22, radius=7.0, shape="circle")],
        custom_hole_ids=["h1"],
    )

    sync_placed_tools(bin_data, _Store([tool]))

    assert (tool.finger_holes[0].x, tool.finger_holes[0].y, tool.finger_holes[0].radius) == (5, 5, 2.0)


def test_depth_override_still_survives_a_custom_hole():
    edited = FingerHole(id="h1", x=28, y=22, radius=2.0, shape="circle", depth_override=25.0)
    bin_data = _bin_with([edited], custom_hole_ids=["h1"])

    sync_placed_tools(bin_data, _Store([_source_tool()]))

    assert _holes(bin_data)["h1"].depth_override == 25.0


def test_sync_is_stable_on_a_second_pass():
    bin_data = _bin_with(
        [
            FingerHole(id="h1", x=28, y=22, radius=2.0, shape="circle"),
            FingerHole(id="bfh-1", x=27, y=23, radius=3.0, shape="cylinder"),
        ],
        custom_hole_ids=["h1"],
        removed_hole_ids=["h2"],
    )
    tools = _Store([_source_tool(("h1", "h2"))])

    sync_placed_tools(bin_data, tools)
    first = [fh.model_dump() for fh in bin_data.placed_tools[0].finger_holes]
    changed_again = sync_placed_tools(bin_data, tools)

    assert changed_again is False
    assert [fh.model_dump() for fh in bin_data.placed_tools[0].finger_holes] == first
