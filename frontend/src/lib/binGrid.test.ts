import { describe, expect, it } from 'vitest'
import { gridUnitsForSpan, pointBounds } from './binGrid'
import { clampGridUnits, GRID_MAX_UNITS } from './constants'

const MARGIN = 2 * 1.2 + 2 * 0.5 + 0.5 // wall + clearance, the bin editor's default

describe('pointBounds', () => {
  it('returns null when there is nothing to measure', () => {
    expect(pointBounds([])).toBeNull()
    expect(pointBounds([[]])).toBeNull()
  })

  it('spans every polygon, not just the first', () => {
    const bounds = pointBounds([
      [{ x: 10, y: 10 }, { x: 20, y: 30 }],
      [{ x: -5, y: 15 }, { x: 15, y: 40 }],
    ])

    expect(bounds).toEqual({ minX: -5, minY: 10, maxX: 20, maxY: 40 })
  })
})

describe('gridUnitsForSpan', () => {
  it('never goes below one unit', () => {
    expect(gridUnitsForSpan(1, MARGIN, 1)).toBe(1)
  })

  it('rounds up to whole units', () => {
    expect(gridUnitsForSpan(50, MARGIN, 1)).toBe(2)
  })

  it('rounds up to half units when the half-grid base is on', () => {
    expect(gridUnitsForSpan(50, MARGIN, 0.5)).toBe(1.5)
  })

  it('reports what a tool needs even when the backend would reject it', () => {
    // a 600mm tool needs more than the 10u / 420mm maximum, and the banner
    // depends on seeing that rather than a pre-clamped value
    const needed = gridUnitsForSpan(600, MARGIN, 1)

    expect(needed).toBeGreaterThan(GRID_MAX_UNITS)
    expect(clampGridUnits(needed)).toBe(GRID_MAX_UNITS)
  })
})
