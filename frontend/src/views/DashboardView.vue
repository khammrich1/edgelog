<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
</script>

<template>
  <div class="dashboard">
    <h1 class="dashboard__title">Welcome back</h1>
    <p class="dashboard__subtitle">{{ auth.user?.email }}</p>
    <p class="dashboard__note">
      This is the EdgeLog application shell (VS1 — Foundation). Daily Journal, Trade Calendar, and
      analytics arrive in later vertical slices.
    </p>
  </div>
</template>

<style scoped>
.dashboard__title {
  margin: 0 0 var(--space-1);
  font-size: 22px;
  letter-spacing: 0.04em;
}

.dashboard__subtitle {
  margin: 0 0 var(--space-5);
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 13px;
}

.dashboard__note {
  max-width: 480px;
  color: var(--color-text-muted);
  font-size: 14px;
  line-height: 1.5;
}
</style>
