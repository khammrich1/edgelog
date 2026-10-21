import { describe, expect, it } from 'vitest'
import { formatApiErrorDetail, parseExecutionBatch, sideLabel, SAMPLE_EXECUTIONS_JSON } from './reconciliation'

const VALID_EXECUTION = {
  id: 1,
  accountId: 28592949,
  contractId: 'CON.F.US.MNQ.Z25',
  creationTimestamp: '2026-10-16T14:30:00Z',
  price: 21000,
  size: 1,
  side: 0
}

describe('parseExecutionBatch', () => {
  it('rejects empty input', () => {
    const { executions, errors } = parseExecutionBatch('')
    expect(executions).toBeNull()
    expect(errors).toHaveLength(1)
  })

  it('rejects malformed JSON with a clear error', () => {
    const { executions, errors } = parseExecutionBatch('{ not json')
    expect(executions).toBeNull()
    expect(errors[0]).toContain('Not valid JSON')
  })

  it('rejects a single object instead of an array', () => {
    const { executions, errors } = parseExecutionBatch(JSON.stringify(VALID_EXECUTION))
    expect(executions).toBeNull()
    expect(errors[0]).toContain('array')
  })

  it('rejects an empty array', () => {
    const { executions, errors } = parseExecutionBatch('[]')
    expect(executions).toBeNull()
    expect(errors[0]).toContain('empty')
  })

  it('rejects a non-object element', () => {
    const { executions, errors } = parseExecutionBatch(JSON.stringify([VALID_EXECUTION, 'not an object']))
    expect(executions).toBeNull()
    expect(errors[0]).toContain('Execution 1')
  })

  it('reports each missing required field with its index', () => {
    const incomplete = { ...VALID_EXECUTION }
    delete incomplete.price
    delete incomplete.side
    const { executions, errors } = parseExecutionBatch(JSON.stringify([incomplete]))
    expect(executions).toBeNull()
    expect(errors).toEqual(
      expect.arrayContaining([expect.stringContaining('"price"'), expect.stringContaining('"side"')])
    )
  })

  it('accepts a valid batch', () => {
    const { executions, errors } = parseExecutionBatch(JSON.stringify([VALID_EXECUTION]))
    expect(errors).toEqual([])
    expect(executions).toEqual([VALID_EXECUTION])
  })

  it('accepts the bundled sample fixture', () => {
    const { executions, errors } = parseExecutionBatch(SAMPLE_EXECUTIONS_JSON)
    expect(errors).toEqual([])
    expect(executions).toHaveLength(2)
  })

  it('trims surrounding whitespace before checking for empty input', () => {
    const { executions, errors } = parseExecutionBatch('   \n  ')
    expect(executions).toBeNull()
    expect(errors[0]).toContain('Paste or upload')
  })
})

describe('sideLabel', () => {
  it('labels known ProjectX side codes', () => {
    expect(sideLabel(0)).toBe('Buy')
    expect(sideLabel(1)).toBe('Sell')
  })

  it('falls back to a raw label for an unknown code rather than guessing', () => {
    expect(sideLabel(9)).toBe('Side 9')
  })
})

describe('formatApiErrorDetail', () => {
  it('passes through a plain string detail (explicit HTTPException)', () => {
    expect(formatApiErrorDetail('Something went wrong')).toEqual(['Something went wrong'])
  })

  it('formats a FastAPI/Pydantic 422 validation array into readable lines', () => {
    const detail = [
      { loc: ['body', 'executions', 0, 'price'], msg: 'Input should be greater than 0', type: 'greater_than' }
    ]
    expect(formatApiErrorDetail(detail)).toEqual(['executions.0.price: Input should be greater than 0'])
  })

  it('handles a missing/null detail without throwing', () => {
    expect(formatApiErrorDetail(null)).toEqual([])
    expect(formatApiErrorDetail(undefined)).toEqual([])
  })

  it('falls back to JSON for an unexpected shape rather than crashing', () => {
    expect(formatApiErrorDetail({ unexpected: true })).toEqual([JSON.stringify({ unexpected: true })])
  })
})
