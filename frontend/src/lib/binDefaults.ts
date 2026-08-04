import type { BinConfig, BinDefaults, BinSummary } from '@/types'
import { GRID_UNIT } from './constants'
import { getSettings, saveSettings } from './settings'

export function createPartialBinsValues(gridX: number, gridY: number): boolean[] {
  return Array(Math.ceil(gridX) * Math.ceil(gridY)).fill(true);
}

/** grid units covered by a custom mm size -- mirrors the backend's resolve_size_mode */
export function gridUnitsForSize(mm: number): number {
  return mm / GRID_UNIT
}

/** whether a config is sized in mm and has both dimensions */
export function isCustomSize(config: Pick<BinDefaults, 'size_mode' | 'custom_width_mm' | 'custom_depth_mm'>): boolean {
  return config.size_mode === 'custom' && config.custom_width_mm != null && config.custom_depth_mm != null
}

/** outer size in mm; custom bins report the exact value the user entered,
 * because deriving it back from the grid is not float-exact (46/42*42 != 46) */
export function binSizeMm(
  config: Pick<BinDefaults, 'size_mode' | 'grid_x' | 'grid_y' | 'custom_width_mm' | 'custom_depth_mm'>
): { width: number; height: number } {
  if (isCustomSize(config)) {
    return { width: config.custom_width_mm!, height: config.custom_depth_mm! }
  }
  return { width: config.grid_x * GRID_UNIT, height: config.grid_y * GRID_UNIT }
}

/** human-readable bin size: "480 × 300 mm" for custom bins, "3x2" for unit bins */
export function formatBinSize(bin: Pick<BinSummary, 'size_mode' | 'grid_x' | 'grid_y' | 'custom_width_mm' | 'custom_depth_mm'>): string {
  if (isCustomSize(bin)) {
    const round = (v: number) => Math.round(v * 10) / 10
    return `${round(bin.custom_width_mm!)} × ${round(bin.custom_depth_mm!)} mm`
  }
  return `${bin.grid_x}x${bin.grid_y}`
}

export const FACTORY_BIN_CONFIG: BinConfig = {
  grid_x: 2,
  grid_y: 2,
  size_mode: 'units',
  custom_width_mm: null,
  custom_depth_mm: null,
  height_units: 4,
  magnets: true,
  magnet_diameter: 6.0,
  magnet_depth: 2.4,
  magnet_corners_only: false,
  stacking_lip: true,
  rim_units: 0,
  wall_thickness: 1.6,
  cutout_depth: 20,
  cutout_clearance: 1.0,
  cutout_chamfer: 0,
  insert_enabled: false,
  insert_height: 1.0,
  insert_clearance: 0.2,
  half_grid_base: false,
  partial_bins: false,
  partial_bins_values: createPartialBinsValues(2, 2),
  partial_bins_connect: false,
  partial_bins_retain_wall: false,
  bed_size: 256,
  text_labels: [],
}

export function buildBinConfig(overrides: Partial<BinDefaults> | null = null): BinConfig {
  const merged = {
      ...FACTORY_BIN_CONFIG,
      ...(overrides || {}),
      text_labels: [] as BinConfig["text_labels"],
  };
  if (isCustomSize(merged)) {
      // the mm size is the source of truth; keep the derived grid in sync so
      // canvas, preview and partial-bin cells all agree with the backend
      merged.grid_x = gridUnitsForSize(merged.custom_width_mm!);
      merged.grid_y = gridUnitsForSize(merged.custom_depth_mm!);
  } else if (merged.size_mode === 'custom') {
      // incomplete custom size, fall back to unit sizing
      merged.size_mode = 'units';
  }
  const expectedLength = Math.ceil(merged.grid_x) * Math.ceil(merged.grid_y);
  if (!merged.partial_bins_values || merged.partial_bins_values.length !== expectedLength) {
      merged.partial_bins_values = createPartialBinsValues(merged.grid_x, merged.grid_y);
  }
  return merged;
}

export function binDefaultsFromConfig(config: Partial<BinConfig>): BinDefaults {
  const { text_labels: _textLabels, ...defaults } = buildBinConfig(config)
  return defaults
}

export function getDefaultBinConfig(): BinConfig {
  const settings = getSettings()
  return buildBinConfig({
    ...(settings.binDefaults || {}),
    bed_size: settings.bedSize,
  })
}

export function getDefaultBinDefaults(): BinDefaults {
  return binDefaultsFromConfig(getDefaultBinConfig())
}

export function saveDefaultBinConfig(config: BinConfig): BinDefaults {
  const defaults = binDefaultsFromConfig(config)
  saveSettings({ bedSize: defaults.bed_size, binDefaults: defaults })
  return defaults
}

export function resetDefaultBinConfig(): BinConfig {
  saveSettings({ bedSize: FACTORY_BIN_CONFIG.bed_size, binDefaults: undefined })
  return buildBinConfig()
}
