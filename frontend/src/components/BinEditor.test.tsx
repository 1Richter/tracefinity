// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { BinEditor } from './BinEditor'
import { SNAP_GRID } from '@/lib/constants'

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
