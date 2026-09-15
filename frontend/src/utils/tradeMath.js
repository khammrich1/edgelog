/**
 * Pure point/price conversion and risk-reward preview math for the trade
 * entry form. Kept framework-free and side-effect-free so it's directly
 * unit-testable, the same way utils/trades.js's formatting helpers are.
 *
 * Dollar figures always come from a caller-supplied multiplier (the
 * centralized table in backend/app/core/instruments.py, fetched once via
 * GET /api/v1/instruments/multipliers) -- nothing here hard-codes a
 * per-instrument dollar value. When no multiplier is supplied/known, dollar
 * fields come back null rather than an invented number.
 */

function toNumberOrNull(value) {
  if (value === null || value === undefined || value === '') return null
  const n = Number(value)
  return Number.isNaN(n) ? null : n
}

// Rounds to a sane futures-price precision without accumulating binary
// float noise (e.g. 19987.500000000002) in the value we'd otherwise send
// to the API or display back to the user.
function roundPrice(value) {
  return Math.round(value * 10000) / 10000
}

/**
 * Converts a points distance to an absolute price, given the trade's entry
 * price, direction, and which field ('stop' | 'target') it's for.
 *
 * LONG stop / SHORT target sit below entry; LONG target / SHORT stop sit
 * above entry.
 *
 * Returns null if entryPrice or points is missing/not a number.
 */
export function pointsToPrice(entryPrice, points, direction, kind) {
  const entry = toNumberOrNull(entryPrice)
  const pts = toNumberOrNull(points)
  if (entry === null || pts === null) return null

  const belowEntry = (kind === 'stop' && direction === 'long') || (kind === 'target' && direction === 'short')
  return roundPrice(belowEntry ? entry - pts : entry + pts)
}

/**
 * Inverse of pointsToPrice: converts an absolute price back to a points
 * distance from entry, given direction and field kind.
 *
 * Returns null if entryPrice or price is missing/not a number.
 */
export function priceToPoints(entryPrice, price, direction, kind) {
  const entry = toNumberOrNull(entryPrice)
  const pr = toNumberOrNull(price)
  if (entry === null || pr === null) return null

  const belowEntry = (kind === 'stop' && direction === 'long') || (kind === 'target' && direction === 'short')
  return roundPrice(belowEntry ? entry - pr : pr - entry)
}

/**
 * Computes the trade form's live risk/reward preview.
 *
 * `multiplier` is the per-point dollar value for the trade's symbol, or
 * null/undefined for an instrument EdgeLog has no verified contract spec
 * for -- in that case riskDollars/rewardDollars stay null rather than
 * guessing. Returns null entirely if there isn't enough information yet
 * (no quantity, or no valid entry price).
 */
export function computeRiskReward({ quantity, entryPrice, stopPrice, targetPrice, direction, multiplier }) {
  const qty = toNumberOrNull(quantity)
  const entry = toNumberOrNull(entryPrice)
  if (!qty || qty <= 0 || entry === null) return null

  const mult = toNumberOrNull(multiplier)

  let riskPoints = null
  let riskDollars = null
  const stop = toNumberOrNull(stopPrice)
  if (stop !== null) {
    riskPoints = roundPrice(Math.abs(entry - stop))
    if (mult !== null) riskDollars = roundPrice(riskPoints * qty * mult)
  }

  let rewardPoints = null
  let rewardDollars = null
  const target = toNumberOrNull(targetPrice)
  if (target !== null) {
    rewardPoints = roundPrice(Math.abs(target - entry))
    if (mult !== null) rewardDollars = roundPrice(rewardPoints * qty * mult)
  }

  const rrRatio = riskPoints && riskPoints > 0 && rewardPoints !== null ? roundPrice(rewardPoints / riskPoints) : null

  return {
    quantity: qty,
    direction,
    riskPoints,
    riskDollars,
    rewardPoints,
    rewardDollars,
    rrRatio,
    multiplierKnown: mult !== null
  }
}
