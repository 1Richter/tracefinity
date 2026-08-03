from typing import Literal

GF_GRID = 42.0

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
