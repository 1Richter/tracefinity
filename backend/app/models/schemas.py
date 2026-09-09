from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

from app.constants import (
    CUSTOM_SIZE_MAX_MM,
    CUSTOM_SIZE_MIN_MM,
    GF_GRID,
    MAX_BIN_GRID_CELLS,
    MAX_BIN_GRID_UNITS,
    MAX_TOOL_QUANTITY,
    MIN_BIN_GRID_UNITS,
    PaperSize,
)

# "units" sizes the bin in gridfinity units, "custom" in exact outer mm
SizeMode = Literal["units", "custom"]

# upper bound for the derived unit count in custom mode
MAX_DERIVED_GRID_UNITS = CUSTOM_SIZE_MAX_MM / GF_GRID


class Point(BaseModel):
    x: float
    y: float

    @field_validator("x", "y")
    @classmethod
    def validate_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("point coordinate must be finite")
        return v


class CaptureCrop(BaseModel):
    x: float
    y: float
    width: float
    height: float

    @field_validator("x", "y", "width", "height")
    @classmethod
    def validate_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("capture crop value must be finite")
        return v

    @field_validator("x", "y")
    @classmethod
    def validate_origin(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError("capture crop origin must be between 0 and 1")
        return v

    @field_validator("width", "height")
    @classmethod
    def validate_size(cls, v: float) -> float:
        if v <= 0 or v > 1:
            raise ValueError("capture crop size must be between 0 and 1")
        return v


class PhotoWarning(BaseModel):
    code: str
    message: str


class FingerHole(BaseModel):
    id: str
    x: float  # center position in pixels
    y: float
    radius: float = 15.0  # radius in mm for circles, half-width for squares
    width: float | None = None  # for rectangles; length along the axis for lines
    height: float | None = None  # for rectangles; trench width for lines
    rotation: float = 0.0  # degrees
    shape: Literal[
        "circle", "cylinder", "square", "rectangle", "filleted_rectangle", "line"
    ] = "circle"
    depth_override: float | None = None  # mm; None = use bin_config.cutout_depth


class TextLabel(BaseModel):
    id: str
    text: str
    x: float
    y: float
    font_size: float = 5.0
    rotation: float = 0.0
    emboss: bool = True
    depth: float = 0.5


class Polygon(BaseModel):
    id: str
    points: list[Point]
    label: str
    finger_holes: list[FingerHole] = []
    interior_rings: list[list[Point]] = []


class UploadResponse(BaseModel):
    session_id: str
    image_url: str
    detected_corners: list[Point] | None
    image_width: int | None = None
    image_height: int | None = None
    corner_source: Literal["detected", "station", "none"] = "none"
    station_id: str | None = None


class CornersRequest(BaseModel):
    corners: list[Point]
    paper_size: PaperSize
    save_station_name: str | None = None


class CornersResponse(BaseModel):
    corrected_image_url: str
    scale_factor: float
    warnings: list[PhotoWarning] = []
    station: "PhotoStation | None" = None


class RedetectCornersResponse(BaseModel):
    corners: list[Point]


class TraceRequest(BaseModel):
    provider: Literal["google"] = "google"
    api_key: str | None = None
    tracer: str | None = None


class TraceResponse(BaseModel):
    polygons: list[Polygon]
    mask_url: str | None = None


class PolygonsRequest(BaseModel):
    polygons: list[Polygon]


class BinParams(BaseModel):
    grid_x: float = 2
    grid_y: float = 2
    # custom mode sizes the bin in mm; grid_x/grid_y are then derived from the
    # mm size, so bins written before custom sizing load unchanged
    size_mode: SizeMode = "units"
    custom_width_mm: float | None = None
    custom_depth_mm: float | None = None
    height_units: int = 4
    magnets: bool = True
    magnet_diameter: float = 6.0
    magnet_depth: float = 2.4
    magnet_corners_only: bool = False
    stacking_lip: bool = True
    rim_units: int = 0  # extra height units (x7mm) the wall/lip rises above the floor face
    wall_thickness: float = 1.6
    cutout_depth: float = 20.0
    cutout_clearance: float = 1.0
    insert_enabled: bool = False
    insert_height: float = 1.0
    insert_clearance: float = 0.2  # mm shaved off the insert so it fits the pocket
    cutout_chamfer: float = 0.0
    half_grid_base: bool = False  # use 21mm half-grid cells for the bottom baseplate
    partial_bins: bool = False
    partial_bins_values: list[bool] = []
    partial_bins_connect: bool = False
    partial_bins_retain_wall: bool = False

    @model_validator(mode="after")
    def resolve_size_mode(self) -> "BinParams":
        """Derive grid_x/grid_y from the mm size in custom mode.

        Everything downstream (base cells, magnets, partial bins, splitting)
        already works in fractional gridfinity units, so custom mm sizes only
        need the unit count derived from them; the exact outer footprint comes
        from custom_width_mm/custom_depth_mm in the generator.
        """
        if self.size_mode == "custom":
            if self.custom_width_mm is None or self.custom_depth_mm is None:
                raise ValueError("custom size mode requires custom_width_mm and custom_depth_mm")
            self.grid_x = self.custom_width_mm / GF_GRID
            self.grid_y = self.custom_depth_mm / GF_GRID
        else:
            for value in (self.grid_x, self.grid_y):
                if value < MIN_BIN_GRID_UNITS or value > MAX_BIN_GRID_UNITS:
                    raise ValueError(
                        f"grid size must be between {MIN_BIN_GRID_UNITS:g} and {MAX_BIN_GRID_UNITS:g} units"
                    )
                if value * 2 != int(value * 2):
                    raise ValueError("grid size must be a multiple of 0.5")
        return self

    @model_validator(mode="after")
    def normalize_partial_bins_values(self) -> "BinParams":
        expected = math.ceil(self.grid_x) * math.ceil(self.grid_y)
        # the cell ceiling protects the full-pre-split geometry step; custom mm
        # sizing predates it and is bounded per axis instead (max 23.8u on a
        # 1000mm bin), so it is not gated by the units-mode footprint cap
        if self.size_mode == "units" and expected > MAX_BIN_GRID_CELLS:
            raise ValueError(
                f"grid footprint must not exceed {MAX_BIN_GRID_CELLS} cells"
            )
        if len(self.partial_bins_values) != expected:
            self.partial_bins_values = [True] * expected
        if not self.partial_bins_connect:
            self.partial_bins_retain_wall = False
        if self.partial_bins and not any(self.partial_bins_values):
            raise ValueError("at least one grid cell must remain enabled when partial bins is on")
        return self

    @field_validator("grid_x", "grid_y")
    @classmethod
    def validate_grid(cls, v: float) -> float:
        # the half-unit rules only apply to unit mode and are enforced
        # in resolve_size_mode; custom mode derives grid values up to
        # CUSTOM_SIZE_MAX_MM / 42u, which this bound still has to allow
        # (never above MAX_BIN_GRID_UNITS, so the max is whichever is larger)
        bound = max(MAX_BIN_GRID_UNITS, MAX_DERIVED_GRID_UNITS)
        if v < MIN_BIN_GRID_UNITS or v > bound + 1e-9:
            raise ValueError(
                f"grid size must be between {MIN_BIN_GRID_UNITS:g} and {bound:.0f}"
            )
        return v

    @field_validator("custom_width_mm", "custom_depth_mm")
    @classmethod
    def validate_custom_size(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if v < CUSTOM_SIZE_MIN_MM or v > CUSTOM_SIZE_MAX_MM:
            raise ValueError(
                f"custom size must be between {CUSTOM_SIZE_MIN_MM:.0f} and {CUSTOM_SIZE_MAX_MM:.0f}mm"
            )
        return v

    @field_validator("height_units")
    @classmethod
    def validate_height(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("height must be between 1 and 20 units")
        return v

    @field_validator("rim_units")
    @classmethod
    def validate_rim(cls, v: int) -> int:
        if v < 0 or v > 20:
            raise ValueError("rim must be between 0 and 20 units")
        return v

    @field_validator("cutout_depth")
    @classmethod
    def validate_depth(cls, v: float) -> float:
        if v < 1 or v > 200:
            raise ValueError("cutout depth must be between 1 and 200mm")
        return v

    @field_validator("cutout_clearance")
    @classmethod
    def validate_clearance(cls, v: float) -> float:
        if v < 0 or v > 10:
            raise ValueError("clearance must be between 0 and 10mm")
        return v

    @field_validator("insert_height")
    @classmethod
    def validate_insert_height(cls, v: float) -> float:
        if v < 0.1 or v > 10:
            raise ValueError("insert height must be between 0.1 and 10mm")
        return v

    @field_validator("insert_clearance")
    @classmethod
    def validate_insert_clearance(cls, v: float) -> float:
        if v < 0 or v > 2:
            raise ValueError("insert clearance must be between 0 and 2mm")
        return v

    @field_validator("cutout_chamfer")
    @classmethod
    def validate_chamfer(cls, v: float) -> float:
        if v < 0 or v > 5:
            raise ValueError("cutout chamfer must be between 0 and 5mm")
        return v

    @field_validator("wall_thickness")
    @classmethod
    def validate_wall(cls, v: float) -> float:
        if v < 0.4 or v > 5:
            raise ValueError("wall thickness must be between 0.4 and 5mm")
        return v

    @model_validator(mode="after")
    def half_grid_disables_magnets(self) -> "BinParams":
        if self.half_grid_base:
            self.magnets = False
        return self


class BinDefaults(BinParams):
    bed_size: float = 256.0  # mm, 0 = no splitting

    @field_validator("bed_size")
    @classmethod
    def validate_bed_size(cls, v: float) -> float:
        # the split cuts one slab per bed length, so a bed of a millimetre
        # turns a large grid into hundreds of STLs plus a ZIP in one request.
        # Wider than the frontend slider (BED_SIZE_MIN_MM / BED_SIZE_MAX_MM in
        # frontend/src/lib/settings.ts) because the API also serves printers
        # outside the sizes the slider offers; the part count itself is capped
        # separately, since a legal bed and a legal grid can still combine into
        # an unreasonable number of pieces.
        if v == 0:
            return v
        if v < 50 or v > 1000:
            raise ValueError("bed size must be 0 (no splitting) or between 50 and 1000mm")
        return v


class GenerateRequest(BinDefaults):
    polygons: list[Polygon] | None = None  # optional: use these instead of session polygons
    text_labels: list[TextLabel] = []


class GenerateResponse(BaseModel):
    stl_url: str
    stl_urls: list[str] = []
    threemf_url: str | None = None
    split_count: int = 1
    # the field the parts were cut into, so the preview can lay them out the
    # way they will actually be printed. Both 0 when there is no split, or when
    # the parts do not form a regular field. stl_urls is column-major:
    # index = col * split_rows + row.
    split_cols: int = 0
    split_rows: int = 0
    zip_url: str | None = None
    insert_stl_url: str | None = None
    warning: str | None = None


class Layout(BaseModel):
    bin_config: GenerateRequest = GenerateRequest()
    polygons: list[Polygon] = []
    text_labels: list[TextLabel] = []


class Session(BaseModel):
    id: str
    name: str | None = None
    description: str | None = None
    tags: list[str] = []
    created_at: str | None = None
    original_image_path: str | None = None
    original_image_width: int | None = None
    original_image_height: int | None = None
    capture_crop: CaptureCrop | None = None
    corrected_image_path: str | None = None
    mask_image_path: str | None = None
    corners: list[Point] | None = None
    paper_size: PaperSize | None = None
    scale_factor: float | None = None
    focal_length_35mm: float | None = None
    photo_warnings: list[PhotoWarning] | None = None
    polygons: list[Polygon] | None = None
    stl_path: str | None = None
    layout: Layout | None = None


class SessionSummary(BaseModel):
    id: str
    name: str | None
    description: str | None
    tags: list[str]
    created_at: str | None
    thumbnail_url: str | None
    tool_count: int
    has_stl: bool


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]


class SessionUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    layout: Layout | None = None


class StatusResponse(BaseModel):
    status: str


# --- photo stations ---

PhotoStationMatchStatus = Literal["exact", "near", "far"]


class PhotoStation(BaseModel):
    id: str
    name: str
    image_width: int
    image_height: int
    image_path: str | None = None
    capture_crop: CaptureCrop | None = None
    paper_size: PaperSize
    corners: list[Point]
    created_at: str | None = None
    updated_at: str | None = None
    last_used_at: str | None = None

    @field_validator("image_width", "image_height")
    @classmethod
    def validate_image_dimension(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("station image dimensions must be positive")
        return v

    @field_validator("corners")
    @classmethod
    def validate_corners(cls, v: list[Point]) -> list[Point]:
        if len(v) != 4:
            raise ValueError("station corners must contain four points")
        return v


class PhotoStationSuggestion(BaseModel):
    station: PhotoStation
    match_status: PhotoStationMatchStatus
    width_delta_percent: float = 0.0
    height_delta_percent: float = 0.0
    max_corner_drift_px: float | None = None
    max_corner_drift_percent: float | None = None
    warnings: list[str] = []


class PhotoStationListResponse(BaseModel):
    stations: list[PhotoStation]


class PhotoStationSuggestionsResponse(BaseModel):
    suggestions: list[PhotoStationSuggestion]
    station_count: int


class PhotoStationCreateRequest(BaseModel):
    name: str
    session_id: str
    paper_size: PaperSize | None = None
    corners: list[Point] | None = None


class PhotoStationUpdateRequest(BaseModel):
    name: str | None = None
    paper_size: PaperSize | None = None
    corners: list[Point] | None = None


class ReuseCornersRequest(BaseModel):
    station_id: str


class ReuseCornersResponse(BaseModel):
    corners: list[Point]
    paper_size: PaperSize
    suggestion: PhotoStationSuggestion


# --- tool library ---

class Tool(BaseModel):
    id: str
    name: str
    points: list[Point]  # mm, centered at (0,0)
    finger_holes: list[FingerHole] = []  # mm, relative to tool origin
    interior_rings: list[list[Point]] = []  # mm, centered at (0,0)
    smoothed: bool = True
    smooth_level: float = 0.5
    source_session_id: str | None = None
    source_polygon_id: str | None = None
    source_image_path: str | None = None
    source_image_width: int | None = None
    source_image_height: int | None = None
    source_image_transform: list[float] | None = None  # 2D affine [a, b, c, d, e, f] mapping image-px to mm
    category: str | None = None
    drawer: str | None = None
    tags: list[str] = []
    project_ids: list[str] = []
    review_status: str | None = None
    needs_cleanup: bool = False
    thumbnail_path: str | None = None
    created_at: str | None = None


class ToolDetailResponse(Tool):
    image_context: dict | None = None


class ToolSummary(BaseModel):
    id: str
    name: str
    created_at: str | None
    point_count: int
    points: list[Point] = []
    interior_rings: list[list[Point]] = []
    smoothed: bool = False
    smooth_level: float = 0.5
    thumbnail_url: str | None = None
    image_transform: list[float] | None = None
    image_context: dict | None = None
    category: str | None = None
    drawer: str | None = None
    tags: list[str] = []
    project_ids: list[str] = []
    review_status: str | None = None
    needs_cleanup: bool = False


class ToolUpdateRequest(BaseModel):
    name: str | None = None
    points: list[Point] | None = None
    finger_holes: list[FingerHole] | None = None
    interior_rings: list[list[Point]] | None = None
    smoothed: bool | None = None
    smooth_level: float | None = None
    source_image_transform: list[float] | None = None
    category: str | None = None
    drawer: str | None = None
    tags: list[str] | None = None
    project_ids: list[str] | None = None
    review_status: str | None = None
    needs_cleanup: bool | None = None


class ToolListResponse(BaseModel):
    tools: list[ToolSummary]


class SaveToolsRequest(BaseModel):
    polygon_ids: list[str] | None = None


class SaveToolsResponse(BaseModel):
    tool_ids: list[str]


# --- bin projects ---

ProjectStatus = Literal["active", "ready_to_print", "printed", "archived"]
ProjectHealthSeverity = Literal["warning", "error"]
ProjectHealthCode = Literal[
    "missing_tool",
    "missing_bin",
    "bin_missing_project_id",
    "bin_project_mismatch",
    "outside_tool",
    "tool_missing_project_id",
    "tool_extra_project_id",
]


def validate_quantity(v: int) -> int:
    if v < 1 or v > MAX_TOOL_QUANTITY:
        raise ValueError(f"quantity must be between 1 and {MAX_TOOL_QUANTITY}")
    return v


class BinProject(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: ProjectStatus = "active"
    tool_ids: list[str] = []
    bin_ids: list[str] = []
    # how many copies of a tool the project plans for; a tool_id missing from
    # the map means 1, so projects written before quantities load unchanged
    tool_quantities: dict[str, int] = {}
    target_grid_x: float | None = None
    target_grid_y: float | None = None
    default_bin_config: BinDefaults | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @field_validator("target_grid_x", "target_grid_y")
    @classmethod
    def validate_target_grid(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if v < 1 or v > 10:
            raise ValueError("grid size must be between 1 and 10")
        if v * 2 != int(v * 2):
            raise ValueError("grid size must be a multiple of 0.5")
        return v

    @field_validator("tool_quantities")
    @classmethod
    def validate_tool_quantities(cls, v: dict[str, int]) -> dict[str, int]:
        return {
            tool_id: validate_quantity(quantity)
            for tool_id, quantity in v.items()
            if quantity != 1
        }


class BinProjectDetail(BinProject):
    placed_tool_ids: list[str] = []
    unplaced_tool_ids: list[str] = []
    # placements found across the project's linked bins, per tool
    placed_counts: dict[str, int] = {}


class BinProjectSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: ProjectStatus = "active"
    tool_count: int = 0
    bin_count: int = 0
    total_quantity: int = 0
    placed_count: int = 0
    unplaced_count: int = 0
    target_grid_x: float | None = None
    target_grid_y: float | None = None
    created_at: str | None = None
    updated_at: str | None = None


class BinProjectListResponse(BaseModel):
    projects: list[BinProjectSummary]


class BinProjectCreateRequest(BaseModel):
    name: str
    description: str | None = None
    status: ProjectStatus = "active"
    target_grid_x: float | None = None
    target_grid_y: float | None = None
    default_bin_config: BinDefaults | None = None
    notes: str | None = None
    tool_ids: list[str] = []

    @field_validator("target_grid_x", "target_grid_y")
    @classmethod
    def validate_target_grid(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if v < 1 or v > 10:
            raise ValueError("grid size must be between 1 and 10")
        if v * 2 != int(v * 2):
            raise ValueError("grid size must be a multiple of 0.5")
        return v


class BinProjectUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None
    target_grid_x: float | None = None
    target_grid_y: float | None = None
    default_bin_config: BinDefaults | None = None
    notes: str | None = None

    @field_validator("target_grid_x", "target_grid_y")
    @classmethod
    def validate_target_grid(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if v < 1 or v > 10:
            raise ValueError("grid size must be between 1 and 10")
        if v * 2 != int(v * 2):
            raise ValueError("grid size must be a multiple of 0.5")
        return v


class BinProjectToolsRequest(BaseModel):
    tool_ids: list[str]


class BinProjectToolQuantityRequest(BaseModel):
    quantity: int

    @field_validator("quantity")
    @classmethod
    def validate_tool_quantity(cls, v: int) -> int:
        return validate_quantity(v)


class BinProjectCreateBinRequest(BaseModel):
    name: str | None = None
    tool_ids: list[str] | None = None
    bin_config: BinDefaults | None = None


class BinProjectBinsRequest(BaseModel):
    bin_ids: list[str]
    import_tools: bool = False
    allow_reassign: bool = False


class ProjectHealthIssue(BaseModel):
    code: ProjectHealthCode
    severity: ProjectHealthSeverity
    message: str
    tool_id: str | None = None
    bin_id: str | None = None
    other_project_id: str | None = None
    repairable: bool = False


class ProjectHealthResponse(BaseModel):
    issues: list[ProjectHealthIssue]
    repairable_count: int = 0
    manual_count: int = 0


# --- bins ---

class PlacedTool(BaseModel):
    id: str  # placement instance id
    tool_id: str  # reference to library tool
    name: str
    points: list[Point]  # mm, bin-space (always raw/accurate)
    finger_holes: list[FingerHole] = []  # mm, bin-space
    interior_rings: list[list[Point]] = []  # mm, bin-space
    rotation: float = 0.0  # degrees, applied on top of library points
    depth_override: float | None = None  # mm; None = use bin_config.cutout_depth
    # cutouts edited in the bin editor. library holes listed here keep their
    # bin-local geometry on sync; ids listed as removed stay out of this
    # placement. holes added in the bin have ids the library does not know.
    custom_hole_ids: list[str] = []
    removed_hole_ids: list[str] = []


class BinConfig(BinDefaults):
    text_labels: list[TextLabel] = []


class BinModel(BaseModel):
    id: str
    name: str | None = None
    project_id: str | None = None
    bin_config: BinConfig = BinConfig()
    placed_tools: list[PlacedTool] = []
    text_labels: list[TextLabel] = []
    stl_path: str | None = None
    created_at: str | None = None


class BinPreviewTool(BaseModel):
    points: list[Point]
    interior_rings: list[list[Point]] = []

class BinSummary(BaseModel):
    id: str
    name: str | None
    project_id: str | None = None
    created_at: str | None
    tool_ids: list[str] = []
    tool_count: int
    has_stl: bool
    grid_x: float = 2
    grid_y: float = 2
    size_mode: SizeMode = "units"
    custom_width_mm: float | None = None
    custom_depth_mm: float | None = None
    preview_tools: list[BinPreviewTool] = []


class BinListResponse(BaseModel):
    bins: list[BinSummary]


class BinUpdateRequest(BaseModel):
    name: str | None = None
    project_id: str | None = None
    bin_config: BinConfig | None = None
    placed_tools: list[PlacedTool] | None = None
    text_labels: list[TextLabel] | None = None


class CreateBinRequest(BaseModel):
    name: str | None = None
    project_id: str | None = None
    tool_ids: list[str] = []  # pre-place these tools
    bin_config: BinDefaults | None = None
