<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LayoutDashboard, BookOpen, CalendarDays, ListOrdered, ChartNoAxesCombined, Wallet, MessageSquare, Settings, LogOut, Menu, X, Shield } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { todayDateKey } from '@/utils/date'
import EdgeLogLogo from './EdgeLogLogo.vue'
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const menuOpen = ref(false)
const menuToggle = ref(null)
let mobileQuery
function handleViewportChange(event) {
  if (!event.matches) menuOpen.value = false
}
onMounted(() => {
  mobileQuery = window.matchMedia('(max-width: 768px)')
  mobileQuery.addEventListener('change', handleViewportChange)
})
onUnmounted(() => mobileQuery?.removeEventListener('change', handleViewportChange))
async function closeMenu() {
  menuOpen.value = false
  await nextTick()
  menuToggle.value?.focus()
}
const links = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: `/journal/${todayDateKey()}`, label: 'Today', icon: BookOpen },
  { to: '/journal', label: 'Calendar', icon: CalendarDays, exact: true },
  { to: '/trades', label: 'Trades', icon: ListOrdered },
  { to: '/stats', label: 'Stats', icon: ChartNoAxesCombined },
  { to: '/financials', label: 'Financials', icon: Wallet }
]
watch(() => route.fullPath, () => { menuOpen.value = false })
function isActive(link) {
  return link.exact ? route.path === link.to : route.path === link.to || route.path.startsWith(`${link.to}/`)
}
async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-shell" @keydown.esc="menuOpen && closeMenu()">
    <a class="skip-link" href="#workspace">Skip to content</a>
    <header class="mobile-header">
      <router-link to="/dashboard"><EdgeLogLogo /></router-link>
      <button ref="menuToggle" class="menu-toggle" :aria-expanded="menuOpen" aria-controls="workspace-navigation" :aria-label="menuOpen ? 'Close navigation' : 'Open navigation'" :title="menuOpen ? 'Close navigation' : 'Open navigation'" @click="menuOpen = !menuOpen">
        <component :is="menuOpen ? X : Menu" :size="22" />
      </button>
    </header>
    <nav id="workspace-navigation" class="app-rail" :class="{ 'app-rail--open': menuOpen }" aria-label="Main navigation">
      <router-link to="/dashboard" class="rail-brand"><EdgeLogLogo /></router-link>
      <div class="rail-section"><span class="rail-caption el-label">Workspace</span>
        <router-link v-for="link in links" :key="link.label" :to="link.to" class="rail-link" :class="{ 'rail-link--active': isActive(link) }" :aria-current="isActive(link) ? 'page' : undefined">
          <component :is="link.icon" :size="18" aria-hidden="true" />{{ link.label }}
        </router-link>
      </div>
      <div class="rail-section rail-section--secondary">
        <router-link to="/feedback" class="rail-link" :class="{ 'rail-link--active': route.path === '/feedback' }" :aria-current="route.path === '/feedback' ? 'page' : undefined"><MessageSquare :size="18" />Feedback</router-link>
        <router-link v-if="authStore.user?.is_admin" to="/admin" class="rail-link" :class="{ 'rail-link--active': route.path === '/admin' }" :aria-current="route.path === '/admin' ? 'page' : undefined"><Shield :size="18" />Admin</router-link>
        <router-link to="/settings" class="rail-link" :class="{ 'rail-link--active': route.path === '/settings' }" :aria-current="route.path === '/settings' ? 'page' : undefined"><Settings :size="18" />Settings</router-link>
        <button class="rail-link" @click="handleLogout"><LogOut :size="18" />Logout</button>
      </div>
      <div class="rail-account"><span class="account-mark">E</span><div><strong>EdgeLog</strong><span>Trading journal</span></div></div>
    </nav>
    <main id="workspace" class="app-main" :inert="menuOpen || undefined" tabindex="-1"><slot /></main>
  </div>
</template>

<style scoped>
.app-shell { min-height: 100vh; display: flex; }
.app-rail { position: sticky; top: 0; width: var(--el-rail-width); height: 100dvh; flex: 0 0 var(--el-rail-width); padding: 28px 14px 16px; display: flex; flex-direction: column; gap: 32px; background: var(--el-surface-sunken); border-right: 1px solid var(--el-border); overflow-y: auto; }
.rail-caption { padding: 0 12px 8px; font-size: 10px; letter-spacing: .12em; }
.rail-brand { padding: 0 12px; display: flex; }
.rail-section { display: flex; flex-direction: column; gap: 4px; }
.rail-link { display: flex; align-items: center; gap: 12px; min-height: 42px; padding: 10px 12px; color: var(--el-text-muted); border-radius: 4px; font-size: 14px; font-weight: 500; text-align: left; }
.rail-link:hover { background: var(--el-surface-raised); color: var(--el-text); }
.rail-link--active { background: var(--el-surface-raised); color: var(--el-copper); box-shadow: inset 3px 0 var(--el-copper); }
.rail-section--secondary { margin-top: auto; padding-top: 20px; border-top: 1px solid var(--el-border); }
.rail-account { display: flex; align-items: center; gap: 10px; padding: 0 12px; font-size: 12px; }
.rail-account strong, .rail-account span { display: block; }
.rail-account div span { color: var(--el-text-subtle); }
.account-mark { width: 32px; height: 32px; display: grid !important; place-items: center; background: var(--el-surface-raised); color: var(--el-copper); border-radius: 4px; font-weight: 700; }
.app-main { flex: 1; min-width: 0; }
.mobile-header { display: none; }
.skip-link { position: fixed; top: -100px; left: 16px; z-index: 100; padding: 12px; background: var(--el-surface); }
.skip-link:focus { top: 12px; }
@media (max-width: 768px) {
  .app-shell { display: block; }
  .mobile-header { position: sticky; top: 0; z-index: 30; display: flex; justify-content: space-between; align-items: center; height: 64px; padding: 12px 16px; background: var(--el-surface-sunken); border-bottom: 1px solid var(--el-border); }
  .menu-toggle { display: grid; place-items: center; width: 40px; height: 40px; }
  .app-rail { display: none; position: fixed; top: 64px; left: 0; bottom: 0; z-index: 30; width: 100%; height: calc(100dvh - 64px); padding: 16px; gap: 24px; }
  .app-rail--open { display: flex; }
  .rail-brand { display: none; }
}
</style>
