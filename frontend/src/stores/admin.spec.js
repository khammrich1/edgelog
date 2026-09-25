import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAdminStore } from './admin'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn() }
}))

describe('admin store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('fetchRoster requests the roster and stores it', async () => {
    const roster = [{ id: 1, email: 'a@example.com', is_admin: true }]
    api.get.mockResolvedValue({ data: roster })
    const store = useAdminStore()

    await store.fetchRoster()

    expect(api.get).toHaveBeenCalledWith('/admin/roster')
    expect(store.roster).toEqual(roster)
  })

  it('fetchTraffic requests traffic and stores it', async () => {
    const traffic = [{ path: '/journal', hits: 10, unique_auth_users: 1, auth_hits: 9, unauth_hits: 1 }]
    api.get.mockResolvedValue({ data: traffic })
    const store = useAdminStore()

    await store.fetchTraffic()

    expect(api.get).toHaveBeenCalledWith('/admin/traffic')
    expect(store.traffic).toEqual(traffic)
  })

  it('fetchFeedback requests feedback and stores it', async () => {
    const feedback = [{ id: 1, user_email: 'a@example.com', message: 'hi', created_at: '2026-01-01T00:00:00Z' }]
    api.get.mockResolvedValue({ data: feedback })
    const store = useAdminStore()

    await store.fetchFeedback()

    expect(api.get).toHaveBeenCalledWith('/admin/feedback')
    expect(store.feedback).toEqual(feedback)
  })
})
