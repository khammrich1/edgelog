<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import NavRail from "@/components/NavRail.vue";

const route = useRoute();
const showShell = computed(() => route.meta.requiresAuth === true);
</script>

<template>
  <div v-if="showShell" class="shell">
    <NavRail />
    <main class="shell__content">
      <RouterView />
    </main>
  </div>
  <RouterView v-else />
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
}

.shell__content {
  flex: 1;
  min-width: 0;
  padding: var(--space-5);
}

@media (max-width: 640px) {
  .shell {
    flex-direction: column;
  }

  .shell__content {
    padding: var(--space-4);
    padding-bottom: calc(var(--nav-rail-width) + var(--space-4));
  }
}
</style>
