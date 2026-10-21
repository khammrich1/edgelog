/**
 * Pure, framework-free helpers for the Reconciliation Preview screen
 * (issue #97): parsing/validating a pasted or uploaded execution batch
 * before it's ever sent to the read-only preview API, plus small display
 * helpers. Kept separate from the view so parsing/validation is directly
 * unit-testable, the same way utils/trades.js and utils/tradeMath.js are.
 *
 * This module never calls the network and never writes anywhere -- it
 * only inspects the JSON text the trader typed/uploaded.
 */

// Fields POST /api/v1/journal/reconciliation/preview's ExecutionIn requires
// (backend/app/schemas/reconciliation.py) -- kept in sync by hand since the
// backend is the actual source of truth; this is a client-side pre-check
// for a fast/clear error, not a replacement for the server's own 422.
const REQUIRED_EXECUTION_FIELDS = ['id', 'accountId', 'contractId', 'creationTimestamp', 'price', 'size', 'side']

/**
 * Parses and shape-validates a pasted/uploaded execution batch.
 *
 * Returns { executions, errors }. `executions` is the parsed array (or
 * null if parsing/shape validation failed); `errors` is a list of
 * human-readable strings, empty on success. Never throws.
 */
export function parseExecutionBatch(rawText) {
  const text = (rawText || '').trim()
  if (!text) {
    return { executions: null, errors: ['Paste or upload a JSON array of execution records first.'] }
  }

  let parsed
  try {
    parsed = JSON.parse(text)
  } catch (error) {
    return { executions: null, errors: [`Not valid JSON: ${error.message}`] }
  }

  if (!Array.isArray(parsed)) {
    return { executions: null, errors: ['Expected a JSON array of execution objects (e.g. [{ "id": 1, ... }]), not a single object or value.'] }
  }
  if (parsed.length === 0) {
    return { executions: null, errors: ['The execution array is empty -- the preview API requires at least one execution.'] }
  }

  const errors = []
  parsed.forEach((execution, index) => {
    if (execution === null || typeof execution !== 'object' || Array.isArray(execution)) {
      errors.push(`Execution ${index}: expected an object, got ${Array.isArray(execution) ? 'an array' : typeof execution}.`)
      return
    }
    for (const field of REQUIRED_EXECUTION_FIELDS) {
      if (execution[field] === undefined || execution[field] === null) {
        errors.push(`Execution ${index}: missing required field "${field}".`)
      }
    }
  })

  if (errors.length > 0) {
    return { executions: null, errors }
  }
  return { executions: parsed, errors: [] }
}

// ProjectX order side enum (docs/integrations/projectx/PROJECTX_API_REFERENCE.md):
// 0 = Bid/buy, 1 = Ask/sell. Anything else is shown as-is rather than guessed.
const SIDE_LABELS = { 0: 'Buy', 1: 'Sell' }

export function sideLabel(side) {
  return SIDE_LABELS[side] ?? `Side ${side}`
}

/**
 * Formats a FastAPI/Pydantic error response body into readable lines.
 * A 422 `detail` is a list of {loc, msg, ...} objects; an explicit
 * HTTPException (400/404/409/...) `detail` is a plain string. Handles
 * both, plus an unexpected shape, without ever throwing.
 */
export function formatApiErrorDetail(detail) {
  if (typeof detail === 'string') return [detail]
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      if (item && typeof item === 'object' && 'msg' in item) {
        const loc = Array.isArray(item.loc) ? item.loc.filter((p) => p !== 'body').join('.') : null
        return loc ? `${loc}: ${item.msg}` : item.msg
      }
      return typeof item === 'string' ? item : JSON.stringify(item)
    })
  }
  if (detail == null) return []
  return [typeof detail === 'string' ? detail : JSON.stringify(detail)]
}

// A small, clearly-synthetic fixture (not real broker data) so an owner
// can exercise the preview immediately: two executions sharing an
// orderId (a confident grouped pair) on an unrecognized symbol, so the
// preview predictably shows a "needs_confirmation"-free confident group
// with an unplanned journal-trade match -- a safe, deterministic first look.
export const SAMPLE_EXECUTIONS_JSON = JSON.stringify(
  [
    {
      id: 900001,
      accountId: 28592949,
      contractId: 'CON.F.US.MNQ.Z25',
      creationTimestamp: '2026-10-16T14:30:00Z',
      price: '21000.00',
      size: 2,
      side: 0,
      orderId: 500001,
      fees: '2.50',
      commissions: '0.62',
      voided: false
    },
    {
      id: 900002,
      accountId: 28592949,
      contractId: 'CON.F.US.MNQ.Z25',
      creationTimestamp: '2026-10-16T14:45:00Z',
      price: '21040.00',
      size: 2,
      side: 1,
      orderId: 500001,
      fees: '2.50',
      commissions: '0.62',
      profitAndLoss: '160.00',
      voided: false
    }
  ],
  null,
  2
)
