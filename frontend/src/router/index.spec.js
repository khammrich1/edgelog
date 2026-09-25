import { createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createAppRouter } from './index'
import { useAuthStore } from '@/stores/auth'
import api from '@/services/api'

// Every navigation fires the tracking beacon (router.afterEach) -- mock it
// so route tests don't make real network calls.
vi.mock('@/services/api', () => ({
  default: { post: vi.fn().mockResolvedValue({}) }
}))

function setupRouter() {
  setActivePinia(createPinia())
  const router = createAppRouter(createMemoryHistory())
  const authStore = useAuthStore()
  return { router, authStore }
}

describe('router auth guard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.post.mockResolvedValue({})
  })

  it('redirects an unauthenticated visitor away from a protected route to login', async () => {
    const { router, authStore } = setupRouter()
    authStore.refreshAuth = vi.fn().mockResolvedValue(false)

    await router.push('/journal')

    expect(router.currentRoute.value.path).toBe('/login')
    expect(authStore.isAuthenticated).toBe(false)
  })

  it('lets an authenticated visitor reach a valid protected route', async () => {
    const { router, authStore } = setupRouter()
    authStore.user = { id: 1, email: 'trader@edgelog.trade' }
    authStore.accessToken = 'fake-access-token'

    await router.push('/journal')

    expect(router.currentRoute.value.name).toBe('Journal')
  })

  it('shows the Not Found view for an unknown route while authenticated, without touching auth state', async () => {
    const { router, authStore } = setupRouter()
    authStore.user = { id: 1, email: 'trader@edgelog.trade' }
    authStore.accessToken = 'fake-access-token'
    const logoutSpy = vi.spyOn(authStore, 'logout')

    await router.push('/canada')

    expect(router.currentRoute.value.name).toBe('NotFound')
    // Authentication must remain intact: an unknown route is a routing
    // problem, not an authentication problem.
    expect(authStore.isAuthenticated).toBe(true)
    expect(authStore.user).not.toBeNull()
    expect(authStore.accessToken).not.toBeNull()
    expect(logoutSpy).not.toHaveBeenCalled()
  })

  it('redirects an unauthenticated visitor hitting an unknown route to login instead of leaking app structure', async () => {
    const { router, authStore } = setupRouter()
    authStore.refreshAuth = vi.fn().mockResolvedValue(false)

    await router.push('/asdf')

    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('restores an authenticated session and lands on the Not Found view when reloading an unknown URL', async () => {
    const { router, authStore } = setupRouter()
    // Simulate what a page reload does: no in-memory state yet, but the
    // refresh cookie is still valid, so refreshAuth() re-establishes it.
    authStore.refreshAuth = vi.fn().mockImplementation(async () => {
      authStore.user = { id: 1, email: 'trader@edgelog.trade' }
      authStore.accessToken = 'restored-access-token'
      return true
    })

    await router.push('/canada')

    expect(authStore.refreshAuth).toHaveBeenCalled()
    expect(authStore.isAuthenticated).toBe(true)
    expect(router.currentRoute.value.name).toBe('NotFound')
  })

  it('resolves /trades to the Trade Calendar and requires auth like other protected routes', async () => {
    const { router, authStore } = setupRouter()
    authStore.refreshAuth = vi.fn().mockResolvedValue(false)

    await router.push('/trades')
    expect(router.currentRoute.value.path).toBe('/login')

    authStore.user = { id: 1, email: 'trader@edgelog.trade' }
    authStore.accessToken = 'fake-access-token'
    await router.push('/trades')
    expect(router.currentRoute.value.name).toBe('TradeCalendar')
  })

  it('resolves /trades/:date to the Trade Calendar week view for a valid date', async () => {
    const { router, authStore } = setupRouter()
    authStore.user = { id: 1, email: 'trader@edgelog.trade' }
    authStore.accessToken = 'fake-access-token'

    await router.push('/trades/2026-02-02')

    expect(router.currentRoute.value.name).toBe('TradeCalendarWeek')
    expect(router.currentRoute.value.params.date).toBe('2026-02-02')
  })

  it('falls through to Not Found for a malformed /trades date', async () => {
    const { router, authStore } = setupRouter()
    authStore.user = { id: 1, email: 'trader@edgelog.trade' }
    authStore.accessToken = 'fake-access-token'

    await router.push('/trades/not-a-date')

    expect(router.currentRoute.value.name).toBe('NotFound')
  })

  it('resolves /financials to the Financials view and requires auth like other protected routes', async () => {
    const { router, authStore } = setupRouter()
    authStore.refreshAuth = vi.fn().mockResolvedValue(false)

    await router.push('/financials')
    expect(router.currentRoute.value.path).toBe('/login')

    authStore.user = { id: 1, email: 'trader@edgelog.trade' }
    authStore.accessToken = 'fake-access-token'
    await router.push('/financials')
    expect(router.currentRoute.value.name).toBe('Financials')
  })

  it('resolves /financials/:year to the FinancialsYear view for a valid year', async () => {
    const { router, authStore } = setupRouter()
    authStore.user = { id: 1, email: 'trader@edgelog.trade' }
    authStore.accessToken = 'fake-access-token'

    await router.push('/financials/2026')

    expect(router.currentRoute.value.name).toBe('FinancialsYear')
    expect(router.currentRoute.value.params.year).toBe('2026')
  })

  it('falls through to Not Found for a malformed /financials year', async () => {
    const { router, authStore } = setupRouter()
    authStore.user = { id: 1, email: 'trader@edgelog.trade' }
    authStore.accessToken = 'fake-access-token'

    await router.push('/financials/abc')

    expect(router.currentRoute.value.name).toBe('NotFound')
  })

  it('redirects a non-admin authenticated user away from /admin', async () => {
    const { router, authStore } = setupRouter()
    authStore.user = { id: 1, email: 'trader@edgelog.trade', is_admin: false }
    authStore.accessToken = 'fake-access-token'

    await router.push('/admin')

    expect(router.currentRoute.value.name).toBe('Journal')
  })

  it('lets an admin user reach /admin', async () => {
    const { router, authStore } = setupRouter()
    authStore.user = { id: 1, email: 'admin@edgelog.trade', is_admin: true }
    authStore.accessToken = 'fake-access-token'

    await router.push('/admin')

    expect(router.currentRoute.value.name).toBe('Admin')
  })

  it('redirects an unauthenticated visitor away from /admin to login rather than exposing the admin gate', async () => {
    const { router, authStore } = setupRouter()
    authStore.refreshAuth = vi.fn().mockResolvedValue(false)

    await router.push('/admin')

    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('lets any authenticated user (not just admins) reach /feedback', async () => {
    const { router, authStore } = setupRouter()
    authStore.user = { id: 1, email: 'trader@edgelog.trade', is_admin: false }
    authStore.accessToken = 'fake-access-token'

    await router.push('/feedback')

    expect(router.currentRoute.value.name).toBe('Feedback')
  })

  it('fires the page-view beacon with the destination path on every navigation', async () => {
    const { router, authStore } = setupRouter()
    authStore.user = { id: 1, email: 'trader@edgelog.trade' }
    authStore.accessToken = 'fake-access-token'

    await router.push('/journal')

    expect(api.post).toHaveBeenCalledWith('/track/pageview', { path: '/journal' })
  })

  it('does not let a beacon failure block navigation', async () => {
    const { router, authStore } = setupRouter()
    authStore.user = { id: 1, email: 'trader@edgelog.trade' }
    authStore.accessToken = 'fake-access-token'
    api.post.mockRejectedValue(new Error('network down'))

    await router.push('/journal')

    expect(router.currentRoute.value.name).toBe('Journal')
  })
})
