import type { BinProject, BinProjectSummary, BinSummary, ProjectStatus, ToolSummary } from '@/types'

export const projectStatusLabels: Record<ProjectStatus, string> = {
  active: 'Active',
  ready_to_print: 'Ready to print',
  printed: 'Printed',
  archived: 'Archived',
}

export function binLabel(bin: BinSummary) {
  return bin.name || `Bin ${bin.id.slice(0, 8)}`
}

export function toolProjectLabel(
  projectIds: string[],
  projectNameById: Map<string, string>,
) {
  if (projectIds.length === 0) return null
  if (projectIds.length > 1) return `${projectIds.length} Projects`
  return projectNameById.get(projectIds[0]) || 'Project'
}

export function toolProjectTitle(
  projectIds: string[],
  projectNameById: Map<string, string>,
) {
  if (projectIds.length === 0) return undefined
  return projectIds.map(projectId => projectNameById.get(projectId) || 'Project').join(', ')
}

export function projectNameMap(projects: BinProjectSummary[]) {
  return new Map(projects.map(project => [project.id, project.name]))
}

/**
 * Whether the dashboard treats a bin as owned by a project.
 *
 * Only `bin.project_id` is available here: the dashboard lists projects as
 * summaries, which carry no `bin_ids`, so the reverse link that
 * getProjectCollections also honours cannot be checked. A bin linked only from
 * the project side counts as unowned and stays visible, which is the safe
 * direction -- the project health check reports it as `bin_missing_project_id`
 * and the repair action writes the missing `project_id` back.
 */
export function isProjectOwnedBin(bin: BinSummary) {
  return Boolean(bin.project_id)
}

/**
 * Label for the project badge on a bin card. Never null for a bin that
 * isProjectOwnedBin hides, so a hidden bin always explains itself once shown.
 */
export function binProjectLabel(bin: BinSummary, projectNameById: Map<string, string>) {
  if (!bin.project_id) return null
  return projectNameById.get(bin.project_id) || 'Project'
}

export type ProjectToolFilter = 'all' | 'unplaced' | 'placed'

export const MIN_TOOL_QUANTITY = 1
export const MAX_TOOL_QUANTITY = 99

/** planned copies of a tool; tools absent from the map count as one */
export function toolQuantity(project: BinProject | null, toolId: string) {
  return project?.tool_quantities?.[toolId] ?? MIN_TOOL_QUANTITY
}

/** copies of a tool already sitting in one of the project's linked bins */
export function toolPlacedCount(project: BinProject | null, toolId: string) {
  return project?.placed_counts?.[toolId] ?? 0
}

export function clampToolQuantity(quantity: number) {
  if (!Number.isFinite(quantity)) return MIN_TOOL_QUANTITY
  return Math.min(MAX_TOOL_QUANTITY, Math.max(MIN_TOOL_QUANTITY, Math.round(quantity)))
}

/** "2/3 placed" — capped so extra copies in bins never overshoot the plan */
export function toolPlacementLabel(project: BinProject | null, toolId: string) {
  const quantity = toolQuantity(project, toolId)
  const placed = Math.min(toolPlacedCount(project, toolId), quantity)
  return `${placed}/${quantity} placed`
}

/** repeat each selected tool id once per planned copy, for bin creation */
export function expandToolIdsByQuantity(project: BinProject | null, toolIds: string[]) {
  return toolIds.flatMap(toolId => Array<string>(toolQuantity(project, toolId)).fill(toolId))
}

export function getUniqueBinTools(
  bin: BinSummary,
  toolById: Map<string, ToolSummary>,
) {
  return Array.from(new Set(bin.tool_ids || []))
    .map(toolId => toolById.get(toolId))
    .filter(Boolean) as ToolSummary[]
}

export function getProjectCollections(
  project: BinProject | null,
  tools: ToolSummary[],
  bins: BinSummary[],
  options: {
    projectSearch: string
    addToolSearch: string
    statusFilter: ProjectToolFilter
    allowReassignBins: boolean
  },
) {
  const projectToolIds = new Set(project?.tool_ids || [])
  const placedToolIds = new Set(project?.placed_tool_ids || [])
  const unplacedToolIds = new Set(project?.unplaced_tool_ids || [])
  const projectTools = tools.filter(tool => projectToolIds.has(tool.id))
  const projectBins = project
    ? bins.filter(bin => bin.project_id === project.id || project.bin_ids.includes(bin.id))
    : []
  const projectBinIds = new Set(projectBins.map(bin => bin.id))
  const toolById = new Map(tools.map(tool => [tool.id, tool]))

  let filteredProjectTools = projectTools
  if (options.statusFilter === 'unplaced') {
    filteredProjectTools = filteredProjectTools.filter(tool => unplacedToolIds.has(tool.id))
  }
  if (options.statusFilter === 'placed') {
    filteredProjectTools = filteredProjectTools.filter(tool => placedToolIds.has(tool.id))
  }
  if (options.projectSearch.trim()) {
    const q = options.projectSearch.toLowerCase()
    filteredProjectTools = filteredProjectTools.filter(tool => tool.name.toLowerCase().includes(q))
  }

  const toolBins = new Map<string, BinSummary[]>()
  for (const bin of projectBins) {
    for (const toolId of new Set(bin.tool_ids || [])) {
      const current = toolBins.get(toolId) || []
      current.push(bin)
      toolBins.set(toolId, current)
    }
  }

  const existingBinOptions = bins.filter(bin => (
    !projectBinIds.has(bin.id) && (options.allowReassignBins || !bin.project_id)
  ))

  let availableTools = tools.filter(tool => !projectToolIds.has(tool.id))
  if (options.addToolSearch.trim()) {
    const q = options.addToolSearch.toLowerCase()
    availableTools = availableTools.filter(tool => tool.name.toLowerCase().includes(q))
  }

  const actionableVisibleToolIds = project
    ? filteredProjectTools
      .filter(tool => !placedToolIds.has(tool.id))
      .map(tool => tool.id)
    : []

  return {
    projectToolIds,
    placedToolIds,
    unplacedToolIds,
    projectTools,
    filteredProjectTools,
    projectBins,
    projectBinIds,
    toolById,
    toolBins,
    existingBinOptions,
    availableTools,
    actionableVisibleToolIds,
  }
}
