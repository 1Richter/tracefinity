from typing import Literal

GF_GRID = 42.0

# gridfinity unit sizing limits (size_mode="units")
MAX_GRID_UNITS = 10.0

# custom mm sizing limits (size_mode="custom"); the minimum is one full
# gridfinity cell, below that the base/lip profile has no room
CUSTOM_SIZE_MIN_MM = GF_GRID
CUSTOM_SIZE_MAX_MM = 1000.0

# how many copies of one tool a project may plan for
MAX_TOOL_QUANTITY = 99

# offset applied to each extra copy when a bin is built with repeated tools,
# so the copies do not land exactly on top of each other
DUPLICATE_OFFSET_MM = 5.0

PaperSize = Literal["a4", "letter", "a3", "tabloid"]

PAPER_SIZES: dict[PaperSize, tuple[float, float]] = {
    "a4": (210, 297),
    "letter": (215.9, 279.4),
    "a3": (297, 420),
    "tabloid": (279.4, 431.8),
}
