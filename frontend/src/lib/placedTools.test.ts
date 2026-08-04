import { describe, expect, it } from 'vitest'

import { duplicatePlacedTool } from './placedTools'
import type { PlacedTool } from '@/types'

const placedTool = (): PlacedTool => ({
  id: 'pt-1',
  tool_id: 'tool-1',
  name: 'Wrench',
  points: [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }],
  finger_holes: [{ id: 'fh-1', x: 5, y: 5, radius: 2, rotation: 0, shape: 'circle' }],
  interior_rings: [[{ x: 2, y: 2 }, { x: 4, y: 2 }, { x: 4, y: 4 }]],
  rotation: 0,
})

describe('duplicatePlacedTool', () => {
  it('offsets the copy and keeps the source tool id', () => {
    const source = placedTool()

    const copy = duplicatePlacedTool(source, 5)

    expect(copy.tool_id).toBe('tool-1')
    expect(copy.points).toEqual([{ x: 5, y: 5 }, { x: 15, y: 5 }, { x: 15, y: 15 }])
    expect(copy.finger_holes[0]).toMatchObject({ x: 10, y: 10, radius: 2 })
    expect(copy.interior_rings[0]).toEqual([{ x: 7, y: 7 }, { x: 9, y: 7 }, { x: 9, y: 9 }])
  })

  it('gives the copy fresh ids so it is an independent placement', () => {
    const source = placedTool()

    const first = duplicatePlacedTool(source, 5)
    const second = duplicatePlacedTool(source, 5)

    expect(first.id).not.toBe(source.id)
    expect(second.id).not.toBe(first.id)
    expect(first.finger_holes[0].id).not.toBe(source.finger_holes[0].id)
    expect(second.finger_holes[0].id).not.toBe(first.finger_holes[0].id)
  })

  it('deep-copies geometry so moving the copy leaves the original alone', () => {
    const source = placedTool()

    const copy = duplicatePlacedTool(source, 5)
    copy.points[0].x = 999
    copy.interior_rings[0][0].y = 999

    expect(source.points[0]).toEqual({ x: 0, y: 0 })
    expect(source.interior_rings[0][0]).toEqual({ x: 2, y: 2 })
  })

  it('handles tools stored without interior rings', () => {
    const source = { ...placedTool(), interior_rings: undefined as unknown as PlacedTool['interior_rings'] }

    expect(duplicatePlacedTool(source, 5).interior_rings).toEqual([])
  })
})
