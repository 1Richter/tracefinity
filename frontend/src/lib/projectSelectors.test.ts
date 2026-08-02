import { describe, expect, it } from 'vitest'

import { binProjectLabel, getProjectCollections, getUniqueBinTools, isProjectOwnedBin } from './projectSelectors'
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
  preview_tools: [],
})

const project: BinProject = {
  id: 'project-1',
  name: 'Project 1',
  description: null,
  status: 'active',
  tool_ids: ['tool-1', 'tool-2'],
  bin_ids: ['bin-1'],
  placed_tool_ids: ['tool-1'],
  unplaced_tool_ids: ['tool-2'],
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

describe('dashboard bin ownership', () => {
  const names = new Map([['project-1', 'Workbench']])

  it('treats a bin with a project id as owned', () => {
    expect(isProjectOwnedBin(bin([]))).toBe(true)
    expect(isProjectOwnedBin({ ...bin([]), project_id: null })).toBe(false)
  })

  it('labels an owned bin with its project name', () => {
    expect(binProjectLabel(bin([]), names)).toBe('Workbench')
  })

  it('never hides a bin without a badge to explain it', () => {
    // a bin whose project is missing from the dashboard list is still hidden,
    // so it has to carry a fallback label once the user reveals it
    const orphan = { ...bin([]), project_id: 'project-gone' }

    expect(isProjectOwnedBin(orphan)).toBe(true)
    expect(binProjectLabel(orphan, names)).toBe('Project')
  })

  it('gives an unowned bin no label', () => {
    expect(binProjectLabel({ ...bin([]), project_id: null }, names)).toBeNull()
  })
})
