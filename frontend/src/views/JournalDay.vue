<script setup>
import WorkspaceHeader from '@/components/common/WorkspaceHeader.vue'
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
const eodReflectionDraft = ref('')
const newChecklistLabel = ref('')
const biasChartObjectUrl = ref(null)
const uploadError = ref(null)
const activeTab = ref('mood')
function navigateTabs(event) {
  const tabs = ['mood', 'trades', 'overview']
  const index = tabs.indexOf(activeTab.value)
  let next
  if (event.key === 'ArrowRight') next = (index + 1) % tabs.length
  else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length
  else if (event.key === 'Home') next = 0
  else if (event.key === 'End') next = tabs.length - 1
  else return
  event.preventDefault()
  activeTab.value = tabs[next]
  event.currentTarget.querySelectorAll('[role="tab"]')[next]?.focus()
}
const loading = ref(true)
const loadError = ref(null)

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
  loading.value = true
  loadError.value = null
  try {
    // checklist-items (the user's configured checklist labels) and this
    // day's own record have no data dependency on each other -- awaiting
    // them one after another only adds a full network round-trip to every
    // page load for no reason. Run them concurrently instead (issue #71).
    const [, data] = await Promise.all([
      journalStore.fetchChecklistItems(),
      journalStore.fetchDay(route.params.date)
    ])
    marketBiasDraft.value = data.market_bias ?? ''
    eodReflectionDraft.value = data.eod_reflection ?? ''
    await refreshBiasChartPreview()
  } catch (e) {
    loadError.value = e.response?.data?.detail || 'Could not load this journal.'
  } finally {
    loading.value = false
  }
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

// Issue #73 + #75 follow-up: the Mood/Sleep scale buttons used to
// highlight only once the save round-trip finished (700-1250ms in DEV),
// which reads as a stuck/unresponsive click. #73 fixed that with an
// optimistic update, but a sequence-number guard that only reasserted the
// latest value *after* a stale response had already landed still let a
// slower, now-superseded response (a) briefly flip the displayed
// selection back before the correction ran, and (b), worse, let the
// *persisted* value end up being whichever request's response the server
// happened to finish last rather than whichever was actually clicked
// last.
//
// The fix: serialize each field's own saves so at most one PUT for that
// field is ever in flight at a time. A click that arrives mid-save is
// queued (only the latest queued value survives a burst -- intermediate
// clicks are coalesced away); it's sent only once the current save
// settles. That makes "latest click wins" structurally true for the
// server write itself, not just the display, which also eliminates the
// flicker: no response can ever be "stale" relative to a concurrently
// in-flight one, because there never is a concurrent one.
const fieldSaveError = ref({ sleep_quality: null, mood: null })
const fieldSaving = { sleep_quality: false, mood: false }
const pendingFieldValue = { sleep_quality: undefined, mood: undefined }
// The value currently being persisted for this field (the request actually
// in flight right now) -- used to reassert against a same-burst value,
// distinct from confirmedFieldValue below (the pre-burst baseline, used
// only for rolling back a burst that ultimately fails outright).
const inFlightValue = { sleep_quality: undefined, mood: undefined }
// The last value this field is actually confirmed to hold on the server,
// captured once per save-burst (not per click) so a failed burst rolls
// all the way back to real, known-good data rather than an intermediate,
// never-confirmed click.
const confirmedFieldValue = { sleep_quality: undefined, mood: undefined }

// A field's own in-progress/queued save can still be transiently
// overwritten by the *other* field's updateDay() response, since every
// response replaces the whole currentDay object. Reassert whichever
// field(s) currently have an unsettled optimistic value immediately after
// any response lands, regardless of which field triggered it.
function reassertUnsettledFields(excludeField) {
  if (!journalStore.currentDay) return
  const patch = {}
  for (const field of ['sleep_quality', 'mood']) {
    if (field === excludeField) continue
    if (pendingFieldValue[field] !== undefined) {
      patch[field] = pendingFieldValue[field]
    } else if (fieldSaving[field]) {
      patch[field] = inFlightValue[field]
    }
  }
  if (Object.keys(patch).length) {
    journalStore.currentDay = { ...journalStore.currentDay, ...patch }
  }
}

async function persistField(field, value) {
  fieldSaving[field] = true
  inFlightValue[field] = value
  try {
    await journalStore.updateDay(route.params.date, { [field]: value })
    confirmedFieldValue[field] = value
    // This field's own value is only already correct if nothing newer is
    // queued -- if a click arrived while this request was in flight, this
    // response is for an *older* value and must not be left displayed
    // over the queued one (that was the source of the flicker: this
    // field's own blanket currentDay replacement winning transiently over
    // a newer, not-yet-sent click).
    reassertUnsettledFields(pendingFieldValue[field] === undefined ? field : undefined)
  } catch (e) {
    // A newer click is already queued -- it supersedes this failure
    // entirely and will get its own success/failure outcome next.
    if (pendingFieldValue[field] === undefined) {
      journalStore.currentDay = { ...journalStore.currentDay, [field]: confirmedFieldValue[field] }
      fieldSaveError.value = {
        ...fieldSaveError.value,
        [field]: e.response?.data?.detail || `Could not save ${field === 'mood' ? 'mood' : 'sleep quality'}.`
      }
      reassertUnsettledFields(field)
    } else {
      reassertUnsettledFields()
    }
  } finally {
    fieldSaving[field] = false
    const next = pendingFieldValue[field]
    if (next !== undefined) {
      pendingFieldValue[field] = undefined
      await persistField(field, next)
    }
  }
}

async function setDayField(field, value) {
  if (!fieldSaving[field]) {
    confirmedFieldValue[field] = day.value[field]
  }
  fieldSaveError.value = { ...fieldSaveError.value, [field]: null }
  journalStore.currentDay = { ...journalStore.currentDay, [field]: value }

  if (fieldSaving[field]) {
    pendingFieldValue[field] = value
    return
  }
  await persistField(field, value)
}

function setSleepQuality(value) {
  return setDayField('sleep_quality', value)
}

function setMood(value) {
  return setDayField('mood', value)
}

async function saveMarketBias() {
  await journalStore.updateDay(route.params.date, { market_bias: marketBiasDraft.value })
}

// DF-VS1 (issue #78): explicit no-trade-day marker, distinct from simply
// never having opened the day. A deliberate click, not a rapid-fire scale
// button, so it doesn't need the optimistic/serialized handling above --
// updateDay's blanket currentDay replacement is fine for one-off saves.
async function setIntendedToTrade(value) {
  await journalStore.updateDay(route.params.date, { intended_to_trade: value })
}

async function saveEodReflection() {
  await journalStore.updateDay(route.params.date, { eod_reflection: eodReflectionDraft.value })
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
  <div v-if="loading" class="journal-day el-page el-empty-state" role="status">Loading journal...</div>
  <div v-else-if="loadError" class="journal-day el-page"><p class="el-error-state" role="alert">{{ loadError }}</p><button class="btn-chip" @click="loadDay">Try again</button></div>
  <div v-else-if="day" class="journal-day el-page">
    <button class="back-link" @click="backToCalendar">&lsaquo; Back to Calendar</button>

    <WorkspaceHeader :title="formattedDate" eyebrow="Daily journal">
      <template #status>
        <span class="status-badge" :class="isLocked ? 'status-badge--locked' : 'status-badge--draft'">
          {{ isLocked ? 'Locked' : 'Draft' }}
        </span>
      </template>
      <template #actions>
        <button class="week-link" @click="viewTradesThisWeek">View trades this week &rsaquo;</button>
        <button class="lock-button" :class="{ 'lock-button--locked': isLocked }" @click="toggleLock">
          {{ isLocked ? 'Unlock' : 'Lock' }}
        </button>
      </template>
    </WorkspaceHeader>

    <p v-if="isLocked" class="locked-hint">This day is locked. Unlock it to make changes.</p>

    <div class="day-tabs" role="tablist" aria-label="Journal sections" @keydown="navigateTabs">
      <button
        role="tab"
        class="day-tab"
        :class="{ 'day-tab--active': activeTab === 'mood' }"
        id="mood-tab"
        aria-controls="preparation-panel"
        :tabindex="activeTab === 'mood' ? 0 : -1"
        :aria-selected="activeTab === 'mood'"
        @click="activeTab = 'mood'"
      >
        Mood &amp; Bias
      </button>
      <button
        role="tab"
        class="day-tab"
        :class="{ 'day-tab--active': activeTab === 'trades' }"
        id="trades-tab"
        aria-controls="trades-panel"
        :tabindex="activeTab === 'trades' ? 0 : -1"
        :aria-selected="activeTab === 'trades'"
        @click="activeTab = 'trades'"
      >
        Trades
      </button>
      <button
        role="tab"
        class="day-tab"
        :class="{ 'day-tab--active': activeTab === 'overview' }"
        id="overview-tab"
        aria-controls="overview-panel"
        :tabindex="activeTab === 'overview' ? 0 : -1"
        :aria-selected="activeTab === 'overview'"
        @click="activeTab = 'overview'"
      >
        Overview
      </button>
    </div>

    <div v-show="activeTab === 'mood'" id="preparation-panel" role="tabpanel" aria-labelledby="mood-tab" tabindex="0" class="prep-grid">
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
                  :aria-label="`Sleep quality ${value} of 5`"
                  :aria-pressed="day.sleep_quality === value"
                  @click="setSleepQuality(value)"
                >
                  {{ value }}
                </button>
              </div>
              <p v-if="fieldSaveError.sleep_quality" class="field-save-error">{{ fieldSaveError.sleep_quality }}</p>
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
                  :aria-label="`Mood ${value} of 5`"
                  :aria-pressed="day.mood === value"
                  @click="setMood(value)"
                >
                  {{ value }}
                </button>
              </div>
              <p v-if="fieldSaveError.mood" class="field-save-error">{{ fieldSaveError.mood }}</p>
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
              aria-label="New checklist item"
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
            aria-label="Market bias and thesis"
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

        <section class="el-workstation">
          <div class="el-workstation-header">
            <span class="el-workstation-title">Reflection</span>
          </div>
          <div class="el-field">
            <span class="el-field-label">Did you intend to trade today?</span>
            <div class="intended-to-trade-buttons">
              <button
                type="button"
                class="btn-chip"
                :class="{ 'btn-chip--primary': day.intended_to_trade === true }"
                :disabled="isLocked"
                @click="setIntendedToTrade(true)"
              >
                Trading today
              </button>
              <button
                type="button"
                class="btn-chip"
                :class="{ 'btn-chip--primary': day.intended_to_trade === false }"
                :disabled="isLocked"
                @click="setIntendedToTrade(false)"
              >
                No-trade day
              </button>
            </div>
          </div>
          <label class="el-field-label" for="eod-reflection">End-of-day reflection</label>
          <textarea
            id="eod-reflection"
            v-model="eodReflectionDraft"
            rows="4"
            placeholder="How did today actually go?"
            aria-label="End-of-day reflection"
            :disabled="isLocked"
          ></textarea>
          <button
            class="el-btn-primary"
            :disabled="isLocked || eodReflectionDraft === (day.eod_reflection ?? '')"
            @click="saveEodReflection"
          >
            Save
          </button>
        </section>
      </div>
    </div>

    <div v-show="activeTab === 'trades'" id="trades-panel" role="tabpanel" aria-labelledby="trades-tab" tabindex="0">
      <TradesSection :date="route.params.date" :locked="isLocked" />
    </div>

    <div v-show="activeTab === 'overview'" id="overview-panel" role="tabpanel" aria-labelledby="overview-tab" tabindex="0" class="day-overview">
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


/* One joined action pill (same construction as the tabs/toggles
   elsewhere) rather than two independently-floating controls -- reads as
   a single "workspace actions" area with a divider between its two
   actions, not two unrelated buttons that happen to be near each other. */

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

.day-tabs {
  display: flex;
  gap: var(--el-space-2);
  border-bottom: 1px solid var(--el-border);
  padding: 0;
  margin: var(--el-space-5) 0 var(--el-space-6);
  width: 100%;
  background: transparent;
}

.day-tab {
  padding: 12px 20px;
  min-height: 44px;
  background: none;
  border: none;
  border-radius: 0;
  border-bottom: 2px solid transparent;
  flex: 0 1 auto;
  white-space: nowrap;
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  font-weight: 500;
  font-family: inherit;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: all var(--el-transition-fast);
}

.day-tab:hover {
  color: var(--el-text);
}

.day-tab--active {
  color: var(--el-text);
  border-bottom-color: var(--el-copper);
  background: var(--el-accent-wash);
  font-weight: 600;
}

/* Mood & Bias: a two-column "Prepare" workspace -- Readiness + Checklist
   on the left, the written plan (Bias/Thesis + chart) on the right --
   instead of one long vertical stack of unrelated sections. */
.prep-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--el-space-8);
}

.prep-column {
  display: flex;
  flex-direction: column;
  gap: var(--el-space-6);
  min-width: 0;
}

.prep-column > .el-workstation,
.day-overview > .el-workstation { margin-bottom: 0; }

.readiness-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-6);
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
  border-top: 1px solid var(--el-border);
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
  border-bottom: 1px solid var(--el-border);
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
  max-width: 100%;
}

.scale-button {
  width: 40px;
  height: 40px;
  background-color: var(--el-surface-sunken);
  color: var(--el-text);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  cursor: pointer;
  flex-shrink: 0;
}

.scale-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.scale-button--selected {
  border-color: var(--el-copper);
  color: var(--el-copper);
  background-color: var(--el-accent-wash);
}

.field-save-error {
  color: var(--el-negative);
  font-size: var(--el-text-sm);
  margin: var(--el-space-2) 0 0;
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

.intended-to-trade-buttons {
  display: flex;
  gap: var(--el-space-2);
  margin-top: var(--el-space-2);
  margin-bottom: var(--el-space-3);
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
  .day-tab { padding: 12px 16px; }

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
@media (max-width: 400px) { .day-tab { padding-inline: 12px; flex: 1; } }
</style>
