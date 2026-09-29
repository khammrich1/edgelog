/**
 * Pure formatting/presentation helpers for trade display. Kept separate
 * from TradesSection.vue so the calculation/presentation rules (in
 * particular, when a result reads as profit vs. loss) are unit-testable
 * without mounting a component.
 */

/**
 * Symbols offered in the quick-entry dropdown. This is a shortcut list for
 * the trader's most-used instruments, not a restriction -- the backend
 * accepts any symbol, and the form falls back to free text for anything
 * not in this list.
 */
export const SYMBOL_PRESETS = ['MNQ', 'MES', 'MGC', 'MCL']

export function formatPrice(value) {
  if (value === null || value === undefined || value === '') return ''
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 4 })
}

export function formatSignedPoints(points) {
  const n = Number(points)
  const sign = n > 0 ? '+' : ''
  return `${sign}${formatPrice(n)}`
}

export function formatSignedDollars(amount) {
  const n = Number(amount)
  const sign = n > 0 ? '+' : n < 0 ? '-' : ''
  return `${sign}$${Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

/**
 * Green for a positive result, red for negative, neutral for exactly zero
 * or an unknown value -- matches EdgeLog's rule that green/red are reserved
 * strictly for profit/loss, never used decoratively.
 */
export function resultClass(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return ''
  if (n > 0) return 'result-positive'
  if (n < 0) return 'result-negative'
  return ''
}

/**
 * Aggregates a list of TradeRead objects (as returned for a single day or
 * merged across a range) into a truthful realized-result summary, for the
 * Dashboard's "recent performance" snapshot and per-day activity rows.
 *
 * Dollar P&L is only summed from trades whose multiplier is known (same
 * per-trade rule TradeCalendarCard already uses) -- it never mixes a known
 * dollar total with a guessed one. When one or more closed trades in the
 * set lack a known multiplier, allMultiplierKnown is false and callers
 * should fall back to the points total rather than presenting a partial
 * dollar figure as complete.
 */
export function summarizeClosedTrades(trades) {
  const closed = trades.filter((t) => t.status === 'closed')

  let dollarTotal = 0
  let pointsTotal = 0
  let allMultiplierKnown = true
  let wins = 0
  let losses = 0
  let breakeven = 0

  for (const trade of closed) {
    pointsTotal += Number(trade.realized_points)

    if (trade.multiplier_known) {
      dollarTotal += Number(trade.realized_pnl)
    } else {
      allMultiplierKnown = false
    }

    const value = trade.multiplier_known ? Number(trade.realized_pnl) : Number(trade.realized_points)
    if (value > 0) wins += 1
    else if (value < 0) losses += 1
    else breakeven += 1
  }

  return {
    tradeCount: trades.length,
    closedCount: closed.length,
    dollarTotal,
    pointsTotal,
    allMultiplierKnown,
    wins,
    losses,
    breakeven
  }
}

/**
 * The single headline figure for a summarizeClosedTrades() result: a dollar
 * amount when every closed trade's multiplier is known, otherwise a points
 * figure so the number shown is never a partial/misleading dollar total.
 * Returns null when there's nothing closed yet to summarize.
 */
export function summaryResultLabel(summary) {
  if (summary.closedCount === 0) return null
  return summary.allMultiplierKnown
    ? formatSignedDollars(summary.dollarTotal)
    : `${formatSignedPoints(summary.pointsTotal)} pts`
}

export function summaryResultClass(summary) {
  if (summary.closedCount === 0) return ''
  return resultClass(summary.allMultiplierKnown ? summary.dollarTotal : summary.pointsTotal)
}
