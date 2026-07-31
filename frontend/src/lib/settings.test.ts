import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getLastTracer, resolvePreferredTracer, saveLastTracer } from './settings'

function installLocalStorage() {
  const data = new Map<string, string>()
  const storage = {
    get length() {
      return data.size
    },
    clear: () => data.clear(),
    getItem: (key: string) => data.get(key) ?? null,
    key: (index: number) => Array.from(data.keys())[index] ?? null,
    removeItem: (key: string) => data.delete(key),
    setItem: (key: string, value: string) => data.set(key, value),
  } as Storage

  vi.stubGlobal('window', { localStorage: storage })
  vi.stubGlobal('localStorage', storage)
  return storage
}

const TRACERS = [{ id: 'isnet' }, { id: 'birefnet-lite' }, { id: 'gemini' }]

describe('tracer persistence', () => {
  beforeEach(() => {
    installLocalStorage()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns null when nothing is stored', () => {
    expect(getLastTracer()).toBeNull()
  })

  it('round-trips the last chosen tracer', () => {
    saveLastTracer('birefnet-lite')

    expect(getLastTracer()).toBe('birefnet-lite')
  })

  it('preselects the stored tracer when it is still available', () => {
    saveLastTracer('birefnet-lite')

    expect(resolvePreferredTracer(TRACERS)).toBe('birefnet-lite')
  })

  it('falls back to the first tracer when the stored one is gone', () => {
    saveLastTracer('replicate')

    expect(resolvePreferredTracer(TRACERS)).toBe('isnet')
  })

  it('falls back to the first tracer when nothing is stored', () => {
    expect(resolvePreferredTracer(TRACERS)).toBe('isnet')
  })

  it('returns null when no tracers are offered', () => {
    expect(resolvePreferredTracer([])).toBeNull()
  })

  it('ignores an empty stored value', () => {
    saveLastTracer('')

    expect(getLastTracer()).toBeNull()
  })
})
