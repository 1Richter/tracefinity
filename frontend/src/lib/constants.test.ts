import { describe, expect, it } from 'vitest'
import { clampGridUnits, GRID_MAX_UNITS, GRID_MIN_UNITS } from './constants'

describe('clampGridUnits', () => {
  it('leaves sizes inside the accepted range untouched', () => {
    expect(clampGridUnits(1)).toBe(1)
    expect(clampGridUnits(3.5)).toBe(3.5)
    expect(clampGridUnits(GRID_MAX_UNITS)).toBe(GRID_MAX_UNITS)
  })

  it('clamps oversized grids to the backend maximum', () => {
    expect(clampGridUnits(10.5)).toBe(GRID_MAX_UNITS)
    expect(clampGridUnits(42)).toBe(GRID_MAX_UNITS)
  })

  it('clamps undersized grids to the minimum', () => {
    expect(clampGridUnits(0)).toBe(GRID_MIN_UNITS)
    expect(clampGridUnits(-3)).toBe(GRID_MIN_UNITS)
  })
})
