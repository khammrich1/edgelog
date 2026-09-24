<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { formatSignedDollars } from '@/utils/trades'

const props = defineProps({
  entries: { type: Array, required: true },
  year: { type: Number, required: true }
})

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const MONTH_LABELS_SHORT = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']

// Chart geometry (fixed viewBox; CSS scales the <svg> fluidly for responsiveness).
const CHART_WIDTH = 760
const CHART_HEIGHT = 320
const PLOT_TOP = 16
const PLOT_BOTTOM = 280
const PLOT_HEIGHT = PLOT_BOTTOM - PLOT_TOP
const GROUP_WIDTH = CHART_WIDTH / 12
const GROUP_GAP = 6
const BAR_GAP = 2
const BAR_WIDTH = (GROUP_WIDTH - GROUP_GAP * 2 - BAR_GAP) / 2

const isNarrow = ref(false)
let mediaQuery = null

function updateIsNarrow(event) {
  isNarrow.value = event.matches
}

onMounted(() => {
  mediaQuery = window.matchMedia('(max-width: 480px)')
  isNarrow.value = mediaQuery.matches
  mediaQuery.addEventListener('change', updateIsNarrow)
})

onUnmounted(() => {
  mediaQuery?.removeEventListener('change', updateIsNarrow)
})

const monthlyTotals = computed(() => {
  const months = Array.from({ length: 12 }, (_, i) => ({ month: i, income: 0, cost: 0 }))
  for (const entry of props.entries) {
    const monthIndex = Number(entry.date.slice(5, 7)) - 1
    const bucket = months[monthIndex]
    if (!bucket) continue
    if (entry.entry_type === 'income') bucket.income += Number(entry.amount)
    else bucket.cost += Number(entry.amount)
  }
  return months
})

const maxValue = computed(() => Math.max(1, ...monthlyTotals.value.flatMap((m) => [m.income, m.cost])))

const totalIncome = computed(() => monthlyTotals.value.reduce((sum, m) => sum + m.income, 0))
const totalCost = computed(() => monthlyTotals.value.reduce((sum, m) => sum + m.cost, 0))

function groupX(index) {
  return index * GROUP_WIDTH
}

function barHeight(value) {
  return (value / maxValue.value) * PLOT_HEIGHT
}

function barY(value) {
  return PLOT_BOTTOM - barHeight(value)
}

function monthLabel(index) {
  return (isNarrow.value ? MONTH_LABELS_SHORT : MONTH_LABELS)[index]
}

// Recessive gridlines at 25/50/75/100% of the shared axis max.
const gridlines = computed(() =>
  [0.25, 0.5, 0.75, 1].map((fraction) => ({
    y: PLOT_BOTTOM - fraction * PLOT_HEIGHT,
    value: fraction * maxValue.value
  }))
)

const tooltip = ref(null)

function showTooltip(event, monthIndex, series, value) {
  const rect = event.currentTarget.closest('.chart-container').getBoundingClientRect()
  tooltip.value = {
    x: event.clientX - rect.left + 12,
    y: event.clientY - rect.top - 12,
    label: `${MONTH_LABELS[monthIndex]} ${series === 'income' ? 'Income' : 'Expenses'}`,
    value
  }
}

function hideTooltip() {
  tooltip.value = null
}
</script>

<template>
  <div class="chart-container">
    <svg
      :viewBox="`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`"
      preserveAspectRatio="xMidYMid meet"
      class="chart-svg"
      role="img"
      :aria-label="`Monthly income vs expenses for ${year}`"
    >
      <line
        v-for="line in gridlines"
        :key="line.value"
        class="gridline"
        :x1="0"
        :x2="CHART_WIDTH"
        :y1="line.y"
        :y2="line.y"
      />
      <text v-for="line in gridlines" :key="`label-${line.value}`" class="axis-label" :x="2" :y="line.y - 4">
        {{ formatSignedDollars(line.value).replace('+', '') }}
      </text>

      <g v-for="(m, i) in monthlyTotals" :key="i" :transform="`translate(${groupX(i)}, 0)`">
        <rect
          class="bar bar--income"
          :x="GROUP_GAP"
          :y="barY(m.income)"
          :width="BAR_WIDTH"
          :height="Math.max(0, barHeight(m.income))"
          rx="2"
          @mouseenter="showTooltip($event, i, 'income', m.income)"
          @mouseleave="hideTooltip"
        />
        <rect
          class="bar bar--cost"
          :x="GROUP_GAP + BAR_WIDTH + BAR_GAP"
          :y="barY(m.cost)"
          :width="BAR_WIDTH"
          :height="Math.max(0, barHeight(m.cost))"
          rx="2"
          @mouseenter="showTooltip($event, i, 'cost', m.cost)"
          @mouseleave="hideTooltip"
        />
        <text class="month-label" :x="GROUP_WIDTH / 2" :y="PLOT_BOTTOM + 20">{{ monthLabel(i) }}</text>
      </g>
    </svg>

    <div v-if="tooltip" class="chart-tooltip" :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
      {{ tooltip.label }}: {{ formatSignedDollars(tooltip.value) }}
    </div>

    <div class="chart-legend">
      <span class="legend-item"><span class="legend-swatch legend-swatch--income"></span>Income {{ formatSignedDollars(totalIncome) }}</span>
      <span class="legend-item"><span class="legend-swatch legend-swatch--cost"></span>Expenses {{ formatSignedDollars(-totalCost) }}</span>
    </div>
  </div>
</template>

<style scoped>
.chart-container {
  position: relative;
}

.chart-svg {
  display: block;
  width: 100%;
  height: auto;
}

.gridline {
  stroke: var(--el-border);
  stroke-width: 1;
}

.axis-label {
  fill: var(--el-text-subtle);
  font-size: 10px;
  font-family: var(--el-font-sans);
}

.bar--income {
  fill: var(--el-positive);
}

.bar--cost {
  fill: var(--el-steel-light);
}

.month-label {
  fill: var(--el-text-muted);
  font-size: 11px;
  font-family: var(--el-font-sans);
  text-anchor: middle;
}

.chart-tooltip {
  position: absolute;
  pointer-events: none;
  padding: var(--el-space-1) var(--el-space-2);
  background-color: var(--el-surface-raised);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  color: var(--el-text);
  font-size: var(--el-text-xs);
  white-space: nowrap;
  z-index: 10;
}

.chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-4);
  margin-top: var(--el-space-2);
  font-size: var(--el-text-sm);
  color: var(--el-text-muted);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--el-space-2);
}

.legend-swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.legend-swatch--income {
  background-color: var(--el-positive);
}

.legend-swatch--cost {
  background-color: var(--el-steel-light);
}
</style>
