<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useJournalStore } from '@/stores/journal'
import { useTradesStore } from '@/stores/trades'
import { formatSignedDollars, formatSignedPoints, resultClass } from '@/utils/trades'
import TradesSection from '@/components/journal/TradesSection.vue'

const route = useRoute()
const router = useRouter()
const journalStore = useJournalStore()
const tradesStore = useTradesStore()

const marketBiasDraft = ref('')
const newChecklistLabel = ref('')
const biasChartObjectUrl = ref(null)
const uploadError = ref(null)
const activeTab = ref('mood')

const day = computed(() => journalStore.currentDay)
const isLocked = computed(() => day.value?.status === 'locked')

const biasPreview = computed(() => {
  const bias = day.value?.market_bias?.trim()
  if (!bias) return null
  return bias.length > 60 ? `${bias.slice(0, 60)}…` : bias
})

// Trades themselves are fetched by TradesSection (kept mounted via v-show
// so its data -- and any in-progress form input -- survives switching
// tabs); this just reads the same store's already-loaded state. Shared by
// the Day Summary stats and the Overview trade recap list below.
const overviewTrades = computed(() =>
  (tradesStore.tradesByDate[route.params.date] || []).filter((t) => t.status !== 'canceled')
)

const overviewStats = computed(() => {
  const trades = overviewTrades.value
  const closedTrades = trades.filter((t) => t.status === 'closed')

  let dayPnlDollars = 0
  let hasDollarPnl = false
  let dayPnlPoints = 0
  let wins = 0
  let losses = 0

  for (const trade of trades) {
    // realized_pnl/realized_points only ever reflect exits actually
    // recorded, so summing across still-open trades too is safe -- an
    // open trade's unrealized remainder is never included.
    if (trade.multiplier_known) {
      dayPnlDollars += Number(trade.realized_pnl)
      hasDollarPnl = true
    } else {
      dayPnlPoints += Number(trade.realized_points)
    }
  }

  for (const trade of closedTrades) {
    const result = trade.multiplier_known ? Number(trade.realized_pnl) : Number(trade.realized_points)
    if (result > 0) wins += 1
    else if (result < 0) losses += 1
  }

  return {
    tradeCount: trades.length,
    wins,
    losses,
    dayPnlDollars: hasDollarPnl ? dayPnlDollars : null,
    dayPnlPoints
  }
})

// Per-row result for the Overview trade recap -- only a closed trade has a
// realized result to show; open/canceled-excluded trades show their state
// instead of a fabricated number.
// Single source of the status/multiplier-known branching so the label and
// its color class can never drift out of sync with each other.
function overviewTradeResult(trade) {
  if (trade.status !== 'closed') {
    return { label: 'OPEN', resultClass: '' }
  }
  const value = trade.multiplier_known ? Number(trade.realized_pnl) : Number(trade.realized_points)
  const label = trade.multiplier_known
    ? formatSignedDollars(trade.realized_pnl)
    : `${formatSignedPoints(trade.realized_points)} pts`
  return { label, resultClass: resultClass(value) }
}

const formattedDate = computed(() => {
  // Parsed as local time (not UTC) so the displayed weekday can't shift by
  // a day relative to the URL's date.
  const [year, month, dayOfMonth] = route.params.date.split('-').map(Number)
  const localDate = new Date(year, month - 1, dayOfMonth)
  return localDate.toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
})

async function loadDay() {
  await journalStore.fetchChecklistItems()
  const data = await journalStore.fetchDay(route.params.date)
  marketBiasDraft.value = data.market_bias ?? ''
  await refreshBiasChartPreview()
}

async function refreshBiasChartPreview() {
  revokeBiasChartPreview()
  if (day.value?.has_bias_chart) {
    biasChartObjectUrl.value = await journalStore.fetchBiasChartObjectUrl(route.params.date)
  }
}

function revokeBiasChartPreview() {
  if (biasChartObjectUrl.value) {
    URL.revokeObjectURL(biasChartObjectUrl.value)
    biasChartObjectUrl.value = null
  }
}

async function setSleepQuality(value) {
  await journalStore.updateDay(route.params.date, { sleep_quality: value })
}

async function setMood(value) {
  await journalStore.updateDay(route.params.date, { mood: value })
}

async function saveMarketBias() {
  await journalStore.updateDay(route.params.date, { market_bias: marketBiasDraft.value })
}

async function toggleChecklistItem(itemId, completed) {
  await journalStore.toggleChecklistItem(route.params.date, itemId, completed)
}

async function addChecklistItem() {
  const label = newChecklistLabel.value.trim()
  if (!label) return
  await journalStore.createChecklistItem(label)
  newChecklistLabel.value = ''
  // The new item only becomes part of *this* day's checklist once the day
  // is re-synced against the active item list.
  await journalStore.fetchDay(route.params.date)
}

async function removeChecklistItem(itemId) {
  await journalStore.deleteChecklistItem(itemId)
}

async function toggleLock() {
  if (isLocked.value) {
    await journalStore.unlockDay(route.params.date)
  } else {
    await journalStore.lockDay(route.params.date)
  }
}

async function handleFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return
  uploadError.value = null
  try {
    await journalStore.uploadBiasChart(route.params.date, file)
    await refreshBiasChartPreview()
  } catch (error) {
    uploadError.value = error.response?.data?.detail || 'Could not upload the chart image.'
  } finally {
    event.target.value = ''
  }
}

async function removeBiasChart() {
  await journalStore.deleteBiasChart(route.params.date)
  await refreshBiasChartPreview()
}

function backToCalendar() {
  router.push('/journal')
}

function viewTradesThisWeek() {
  router.push(`/trades/${route.params.date}`)
}

watch(() => route.params.date, loadDay)
loadDay()

onBeforeUnmount(revokeBiasChartPreview)
</script>

<template>
  <div v-if="day" class="journal-day">
    <button class="back-link" @click="backToCalendar">&lsaquo; Back to Calendar</button>

    <div class="workspace-header">
      <div class="workspace-title-group">
        <h1>{{ formattedDate }}</h1>
        <span class="status-badge" :class="isLocked ? 'status-badge--locked' : 'status-badge--draft'">
          {{ isLocked ? 'Locked' : 'Draft' }}
        </span>
      </div>
      <div class="workspace-header-actions">
        <button class="week-link" @click="viewTradesThisWeek">View trades this week &rsaquo;</button>
        <button class="lock-button" :class="{ 'lock-button--locked': isLocked }" @click="toggleLock">
          {{ isLocked ? 'Unlock' : 'Lock' }}
        </button>
      </div>
    </div>

    <p v-if="isLocked" class="locked-hint">This day is locked. Unlock it to make changes.</p>

    <div class="day-tabs el-segmented" role="tablist">
      <button
        role="tab"
        class="day-tab el-segmented-option"
        :class="{ 'day-tab--active el-segmented-option--active': activeTab === 'mood' }"
        :aria-selected="activeTab === 'mood'"
        @click="activeTab = 'mood'"
      >
        Mood &amp; Bias
      </button>
      <button
        role="tab"
        class="day-tab el-segmented-option"
        :class="{ 'day-tab--active el-segmented-option--active': activeTab === 'trades' }"
        :aria-selected="activeTab === 'trades'"
        @click="activeTab = 'trades'"
      >
        Trades
      </button>
      <button
        role="tab"
        class="day-tab el-segmented-option"
        :class="{ 'day-tab--active el-segmented-option--active': activeTab === 'overview' }"
        :aria-selected="activeTab === 'overview'"
        @click="activeTab = 'overview'"
      >
        Overview
      </button>
    </div>

    <div v-show="activeTab === 'mood'" class="prep-grid">
      <div class="prep-column">
        <section class="el-workstation">
          <div class="el-workstation-header">
            <span class="el-workstation-title">Readiness</span>
          </div>
          <div class="readiness-row">
            <div class="el-field">
              <span class="el-field-label">Sleep Quality</span>
              <div class="scale-buttons">
                <button
                  v-for="value in [1, 2, 3, 4, 5]"
                  :key="`sleep-${value}`"
                  class="scale-button"
                  :class="{ 'scale-button--selected': day.sleep_quality === value }"
                  :disabled="isLocked"
                  @click="setSleepQuality(value)"
                >
                  {{ value }}
                </button>
              </div>
            </div>
            <div class="el-field">
              <span class="el-field-label">Mood</span>
              <div class="scale-buttons">
                <button
                  v-for="value in [1, 2, 3, 4, 5]"
                  :key="`mood-${value}`"
                  class="scale-button"
                  :class="{ 'scale-button--selected': day.mood === value }"
                  :disabled="isLocked"
                  @click="setMood(value)"
                >
                  {{ value }}
                </button>
              </div>
            </div>
          </div>
        </section>

        <section class="el-workstation">
          <div class="el-workstation-header">
            <span class="el-workstation-title">Morning Checklist</span>
          </div>
          <ul class="checklist">
            <li v-for="entry in day.checklist" :key="entry.checklist_item_id" class="checklist-row">
              <label class="checklist-label">
                <input
                  type="checkbox"
                  :checked="entry.completed"
                  :disabled="isLocked"
                  @change="toggleChecklistItem(entry.checklist_item_id, $event.target.checked)"
                />
                {{ entry.label }}
              </label>
              <button
                class="remove-item-button"
                :disabled="isLocked"
                title="Remove from checklist"
                @click="removeChecklistItem(entry.checklist_item_id)"
              >
                &times;
              </button>
            </li>
            <li v-if="day.checklist.length === 0" class="el-empty-state checklist-empty">No checklist items yet.</li>
          </ul>
          <form class="add-item-form" @submit.prevent="addChecklistItem">
            <input
              v-model="newChecklistLabel"
              type="text"
              placeholder="Add a checklist item"
              :disabled="isLocked"
              maxlength="200"
            />
            <button type="submit" :disabled="isLocked || !newChecklistLabel.trim()">Add</button>
          </form>
        </section>
      </div>

      <div class="prep-column">
        <section class="el-workstation">
          <div class="el-workstation-header">
            <span class="el-workstation-title">Market Bias / Thesis</span>
          </div>
          <textarea
            v-model="marketBiasDraft"
            rows="5"
            placeholder="What's the plan today?"
            :disabled="isLocked"
          ></textarea>
          <button
            class="el-btn-primary"
            :disabled="isLocked || marketBiasDraft === (day.market_bias ?? '')"
            @click="saveMarketBias"
          >
            Save
          </button>
        </section>

        <section class="el-workstation">
          <div class="el-workstation-header">
            <span class="el-workstation-title">Bias Chart</span>
          </div>
          <img v-if="biasChartObjectUrl" :src="biasChartObjectUrl" alt="Bias chart" class="bias-chart-preview" />
          <p v-if="uploadError" class="upload-error">{{ uploadError }}</p>
          <div class="chart-actions">
            <label class="upload-button" :class="{ 'upload-button--disabled': isLocked }">
              {{ day.has_bias_chart ? 'Replace image' : 'Upload image' }}
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                :disabled="isLocked"
                @change="handleFileSelected"
                hidden
              />
            </label>
            <button v-if="day.has_bias_chart" class="remove-item-button" :disabled="isLocked" @click="removeBiasChart">
              Remove
            </button>
          </div>
        </section>
      </div>
    </div>

    <div v-show="activeTab === 'trades'">
      <TradesSection :date="route.params.date" :locked="isLocked" />
    </div>

    <div v-show="activeTab === 'overview'" class="day-overview">
      <section class="el-workstation">
        <div class="el-workstation-header">
          <span class="el-workstation-title">Day Summary</span>
        </div>
        <div class="overview-stat-row">
          <div class="el-field">
            <span class="el-field-label">Trades</span>
            <span class="overview-value">{{ overviewStats.tradeCount }}</span>
          </div>
          <div class="el-field">
            <span class="el-field-label">Wins</span>
            <span class="overview-value">{{ overviewStats.wins }}</span>
          </div>
          <div class="el-field">
            <span class="el-field-label">Losses</span>
            <span class="overview-value">{{ overviewStats.losses }}</span>
          </div>
          <div class="el-field">
            <span class="el-field-label">Day P&amp;L</span>
            <span
              class="overview-value"
              :class="resultClass(overviewStats.dayPnlDollars ?? overviewStats.dayPnlPoints)"
            >
              <template v-if="overviewStats.dayPnlDollars !== null">
                {{ formatSignedDollars(overviewStats.dayPnlDollars) }}
                <span v-if="overviewStats.dayPnlPoints !== 0" class="overview-value-note">
                  + {{ formatSignedPoints(overviewStats.dayPnlPoints) }} pts (unknown instrument)
                </span>
              </template>
              <template v-else-if="overviewStats.tradeCount > 0">
                {{ formatSignedPoints(overviewStats.dayPnlPoints) }} pts
              </template>
              <template v-else>—</template>
            </span>
          </div>
        </div>
      </section>

      <section class="el-workstation">
        <div class="el-workstation-header">
          <span class="el-workstation-title">Preparation Recap</span>
        </div>
        <div class="overview-stat-row overview-stat-row--prep">
          <div class="el-field">
            <span class="el-field-label">Sleep</span>
            <span class="overview-value">{{ day.sleep_quality ?? '—' }}</span>
          </div>
          <div class="el-field">
            <span class="el-field-label">Mood</span>
            <span class="overview-value">{{ day.mood ?? '—' }}</span>
          </div>
        </div>
        <div class="el-field overview-bias-field">
          <span class="el-field-label">Bias</span>
          <span class="overview-bias-text">{{ biasPreview ?? '—' }}</span>
        </div>
      </section>

      <section class="el-workstation overview-trades-panel">
        <div class="el-workstation-header">
          <span class="el-workstation-title">Trades</span>
        </div>
        <div v-if="overviewTrades.length === 0" class="el-empty-state">No trades logged today.</div>
        <ul v-else class="overview-trade-list">
          <li v-for="trade in overviewTrades" :key="trade.id" class="overview-trade-row">
            <span class="overview-trade-symbol">{{ trade.symbol }}</span>
            <span class="overview-trade-direction" :class="`overview-trade-direction--${trade.direction}`">
              {{ trade.direction === 'long' ? 'LONG' : 'SHORT' }}
            </span>
            <span class="overview-trade-setup">{{ trade.setup || '—' }}</span>
            <span class="overview-trade-result" :class="overviewTradeResult(trade).resultClass">
              {{ overviewTradeResult(trade).label }}
            </span>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style scoped>
.journal-day {
  /* Same composition language approved for the Dashboard in P2: a
     controlled content width with a deliberate side gutter, instead of a
     narrow form floating in the middle of a mostly-empty canvas. */
  padding: var(--el-space-8) var(--el-space-12);
  max-width: 1100px;
  margin: 0 auto;
}

.back-link {
  display: inline-block;
  background: none;
  border: none;
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  cursor: pointer;
  padding: 0;
  margin-bottom: var(--el-space-4);
}

.back-link:hover {
  color: var(--el-copper);
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--el-space-3);
  margin-bottom: var(--el-space-2);
}

/* One joined action pill (same construction as the tabs/toggles
   elsewhere) rather than two independently-floating controls -- reads as
   a single "workspace actions" area with a divider between its two
   actions, not two unrelated buttons that happen to be near each other. */
.workspace-header-actions {
  display: flex;
  align-items: stretch;
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-md);
  overflow: hidden;
}

.week-link {
  display: flex;
  align-items: center;
  background: none;
  border: none;
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  cursor: pointer;
  padding: var(--el-space-2) var(--el-space-4);
  transition: all var(--el-transition-fast);
}

.week-link:hover {
  color: var(--el-copper);
  background-color: var(--el-surface-raised);
}

.workspace-title-group {
  display: flex;
  align-items: center;
  gap: var(--el-space-3);
}

.workspace-header h1 {
  font-size: var(--el-text-2xl);
  margin: 0;
}

.status-badge {
  font-size: var(--el-text-xs);
  font-weight: var(--el-label-weight);
  text-transform: uppercase;
  letter-spacing: var(--el-label-tracking);
  padding: var(--el-space-1) var(--el-space-3);
  border-radius: var(--el-radius-sm);
}

.status-badge--draft {
  color: var(--el-copper);
  border: 1px solid var(--el-copper);
  background-color: rgba(184, 115, 51, 0.1);
}

.status-badge--locked {
  color: var(--el-steel-light);
  border: 1px solid var(--el-steel);
  background-color: var(--el-surface-raised);
}

.lock-button {
  padding: var(--el-space-2) var(--el-space-4);
  background-color: transparent;
  color: var(--el-text);
  border: none;
  border-left: 1px solid var(--el-border);
  font-size: var(--el-text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--el-transition-fast);
}

.lock-button:hover {
  color: var(--el-copper);
  background-color: var(--el-surface-raised);
}

.lock-button--locked {
  color: var(--el-steel-light);
}

.locked-hint {
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  margin-bottom: var(--el-space-6);
}

/* Visuals (background/border/active state) now come from the shared
   .el-segmented/.el-segmented-option primitive (P3.5B) -- only this
   page's own placement stays local. .day-tabs/.day-tab/.day-tab--active
   stay as additional classes purely as stable test hooks. */
.day-tabs {
  margin: var(--el-space-5) 0 var(--el-space-6);
}

/* Mood & Bias: a two-column "Prepare" workspace -- Readiness + Checklist
   on the left, the written plan (Bias/Thesis + chart) on the right --
   instead of one long vertical stack of unrelated sections. */
.prep-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--el-space-6);
}

.prep-column {
  display: flex;
  flex-direction: column;
  gap: var(--el-space-6);
}

.readiness-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-8);
}

.day-overview {
  display: flex;
  flex-direction: column;
  gap: var(--el-space-6);
}

/* Same non-stretching row treatment as the Dashboard's stat rows: a field
   or two forced to fill a wide panel just spreads each value into its own
   pocket of whitespace, so these stay left-aligned at their natural
   width instead. */
.overview-stat-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-6) var(--el-space-8);
}

.overview-stat-row--prep {
  margin-bottom: var(--el-space-5);
}

.overview-value {
  font-size: var(--el-text-xl);
  font-weight: 700;
  color: var(--el-text);
  font-variant-numeric: tabular-nums;
}

.overview-value-note {
  display: block;
  font-size: var(--el-text-xs);
  font-weight: 400;
  color: var(--el-text-muted);
}

.overview-bias-field {
  padding-top: var(--el-space-5);
  border-top: 1px solid var(--el-divider);
}

.overview-bias-text {
  font-size: var(--el-text-sm);
  font-weight: 400;
  color: var(--el-text-muted);
}

.result-positive {
  color: var(--el-positive);
}

.result-negative {
  color: var(--el-negative);
}

.overview-trade-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.overview-trade-row {
  display: grid;
  grid-template-columns: 90px 70px 1fr auto;
  align-items: center;
  gap: var(--el-space-3);
  padding: var(--el-space-3) 0;
  border-bottom: 1px solid var(--el-divider);
  font-size: var(--el-text-sm);
}

.overview-trade-row:last-child {
  border-bottom: none;
}

.overview-trade-symbol {
  font-weight: 700;
  font-family: var(--el-font-mono);
}

.overview-trade-direction {
  font-size: var(--el-text-xs);
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 2px var(--el-space-2);
  border-radius: var(--el-radius-sm);
  width: fit-content;
}

.overview-trade-direction--long {
  color: var(--el-positive);
  border: 1px solid var(--el-positive);
}

.overview-trade-direction--short {
  color: var(--el-negative);
  border: 1px solid var(--el-negative);
}

.overview-trade-setup {
  color: var(--el-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.overview-trade-result {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.checklist-empty {
  padding: var(--el-space-4) 0;
  text-align: left;
}

.checklist {
  list-style: none;
  margin: 0 0 var(--el-space-4);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--el-space-2);
}

.checklist-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--el-space-3);
}

.checklist-label {
  display: flex;
  align-items: center;
  gap: var(--el-space-2);
  font-size: var(--el-text-base);
  color: var(--el-text);
}

.remove-item-button {
  background: none;
  border: none;
  color: var(--el-text-subtle);
  cursor: pointer;
  font-size: var(--el-text-lg);
  line-height: 1;
}

.remove-item-button:hover {
  color: var(--el-negative);
}

.remove-item-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.add-item-form {
  display: flex;
  gap: var(--el-space-2);
}

.add-item-form input {
  flex: 1;
}

.add-item-form button {
  padding: var(--el-space-2) var(--el-space-4);
  background-color: transparent;
  color: var(--el-copper);
  border: 1px solid var(--el-copper);
  border-radius: var(--el-radius-sm);
  cursor: pointer;
}

.add-item-form button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.scale-buttons {
  display: flex;
  gap: var(--el-space-2);
}

.scale-button {
  width: 40px;
  height: 40px;
  background-color: var(--el-surface);
  color: var(--el-text);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  cursor: pointer;
}

.scale-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.scale-button--selected {
  border-color: var(--el-copper);
  color: var(--el-copper);
  background-color: rgba(184, 115, 51, 0.1);
}

.el-workstation textarea {
  width: 100%;
  resize: vertical;
  margin-bottom: var(--el-space-3);
}

.bias-chart-preview {
  max-width: 100%;
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-md);
  margin-bottom: var(--el-space-3);
}

.upload-error {
  color: var(--el-negative);
  font-size: var(--el-text-sm);
  margin: 0 0 var(--el-space-3);
}

.chart-actions {
  display: flex;
  gap: var(--el-space-3);
}

.upload-button {
  padding: var(--el-space-2) var(--el-space-4);
  background-color: transparent;
  color: var(--el-text);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  font-size: var(--el-text-sm);
  cursor: pointer;
}

.upload-button:hover {
  border-color: var(--el-copper);
  color: var(--el-copper);
}

.upload-button--disabled {
  cursor: not-allowed;
  opacity: 0.5;
  pointer-events: none;
}

@media (max-width: 900px) {
  .prep-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .journal-day {
    padding: var(--el-space-4);
  }

  .overview-trade-row {
    grid-template-columns: 1fr auto;
    grid-template-areas:
      'symbol result'
      'direction direction'
      'setup setup';
    row-gap: var(--el-space-1);
  }

  .overview-trade-symbol {
    grid-area: symbol;
  }

  .overview-trade-direction {
    grid-area: direction;
  }

  .overview-trade-setup {
    grid-area: setup;
    white-space: normal;
  }

  .overview-trade-result {
    grid-area: result;
  }
}
</style>
