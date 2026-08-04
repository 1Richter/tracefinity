export const GRID_UNIT = 42
/** print bed edge in mm, used as the factory bin default and by the 3D preview */
export const DEFAULT_BED_SIZE_MM = 256
// grid size limits, kept in sync with validate_grid in backend/app/models/schemas.py
export const GRID_MIN_UNITS = 1
export const GRID_MAX_UNITS = 10
// custom (mm) bin sizing limits, mirrors backend app/constants.py
export const CUSTOM_SIZE_MIN_MM = GRID_UNIT
export const CUSTOM_SIZE_MAX_MM = 1000
export const DISPLAY_SCALE = 8
export const SNAP_GRID = 5 // default snap increment in mm
export const SNAP_GRID_MIN = 0.5
export const SNAP_GRID_MAX = 42
export const MAX_HISTORY = 50
// offset in mm applied to a duplicated tool so the copy is visible under the original
export const DUPLICATE_OFFSET = 5
export const ZOOM_FACTOR = 1.15
export const DEFAULT_CUTOUT_DEPTH = 20
export const DOCS_BASE_URL = 'https://github.com/tracefinity/tracefinity/blob/main/docs'

/**
 * Keep a grid size inside the range the backend accepts. Only the range:
 * validate_grid also wants 0.5 steps, which every caller already snaps to.
 */
export function clampGridUnits(units: number): number {
  return Math.min(GRID_MAX_UNITS, Math.max(GRID_MIN_UNITS, units))
}
