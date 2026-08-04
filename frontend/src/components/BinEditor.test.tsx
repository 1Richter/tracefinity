// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
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

describe('BinEditor partial bins on a fractional grid', () => {
  afterEach(cleanup)

  it('draws one marker per disabled whole cell', () => {
    // 2.5 x 1.5 units => a 3x2 cell mask, of which two cells are disabled
    const { container } = render(
      <BinEditor
        {...baseProps}
        gridX={2.5}
        gridY={1.5}
        partialBins
        partialBinsValues={[true, true, false, true, false, true]}
      />
    )

    const canvas = container.querySelector('[data-testid="bin-canvas"]')!
    const markers = [...canvas.querySelectorAll('rect')].filter(
      r => r.getAttribute('fill') === 'rgba(239, 68, 68, 0.22)'
    )
    expect(markers).toHaveLength(2)
  })

  it('clips a trailing partial cell to the bin edge', () => {
    const { container } = render(
      <BinEditor {...baseProps} gridX={2.5} gridY={1} partialBins partialBinsValues={[true, true, false]} />
    )

    const canvas = container.querySelector('[data-testid="bin-canvas"]')!
    const marker = [...canvas.querySelectorAll('rect')].find(
      r => r.getAttribute('fill') === 'rgba(239, 68, 68, 0.22)'
    )!
    // half a unit wide, not a full 42mm cell hanging over the edge
    expect(Number(marker.getAttribute('width'))).toBeCloseTo(21 * 8)
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

describe('BinEditor cutout depth cap', () => {
  afterEach(cleanup)

  const toolWithCutout = (): PlacedTool => ({
    ...placedTool,
    points: [{ x: 10, y: 10 }, { x: 40, y: 10 }, { x: 40, y: 40 }, { x: 10, y: 40 }],
    finger_holes: [{ id: 'h1', x: 25, y: 25, radius: 3, shape: 'circle', rotation: 0 }],
  })

  function renderCapEditor() {
    const onPlacedToolsChange = vi.fn()
    const view = render(
      <BinEditor {...baseProps} placedTools={[toolWithCutout()]} onPlacedToolsChange={onPlacedToolsChange} />
    )
    const canvas = view.container.querySelector('[data-testid="bin-canvas"]')!
    return { canvas, onPlacedToolsChange }
  }

  const depthInput = () => screen.getByPlaceholderText(baseProps.defaultCutoutDepth.toFixed(1))

  it('shows the maximum depth next to a tool depth override', () => {
    const { canvas } = renderCapEditor()

    fireEvent.mouseDown(canvas.querySelector('path')!)

    expect(screen.getByTestId('max-depth-hint').textContent).toBe(`max ${baseProps.maxCutoutDepth.toFixed(1)}`)
  })

  it('clamps a too-deep cutout override and flags it', () => {
    const { canvas, onPlacedToolsChange } = renderCapEditor()

    fireEvent.mouseDown(canvas.querySelector('circle')!)
    fireEvent.change(depthInput(), { target: { value: '999' } })
    fireEvent.blur(depthInput())

    const tool = onPlacedToolsChange.mock.calls.at(-1)![0][0] as PlacedTool
    expect(tool.finger_holes[0].depth_override).toBe(baseProps.maxCutoutDepth)
    expect(screen.getByTestId('max-depth-hint').className).toContain('text-amber-400')
  })

  it('raises a too-shallow depth without flagging the cap', () => {
    const { canvas, onPlacedToolsChange } = renderCapEditor()

    fireEvent.mouseDown(canvas.querySelector('circle')!)
    fireEvent.change(depthInput(), { target: { value: '1' } })
    fireEvent.blur(depthInput())

    const tool = onPlacedToolsChange.mock.calls.at(-1)![0][0] as PlacedTool
    expect(tool.finger_holes[0].depth_override).toBe(5)
    expect(screen.getByTestId('max-depth-hint').className).toContain('text-text-muted')
  })

  it('keeps a depth within the cap unflagged', () => {
    const { canvas, onPlacedToolsChange } = renderCapEditor()

    fireEvent.mouseDown(canvas.querySelector('circle')!)
    fireEvent.change(depthInput(), { target: { value: '12' } })
    fireEvent.blur(depthInput())

    const tool = onPlacedToolsChange.mock.calls.at(-1)![0][0] as PlacedTool
    expect(tool.finger_holes[0].depth_override).toBe(12)
    expect(screen.getByTestId('max-depth-hint').className).toContain('text-text-muted')
  })
})
