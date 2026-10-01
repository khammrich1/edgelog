<template>
  <div class="app-shell">
    <nav class="app-rail">
      <router-link to="/dashboard" class="rail-brand">
        <EdgeLogLogo />
      </router-link>
      <p class="rail-tagline">Find Your Edge.</p>

      <div class="rail-section">
        <router-link to="/dashboard" class="rail-link">Dashboard</router-link>
        <button class="rail-link rail-link--action" @click="goToToday">Today</button>
        <router-link to="/journal" class="rail-link">Calendar</router-link>
        <router-link to="/trades" class="rail-link">Trades</router-link>
        <router-link to="/stats" class="rail-link">Stats</router-link>
        <router-link to="/financials" class="rail-link">Financials</router-link>
      </div>

      <div class="rail-spacer"></div>

      <div class="rail-section rail-section--secondary">
        <router-link to="/feedback" class="rail-link rail-link--secondary">Feedback</router-link>
        <router-link v-if="authStore.user?.is_admin" to="/admin" class="rail-link rail-link--secondary">
          Admin
        </router-link>
        <router-link to="/settings" class="rail-link rail-link--secondary">Settings</router-link>
        <button class="rail-link rail-link--secondary" @click="handleLogout">Logout</button>
      </div>
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
}

/* Narrow left navigation rail -- the primary "this is EdgeLog" cue. Fixed
   width on desktop; collapses to a horizontal strip on narrow viewports
   (see the media query below) rather than disappearing behind a hamburger,
   since every link here needs to stay reachable in one tap. */
.app-rail {
  width: var(--el-rail-width);
  flex-shrink: 0;
  /* Structural plane, not a content panel -- the rail extends the onyx
     canvas rather than sitting on it as another graphite card (P3.5). */
  background-color: var(--el-surface-sunken);
  border-right: 1px solid var(--el-border);
  padding: var(--el-space-6) var(--el-space-4);
  display: flex;
  flex-direction: column;
  gap: var(--el-space-6);
}

.rail-brand {
  display: flex;
}

.rail-tagline {
  margin-top: calc(var(--el-space-4) * -1);
  font-size: 10px;
  font-weight: var(--el-label-weight);
  text-transform: uppercase;
  letter-spacing: var(--el-label-tracking);
  color: var(--el-steel);
}

.rail-section {
  display: flex;
  flex-direction: column;
  gap: var(--el-space-1);
}

.rail-link {
  display: flex;
  align-items: center;
  width: 100%;
  padding: var(--el-space-2) var(--el-space-3);
  background-color: transparent;
  color: var(--el-text-muted);
  border: none;
  border-radius: var(--el-radius-sm);
  font-family: inherit;
  font-size: var(--el-text-sm);
  font-weight: 500;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
  transition: all var(--el-transition-fast);
}

.rail-link:hover {
  /* A translucent lift (not --el-surface-raised) -- that's tuned for
     hovering content panels, a visibly brighter jump off the much darker
     sunken rail. This stays proportional to the structural plane itself. */
  background-color: rgba(255, 255, 255, 0.06);
  color: var(--el-text);
}

.rail-link.router-link-active {
  color: var(--el-copper);
  background-color: rgba(184, 115, 51, 0.12);
}

.rail-link--action {
  border: 1px solid var(--el-border);
  margin-bottom: var(--el-space-2);
}

.rail-link--action:hover {
  border-color: var(--el-copper);
  color: var(--el-copper);
  background-color: transparent;
}

.rail-spacer {
  flex: 1;
}

.rail-section--secondary {
  /* A quiet internal grouping line, not another hard panel edge. */
  border-top: 1px solid var(--el-divider);
  padding-top: var(--el-space-4);
}

.app-main {
  flex: 1;
  min-width: 0;
  background-color: var(--el-bg);
}

/* Below desktop widths the rail becomes a compact, horizontally scrollable
   top strip instead of a sidebar -- everything above still applies (same
   colors, same active-state treatment), only the axis and a couple of
   spacing rules change. */
@media (max-width: 768px) {
  .app-shell {
    flex-direction: column;
  }

  .app-rail {
    width: 100%;
    flex-direction: row;
    align-items: center;
    gap: var(--el-space-4);
    padding: var(--el-space-2) var(--el-space-4);
    border-right: none;
    border-bottom: 1px solid var(--el-border);
    overflow-x: auto;
  }

  .rail-tagline {
    display: none;
  }

  .rail-section {
    flex-direction: row;
  }

  .rail-link {
    width: auto;
    white-space: nowrap;
  }

  .rail-link--action {
    margin-bottom: 0;
  }

  .rail-spacer {
    display: none;
  }

  .rail-section--secondary {
    border-top: none;
    border-left: 1px solid var(--el-divider);
    padding-top: 0;
    padding-left: var(--el-space-4);
  }
}
</style>
