<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useTradesStore } from '@/stores/trades'
import { useInstrumentsStore } from '@/stores/instruments'
import { formatPrice, formatSignedDollars, formatSignedPoints, resultClass, SYMBOL_PRESETS } from '@/utils/trades'
import { computeRiskReward, pointsToPrice, priceToPoints } from '@/utils/tradeMath'

const props = defineProps({
  date: { type: String, required: true },
  locked: { type: Boolean, default: false }
})

const tradesStore = useTradesStore()
const instrumentsStore = useInstrumentsStore()

const trades = computed(() => tradesStore.tradesByDate[props.date] || [])
const expandedTradeId = ref(null)
const editingTradeId = ref(null)
const editingExitId = ref(null)
const showMoreFields = ref(false)
const submitError = ref(null)
// 'preset' shows the symbol dropdown; 'custom' shows a free-text field for
// any symbol not in SYMBOL_PRESETS -- the backend accepts either.
const symbolEntryMode = ref('preset')
// Same preset/custom split as the symbol field, but sourced from the
// user's configured trade setups (Settings page) instead of a fixed list.
// Starts 'custom' until setups load so the field never renders an empty
// dropdown before we know whether any setups are configured.
const setupEntryMode = ref('custom')
// Stop/target can be entered as an absolute price or a points distance from
// entry; whichever mode isn't active still keeps its own last-typed value
// (see tradeMath.js) so toggling never silently discards what was typed.
const stopMode = ref('price')
const targetMode = ref('price')

// Screenshot capture: extraction only prefills the form below for the user
// to review -- it never creates a trade on its own.
const screenshotState = ref('idle') // idle | loading | error
const screenshotError = ref(null)
const extractionHint = ref(null)
const dragActive = ref(false)
const fileInput = ref(null)

function applyExtraction(extracted) {
  if (extracted.symbol) {
    if (SYMBOL_PRESETS.includes(extracted.symbol)) {
      symbolEntryMode.value = 'preset'
    } else {
      symbolEntryMode.value = 'custom'
    }
    tradeForm.symbol = extracted.symbol
  }
  if (extracted.direction) tradeForm.direction = extracted.direction
  if (extracted.initial_quantity != null) tradeForm.initial_quantity = String(extracted.initial_quantity)
  if (extracted.entry_price != null) tradeForm.entry_price = String(extracted.entry_price)
  if (extracted.stop_price != null) {
    tradeForm.stop_price = String(extracted.stop_price)
    stopMode.value = 'price'
  }
  if (extracted.target_price != null) {
    tradeForm.target_price = String(extracted.target_price)
    targetMode.value = 'price'
    showMoreFields.value = true
  }
  extractionHint.value = extracted.notes || null
}

async function handleScreenshotFile(file) {
  if (!file) return
  screenshotState.value = 'loading'
  screenshotError.value = null
  try {
    const extracted = await tradesStore.parseScreenshot(file)
    applyExtraction(extracted)
    screenshotState.value = 'idle'
  } catch (error) {
    screenshotError.value = error.response?.data?.detail || 'Could not read that screenshot. Enter the trade manually below.'
    screenshotState.value = 'error'
  }
}

function onFilePicked(event) {
  const file = event.target.files?.[0]
  handleScreenshotFile(file)
  event.target.value = ''
}

function onDrop(event) {
  dragActive.value = false
  const file = event.dataTransfer?.files?.[0]
  handleScreenshotFile(file)
}

function onPaste(event) {
  const item = Array.from(event.clipboardData?.items || []).find((i) => i.type.startsWith('image/'))
  if (item) {
    handleScreenshotFile(item.getAsFile())
  }
}

function handleSymbolPresetChange(value) {
  if (value === '__custom__') {
    symbolEntryMode.value = 'custom'
    tradeForm.symbol = ''
  } else {
    tradeForm.symbol = value
  }
}

function switchToPresetList() {
  symbolEntryMode.value = 'preset'
  tradeForm.symbol = ''
}

function handleSetupPresetChange(value) {
  if (value === '__custom__') {
    setupEntryMode.value = 'custom'
    tradeForm.setup = ''
  } else {
    tradeForm.setup = value
  }
}

function switchToSetupPresetList() {
  setupEntryMode.value = 'preset'
  tradeForm.setup = ''
}

function resetSetupEntryMode() {
  setupEntryMode.value = tradesStore.setups.length > 0 ? 'preset' : 'custom'
}

function nowForDateTimeLocal() {
  return toDateTimeLocal(new Date())
}

function toDateTimeLocal(date) {
  const d = new Date(date)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function emptyTradeForm() {
  return {
    symbol: '',
    direction: 'long',
    initial_quantity: '',
    entry_price: '',
    stop_price: '',
    stop_points: '',
    entry_time: nowForDateTimeLocal(),
    target_price: '',
    target_points: '',
    setup: '',
    notes: ''
  }
}

const tradeForm = reactive(emptyTradeForm())

// The price actually submitted, regardless of which representation
// (price/points) is currently being edited -- see stopMode/targetMode.
const effectiveStopPrice = computed(() =>
  stopMode.value === 'price'
    ? tradeForm.stop_price || null
    : pointsToPrice(tradeForm.entry_price, tradeForm.stop_points, tradeForm.direction, 'stop')
)
const effectiveTargetPrice = computed(() =>
  targetMode.value === 'price'
    ? tradeForm.target_price || null
    : pointsToPrice(tradeForm.entry_price, tradeForm.target_points, tradeForm.direction, 'target')
)

// Shows the converted counterpart of whichever representation is active,
// without ever overwriting what the user actually typed.
const stopConversionHint = computed(() => {
  if (stopMode.value === 'price') {
    const pts = priceToPoints(tradeForm.entry_price, tradeForm.stop_price, tradeForm.direction, 'stop')
    return pts !== null ? `≈ ${pts} pts` : null
  }
  return effectiveStopPrice.value !== null ? `≈ ${formatPrice(effectiveStopPrice.value)}` : null
})
const targetConversionHint = computed(() => {
  if (targetMode.value === 'price') {
    const pts = priceToPoints(tradeForm.entry_price, tradeForm.target_price, tradeForm.direction, 'target')
    return pts !== null ? `≈ ${pts} pts` : null
  }
  return effectiveTargetPrice.value !== null ? `≈ ${formatPrice(effectiveTargetPrice.value)}` : null
})

const riskRewardPreview = computed(() =>
  computeRiskReward({
    quantity: tradeForm.initial_quantity,
    entryPrice: tradeForm.entry_price,
    stopPrice: effectiveStopPrice.value,
    targetPrice: effectiveTargetPrice.value,
    direction: tradeForm.direction,
    multiplier: instrumentsStore.getMultiplier(tradeForm.symbol)
  })
)
const exitForms = reactive({}) // tradeId -> { quantity, exit_price, exit_time }
const entryForms = reactive({}) // tradeId -> { quantity, entry_price, entry_time }

function exitFormFor(tradeId) {
  if (!exitForms[tradeId]) {
    exitForms[tradeId] = { quantity: '', exit_price: '', exit_time: nowForDateTimeLocal() }
  }
  return exitForms[tradeId]
}

function entryFormFor(tradeId) {
  if (!entryForms[tradeId]) {
    entryForms[tradeId] = { quantity: '', entry_price: '', entry_time: nowForDateTimeLocal() }
  }
  return entryForms[tradeId]
}

const editExitForms = reactive({}) // exitId -> { quantity, exit_price, exit_time }

function startEditExit(exit) {
  editExitForms[exit.id] = {
    quantity: exit.quantity,
    exit_price: Number(exit.exit_price),
    exit_time: toDateTimeLocal(exit.exit_time)
  }
  editingExitId.value = exit.id
}

function cancelEditExit() {
  editingExitId.value = null
}

async function submitEditExit(trade, exit) {
  const form = editExitForms[exit.id]
  try {
    await tradesStore.updateExit(props.date, trade.id, exit.id, {
      quantity: Number(form.quantity),
      exit_price: form.exit_price,
      exit_time: new Date(form.exit_time).toISOString()
    })
    editingExitId.value = null
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Could not update that trim.')
  }
}

const editTradeForms = reactive({}) // tradeId -> full trade field set

function startEditTrade(trade) {
  editTradeForms[trade.id] = {
    symbol: trade.symbol,
    direction: trade.direction,
    initial_quantity: trade.initial_quantity,
    entry_price: Number(trade.entry_price),
    entry_time: toDateTimeLocal(trade.entry_time),
    stop_price: trade.stop_price !== null ? Number(trade.stop_price) : '',
    target_price: trade.target_price !== null ? Number(trade.target_price) : '',
    setup: trade.setup ?? '',
    notes: trade.notes ?? ''
  }
  editingTradeId.value = trade.id
}

function cancelEditTrade() {
  editingTradeId.value = null
}

async function submitEditTrade(trade) {
  const form = editTradeForms[trade.id]
  try {
    await tradesStore.updateTrade(props.date, trade.id, {
      symbol: form.symbol.trim(),
      direction: form.direction,
      initial_quantity: Number(form.initial_quantity),
      entry_price: form.entry_price,
      entry_time: new Date(form.entry_time).toISOString(),
      stop_price: form.stop_price || null,
      target_price: form.target_price || null,
      setup: form.setup || null,
      notes: form.notes || null
    })
    editingTradeId.value = null
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Could not update that trade.')
  }
}

async function loadTrades() {
  await tradesStore.fetchTrades(props.date)
}

async function submitNewTrade() {
  submitError.value = null
  const payload = {
    symbol: tradeForm.symbol.trim(),
    direction: tradeForm.direction,
    initial_quantity: Number(tradeForm.initial_quantity),
    entry_price: tradeForm.entry_price,
    entry_time: new Date(tradeForm.entry_time).toISOString(),
    stop_price: effectiveStopPrice.value,
    target_price: effectiveTargetPrice.value,
    setup: tradeForm.setup || null,
    notes: tradeForm.notes || null
  }
  try {
    await tradesStore.createTrade(props.date, payload)
    Object.assign(tradeForm, emptyTradeForm())
    symbolEntryMode.value = 'preset'
    resetSetupEntryMode()
    stopMode.value = 'price'
    targetMode.value = 'price'
    showMoreFields.value = false
    extractionHint.value = null
    screenshotError.value = null
  } catch (error) {
    submitError.value = error.response?.data?.detail || 'Could not save that trade.'
  }
}

function toggleExpand(tradeId) {
  expandedTradeId.value = expandedTradeId.value === tradeId ? null : tradeId
}

async function submitExit(trade) {
  const form = exitFormFor(trade.id)
  try {
    await tradesStore.addExit(props.date, trade.id, {
      quantity: Number(form.quantity),
      exit_price: form.exit_price,
      exit_time: new Date(form.exit_time).toISOString()
    })
    delete exitForms[trade.id]
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Could not save that exit.')
  }
}

async function removeExit(trade, exit) {
  if (!window.confirm(`Remove the ${exit.quantity} @ ${exit.exit_price} exit? This cannot be undone.`)) return
  await tradesStore.deleteExit(props.date, trade.id, exit.id)
}

async function submitEntry(trade) {
  const form = entryFormFor(trade.id)
  try {
    await tradesStore.addEntry(props.date, trade.id, {
      quantity: Number(form.quantity),
      entry_price: form.entry_price,
      entry_time: new Date(form.entry_time).toISOString()
    })
    delete entryForms[trade.id]
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Could not add that entry.')
  }
}

async function removeEntry(trade, entry) {
  if (!window.confirm(`Remove the ${entry.quantity} @ ${entry.entry_price} entry? This cannot be undone.`)) return
  await tradesStore.deleteEntry(props.date, trade.id, entry.id)
}

async function stopHit(trade) {
  if (
    !window.confirm(
      `Mark stop hit? This exits the remaining ${trade.remaining_quantity} @ ${trade.stop_price}.`
    )
  )
    return
  try {
    await tradesStore.addExit(props.date, trade.id, {
      quantity: trade.remaining_quantity,
      exit_price: trade.stop_price,
      exit_time: new Date().toISOString()
    })
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Could not record the stop-hit exit.')
  }
}

async function targetHit(trade) {
  if (
    !window.confirm(
      `Mark target hit? This exits the remaining ${trade.remaining_quantity} @ ${trade.target_price}.`
    )
  )
    return
  try {
    await tradesStore.addExit(props.date, trade.id, {
      quantity: trade.remaining_quantity,
      exit_price: trade.target_price,
      exit_time: new Date().toISOString()
    })
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Could not record the target-hit exit.')
  }
}

async function cancelTradeAction(trade) {
  if (!window.confirm(`Cancel this ${trade.symbol} trade? It will be kept but excluded from P&L.`)) return
  try {
    await tradesStore.cancelTrade(props.date, trade.id)
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Could not cancel that trade.')
  }
}

async function removeTrade(trade) {
  if (!window.confirm(`Delete this ${trade.symbol} trade and all of its exits? This cannot be undone.`)) return
  await tradesStore.deleteTrade(props.date, trade.id)
}

watch(() => props.date, loadTrades)
onMounted(async () => {
  loadTrades()
  instrumentsStore.fetchMultipliers()
  await tradesStore.fetchSetups()
  resetSetupEntryMode()
})
</script>

<template>
  <section class="trades-section">
    <h2>Trades</h2>

    <ul class="trade-list">
      <li v-for="trade in trades" :key="trade.id" class="trade-card" :class="`trade-card--${trade.status}`">
        <div class="trade-card__header" @click="toggleExpand(trade.id)">
          <div class="trade-card__title">
            <span class="trade-card__symbol">{{ trade.symbol }}</span>
            <span class="trade-direction" :class="`trade-direction--${trade.direction}`">
              {{ trade.direction === 'long' ? 'LONG' : 'SHORT' }}
            </span>
            <span class="trade-status" :class="`trade-status--${trade.status}`">{{ trade.status.toUpperCase() }}</span>
          </div>
          <div class="trade-card__summary-right">
            <span v-if="trade.status === 'open'" class="trade-remaining">Remaining {{ trade.remaining_quantity }}</span>
            <template v-else-if="trade.status === 'closed'">
              <span v-if="trade.multiplier_known" class="trade-result" :class="resultClass(trade.realized_pnl)">
                {{ formatSignedDollars(trade.realized_pnl) }}
              </span>
              <span v-else class="trade-result" :class="resultClass(trade.realized_points)">
                {{ formatSignedPoints(trade.realized_points) }} pts
              </span>
            </template>
          </div>
        </div>

        <div v-if="expandedTradeId === trade.id" class="trade-card__body">
          <p v-if="trade.status === 'canceled'" class="canceled-hint">Canceled -- excluded from P&L.</p>

          <div class="trade-card__info">
            <div class="info-item">
              <span class="info-label">Entry</span>
              <span class="info-value">{{ formatPrice(trade.average_entry_price) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Contracts</span>
              <span class="info-value">{{ trade.total_quantity }}</span>
            </div>
            <div v-if="trade.stop_price" class="info-item">
              <span class="info-label">Stop</span>
              <span class="info-value info-value--negative">{{ formatPrice(trade.stop_price) }}</span>
            </div>
            <div v-if="trade.target_price" class="info-item">
              <span class="info-label">Target</span>
              <span class="info-value info-value--positive">{{ formatPrice(trade.target_price) }}</span>
            </div>
            <div v-if="trade.setup" class="info-item">
              <span class="info-label">Setup</span>
              <span class="info-value">{{ trade.setup }}</span>
            </div>
            <div v-if="trade.planned_risk_dollars || trade.planned_risk_points" class="info-item">
              <span class="info-label">Planned risk</span>
              <span class="info-value">
                <template v-if="trade.planned_risk_dollars">${{ formatPrice(trade.planned_risk_dollars) }}</template>
                <template v-else>{{ formatPrice(trade.planned_risk_points) }} pts</template>
              </span>
            </div>
          </div>

          <p v-if="trade.notes" class="trade-notes">{{ trade.notes }}</p>

          <div v-if="trade.entries.length" class="trade-card__section">
            <div class="trade-card__section-label">Entries</div>
            <ul class="exit-list">
              <li class="exit-row">
                <span>{{ trade.initial_quantity }} @ {{ formatPrice(trade.entry_price) }} <small>(original)</small></span>
              </li>
              <li v-for="entry in trade.entries" :key="entry.id" class="exit-row">
                <span>{{ entry.quantity }} @ {{ formatPrice(entry.entry_price) }}</span>
                <button class="remove-item-button" :disabled="locked" @click="removeEntry(trade, entry)">&times;</button>
              </li>
            </ul>
          </div>

          <div v-if="trade.exits.length" class="trade-card__section">
            <div class="trade-card__section-label">Trims</div>
            <ul class="exit-list">
              <li v-for="exit in trade.exits" :key="exit.id" class="exit-row">
                <form v-if="editingExitId === exit.id" class="exit-form exit-edit-form" @submit.prevent="submitEditExit(trade, exit)">
                  <input v-model="editExitForms[exit.id].quantity" type="number" min="1" required />
                  <input v-model="editExitForms[exit.id].exit_price" type="number" step="any" required />
                  <input v-model="editExitForms[exit.id].exit_time" type="datetime-local" required />
                  <button type="submit">Save</button>
                  <button type="button" @click="cancelEditExit">Cancel</button>
                </form>
                <template v-else>
                  <span>{{ exit.quantity }} @ {{ formatPrice(exit.exit_price) }}</span>
                  <span class="exit-row-actions">
                    <button
                      v-if="!locked"
                      class="remove-item-button edit-item-button"
                      title="Edit trim"
                      @click="startEditExit(exit)"
                    >
                      ✎
                    </button>
                    <button class="remove-item-button" :disabled="locked" @click="removeExit(trade, exit)">&times;</button>
                  </span>
                </template>
              </li>
            </ul>
          </div>

          <template v-if="trade.status === 'open' && !locked">
            <form class="exit-form" @submit.prevent="submitEntry(trade)">
              <input v-model="entryFormFor(trade.id).quantity" type="number" min="1" placeholder="Qty" required />
              <input
                v-model="entryFormFor(trade.id).entry_price"
                type="number"
                step="any"
                placeholder="Entry price"
                required
              />
              <input v-model="entryFormFor(trade.id).entry_time" type="datetime-local" required />
              <button type="submit">Add contracts</button>
            </form>

            <form class="exit-form" @submit.prevent="submitExit(trade)">
              <input
                v-model="exitFormFor(trade.id).quantity"
                type="number"
                min="1"
                :max="trade.remaining_quantity"
                placeholder="Qty"
                required
              />
              <input v-model="exitFormFor(trade.id).exit_price" type="number" step="any" placeholder="Exit price" required />
              <input v-model="exitFormFor(trade.id).exit_time" type="datetime-local" required />
              <button type="submit">Add trim</button>
            </form>

            <div class="quick-exit-buttons">
              <button v-if="trade.target_price" type="button" class="toggle-more-button" @click="targetHit(trade)">
                Target hit
              </button>
              <button v-if="trade.stop_price" type="button" class="toggle-more-button" @click="stopHit(trade)">
                Stop hit
              </button>
            </div>
          </template>

          <div v-if="editingTradeId === trade.id" class="trade-card__section">
            <div class="trade-card__section-label">Edit trade</div>
            <div class="trade-form-secondary">
              <input v-model="editTradeForms[trade.id].symbol" type="text" placeholder="Symbol" maxlength="20" required />
              <select v-model="editTradeForms[trade.id].direction">
                <option value="long">Long</option>
                <option value="short">Short</option>
              </select>
              <input v-model="editTradeForms[trade.id].initial_quantity" type="number" min="1" placeholder="Qty" required />
              <input
                v-model="editTradeForms[trade.id].entry_price"
                type="number"
                step="any"
                placeholder="Entry"
                required
              />
              <input v-model="editTradeForms[trade.id].entry_time" type="datetime-local" required />
              <input v-model="editTradeForms[trade.id].stop_price" type="number" step="any" placeholder="Stop" />
              <input v-model="editTradeForms[trade.id].target_price" type="number" step="any" placeholder="Target" />
              <input v-model="editTradeForms[trade.id].setup" type="text" placeholder="Setup" maxlength="200" />
              <textarea v-model="editTradeForms[trade.id].notes" rows="2" placeholder="Notes"></textarea>
            </div>
            <div class="trade-card__edit-actions">
              <button type="button" class="btn-chip btn-chip--ghost" @click="cancelEditTrade">Cancel</button>
              <button type="button" class="btn-chip btn-chip--primary" @click="submitEditTrade(trade)">Save changes</button>
            </div>
          </div>

          <div class="trade-card__actions">
            <button
              v-if="editingTradeId !== trade.id"
              class="btn-chip btn-chip--ghost"
              :disabled="locked"
              @click="startEditTrade(trade)"
            >
              Edit trade
            </button>
            <button
              v-if="trade.status === 'open' && trade.exits.length === 0 && trade.entries.length === 0"
              class="btn-chip btn-chip--warning"
              :disabled="locked"
              @click="cancelTradeAction(trade)"
            >
              Cancel trade
            </button>
            <button class="btn-chip btn-chip--danger" :disabled="locked" @click="removeTrade(trade)">
              Delete trade
            </button>
          </div>
        </div>
      </li>
    </ul>

    <form v-if="!locked" class="trade-form" @submit.prevent="submitNewTrade">
      <div
        class="screenshot-dropzone"
        :class="{ 'screenshot-dropzone--active': dragActive, 'screenshot-dropzone--loading': screenshotState === 'loading' }"
        tabindex="0"
        @dragover.prevent="dragActive = true"
        @dragleave.prevent="dragActive = false"
        @drop.prevent="onDrop"
        @paste="onPaste"
      >
        <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" class="screenshot-input" @change="onFilePicked" />
        <span v-if="screenshotState === 'loading'">Reading screenshot…</span>
        <span v-else>
          Drop or paste a trade screenshot, or
          <button type="button" class="screenshot-browse-button" @click="fileInput.click()">browse a file</button>
        </span>
      </div>
      <p v-if="screenshotError" class="submit-error">{{ screenshotError }}</p>
      <p v-if="extractionHint" class="extraction-hint">Note: {{ extractionHint }}</p>

      <div class="trade-form-primary">
        <select
          v-if="symbolEntryMode === 'preset'"
          :value="tradeForm.symbol"
          required
          @change="handleSymbolPresetChange($event.target.value)"
        >
          <option value="" disabled>Symbol</option>
          <option v-for="symbol in SYMBOL_PRESETS" :key="symbol" :value="symbol">{{ symbol }}</option>
          <option value="__custom__">Other…</option>
        </select>
        <span v-else class="custom-symbol">
          <input v-model="tradeForm.symbol" type="text" placeholder="Symbol" maxlength="20" required />
          <button type="button" class="toggle-more-button" @click="switchToPresetList">Use list</button>
        </span>
        <div class="direction-toggle" role="group" aria-label="Direction">
          <button
            type="button"
            class="direction-toggle-btn direction-toggle-btn--long"
            :class="{ 'direction-toggle-btn--active': tradeForm.direction === 'long' }"
            @click="tradeForm.direction = 'long'"
          >
            LONG
          </button>
          <button
            type="button"
            class="direction-toggle-btn direction-toggle-btn--short"
            :class="{ 'direction-toggle-btn--active': tradeForm.direction === 'short' }"
            @click="tradeForm.direction = 'short'"
          >
            SHORT
          </button>
        </div>
        <input v-model="tradeForm.initial_quantity" type="number" min="1" placeholder="Qty" required />
        <input v-model="tradeForm.entry_price" type="number" step="any" placeholder="Entry" required />
        <span class="price-points-field">
          <input
            v-if="stopMode === 'price'"
            v-model="tradeForm.stop_price"
            type="number"
            step="any"
            placeholder="Stop"
          />
          <input v-else v-model="tradeForm.stop_points" type="number" step="any" placeholder="Stop pts" />
          <span class="price-points-toggle">
            <button type="button" :class="{ active: stopMode === 'price' }" @click="stopMode = 'price'">
              Price
            </button>
            <button type="button" :class="{ active: stopMode === 'points' }" @click="stopMode = 'points'">
              Points
            </button>
          </span>
          <span v-if="stopConversionHint" class="conversion-hint">{{ stopConversionHint }}</span>
        </span>
        <button type="submit">Add trade</button>
      </div>

      <p v-if="riskRewardPreview" class="rr-preview">
        {{ riskRewardPreview.quantity }} {{ tradeForm.symbol || 'contracts' }}
        <template v-if="riskRewardPreview.riskPoints !== null">
          | Risk: {{ riskRewardPreview.riskPoints }} pts<template v-if="riskRewardPreview.riskDollars !== null">
            / ${{ formatPrice(riskRewardPreview.riskDollars) }}</template
          >
        </template>
        <template v-if="riskRewardPreview.rewardPoints !== null">
          | Reward: {{ riskRewardPreview.rewardPoints }} pts<template v-if="riskRewardPreview.rewardDollars !== null">
            / ${{ formatPrice(riskRewardPreview.rewardDollars) }}</template
          >
        </template>
        <template v-if="riskRewardPreview.rrRatio !== null"> | R:R {{ riskRewardPreview.rrRatio.toFixed(1) }}</template>
      </p>

      <button type="button" class="toggle-more-button" @click="showMoreFields = !showMoreFields">
        {{ showMoreFields ? 'Fewer fields' : 'More fields' }}
      </button>

      <div v-if="showMoreFields" class="trade-form-secondary">
        <input v-model="tradeForm.entry_time" type="datetime-local" />
        <span class="price-points-field">
          <input
            v-if="targetMode === 'price'"
            v-model="tradeForm.target_price"
            type="number"
            step="any"
            placeholder="Target"
          />
          <input v-else v-model="tradeForm.target_points" type="number" step="any" placeholder="Target pts" />
          <span class="price-points-toggle">
            <button type="button" :class="{ active: targetMode === 'price' }" @click="targetMode = 'price'">
              Price
            </button>
            <button type="button" :class="{ active: targetMode === 'points' }" @click="targetMode = 'points'">
              Points
            </button>
          </span>
          <span v-if="targetConversionHint" class="conversion-hint">{{ targetConversionHint }}</span>
        </span>
        <select
          v-if="setupEntryMode === 'preset'"
          :value="tradeForm.setup"
          @change="handleSetupPresetChange($event.target.value)"
        >
          <option value="">No setup</option>
          <option v-for="setup in tradesStore.setups" :key="setup.id" :value="setup.name">{{ setup.name }}</option>
          <option value="__custom__">Other…</option>
        </select>
        <span v-else class="custom-symbol">
          <input v-model="tradeForm.setup" type="text" placeholder="Setup" maxlength="200" />
          <button
            v-if="tradesStore.setups.length > 0"
            type="button"
            class="toggle-more-button"
            @click="switchToSetupPresetList"
          >
            Use list
          </button>
        </span>
        <textarea v-model="tradeForm.notes" rows="2" placeholder="Notes"></textarea>
      </div>

      <p v-if="submitError" class="submit-error">{{ submitError }}</p>
    </form>
    <p v-else-if="trades.length === 0" class="locked-hint">This day is locked. Unlock it to log trades.</p>
  </section>
</template>

<style scoped>
.trades-section {
  margin-bottom: var(--el-space-8);
}

.trades-section h2 {
  font-size: var(--el-text-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--el-text-muted);
  margin: 0 0 var(--el-space-3);
}

.trade-list {
  list-style: none;
  margin: 0 0 var(--el-space-4);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--el-space-3);
}

.trade-card {
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-left: 3px solid var(--el-border);
  border-radius: var(--el-radius-md);
  overflow: hidden;
}

.trade-card--open {
  border-left-color: var(--el-copper);
}

.trade-card--closed {
  border-left-color: var(--el-steel);
}

.trade-card--canceled {
  border-left-color: var(--el-steel);
  opacity: 0.7;
}

.trade-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--el-space-3);
  padding: var(--el-space-3) var(--el-space-4);
  cursor: pointer;
  font-size: var(--el-text-sm);
}

.trade-card__header:hover {
  background-color: var(--el-surface-raised);
}

.trade-card__title {
  display: flex;
  align-items: center;
  gap: var(--el-space-2);
}

.trade-card__symbol {
  font-weight: 700;
  font-family: var(--el-font-mono);
}

.trade-card__summary-right {
  display: flex;
  align-items: center;
  gap: var(--el-space-2);
}

.trade-direction {
  font-size: var(--el-text-xs);
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 2px var(--el-space-2);
  border-radius: var(--el-radius-sm);
}

.trade-direction--long {
  color: var(--el-positive);
  border: 1px solid var(--el-positive);
}

.trade-direction--short {
  color: var(--el-negative);
  border: 1px solid var(--el-negative);
}

.trade-remaining {
  color: var(--el-text-muted);
  font-size: var(--el-text-xs);
}

.trade-status {
  font-size: var(--el-text-xs);
  font-weight: 600;
  letter-spacing: 0.05em;
  padding: 2px var(--el-space-2);
  border-radius: var(--el-radius-sm);
}

.trade-status--open {
  color: var(--el-copper);
  background-color: rgba(184, 115, 51, 0.12);
}

.trade-status--closed {
  color: var(--el-text-subtle);
  background-color: var(--el-bg);
}

.trade-status--canceled {
  color: var(--el-steel-light);
  background-color: var(--el-bg);
}

.canceled-hint {
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  margin: 0 0 var(--el-space-2);
}

.trade-result {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.result-positive {
  color: var(--el-positive);
}

.result-negative {
  color: var(--el-negative);
}

.trade-card__body {
  padding: 0 var(--el-space-4) var(--el-space-4);
  border-top: 1px solid var(--el-border);
}

.trade-card__info {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-4);
  padding: var(--el-space-3) var(--el-space-4);
  margin: var(--el-space-3) 0;
  background-color: var(--el-bg);
  border-radius: var(--el-radius-sm);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: var(--el-text-sm);
}

.info-label {
  font-size: var(--el-text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--el-text-subtle);
}

.info-value {
  color: var(--el-text);
  font-variant-numeric: tabular-nums;
}

.info-value--positive {
  color: var(--el-positive);
}

.info-value--negative {
  color: var(--el-negative);
}

.trade-card__section {
  margin-bottom: var(--el-space-3);
}

.trade-card__section-label {
  font-size: var(--el-text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--el-text-subtle);
  margin-bottom: var(--el-space-1);
}

.trade-card__actions,
.trade-card__edit-actions {
  display: flex;
  gap: var(--el-space-2);
  flex-wrap: wrap;
  margin-top: var(--el-space-3);
}

.btn-chip {
  padding: var(--el-space-1) var(--el-space-3);
  background-color: transparent;
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  color: var(--el-text-muted);
  font-size: var(--el-text-xs);
  font-weight: 500;
  cursor: pointer;
}

.btn-chip:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.btn-chip--ghost:hover:not(:disabled) {
  border-color: var(--el-copper);
  color: var(--el-copper);
}

.btn-chip--primary {
  background-color: var(--el-copper);
  border-color: var(--el-copper);
  color: var(--el-bg);
}

.btn-chip--warning {
  border-color: var(--el-warning);
  color: var(--el-warning);
}

.btn-chip--warning:hover:not(:disabled) {
  background-color: rgba(251, 191, 36, 0.12);
}

.btn-chip--danger {
  border-color: var(--el-negative);
  color: var(--el-negative);
}

.btn-chip--danger:hover:not(:disabled) {
  background-color: rgba(248, 113, 113, 0.12);
}

.trade-notes {
  color: var(--el-text);
  font-size: var(--el-text-sm);
  margin: 0 0 var(--el-space-3);
}

.exit-list {
  list-style: none;
  margin: 0 0 var(--el-space-3);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--el-space-1);
}

.exit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--el-text-sm);
  color: var(--el-text-muted);
}

.exit-row-actions {
  display: flex;
  gap: var(--el-space-1);
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

.edit-item-button:hover {
  color: var(--el-copper);
}

.remove-item-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.exit-form {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-2);
  margin-bottom: var(--el-space-2);
}

.exit-form input {
  flex: 1;
  min-width: 90px;
  padding: var(--el-space-2);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  color: var(--el-text);
  font-size: var(--el-text-sm);
}

.exit-form button {
  padding: var(--el-space-2) var(--el-space-4);
  background-color: transparent;
  color: var(--el-copper);
  border: 1px solid var(--el-copper);
  border-radius: var(--el-radius-sm);
  font-size: var(--el-text-sm);
  cursor: pointer;
}

.screenshot-dropzone {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--el-space-2);
  padding: var(--el-space-4);
  margin-bottom: var(--el-space-3);
  border: 1px dashed var(--el-border);
  border-radius: var(--el-radius-md);
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  cursor: text;
  text-align: center;
}

.screenshot-dropzone:hover,
.screenshot-dropzone:focus-visible {
  border-color: var(--el-copper);
  color: var(--el-text);
  outline: none;
}

.screenshot-dropzone--active {
  border-color: var(--el-copper);
  background-color: var(--el-surface);
}

.screenshot-dropzone--loading {
  color: var(--el-copper);
}

.screenshot-browse-button {
  background: none;
  border: none;
  padding: 0;
  color: var(--el-copper);
  font-size: inherit;
  font-family: inherit;
  text-decoration: underline;
  cursor: pointer;
}

.screenshot-browse-button:hover {
  color: var(--el-copper-hover);
}

.screenshot-input {
  display: none;
}

.extraction-hint {
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  margin: 0 0 var(--el-space-3);
}

.trade-form-primary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-2);
}

.trade-form-primary input,
.trade-form-primary select {
  padding: var(--el-space-2) var(--el-space-3);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  color: var(--el-text);
  font-size: var(--el-text-sm);
}

.trade-form-primary input[type='text'] {
  width: 90px;
}

.custom-symbol {
  display: flex;
  align-items: center;
  gap: var(--el-space-2);
}

.trade-form-primary input[type='number'] {
  width: 100px;
}

.trade-form-primary button {
  padding: var(--el-space-2) var(--el-space-6);
  background-color: var(--el-copper);
  color: var(--el-bg);
  border: none;
  border-radius: var(--el-radius-sm);
  font-weight: 500;
  cursor: pointer;
}

.direction-toggle {
  display: flex;
}

.trade-form-primary .direction-toggle-btn {
  padding: var(--el-space-2) var(--el-space-3);
  background-color: var(--el-surface);
  color: var(--el-text-muted);
  border: 1px solid var(--el-border);
  font-weight: 600;
  font-size: var(--el-text-xs);
  letter-spacing: 0.05em;
  cursor: pointer;
}

.direction-toggle .direction-toggle-btn:first-child {
  border-radius: var(--el-radius-sm) 0 0 var(--el-radius-sm);
}

.direction-toggle .direction-toggle-btn:last-child {
  border-radius: 0 var(--el-radius-sm) var(--el-radius-sm) 0;
}

.trade-form-primary .direction-toggle-btn--long {
  color: var(--el-positive);
  border-color: var(--el-positive);
}

.trade-form-primary .direction-toggle-btn--short {
  color: var(--el-negative);
  border-color: var(--el-negative);
}

.trade-form-primary .direction-toggle-btn--long.direction-toggle-btn--active {
  background-color: var(--el-positive);
  color: var(--el-bg);
}

.trade-form-primary .direction-toggle-btn--short.direction-toggle-btn--active {
  background-color: var(--el-negative);
  color: var(--el-bg);
}

.price-points-field {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--el-space-1);
}

.price-points-toggle {
  display: flex;
  gap: 2px;
}

.trade-form-primary .price-points-toggle button,
.trade-form-secondary .price-points-toggle button {
  padding: 2px var(--el-space-2);
  background: none;
  color: var(--el-text-subtle);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  font-size: 10px;
  cursor: pointer;
}

.trade-form-primary .price-points-toggle button.active,
.trade-form-secondary .price-points-toggle button.active {
  color: var(--el-copper);
  border-color: var(--el-copper);
}

.conversion-hint {
  color: var(--el-text-subtle);
  font-size: var(--el-text-xs);
}

.rr-preview {
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  margin: var(--el-space-2) 0 0;
}

.toggle-more-button {
  background: none;
  border: none;
  color: var(--el-text-muted);
  font-size: var(--el-text-xs);
  cursor: pointer;
  margin-top: var(--el-space-2);
  padding: 0;
}

.quick-exit-buttons {
  display: flex;
  gap: var(--el-space-4);
}

.toggle-more-button:hover {
  color: var(--el-copper);
}

.trade-form-secondary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-2);
  margin-top: var(--el-space-2);
}

.trade-form-secondary input,
.trade-form-secondary textarea {
  padding: var(--el-space-2) var(--el-space-3);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  color: var(--el-text);
  font-size: var(--el-text-sm);
  font-family: inherit;
}

.trade-form-secondary textarea {
  flex: 1 0 100%;
  resize: vertical;
}

.submit-error {
  color: var(--el-negative);
  font-size: var(--el-text-sm);
  margin: var(--el-space-2) 0 0;
}

.locked-hint {
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
}
</style>
