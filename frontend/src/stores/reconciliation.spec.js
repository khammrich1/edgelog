import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useReconciliationStore } from './reconciliation'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }
}))

describe('reconciliation store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('preview posts to the existing read-only reconciliation endpoint and stores the result', async () => {
    const payload = { account_id: 1, date: '2026-10-16', executions: [{ id: 1 }] }
    const response = { account_id: 1, date: '2026-10-16', executions: [], fill_groups: [], summary: {} }
    api.post.mockResolvedValue({ data: response })
    const store = useReconciliationStore()

    const result = await store.preview(payload)

    expect(api.post).toHaveBeenCalledWith('/journal/reconciliation/preview', payload)
    expect(result).toEqual(response)
    expect(store.result).toEqual(response)
  })

  it('preview never calls any write endpoint -- only the one preview POST', async () => {
    api.post.mockResolvedValue({ data: {} })
    const store = useReconciliationStore()

    await store.preview({ account_id: 1, date: '2026-10-16', executions: [{ id: 1 }] })

    expect(api.post).toHaveBeenCalledTimes(1)
    expect(api.put).not.toHaveBeenCalled()
    expect(api.delete).not.toHaveBeenCalled()
  })

  it('clear resets the stored result', async () => {
    api.post.mockResolvedValue({ data: { executions: [] } })
    const store = useReconciliationStore()
    await store.preview({ account_id: 1, date: '2026-10-16', executions: [{ id: 1 }] })
    expect(store.result).not.toBeNull()

    store.clear()

    expect(store.result).toBeNull()
  })

  it('propagates a failed preview request to the caller', async () => {
    const error = { response: { status: 422, data: { detail: 'bad request' } } }
    api.post.mockRejectedValue(error)
    const store = useReconciliationStore()

    await expect(store.preview({ account_id: 1, date: '2026-10-16', executions: [{ id: 1 }] })).rejects.toBe(error)
    expect(store.result).toBeNull()
  })
})
