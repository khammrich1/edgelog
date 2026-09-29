<script setup>
import { reactive, ref, watch } from 'vue'
import { useFinancialEntriesStore } from '@/stores/financialEntries'
import { todayDateKey } from '@/utils/date'

const props = defineProps({
  // When set, the form edits this entry instead of creating a new one.
  entry: { type: Object, default: null }
})

const emit = defineEmits(['saved', 'cancel'])

const financialEntriesStore = useFinancialEntriesStore()

function emptyForm() {
  return {
    entry_type: 'expense',
    category: '',
    amount: '',
    date: todayDateKey(),
    firm: '',
    notes: ''
  }
}

const form = reactive(emptyForm())
const submitError = ref(null)

// Screenshot capture: extraction only prefills the form below for the user
// to review -- it never creates/saves an entry on its own. The uploaded
// file itself is kept in screenshotFile so it can be attached once the
// entry is saved, even if extraction failed or is unconfigured.
const screenshotState = ref('idle') // idle | loading | error
const screenshotError = ref(null)
const screenshotFile = ref(null)
const extractionHint = ref(null)
const dragActive = ref(false)
const fileInput = ref(null)

function populateFromEntry(entry) {
  if (!entry) {
    Object.assign(form, emptyForm())
    return
  }
  form.entry_type = entry.entry_type
  form.category = entry.category
  form.amount = String(entry.amount)
  form.date = entry.date
  form.firm = entry.firm || ''
  form.notes = entry.notes || ''
}

watch(() => props.entry, populateFromEntry, { immediate: true })

function applyExtraction(extracted) {
  if (extracted.entry_type) form.entry_type = extracted.entry_type
  if (extracted.category) form.category = extracted.category
  if (extracted.amount != null) form.amount = String(extracted.amount)
  if (extracted.date) form.date = extracted.date
  if (extracted.firm) form.firm = extracted.firm
  extractionHint.value = extracted.notes || null
}

async function handleScreenshotFile(file) {
  if (!file) return
  screenshotFile.value = file
  screenshotState.value = 'loading'
  screenshotError.value = null
  try {
    const extracted = await financialEntriesStore.parseFinancialScreenshot(file)
    applyExtraction(extracted)
    screenshotState.value = 'idle'
  } catch (error) {
    screenshotError.value =
      error.response?.data?.detail || 'Could not read that screenshot. Enter it manually below.'
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

function resetForm() {
  Object.assign(form, emptyForm())
  screenshotFile.value = null
  extractionHint.value = null
  screenshotError.value = null
}

async function submitForm() {
  submitError.value = null
  const payload = {
    entry_type: form.entry_type,
    category: form.category.trim(),
    amount: form.amount,
    date: form.date,
    firm: form.firm.trim() || null,
    notes: form.notes.trim() || null
  }

  try {
    const saved = props.entry
      ? await financialEntriesStore.updateEntry(props.entry.id, payload)
      : await financialEntriesStore.createEntry(payload)

    if (screenshotFile.value) {
      try {
        await financialEntriesStore.uploadEntryScreenshot(saved.id, screenshotFile.value)
      } catch (screenshotUploadError) {
        // The entry itself saved fine; only the screenshot attach failed.
        window.alert(
          screenshotUploadError.response?.data?.detail || 'Entry saved, but the screenshot could not be attached.'
        )
      }
    }

    if (!props.entry) resetForm()
    emit('saved', saved)
  } catch (error) {
    submitError.value = error.response?.data?.detail || 'Could not save that entry.'
  }
}

function cancelEdit() {
  emit('cancel')
}
</script>

<template>
  <form class="entry-form el-workstation" @submit.prevent="submitForm">
    <div class="el-workstation-header">
      <span class="el-workstation-title">{{ entry ? 'Edit Entry' : 'New Entry' }}</span>
    </div>

    <div
      class="el-dropzone screenshot-dropzone"
      :class="{ 'el-dropzone--active': dragActive, 'el-dropzone--loading': screenshotState === 'loading' }"
      tabindex="0"
      @dragover.prevent="dragActive = true"
      @dragleave.prevent="dragActive = false"
      @drop.prevent="onDrop"
      @paste="onPaste"
    >
      <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" class="screenshot-input" @change="onFilePicked" />
      <span v-if="screenshotState === 'loading'">Reading screenshot…</span>
      <span v-else>
        Drop or paste a receipt/payout screenshot, or
        <button type="button" class="screenshot-browse-button" @click="fileInput.click()">browse a file</button>
      </span>
    </div>
    <p v-if="screenshotError" class="submit-error">{{ screenshotError }}</p>
    <p v-if="extractionHint" class="extraction-hint">Note: {{ extractionHint }}</p>
    <p v-if="screenshotFile && screenshotState !== 'loading'" class="extraction-hint">
      Screenshot attached -- will be saved with this entry.
      <button type="button" class="toggle-more-button" @click="screenshotFile = null">Remove</button>
    </p>

    <div class="entry-form-grid">
      <div class="el-field entry-field--type">
        <label class="el-field-label">Type</label>
        <div class="type-toggle" role="group" aria-label="Entry type">
          <button
            type="button"
            class="type-toggle-btn type-toggle-btn--expense"
            :class="{ 'type-toggle-btn--active': form.entry_type === 'expense' }"
            @click="form.entry_type = 'expense'"
          >
            EXPENSE
          </button>
          <button
            type="button"
            class="type-toggle-btn type-toggle-btn--income"
            :class="{ 'type-toggle-btn--active': form.entry_type === 'income' }"
            @click="form.entry_type = 'income'"
          >
            INCOME
          </button>
        </div>
      </div>
      <div class="el-field entry-field--category">
        <label class="el-field-label">Category</label>
        <input v-model="form.category" type="text" placeholder="Category (e.g. Payout, Evaluation fee)" maxlength="200" required />
      </div>
      <div class="el-field">
        <label class="el-field-label">Amount</label>
        <input v-model="form.amount" type="number" step="any" min="0" placeholder="Amount" required />
      </div>
      <div class="el-field">
        <label class="el-field-label">Date</label>
        <input v-model="form.date" type="date" required />
      </div>
    </div>

    <div class="entry-form-grid entry-form-grid--secondary">
      <div class="el-field entry-field--firm">
        <label class="el-field-label">Firm / account</label>
        <input v-model="form.firm" type="text" placeholder="Firm / account (optional)" maxlength="200" />
      </div>
      <div class="el-field entry-field--notes">
        <label class="el-field-label">Notes</label>
        <textarea v-model="form.notes" rows="2" placeholder="Notes"></textarea>
      </div>
    </div>

    <div class="el-ticket-footer">
      <p v-if="submitError" class="submit-error">{{ submitError }}</p>
      <div class="el-ticket-footer-actions">
        <button v-if="entry" type="button" class="el-disclosure toggle-more-button" @click="cancelEdit">Cancel</button>
        <button type="submit" class="el-btn-primary">{{ entry ? 'Save Changes' : 'Add Entry' }}</button>
      </div>
    </div>
  </form>
</template>

<style scoped>
.entry-form {
  margin-bottom: var(--el-space-6);
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

.entry-form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: var(--el-space-3);
}

.entry-form-grid--secondary {
  margin-top: var(--el-space-3);
}

.entry-field--category {
  grid-column: span 2;
}

.entry-field--firm {
  grid-column: span 1;
}

.entry-field--notes {
  grid-column: span 3;
}

.entry-field--notes textarea {
  resize: vertical;
}

.type-toggle {
  display: flex;
  height: 38px;
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  overflow: hidden;
}

.type-toggle-btn {
  flex: 1;
  padding: 0 var(--el-space-2);
  background-color: var(--el-surface);
  color: var(--el-text-muted);
  border: none;
  font-weight: 600;
  font-size: var(--el-text-xs);
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all var(--el-transition-fast);
}

.type-toggle-btn + .type-toggle-btn {
  border-left: 1px solid var(--el-border);
}

.type-toggle-btn:hover:not(.type-toggle-btn--active) {
  color: var(--el-text);
  background-color: var(--el-surface-raised);
}

.type-toggle-btn--expense.type-toggle-btn--active {
  background-color: var(--el-steel);
  color: var(--el-bg);
}

.type-toggle-btn--income.type-toggle-btn--active {
  background-color: var(--el-positive);
  color: var(--el-bg);
}

.submit-error {
  color: var(--el-negative);
  font-size: var(--el-text-sm);
  margin: var(--el-space-2) 0 0;
}
</style>
