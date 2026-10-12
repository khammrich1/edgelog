<script setup>
import WorkspaceHeader from '@/components/common/WorkspaceHeader.vue'
import WorkspaceSummary from '@/components/common/WorkspaceSummary.vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useJournalStore } from '@/stores/journal'
import { toDateKey, todayDateKey } from '@/utils/date'

const router = useRouter()
const journalStore = useJournalStore()

const today = new Date()
const viewedMonth = ref(new Date(today.getFullYear(), today.getMonth(), 1))
const loading = ref(true)
const error = ref(null)
let requestId = 0

const monthLabel = computed(() =>
  viewedMonth.value.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
)

const WEEKDAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

// Leading/trailing blanks pad the grid to whole weeks; day cells carry a
// dateKey and the calendar summary for that day, if one exists.
const calendarCells = computed(() => {
  const year = viewedMonth.value.getFullYear()
  const month = viewedMonth.value.getMonth()
  const firstOfMonth = new Date(year, month, 1)
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const leadingBlanks = firstOfMonth.getDay()

  const cells = []
  for (let i = 0; i < leadingBlanks; i++) {
    cells.push(null)
  }
  for (let day = 1; day <= daysInMonth; day++) {
    const dateKey = toDateKey(new Date(year, month, day))
    cells.push({
      day,
      dateKey,
      isToday: dateKey === todayDateKey(),
      summary: journalStore.daysByDate[dateKey] ?? null
    })
  }
  while (cells.length % 7) cells.push(null)
  return cells
})

const monthSummary = computed(() => {
  const days = calendarCells.value.filter(Boolean).map(cell => cell.summary).filter(Boolean)
  return [
    { label: 'Journal days', value: days.length },
    { label: 'Draft', value: days.filter(day => day.status === 'draft').length },
    { label: 'Locked', value: days.filter(day => day.status === 'locked').length },
    { label: 'With bias chart', value: days.filter(day => day.has_bias_chart).length }
  ]
})

async function loadMonth() {
  const year = viewedMonth.value.getFullYear()
  const month = viewedMonth.value.getMonth()
  const start = toDateKey(new Date(year, month, 1))
  const end = toDateKey(new Date(year, month + 1, 0))
  const id = ++requestId
  loading.value = true
  error.value = null
  try {
    await journalStore.fetchDaysInRange(start, end)
  } catch (e) {
    if (id === requestId) error.value = e.response?.data?.detail || 'Could not load the calendar.'
  } finally {
    if (id === requestId) loading.value = false
  }
}

function goToPreviousMonth() {
  viewedMonth.value = new Date(viewedMonth.value.getFullYear(), viewedMonth.value.getMonth() - 1, 1)
}

function goToNextMonth() {
  viewedMonth.value = new Date(viewedMonth.value.getFullYear(), viewedMonth.value.getMonth() + 1, 1)
}

function goToToday() {
  viewedMonth.value = new Date(today.getFullYear(), today.getMonth(), 1)
}

function openDay(dateKey) {
  router.push(`/journal/${dateKey}`)
}

watch(viewedMonth, loadMonth)
onMounted(loadMonth)
</script>

<template>
  <div class="journal-calendar el-page">
    <WorkspaceHeader :title="monthLabel" eyebrow="Journal calendar" description="Revisit a day, continue a draft, or prepare today's journal.">
      <template #actions>
        <div class="calendar-nav el-toolbar">
          <button class="nav-button" @click="goToPreviousMonth" aria-label="Previous month">&lsaquo;</button>
          <button class="nav-button nav-today" @click="goToToday">Today</button>
          <button class="nav-button" @click="goToNextMonth" aria-label="Next month">&rsaquo;</button>
        </div>
        <button class="el-btn-primary" @click="openDay(todayDateKey())">Open today's journal</button>
      </template>
    </WorkspaceHeader>

    <p v-if="loading" class="el-empty-state" role="status">Loading calendar...</p>
    <div v-else-if="error"><p class="el-error-state" role="alert">{{ error }}</p><button class="btn-chip" @click="loadMonth">Try again</button></div>
    <template v-else>
    <WorkspaceSummary label="Journals in the displayed month" :items="monthSummary" />
    <div class="calendar-legend" aria-label="Calendar legend">
      <span><i class="status-dot status-dot--draft" aria-hidden="true"></i>Draft</span>
      <span><i class="status-dot status-dot--locked" aria-hidden="true"></i>Locked</span>
      <span>Fractions show checklist progress</span>
    </div>
    <div class="calendar-grid">
      <div v-for="label in WEEKDAY_LABELS" :key="label" class="weekday-label">{{ label }}</div>

      <div
        v-for="(cell, index) in calendarCells"
        :key="cell ? cell.dateKey : `blank-${index}`"
        class="day-cell"
        :class="{ 'day-cell--blank': !cell, 'day-cell--today': cell?.isToday, 'day-cell--recorded': !!cell?.summary }"
        :role="cell ? 'link' : undefined"
        :tabindex="cell ? 0 : undefined"
        :aria-current="cell?.isToday ? 'date' : undefined"
        :aria-label="cell ? `Open journal ${cell.dateKey}${cell.summary ? ', ' + cell.summary.status : ''}` : undefined"
        @click="cell && openDay(cell.dateKey)"
        @keydown.enter="cell && openDay(cell.dateKey)"
        @keydown.space.prevent="cell && openDay(cell.dateKey)"
      >
        <template v-if="cell">
          <div class="day-number">{{ cell.day }}</div>
          <div v-if="cell.summary" class="day-indicators">
            <span
              class="status-dot"
              :class="cell.summary.status === 'locked' ? 'status-dot--locked' : 'status-dot--draft'"
              :title="cell.summary.status === 'locked' ? 'Locked' : 'Draft'"
            ></span>
            <span v-if="cell.summary.checklist_total_count > 0" class="checklist-progress">
              {{ cell.summary.checklist_completed_count }}/{{ cell.summary.checklist_total_count }}
            </span>
            <span v-if="cell.summary.has_bias_chart" class="chart-indicator" title="Bias chart attached" aria-label="Bias chart attached">↗</span>
          </div>
          <span v-if="cell.summary" class="day-entry-label">{{ cell.summary.status === 'locked' ? 'Locked journal' : 'Draft journal' }}</span>
        </template>
      </div>
    </div>
    <p class="calendar-note">An empty date means no journal is recorded. It does not indicate a missed trading day.</p>
    </template>
  </div>
</template>

<style scoped>
.calendar-nav {
  display: flex;
  gap: var(--el-space-2);
}

.nav-button {
  padding: var(--el-space-2) var(--el-space-3);
  background-color: var(--el-surface);
  color: var(--el-text);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  font-size: var(--el-text-sm);
  cursor: pointer;
  transition: all var(--el-transition-fast);
}

.nav-button:hover {
  border-color: var(--el-copper);
  color: var(--el-copper);
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 1px;
  background-color: var(--el-divider);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-md);
  overflow: hidden;
}

.weekday-label {
  background-color: var(--el-surface);
  color: var(--el-text-subtle);
  font-size: var(--el-text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  text-align: center;
  padding: var(--el-space-2);
}

.day-cell {
  min-width: 0;
  background-color: var(--el-surface-sunken);
  min-height: 104px;
  position: relative;
  padding: 12px;
  cursor: pointer;
  transition: background-color var(--el-transition-fast);
}

.day-cell:hover {
  background-color: var(--el-surface-raised);
}

.day-cell--blank {
  cursor: default;
  background-color: var(--el-bg);
}

.day-cell--blank:hover {
  background-color: var(--el-bg);
}

.day-cell--recorded { background: var(--el-surface); }
.day-cell--today { box-shadow: inset 0 2px var(--el-copper); }
.day-entry-label { display: block; font-size: 11px; color: var(--el-text-subtle); margin-top: 12px; }
.day-cell:focus-visible { outline-offset: -3px; z-index: 1; }

.day-cell--today .day-number {
  color: var(--el-copper);
  font-weight: 600;
}

.day-number {
  font-size: var(--el-text-sm);
  color: var(--el-text-muted);
}

.day-indicators {
  display: flex;
  align-items: center;
  gap: var(--el-space-1);
  margin-top: var(--el-space-2);
  font-size: var(--el-text-xs);
  color: var(--el-text-subtle);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot--draft {
  background-color: var(--el-copper);
}

.status-dot--locked {
  background-color: var(--el-steel);
}

@media (max-width: 640px) {
  .journal-calendar {
    padding: var(--el-space-4);
  }

  .day-entry-label { display: none; }
  .day-cell {
    padding: 8px 4px;
    min-height: 64px;
  }
}
@media (min-width: 641px) and (max-width: 1000px) { .day-entry-label { display: none; } }
.calendar-legend { display: flex; flex-wrap: wrap; gap: 12px 20px; align-items: center; font-size: 12px; color: var(--el-text-subtle); margin-bottom: 16px; }
.calendar-legend span { display: inline-flex; gap: 8px; align-items: center; }
.calendar-note { color: var(--el-text-subtle); font-size: 12px; margin-top: 16px; }
</style>
