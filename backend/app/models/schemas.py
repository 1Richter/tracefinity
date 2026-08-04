from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

from app.constants import (
    CUSTOM_SIZE_MAX_MM,
    CUSTOM_SIZE_MIN_MM,
    GF_GRID,
    MAX_GRID_UNITS,
    PaperSize,
)

# "units" sizes the bin in gridfinity units, "custom" in exact outer mm
SizeMode = Literal["units", "custom"]

# upper bound for the derived unit count in custom mode
MAX_DERIVED_GRID_UNITS = CUSTOM_SIZE_MAX_MM / GF_GRID


class Point(BaseModel):
    x: float
    y: float


class PhotoWarning(BaseModel):
    code: str
    message: str


class FingerHole(BaseModel):
    id: str
    x: float  # center position in pixels
    y: float
    radius: float = 15.0  # radius in mm for circles, half-width for squares
    width: float | None = None  # for rectangles
    height: float | None = None  # for rectangles
    rotation: float = 0.0  # degrees
    shape: Literal["circle", "cylinder", "square", "rectangle", "filleted_rectangle"] = "circle"
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


class CornersRequest(BaseModel):
    corners: list[Point]
    paper_size: PaperSize


class CornersResponse(BaseModel):
    corrected_image_url: str
    scale_factor: float
    warnings: list[PhotoWarning] = []


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
                if value > MAX_GRID_UNITS:
                    raise ValueError(f"grid size must be between 1 and {MAX_GRID_UNITS:.0f}")
                if value * 2 != int(value * 2):
                    raise ValueError("grid size must be a multiple of 0.5")
        return self

    @model_validator(mode="after")
    def normalize_partial_bins_values(self) -> "BinParams":
        import math

        expected = math.ceil(self.grid_x) * math.ceil(self.grid_y)
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
        # the 1-10 / half-unit rules only apply to unit mode and are enforced
        # in resolve_size_mode; custom mode derives grid values up to
        # CUSTOM_SIZE_MAX_MM / 42u, which this bound still has to allow
        if v < 1 or v > MAX_DERIVED_GRID_UNITS + 1e-9:
            raise ValueError(f"grid size must be between 1 and {MAX_GRID_UNITS:.0f}")
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

class BinProject(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: ProjectStatus = "active"
    tool_ids: list[str] = []
    bin_ids: list[str] = []
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

class BinProjectDetail(BinProject):
    placed_tool_ids: list[str] = []
    unplaced_tool_ids: list[str] = []


class BinProjectSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: ProjectStatus = "active"
    tool_count: int = 0
    bin_count: int = 0
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
