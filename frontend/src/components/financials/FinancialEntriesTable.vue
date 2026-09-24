<script setup>
import { onUnmounted, reactive } from 'vue'
import { useFinancialEntriesStore } from '@/stores/financialEntries'
import { formatSignedDollars, resultClass } from '@/utils/trades'

const props = defineProps({
  entries: { type: Array, required: true }
})

const emit = defineEmits(['edit'])

const financialEntriesStore = useFinancialEntriesStore()

const screenshotUrls = reactive({}) // entryId -> object URL
const entryScreenshotInputs = {} // entryId -> <input type=file> element, not reactive

function setEntryScreenshotInputRef(entryId, el) {
  entryScreenshotInputs[entryId] = el
}

function triggerEntryScreenshotPicker(entryId) {
  entryScreenshotInputs[entryId]?.click()
}

function revokeEntryScreenshot(entryId) {
  if (screenshotUrls[entryId]) {
    URL.revokeObjectURL(screenshotUrls[entryId])
    delete screenshotUrls[entryId]
  }
}

async function loadEntryScreenshot(entry) {
  if (!entry.has_screenshot || screenshotUrls[entry.id]) return
  screenshotUrls[entry.id] = await financialEntriesStore.fetchEntryScreenshotObjectUrl(entry.id)
}

function openEntryScreenshot(entryId) {
  if (screenshotUrls[entryId]) window.open(screenshotUrls[entryId], '_blank')
}

async function onEntryScreenshotPicked(entry, event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  try {
    await financialEntriesStore.uploadEntryScreenshot(entry.id, file)
    revokeEntryScreenshot(entry.id)
    const updated = props.entries.find((e) => e.id === entry.id)
    if (updated) await loadEntryScreenshot(updated)
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Could not save that screenshot.')
  }
}

async function removeEntryScreenshot(entry) {
  if (!window.confirm('Remove this screenshot?')) return
  await financialEntriesStore.deleteEntryScreenshot(entry.id)
  revokeEntryScreenshot(entry.id)
}

async function removeEntry(entry) {
  if (!window.confirm(`Delete this ${entry.category} entry? This cannot be undone.`)) return
  await financialEntriesStore.deleteEntry(entry.id)
  revokeEntryScreenshot(entry.id)
}

function signedAmount(entry) {
  return entry.entry_type === 'income' ? Number(entry.amount) : -Number(entry.amount)
}

onUnmounted(() => {
  Object.keys(screenshotUrls).forEach((id) => revokeEntryScreenshot(Number(id)))
})

defineExpose({ loadEntryScreenshot })
</script>

<template>
  <table class="entries-table">
    <thead>
      <tr>
        <th>Date</th>
        <th>Type</th>
        <th>Category</th>
        <th>Firm / Account</th>
        <th>Amount</th>
        <th>Screenshot</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="entry in entries" :key="entry.id">
        <td>{{ entry.date }}</td>
        <td>
          <span class="type-badge" :class="`type-badge--${entry.entry_type}`">
            {{ entry.entry_type === 'income' ? 'Income' : 'Expense' }}
          </span>
        </td>
        <td>{{ entry.category }}</td>
        <td>{{ entry.firm || '—' }}</td>
        <td class="amount-cell" :class="resultClass(signedAmount(entry))">
          {{ formatSignedDollars(signedAmount(entry)) }}
        </td>
        <td>
          <img
            v-if="screenshotUrls[entry.id]"
            :src="screenshotUrls[entry.id]"
            alt="Entry screenshot"
            class="entry-screenshot-thumb"
            @click="openEntryScreenshot(entry.id)"
          />
          <button v-else-if="entry.has_screenshot" type="button" class="link-button" @click="loadEntryScreenshot(entry)">
            View
          </button>
          <input
            :ref="(el) => setEntryScreenshotInputRef(entry.id, el)"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            class="screenshot-input"
            @change="onEntryScreenshotPicked(entry, $event)"
          />
          <div class="screenshot-actions">
            <button type="button" class="link-button" @click="triggerEntryScreenshotPicker(entry.id)">
              {{ entry.has_screenshot ? 'Replace' : '+ Add' }}
            </button>
            <button v-if="entry.has_screenshot" type="button" class="link-button link-button--danger" @click="removeEntryScreenshot(entry)">
              Remove
            </button>
          </div>
        </td>
        <td class="actions-cell">
          <button type="button" class="btn-chip btn-chip--ghost" @click="$emit('edit', entry)">Edit</button>
          <button type="button" class="btn-chip btn-chip--danger" @click="removeEntry(entry)">Delete</button>
        </td>
      </tr>
      <tr v-if="entries.length === 0">
        <td colspan="7" class="empty-hint">No entries yet this year.</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.entries-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--el-text-sm);
}

.entries-table th {
  text-align: left;
  padding: var(--el-space-2) var(--el-space-3);
  color: var(--el-text-subtle);
  font-size: var(--el-text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--el-border);
}

.entries-table td {
  padding: var(--el-space-2) var(--el-space-3);
  border-bottom: 1px solid var(--el-border);
  color: var(--el-text);
  vertical-align: middle;
}

.type-badge {
  font-size: var(--el-text-xs);
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 2px var(--el-space-2);
  border-radius: var(--el-radius-sm);
}

.type-badge--income {
  color: var(--el-positive);
  border: 1px solid var(--el-positive);
}

.type-badge--expense {
  color: var(--el-steel-light);
  border: 1px solid var(--el-steel);
}

.amount-cell {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.result-positive {
  color: var(--el-positive);
}

.result-negative {
  color: var(--el-negative);
}

.entry-screenshot-thumb {
  max-width: 48px;
  max-height: 32px;
  border-radius: var(--el-radius-sm);
  cursor: zoom-in;
  display: block;
  margin-bottom: var(--el-space-1);
}

.screenshot-input {
  display: none;
}

.screenshot-actions {
  display: flex;
  gap: var(--el-space-2);
}

.link-button {
  background: none;
  border: none;
  padding: 0;
  color: var(--el-copper);
  font-size: var(--el-text-xs);
  cursor: pointer;
}

.link-button--danger:hover {
  color: var(--el-negative);
}

.actions-cell {
  display: flex;
  gap: var(--el-space-2);
  white-space: nowrap;
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

.btn-chip--ghost:hover {
  border-color: var(--el-copper);
  color: var(--el-copper);
}

.btn-chip--danger {
  border-color: var(--el-negative);
  color: var(--el-negative);
}

.btn-chip--danger:hover {
  background-color: rgba(248, 113, 113, 0.12);
}

.empty-hint {
  text-align: center;
  color: var(--el-text-subtle);
  padding: var(--el-space-6);
}

@media (max-width: 640px) {
  .entries-table {
    display: block;
    overflow-x: auto;
    white-space: nowrap;
  }
}
</style>
