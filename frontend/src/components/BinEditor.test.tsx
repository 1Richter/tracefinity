// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { BinEditor } from './BinEditor'
import { DUPLICATE_OFFSET, SNAP_GRID } from '@/lib/constants'
import type { PlacedTool } from '@/types'

const baseProps = {
  placedTools: [] as PlacedTool[],
  onPlacedToolsChange: (_tools: PlacedTool[]) => {},
  textLabels: [],
  onTextLabelsChange: () => {},
  gridX: 2,
  gridY: 2,
  partialBins: false,
  partialBinsValues: [false, false],
  wallThickness: 1.6,
  defaultCutoutDepth: 10,
  maxCutoutDepth: 20,
}

describe('BinEditor snap to grid', () => {
  afterEach(cleanup)

  it('defaults to off', () => {
    render(<BinEditor {...baseProps} />)

    expect(screen.getByTitle(`Snap to ${SNAP_GRID}mm grid (off)`)).toBeTruthy()
  })

  it('can be toggled on', () => {
    render(<BinEditor {...baseProps} />)

    fireEvent.click(screen.getByTitle(`Snap to ${SNAP_GRID}mm grid (off)`))

    expect(screen.getByTitle(`Snap to ${SNAP_GRID}mm grid (on)`)).toBeTruthy()
  })
})

const placedTool: PlacedTool = {
  id: 'pt-1',
  tool_id: 'tool-1',
  name: 'Wrench',
  points: [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }],
  finger_holes: [],
  interior_rings: [],
  rotation: 0,
}

function renderWithSelectedTool(onPlacedToolsChange: (tools: PlacedTool[]) => void) {
  const { container } = render(
    <BinEditor {...baseProps} placedTools={[placedTool]} onPlacedToolsChange={onPlacedToolsChange} />
  )
  const toolPath = container.querySelector('path[fill-rule="evenodd"]')
  if (!toolPath) throw new Error('tool outline not rendered')
  fireEvent.mouseDown(toolPath)
  fireEvent.mouseUp(window)
  return container
}

describe('BinEditor duplicate placed tool', () => {
  afterEach(cleanup)

  it('duplicates the selection from the toolbar button', () => {
    const onPlacedToolsChange = vi.fn()
    renderWithSelectedTool(onPlacedToolsChange)

    fireEvent.click(screen.getByLabelText('Duplicate'))

    expect(onPlacedToolsChange).toHaveBeenCalledTimes(1)
    const [original, copy] = onPlacedToolsChange.mock.calls[0][0]
    expect(original).toBe(placedTool)
    expect(copy.tool_id).toBe('tool-1')
    expect(copy.id).not.toBe(placedTool.id)
    expect(copy.points[0]).toEqual({ x: DUPLICATE_OFFSET, y: DUPLICATE_OFFSET })
  })

  it('duplicates the selection with Ctrl+C then Ctrl+V', () => {
    const onPlacedToolsChange = vi.fn()
    renderWithSelectedTool(onPlacedToolsChange)

    fireEvent.keyDown(window, { key: 'c', ctrlKey: true })
    fireEvent.keyDown(window, { key: 'v', ctrlKey: true })

    expect(onPlacedToolsChange).toHaveBeenCalledTimes(1)
    const [, copy] = onPlacedToolsChange.mock.calls[0][0]
    expect(copy.tool_id).toBe('tool-1')
    expect(copy.points[0]).toEqual({ x: DUPLICATE_OFFSET, y: DUPLICATE_OFFSET })
  })

  it('pastes nothing until something has been copied', () => {
    const onPlacedToolsChange = vi.fn()
    renderWithSelectedTool(onPlacedToolsChange)

    fireEvent.keyDown(window, { key: 'v', ctrlKey: true })

    expect(onPlacedToolsChange).not.toHaveBeenCalled()
  })

  it('cascades repeated pastes instead of stacking them at one offset', () => {
    const onPlacedToolsChange = vi.fn()
    renderWithSelectedTool(onPlacedToolsChange)

    fireEvent.keyDown(window, { key: 'c', ctrlKey: true })
    fireEvent.keyDown(window, { key: 'v', ctrlKey: true })
    fireEvent.keyDown(window, { key: 'v', ctrlKey: true })

    expect(onPlacedToolsChange).toHaveBeenCalledTimes(2)
    const [, firstCopy] = onPlacedToolsChange.mock.calls[0][0]
    const [, secondCopy] = onPlacedToolsChange.mock.calls[1][0]
    expect(firstCopy.points[0]).toEqual({ x: DUPLICATE_OFFSET, y: DUPLICATE_OFFSET })
    expect(secondCopy.points[0]).toEqual({ x: DUPLICATE_OFFSET * 2, y: DUPLICATE_OFFSET * 2 })
  })

  it('leaves copy and paste to the browser while typing in an input', () => {
    const onPlacedToolsChange = vi.fn()
    renderWithSelectedTool(onPlacedToolsChange)
    const input = document.createElement('input')
    document.body.appendChild(input)

    fireEvent.keyDown(input, { key: 'c', ctrlKey: true })
    fireEvent.keyDown(input, { key: 'v', ctrlKey: true })

    expect(onPlacedToolsChange).not.toHaveBeenCalled()
  })

  it('offers no duplicate button without a selection', () => {
    render(<BinEditor {...baseProps} placedTools={[placedTool]} />)

    expect(screen.queryByLabelText('Duplicate')).toBeNull()
  })
})
