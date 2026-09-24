<script setup>
import { computed, ref } from 'vue'
import { useFinancialEntriesStore } from '@/stores/financialEntries'
import { todayDateKey } from '@/utils/date'

const financialEntriesStore = useFinancialEntriesStore()

// Screenshot capture: same dropzone pattern as FinancialEntryForm, but the
// extraction returns a LIST of candidate rows (e.g. a payout-history table)
// instead of one entry. Nothing is saved until the user reviews and submits.
const screenshotState = ref('idle') // idle | loading | error
const screenshotError = ref(null)
const dragActive = ref(false)
const fileInput = ref(null)

const draftRows = ref([])
const submitError = ref(null)
const submitting = ref(false)

function draftFromExtraction(extracted) {
  return {
    include: !extracted.possible_duplicate,
    possibleDuplicate: !!extracted.possible_duplicate,
    entry_type: extracted.entry_type || 'expense',
    category: extracted.category || '',
    amount: extracted.amount != null ? String(extracted.amount) : '',
    date: extracted.date || todayDateKey(),
    firm: extracted.firm || '',
    notes: extracted.notes || ''
  }
}

async function handleScreenshotFile(file) {
  if (!file) return
  screenshotState.value = 'loading'
  screenshotError.value = null
  submitError.value = null
  try {
    const extracted = await financialEntriesStore.parseFinancialScreenshotBulk(file)
    draftRows.value = extracted.map(draftFromExtraction)
    screenshotState.value = 'idle'
  } catch (error) {
    screenshotError.value =
      error.response?.data?.detail || 'Could not read that screenshot. Enter entries manually instead.'
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

function rowIsValid(row) {
  // Zero is a valid amount (e.g. a free reset) -- only blank/negative isn't.
  return row.category.trim().length > 0 && row.amount !== '' && Number(row.amount) >= 0 && !!row.date
}

const includedCount = computed(() => draftRows.value.filter((row) => row.include).length)
const duplicateCount = computed(() => draftRows.value.filter((row) => row.possibleDuplicate).length)

const canImport = computed(
  () => includedCount.value > 0 && draftRows.value.every((row) => !row.include || rowIsValid(row))
)

async function submitImport() {
  submitError.value = null
  const payload = draftRows.value
    .filter((row) => row.include)
    .map((row) => ({
      entry_type: row.entry_type,
      category: row.category.trim(),
      amount: row.amount,
      date: row.date,
      firm: row.firm.trim() || null,
      notes: row.notes.trim() || null
    }))

  submitting.value = true
  try {
    await financialEntriesStore.bulkCreateEntries(payload)
    draftRows.value = []
    screenshotState.value = 'idle'
  } catch (error) {
    submitError.value = error.response?.data?.detail || 'Could not import those entries.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="bulk-import">
    <div
      class="screenshot-dropzone"
      :class="{ 'screenshot-dropzone--active': dragActive, 'screenshot-dropzone--loading': screenshotState === 'loading' }"
      tabindex="0"
      @dragover.prevent="dragActive = true"
      @dragleave.prevent="dragActive = false"
      @drop.prevent="onDrop"
      @paste="onPaste"
    >
      <input
        ref="fileInput"
        type="file"
        accept="image/png,image/jpeg,image/webp"
        class="screenshot-input"
        @change="onFilePicked"
      />
      <span v-if="screenshotState === 'loading'">Reading screenshot…</span>
      <span v-else>
        Drop or paste a payout-history / expenses table screenshot, or
        <button type="button" class="screenshot-browse-button" @click="fileInput.click()">browse a file</button>
      </span>
    </div>
    <p v-if="screenshotError" class="submit-error">{{ screenshotError }}</p>
    <p v-if="duplicateCount > 0" class="extraction-hint">
      {{ duplicateCount }} row{{ duplicateCount === 1 ? '' : 's' }} matched an entry you already have (same date,
      amount, and category) and {{ duplicateCount === 1 ? 'was' : 'were' }} unchecked automatically -- review before
      importing.
    </p>

    <table v-if="draftRows.length" class="draft-table">
      <thead>
        <tr>
          <th></th>
          <th>Type</th>
          <th>Category</th>
          <th>Amount</th>
          <th>Date</th>
          <th>Firm / Account</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in draftRows" :key="index" :class="{ 'draft-row--excluded': !row.include }">
          <td>
            <input type="checkbox" v-model="row.include" :aria-label="`Include row ${index + 1}`" />
            <span v-if="row.possibleDuplicate" class="duplicate-flag" title="Matches an existing entry (same date, amount, category)">
              dup
            </span>
          </td>
          <td>
            <div class="type-toggle type-toggle--compact" role="group" aria-label="Entry type">
              <button
                type="button"
                class="type-toggle-btn type-toggle-btn--expense"
                :class="{ 'type-toggle-btn--active': row.entry_type === 'expense' }"
                @click="row.entry_type = 'expense'"
              >
                EXP
              </button>
              <button
                type="button"
                class="type-toggle-btn type-toggle-btn--income"
                :class="{ 'type-toggle-btn--active': row.entry_type === 'income' }"
                @click="row.entry_type = 'income'"
              >
                INC
              </button>
            </div>
          </td>
          <td><input v-model="row.category" type="text" class="draft-input draft-input--category" placeholder="Category" /></td>
          <td><input v-model="row.amount" type="number" step="any" min="0" class="draft-input draft-input--amount" placeholder="Amount" /></td>
          <td><input v-model="row.date" type="date" class="draft-input" /></td>
          <td><input v-model="row.firm" type="text" class="draft-input draft-input--category" placeholder="Firm / account" /></td>
        </tr>
      </tbody>
    </table>

    <button v-if="draftRows.length" type="button" class="import-button" :disabled="!canImport || submitting" @click="submitImport">
      Import {{ includedCount }} {{ includedCount === 1 ? 'entry' : 'entries' }}
    </button>
    <p v-if="submitError" class="submit-error">{{ submitError }}</p>
  </div>
</template>

<style scoped>
.bulk-import {
  margin-top: var(--el-space-3);
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

.screenshot-browse-button {
  background: none;
  border: none;
  padding: 0;
  color: var(--el-copper);
  text-decoration: underline;
  cursor: pointer;
  font-size: inherit;
}

.extraction-hint {
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  margin: 0 0 var(--el-space-3);
}

.duplicate-flag {
  display: inline-block;
  margin-left: var(--el-space-1);
  padding: 1px var(--el-space-1);
  border: 1px solid var(--el-copper);
  border-radius: var(--el-radius-sm);
  color: var(--el-copper);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: help;
}

.draft-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--el-text-sm);
  margin-bottom: var(--el-space-3);
}

.draft-table th {
  text-align: left;
  padding: var(--el-space-2) var(--el-space-2);
  color: var(--el-text-subtle);
  font-size: var(--el-text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--el-border);
}

.draft-table td {
  padding: var(--el-space-2);
  border-bottom: 1px solid var(--el-border);
  vertical-align: middle;
}

.draft-row--excluded {
  opacity: 0.5;
}

.draft-input {
  width: 100%;
  padding: var(--el-space-2) var(--el-space-2);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  color: var(--el-text);
  font-size: var(--el-text-sm);
  font-family: inherit;
}

.draft-input--category {
  min-width: 140px;
}

.draft-input--amount {
  width: 90px;
}

.type-toggle {
  display: flex;
}

.type-toggle-btn {
  padding: var(--el-space-2) var(--el-space-3);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  font-weight: 600;
  font-size: var(--el-text-xs);
  letter-spacing: 0.05em;
  cursor: pointer;
}

.type-toggle .type-toggle-btn:first-child {
  border-radius: var(--el-radius-sm) 0 0 var(--el-radius-sm);
}

.type-toggle .type-toggle-btn:last-child {
  border-radius: 0 var(--el-radius-sm) var(--el-radius-sm) 0;
  border-left: none;
}

.type-toggle-btn--expense {
  color: var(--el-steel-light);
}

.type-toggle-btn--income {
  color: var(--el-positive);
}

.type-toggle-btn--expense.type-toggle-btn--active {
  background-color: var(--el-steel);
  color: var(--el-bg);
  border-color: var(--el-steel);
}

.type-toggle-btn--income.type-toggle-btn--active {
  background-color: var(--el-positive);
  color: var(--el-bg);
  border-color: var(--el-positive);
}

.import-button {
  padding: var(--el-space-2) var(--el-space-5);
  background-color: var(--el-copper);
  color: var(--el-bg);
  border: none;
  border-radius: var(--el-radius-sm);
  font-weight: 500;
  cursor: pointer;
}

.import-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.submit-error {
  color: var(--el-negative);
  font-size: var(--el-text-sm);
  margin: var(--el-space-2) 0 0;
}

@media (max-width: 640px) {
  .draft-table {
    display: block;
    overflow-x: auto;
    white-space: nowrap;
  }
}
</style>
