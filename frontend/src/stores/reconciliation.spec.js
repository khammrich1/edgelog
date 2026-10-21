import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useReconciliationStore } from './reconciliation'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: { post: vi.fn() }
}))

describe('reconciliation store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('previewReconciliation posts to the existing read-only preview endpoint and stores the result', async () => {
    const payload = { account_id: 123, date: '2026-02-04', executions: [{ id: 1 }] }
    const response = { account_id: 123, date: '2026-02-04', executions: [], fill_groups: [], summary: {} }
    api.post.mockResolvedValue({ data: response })
    const store = useReconciliationStore()

    const result = await store.previewReconciliation(payload)

    expect(api.post).toHaveBeenCalledWith('/journal/reconciliation/preview', payload)
    expect(result).toEqual(response)
    expect(store.lastPreview).toEqual(response)
  })

  it('previewReconciliation never calls any write-looking endpoint', async () => {
    api.post.mockResolvedValue({ data: {} })
    const store = useReconciliationStore()

    await store.previewReconciliation({ account_id: 1, date: '2026-02-04', executions: [{ id: 1 }] })

    for (const call of api.post.mock.calls) {
      expect(call[0]).toBe('/journal/reconciliation/preview')
    }
  })

  it('clearPreview resets the stored preview', async () => {
    api.post.mockResolvedValue({ data: { foo: 'bar' } })
    const store = useReconciliationStore()
    await store.previewReconciliation({ account_id: 1, date: '2026-02-04', executions: [{ id: 1 }] })

    store.clearPreview()

    expect(store.lastPreview).toBeNull()
  })

  it('a failed preview call rejects without mutating lastPreview', async () => {
    api.post.mockRejectedValue(new Error('network down'))
    const store = useReconciliationStore()

    await expect(
      store.previewReconciliation({ account_id: 1, date: '2026-02-04', executions: [{ id: 1 }] })
    ).rejects.toThrow('network down')
    expect(store.lastPreview).toBeNull()
  })
})
