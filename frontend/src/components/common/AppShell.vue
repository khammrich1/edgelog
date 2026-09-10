<template>
  <div class="app-shell">
    <nav class="app-nav">
      <EdgeLogLogo />

      <div class="nav-spacer"></div>

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
import EdgeLogLogo from './EdgeLogLogo.vue'

const router = useRouter()
const authStore = useAuthStore()

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
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

.nav-spacer {
  flex: 1;
}

.nav-logout {
  padding: var(--el-space-2) var(--el-space-4);
  background-color: transparent;
  color: var(--el-text-muted);
  border: none;
  border-radius: var(--el-radius-sm);
  font-size: var(--el-text-sm);
  cursor: pointer;
  transition: all var(--el-transition-fast);
}

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
