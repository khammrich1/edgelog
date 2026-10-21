import { describe, expect, it } from 'vitest'
import { formatPreviewRequestError, parseExecutionsInput } from './reconciliation'

function validExecution(overrides = {}) {
  return {
    id: 1,
    accountId: 123,
    contractId: 'CON.F.US.MNQ.Z25',
    creationTimestamp: '2026-02-04T14:31:00Z',
    orderId: 55,
    price: 21050.25,
    size: 1,
    side: 0,
    ...overrides
  }
}

describe('parseExecutionsInput', () => {
  it('rejects empty input with a helpful message', () => {
    expect(parseExecutionsInput('')).toEqual({
      executions: null,
      error: 'Paste or upload execution JSON before previewing.'
    })
    expect(parseExecutionsInput('   ')).toEqual({
      executions: null,
      error: 'Paste or upload execution JSON before previewing.'
    })
  })

  it('rejects malformed JSON with the parser error', () => {
    const { executions, error } = parseExecutionsInput('{not valid json')
    expect(executions).toBeNull()
    expect(error).toMatch(/isn't valid JSON/)
  })

  it('accepts a bare JSON array', () => {
    const { executions, error } = parseExecutionsInput(JSON.stringify([validExecution()]))
    expect(error).toBeNull()
    expect(executions).toHaveLength(1)
    expect(executions[0].id).toBe(1)
  })

  it('accepts an object wrapping the array under "executions"', () => {
    const { executions, error } = parseExecutionsInput(JSON.stringify({ executions: [validExecution()] }))
    expect(error).toBeNull()
    expect(executions).toHaveLength(1)
  })

  it('rejects a JSON value that is neither an array nor an {executions: [...]} object', () => {
    const { executions, error } = parseExecutionsInput(JSON.stringify({ foo: 'bar' }))
    expect(executions).toBeNull()
    expect(error).toMatch(/Expected a JSON array/)
  })

  it('rejects an empty executions array', () => {
    const { executions, error } = parseExecutionsInput('[]')
    expect(executions).toBeNull()
    expect(error).toMatch(/empty/)
  })

  it('reports which required fields are missing, per execution, up to 5 problems', () => {
    const batch = [validExecution({ id: 1, price: undefined }), { id: 2 }]
    const { executions, error } = parseExecutionsInput(JSON.stringify(batch))
    expect(executions).toBeNull()
    expect(error).toContain('Execution 1 is missing: price.')
    expect(error).toContain('Execution 2 is missing:')
  })

  it('flags a non-object entry in the array', () => {
    const { executions, error } = parseExecutionsInput(JSON.stringify(['not an object']))
    expect(executions).toBeNull()
    expect(error).toContain('Execution 1 is not a JSON object.')
  })

  it('passes a fully valid multi-execution batch through unchanged', () => {
    const batch = [validExecution({ id: 1 }), validExecution({ id: 2, orderId: null })]
    const { executions, error } = parseExecutionsInput(JSON.stringify(batch))
    expect(error).toBeNull()
    expect(executions).toEqual(batch)
  })
})

describe('formatPreviewRequestError', () => {
  it('reports a network error when there is no response', () => {
    expect(formatPreviewRequestError({})).toMatch(/Network error/)
  })

  it('reports an expired session on 401', () => {
    const error = { response: { status: 401, data: {} } }
    expect(formatPreviewRequestError(error)).toMatch(/session has expired/)
  })

  it('surfaces a string detail from a 400 response as-is', () => {
    const error = { response: { status: 400, data: { detail: 'Execution(s) [1] report a different accountId...' } } }
    expect(formatPreviewRequestError(error)).toBe('Execution(s) [1] report a different accountId...')
  })

  it('formats a 422 validation array into readable per-field messages', () => {
    const error = {
      response: {
        status: 422,
        data: {
          detail: [
            { loc: ['body', 'executions', 0, 'price'], msg: 'Input should be greater than 0' },
            { loc: ['body', 'account_id'], msg: 'Input should be greater than 0' }
          ]
        }
      }
    }
    const message = formatPreviewRequestError(error)
    expect(message).toContain('executions.0.price: Input should be greater than 0')
    expect(message).toContain('account_id: Input should be greater than 0')
  })

  it('falls back to a generic message when there is no usable detail', () => {
    const error = { response: { status: 500, data: {} } }
    expect(formatPreviewRequestError(error)).toMatch(/preview request failed/)
  })
})
