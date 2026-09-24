<template>
  <div class="app-shell">
    <nav class="app-nav">
      <EdgeLogLogo />

      <div class="nav-links">
        <button class="nav-link" @click="goToToday">Today</button>
        <router-link to="/journal" class="nav-link">Calendar</router-link>
        <router-link to="/trades" class="nav-link">Trades</router-link>
        <router-link to="/stats" class="nav-link">Stats</router-link>
        <router-link to="/financials" class="nav-link">Financials</router-link>
      </div>

      <div class="nav-spacer"></div>

      <router-link to="/settings" class="nav-settings">Settings</router-link>
      <button @click="handleLogout" class="nav-logout">
        Logout
      </button>
    </nav>

    <main class="app-main">
      <slot />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { todayDateKey } from '@/utils/date'
import EdgeLogLogo from './EdgeLogLogo.vue'

const router = useRouter()
const authStore = useAuthStore()

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}

function goToToday() {
  router.push(`/journal/${todayDateKey()}`)
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-nav {
  height: 64px;
  background-color: var(--el-surface);
  border-bottom: 1px solid var(--el-border);
  padding: 0 var(--el-space-6);
  display: flex;
  align-items: center;
  gap: var(--el-space-6);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: var(--el-space-2);
}

.nav-link {
  padding: var(--el-space-2) var(--el-space-4);
  background-color: transparent;
  color: var(--el-text-muted);
  border: none;
  border-radius: var(--el-radius-sm);
  font-size: var(--el-text-sm);
  font-family: inherit;
  cursor: pointer;
  text-decoration: none;
  transition: all var(--el-transition-fast);
}

.nav-link:hover {
  background-color: var(--el-surface-raised);
  color: var(--el-text);
}

.nav-link.router-link-active {
  color: var(--el-copper);
}

.nav-spacer {
  flex: 1;
}

.nav-settings,
.nav-logout {
  padding: var(--el-space-2) var(--el-space-4);
  background-color: transparent;
  color: var(--el-text-muted);
  border: none;
  border-radius: var(--el-radius-sm);
  font-size: var(--el-text-sm);
  cursor: pointer;
  text-decoration: none;
  transition: all var(--el-transition-fast);
}

.nav-settings:hover,
.nav-logout:hover {
  background-color: var(--el-surface-raised);
  color: var(--el-text);
}

.app-main {
  flex: 1;
  background-color: var(--el-bg);
}

/* Mobile responsive */
@media (max-width: 768px) {
  .app-nav {
    padding: 0 var(--el-space-4);
  }
}
</style>
