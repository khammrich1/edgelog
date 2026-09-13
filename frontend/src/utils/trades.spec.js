import { describe, expect, it } from 'vitest'
import { formatPrice, formatSignedDollars, formatSignedPoints, resultClass } from './trades'

describe('formatPrice', () => {
  it('formats whole numbers without decimals', () => {
    expect(formatPrice(24500)).toBe('24,500')
  })

  it('preserves fractional ticks', () => {
    expect(formatPrice(24487.5)).toBe('24,487.5')
  })

  it('returns an empty string for null/undefined/empty', () => {
    expect(formatPrice(null)).toBe('')
    expect(formatPrice(undefined)).toBe('')
    expect(formatPrice('')).toBe('')
  })
})

describe('formatSignedPoints', () => {
  it('prefixes a plus sign for a positive value', () => {
    expect(formatSignedPoints(50)).toBe('+50')
  })

  it('does not double a negative sign', () => {
    expect(formatSignedPoints(-50)).toBe('-50')
  })
})

describe('formatSignedDollars', () => {
  it('formats a profit with a leading plus and two decimals', () => {
    expect(formatSignedDollars(100)).toBe('+$100.00')
  })

  it('formats a loss with a leading minus, not double-negative', () => {
    expect(formatSignedDollars(-42.5)).toBe('-$42.50')
  })

  it('formats exactly zero with no sign', () => {
    expect(formatSignedDollars(0)).toBe('$0.00')
  })
})

describe('resultClass', () => {
  it('is green (result-positive) only for a positive number', () => {
    expect(resultClass(1)).toBe('result-positive')
  })

  it('is red (result-negative) only for a negative number', () => {
    expect(resultClass(-1)).toBe('result-negative')
  })

  it('is neutral for exactly zero', () => {
    expect(resultClass(0)).toBe('')
  })
})
