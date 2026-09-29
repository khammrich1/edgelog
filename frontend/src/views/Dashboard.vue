<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useJournalStore } from '@/stores/journal'
import { useTradesStore } from '@/stores/trades'
import { addDaysToDateKey, eachDateKeyInRange, parseDateKey, startOfWeekDateKey, todayDateKey } from '@/utils/date'
import { summarizeClosedTrades, summaryResultClass, summaryResultLabel } from '@/utils/trades'

const router = useRouter()
const journalStore = useJournalStore()
const tradesStore = useTradesStore()

const error = ref(null)

const today = todayDateKey()
const weekStart = startOfWeekDateKey(today)
// Recent activity looks back further than the current week -- the window
// is sized to comfortably contain the week too, so one fetch of each store
// serves the Today, This Week, and Recent Activity sections without any
// duplicate backend calls.
const RECENT_ACTIVITY_DAYS = 14
const rangeStart = addDaysToDateKey(today, -(RECENT_ACTIVITY_DAYS - 1))

async function load() {
  error.value = null
  try {
    await Promise.all([
      journalStore.fetchDaysInRange(rangeStart, today),
      tradesStore.fetchTradesInWeek(rangeStart, today)
    ])
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not load your dashboard right now.'
  }
}

onMounted(load)

function uniqueSetups(trades) {
  return [...new Set(trades.map((t) => t.setup).filter(Boolean))]
}

function setupTally(trades) {
  const counts = new Map()
  for (const trade of trades) {
    if (!trade.setup) continue
    counts.set(trade.setup, (counts.get(trade.setup) ?? 0) + 1)
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
}

function formatDateLabel(dateKey) {
  const label = parseDateKey(dateKey).toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  })
  return dateKey === today ? `${label} (Today)` : label
}

// ---- Today ----

const todaySummary = computed(() => journalStore.daysByDate[today] ?? null)
const todayTrades = computed(() => tradesStore.tradesByDate[today] ?? [])
const todayResultSummary = computed(() => summarizeClosedTrades(todayTrades.value))
const todaySetups = computed(() => uniqueSetups(todayTrades.value))

// "not_started" is only knowable because /journal/days (a read-only range
// query) never auto-creates a TradingDay the way GET /journal/days/{date}
// does -- so today simply not appearing in daysByDate is a truthful signal,
// not an artifact of a side-effecting fetch.
const todayState = computed(() => todaySummary.value?.status ?? 'not_started')

const todayStatusLabel = computed(() => {
  if (todayState.value === 'draft') return 'Draft'
  if (todayState.value === 'locked') return 'Locked'
  return 'Not Started'
})

const todayBadgeClass = computed(() => (todayState.value === 'draft' ? 'el-badge--accent' : 'el-badge--neutral'))

const todayCta = computed(() => {
  if (todayState.value === 'not_started') return { label: "Start Today's Journal", primary: true }
  if (todayState.value === 'draft') return { label: "Continue Today's Journal", primary: true }
  return { label: "Review Today's Journal", primary: false }
})

function goToToday() {
  router.push(`/journal/${today}`)
}

function openDay(dateKey) {
  router.push(`/journal/${dateKey}`)
}

// A past (not today) day still sitting in draft is the one other place the
// trader most likely needs to go next -- surfaced as a single secondary
// nudge, not a second unrelated shortcut.
const unfinishedPastDay = computed(() =>
  recentDays.value.find((day) => day.date !== today && day.status === 'draft')
)

// ---- This week ----

const weekEnd = addDaysToDateKey(weekStart, 6)
const weekDateKeys = computed(() => eachDateKeyInRange(weekStart, weekEnd).filter((d) => d <= today))
const weekTrades = computed(() => weekDateKeys.value.flatMap((d) => tradesStore.tradesByDate[d] ?? []))
const weekSummary = computed(() => summarizeClosedTrades(weekTrades.value))
const weekResultLabel = computed(() => summaryResultLabel(weekSummary.value))
const weekResultClass = computed(() => summaryResultClass(weekSummary.value))
const weekSetupTally = computed(() => setupTally(weekTrades.value))

// ---- Recent activity ----

const recentDays = computed(() => {
  const keys = eachDateKeyInRange(rangeStart, today).reverse()
  return keys
    .filter((d) => journalStore.daysByDate[d])
    .map((d) => {
      const trades = tradesStore.tradesByDate[d] ?? []
      const summary = summarizeClosedTrades(trades)
      return {
        date: d,
        status: journalStore.daysByDate[d].status,
        tradeCount: trades.length,
        resultLabel: summaryResultLabel(summary),
        resultClass: summaryResultClass(summary),
        setups: uniqueSetups(trades)
      }
    })
})
</script>

<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h1>Dashboard</h1>
      <p class="el-label dashboard-date">
        {{ parseDateKey(today).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' }) }}
      </p>
    </div>

    <p v-if="error" class="el-error-state">{{ error }}</p>

    <template v-else>
      <div class="dashboard-top-grid">
        <section class="el-workstation dashboard-today">
          <div class="el-workstation-header">
            <span class="el-workstation-title">Today</span>
            <span class="el-badge" :class="todayBadgeClass">{{ todayStatusLabel }}</span>
          </div>

          <div class="dashboard-stat-row">
            <div class="el-field">
              <span class="el-field-label">Trades Logged</span>
              <span class="dashboard-stat">{{ todayTrades.length }}</span>
            </div>
            <div class="el-field">
              <span class="el-field-label">Result</span>
              <span class="dashboard-stat" :class="summaryResultClass(todayResultSummary)">
                {{ summaryResultLabel(todayResultSummary) ?? '—' }}
              </span>
            </div>
            <div v-if="todaySummary?.checklist_total_count" class="el-field">
              <span class="el-field-label">Checklist</span>
              <span class="dashboard-stat">
                {{ todaySummary.checklist_completed_count }}/{{ todaySummary.checklist_total_count }}
              </span>
            </div>
          </div>

          <p v-if="todaySetups.length" class="dashboard-setups">
            <span class="el-label">Setup</span> {{ todaySetups.join(', ') }}
          </p>

          <div class="dashboard-next-action">
            <span class="el-label">Next Action</span>
            <div class="dashboard-next-action-buttons">
              <button
                type="button"
                :class="todayCta.primary ? 'el-btn-primary' : 'dashboard-btn-secondary'"
                @click="goToToday"
              >
                {{ todayCta.label }}
              </button>
              <button
                v-if="unfinishedPastDay"
                type="button"
                class="dashboard-btn-link"
                @click="openDay(unfinishedPastDay.date)"
              >
                Also finish reflecting on {{ formatDateLabel(unfinishedPastDay.date) }}
              </button>
            </div>
          </div>
        </section>

        <section class="el-workstation dashboard-snapshot">
          <div class="el-workstation-header">
            <span class="el-workstation-title">This Week</span>
          </div>

          <div v-if="weekSummary.closedCount === 0" class="el-empty-state">No closed trades yet this week.</div>
          <template v-else>
            <div class="dashboard-snapshot-headline" :class="weekResultClass">{{ weekResultLabel }}</div>
            <p v-if="!weekSummary.allMultiplierKnown" class="dashboard-caveat">
              Points-based -- one or more trades this week are missing instrument $ conversion.
            </p>
            <div class="dashboard-stat-row">
              <div class="el-field">
                <span class="el-field-label">Trades</span>
                <span class="dashboard-stat">{{ weekSummary.tradeCount }}</span>
              </div>
              <div class="el-field">
                <span class="el-field-label">Win / Loss / BE</span>
                <span class="dashboard-stat">{{ weekSummary.wins }}/{{ weekSummary.losses }}/{{ weekSummary.breakeven }}</span>
              </div>
            </div>
          </template>

          <div v-if="weekSetupTally.length" class="dashboard-setup-tally">
            <span class="el-label">Setups This Week</span>
            <div class="dashboard-setup-badges">
              <span v-for="s in weekSetupTally" :key="s.name" class="el-badge el-badge--neutral">
                {{ s.name }} &times;{{ s.count }}
              </span>
            </div>
          </div>
        </section>
      </div>

      <section class="el-workstation dashboard-activity">
        <div class="el-workstation-header">
          <span class="el-workstation-title">Recent Activity</span>
        </div>

        <div v-if="recentDays.length === 0" class="el-empty-state">
          No trading days yet. Start today's journal to begin your history.
        </div>

        <ul v-else class="dashboard-activity-list">
          <li v-for="day in recentDays" :key="day.date" class="dashboard-activity-row" @click="openDay(day.date)">
            <span class="dashboard-activity-date">{{ formatDateLabel(day.date) }}</span>
            <span class="el-badge" :class="day.status === 'locked' ? 'el-badge--neutral' : 'el-badge--accent'">
              {{ day.status === 'locked' ? 'Locked' : 'Draft' }}
            </span>
            <span class="dashboard-activity-trades">{{ day.tradeCount }} trade{{ day.tradeCount === 1 ? '' : 's' }}</span>
            <span v-if="day.setups.length" class="dashboard-activity-setups">{{ day.setups.join(', ') }}</span>
            <span class="dashboard-activity-result" :class="day.resultClass">{{ day.resultLabel ?? '—' }}</span>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.dashboard {
  /* Narrower than the shared content-max and with a deliberately generous
     side gutter -- at typical desktop widths this reads as a composed
     workspace instead of stretching edge-to-edge against the rail. */
  padding: var(--el-space-8) var(--el-space-12);
  max-width: 1100px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--el-space-3);
  margin-bottom: var(--el-space-8);
}

.dashboard-header h1 {
  font-size: var(--el-text-2xl);
  margin: 0;
}

.dashboard-date {
  color: var(--el-text-subtle);
}

/* The shared .el-workstation padding is tuned for compact data-entry
   tickets; the Dashboard's panels are read-heavy, not entry forms, so they
   get noticeably more interior breathing room. Scoped to this component
   only -- other .el-workstation usages (trade/financial tickets) are
   untouched. */
.el-workstation {
  padding: var(--el-space-8) var(--el-space-6) var(--el-space-6);
}

.dashboard-top-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--el-space-6);
  margin-bottom: var(--el-space-6);
}

/* Deliberately not a stretching grid -- with a stat or two per panel,
   forcing them to fill the row just spreads each value out into its own
   awkward pocket of whitespace. Left-aligned, content-sized fields read as
   one composed row with a single intentional margin at the end, not a
   spreadsheet. */
.dashboard-stat-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-6) var(--el-space-8);
  margin-bottom: var(--el-space-5);
}

.dashboard-stat-row .el-field {
  flex: 0 0 auto;
  min-width: 80px;
}

.dashboard-stat {
  font-size: var(--el-text-xl);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.dashboard-setups {
  margin: 0 0 var(--el-space-4);
  font-size: var(--el-text-sm);
  color: var(--el-text-muted);
  display: flex;
  gap: var(--el-space-2);
  align-items: baseline;
}

.dashboard-next-action {
  padding-top: var(--el-space-3);
  border-top: 1px solid var(--el-border);
  display: flex;
  flex-direction: column;
  gap: var(--el-space-2);
}

.dashboard-next-action-buttons {
  display: flex;
  align-items: center;
  gap: var(--el-space-4);
  flex-wrap: wrap;
}

.dashboard-btn-secondary {
  padding: var(--el-space-3) var(--el-space-6);
  background-color: transparent;
  color: var(--el-text);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-md);
  font-weight: 600;
  font-size: var(--el-text-sm);
  cursor: pointer;
  transition: border-color var(--el-transition-fast), color var(--el-transition-fast);
}

.dashboard-btn-secondary:hover {
  border-color: var(--el-copper);
  color: var(--el-copper);
}

.dashboard-btn-link {
  background: none;
  border: none;
  padding: 0;
  color: var(--el-text-muted);
  font-size: var(--el-text-xs);
  text-decoration: underline;
  cursor: pointer;
}

.dashboard-btn-link:hover {
  color: var(--el-copper);
}

.dashboard-snapshot-headline {
  font-size: var(--el-text-3xl);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  margin-bottom: var(--el-space-1);
}

.dashboard-caveat {
  margin: 0 0 var(--el-space-4);
  font-size: var(--el-text-xs);
  color: var(--el-text-subtle);
}

.dashboard-setup-tally {
  padding-top: var(--el-space-3);
  border-top: 1px solid var(--el-border);
  display: flex;
  flex-direction: column;
  gap: var(--el-space-2);
}

.dashboard-setup-badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-2);
}

.dashboard-activity-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.dashboard-activity-row {
  display: grid;
  grid-template-columns: 140px 90px 90px 1fr auto;
  align-items: center;
  gap: var(--el-space-4);
  padding: var(--el-space-4) var(--el-space-3);
  border-bottom: 1px solid var(--el-border);
  cursor: pointer;
  transition: background-color var(--el-transition-fast);
}

.dashboard-activity-row:last-child {
  border-bottom: none;
}

.dashboard-activity-row:hover {
  background-color: var(--el-surface-raised);
}

.dashboard-activity-date {
  font-size: var(--el-text-sm);
  color: var(--el-text);
}

.dashboard-activity-trades {
  font-size: var(--el-text-sm);
  color: var(--el-text-muted);
}

.dashboard-activity-setups {
  font-size: var(--el-text-xs);
  color: var(--el-text-subtle);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dashboard-activity-result {
  font-size: var(--el-text-sm);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.result-positive {
  color: var(--el-positive);
}

.result-negative {
  color: var(--el-negative);
}

@media (max-width: 900px) {
  .dashboard-top-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .dashboard {
    padding: var(--el-space-4);
  }

  .el-workstation {
    padding: var(--el-space-5) var(--el-space-4) var(--el-space-4);
  }

  .dashboard-activity-row {
    grid-template-columns: 1fr auto;
    grid-template-areas:
      'date badge'
      'trades result'
      'setups setups';
  }

  .dashboard-activity-date {
    grid-area: date;
  }

  .dashboard-activity-row .el-badge {
    grid-area: badge;
    justify-self: end;
  }

  .dashboard-activity-trades {
    grid-area: trades;
  }

  .dashboard-activity-result {
    grid-area: result;
  }

  .dashboard-activity-setups {
    grid-area: setups;
    white-space: normal;
  }
}
</style>
