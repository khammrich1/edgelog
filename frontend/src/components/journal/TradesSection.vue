<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useTradesStore } from '@/stores/trades'
import { formatPrice, formatSignedDollars, formatSignedPoints, resultClass, SYMBOL_PRESETS } from '@/utils/trades'

const props = defineProps({
  date: { type: String, required: true },
  locked: { type: Boolean, default: false }
})

const tradesStore = useTradesStore()

const trades = computed(() => tradesStore.tradesByDate[props.date] || [])
const expandedTradeId = ref(null)
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
  if (extracted.stop_price != null) tradeForm.stop_price = String(extracted.stop_price)
  if (extracted.target_price != null) {
    tradeForm.target_price = String(extracted.target_price)
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
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`
}

function emptyTradeForm() {
  return {
    symbol: '',
    direction: 'long',
    initial_quantity: '',
    entry_price: '',
    stop_price: '',
    entry_time: nowForDateTimeLocal(),
    target_price: '',
    setup: '',
    notes: ''
  }
}

const tradeForm = reactive(emptyTradeForm())
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
    stop_price: tradeForm.stop_price || null,
    target_price: tradeForm.target_price || null,
    setup: tradeForm.setup || null,
    notes: tradeForm.notes || null
  }
  try {
    await tradesStore.createTrade(props.date, payload)
    Object.assign(tradeForm, emptyTradeForm())
    symbolEntryMode.value = 'preset'
    resetSetupEntryMode()
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
  await tradesStore.fetchSetups()
  resetSetupEntryMode()
})
</script>

<template>
  <section class="trades-section">
    <h2>Trades</h2>

    <ul class="trade-list">
      <li v-for="trade in trades" :key="trade.id" class="trade-row">
        <div class="trade-summary" @click="toggleExpand(trade.id)">
          <span class="trade-symbol">{{ trade.symbol }}</span>
          <span class="trade-direction" :class="`trade-direction--${trade.direction}`">
            {{ trade.direction === 'long' ? 'LONG' : 'SHORT' }}
          </span>
          <span class="trade-quantity">{{ trade.total_quantity }}</span>
          <span class="trade-entry">Entry {{ formatPrice(trade.average_entry_price) }}</span>

          <template v-if="trade.status === 'canceled'">
            <span class="trade-status trade-status--canceled">CANCELED</span>
          </template>
          <template v-else-if="trade.status === 'open'">
            <span class="trade-remaining">Remaining {{ trade.remaining_quantity }}</span>
            <span class="trade-status trade-status--open">OPEN</span>
          </template>
          <template v-else>
            <span class="trade-status trade-status--closed">CLOSED</span>
            <span v-if="trade.multiplier_known" class="trade-result" :class="resultClass(trade.realized_pnl)">
              {{ formatSignedDollars(trade.realized_pnl) }}
            </span>
            <span v-else class="trade-result" :class="resultClass(trade.realized_points)">
              {{ formatSignedPoints(trade.realized_points) }} pts
            </span>
          </template>
        </div>

        <div v-if="expandedTradeId === trade.id" class="trade-detail">
          <p v-if="trade.status === 'canceled'" class="canceled-hint">Canceled -- excluded from P&L.</p>
          <div class="trade-detail-grid">
            <span v-if="trade.stop_price">Stop {{ formatPrice(trade.stop_price) }}</span>
            <span v-if="trade.target_price">Target {{ formatPrice(trade.target_price) }}</span>
            <span v-if="trade.setup">Setup: {{ trade.setup }}</span>
            <span v-if="trade.planned_risk_dollars">Planned risk: ${{ formatPrice(trade.planned_risk_dollars) }}</span>
            <span v-else-if="trade.planned_risk_points">Planned risk: {{ formatPrice(trade.planned_risk_points) }} pts</span>
          </div>
          <p v-if="trade.notes" class="trade-notes">{{ trade.notes }}</p>

          <ul v-if="trade.entries.length" class="exit-list">
            <li class="exit-row">
              <span>{{ trade.initial_quantity }} @ {{ formatPrice(trade.entry_price) }} (original)</span>
            </li>
            <li v-for="entry in trade.entries" :key="entry.id" class="exit-row">
              <span>{{ entry.quantity }} @ {{ formatPrice(entry.entry_price) }}</span>
              <button class="remove-item-button" :disabled="locked" @click="removeEntry(trade, entry)">&times;</button>
            </li>
          </ul>

          <ul v-if="trade.exits.length" class="exit-list">
            <li v-for="exit in trade.exits" :key="exit.id" class="exit-row">
              <span>{{ exit.quantity }} @ {{ formatPrice(exit.exit_price) }}</span>
              <button class="remove-item-button" :disabled="locked" @click="removeExit(trade, exit)">&times;</button>
            </li>
          </ul>

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

            <button v-if="trade.stop_price" type="button" class="toggle-more-button" @click="stopHit(trade)">
              Stop hit
            </button>
          </template>

          <div class="trade-detail-actions">
            <button
              v-if="trade.status === 'open' && trade.exits.length === 0 && trade.entries.length === 0"
              class="remove-item-button remove-item-button--text"
              :disabled="locked"
              @click="cancelTradeAction(trade)"
            >
              Cancel trade
            </button>
            <button class="remove-item-button remove-item-button--text" :disabled="locked" @click="removeTrade(trade)">
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
        @click="fileInput.click()"
        @keydown.enter="fileInput.click()"
        @dragover.prevent="dragActive = true"
        @dragleave.prevent="dragActive = false"
        @drop.prevent="onDrop"
        @paste="onPaste"
      >
        <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" class="screenshot-input" @change="onFilePicked" />
        <span v-if="screenshotState === 'loading'">Reading screenshot…</span>
        <span v-else>Drop, paste, or click to upload a trade screenshot</span>
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
        <select v-model="tradeForm.direction">
          <option value="long">Long</option>
          <option value="short">Short</option>
        </select>
        <input v-model="tradeForm.initial_quantity" type="number" min="1" placeholder="Qty" required />
        <input v-model="tradeForm.entry_price" type="number" step="any" placeholder="Entry" required />
        <input v-model="tradeForm.stop_price" type="number" step="any" placeholder="Stop" />
        <button type="submit">Add trade</button>
      </div>

      <button type="button" class="toggle-more-button" @click="showMoreFields = !showMoreFields">
        {{ showMoreFields ? 'Fewer fields' : 'More fields' }}
      </button>

      <div v-if="showMoreFields" class="trade-form-secondary">
        <input v-model="tradeForm.entry_time" type="datetime-local" />
        <input v-model="tradeForm.target_price" type="number" step="any" placeholder="Target" />
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
  gap: 1px;
  background-color: var(--el-border);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-md);
  overflow: hidden;
}

.trade-row {
  background-color: var(--el-bg);
}

.trade-summary {
  display: flex;
  align-items: center;
  gap: var(--el-space-3);
  padding: var(--el-space-3);
  cursor: pointer;
  font-size: var(--el-text-sm);
}

.trade-summary:hover {
  background-color: var(--el-surface);
}

.trade-symbol {
  font-weight: 600;
  min-width: 48px;
}

.trade-direction {
  font-size: var(--el-text-xs);
  letter-spacing: 0.04em;
  padding: 2px var(--el-space-2);
  border-radius: var(--el-radius-sm);
}

.trade-direction--long {
  color: var(--el-copper);
  border: 1px solid var(--el-copper);
}

.trade-direction--short {
  color: var(--el-steel-light);
  border: 1px solid var(--el-steel);
}

.trade-quantity,
.trade-entry,
.trade-remaining {
  color: var(--el-text-muted);
}

.trade-status {
  margin-left: auto;
  font-size: var(--el-text-xs);
  letter-spacing: 0.05em;
}

.trade-status--open {
  color: var(--el-copper);
}

.trade-status--closed {
  color: var(--el-text-subtle);
}

.trade-status--canceled {
  color: var(--el-steel-light);
}

.canceled-hint {
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  margin: 0 0 var(--el-space-2);
}

.trade-detail-actions {
  display: flex;
  gap: var(--el-space-4);
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

.trade-detail {
  padding: 0 var(--el-space-3) var(--el-space-3);
  border-top: 1px solid var(--el-border);
}

.trade-detail-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-4);
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  margin: var(--el-space-3) 0;
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

.remove-item-button--text {
  font-size: var(--el-text-xs);
  margin-top: var(--el-space-2);
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
  cursor: pointer;
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
  padding: var(--el-space-2) var(--el-space-5);
  background-color: var(--el-copper);
  color: var(--el-bg);
  border: none;
  border-radius: var(--el-radius-sm);
  font-weight: 500;
  cursor: pointer;
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
