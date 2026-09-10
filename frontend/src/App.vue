<template>
  <div id="app">
    <!-- Toast notifications -->
    <div v-if="uiStore.toast" class="toast" :class="`toast--${uiStore.toast.type}`">
      {{ uiStore.toast.message }}
    </div>

    <!-- App shell for authenticated routes -->
    <AppShell v-if="showAppShell">
      <router-view />
    </AppShell>

    <!-- Public routes (login, register) -->
    <router-view v-else />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import AppShell from '@/components/common/AppShell.vue'

const route = useRoute()
const uiStore = useUiStore()

const showAppShell = computed(() => {
  return route.meta.requiresAuth !== false
})
</script>

<style>
@import '@/assets/styles/global.css';

.toast {
  position: fixed;
  top: var(--el-space-6);
  right: var(--el-space-6);
  padding: var(--el-space-4) var(--el-space-6);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-md);
  color: var(--el-text);
  font-size: var(--el-text-sm);
  box-shadow: var(--el-shadow-lg);
  z-index: 1000;
  animation: slideIn 0.3s ease;
}

.toast--success {
  border-left: 3px solid var(--el-positive);
}

.toast--error {
  border-left: 3px solid var(--el-negative);
}

.toast--warning {
  border-left: 3px solid var(--el-warning);
}

.toast--info {
  border-left: 3px solid var(--el-copper);
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
