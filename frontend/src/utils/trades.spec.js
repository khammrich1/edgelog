import { describe, expect, it } from 'vitest'
import {
  formatPrice,
  formatSignedDollars,
  formatSignedPoints,
  resultClass,
  summarizeClosedTrades,
  summaryResultClass,
  summaryResultLabel,
  SYMBOL_PRESETS
} from './trades'

function fakeTrade(overrides = {}) {
  return {
    status: 'closed',
    realized_points: 0,
    realized_pnl: 0,
    multiplier_known: true,
    ...overrides
  }
}

describe('SYMBOL_PRESETS', () => {
  it('offers the requested quick-entry symbols', () => {
    expect(SYMBOL_PRESETS).toEqual(['MNQ', 'MES', 'MGC', 'MCL'])
  })
})

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

describe('summarizeClosedTrades', () => {
  it('counts all trades but only sums closed ones', () => {
    const summary = summarizeClosedTrades([
      fakeTrade({ status: 'open' }),
      fakeTrade({ status: 'closed', realized_pnl: 100, realized_points: 10 }),
      fakeTrade({ status: 'canceled' })
    ])
    expect(summary.tradeCount).toBe(3)
    expect(summary.closedCount).toBe(1)
    expect(summary.dollarTotal).toBe(100)
  })

  it('sums dollar totals when every closed trade has a known multiplier', () => {
    const summary = summarizeClosedTrades([
      fakeTrade({ realized_pnl: 100, realized_points: 10 }),
      fakeTrade({ realized_pnl: -40, realized_points: -4 })
    ])
    expect(summary.allMultiplierKnown).toBe(true)
    expect(summary.dollarTotal).toBe(60)
    expect(summary.wins).toBe(1)
    expect(summary.losses).toBe(1)
    expect(summary.breakeven).toBe(0)
  })

  it('flags allMultiplierKnown false when any closed trade lacks a known multiplier, without inventing its dollar figure', () => {
    const summary = summarizeClosedTrades([
      fakeTrade({ realized_pnl: 100, realized_points: 10 }),
      fakeTrade({ multiplier_known: false, realized_pnl: null, realized_points: 5 })
    ])
    expect(summary.allMultiplierKnown).toBe(false)
    // Only the known-multiplier trade's dollar figure is summed -- the
    // unknown trade contributes to pointsTotal, never to dollarTotal.
    expect(summary.dollarTotal).toBe(100)
    expect(summary.pointsTotal).toBe(15)
  })

  it('classifies wins/losses/breakeven per-trade using dollar when known, points otherwise', () => {
    const summary = summarizeClosedTrades([
      fakeTrade({ multiplier_known: false, realized_pnl: null, realized_points: 5 }),
      fakeTrade({ multiplier_known: false, realized_pnl: null, realized_points: -3 }),
      fakeTrade({ multiplier_known: false, realized_pnl: null, realized_points: 0 })
    ])
    expect(summary.wins).toBe(1)
    expect(summary.losses).toBe(1)
    expect(summary.breakeven).toBe(1)
  })

  it('reports zero closed trades without dividing by anything or fabricating a result', () => {
    const summary = summarizeClosedTrades([fakeTrade({ status: 'open' })])
    expect(summary.closedCount).toBe(0)
    expect(summary.dollarTotal).toBe(0)
    expect(summaryResultLabel(summary)).toBeNull()
  })
})

describe('summaryResultLabel / summaryResultClass', () => {
  it('labels a fully-known set in dollars', () => {
    const summary = summarizeClosedTrades([fakeTrade({ realized_pnl: 250, realized_points: 25 })])
    expect(summaryResultLabel(summary)).toBe('+$250.00')
    expect(summaryResultClass(summary)).toBe('result-positive')
  })

  it('falls back to points when any multiplier is unknown, never showing a partial dollar figure', () => {
    const summary = summarizeClosedTrades([
      fakeTrade({ realized_pnl: 250, realized_points: 25 }),
      fakeTrade({ multiplier_known: false, realized_pnl: null, realized_points: -5 })
    ])
    expect(summaryResultLabel(summary)).toBe('+20 pts')
    expect(summaryResultClass(summary)).toBe('result-positive')
  })

  it('returns null/neutral when nothing has closed yet', () => {
    const summary = summarizeClosedTrades([])
    expect(summaryResultLabel(summary)).toBeNull()
    expect(summaryResultClass(summary)).toBe('')
  })
})
