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
  <form class="entry-form" @submit.prevent="submitForm">
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

    <div class="entry-form-primary">
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
      <input v-model="form.category" type="text" placeholder="Category (e.g. Payout, Evaluation fee)" maxlength="200" required />
      <input v-model="form.amount" type="number" step="any" min="0" placeholder="Amount" required />
      <input v-model="form.date" type="date" required />
      <button type="submit">{{ entry ? 'Save changes' : 'Add entry' }}</button>
    </div>

    <div class="entry-form-secondary">
      <input v-model="form.firm" type="text" placeholder="Firm / account (optional)" maxlength="200" />
      <textarea v-model="form.notes" rows="2" placeholder="Notes"></textarea>
    </div>

    <button v-if="entry" type="button" class="toggle-more-button" @click="cancelEdit">Cancel</button>
    <p v-if="submitError" class="submit-error">{{ submitError }}</p>
  </form>
</template>

<style scoped>
.entry-form {
  margin-bottom: var(--el-space-6);
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

.entry-form-primary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-2);
}

.entry-form-primary input {
  padding: var(--el-space-2) var(--el-space-3);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  color: var(--el-text);
  font-size: var(--el-text-sm);
}

.entry-form-primary input[type='text'] {
  width: 200px;
}

.entry-form-primary input[type='number'] {
  width: 110px;
}

.entry-form-primary button[type='submit'] {
  padding: var(--el-space-2) var(--el-space-5);
  background-color: var(--el-copper);
  color: var(--el-bg);
  border: none;
  border-radius: var(--el-radius-sm);
  font-weight: 500;
  cursor: pointer;
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

.entry-form-secondary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-2);
  margin-top: var(--el-space-2);
}

.entry-form-secondary input,
.entry-form-secondary textarea {
  padding: var(--el-space-2) var(--el-space-3);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  color: var(--el-text);
  font-size: var(--el-text-sm);
  font-family: inherit;
}

.entry-form-secondary input {
  width: 220px;
}

.entry-form-secondary textarea {
  flex: 1 0 100%;
  resize: vertical;
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

.submit-error {
  color: var(--el-negative);
  font-size: var(--el-text-sm);
  margin: var(--el-space-2) 0 0;
}
</style>
