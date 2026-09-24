<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTradesStore } from '@/stores/trades'
import { formatPrice, formatSignedDollars, formatSignedPoints, resultClass } from '@/utils/trades'
import { computeRealizedR } from '@/utils/tradeMath'

const props = defineProps({
  trade: { type: Object, required: true },
  date: { type: String, required: true }
})

const emit = defineEmits(['close'])

const router = useRouter()
const tradesStore = useTradesStore()

const screenshotUrl = ref(null)

async function loadScreenshot() {
  revokeScreenshot()
  if (props.trade.has_screenshot) {
    screenshotUrl.value = await tradesStore.fetchTradeScreenshotObjectUrl(props.date, props.trade.id)
  }
}

function revokeScreenshot() {
  if (screenshotUrl.value) {
    URL.revokeObjectURL(screenshotUrl.value)
    screenshotUrl.value = null
  }
}

watch(() => props.trade.id, loadScreenshot, { immediate: true })

function handleKeydown(event) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  revokeScreenshot()
})

const realizedR = computed(() => computeRealizedR(props.trade.realized_pnl, props.trade.planned_risk_dollars))

const resultLabel = computed(() => {
  if (props.trade.status !== 'closed') return null
  return props.trade.multiplier_known
    ? formatSignedDollars(props.trade.realized_pnl)
    : `${formatSignedPoints(props.trade.realized_points)} pts`
})

const resultClassName = computed(() => {
  if (props.trade.status !== 'closed') return ''
  return resultClass(props.trade.multiplier_known ? props.trade.realized_pnl : props.trade.realized_points)
})

function openInJournal() {
  router.push(`/journal/${props.date}`)
}
</script>

<template>
  <div class="drawer-backdrop" @click="$emit('close')">
    <div class="drawer-panel" role="dialog" aria-label="Trade detail" @click.stop>
      <div class="drawer-header">
        <div class="drawer-title">
          <span class="drawer-symbol">{{ trade.symbol }}</span>
          <span class="trade-direction" :class="`trade-direction--${trade.direction}`">
            {{ trade.direction === 'long' ? 'LONG' : 'SHORT' }}
          </span>
        </div>
        <button type="button" class="close-button" aria-label="Close" @click="$emit('close')">&times;</button>
      </div>

      <div class="drawer-info">
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
        <div v-if="resultLabel" class="info-item">
          <span class="info-label">Realized</span>
          <span class="info-value" :class="resultClassName">
            {{ resultLabel }}
            <template v-if="realizedR !== null">({{ realizedR > 0 ? '+' : '' }}{{ realizedR.toFixed(1) }}R)</template>
          </span>
        </div>
      </div>

      <p v-if="trade.notes" class="drawer-notes">{{ trade.notes }}</p>

      <div v-if="trade.entries.length" class="drawer-section">
        <div class="drawer-section-label">Entries</div>
        <ul class="drawer-list">
          <li>{{ trade.initial_quantity }} @ {{ formatPrice(trade.entry_price) }} <small>(original)</small></li>
          <li v-for="entry in trade.entries" :key="entry.id">{{ entry.quantity }} @ {{ formatPrice(entry.entry_price) }}</li>
        </ul>
      </div>

      <div v-if="trade.exits.length" class="drawer-section">
        <div class="drawer-section-label">Trims</div>
        <ul class="drawer-list">
          <li v-for="exit in trade.exits" :key="exit.id">{{ exit.quantity }} @ {{ formatPrice(exit.exit_price) }}</li>
        </ul>
      </div>

      <div v-if="screenshotUrl" class="drawer-section">
        <div class="drawer-section-label">Setup screenshot</div>
        <img :src="screenshotUrl" alt="Trade setup screenshot" class="drawer-screenshot" />
      </div>

      <button type="button" class="journal-link" @click="openInJournal">View in Daily Journal &rsaquo;</button>
    </div>
  </div>
</template>

<style scoped>
.drawer-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: flex-end;
  z-index: 100;
}

.drawer-panel {
  width: 100%;
  max-width: 400px;
  height: 100%;
  overflow-y: auto;
  background-color: var(--el-surface);
  border-left: 1px solid var(--el-border);
  padding: var(--el-space-6);
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--el-space-4);
}

.drawer-title {
  display: flex;
  align-items: center;
  gap: var(--el-space-2);
}

.drawer-symbol {
  font-weight: 700;
  font-family: var(--el-font-mono);
  font-size: var(--el-text-lg);
}

.close-button {
  background: none;
  border: none;
  color: var(--el-text-subtle);
  font-size: var(--el-text-xl);
  line-height: 1;
  cursor: pointer;
}

.close-button:hover {
  color: var(--el-text);
}

.drawer-info {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-4);
  padding: var(--el-space-3) var(--el-space-4);
  margin-bottom: var(--el-space-4);
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

.result-positive {
  color: var(--el-positive);
}

.result-negative {
  color: var(--el-negative);
}

.drawer-notes {
  color: var(--el-text);
  font-size: var(--el-text-sm);
  margin: 0 0 var(--el-space-4);
}

.drawer-section {
  margin-bottom: var(--el-space-4);
}

.drawer-section-label {
  font-size: var(--el-text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--el-text-subtle);
  margin-bottom: var(--el-space-1);
}

.drawer-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--el-space-1);
  font-size: var(--el-text-sm);
  color: var(--el-text-muted);
}

.drawer-screenshot {
  max-width: 100%;
  border-radius: var(--el-radius-sm);
  border: 1px solid var(--el-border);
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

.journal-link {
  display: block;
  width: 100%;
  padding: var(--el-space-2) var(--el-space-4);
  background-color: transparent;
  color: var(--el-copper);
  border: 1px solid var(--el-copper);
  border-radius: var(--el-radius-sm);
  font-size: var(--el-text-sm);
  cursor: pointer;
  text-align: center;
}

.journal-link:hover {
  background-color: rgba(184, 115, 51, 0.12);
}

@media (max-width: 768px) {
  .drawer-backdrop {
    align-items: flex-end;
  }

  .drawer-panel {
    max-width: none;
    height: auto;
    max-height: 80vh;
    border-left: none;
    border-top: 1px solid var(--el-border);
    border-radius: var(--el-radius-lg) var(--el-radius-lg) 0 0;
  }
}
</style>
