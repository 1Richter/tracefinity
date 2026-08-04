import { GRID_MIN_UNITS, GRID_UNIT } from './constants'
import type { Point } from '@/types'

export interface Bounds {
  minX: number
  minY: number
  maxX: number
  maxY: number
}

/** Axis-aligned bounds over every point, or null when there is nothing to measure. */
export function pointBounds(polygons: Point[][]): Bounds | null {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (const points of polygons) {
    for (const p of points) {
      minX = Math.min(minX, p.x)
      minY = Math.min(minY, p.y)
      maxX = Math.max(maxX, p.x)
      maxY = Math.max(maxY, p.y)
    }
  }
  return minX === Infinity ? null : { minX, minY, maxX, maxY }
}

/**
 * Grid units needed to hold a tool span of `mm`, plus `margin` mm of wall and
 * clearance, rounded up to whole `snap` units. Deliberately not clamped: the
 * caller decides what to do when the answer is more than the backend accepts.
 */
export function gridUnitsForSpan(mm: number, margin: number, snap: number): number {
  const snapUnit = GRID_UNIT * snap
  return Math.max(GRID_MIN_UNITS, Math.ceil((mm + margin) / snapUnit) * snap)
}
