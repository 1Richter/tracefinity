export interface PartSize {
  w: number
  d: number
}

export interface PartOffset {
  x: number
  y: number
}

/** Lay split parts out in rows that stay inside the print bed, mirroring how
 *  they get arranged on the printer instead of a single endless row.
 *  Returns the in-plane translation for each part, centred on the origin.
 *  Parts wider than the bed get a row of their own. */
export function layOutOnBed(sizes: PartSize[], bedSize: number, gap: number): PartOffset[] {
  const rows: { indices: number[]; width: number; depth: number }[] = []
  for (let i = 0; i < sizes.length; i++) {
    const { w, d } = sizes[i]
    const row = rows[rows.length - 1]
    if (row && row.width + gap + w <= bedSize) {
      row.indices.push(i)
      row.width += gap + w
      row.depth = Math.max(row.depth, d)
    } else {
      rows.push({ indices: [i], width: w, depth: d })
    }
  }

  const totalDepth = rows.reduce((sum, r) => sum + r.depth, 0) + gap * Math.max(0, rows.length - 1)
  const offsets: PartOffset[] = new Array(sizes.length)
  let y = totalDepth / 2
  for (const row of rows) {
    let x = -row.width / 2
    const centreY = y - row.depth / 2
    for (const i of row.indices) {
      offsets[i] = { x: x + sizes[i].w / 2, y: centreY }
      x += sizes[i].w + gap
    }
    y -= row.depth + gap
  }
  return offsets
}
