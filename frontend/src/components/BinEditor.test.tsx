// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { BinEditor } from './BinEditor'
import { SNAP_GRID } from '@/lib/constants'
import type { PlacedTool } from '@/types'

const baseProps = {
  placedTools: [],
  onPlacedToolsChange: () => {},
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

describe('BinEditor cutout depth cap', () => {
  afterEach(cleanup)

  const placedTool = (): PlacedTool => ({
    id: 'pt-1',
    tool_id: 'tool-1',
    name: 'hammer',
    points: [{ x: 10, y: 10 }, { x: 40, y: 10 }, { x: 40, y: 40 }, { x: 10, y: 40 }],
    finger_holes: [{ id: 'h1', x: 25, y: 25, radius: 3, shape: 'circle', rotation: 0 }],
    interior_rings: [],
    rotation: 0,
  })

  function renderEditor() {
    const onPlacedToolsChange = vi.fn()
    const view = render(
      <BinEditor {...baseProps} placedTools={[placedTool()]} onPlacedToolsChange={onPlacedToolsChange} />
    )
    const canvas = view.container.querySelector('[data-testid="bin-canvas"]')!
    return { ...view, canvas, onPlacedToolsChange }
  }

  it('shows the maximum depth next to a tool depth override', () => {
    const { canvas } = renderEditor()

    fireEvent.mouseDown(canvas.querySelector('path')!)

    expect(screen.getByTestId('max-depth-hint').textContent).toBe(`max ${baseProps.maxCutoutDepth.toFixed(1)}`)
  })

  it('clamps a too-deep cutout override and flags it', () => {
    const { canvas, onPlacedToolsChange } = renderEditor()

    fireEvent.mouseDown(canvas.querySelector('circle')!)
    const input = screen.getByPlaceholderText(baseProps.defaultCutoutDepth.toFixed(1))
    fireEvent.change(input, { target: { value: '999' } })
    fireEvent.blur(input)

    const tool = onPlacedToolsChange.mock.calls.at(-1)![0][0] as PlacedTool
    expect(tool.finger_holes[0].depth_override).toBe(baseProps.maxCutoutDepth)
    expect(screen.getByTestId('max-depth-hint').className).toContain('text-amber-400')
  })

  it('raises a too-shallow depth without flagging the cap', () => {
    const { canvas, onPlacedToolsChange } = renderEditor()

    fireEvent.mouseDown(canvas.querySelector('circle')!)
    const input = screen.getByPlaceholderText(baseProps.defaultCutoutDepth.toFixed(1))
    fireEvent.change(input, { target: { value: '1' } })
    fireEvent.blur(input)

    const tool = onPlacedToolsChange.mock.calls.at(-1)![0][0] as PlacedTool
    expect(tool.finger_holes[0].depth_override).toBe(5)
    expect(screen.getByTestId('max-depth-hint').className).toContain('text-text-muted')
  })

  it('keeps a depth within the cap unflagged', () => {
    const { canvas, onPlacedToolsChange } = renderEditor()

    fireEvent.mouseDown(canvas.querySelector('circle')!)
    const input = screen.getByPlaceholderText(baseProps.defaultCutoutDepth.toFixed(1))
    fireEvent.change(input, { target: { value: '12' } })
    fireEvent.blur(input)

    const tool = onPlacedToolsChange.mock.calls.at(-1)![0][0] as PlacedTool
    expect(tool.finger_holes[0].depth_override).toBe(12)
    expect(screen.getByTestId('max-depth-hint').className).toContain('text-text-muted')
  })
})
