import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useBrokerAccountsStore } from './brokerAccounts'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn() }
}))

describe('brokerAccounts store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('fetchAccounts replaces the list', async () => {
    const account = { id: 1, provider: 'topstepx', account_id: 'PRACTICE-1', label: null }
    api.get.mockResolvedValue({ data: [account] })
    const store = useBrokerAccountsStore()

    await store.fetchAccounts()

    expect(api.get).toHaveBeenCalledWith('/broker-accounts')
    expect(store.accounts).toEqual([account])
  })

  it('createAccount posts the payload and appends the result', async () => {
    const payload = { provider: 'topstepx', account_id: 'PRACTICE-1', label: 'Practice' }
    const created = { id: 1, ...payload }
    api.post.mockResolvedValue({ data: created })
    const store = useBrokerAccountsStore()

    const result = await store.createAccount(payload)

    expect(api.post).toHaveBeenCalledWith('/broker-accounts', payload)
    expect(result).toEqual(created)
    expect(store.accounts).toEqual([created])
  })
})
