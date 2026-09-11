import { createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createAppRouter } from './index'
import { useAuthStore } from '@/stores/auth'

function setupRouter() {
  setActivePinia(createPinia())
  const router = createAppRouter(createMemoryHistory())
  const authStore = useAuthStore()
  return { router, authStore }
}

describe('router auth guard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
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
})
