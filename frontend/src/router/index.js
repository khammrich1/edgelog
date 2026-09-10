import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'
import Journal from '@/views/Journal.vue'

const routes = [
  {
    path: '/',
    redirect: '/journal'
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresAuth: false }
  },
  {
    path: '/journal',
    name: 'Journal',
    component: Journal,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Try to restore authentication on first load
  if (!authStore.isAuthenticated && !authStore.loading) {
    await authStore.refreshAuth()
  }

  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login if not authenticated
    next('/login')
  } else if (!requiresAuth && authStore.isAuthenticated) {
    // Redirect to journal if already authenticated
    next('/journal')
  } else {
    next()
  }
})

export default router
