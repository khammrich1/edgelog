import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from './auth'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }
}))

describe('auth store refreshAuth concurrency (issue #71)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('shares a single in-flight refresh across concurrent callers instead of one per caller', async () => {
    // Several requests can all hit a 401 at once (e.g. Today's several
    // independent fetches, if the access token happens to already be
    // expired) and each one's response interceptor calls refreshAuth().
    // Without dedup, that's N independent POST /auth/refresh + GET /auth/me
    // pairs instead of one shared pair.
    let resolveRefresh
    api.post.mockImplementation(() => new Promise((resolve) => { resolveRefresh = resolve }))
    api.get.mockResolvedValue({ data: { id: 1, email: 'trader@example.com' } })

    const store = useAuthStore()

    // Five "concurrent" callers, exactly like five requests' interceptors
    // all calling refreshAuth() before any of them has resolved.
    const calls = [store.refreshAuth(), store.refreshAuth(), store.refreshAuth(), store.refreshAuth(), store.refreshAuth()]

    expect(api.post).toHaveBeenCalledTimes(1)

    resolveRefresh({ data: { access_token: 'new-token' } })
    const results = await Promise.all(calls)

    expect(results).toEqual([true, true, true, true, true])
    expect(api.post).toHaveBeenCalledTimes(1)
    expect(api.get).toHaveBeenCalledTimes(1)
    expect(store.accessToken).toBe('new-token')
  })

  it('allows a fresh refresh after a previous one has fully completed', async () => {
    api.post.mockResolvedValue({ data: { access_token: 'token-1' } })
    api.get.mockResolvedValue({ data: { id: 1, email: 'trader@example.com' } })
    const store = useAuthStore()

    await store.refreshAuth()
    await store.refreshAuth()

    // Two genuinely separate (non-overlapping) refresh cycles must each
    // still hit the network -- dedup only collapses truly concurrent ones.
    expect(api.post).toHaveBeenCalledTimes(2)
  })

  it('a failed refresh clears auth state and lets a later refresh try again', async () => {
    api.post.mockRejectedValueOnce(new Error('refresh token invalid'))
    const store = useAuthStore()

    const result = await store.refreshAuth()

    expect(result).toBe(false)
    expect(store.accessToken).toBeNull()
    expect(store.user).toBeNull()

    api.post.mockResolvedValueOnce({ data: { access_token: 'token-2' } })
    api.get.mockResolvedValueOnce({ data: { id: 1, email: 'trader@example.com' } })
    const secondResult = await store.refreshAuth()

    expect(secondResult).toBe(true)
    expect(store.accessToken).toBe('token-2')
  })
})
