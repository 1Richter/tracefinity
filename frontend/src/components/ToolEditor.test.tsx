// @vitest-environment jsdom
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { ToolEditor } from './ToolEditor'
import type { FingerHole } from '@/types'

const points = [
  { x: 0, y: 0 },
  { x: 20, y: 0 },
  { x: 20, y: 20 },
  { x: 0, y: 20 },
]

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockReturnValue({ matches: false }),
  })
})

function renderEditor(outputSmoothed = true) {
  const onSmoothedChange = vi.fn()
  const result = render(
    <ToolEditor
      points={points}
      fingerHoles={[]}
      smoothed={outputSmoothed}
      smoothLevel={0.5}
      onPointsChange={() => {}}
      onFingerHolesChange={() => {}}
      onSmoothedChange={onSmoothedChange}
      onSmoothLevelChange={() => {}}
    />
  )
  return { ...result, onSmoothedChange }
}

describe('ToolEditor outline view', () => {
  afterEach(cleanup)

  it('opens in the accurate editable view without changing the smooth output preference', () => {
    const { container, onSmoothedChange } = renderEditor(true)

    expect(screen.getByRole('button', { name: 'Accurate' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: 'Output: Smooth' }).getAttribute('aria-pressed')).toBe('true')
    expect(container.querySelectorAll('circle.cursor-move')).toHaveLength(points.length)
    expect(onSmoothedChange).not.toHaveBeenCalled()
  })

  it('previews smoothing independently from the saved output preference', () => {
    const { container, onSmoothedChange } = renderEditor(false)

    fireEvent.click(screen.getByRole('button', { name: 'Smooth' }))

    expect(screen.getByRole('button', { name: 'Smooth' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: 'Output: Accurate' }).getAttribute('aria-pressed')).toBe('false')
    expect(container.querySelectorAll('circle.cursor-move')).toHaveLength(0)
    expect(onSmoothedChange).not.toHaveBeenCalled()
  })

  it('changes the saved output preference only through the output control', () => {
    const { onSmoothedChange } = renderEditor(true)

    fireEvent.click(screen.getByRole('button', { name: 'Output: Smooth' }))

    expect(onSmoothedChange).toHaveBeenCalledWith(false)
  })
})

describe('ToolEditor cutout line', () => {
  afterEach(cleanup)

  function renderWithHoles(fingerHoles: FingerHole[] = []) {
    // jsdom has no layout, so screenToMm would divide by a zero-sized rect
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({
      width: 1000, height: 1000, left: 0, top: 0, right: 1000, bottom: 1000,
      x: 0, y: 0, toJSON: () => ({}),
    } as DOMRect)
    const onFingerHolesChange = vi.fn()
    const result = render(
      <ToolEditor
        points={points}
        fingerHoles={fingerHoles}
        smoothed={false}
        smoothLevel={0.5}
        onPointsChange={() => {}}
        onFingerHolesChange={onFingerHolesChange}
        onSmoothedChange={() => {}}
        onSmoothLevelChange={() => {}}
      />
    )
    return { ...result, onFingerHolesChange }
  }

  afterEach(() => vi.restoreAllMocks())

  const line = (overrides: Partial<FingerHole> = {}): FingerHole => ({
    id: 'l1', x: 10, y: 10, radius: 30, width: 60, height: 8, rotation: 0, shape: 'line', ...overrides,
  })

  it('adds a line with a length and a trench width', () => {
    const { container, onFingerHolesChange } = renderWithHoles()

    fireEvent.click(screen.getByText('Cutout').closest('button')!)
    fireEvent.click(screen.getByText('Cutout line').closest('button')!)
    fireEvent.click(container.querySelector('svg')!, { clientX: 300, clientY: 300 })

    const added = onFingerHolesChange.mock.calls.at(-1)![0][0] as FingerHole
    expect(added.shape).toBe('line')
    expect([added.width, added.height]).toEqual([60, 8])
  })

  it('renders a line as a stadium, not a plain rectangle', () => {
    const { container } = renderWithHoles([line()])

    const stadium = [...container.querySelectorAll('rect')].find(r => r.getAttribute('rx'))
    expect(stadium).toBeTruthy()
    // rx is half the trench width in display units, so the ends are round
    expect(Number(stadium!.getAttribute('rx'))).toBeCloseTo(Number(stadium!.getAttribute('height')) / 2)
  })

  it('edits length, width and rotation numerically', () => {
    const { container, onFingerHolesChange } = renderWithHoles([line()])

    const stadium = [...container.querySelectorAll('rect')].find(r => r.getAttribute('rx'))!
    fireEvent.mouseDown(stadium)

    const lengthInput = screen.getByDisplayValue('60')
    fireEvent.change(lengthInput, { target: { value: '180' } })
    fireEvent.blur(lengthInput)

    const updated = onFingerHolesChange.mock.calls.at(-1)![0][0] as FingerHole
    expect(updated.width).toBe(180)
    // radius tracks the largest dimension so hit-testing keeps up
    expect(updated.radius).toBe(90)
  })
})
