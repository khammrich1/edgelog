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
