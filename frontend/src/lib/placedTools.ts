import type { PlacedTool } from '@/types'

let duplicateCounter = 0

/**
 * Independent copy of a placed tool, offset so it does not hide under the
 * original. Geometry is deep-copied -- the copy shares the same `tool_id` but
 * moving or rotating it must never touch the tool it came from.
 */
export function duplicatePlacedTool(tool: PlacedTool, offset: number): PlacedTool {
  duplicateCounter += 1
  return {
    ...tool,
    id: `pt-${Date.now()}-${duplicateCounter}`,
    points: tool.points.map(p => ({ x: p.x + offset, y: p.y + offset })),
    finger_holes: tool.finger_holes.map((fh, index) => ({
      ...fh,
      id: `fh-${Date.now()}-${duplicateCounter}-${index}`,
      x: fh.x + offset,
      y: fh.y + offset,
    })),
    interior_rings: (tool.interior_rings ?? []).map(ring =>
      ring.map(p => ({ x: p.x + offset, y: p.y + offset }))
    ),
  }
}
