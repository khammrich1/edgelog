<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useJournalStore } from '@/stores/journal'
import TradesSection from '@/components/journal/TradesSection.vue'

const route = useRoute()
const router = useRouter()
const journalStore = useJournalStore()

const marketBiasDraft = ref('')
const newChecklistLabel = ref('')
const biasChartObjectUrl = ref(null)
const uploadError = ref(null)

const day = computed(() => journalStore.currentDay)
const isLocked = computed(() => day.value?.status === 'locked')

const formattedDate = computed(() => {
  // Parsed as local time (not UTC) so the displayed weekday can't shift by
  // a day relative to the URL's date.
  const [year, month, dayOfMonth] = route.params.date.split('-').map(Number)
  const localDate = new Date(year, month - 1, dayOfMonth)
  return localDate.toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
})

async function loadDay() {
  await journalStore.fetchChecklistItems()
  const data = await journalStore.fetchDay(route.params.date)
  marketBiasDraft.value = data.market_bias ?? ''
  await refreshBiasChartPreview()
}

async function refreshBiasChartPreview() {
  revokeBiasChartPreview()
  if (day.value?.has_bias_chart) {
    biasChartObjectUrl.value = await journalStore.fetchBiasChartObjectUrl(route.params.date)
  }
}

function revokeBiasChartPreview() {
  if (biasChartObjectUrl.value) {
    URL.revokeObjectURL(biasChartObjectUrl.value)
    biasChartObjectUrl.value = null
  }
}

async function setSleepQuality(value) {
  await journalStore.updateDay(route.params.date, { sleep_quality: value })
}

async function setMood(value) {
  await journalStore.updateDay(route.params.date, { mood: value })
}

async function saveMarketBias() {
  await journalStore.updateDay(route.params.date, { market_bias: marketBiasDraft.value })
}

async function toggleChecklistItem(itemId, completed) {
  await journalStore.toggleChecklistItem(route.params.date, itemId, completed)
}

async function addChecklistItem() {
  const label = newChecklistLabel.value.trim()
  if (!label) return
  await journalStore.createChecklistItem(label)
  newChecklistLabel.value = ''
  // The new item only becomes part of *this* day's checklist once the day
  // is re-synced against the active item list.
  await journalStore.fetchDay(route.params.date)
}

async function removeChecklistItem(itemId) {
  await journalStore.deleteChecklistItem(itemId)
}

async function toggleLock() {
  if (isLocked.value) {
    await journalStore.unlockDay(route.params.date)
  } else {
    await journalStore.lockDay(route.params.date)
  }
}

async function handleFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return
  uploadError.value = null
  try {
    await journalStore.uploadBiasChart(route.params.date, file)
    await refreshBiasChartPreview()
  } catch (error) {
    uploadError.value = error.response?.data?.detail || 'Could not upload the chart image.'
  } finally {
    event.target.value = ''
  }
}

async function removeBiasChart() {
  await journalStore.deleteBiasChart(route.params.date)
  await refreshBiasChartPreview()
}

function backToCalendar() {
  router.push('/journal')
}

watch(() => route.params.date, loadDay)
loadDay()

onBeforeUnmount(revokeBiasChartPreview)
</script>

<template>
  <div v-if="day" class="journal-day">
    <div class="day-header">
      <button class="back-link" @click="backToCalendar">&lsaquo; Back to Calendar</button>
      <h1>{{ formattedDate }}</h1>
      <div class="header-actions">
        <span class="status-badge" :class="isLocked ? 'status-badge--locked' : 'status-badge--draft'">
          {{ isLocked ? 'Locked' : 'Draft' }}
        </span>
        <button class="lock-button" @click="toggleLock">{{ isLocked ? 'Unlock' : 'Lock' }}</button>
      </div>
    </div>

    <p v-if="isLocked" class="locked-hint">This day is locked. Unlock it to make changes.</p>

    <section class="field-section">
      <h2>Sleep quality</h2>
      <div class="scale-buttons">
        <button
          v-for="value in [1, 2, 3, 4, 5]"
          :key="`sleep-${value}`"
          class="scale-button"
          :class="{ 'scale-button--selected': day.sleep_quality === value }"
          :disabled="isLocked"
          @click="setSleepQuality(value)"
        >
          {{ value }}
        </button>
      </div>
    </section>

    <section class="field-section">
      <h2>Mood</h2>
      <div class="scale-buttons">
        <button
          v-for="value in [1, 2, 3, 4, 5]"
          :key="`mood-${value}`"
          class="scale-button"
          :class="{ 'scale-button--selected': day.mood === value }"
          :disabled="isLocked"
          @click="setMood(value)"
        >
          {{ value }}
        </button>
      </div>
    </section>

    <section class="field-section">
      <h2>Morning checklist</h2>
      <ul class="checklist">
        <li v-for="entry in day.checklist" :key="entry.checklist_item_id" class="checklist-row">
          <label class="checklist-label">
            <input
              type="checkbox"
              :checked="entry.completed"
              :disabled="isLocked"
              @change="toggleChecklistItem(entry.checklist_item_id, $event.target.checked)"
            />
            {{ entry.label }}
          </label>
          <button
            class="remove-item-button"
            :disabled="isLocked"
            title="Remove from checklist"
            @click="removeChecklistItem(entry.checklist_item_id)"
          >
            &times;
          </button>
        </li>
      </ul>
      <form class="add-item-form" @submit.prevent="addChecklistItem">
        <input
          v-model="newChecklistLabel"
          type="text"
          placeholder="Add a checklist item"
          :disabled="isLocked"
          maxlength="200"
        />
        <button type="submit" :disabled="isLocked || !newChecklistLabel.trim()">Add</button>
      </form>
    </section>

    <section class="field-section">
      <h2>Market bias / thesis</h2>
      <textarea
        v-model="marketBiasDraft"
        rows="4"
        placeholder="What's the plan today?"
        :disabled="isLocked"
      ></textarea>
      <button
        class="save-button"
        :disabled="isLocked || marketBiasDraft === (day.market_bias ?? '')"
        @click="saveMarketBias"
      >
        Save
      </button>
    </section>

    <section class="field-section">
      <h2>Bias chart</h2>
      <img v-if="biasChartObjectUrl" :src="biasChartObjectUrl" alt="Bias chart" class="bias-chart-preview" />
      <p v-if="uploadError" class="upload-error">{{ uploadError }}</p>
      <div class="chart-actions">
        <label class="upload-button" :class="{ 'upload-button--disabled': isLocked }">
          {{ day.has_bias_chart ? 'Replace image' : 'Upload image' }}
          <input type="file" accept="image/png,image/jpeg,image/webp" :disabled="isLocked" @change="handleFileSelected" hidden />
        </label>
        <button v-if="day.has_bias_chart" class="remove-item-button" :disabled="isLocked" @click="removeBiasChart">
          Remove
        </button>
      </div>
    </section>

    <TradesSection :date="route.params.date" :locked="isLocked" />
  </div>
</template>

<style scoped>
.journal-day {
  padding: var(--el-space-8);
  max-width: 640px;
  margin: 0 auto;
}

.back-link {
  background: none;
  border: none;
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  cursor: pointer;
  padding: 0;
  margin-bottom: var(--el-space-4);
}

.back-link:hover {
  color: var(--el-copper);
}

.day-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--el-space-3);
  margin-bottom: var(--el-space-2);
}

.day-header h1 {
  font-size: var(--el-text-xl);
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--el-space-3);
}

.status-badge {
  font-size: var(--el-text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: var(--el-space-1) var(--el-space-3);
  border-radius: var(--el-radius-sm);
}

.status-badge--draft {
  color: var(--el-copper);
  border: 1px solid var(--el-copper);
}

.status-badge--locked {
  color: var(--el-steel-light);
  border: 1px solid var(--el-steel);
}

.lock-button {
  padding: var(--el-space-2) var(--el-space-4);
  background-color: transparent;
  color: var(--el-text);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  font-size: var(--el-text-sm);
  cursor: pointer;
}

.lock-button:hover {
  border-color: var(--el-copper);
  color: var(--el-copper);
}

.locked-hint {
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  margin-bottom: var(--el-space-6);
}

.field-section {
  margin-bottom: var(--el-space-8);
}

.field-section h2 {
  font-size: var(--el-text-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--el-text-muted);
  margin: 0 0 var(--el-space-3);
}

.scale-buttons {
  display: flex;
  gap: var(--el-space-2);
}

.scale-button {
  width: 40px;
  height: 40px;
  background-color: var(--el-surface);
  color: var(--el-text);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  cursor: pointer;
}

.scale-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.scale-button--selected {
  border-color: var(--el-copper);
  color: var(--el-copper);
  background-color: rgba(184, 115, 51, 0.1);
}

.checklist {
  list-style: none;
  margin: 0 0 var(--el-space-4);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--el-space-2);
}

.checklist-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--el-space-3);
}

.checklist-label {
  display: flex;
  align-items: center;
  gap: var(--el-space-2);
  font-size: var(--el-text-base);
  color: var(--el-text);
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

.add-item-form {
  display: flex;
  gap: var(--el-space-2);
}

.add-item-form input {
  flex: 1;
  padding: var(--el-space-2) var(--el-space-3);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  color: var(--el-text);
  font-size: var(--el-text-sm);
}

.add-item-form button {
  padding: var(--el-space-2) var(--el-space-4);
  background-color: transparent;
  color: var(--el-copper);
  border: 1px solid var(--el-copper);
  border-radius: var(--el-radius-sm);
  cursor: pointer;
}

.add-item-form button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.field-section textarea {
  width: 100%;
  padding: var(--el-space-3);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  color: var(--el-text);
  font-size: var(--el-text-base);
  font-family: inherit;
  resize: vertical;
  margin-bottom: var(--el-space-3);
}

.save-button {
  padding: var(--el-space-2) var(--el-space-6);
  background-color: var(--el-copper);
  color: var(--el-bg);
  border: none;
  border-radius: var(--el-radius-sm);
  font-weight: 500;
  cursor: pointer;
}

.save-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.bias-chart-preview {
  max-width: 100%;
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-md);
  margin-bottom: var(--el-space-3);
}

.upload-error {
  color: var(--el-negative);
  font-size: var(--el-text-sm);
  margin: 0 0 var(--el-space-3);
}

.chart-actions {
  display: flex;
  gap: var(--el-space-3);
}

.upload-button {
  padding: var(--el-space-2) var(--el-space-4);
  background-color: transparent;
  color: var(--el-text);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  font-size: var(--el-text-sm);
  cursor: pointer;
}

.upload-button:hover {
  border-color: var(--el-copper);
  color: var(--el-copper);
}

.upload-button--disabled {
  cursor: not-allowed;
  opacity: 0.5;
  pointer-events: none;
}
</style>
