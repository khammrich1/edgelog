import { describe, expect, it } from 'vitest'
import { toDateKey } from './date'

describe('toDateKey', () => {
  it('formats using local date parts, not UTC', () => {
    // Deliberately picking a local midnight instant that would roll back a
    // calendar day under toISOString() in any timezone behind UTC.
    const localMidnight = new Date(2026, 0, 5) // Jan 5, 2026, local time
    expect(toDateKey(localMidnight)).toBe('2026-01-05')
  })

  it('zero-pads single-digit month and day', () => {
    expect(toDateKey(new Date(2026, 2, 3))).toBe('2026-03-03')
  })
})
