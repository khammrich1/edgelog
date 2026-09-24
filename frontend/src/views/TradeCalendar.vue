<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTradesStore } from '@/stores/trades'
import {
  addDaysToDateKey,
  eachDateKeyInRange,
  formatWeekRange,
  parseDateKey,
  startOfWeekDateKey,
  todayDateKey
} from '@/utils/date'
import TradeCalendarCard from '@/components/tradeCalendar/TradeCalendarCard.vue'
import TradeDetailDrawer from '@/components/tradeCalendar/TradeDetailDrawer.vue'

const route = useRoute()
const router = useRouter()
const tradesStore = useTradesStore()

const WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const viewedDate = ref(route.params.date || todayDateKey())
const weekStart = computed(() => startOfWeekDateKey(viewedDate.value))
const weekEnd = computed(() => addDaysToDateKey(weekStart.value, 6))
const heading = computed(() => formatWeekRange(weekStart.value, weekEnd.value))

const weekDays = computed(() =>
  eachDateKeyInRange(weekStart.value, weekEnd.value).map((dateKey, index) => ({
    dateKey,
    weekdayLabel: WEEKDAY_LABELS[index],
    dayNumber: parseDateKey(dateKey).getDate(),
    isToday: dateKey === todayDateKey(),
    trades: tradesStore.tradesByDate[dateKey] ?? []
  }))
)

const selectedTradeId = ref(null)
const selectedTrade = computed(() => {
  if (selectedTradeId.value === null) return null
  for (const day of weekDays.value) {
    const trade = day.trades.find((t) => t.id === selectedTradeId.value)
    if (trade) return { trade, date: day.dateKey }
  }
  return null
})

// Mobile day-focused view: which single day's trades are shown below the
// week-selector strip. Defaults to today if it's in the visible week,
// otherwise the first day of the week.
const focusedDayKey = ref(weekDays.value.find((d) => d.isToday)?.dateKey ?? weekDays.value[0].dateKey)

watch(weekDays, (days) => {
  if (!days.some((d) => d.dateKey === focusedDayKey.value)) {
    focusedDayKey.value = days.find((d) => d.isToday)?.dateKey ?? days[0].dateKey
  }
})

const focusedDay = computed(() => weekDays.value.find((d) => d.dateKey === focusedDayKey.value))

async function fetchWeek() {
  await tradesStore.fetchTradesInWeek(weekStart.value, weekEnd.value)
}

// Using replace (not push) for week navigation keeps browser history from
// filling up with one entry per week click -- the back button leaves
// /trades entirely rather than stepping week-by-week.
function navigateToDate(dateKey) {
  viewedDate.value = dateKey
  router.replace(`/trades/${dateKey}`)
}

function goToPreviousWeek() {
  navigateToDate(addDaysToDateKey(weekStart.value, -7))
}

function goToNextWeek() {
  navigateToDate(addDaysToDateKey(weekStart.value, 7))
}

function goToToday() {
  navigateToDate(todayDateKey())
}

function onJumpToDate(event) {
  if (event.target.value) navigateToDate(event.target.value)
}

function selectTrade(tradeId) {
  selectedTradeId.value = tradeId
}

function closeDrawer() {
  selectedTradeId.value = null
}

watch(
  () => route.params.date,
  (newDate) => {
    if (newDate && newDate !== viewedDate.value) viewedDate.value = newDate
  }
)

watch([weekStart, weekEnd], fetchWeek, { immediate: true })
</script>

<template>
  <div class="trade-calendar">
    <div class="calendar-header">
      <h1>{{ heading }}</h1>
      <div class="calendar-nav">
        <button class="nav-button" @click="goToPreviousWeek" aria-label="Previous week">&lsaquo;</button>
        <button class="nav-button nav-today" @click="goToToday">Today</button>
        <button class="nav-button" @click="goToNextWeek" aria-label="Next week">&rsaquo;</button>
        <input
          type="date"
          class="jump-input"
          :value="viewedDate"
          aria-label="Jump to date"
          @change="onJumpToDate"
        />
      </div>
    </div>

    <!-- Desktop: full 7-column week grid -->
    <div class="week-grid">
      <div v-for="day in weekDays" :key="day.dateKey" class="day-column" :class="{ 'day-column--today': day.isToday }">
        <div class="day-column-header">
          <span class="day-weekday">{{ day.weekdayLabel }}</span>
          <span class="day-number">{{ day.dayNumber }}</span>
        </div>
        <div class="day-column-cards">
          <TradeCalendarCard
            v-for="trade in day.trades"
            :key="trade.id"
            :trade="trade"
            :selected="trade.id === selectedTradeId"
            @select="selectTrade"
          />
        </div>
      </div>
    </div>

    <!-- Mobile: week-selector chip strip + single focused day -->
    <div class="week-chip-strip">
      <button
        v-for="day in weekDays"
        :key="day.dateKey"
        type="button"
        class="week-chip"
        :class="{ 'week-chip--focused': day.dateKey === focusedDayKey, 'week-chip--today': day.isToday }"
        @click="focusedDayKey = day.dateKey"
      >
        <span class="week-chip-label">{{ day.weekdayLabel }}</span>
        <span class="week-chip-number">{{ day.dayNumber }}</span>
        <span v-if="day.trades.length" class="week-chip-dot"></span>
      </button>
    </div>
    <div class="focused-day-cards">
      <TradeCalendarCard
        v-for="trade in focusedDay?.trades ?? []"
        :key="trade.id"
        :trade="trade"
        :selected="trade.id === selectedTradeId"
        @select="selectTrade"
      />
      <p v-if="focusedDay && focusedDay.trades.length === 0" class="empty-day-hint">No trades this day.</p>
    </div>

    <TradeDetailDrawer
      v-if="selectedTrade"
      :trade="selectedTrade.trade"
      :date="selectedTrade.date"
      @close="closeDrawer"
    />
  </div>
</template>

<style scoped>
.trade-calendar {
  padding: var(--el-space-8);
  max-width: 1200px;
  margin: 0 auto;
}

.calendar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--el-space-3);
  margin-bottom: var(--el-space-6);
}

.calendar-header h1 {
  font-size: var(--el-text-2xl);
  margin: 0;
}

.calendar-nav {
  display: flex;
  align-items: center;
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

.jump-input {
  padding: var(--el-space-2) var(--el-space-3);
  background-color: var(--el-surface);
  color: var(--el-text);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  font-size: var(--el-text-sm);
  font-family: inherit;
}

.week-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: var(--el-space-2);
}

.day-column {
  min-height: 120px;
  padding: var(--el-space-2);
  background-color: var(--el-bg);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-md);
}

.day-column--today .day-number {
  color: var(--el-copper);
  font-weight: 600;
}

.day-column-header {
  display: flex;
  align-items: baseline;
  gap: var(--el-space-2);
  margin-bottom: var(--el-space-2);
}

.day-weekday {
  font-size: var(--el-text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--el-text-subtle);
}

.day-number {
  font-size: var(--el-text-sm);
  color: var(--el-text-muted);
}

.day-column-cards {
  display: flex;
  flex-direction: column;
  gap: var(--el-space-2);
}

.week-chip-strip,
.focused-day-cards {
  display: none;
}

@media (max-width: 768px) {
  .trade-calendar {
    padding: var(--el-space-4);
  }

  .week-grid {
    display: none;
  }

  .week-chip-strip {
    display: flex;
    gap: var(--el-space-1);
    overflow-x: auto;
    margin-bottom: var(--el-space-4);
  }

  .week-chip {
    flex: 1 0 auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: var(--el-space-2);
    background-color: var(--el-surface);
    border: 1px solid var(--el-border);
    border-radius: var(--el-radius-sm);
    color: var(--el-text-muted);
    cursor: pointer;
  }

  .week-chip--today {
    color: var(--el-copper);
  }

  .week-chip--focused {
    border-color: var(--el-copper);
  }

  .week-chip-label {
    font-size: var(--el-text-xs);
    text-transform: uppercase;
  }

  .week-chip-number {
    font-size: var(--el-text-sm);
    font-weight: 600;
  }

  .week-chip-dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background-color: var(--el-copper);
  }

  .focused-day-cards {
    display: flex;
    flex-direction: column;
    gap: var(--el-space-2);
  }

  .empty-day-hint {
    color: var(--el-text-subtle);
    font-size: var(--el-text-sm);
  }
}
</style>
