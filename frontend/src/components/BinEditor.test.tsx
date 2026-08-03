// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
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

describe('BinEditor cutout editing', () => {
  afterEach(cleanup)

  beforeEach(() => {
    // jsdom has no layout, so screenToMm would divide by a zero-sized rect
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({
      width: 1000, height: 1000, left: 0, top: 0, right: 1000, bottom: 1000,
      x: 0, y: 0, toJSON: () => ({}),
    } as DOMRect)
  })

  afterEach(() => vi.restoreAllMocks())

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

  const lastTools = (fn: ReturnType<typeof vi.fn>): PlacedTool[] =>
    fn.mock.calls[fn.mock.calls.length - 1][0]

  it('offers every cutout shape and toggles the mode off again', () => {
    render(<BinEditor {...baseProps} />)
    const button = screen.getByLabelText('Add Circle (sphere) cutout')

    expect(screen.getByLabelText('Add Rectangle cutout')).toBeTruthy()
    expect(screen.getByLabelText('Add Filleted rectangle cutout')).toBeTruthy()

    fireEvent.click(button)
    expect(button.className).toContain('text-accent')

    fireEvent.click(button)
    expect(button.className).not.toContain('text-accent')
  })

  it('adds a cutout to the tool that was clicked', () => {
    const { canvas, onPlacedToolsChange } = renderEditor()

    fireEvent.click(screen.getByLabelText('Add Cylinder (flat) cutout'))
    fireEvent.mouseDown(canvas.querySelector('path')!, { clientX: 283, clientY: 310 })

    const holes = lastTools(onPlacedToolsChange)[0].finger_holes
    expect(holes).toHaveLength(2)
    expect(holes[1].shape).toBe('cylinder')
    expect(holes[1].radius).toBe(10)
  })

  it('adds rectangles with both dimensions set', () => {
    const { canvas, onPlacedToolsChange } = renderEditor()

    fireEvent.click(screen.getByLabelText('Add Rectangle cutout'))
    fireEvent.mouseDown(canvas.querySelector('path')!, { clientX: 283, clientY: 310 })

    const added = lastTools(onPlacedToolsChange)[0].finger_holes[1]
    expect([added.shape, added.width, added.height]).toEqual(['rectangle', 30, 20])
  })

  it('marks a moved cutout as bin-local so sync cannot revert it', async () => {
    const { canvas, onPlacedToolsChange } = renderEditor()

    fireEvent.mouseDown(canvas.querySelector('circle')!, { clientX: 283, clientY: 310 })
    fireEvent.mouseMove(window, { clientX: 350, clientY: 310 })
    await new Promise(resolve => setTimeout(resolve, 30))

    const tool = lastTools(onPlacedToolsChange)[0]
    expect(tool.custom_hole_ids).toEqual(['h1'])
    expect(tool.finger_holes[0].x).toBeGreaterThan(25)
    expect(tool.finger_holes[0].y).toBeCloseTo(25)
  })

  it('resizes a selected cutout', async () => {
    const { canvas, onPlacedToolsChange } = renderEditor()

    fireEvent.mouseDown(canvas.querySelector('circle')!, { clientX: 283, clientY: 310 })
    fireEvent.mouseUp(window)
    fireEvent.mouseDown(screen.getByLabelText('Resize cutout'), { clientX: 283, clientY: 310 })
    fireEvent.mouseMove(window, { clientX: 400, clientY: 310 })
    await new Promise(resolve => setTimeout(resolve, 30))

    const tool = lastTools(onPlacedToolsChange)[0]
    expect(tool.finger_holes[0].radius).toBeGreaterThan(3)
    expect(tool.custom_hole_ids).toEqual(['h1'])
  })

  it('records a deleted cutout so it stays deleted for this placement', () => {
    const { canvas, onPlacedToolsChange } = renderEditor()

    fireEvent.mouseDown(canvas.querySelector('circle')!, { clientX: 283, clientY: 310 })
    fireEvent.click(screen.getByLabelText('Delete cutout'))

    const tool = lastTools(onPlacedToolsChange)[0]
    expect(tool.finger_holes).toEqual([])
    expect(tool.removed_hole_ids).toEqual(['h1'])
  })

  it('deletes the selected cutout with the Delete key', () => {
    const { canvas, onPlacedToolsChange } = renderEditor()

    fireEvent.mouseDown(canvas.querySelector('circle')!, { clientX: 283, clientY: 310 })
    fireEvent.keyDown(window, { key: 'Delete' })

    expect(lastTools(onPlacedToolsChange)[0].finger_holes).toEqual([])
  })

  it('leaves cutout placement mode on Escape', () => {
    render(<BinEditor {...baseProps} />)

    fireEvent.click(screen.getByLabelText('Add Square cutout'))
    fireEvent.keyDown(window, { key: 'Escape' })

    expect(screen.getByLabelText('Add Square cutout').className).not.toContain('text-accent')
  })
})
