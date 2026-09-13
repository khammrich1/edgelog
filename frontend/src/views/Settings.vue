<script setup>
import { onMounted, ref } from 'vue'
import { useTradesStore } from '@/stores/trades'

const tradesStore = useTradesStore()
const newSetupName = ref('')
const submitError = ref(null)

onMounted(() => {
  tradesStore.fetchSetups()
})

async function addSetup() {
  const name = newSetupName.value.trim()
  if (!name) return
  submitError.value = null
  try {
    await tradesStore.createSetup(name)
    newSetupName.value = ''
  } catch (error) {
    submitError.value = error.response?.data?.detail || 'Could not add that setup.'
  }
}

async function removeSetup(setupId) {
  await tradesStore.deleteSetup(setupId)
}
</script>

<template>
  <div class="settings-page">
    <h1>Settings</h1>

    <section class="field-section">
      <h2>Trade Setups</h2>
      <p class="section-hint">
        These appear as quick-pick options on the trade entry form. You can still type any
        setup by hand -- this list is a shortcut, not a restriction.
      </p>

      <ul v-if="tradesStore.setups.length > 0" class="setup-list">
        <li v-for="setup in tradesStore.setups" :key="setup.id" class="setup-row">
          <span class="setup-name">{{ setup.name }}</span>
          <button class="remove-item-button" title="Remove setup" @click="removeSetup(setup.id)">
            &times;
          </button>
        </li>
      </ul>
      <p v-else class="section-hint">No setups configured yet.</p>

      <form class="add-item-form" @submit.prevent="addSetup">
        <input
          v-model="newSetupName"
          type="text"
          placeholder="Add a setup (e.g. Breakout, Reversal)"
          maxlength="200"
        />
        <button type="submit" :disabled="!newSetupName.trim()">Add</button>
      </form>
      <p v-if="submitError" class="submit-error">{{ submitError }}</p>
    </section>
  </div>
</template>

<style scoped>
.settings-page {
  padding: var(--el-space-8);
  max-width: 640px;
  margin: 0 auto;
}

.settings-page h1 {
  font-size: var(--el-text-xl);
  margin: 0 0 var(--el-space-6);
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

.section-hint {
  font-size: var(--el-text-sm);
  color: var(--el-text-muted);
  margin: 0 0 var(--el-space-4);
}

.setup-list {
  list-style: none;
  margin: 0 0 var(--el-space-4);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--el-space-2);
}

.setup-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--el-space-3);
  padding: var(--el-space-2) var(--el-space-3);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
}

.setup-name {
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

.submit-error {
  color: var(--el-negative);
  font-size: var(--el-text-sm);
  margin-top: var(--el-space-2);
}
</style>
