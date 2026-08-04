import { describe, expect, it } from 'vitest'

import {
  clampToolQuantity,
  expandToolIdsByQuantity,
  getProjectCollections,
  getUniqueBinTools,
  toolPlacementLabel,
  toolQuantity,
  MAX_TOOL_QUANTITY,
} from './projectSelectors'
import type { BinProject, BinSummary, ToolSummary } from '@/types'

const tool = (id: string): ToolSummary => ({
  id,
  name: id,
  created_at: null,
  point_count: 0,
  points: [],
  interior_rings: [],
  smoothed: false,
  smooth_level: 0,
  thumbnail_url: null,
  image_transform: null,
  image_context: null,
  category: null,
  drawer: null,
  tags: [],
  project_ids: [],
  review_status: null,
  needs_cleanup: false,
})

const bin = (toolIds: string[]): BinSummary => ({
  id: 'bin-1',
  name: 'Bin 1',
  project_id: 'project-1',
  created_at: null,
  tool_ids: toolIds,
  tool_count: toolIds.length,
  has_stl: false,
  grid_x: 2,
  grid_y: 2,
  size_mode: 'units',
  custom_width_mm: null,
  custom_depth_mm: null,
  preview_tools: [],
})

const project: BinProject = {
  id: 'project-1',
  name: 'Project 1',
  description: null,
  status: 'active',
  tool_ids: ['tool-1', 'tool-2'],
  bin_ids: ['bin-1'],
  tool_quantities: {},
  placed_tool_ids: ['tool-1'],
  unplaced_tool_ids: ['tool-2'],
  placed_counts: { 'tool-1': 1 },
  target_grid_x: null,
  target_grid_y: null,
  default_bin_config: null,
  notes: null,
  created_at: null,
  updated_at: null,
}

describe('project selectors', () => {
  it('deduplicates repeated tool placements for linked-bin display', () => {
    const toolById = new Map([tool('tool-1'), tool('tool-2')].map(item => [item.id, item]))

    expect(getUniqueBinTools(bin(['tool-1', 'tool-1', 'tool-2']), toolById).map(item => item.id))
      .toEqual(['tool-1', 'tool-2'])
  })

  it('counts a bin once per tool when building project tool metadata', () => {
    const toolOne = tool('tool-1')
    const collections = getProjectCollections(project, [toolOne, tool('tool-2')], [bin(['tool-1', 'tool-1'])], {
      projectSearch: '',
      addToolSearch: '',
      statusFilter: 'all',
      allowReassignBins: false,
    })

    expect(collections.toolBins.get(toolOne.id)?.map(item => item.id)).toEqual(['bin-1'])
  })
})

describe('tool quantities', () => {
  const withQuantities = (
    quantities: Record<string, number>,
    placedCounts: Record<string, number> = {},
  ): BinProject => ({
    ...project,
    tool_quantities: quantities,
    placed_counts: placedCounts,
  })

  it('treats tools missing from the quantity map as a single copy', () => {
    expect(toolQuantity(withQuantities({ 'tool-2': 3 }), 'tool-1')).toBe(1)
    expect(toolQuantity(withQuantities({ 'tool-2': 3 }), 'tool-2')).toBe(3)
    expect(toolQuantity(null, 'tool-1')).toBe(1)
  })

  it('repeats each tool id once per planned copy', () => {
    expect(expandToolIdsByQuantity(withQuantities({ 'tool-1': 3 }), ['tool-1', 'tool-2']))
      .toEqual(['tool-1', 'tool-1', 'tool-1', 'tool-2'])
  })

  it('leaves the selection untouched when no tool has extra copies', () => {
    expect(expandToolIdsByQuantity(withQuantities({}), ['tool-1', 'tool-2']))
      .toEqual(['tool-1', 'tool-2'])
  })

  it('reports progress against the planned copies', () => {
    const target = withQuantities({ 'tool-1': 3 }, { 'tool-1': 2 })

    expect(toolPlacementLabel(target, 'tool-1')).toBe('2/3 placed')
    expect(toolPlacementLabel(target, 'tool-2')).toBe('0/1 placed')
  })

  it('caps the placed count so extra copies in bins never overshoot', () => {
    expect(toolPlacementLabel(withQuantities({}, { 'tool-1': 4 }), 'tool-1')).toBe('1/1 placed')
  })

  it('clamps quantities to the allowed range', () => {
    expect(clampToolQuantity(0)).toBe(1)
    expect(clampToolQuantity(-5)).toBe(1)
    expect(clampToolQuantity(MAX_TOOL_QUANTITY + 1)).toBe(MAX_TOOL_QUANTITY)
    expect(clampToolQuantity(2.4)).toBe(2)
    expect(clampToolQuantity(Number.NaN)).toBe(1)
  })
})
