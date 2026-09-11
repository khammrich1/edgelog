<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useJournalStore } from '@/stores/journal'
import { toDateKey, todayDateKey } from '@/utils/date'

const router = useRouter()
const journalStore = useJournalStore()

const today = new Date()
const viewedMonth = ref(new Date(today.getFullYear(), today.getMonth(), 1))

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
  return cells
})

async function loadMonth() {
  const year = viewedMonth.value.getFullYear()
  const month = viewedMonth.value.getMonth()
  const start = toDateKey(new Date(year, month, 1))
  const end = toDateKey(new Date(year, month + 1, 0))
  await journalStore.fetchDaysInRange(start, end)
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
  <div class="journal-calendar">
    <div class="calendar-header">
      <h1>{{ monthLabel }}</h1>
      <div class="calendar-nav">
        <button class="nav-button" @click="goToPreviousMonth" aria-label="Previous month">&lsaquo;</button>
        <button class="nav-button nav-today" @click="goToToday">Today</button>
        <button class="nav-button" @click="goToNextMonth" aria-label="Next month">&rsaquo;</button>
      </div>
    </div>

    <div class="calendar-grid">
      <div v-for="label in WEEKDAY_LABELS" :key="label" class="weekday-label">{{ label }}</div>

      <div
        v-for="(cell, index) in calendarCells"
        :key="cell ? cell.dateKey : `blank-${index}`"
        class="day-cell"
        :class="{ 'day-cell--blank': !cell, 'day-cell--today': cell?.isToday }"
        @click="cell && openDay(cell.dateKey)"
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
            <span v-if="cell.summary.has_bias_chart" class="chart-indicator" title="Bias chart attached">&#128200;</span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.journal-calendar {
  padding: var(--el-space-8);
  max-width: 900px;
  margin: 0 auto;
}

.calendar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--el-space-6);
}

.calendar-header h1 {
  font-size: var(--el-text-2xl);
  margin: 0;
}

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
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  background-color: var(--el-border);
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
  background-color: var(--el-bg);
  min-height: 84px;
  padding: var(--el-space-2);
  cursor: pointer;
  transition: background-color var(--el-transition-fast);
}

.day-cell:hover {
  background-color: var(--el-surface);
}

.day-cell--blank {
  cursor: default;
  background-color: var(--el-bg);
}

.day-cell--blank:hover {
  background-color: var(--el-bg);
}

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

  .day-cell {
    min-height: 56px;
  }
}
</style>
