export const GRID_UNIT = 42
// grid size limits, kept in sync with validate_grid in backend/app/models/schemas.py
export const GRID_MIN_UNITS = 1
export const GRID_MAX_UNITS = 10
export const DISPLAY_SCALE = 8
export const SNAP_GRID = 5 // default snap increment in mm
export const SNAP_GRID_MIN = 0.5
export const SNAP_GRID_MAX = 42
export const MAX_HISTORY = 50
export const ZOOM_FACTOR = 1.15
export const DEFAULT_CUTOUT_DEPTH = 20
export const DOCS_BASE_URL = 'https://github.com/tracefinity/tracefinity/blob/main/docs'

/** Keep a grid size inside the range the backend accepts. */
export function clampGridUnits(units: number): number {
  return Math.min(GRID_MAX_UNITS, Math.max(GRID_MIN_UNITS, units))
}
