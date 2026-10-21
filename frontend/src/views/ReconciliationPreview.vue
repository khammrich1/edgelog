<script setup>
import { computed, ref } from 'vue'
import { useReconciliationStore } from '@/stores/reconciliation'
import { parseExecutionsInput, formatPreviewRequestError } from '@/utils/reconciliation'
import { formatSignedDollars, resultClass } from '@/utils/trades'
import { todayDateKey } from '@/utils/date'
import WorkspaceHeader from '@/components/common/WorkspaceHeader.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseButton from '@/components/common/BaseButton.vue'

// DF-VS1.5 Step 3B (issue #97): a read-only view onto the existing
// reconciliation preview API (PR #91). This component never writes --
// the only network call it makes is the preview POST itself, which the
// backend guarantees makes zero database writes. See
// app.services.reconciliation's own docstring for the three-stage
// (facts / grouping / journal-match) doctrine this view mirrors.

const reconciliationStore = useReconciliationStore()

const accountId = ref('')
const date = ref(todayDateKey())
const executionsText = ref('')
const inputError = ref(null)
const fileInput = ref(null)

const requestState = ref('idle') // idle | loading | success | error
const requestError = ref(null)
const lastPayload = ref(null)

const preview = computed(() => reconciliationStore.lastPreview)

function onFilePicked(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    executionsText.value = String(reader.result ?? '')
  }
  reader.readAsText(file)
  event.target.value = ''
}

function buildPayload() {
  inputError.value = null

  const trimmedAccountId = String(accountId.value ?? '').trim()
  if (!trimmedAccountId || !/^\d+$/.test(trimmedAccountId) || Number(trimmedAccountId) <= 0) {
    inputError.value =
      "Enter the broker's numeric API account ID (a positive whole number, e.g. 28592949) -- not the " +
      'alphanumeric TopstepX display ID (e.g. "PRAC-V2-...") and not the EdgeLog broker-registry ID.'
    return null
  }

  if (!date.value) {
    inputError.value = 'Pick a date for this preview.'
    return null
  }

  const { executions, error } = parseExecutionsInput(executionsText.value)
  if (error) {
    inputError.value = error
    return null
  }

  return { account_id: Number(trimmedAccountId), date: date.value, executions }
}

// A safe, numeric-account-ID fixture for DEV acceptance -- mirrors the
// backend's own canonical test fixture (_execution() in
// backend/app/tests/test_reconciliation_preview.py) exactly, so this is
// known to pass the API's validation and account-scope check, not a
// guess at a shape that might work.
const SAFE_FIXTURE_ACCOUNT_ID = '28592949'
const SAFE_FIXTURE_DATE = '2026-10-16'
const SAFE_FIXTURE_EXECUTIONS = [
  {
    id: 1001,
    accountId: 28592949,
    contractId: 'CON.F.US.MNQ.Z25',
    creationTimestamp: '2026-10-16T14:30:00Z',
    price: '21000',
    size: 2,
    side: 0,
    orderId: 500,
    fees: '2.50',
    commissions: '0.62',
    voided: false
  }
]

function loadSafeFixture() {
  accountId.value = SAFE_FIXTURE_ACCOUNT_ID
  date.value = SAFE_FIXTURE_DATE
  executionsText.value = JSON.stringify(SAFE_FIXTURE_EXECUTIONS, null, 2)
  inputError.value = null
}

// Every new preview attempt -- whether it fails validation before a
// request is ever sent, fails at the API, or succeeds -- must not leave
// a PRIOR attempt's result on screen looking like it belongs to this
// one. Clearing first, before validation even runs, means a result is
// visible only when it actually reflects the most recent request.
function invalidatePriorResult() {
  requestState.value = 'idle'
  requestError.value = null
  reconciliationStore.clearPreview()
}

async function sendPayload(payload) {
  requestState.value = 'loading'
  requestError.value = null
  try {
    await reconciliationStore.previewReconciliation(payload)
    requestState.value = 'success'
  } catch (error) {
    requestError.value = formatPreviewRequestError(error)
    requestState.value = 'error'
  }
}

async function runPreview() {
  invalidatePriorResult()
  const payload = buildPayload()
  if (!payload) return
  lastPayload.value = payload
  await sendPayload(payload)
}

async function retry() {
  if (!lastPayload.value) return
  invalidatePriorResult()
  await sendPayload(lastPayload.value)
}

function resetAll() {
  accountId.value = ''
  date.value = todayDateKey()
  executionsText.value = ''
  inputError.value = null
  requestState.value = 'idle'
  requestError.value = null
  lastPayload.value = null
  reconciliationStore.clearPreview()
}

function groupingBasisLabel(basis) {
  return (
    {
      shared_order_id: 'Shared order ID',
      inferred_open_close_pair: 'Inferred open/close pair',
      ungrouped_single: 'Single execution',
      ambiguous: 'Ambiguous grouping'
    }[basis] ?? basis
  )
}

function groupingStatusLabel(status) {
  return status === 'confident' ? 'Confident' : 'Needs confirmation'
}

function groupingStatusBadgeClass(status) {
  return status === 'confident' ? 'el-badge--accent' : 'el-badge--warning'
}

function matchStatusLabel(status) {
  return (
    {
      candidate_match: 'Candidate match',
      ambiguous_candidate_match: 'Ambiguous candidate match',
      unplanned: 'No journal match',
      already_imported: 'Already imported'
    }[status] ?? status
  )
}

function matchStatusBadgeClass(status) {
  if (status === 'candidate_match') return 'el-badge--accent'
  if (status === 'ambiguous_candidate_match') return 'el-badge--warning'
  return 'el-badge--neutral'
}

function formatTimestamp(value) {
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString()
}

function formatDecimal(value) {
  return value === null || value === undefined ? '--' : formatSignedDollars(value)
}
</script>

<template>
  <div class="reconciliation-page el-page">
    <WorkspaceHeader
      title="Reconciliation Preview"
      eyebrow="Broker execution review"
      description="Paste or upload a batch of broker executions to see broker-reported facts, proposed fill groupings, and candidate journal matches. Nothing here is imported, written, or sent to a broker -- this is read-only, every time."
    />

    <form class="el-workstation input-panel" @submit.prevent="runPreview">
      <div class="el-workstation-header"><span class="el-workstation-title">Preview input</span></div>

      <div class="input-grid">
        <BaseInput
          v-model="accountId"
          type="number"
          min="1"
          label="Account ID (broker numeric API ID)"
          placeholder="e.g. 28592949"
          autocomplete="off"
        />
        <BaseInput v-model="date" type="date" label="Trading date" />
      </div>
      <p class="field-caption">
        This is the broker's own <strong>numeric API account ID</strong> (e.g. <code>28592949</code>) -- it is
        <em>not</em> the alphanumeric TopstepX display ID shown in the account selector (e.g.
        <code>PRAC-V2-...</code>), and <em>not</em> the EdgeLog broker-registry ID from Settings (see issue #95).
        The reconciliation API requires this same numeric ID for both <code>account_id</code> and every
        execution's <code>accountId</code>; it is client-supplied here and not verified against broker identity.
      </p>

      <label class="base-input-label executions-label" for="executions-input">Execution JSON</label>
      <textarea
        id="executions-input"
        v-model="executionsText"
        class="executions-textarea"
        rows="10"
        spellcheck="false"
        placeholder='Paste a JSON array of executions, e.g. [{"id": 1, "accountId": 123, "contractId": "CON.F.US.MNQ.Z25", "creationTimestamp": "2026-02-04T14:31:00Z", "orderId": 55, "price": 21050.25, "size": 1, "side": 0}]'
      ></textarea>
      <div class="executions-toolbar">
        <input ref="fileInput" type="file" accept="application/json,.json" class="file-input" @change="onFilePicked" />
        <BaseButton type="button" variant="ghost" @click="fileInput.click()">Upload JSON file</BaseButton>
        <BaseButton type="button" variant="ghost" @click="loadSafeFixture">Load safe numeric fixture</BaseButton>
      </div>
      <p class="field-caption">
        "Load safe numeric fixture" fills in a known-safe, all-numeric example (account ID
        <code>{{ SAFE_FIXTURE_ACCOUNT_ID }}</code>) for DEV acceptance testing -- the same shape the backend's own
        test suite uses, not a guess at what the API will accept.
      </p>

      <p v-if="inputError" class="el-error-state input-error" role="alert">{{ inputError }}</p>

      <div class="form-actions">
        <BaseButton type="submit" :disabled="requestState === 'loading'">
          {{ requestState === 'loading' ? 'Running preview…' : 'Preview' }}
        </BaseButton>
        <BaseButton type="button" variant="secondary" @click="resetAll">Clear</BaseButton>
      </div>
    </form>

    <div v-if="requestState === 'error'" class="el-error-state result-error">
      <p>{{ requestError }}</p>
      <BaseButton type="button" variant="secondary" @click="retry">Retry</BaseButton>
    </div>

    <div v-else-if="requestState === 'idle' && !preview" class="el-empty-state">
      Paste or upload execution JSON above and click Preview to see broker execution facts, grouping proposals, and
      candidate journal matches.
    </div>

    <div v-else-if="requestState === 'loading'" class="el-empty-state">Running preview…</div>

    <template v-else-if="preview">
      <div class="summary-row">
        <span class="el-badge el-badge--neutral">{{ preview.summary.total_executions }} executions</span>
        <span class="el-badge el-badge--neutral">{{ preview.summary.voided_count }} voided</span>
        <span class="el-badge el-badge--neutral">{{ preview.summary.already_imported_count }} already imported</span>
        <span class="el-badge el-badge--accent">{{ preview.summary.confident_groups }} confident groups</span>
        <span class="el-badge el-badge--warning">{{ preview.summary.needs_confirmation_groups }} need confirmation</span>
        <span class="el-badge el-badge--accent">{{ preview.summary.candidate_plan_matches }} candidate matches</span>
        <span class="el-badge el-badge--warning">{{ preview.summary.ambiguous_plan_matches }} ambiguous matches</span>
        <span class="el-badge el-badge--neutral">{{ preview.summary.unplanned_groups }} unplanned</span>
        <span class="el-badge el-badge--neutral">{{ preview.summary.groups_with_candidate_pnl }} with candidate P&amp;L</span>
      </div>

      <h2 class="section-title">A. Broker execution facts</h2>
      <p class="section-caption">Confirmed, unmodified broker-reported data. Nothing here is inferred.</p>
      <div class="table-scroll">
        <table class="el-focus-surface data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Order ID</th>
              <th>Contract</th>
              <th>Time</th>
              <th title="Reported by the broker; Buy/Sell mapping is not confirmed, so this is shown as-reported.">
                Side (raw)
              </th>
              <th>Size</th>
              <th>Price</th>
              <th>Fees</th>
              <th>Commissions</th>
              <th title="The broker's own reported P&amp;L for this fill -- not a reconciled journal result.">
                Broker P&amp;L (reported)
              </th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="execution in preview.executions" :key="execution.id">
              <td>{{ execution.id }}</td>
              <td>{{ execution.order_id ?? '--' }}</td>
              <td>{{ execution.contract_id }}</td>
              <td>{{ formatTimestamp(execution.creation_timestamp) }}</td>
              <td>{{ execution.side }}</td>
              <td>{{ execution.size }}</td>
              <td>{{ execution.price }}</td>
              <td>{{ execution.fees ?? '--' }}</td>
              <td>{{ execution.commissions ?? '--' }}</td>
              <td>{{ execution.broker_profit_and_loss ?? '--' }}</td>
              <td>
                <span v-if="execution.voided" class="el-badge el-badge--warning">Voided</span>
                <span v-if="execution.already_imported" class="el-badge el-badge--neutral">
                  Already imported{{ execution.already_imported_trade_id ? ` (Trade #${execution.already_imported_trade_id})` : '' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 class="section-title">B. Grouping proposals</h2>
      <p class="section-caption">
        Proposed, not confirmed. Only a shared broker order ID is treated as confident; every other pairing needs
        your confirmation.
      </p>
      <div v-if="preview.fill_groups.length === 0" class="el-empty-state">
        No groups to propose -- every execution was voided or already imported.
      </div>
      <div v-else class="table-scroll">
        <table class="el-focus-surface data-table">
          <thead>
            <tr>
              <th>Execution IDs</th>
              <th>Basis</th>
              <th>Status</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(group, index) in preview.fill_groups" :key="`grouping-${index}`">
              <td>{{ group.execution_ids.join(', ') }}</td>
              <td>{{ groupingBasisLabel(group.grouping_basis) }}</td>
              <td><span class="el-badge" :class="groupingStatusBadgeClass(group.grouping_status)">{{ groupingStatusLabel(group.grouping_status) }}</span></td>
              <td>{{ group.grouping_note }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 class="section-title">C. Journal trade candidates</h2>
      <p class="section-caption">
        A proposal for your review, never a certified match -- even when exactly one candidate is found.
      </p>
      <div v-if="preview.fill_groups.length === 0" class="el-empty-state">
        No groups to match against your journal -- every execution was voided or already imported.
      </div>
      <div v-else class="table-scroll">
        <table class="el-focus-surface data-table">
          <thead>
            <tr>
              <th>Execution IDs</th>
              <th>Match</th>
              <th>Candidate trade IDs</th>
              <th>Note</th>
              <th>P&amp;L</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(group, index) in preview.fill_groups" :key="`match-${index}`">
              <td>{{ group.execution_ids.join(', ') }}</td>
              <td><span class="el-badge" :class="matchStatusBadgeClass(group.plan_match_status)">{{ matchStatusLabel(group.plan_match_status) }}</span></td>
              <td>{{ group.candidate_trade_ids.length ? group.candidate_trade_ids.join(', ') : '--' }}</td>
              <td>{{ group.plan_match_note }}</td>
              <td>
                <span v-if="group.pnl_status === 'candidate'" :class="resultClass(group.candidate_gross_pnl)">
                  {{ formatDecimal(group.candidate_gross_pnl) }} (candidate gross)
                </span>
                <span v-else class="pnl-unresolved">Unresolved -- {{ group.pnl_unresolved_reason }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.input-panel {
  display: flex;
  flex-direction: column;
  gap: var(--el-space-4);
}

.input-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(160px, 1fr));
  gap: var(--el-space-4);
}

.field-caption {
  margin-top: calc(-1 * var(--el-space-2));
  color: var(--el-text-subtle);
  font-size: var(--el-text-xs);
}

.executions-label {
  margin-bottom: calc(-1 * var(--el-space-2));
}

.executions-textarea {
  width: 100%;
  padding: var(--el-space-3) var(--el-space-4);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-md);
  color: var(--el-text);
  font-family: var(--el-font-mono);
  font-size: var(--el-text-sm);
  resize: vertical;
}

.executions-textarea:focus {
  border-color: var(--el-copper);
  outline: none;
}

.executions-toolbar {
  display: flex;
  align-items: center;
}

.file-input {
  display: none;
}

.form-actions {
  display: flex;
  gap: var(--el-space-3);
}

.result-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--el-space-4);
  margin-top: var(--el-space-5);
}

.summary-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--el-space-2);
  margin: var(--el-space-6) 0;
}

.section-title {
  margin-top: var(--el-space-8);
  margin-bottom: var(--el-space-2);
  font-size: var(--el-text-lg);
}

.section-caption {
  margin-bottom: var(--el-space-3);
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
}

.table-scroll {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--el-text-sm);
}

.data-table th,
.data-table td {
  padding: var(--el-space-2) var(--el-space-3);
  border-bottom: 1px solid var(--el-border);
  text-align: left;
  white-space: nowrap;
}

.data-table th {
  color: var(--el-text-subtle);
  font-size: var(--el-text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.pnl-unresolved {
  color: var(--el-text-subtle);
  font-style: italic;
}

.result-positive {
  color: var(--el-positive);
}

.result-negative {
  color: var(--el-negative);
}

@media (max-width: 640px) {
  .input-grid {
    grid-template-columns: 1fr;
  }
}
</style>
