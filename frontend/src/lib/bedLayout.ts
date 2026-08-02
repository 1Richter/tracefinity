export interface PartSize {
  w: number
  d: number
}

export interface PartOffset {
  x: number
  y: number
}

/**
 * Place split parts where the backend actually cut them.
 *
 * `split_bin` writes a `cols` x `rows` field column-major -- all rows of the
 * lowest x column first, each axis counted from its low end -- so part `i`
 * sits at column `floor(i / rows)`, row `i % rows`. Returns the in-plane
 * translation for each part, centred on the origin, with `gap` mm between
 * neighbours so the cuts stay visible.
 *
 * Packing by size instead would be misleading: the backend makes every slab as
 * large as the bed allows, so no two parts ever fit side by side on it and any
 * size-driven packing degenerates into one part per row.
 *
 * When there is no regular field (`split_cols`/`split_rows` are 0, or they
 * disagree with the number of parts, which separated partial-bin islands do)
 * the parts fall back to a single row.
 */
export function layOutCutField(
  sizes: PartSize[],
  cols: number,
  rows: number,
  gap: number,
): PartOffset[] {
  const isField = cols > 0 && rows > 0 && cols * rows === sizes.length
  const nCols = isField ? cols : sizes.length
  const nRows = isField ? rows : 1

  const colWidths: number[] = new Array(nCols).fill(0)
  const rowDepths: number[] = new Array(nRows).fill(0)
  for (let i = 0; i < sizes.length; i++) {
    const col = Math.floor(i / nRows)
    const row = i % nRows
    colWidths[col] = Math.max(colWidths[col], sizes[i].w)
    rowDepths[row] = Math.max(rowDepths[row], sizes[i].d)
  }

  /** centre of each span, laid end to end and centred on the origin */
  const centresOf = (spans: number[]) => {
    const total = spans.reduce((sum, s) => sum + s, 0) + gap * Math.max(0, spans.length - 1)
    const centres: number[] = []
    let edge = -total / 2
    for (const span of spans) {
      centres.push(edge + span / 2)
      edge += span + gap
    }
    return centres
  }

  const colCentres = centresOf(colWidths)
  const rowCentres = centresOf(rowDepths)

  return sizes.map((_, i) => ({
    x: colCentres[Math.floor(i / nRows)],
    y: rowCentres[i % nRows],
  }))
}
