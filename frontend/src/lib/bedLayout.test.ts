import { describe, expect, it } from 'vitest'
import { layOutOnBed } from './bedLayout'

const GAP = 10

describe('layOutOnBed', () => {
  it('keeps parts that fit the bed in one row', () => {
    const sizes = [{ w: 100, d: 80 }, { w: 100, d: 80 }]

    const offsets = layOutOnBed(sizes, 256, GAP)

    expect(offsets).toHaveLength(2)
    expect(offsets[0].y).toBe(offsets[1].y)
    expect(offsets[1].x - offsets[0].x).toBe(100 + GAP)
    // centred on the origin
    expect(offsets[0].x).toBe(-(100 + GAP) / 2)
  })

  it('wraps to a second row when the bed is full', () => {
    const sizes = Array.from({ length: 4 }, () => ({ w: 120, d: 120 }))

    const offsets = layOutOnBed(sizes, 256, GAP)

    // two per row: 120 + 10 + 120 = 250 <= 256, a third would not fit
    expect(offsets[0].y).toBe(offsets[1].y)
    expect(offsets[2].y).toBe(offsets[3].y)
    expect(offsets[0].y).toBeGreaterThan(offsets[2].y)
    expect(offsets[0].y - offsets[2].y).toBe(120 + GAP)
  })

  it('centres a 2x2 layout on the origin', () => {
    const sizes = Array.from({ length: 4 }, () => ({ w: 120, d: 120 }))

    const offsets = layOutOnBed(sizes, 256, GAP)

    const xs = offsets.map(o => o.x)
    const ys = offsets.map(o => o.y)
    expect(xs.reduce((a, b) => a + b, 0)).toBeCloseTo(0)
    expect(ys.reduce((a, b) => a + b, 0)).toBeCloseTo(0)
  })

  it('gives a part wider than the bed its own row', () => {
    const sizes = [{ w: 300, d: 100 }, { w: 50, d: 40 }]

    const offsets = layOutOnBed(sizes, 256, GAP)

    expect(offsets[0].y).not.toBe(offsets[1].y)
  })

  it('handles a single part', () => {
    expect(layOutOnBed([{ w: 100, d: 50 }], 256, GAP)).toEqual([{ x: 0, y: 0 }])
  })

  it('handles an empty list', () => {
    expect(layOutOnBed([], 256, GAP)).toEqual([])
  })
})
