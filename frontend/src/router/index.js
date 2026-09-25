import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/services/api'
import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'
import Journal from '@/views/Journal.vue'
import JournalDay from '@/views/JournalDay.vue'
import TradeCalendar from '@/views/TradeCalendar.vue'
import Financials from '@/views/Financials.vue'
import Settings from '@/views/Settings.vue'
import Stats from '@/views/Stats.vue'
import Admin from '@/views/Admin.vue'
import Feedback from '@/views/Feedback.vue'
import NotFound from '@/views/NotFound.vue'

export const routes = [
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
  },
  {
    // Constrained to YYYY-MM-DD so a malformed date (or anything else under
    // /journal/) falls through to the catch-all NotFound route below rather
    // than reaching JournalDay with a value it can't parse.
    path: '/journal/:date(\\d{4}-\\d{2}-\\d{2})',
    name: 'JournalDay',
    component: JournalDay,
    meta: { requiresAuth: true }
  },
  {
    // VS4 Trade Calendar -- deliberately not "/calendar" to avoid colliding
    // with the existing "Calendar" nav label, which points at /journal.
    path: '/trades',
    name: 'TradeCalendar',
    component: TradeCalendar,
    meta: { requiresAuth: true }
  },
  {
    // The :date param picks which week to display (any date within it),
    // not a specific day -- gives the calendar deep-linkable week URLs and
    // a link target for the Daily Journal to jump to a trade's week.
    path: '/trades/:date(\\d{4}-\\d{2}-\\d{2})',
    name: 'TradeCalendarWeek',
    component: TradeCalendar,
    meta: { requiresAuth: true }
  },
  {
    // Annual P&L / Financial Tracker -- a separate cash ledger (evals,
    // deposits, expenses vs. payouts), independent of Trade/TradingDay.
    path: '/financials',
    name: 'Financials',
    component: Financials,
    meta: { requiresAuth: true }
  },
  {
    // :year picks which year to display, mirroring TradeCalendarWeek's
    // :date -- deep-linkable year URLs.
    path: '/financials/:year(\\d{4})',
    name: 'FinancialsYear',
    component: Financials,
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings,
    meta: { requiresAuth: true }
  },
  {
    path: '/stats',
    name: 'Stats',
    component: Stats,
    meta: { requiresAuth: true }
  },
  {
    path: '/feedback',
    name: 'Feedback',
    component: Feedback,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: Admin,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    // Catch-all: any route that doesn't match one of the above. Kept behind
    // requiresAuth so an unauthenticated visitor to an unknown URL still
    // goes through the normal login redirect rather than seeing app
    // structure it isn't authenticated for; an authenticated visitor gets
    // the branded Not Found view inside the app shell instead of a blank
    // router-view.
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFound,
    meta: { requiresAuth: true }
  }
]

export function createAppRouter(history) {
  const router = createRouter({ history, routes })

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
    } else if (to.meta.requiresAdmin && !authStore.user?.is_admin) {
      // Non-admin trying to reach an admin-only route
      next('/journal')
    } else {
      next()
    }
  })

  // Site-traffic beacon for the admin page: fire-and-forget on every route
  // change, for logged-in and anonymous visitors alike. A tracking failure
  // must never surface to the user or block navigation.
  router.afterEach((to) => {
    api.post('/track/pageview', { path: to.path }).catch(() => {})
  })

  return router
}

const router = createAppRouter(createWebHistory())

export default router
