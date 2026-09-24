<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFinancialEntriesStore } from '@/stores/financialEntries'
import { formatSignedDollars, resultClass } from '@/utils/trades'
import FinancialEntryForm from '@/components/financials/FinancialEntryForm.vue'
import FinancialChart from '@/components/financials/FinancialChart.vue'
import FinancialEntriesTable from '@/components/financials/FinancialEntriesTable.vue'
import FinancialBulkImport from '@/components/financials/FinancialBulkImport.vue'

const route = useRoute()
const router = useRouter()
const financialEntriesStore = useFinancialEntriesStore()

const currentYear = new Date().getFullYear()
const viewedYear = ref(Number(route.params.year) || currentYear)

const entries = computed(() => financialEntriesStore.entriesByYear[viewedYear.value] ?? [])

const totalIncome = computed(() => entries.value.filter((e) => e.entry_type === 'income').reduce((sum, e) => sum + Number(e.amount), 0))
const totalExpenses = computed(() => entries.value.filter((e) => e.entry_type === 'expense').reduce((sum, e) => sum + Number(e.amount), 0))
const netProfit = computed(() => totalIncome.value - totalExpenses.value)

const editingEntry = ref(null)
const showBulkImport = ref(false)

async function fetchYear() {
  await financialEntriesStore.fetchEntriesForYear(viewedYear.value)
}

// Using replace (not push) for year navigation keeps browser history from
// filling up with one entry per year click -- the back button leaves
// /financials entirely rather than stepping year-by-year.
function navigateToYear(year) {
  viewedYear.value = year
  router.replace(`/financials/${year}`)
}

function goToPreviousYear() {
  navigateToYear(viewedYear.value - 1)
}

function goToNextYear() {
  navigateToYear(viewedYear.value + 1)
}

function goToCurrentYear() {
  navigateToYear(currentYear)
}

function onJumpToYear(event) {
  const year = Number(event.target.value)
  if (year) navigateToYear(year)
}

function onEditRequested(entry) {
  editingEntry.value = entry
}

function onEntrySaved() {
  editingEntry.value = null
}

function onCancelEdit() {
  editingEntry.value = null
}

watch(
  () => route.params.year,
  (newYear) => {
    if (newYear && Number(newYear) !== viewedYear.value) viewedYear.value = Number(newYear)
  }
)

watch(viewedYear, fetchYear, { immediate: true })
</script>

<template>
  <div class="financials-page">
    <div class="page-header">
      <h1>Financials -- {{ viewedYear }}</h1>
      <div class="year-nav">
        <button class="nav-button" @click="goToPreviousYear" aria-label="Previous year">&lsaquo;</button>
        <button class="nav-button nav-today" @click="goToCurrentYear">This year</button>
        <button class="nav-button" @click="goToNextYear" aria-label="Next year">&rsaquo;</button>
        <input type="number" class="jump-input" :value="viewedYear" aria-label="Jump to year" @change="onJumpToYear" />
      </div>
    </div>

    <div class="summary-tiles">
      <div class="summary-tile">
        <span class="summary-label">Income</span>
        <span class="summary-value result-positive">{{ formatSignedDollars(totalIncome) }}</span>
      </div>
      <div class="summary-tile">
        <span class="summary-label">Expenses</span>
        <span class="summary-value">{{ formatSignedDollars(-totalExpenses) }}</span>
      </div>
      <div class="summary-tile">
        <span class="summary-label">Net P&amp;L</span>
        <span class="summary-value" :class="resultClass(netProfit)">{{ formatSignedDollars(netProfit) }}</span>
      </div>
    </div>

    <FinancialChart :entries="entries" :year="viewedYear" />

    <h2 class="section-title">{{ editingEntry ? 'Edit entry' : 'Add entry' }}</h2>
    <FinancialEntryForm :entry="editingEntry" @saved="onEntrySaved" @cancel="onCancelEdit" />

    <button type="button" class="toggle-more-button" @click="showBulkImport = !showBulkImport">
      {{ showBulkImport ? 'Hide bulk import' : 'Import multiple from a screenshot' }}
    </button>
    <FinancialBulkImport v-if="showBulkImport" />

    <h2 class="section-title">Entries</h2>
    <FinancialEntriesTable :entries="entries" @edit="onEditRequested" />
  </div>
</template>

<style scoped>
.financials-page {
  padding: var(--el-space-8);
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--el-space-3);
  margin-bottom: var(--el-space-6);
}

.page-header h1 {
  font-size: var(--el-text-2xl);
  margin: 0;
}

.year-nav {
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
  width: 90px;
  padding: var(--el-space-2) var(--el-space-3);
  background-color: var(--el-surface);
  color: var(--el-text);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  font-size: var(--el-text-sm);
  font-family: inherit;
}

.summary-tiles {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-4);
  margin-bottom: var(--el-space-6);
}

.summary-tile {
  flex: 1 1 160px;
  display: flex;
  flex-direction: column;
  gap: var(--el-space-1);
  padding: var(--el-space-4);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-md);
}

.summary-label {
  font-size: var(--el-text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--el-text-subtle);
}

.summary-value {
  font-size: var(--el-text-xl);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--el-text);
}

.result-positive {
  color: var(--el-positive);
}

.result-negative {
  color: var(--el-negative);
}

.section-title {
  font-size: var(--el-text-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--el-text-muted);
  margin: var(--el-space-8) 0 var(--el-space-3);
}

.toggle-more-button {
  background: none;
  border: none;
  color: var(--el-text-muted);
  font-size: var(--el-text-xs);
  cursor: pointer;
  padding: 0;
}

.toggle-more-button:hover {
  color: var(--el-copper);
}

@media (max-width: 640px) {
  .financials-page {
    padding: var(--el-space-4);
  }
}
</style>
