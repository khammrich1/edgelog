<script setup lang="ts">
import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();

async function handleLogout() {
  await auth.logout();
  router.push({ name: "login" });
}
</script>

<template>
  <nav class="nav-rail">
    <div class="nav-rail__mark">
      <img src="/edgelog-mark.svg" alt="EdgeLog" width="32" height="32" />
    </div>

    <div class="nav-rail__items">
      <RouterLink to="/" class="nav-rail__item" title="Trade Calendar">
        <span class="nav-rail__glyph">TC</span>
      </RouterLink>
    </div>

    <button class="nav-rail__logout" title="Log out" @click="handleLogout">
      <span class="nav-rail__glyph">OUT</span>
    </button>
  </nav>
</template>

<style scoped>
.nav-rail {
  width: var(--nav-rail-width);
  flex-shrink: 0;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-4) 0;
}

.nav-rail__mark {
  margin-bottom: var(--space-6);
}

.nav-rail__items {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  flex: 1;
}

.nav-rail__item,
.nav-rail__logout {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  text-decoration: none;
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
}

.nav-rail__item.router-link-active {
  color: var(--color-accent);
  border-color: var(--color-accent);
  background: rgba(184, 115, 51, 0.1);
}

.nav-rail__item:hover,
.nav-rail__logout:hover {
  color: var(--color-text);
  border-color: var(--color-border);
}

.nav-rail__glyph {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.05em;
}

@media (max-width: 640px) {
  .nav-rail {
    width: 100%;
    height: var(--nav-rail-width);
    flex-direction: row;
    position: fixed;
    bottom: 0;
    left: 0;
    border-right: none;
    border-top: 1px solid var(--color-border);
    padding: 0 var(--space-4);
  }

  .nav-rail__mark {
    margin-bottom: 0;
    margin-right: var(--space-5);
  }

  .nav-rail__items {
    flex-direction: row;
  }
}
</style>
