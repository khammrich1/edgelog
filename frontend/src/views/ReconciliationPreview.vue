<script setup>
import { computed, reactive, ref } from 'vue'
import WorkspaceHeader from '@/components/common/WorkspaceHeader.vue'
import { useReconciliationStore } from '@/stores/reconciliation'
import { todayDateKey } from '@/utils/date'
import { formatPrice, formatSignedDollars } from '@/utils/trades'
import { formatApiErrorDetail, parseExecutionBatch, SAMPLE_EXECUTIONS_JSON, sideLabel } from '@/utils/reconciliation'

const reconciliationStore = useReconciliationStore()

const form = reactive({
  account_id: '',
  date: todayDateKey(),
  executionsText: ''
})

const fileInput = ref(null)
const validationErrors = ref([])
const requestError = ref(null) // { kind: 'network' | 'auth' | 'request', lines: string[] }
const loading = ref(false)
const hasRunOnce = ref(false)
let lastPayload = null

function onFilePicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    form.executionsText = String(reader.result || '')
    validationErrors.value = []
  }
  reader.onerror = () => {
    validationErrors.value = ['Could not read that file.']
  }
  reader.readAsText(file)
}

function loadSample() {
  form.executionsText = SAMPLE_EXECUTIONS_JSON
  validationErrors.value = []
}

function clearBatch() {
  form.executionsText = ''
  validationErrors.value = []
}

function resetAll() {
  clearBatch()
  requestError.value = null
  reconciliationStore.clear()
  hasRunOnce.value = false
}

function classifyAndSetError(error) {
  if (!error.response) {
    requestError.value = { kind: 'network', lines: ['Could not reach the server. Check your connection and try again.'] }
    return
  }
  const status = error.response.status
  if (status === 401 || status === 403) {
    requestError.value = { kind: 'auth', lines: ['Your session is no longer valid for this action -- log in again and retry.'] }
    return
  }
  const lines = formatApiErrorDetail(error.response.data?.detail)
  requestError.value = { kind: 'request', lines: lines.length ? lines : [`Request failed (HTTP ${status}).`] }
}

async function sendPreview(payload) {
  loading.value = true
  requestError.value = null
  try {
    await reconciliationStore.preview(payload)
    hasRunOnce.value = true
  } catch (error) {
    classifyAndSetError(error)
  } finally {
    loading.value = false
  }
}

// Explicit action only -- pasting, uploading, or loading the sample never
// sends anything by itself; only this handler (the Preview button) does.
async function runPreview() {
  validationErrors.value = []
  requestError.value = null

  const accountId = Number(form.account_id)
  const errors = []
  if (!form.account_id || !Number.isInteger(accountId) || accountId <= 0) {
    errors.push('Enter a positive account ID.')
  }
  if (!form.date) {
    errors.push('Pick a date.')
  }
  const { executions, errors: batchErrors } = parseExecutionBatch(form.executionsText)
  errors.push(...batchErrors)

  if (errors.length > 0) {
    validationErrors.value = errors
    return
  }

  const payload = { account_id: accountId, date: form.date, executions }
  lastPayload = payload
  await sendPreview(payload)
}

function retry() {
  if (lastPayload) sendPreview(lastPayload)
}

const executions = computed(() => reconciliationStore.result?.executions || [])
const fillGroups = computed(() => reconciliationStore.result?.fill_groups || [])
const summary = computed(() => reconciliationStore.result?.summary || null)

const GROUPING_STATUS_LABEL = { confident: 'Confident', needs_confirmation: 'Needs confirmation' }
const MATCH_STATUS_LABEL = {
  candidate_match: 'Candidate match',
  ambiguous_candidate_match: 'Ambiguous candidate',
  unplanned: 'Unplanned',
  already_imported: 'Already imported'
}
const GROUPING_BASIS_LABEL = {
  shared_order_id: 'Shared order ID',
  inferred_open_close_pair: 'Inferred open/close pair',
  ungrouped_single: 'Ungrouped (single)',
  ambiguous: 'Ambiguous'
}
</script>

<template>
  <div class="reconciliation-page el-page">
    <WorkspaceHeader
      title="Reconciliation Preview"
      eyebrow="Broker execution review"
      description="Paste or upload broker execution data to preview proposed groupings and candidate journal-trade matches. Nothing here is imported, saved, or confirmed."
    />

    <p class="readonly-banner">
      Read-only preview. This screen never writes to your journal, creates a trade, or sends anything to a broker --
      it only calls the existing read-only preview endpoint and shows you the result.
    </p>

    <section class="el-workstation">
      <div class="el-workstation-header">
        <span class="el-workstation-title">Execution batch</span>
      </div>

      <div class="input-grid">
        <div class="el-field">
          <label class="el-field-label">Account ID</label>
          <input v-model="form.account_id" type="number" min="1" placeholder="e.g. 28592949" />
          <span class="el-field-hint">Client-supplied, unverified -- not proof of broker account ownership.</span>
        </div>
        <div class="el-field">
          <label class="el-field-label">Date</label>
          <input v-model="form.date" type="date" />
        </div>
      </div>

      <div class="el-field">
        <div class="el-field-label-row">
          <label class="el-field-label">Executions (JSON array)</label>
          <div class="batch-actions">
            <input ref="fileInput" type="file" accept="application/json,.json" class="file-input" @change="onFilePicked" />
            <button type="button" class="toggle-more-button" @click="fileInput.click()">Upload file</button>
            <button type="button" class="toggle-more-button" @click="loadSample">Load sample fixture</button>
            <button type="button" class="toggle-more-button" @click="clearBatch">Clear</button>
          </div>
        </div>
        <textarea
          v-model="form.executionsText"
          rows="10"
          class="executions-textarea"
          placeholder='Paste a JSON array, e.g. [{"id": 1, "accountId": 123, "contractId": "CON.F.US.MNQ.Z25", "creationTimestamp": "2026-10-16T14:30:00Z", "price": 21000, "size": 1, "side": 0}]'
          spellcheck="false"
        ></textarea>
      </div>

      <ul v-if="validationErrors.length" class="error-list" role="alert">
        <li v-for="(error, i) in validationErrors" :key="i">{{ error }}</li>
      </ul>

      <div class="el-ticket-footer">
        <div class="el-ticket-footer-actions">
          <button type="button" class="el-btn-primary" :disabled="loading" @click="runPreview">
            {{ loading ? 'Running preview…' : 'Run Preview' }}
          </button>
          <button v-if="reconciliationStore.result" type="button" class="btn-chip btn-chip--ghost" @click="resetAll">
            Start over
          </button>
        </div>
      </div>

      <div v-if="requestError" class="request-error" role="alert">
        <p v-for="(line, i) in requestError.lines" :key="i">{{ line }}</p>
        <button v-if="requestError.kind !== 'auth'" type="button" class="btn-chip btn-chip--ghost" @click="retry">
          Retry
        </button>
      </div>
    </section>

    <p v-if="!reconciliationStore.result && !loading && !requestError && hasRunOnce === false" class="empty-hint">
      No preview run yet. Paste or upload an execution batch above and click Run Preview.
    </p>

    <template v-if="reconciliationStore.result">
      <section class="el-workstation summary-bar">
        <div class="el-workstation-header">
          <span class="el-workstation-title">Summary</span>
        </div>
        <div class="summary-grid">
          <div class="info-item"><span class="info-label">Executions</span><span class="info-value">{{ summary.total_executions }}</span></div>
          <div class="info-item"><span class="info-label">Voided</span><span class="info-value">{{ summary.voided_count }}</span></div>
          <div class="info-item"><span class="info-label">Already imported</span><span class="info-value">{{ summary.already_imported_count }}</span></div>
          <div class="info-item"><span class="info-label">Confident groups</span><span class="info-value">{{ summary.confident_groups }}</span></div>
          <div class="info-item"><span class="info-label">Needs confirmation</span><span class="info-value">{{ summary.needs_confirmation_groups }}</span></div>
          <div class="info-item"><span class="info-label">Candidate matches</span><span class="info-value">{{ summary.candidate_plan_matches }}</span></div>
          <div class="info-item"><span class="info-label">Ambiguous matches</span><span class="info-value">{{ summary.ambiguous_plan_matches }}</span></div>
          <div class="info-item"><span class="info-label">Unplanned</span><span class="info-value">{{ summary.unplanned_groups }}</span></div>
          <div class="info-item"><span class="info-label">Candidate P&amp;L groups</span><span class="info-value">{{ summary.groups_with_candidate_pnl }}</span></div>
        </div>
      </section>

      <section class="el-workstation">
        <div class="el-workstation-header">
          <span class="el-workstation-title">A. Broker-reported execution facts</span>
        </div>
        <p class="section-hint">Exactly what the broker batch reported for each fill -- unmodified, confirmed facts.</p>
        <div class="table-scroll">
          <table class="recon-table">
            <thead>
              <tr>
                <th>ID</th><th>Order ID</th><th>Contract</th><th>Time</th><th>Side</th><th>Size</th><th>Price</th>
                <th>Fees</th><th>Commissions</th><th>Broker P&amp;L</th><th>Flags</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="execution in executions" :key="execution.id" :class="{ 'row--voided': execution.voided }">
                <td>{{ execution.id }}</td>
                <td>{{ execution.order_id ?? '—' }}</td>
                <td>{{ execution.contract_id }}</td>
                <td>{{ new Date(execution.creation_timestamp).toLocaleString() }}</td>
                <td>{{ sideLabel(execution.side) }}</td>
                <td>{{ execution.size }}</td>
                <td>{{ formatPrice(execution.price) }}</td>
                <td>{{ execution.fees != null ? formatPrice(execution.fees) : '—' }}</td>
                <td>{{ execution.commissions != null ? formatPrice(execution.commissions) : '—' }}</td>
                <td>{{ execution.broker_profit_and_loss != null ? formatSignedDollars(execution.broker_profit_and_loss) : '—' }}</td>
                <td>
                  <span v-if="execution.voided" class="el-badge el-badge--warning">Voided</span>
                  <span v-if="execution.already_imported" class="el-badge">
                    Already imported<template v-if="execution.already_imported_trade_id"> (trade #{{ execution.already_imported_trade_id }})</template>
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="el-workstation">
        <div class="el-workstation-header">
          <span class="el-workstation-title">B. Grouping proposals</span>
        </div>
        <p class="section-hint">Proposed groupings of the executions above into logical fills -- a proposal, never a confirmed grouping.</p>
        <div class="table-scroll">
          <table class="recon-table">
            <thead>
              <tr><th>Executions</th><th>Basis</th><th>Status</th><th>Note</th></tr>
            </thead>
            <tbody>
              <tr v-for="(group, i) in fillGroups" :key="i" :class="{ 'row--voided': group.voided }">
                <td>{{ group.execution_ids.join(', ') }}</td>
                <td>{{ GROUPING_BASIS_LABEL[group.grouping_basis] || group.grouping_basis }}</td>
                <td>
                  <span class="el-badge" :class="`status-badge--${group.grouping_status}`">
                    {{ GROUPING_STATUS_LABEL[group.grouping_status] || group.grouping_status }}
                  </span>
                  <span v-if="group.voided" class="el-badge el-badge--warning">Voided</span>
                </td>
                <td>{{ group.grouping_note }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="el-workstation">
        <div class="el-workstation-header">
          <span class="el-workstation-title">C. Candidate journal-trade association</span>
        </div>
        <p class="section-hint">
          Proposed matches against your existing journaled trades only -- not your pre-trade Plans, and never a
          confirmed or verified association. Treat every row here as a candidate to review, not a fact.
        </p>
        <div class="table-scroll">
          <table class="recon-table">
            <thead>
              <tr><th>Executions</th><th>Match status</th><th>Candidate trade IDs</th><th>Note</th><th>P&amp;L</th></tr>
            </thead>
            <tbody>
              <tr v-for="(group, i) in fillGroups" :key="i">
                <td>{{ group.execution_ids.join(', ') }}</td>
                <td>
                  <span class="el-badge" :class="`status-badge--${group.plan_match_status}`">
                    {{ MATCH_STATUS_LABEL[group.plan_match_status] || group.plan_match_status }}
                  </span>
                </td>
                <td>{{ group.candidate_trade_ids.length ? group.candidate_trade_ids.join(', ') : '—' }}</td>
                <td>{{ group.plan_match_note }}</td>
                <td>
                  <template v-if="group.pnl_status === 'candidate'">
                    <span class="pnl-candidate">{{ formatSignedDollars(group.candidate_gross_pnl) }} (candidate gross)</span>
                  </template>
                  <template v-else>
                    <span class="pnl-unresolved">Unresolved{{ group.pnl_unresolved_reason ? ` -- ${group.pnl_unresolved_reason}` : '' }}</span>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.readonly-banner {
  margin: 0 0 var(--el-space-4);
  padding: var(--el-space-3) var(--el-space-4);
  background: var(--el-surface-sunken);
  border: 1px solid var(--el-border);
  border-left: 3px solid var(--el-copper);
  border-radius: var(--el-radius-sm);
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
}

.input-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--el-space-3);
  margin-bottom: var(--el-space-4);
}

.el-field-hint {
  display: block;
  margin-top: var(--el-space-1);
  color: var(--el-text-subtle);
  font-size: var(--el-text-xs);
}

.el-field-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--el-space-2);
}

.batch-actions {
  display: flex;
  gap: var(--el-space-3);
}

.file-input {
  display: none;
}

.executions-textarea {
  width: 100%;
  margin-top: var(--el-space-2);
  padding: var(--el-space-3);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  color: var(--el-text);
  font-family: var(--el-font-mono);
  font-size: var(--el-text-sm);
  resize: vertical;
}

.error-list {
  margin: var(--el-space-3) 0 0;
  padding-left: 1.2em;
  color: var(--el-negative);
  font-size: var(--el-text-sm);
}

.request-error {
  margin-top: var(--el-space-3);
  padding: var(--el-space-3);
  background: var(--el-surface-sunken);
  border: 1px solid var(--el-negative);
  border-radius: var(--el-radius-sm);
  color: var(--el-negative);
  font-size: var(--el-text-sm);
}

.request-error p {
  margin: 0 0 var(--el-space-2);
}

.empty-hint {
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  margin: var(--el-space-4) 0;
}

.summary-bar .summary-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-4);
}

.section-hint {
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  margin: 0 0 var(--el-space-3);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: var(--el-text-sm);
}

.info-label {
  font-size: var(--el-text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--el-text-subtle);
}

.info-value {
  color: var(--el-text);
  font-variant-numeric: tabular-nums;
}

.table-scroll {
  overflow-x: auto;
}

.recon-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--el-text-sm);
}

.recon-table th {
  text-align: left;
  padding: var(--el-space-2);
  color: var(--el-text-subtle);
  font-size: var(--el-text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--el-border);
  white-space: nowrap;
}

.recon-table td {
  padding: var(--el-space-2);
  border-bottom: 1px solid var(--el-border);
  vertical-align: middle;
  white-space: nowrap;
}

.row--voided {
  opacity: 0.6;
}

.status-badge--confident,
.status-badge--candidate_match {
  color: var(--el-positive);
}

.status-badge--needs_confirmation,
.status-badge--ambiguous_candidate_match {
  color: var(--el-copper);
}

.status-badge--unplanned {
  color: var(--el-text-subtle);
}

.status-badge--already_imported {
  color: var(--el-negative);
}

.pnl-candidate {
  color: var(--el-text);
}

.pnl-unresolved {
  color: var(--el-text-subtle);
  font-style: italic;
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
  .batch-actions {
    flex-wrap: wrap;
  }
}
</style>
