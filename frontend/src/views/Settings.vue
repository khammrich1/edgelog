<script setup>
import WorkspaceHeader from '@/components/common/WorkspaceHeader.vue'
import { onMounted, ref } from 'vue'
import { useTradesStore } from '@/stores/trades'

const tradesStore = useTradesStore()
const newSetupName = ref('')
const submitError = ref(null)
const loadError = ref(null)
const loading = ref(true)
const saving = ref(false)
const removing = ref(null)

async function loadSetups() {
  loading.value = true
  loadError.value = null
  try { await tradesStore.fetchSetups() }
  catch { loadError.value = 'Could not load your setups. Try again.' }
  finally { loading.value = false }
}
onMounted(loadSetups)

async function addSetup() {
  const name = newSetupName.value.trim()
  if (!name || saving.value) return
  saving.value = true
  submitError.value = null
  try {
    await tradesStore.createSetup(name)
    newSetupName.value = ''
  } catch (error) {
    submitError.value = error.response?.data?.detail || 'Could not add that setup.'
  } finally { saving.value = false }
}

async function removeSetup(setupId) {
  if (removing.value !== null) return
  removing.value = setupId
  submitError.value = null
  try { await tradesStore.deleteSetup(setupId) }
  catch { submitError.value = 'Could not remove that setup. Try again.' }
  finally { removing.value = null }
}
</script>

<template>
  <div class="settings-page el-page">
    <WorkspaceHeader title="Settings" eyebrow="Your workspace" />

    <section class="field-section el-workstation" :aria-busy="loading">
      <h2>Trade Setups</h2>
      <p class="section-hint">
        These appear as quick-pick options on the trade entry form. You can still type any
        setup by hand -- this list is a shortcut, not a restriction.
      </p>

      <p v-if="loading" class="section-hint" role="status">Loading your setups…</p>
      <div v-else-if="loadError" class="load-error" role="alert"><p>{{ loadError }}</p><button class="retry-button" @click="loadSetups">Try again</button></div>
      <ul v-else-if="tradesStore.setups.length > 0" class="setup-list">
        <li v-for="setup in tradesStore.setups" :key="setup.id" class="setup-row">
          <span class="setup-name">{{ setup.name }}</span>
          <button class="remove-item-button" :aria-label="`Remove ${setup.name}`" :disabled="removing !== null" @click="removeSetup(setup.id)">
            &times;
          </button>
        </li>
      </ul>
      <p v-else class="section-hint">No setups configured yet.</p>

      <form v-if="!loading && !loadError" class="add-item-form" @submit.prevent="addSetup">
        <input
          v-model="newSetupName"
          aria-label="New setup name"
          :disabled="saving"
          type="text"
          placeholder="Add a setup (e.g. Breakout, Reversal)"
          maxlength="200"
        />
        <button type="submit" :disabled="saving || !newSetupName.trim()">{{ saving ? 'Adding…' : 'Add setup' }}</button>
      </form>
      <p v-if="submitError" class="submit-error" role="alert">{{ submitError }}</p>
    </section>
  </div>
</template>

<style scoped>



.field-section {
  max-width: 680px;
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
  min-width: 44px;
  min-height: 44px;
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
.setup-name { overflow-wrap: anywhere; min-width: 0; }
.load-error { color: var(--el-text-muted); margin-bottom: 20px; }
.retry-button { color: var(--el-copper); text-decoration: underline; padding: 8px 0; }
@media (max-width: 640px) {
  .settings-page { padding: 20px 16px; }
  .add-item-form { flex-wrap: wrap; }
  .add-item-form input { flex-basis: 100%; }
}
</style>
