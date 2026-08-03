import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  binDefaultsFromConfig,
  buildBinConfig,
  formatBinSize,
  getDefaultBinConfig,
  getDefaultBinDefaults,
  isCustomSize,
  resetDefaultBinConfig,
  saveDefaultBinConfig,
} from './binDefaults'
import type { BinSummary } from '@/types'

const SETTINGS_KEY = 'tracefinity-settings'

function installLocalStorage() {
  const data = new Map<string, string>()
  const storage = {
    get length() {
      return data.size
    },
    clear: () => data.clear(),
    getItem: (key: string) => data.get(key) ?? null,
    key: (index: number) => Array.from(data.keys())[index] ?? null,
    removeItem: (key: string) => data.delete(key),
    setItem: (key: string, value: string) => data.set(key, value),
  } as Storage

  vi.stubGlobal('window', { localStorage: storage })
  vi.stubGlobal('localStorage', storage)
  return storage
}

describe('bin defaults', () => {
  let storage: Storage

  beforeEach(() => {
    storage = installLocalStorage()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('normalizes partial_bins_values to match grid size', () => {
    const config = buildBinConfig({ grid_x: 3, grid_y: 4 })

    expect(config.partial_bins).toBe(false)
    expect(config.partial_bins_values).toEqual(Array(12).fill(true))
  })

  it('resets partial_bins_values when grid overrides change size', () => {
    const config = buildBinConfig({
      grid_x: 3,
      grid_y: 2,
      partial_bins_values: [true, true],
    })

    expect(config.partial_bins_values).toEqual(Array(6).fill(true))
  })

  it('uses legacy bedSize when no full bin defaults are saved', () => {
    storage.setItem(SETTINGS_KEY, JSON.stringify({ bedSize: 220 }))

    const defaults = getDefaultBinConfig()

    expect(defaults.bed_size).toBe(220)
    expect(defaults.magnet_diameter).toBe(6)
  })

  it('saves and restores magnet defaults', () => {
    saveDefaultBinConfig(buildBinConfig({
      magnet_diameter: 6.2,
      magnet_depth: 2.8,
      magnet_corners_only: true,
      bed_size: 230,
    }))

    const stored = JSON.parse(storage.getItem(SETTINGS_KEY) || '{}')
    const defaults = getDefaultBinDefaults()

    expect(stored.bedSize).toBe(230)
    expect(defaults.magnet_diameter).toBe(6.2)
    expect(defaults.magnet_depth).toBe(2.8)
    expect(defaults.magnet_corners_only).toBe(true)
    expect('text_labels' in defaults).toBe(false)
  })

  it('strips text labels when deriving defaults from a full config', () => {
    const defaults = binDefaultsFromConfig({
      ...buildBinConfig({ magnet_diameter: 6.2 }),
      text_labels: [{ id: 'label-1', text: '12mm', x: 1, y: 2, font_size: 4, rotation: 0, emboss: true, depth: 0.6 }],
    })

    expect(defaults.magnet_diameter).toBe(6.2)
    expect('text_labels' in defaults).toBe(false)
  })

  it('keeps the legacy bedSize setting authoritative', () => {
    storage.setItem(SETTINGS_KEY, JSON.stringify({
      bedSize: 245,
      binDefaults: { magnet_diameter: 6.2, bed_size: 220 },
    }))

    const defaults = getDefaultBinDefaults()

    expect(defaults.bed_size).toBe(245)
    expect(defaults.magnet_diameter).toBe(6.2)
  })

  it('clears saved defaults without leaving a stale binDefaults key', () => {
    saveDefaultBinConfig(buildBinConfig({ magnet_diameter: 6.2 }))

    const reset = resetDefaultBinConfig()
    const stored = JSON.parse(storage.getItem(SETTINGS_KEY) || '{}')

    expect(reset.magnet_diameter).toBe(6)
    expect(stored.bedSize).toBe(256)
    expect(stored.binDefaults).toBeUndefined()
  })

  it('defaults to unit sizing', () => {
    const config = buildBinConfig()

    expect(config.size_mode).toBe('units')
    expect(config.custom_width_mm).toBeNull()
    expect(isCustomSize(config)).toBe(false)
  })

  it('derives the grid from a custom mm size', () => {
    const config = buildBinConfig({
      size_mode: 'custom',
      custom_width_mm: 480,
      custom_depth_mm: 300,
      grid_x: 2,
      grid_y: 2,
    })

    expect(config.grid_x).toBeCloseTo(480 / 42)
    expect(config.grid_y).toBeCloseTo(300 / 42)
    // 12 columns x 8 rows of 42mm cells cover the custom size
    expect(config.partial_bins_values).toHaveLength(96)
  })

  it('falls back to unit sizing when a custom size is incomplete', () => {
    const config = buildBinConfig({ size_mode: 'custom', custom_width_mm: 480 })

    expect(config.size_mode).toBe('units')
    expect(config.grid_x).toBe(2)
  })

  it('formats bin sizes for cards', () => {
    const summary = (overrides: Partial<BinSummary>): BinSummary => ({
      id: 'bin-1',
      name: null,
      project_id: null,
      created_at: null,
      tool_ids: [],
      tool_count: 0,
      has_stl: false,
      grid_x: 2,
      grid_y: 3,
      size_mode: 'units',
      custom_width_mm: null,
      custom_depth_mm: null,
      preview_tools: [],
      ...overrides,
    })

    expect(formatBinSize(summary({}))).toBe('2x3')
    expect(
      formatBinSize(summary({ size_mode: 'custom', custom_width_mm: 480, custom_depth_mm: 300.25 }))
    ).toBe('480 × 300.3 mm')
  })

  it('does not throw when localStorage writes are unavailable', () => {
    const storage = {
      get length() {
        return 0
      },
      clear: () => {},
      getItem: () => null,
      key: () => null,
      removeItem: () => {},
      setItem: () => {
        throw new Error('localStorage blocked')
      },
    } as Storage
    vi.stubGlobal('window', { localStorage: storage })
    vi.stubGlobal('localStorage', storage)

    expect(() => saveDefaultBinConfig(buildBinConfig({ magnet_diameter: 6.2 }))).not.toThrow()
    expect(() => resetDefaultBinConfig()).not.toThrow()
  })
})
