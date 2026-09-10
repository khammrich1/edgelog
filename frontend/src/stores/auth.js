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

  async function refreshAuth() {
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
