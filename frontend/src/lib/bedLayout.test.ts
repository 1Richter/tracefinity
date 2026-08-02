import { describe, expect, it } from 'vitest'
import { layOutCutField } from './bedLayout'

const GAP = 10

/**
 * What split_bin actually produces, not synthetic sizes: it makes each slab as
 * large as the bed allows, so a 420mm bin becomes 2x2 of ~210mm on a 256mm bed
 * and 3x3 of ~140mm on a 150mm bed. Sizes measured from the generated STLs.
 */
const SPLIT_2X2 = Array.from({ length: 4 }, () => ({ w: 209.8, d: 209.8 }))
const SPLIT_3X3 = Array.from({ length: 9 }, () => ({ w: 147, d: 147 }))

describe('layOutCutField', () => {
  it('places a 2x2 split in two columns and two rows', () => {
    const offsets = layOutCutField(SPLIT_2X2, 2, 2, GAP)

    // column-major: [col0row0, col0row1, col1row0, col1row1]
    expect(offsets[0].x).toBe(offsets[1].x)
    expect(offsets[2].x).toBe(offsets[3].x)
    expect(offsets[0].y).toBe(offsets[2].y)
    expect(offsets[1].y).toBe(offsets[3].y)
    expect(offsets[2].x - offsets[0].x).toBeCloseTo(209.8 + GAP)
    expect(offsets[1].y - offsets[0].y).toBeCloseTo(209.8 + GAP)
  })

  it('keeps a 3x3 split three parts wide instead of stacking nine rows', () => {
    const offsets = layOutCutField(SPLIT_3X3, 3, 3, GAP)

    expect(new Set(offsets.map(o => o.x)).size).toBe(3)
    expect(new Set(offsets.map(o => o.y)).size).toBe(3)
  })

  it('centres the field on the origin', () => {
    const offsets = layOutCutField(SPLIT_3X3, 3, 3, GAP)

    expect(offsets.reduce((sum, o) => sum + o.x, 0)).toBeCloseTo(0)
    expect(offsets.reduce((sum, o) => sum + o.y, 0)).toBeCloseTo(0)
  })

  it('counts rows from the low end of the axis, as the backend cuts them', () => {
    const offsets = layOutCutField(SPLIT_2X2, 2, 2, GAP)

    expect(offsets[0].y).toBeLessThan(offsets[1].y)
  })

  it('sizes each column and row to its largest part', () => {
    // a fractional grid leaves a narrower trailing slab
    const sizes = [
      { w: 200, d: 200 }, { w: 200, d: 90 },
      { w: 80, d: 200 }, { w: 80, d: 90 },
    ]

    const offsets = layOutCutField(sizes, 2, 2, GAP)

    expect(offsets[2].x - offsets[0].x).toBeCloseTo(200 / 2 + GAP + 80 / 2)
    expect(offsets[1].y - offsets[0].y).toBeCloseTo(200 / 2 + GAP + 90 / 2)
  })

  it('falls back to a single row when there is no regular field', () => {
    // separated partial-bin islands report 0 x 0
    const sizes = [{ w: 100, d: 80 }, { w: 60, d: 40 }, { w: 30, d: 30 }]

    const offsets = layOutCutField(sizes, 0, 0, GAP)

    expect(new Set(offsets.map(o => o.y)).size).toBe(1)
    expect(offsets[1].x).toBeGreaterThan(offsets[0].x)
    expect(offsets[2].x).toBeGreaterThan(offsets[1].x)
  })

  it('falls back when the field disagrees with the part count', () => {
    const offsets = layOutCutField(SPLIT_2X2, 3, 3, GAP)

    expect(new Set(offsets.map(o => o.y)).size).toBe(1)
  })

  it('handles a single part', () => {
    expect(layOutCutField([{ w: 100, d: 50 }], 1, 1, GAP)).toEqual([{ x: 0, y: 0 }])
  })

  it('handles an empty list', () => {
    expect(layOutCutField([], 0, 0, GAP)).toEqual([])
  })
})
