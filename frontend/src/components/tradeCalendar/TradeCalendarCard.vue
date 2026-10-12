<script setup>
import { computed } from 'vue'
import { formatSignedDollars, formatSignedPoints, resultClass } from '@/utils/trades'
import { computeRealizedR } from '@/utils/tradeMath'

const props = defineProps({
  trade: { type: Object, required: true },
  selected: { type: Boolean, default: false }
})

defineEmits(['select'])

const entryTimeLabel = computed(() =>
  new Date(props.trade.entry_time).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
)

const realizedR = computed(() => computeRealizedR(props.trade.realized_pnl, props.trade.planned_risk_dollars))

const pnlLabel = computed(() => {
  if (props.trade.status !== 'closed') return null
  return props.trade.multiplier_known
    ? formatSignedDollars(props.trade.realized_pnl)
    : `${formatSignedPoints(props.trade.realized_points)} pts`
})

// Neutral for anything that isn't a realized dollar/points result -- open
// and canceled trades never get a green/red result class.
const pnlResultClass = computed(() => {
  if (props.trade.status !== 'closed') return ''
  return resultClass(props.trade.multiplier_known ? props.trade.realized_pnl : props.trade.realized_points)
})
</script>

<template>
  <button
    type="button"
    class="calendar-trade-card"
    :class="{ 'calendar-trade-card--selected': selected }"
    :aria-pressed="selected"
    @click="$emit('select', trade.id)"
  >
    <div class="calendar-trade-card__top">
      <span class="calendar-trade-card__symbol">{{ trade.symbol }}</span>
      <span class="trade-direction" :class="`trade-direction--${trade.direction}`">
        {{ trade.direction === 'long' ? 'LONG' : 'SHORT' }}
      </span>
    </div>
    <div class="calendar-trade-card__meta">
      <span>{{ entryTimeLabel }}</span>
      <span v-if="trade.setup" class="calendar-trade-card__setup">{{ trade.setup }}</span>
    </div>
    <div class="calendar-trade-card__bottom">
      <span class="trade-status" :class="`trade-status--${trade.status}`">{{ trade.status.toUpperCase() }}</span>
      <span v-if="pnlLabel" class="calendar-trade-card__result" :class="pnlResultClass">
        <span>{{ pnlLabel }}</span>
        <span v-if="realizedR !== null">({{ realizedR > 0 ? '+' : '' }}{{ realizedR.toFixed(1) }}R)</span>
      </span>
    </div>
  </button>
</template>

<style scoped>
.calendar-trade-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  padding: 12px;
  box-shadow: inset 0 1px var(--el-surface-highlight);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  color: var(--el-text);
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color var(--el-transition-fast), box-shadow var(--el-transition-fast);
}

.calendar-trade-card:hover {
  background-color: var(--el-surface-raised);
}

.calendar-trade-card--selected {
  border-color: var(--el-copper);
  background-color: var(--el-surface-raised);
  box-shadow: 0 0 0 1px var(--el-copper);
}

.calendar-trade-card__top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--el-space-2);
}

.calendar-trade-card__symbol {
  font-weight: 700;
  font-family: var(--el-font-mono);
  font-size: var(--el-text-sm);
}

.calendar-trade-card__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--el-space-2);
  font-size: var(--el-text-xs);
  color: var(--el-text-muted);
}

.calendar-trade-card__setup {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.calendar-trade-card__bottom {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--el-space-2);
}

.calendar-trade-card__result {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  font-size: var(--el-text-xs);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.calendar-trade-card__result > span,
.calendar-trade-card__meta > span:first-child { white-space: nowrap; }
.calendar-trade-card__setup { min-width: 0; max-width: 100%; }

.trade-direction {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 2px 5px;
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

.trade-status {
  white-space: nowrap;
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

.result-positive {
  color: var(--el-positive);
}

.result-negative {
  color: var(--el-negative);
}
</style>
