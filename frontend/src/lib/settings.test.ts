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
  let storage: Storage

  beforeEach(() => {
    storage = installLocalStorage()
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

    expect(resolvePreferredTracer(TRACERS, getLastTracer())).toBe('birefnet-lite')
  })

  it('falls back to the first tracer when the stored one is gone', () => {
    saveLastTracer('replicate')

    expect(resolvePreferredTracer(TRACERS, getLastTracer())).toBe('isnet')
  })

  it('falls back to the first tracer when nothing is stored', () => {
    expect(resolvePreferredTracer(TRACERS, null)).toBe('isnet')
  })

  it('returns null when no tracers are offered', () => {
    expect(resolvePreferredTracer([], 'isnet')).toBeNull()
  })

  it('keeps the previous tracer when an empty id is saved', () => {
    saveLastTracer('isnet')
    saveLastTracer('')

    expect(getLastTracer()).toBe('isnet')
  })

  it('survives a storage backend that refuses to write', () => {
    vi.spyOn(storage, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError')
    })

    expect(() => saveLastTracer('gemini')).not.toThrow()
    expect(getLastTracer()).toBeNull()
  })

  it('ignores a stored value of the wrong type', () => {
    storage.setItem('tracefinity-settings', JSON.stringify({ lastTracer: 42 }))

    expect(getLastTracer()).toBeNull()
  })
})
