import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const accessToken = ref(null)
  const loading = ref(false)

  // Getters
  const isAuthenticated = computed(() => !!user.value && !!accessToken.value)

  // Actions
  async function register(email, password) {
    loading.value = true
    try {
      const { data } = await api.post('/auth/register', { email, password })
      accessToken.value = data.access_token
      await fetchUser()
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Registration failed'
      }
    } finally {
      loading.value = false
    }
  }

  async function login(email, password) {
    loading.value = true
    try {
      const { data } = await api.post('/auth/login', { email, password })
      accessToken.value = data.access_token
      await fetchUser()
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed'
      }
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    loading.value = true
    try {
      await api.post('/auth/logout')
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      accessToken.value = null
      user.value = null
      loading.value = false
    }
  }

  async function fetchUser() {
    try {
      const { data } = await api.get('/auth/me')
      user.value = data
    } catch (error) {
      console.error('Fetch user error:', error)
      accessToken.value = null
      user.value = null
    }
  }

  // Several requests can hit a 401 at once (e.g. the access token expires
  // while Today's several independent fetches are all in flight) and each
  // one's response interceptor calls refreshAuth(). Without sharing a
  // single in-flight attempt, every one of those would fire its own
  // POST /auth/refresh + GET /auth/me, multiplying network calls and
  // serializing the delay instead of it happening once. inFlightRefresh is
  // plain module state (not a ref) -- it's a dedup token, not UI state.
  let inFlightRefresh = null

  async function refreshAuth() {
    if (inFlightRefresh) return inFlightRefresh

    inFlightRefresh = (async () => {
      try {
        const { data } = await api.post('/auth/refresh')
        accessToken.value = data.access_token
        await fetchUser()
        return true
      } catch (error) {
        accessToken.value = null
        user.value = null
        return false
      }
    })()

    try {
      return await inFlightRefresh
    } finally {
      inFlightRefresh = null
    }
  }

  return {
    user,
    accessToken,
    loading,
    isAuthenticated,
    register,
    login,
    logout,
    fetchUser,
    refreshAuth
  }
})
