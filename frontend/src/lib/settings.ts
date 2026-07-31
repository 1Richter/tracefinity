import type { BinDefaults } from '@/types'

export interface UserSettings {
  bedSize: number
  binDefaults?: Partial<BinDefaults>
  /** Id of the tracer last used on the trace page, preselected on the next visit. */
  lastTracer?: string
}

export const BED_SIZE_MIN_MM = 150
export const BED_SIZE_MAX_MM = 500

const DEFAULTS: UserSettings = { bedSize: 256 }
const KEY = 'tracefinity-settings'

export function getSettings(): UserSettings {
  if (typeof window === 'undefined') return DEFAULTS
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return DEFAULTS
    return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch {
    return DEFAULTS
  }
}

/** Preferred tracer id, or null when nothing usable is stored. */
export function getLastTracer(): string | null {
  const stored = getSettings().lastTracer
  return typeof stored === 'string' && stored ? stored : null
}

export function saveLastTracer(tracerId: string): void {
  if (!tracerId) return
  saveSettings({ lastTracer: tracerId })
}

/** Pick the tracer to preselect: the stored one if still offered, else the first. */
export function resolvePreferredTracer(
  tracers: { id: string }[],
  stored: string | null = getLastTracer(),
): string | null {
  if (!tracers.length) return null
  if (stored && tracers.some(t => t.id === stored)) return stored
  return tracers[0].id
}

export function saveSettings(partial: Partial<UserSettings>): void {
  if (typeof window === 'undefined') return
  try {
    const current = getSettings()
    const next: Record<string, unknown> = { ...current, ...partial }
    for (const key of Object.keys(next)) {
      if (next[key] === undefined) delete next[key]
    }
    window.localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    // localStorage can be unavailable in private browsing or restricted contexts.
  }
}
