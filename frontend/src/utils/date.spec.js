import { describe, expect, it } from 'vitest'
import {
  addDaysToDateKey,
  eachDateKeyInRange,
  formatWeekRange,
  parseDateKey,
  startOfWeekDateKey,
  toDateKey
} from './date'

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

describe('parseDateKey', () => {
  it('parses as local midnight, not UTC', () => {
    const date = parseDateKey('2026-01-05')
    expect(date.getFullYear()).toBe(2026)
    expect(date.getMonth()).toBe(0)
    expect(date.getDate()).toBe(5)
    expect(date.getHours()).toBe(0)
  })
})

describe('addDaysToDateKey', () => {
  it('adds days within a month', () => {
    expect(addDaysToDateKey('2026-02-02', 6)).toBe('2026-02-08')
  })

  it('rolls over a month boundary', () => {
    expect(addDaysToDateKey('2026-01-30', 3)).toBe('2026-02-02')
  })

  it('supports negative offsets', () => {
    expect(addDaysToDateKey('2026-02-02', -7)).toBe('2026-01-26')
  })
})

describe('startOfWeekDateKey', () => {
  it('returns the same date when it is already Monday', () => {
    expect(startOfWeekDateKey('2026-02-02')).toBe('2026-02-02')
  })

  it('returns the prior Monday for a mid-week date', () => {
    expect(startOfWeekDateKey('2026-02-05')).toBe('2026-02-02')
  })

  it('returns the prior Monday for a Sunday', () => {
    expect(startOfWeekDateKey('2026-02-08')).toBe('2026-02-02')
  })
})

describe('eachDateKeyInRange', () => {
  it('returns every date inclusive, Monday through Sunday', () => {
    expect(eachDateKeyInRange('2026-02-02', '2026-02-08')).toEqual([
      '2026-02-02',
      '2026-02-03',
      '2026-02-04',
      '2026-02-05',
      '2026-02-06',
      '2026-02-07',
      '2026-02-08'
    ])
  })

  it('returns a single-day range as one entry', () => {
    expect(eachDateKeyInRange('2026-02-02', '2026-02-02')).toEqual(['2026-02-02'])
  })

  it('crosses a month boundary correctly', () => {
    expect(eachDateKeyInRange('2026-01-30', '2026-02-01')).toEqual(['2026-01-30', '2026-01-31', '2026-02-01'])
  })
})

describe('formatWeekRange', () => {
  it('formats a same-month range', () => {
    expect(formatWeekRange('2026-02-02', '2026-02-08')).toBe('Feb 2 – Feb 8, 2026')
  })

  it('formats a cross-month, same-year range without repeating the year', () => {
    expect(formatWeekRange('2026-01-26', '2026-02-01')).toBe('Jan 26 – Feb 1, 2026')
  })

  it('formats a cross-year range with both years shown', () => {
    expect(formatWeekRange('2025-12-29', '2026-01-04')).toBe('Dec 29, 2025 – Jan 4, 2026')
  })
})
