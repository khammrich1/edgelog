/**
 * Pure parsing/validation/error-formatting helpers for the Reconciliation
 * Preview view (issue #97). Kept separate from the view component so the
 * input-validation rules are unit-testable without mounting anything, and
 * so a malformed paste/upload gets a useful message before a round trip
 * to the (otherwise authoritative) backend validation.
 */

const REQUIRED_EXECUTION_FIELDS = ['id', 'accountId', 'contractId', 'creationTimestamp', 'price', 'size', 'side']

/**
 * Parses pasted or uploaded execution JSON into an array ready to send as
 * `executions` in a reconciliation preview request. Accepts either a bare
 * JSON array or an object shaped like `{ "executions": [...] }` (useful
 * when pasting a raw diagnostic export that wraps the array). Returns
 * `{ executions, error }` -- exactly one of the two is non-null -- rather
 * than throwing, so the caller can render the error directly.
 */
export function parseExecutionsInput(rawText) {
  const trimmed = (rawText ?? '').trim()
  if (!trimmed) {
    return { executions: null, error: 'Paste or upload execution JSON before previewing.' }
  }

  let parsed
  try {
    parsed = JSON.parse(trimmed)
  } catch (e) {
    return { executions: null, error: `That isn't valid JSON: ${e.message}` }
  }

  const executions = Array.isArray(parsed) ? parsed : Array.isArray(parsed?.executions) ? parsed.executions : null

  if (executions === null) {
    return {
      executions: null,
      error: 'Expected a JSON array of executions, or an object with an "executions" array.'
    }
  }

  if (executions.length === 0) {
    return { executions: null, error: 'The executions array is empty -- the preview needs at least one execution.' }
  }

  const problems = []
  executions.forEach((execution, index) => {
    if (typeof execution !== 'object' || execution === null || Array.isArray(execution)) {
      problems.push(`Execution ${index + 1} is not a JSON object.`)
      return
    }
    const missing = REQUIRED_EXECUTION_FIELDS.filter(
      (field) => execution[field] === undefined || execution[field] === null
    )
    if (missing.length > 0) {
      problems.push(`Execution ${index + 1} is missing: ${missing.join(', ')}.`)
    }
  })

  if (problems.length > 0) {
    const shown = problems.slice(0, 5)
    const suffix = problems.length > shown.length ? ` …and ${problems.length - shown.length} more.` : ''
    return { executions: null, error: shown.join(' ') + suffix }
  }

  return { executions, error: null }
}

/**
 * Turns an Axios error from the preview request into one readable
 * message, distinguishing the states the backend (and the network) can
 * actually produce: validation (422), a refused request (400), an
 * unauthenticated session (401, surfaced only once the api client's own
 * refresh attempt has already failed), and no response at all.
 */
export function formatPreviewRequestError(error) {
  if (!error?.response) {
    return 'Network error -- check your connection and try again.'
  }

  const { status, data } = error.response
  const detail = data?.detail

  if (status === 401) {
    return 'Your session has expired. Sign in again to run a preview.'
  }

  if (status === 422 && Array.isArray(detail)) {
    return detail
      .map((item) => {
        const loc = Array.isArray(item.loc) ? item.loc.filter((part) => part !== 'body').join('.') : ''
        return loc ? `${loc}: ${item.msg}` : item.msg
      })
      .join(' ')
  }

  if (typeof detail === 'string' && detail.length > 0) {
    return detail
  }

  return 'The preview request failed. Check the input and try again.'
}
