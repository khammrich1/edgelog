<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useTradePlansStore } from '@/stores/tradePlans'
import { useTradesStore } from '@/stores/trades'
import { useInstrumentsStore } from '@/stores/instruments'
import { useBrokerAccountsStore } from '@/stores/brokerAccounts'
import { formatPrice, formatSignedDollars, resultClass, SYMBOL_PRESETS } from '@/utils/trades'
import { computeRiskReward } from '@/utils/tradeMath'

const plansStore = useTradePlansStore()
const tradesStore = useTradesStore()
const instrumentsStore = useInstrumentsStore()
const brokerAccountsStore = useBrokerAccountsStore()

const plans = computed(() => plansStore.plans)
const expandedPlanId = ref(null)
const submitError = ref(null)
const symbolEntryMode = ref('preset')
const setupEntryMode = ref('custom')

function defaultExpiry(hoursFromNow = 8) {
  const d = new Date(Date.now() + hoursFromNow * 60 * 60 * 1000)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function emptyPlanForm() {
  return {
    broker_account_id: '',
    symbol: '',
    direction: 'long',
    entry_price: '',
    stop_price: '',
    target_price: '',
    quantity: '',
    max_risk_dollars: '',
    setup: '',
    invalidation_condition: '',
    rationale: '',
    expires_at: defaultExpiry()
  }
}

const planForm = reactive(emptyPlanForm())

const showRegisterAccount = ref(false)
const newAccountForm = reactive({ provider: '', account_id: '', label: '' })
const registerAccountError = ref(null)

async function registerAccount() {
  registerAccountError.value = null
  try {
    const account = await brokerAccountsStore.createAccount({
      provider: newAccountForm.provider.trim(),
      account_id: newAccountForm.account_id.trim(),
      label: newAccountForm.label || null
    })
    planForm.broker_account_id = account.id
    newAccountForm.provider = ''
    newAccountForm.account_id = ''
    newAccountForm.label = ''
    showRegisterAccount.value = false
  } catch (error) {
    registerAccountError.value = error.response?.data?.detail || 'Could not register that account.'
  }
}

function handleSymbolPresetChange(value) {
  if (value === '__custom__') {
    symbolEntryMode.value = 'custom'
    planForm.symbol = ''
  } else {
    planForm.symbol = value
  }
}

function switchToPresetList() {
  symbolEntryMode.value = 'preset'
  planForm.symbol = ''
}

function handleSetupPresetChange(value) {
  if (value === '__custom__') {
    setupEntryMode.value = 'custom'
    planForm.setup = ''
  } else {
    planForm.setup = value
  }
}

function switchToSetupPresetList() {
  setupEntryMode.value = 'preset'
  planForm.setup = ''
}

function resetSetupEntryMode() {
  setupEntryMode.value = tradesStore.setups.length > 0 ? 'preset' : 'custom'
}

const riskRewardPreview = computed(() =>
  computeRiskReward({
    quantity: planForm.quantity,
    entryPrice: planForm.entry_price,
    stopPrice: planForm.stop_price,
    targetPrice: planForm.target_price,
    direction: planForm.direction,
    multiplier: instrumentsStore.getMultiplier(planForm.symbol)
  })
)

function planPayload(form) {
  return {
    broker_account_id: form.broker_account_id ? Number(form.broker_account_id) : null,
    symbol: form.symbol.trim(),
    direction: form.direction,
    entry_price: form.entry_price,
    stop_price: form.stop_price,
    target_price: form.target_price || null,
    quantity: Number(form.quantity),
    max_risk_dollars: form.max_risk_dollars || null,
    setup: form.setup || null,
    invalidation_condition: form.invalidation_condition || null,
    rationale: form.rationale || null,
    expires_at: new Date(form.expires_at).toISOString()
  }
}

async function submitNewPlan() {
  submitError.value = null
  try {
    await plansStore.createPlan(planPayload(planForm))
    Object.assign(planForm, emptyPlanForm())
    symbolEntryMode.value = 'preset'
    resetSetupEntryMode()
  } catch (error) {
    submitError.value = error.response?.data?.detail || 'Could not save that plan.'
  }
}

function toggleExpand(planId) {
  expandedPlanId.value = expandedPlanId.value === planId ? null : planId
}

const decisionNotes = reactive({}) // planId -> decision note draft

async function approve(plan) {
  try {
    await plansStore.approvePlan(plan.id, decisionNotes[plan.id])
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Could not approve that plan.')
  }
}

async function reject(plan) {
  try {
    await plansStore.rejectPlan(plan.id, decisionNotes[plan.id])
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Could not reject that plan.')
  }
}

async function invalidate(plan) {
  try {
    await plansStore.invalidatePlan(plan.id, decisionNotes[plan.id])
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Could not invalidate that plan.')
  }
}

async function cancel(plan) {
  if (!window.confirm('Cancel this plan? It stays in your history but can no longer be approved.')) return
  try {
    await plansStore.cancelPlan(plan.id, decisionNotes[plan.id])
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Could not cancel that plan.')
  }
}

const reviseFormOpenId = ref(null)
const reviseForms = reactive({}) // planId -> form

function startRevise(plan) {
  reviseForms[plan.id] = {
    broker_account_id: plan.broker_account_id || '',
    symbol: plan.symbol,
    direction: plan.direction,
    entry_price: Number(plan.entry_price),
    stop_price: Number(plan.stop_price),
    target_price: plan.target_price !== null ? Number(plan.target_price) : '',
    quantity: plan.quantity,
    max_risk_dollars: plan.max_risk_dollars !== null ? Number(plan.max_risk_dollars) : '',
    setup: plan.setup || '',
    invalidation_condition: plan.invalidation_condition || '',
    rationale: plan.rationale || '',
    expires_at: defaultExpiry()
  }
  reviseFormOpenId.value = plan.id
}

function cancelRevise() {
  reviseFormOpenId.value = null
}

async function submitRevise(plan) {
  try {
    await plansStore.revisePlan(plan.id, planPayload(reviseForms[plan.id]))
    reviseFormOpenId.value = null
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Could not save that revision.')
  }
}

const STATUS_LABEL = {
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
  expired: 'Expired',
  invalidated: 'Invalidated',
  canceled: 'Canceled'
}

onMounted(async () => {
  plansStore.fetchPlans().catch(() => {})
  instrumentsStore.fetchMultipliers()
  brokerAccountsStore.fetchAccounts().catch(() => {})
  await tradesStore.fetchSetups()
  resetSetupEntryMode()
})
</script>

<template>
  <section class="plans-section">
    <form class="plan-form el-workstation" @submit.prevent="submitNewPlan">
      <div class="el-workstation-header">
        <span class="el-workstation-title">New Pre-Trade Plan</span>
      </div>
      <p class="plan-form-hint">
        A plan is a recorded intent to review, not an order. Approving it never submits anything to a broker.
      </p>

      <div class="ticket-grid">
        <div class="el-field">
          <label class="el-field-label">Account</label>
          <select v-model="planForm.broker_account_id">
            <option value="">No account selected</option>
            <option v-for="account in brokerAccountsStore.accounts" :key="account.id" :value="account.id">
              {{ account.provider }} {{ account.account_id }}<template v-if="account.label"> ({{ account.label }})</template>
            </option>
          </select>
          <button type="button" class="toggle-more-button" @click="showRegisterAccount = !showRegisterAccount">
            {{ showRegisterAccount ? 'Cancel' : '+ Register an account' }}
          </button>
          <div v-if="showRegisterAccount" class="register-account-form">
            <input v-model="newAccountForm.provider" type="text" placeholder="Provider (e.g. topstepx)" maxlength="50" />
            <input v-model="newAccountForm.account_id" type="text" placeholder="Account ID" maxlength="100" />
            <input v-model="newAccountForm.label" type="text" placeholder="Label (optional)" maxlength="200" />
            <button type="button" class="btn-chip btn-chip--ghost" @click="registerAccount">Save account</button>
            <p v-if="registerAccountError" class="submit-error">{{ registerAccountError }}</p>
          </div>
        </div>

        <div class="el-field">
          <label class="el-field-label">Symbol</label>
          <select v-if="symbolEntryMode === 'preset'" :value="planForm.symbol" required @change="handleSymbolPresetChange($event.target.value)">
            <option value="" disabled>Symbol</option>
            <option v-for="symbol in SYMBOL_PRESETS" :key="symbol" :value="symbol">{{ symbol }}</option>
            <option value="__custom__">Other…</option>
          </select>
          <span v-else class="custom-symbol">
            <input v-model="planForm.symbol" type="text" placeholder="Symbol" maxlength="20" required />
            <button type="button" class="toggle-more-button" @click="switchToPresetList">Use list</button>
          </span>
        </div>

        <div class="el-field">
          <label class="el-field-label">Direction</label>
          <div class="direction-toggle" role="group" aria-label="Direction">
            <button type="button" class="direction-toggle-btn direction-toggle-btn--long" :class="{ 'direction-toggle-btn--active': planForm.direction === 'long' }" @click="planForm.direction = 'long'">LONG</button>
            <button type="button" class="direction-toggle-btn direction-toggle-btn--short" :class="{ 'direction-toggle-btn--active': planForm.direction === 'short' }" @click="planForm.direction = 'short'">SHORT</button>
          </div>
        </div>

        <div class="el-field">
          <label class="el-field-label">Qty</label>
          <input v-model="planForm.quantity" type="number" min="1" placeholder="Qty" required />
        </div>

        <div class="el-field">
          <label class="el-field-label">Limit entry</label>
          <input v-model="planForm.entry_price" type="number" step="any" placeholder="Entry" required />
        </div>

        <div class="el-field">
          <label class="el-field-label">Stop</label>
          <input v-model="planForm.stop_price" type="number" step="any" placeholder="Stop" required />
        </div>

        <div class="el-field">
          <label class="el-field-label">Target</label>
          <input v-model="planForm.target_price" type="number" step="any" placeholder="Target (optional)" />
        </div>

        <div class="el-field">
          <label class="el-field-label">Max risk $</label>
          <input v-model="planForm.max_risk_dollars" type="number" step="any" min="0" placeholder="Optional ceiling" />
        </div>

        <div class="el-field">
          <label class="el-field-label">Setup</label>
          <select v-if="setupEntryMode === 'preset'" :value="planForm.setup" @change="handleSetupPresetChange($event.target.value)">
            <option value="">No setup selected</option>
            <option v-for="setup in tradesStore.setups" :key="setup.id" :value="setup.name">{{ setup.name }}</option>
            <option value="__custom__">Other…</option>
          </select>
          <span v-else class="custom-symbol">
            <input v-model="planForm.setup" type="text" placeholder="Setup" maxlength="200" />
            <button v-if="tradesStore.setups.length > 0" type="button" class="toggle-more-button" @click="switchToSetupPresetList">Use list</button>
          </span>
        </div>

        <div class="el-field">
          <label class="el-field-label">Expires</label>
          <input v-model="planForm.expires_at" type="datetime-local" required />
        </div>

        <div class="el-field ticket-field--notes">
          <label class="el-field-label">Invalidation condition</label>
          <textarea v-model="planForm.invalidation_condition" rows="1" placeholder="What would make this setup no longer valid"></textarea>
        </div>

        <div class="el-field ticket-field--notes">
          <label class="el-field-label">Rationale / confluences</label>
          <textarea v-model="planForm.rationale" rows="2" placeholder="Why this setup qualifies"></textarea>
        </div>
      </div>

      <div class="el-ticket-footer">
        <p v-if="riskRewardPreview" class="rr-preview">
          {{ riskRewardPreview.quantity }} {{ planForm.symbol || 'contracts' }}
          <template v-if="riskRewardPreview.riskPoints !== null">
            | Risk: {{ riskRewardPreview.riskPoints }} pts<template v-if="riskRewardPreview.riskDollars !== null"> / ${{ formatPrice(riskRewardPreview.riskDollars) }}</template>
          </template>
          <template v-if="riskRewardPreview.rewardPoints !== null">
            | Reward: {{ riskRewardPreview.rewardPoints }} pts<template v-if="riskRewardPreview.rewardDollars !== null"> / ${{ formatPrice(riskRewardPreview.rewardDollars) }}</template>
          </template>
          <template v-if="riskRewardPreview.rrRatio !== null"> | R:R {{ riskRewardPreview.rrRatio.toFixed(1) }}</template>
        </p>
        <div class="el-ticket-footer-actions">
          <button type="submit" class="el-btn-primary">Save Plan</button>
        </div>
      </div>
      <p v-if="submitError" class="submit-error">{{ submitError }}</p>
    </form>

    <h2 v-if="plans.length" class="plans-list-title">Pre-Trade Plans</h2>
    <ul class="plan-list">
      <li v-for="plan in plans" :key="plan.id" class="plan-card" :class="`plan-card--${plan.status}`">
        <div class="plan-card__header" @click="toggleExpand(plan.id)">
          <div class="plan-card__title">
            <span class="plan-card__symbol">{{ plan.symbol }}</span>
            <span class="trade-direction" :class="`trade-direction--${plan.direction}`">{{ plan.direction === 'long' ? 'LONG' : 'SHORT' }}</span>
            <span class="plan-status" :class="`plan-status--${plan.status}`">{{ STATUS_LABEL[plan.status] }}</span>
            <span v-if="plan.revision_number > 1" class="el-badge">rev {{ plan.revision_number }}</span>
          </div>
          <div class="plan-card__summary-right">
            <span v-if="plan.multiplier_known" class="info-value">${{ formatPrice(plan.risk_dollars) }} risk</span>
            <span v-else class="info-value">{{ plan.risk_points }} pts risk</span>
          </div>
        </div>

        <div v-if="expandedPlanId === plan.id" class="plan-card__body">
          <div class="plan-card__info">
            <div class="info-item"><span class="info-label">Entry</span><span class="info-value">{{ formatPrice(plan.entry_price) }}</span></div>
            <div class="info-item"><span class="info-label">Stop</span><span class="info-value info-value--negative">{{ formatPrice(plan.stop_price) }}</span></div>
            <div v-if="plan.target_price" class="info-item"><span class="info-label">Target</span><span class="info-value info-value--positive">{{ formatPrice(plan.target_price) }}</span></div>
            <div class="info-item"><span class="info-label">Qty</span><span class="info-value">{{ plan.quantity }}</span></div>
            <div v-if="plan.broker_account_id" class="info-item">
              <span class="info-label">Account</span>
              <span class="info-value">{{ plan.broker_account_provider }} {{ plan.broker_account_account_id }}<template v-if="plan.broker_account_label"> ({{ plan.broker_account_label }})</template></span>
            </div>
            <div v-if="plan.setup" class="info-item"><span class="info-label">Setup</span><span class="info-value">{{ plan.setup }}</span></div>
            <div class="info-item"><span class="info-label">Expires</span><span class="info-value">{{ new Date(plan.expires_at).toLocaleString() }}</span></div>
            <div v-if="plan.reward_risk_ratio !== null" class="info-item"><span class="info-label">R:R</span><span class="info-value">{{ Number(plan.reward_risk_ratio).toFixed(2) }}</span></div>
          </div>

          <p v-if="!plan.multiplier_known" class="el-badge el-badge--warning">
            No verified dollar multiplier for {{ plan.symbol }} -- risk shown in points only, and approval is blocked until one exists.
          </p>
          <p v-if="plan.exceeds_max_risk" class="el-badge el-badge--warning">
            Risk (${{ formatPrice(plan.risk_dollars) }}) exceeds your declared max risk (${{ formatPrice(plan.max_risk_dollars) }}).
          </p>

          <div v-if="plan.invalidation_condition" class="plan-card__section">
            <div class="plan-card__section-label">Invalidation condition</div>
            <p class="trade-notes">{{ plan.invalidation_condition }}</p>
          </div>
          <div v-if="plan.rationale" class="plan-card__section">
            <div class="plan-card__section-label">Rationale / confluences</div>
            <p class="trade-notes">{{ plan.rationale }}</p>
          </div>

          <div v-if="plan.decided_at" class="plan-card__section">
            <div class="plan-card__section-label">Decision</div>
            <p class="trade-notes">
              {{ STATUS_LABEL[plan.status] }} at {{ new Date(plan.decided_at).toLocaleString() }}
              <template v-if="plan.decision_note">&mdash; {{ plan.decision_note }}</template>
            </p>
          </div>

          <template v-if="plan.status === 'pending'">
            <textarea v-model="decisionNotes[plan.id]" rows="1" class="decision-note-input" placeholder="Decision note (optional)"></textarea>
            <div class="plan-card__actions">
              <button class="btn-chip btn-chip--primary" @click="approve(plan)">Approve</button>
              <button class="btn-chip btn-chip--warning" @click="reject(plan)">Reject</button>
              <button class="btn-chip btn-chip--ghost" @click="invalidate(plan)">Invalidate</button>
              <button class="btn-chip btn-chip--danger" @click="cancel(plan)">Cancel</button>
            </div>
          </template>
          <template v-else-if="plan.status === 'approved'">
            <p class="approved-hint">Approved -- recorded intent only. No order has been placed; local Practice execution is a separate, not-yet-built step.</p>
            <div class="plan-card__actions">
              <button class="btn-chip btn-chip--danger" @click="cancel(plan)">Cancel</button>
            </div>
          </template>

          <div v-if="plan.is_latest_revision && plan.status !== 'pending'" class="plan-card__actions">
            <button v-if="reviseFormOpenId !== plan.id" class="btn-chip btn-chip--ghost" @click="startRevise(plan)">Revise &amp; resubmit</button>
          </div>

          <form v-if="reviseFormOpenId === plan.id" class="revise-form" @submit.prevent="submitRevise(plan)">
            <div class="plan-card__section-label">New revision (requires fresh approval)</div>
            <div class="revise-grid">
              <input v-model="reviseForms[plan.id].entry_price" type="number" step="any" placeholder="Entry" required />
              <input v-model="reviseForms[plan.id].stop_price" type="number" step="any" placeholder="Stop" required />
              <input v-model="reviseForms[plan.id].target_price" type="number" step="any" placeholder="Target" />
              <input v-model="reviseForms[plan.id].quantity" type="number" min="1" placeholder="Qty" required />
              <input v-model="reviseForms[plan.id].expires_at" type="datetime-local" required />
            </div>
            <div class="plan-card__actions">
              <button type="submit" class="btn-chip btn-chip--primary">Save revision</button>
              <button type="button" class="btn-chip btn-chip--ghost" @click="cancelRevise">Cancel</button>
            </div>
          </form>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.plans-section { margin-bottom: var(--el-space-8); }
.plan-form-hint { color: var(--el-text-muted); font-size: var(--el-text-sm); margin: 0 0 var(--el-space-4); }
.ticket-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--el-space-3); margin-bottom: var(--el-space-4); }
.ticket-field--notes { grid-column: 1 / -1; }
.ticket-field--notes textarea { width: 100%; resize: vertical; }
.custom-symbol { display: flex; align-items: center; gap: var(--el-space-2); }
.custom-symbol input { flex: 1; min-width: 0; }
.direction-toggle { display: flex; height: 38px; border: 1px solid var(--el-border); border-radius: var(--el-radius-sm); overflow: hidden; }
.direction-toggle-btn { flex: 1; padding: 0 var(--el-space-2); background-color: var(--el-surface); color: var(--el-text-muted); border: none; font-weight: 600; font-size: var(--el-text-xs); letter-spacing: 0.05em; cursor: pointer; }
.direction-toggle-btn + .direction-toggle-btn { border-left: 1px solid var(--el-border); }
.direction-toggle-btn--long.direction-toggle-btn--active { background-color: var(--el-positive); color: var(--el-bg); }
.direction-toggle-btn--short.direction-toggle-btn--active { background-color: var(--el-negative); color: var(--el-bg); }
.toggle-more-button { background: none; border: none; color: var(--el-text-muted); font-size: var(--el-text-xs); cursor: pointer; margin-top: var(--el-space-2); padding: 0; }
.toggle-more-button:hover { color: var(--el-copper); }
.register-account-form { display: flex; flex-wrap: wrap; gap: var(--el-space-2); margin-top: var(--el-space-2); }
.register-account-form input { flex: 1 1 110px; padding: var(--el-space-2); background-color: var(--el-surface); border: 1px solid var(--el-border); border-radius: var(--el-radius-sm); color: var(--el-text); font-size: var(--el-text-sm); }
.rr-preview { color: var(--el-text-muted); font-size: var(--el-text-sm); margin: 0; }
.submit-error { color: var(--el-negative); font-size: var(--el-text-sm); margin: var(--el-space-2) 0 0; }
.plans-list-title { margin-top: 0; font-size: var(--el-text-sm); text-transform: uppercase; letter-spacing: 0.05em; color: var(--el-text-muted); }

.plan-list { list-style: none; margin: 0 0 var(--el-space-4); padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); align-items: start; gap: var(--el-space-3); }
@media (max-width: 820px) { .plan-list { grid-template-columns: 1fr; } }

.plan-card { background-color: var(--el-surface); border: 1px solid var(--el-border); border-left: 3px solid var(--el-border); border-radius: var(--el-radius-md); overflow: hidden; }
.plan-card--pending { border-left-color: var(--el-copper); }
.plan-card--approved { border-left-color: var(--el-positive); }
.plan-card--rejected, .plan-card--invalidated, .plan-card--canceled { border-left-color: var(--el-steel); opacity: 0.85; }
.plan-card--expired { border-left-color: var(--el-negative); opacity: 0.85; }

.plan-card__header { display: flex; align-items: center; justify-content: space-between; gap: var(--el-space-3); padding: var(--el-space-3) var(--el-space-4); cursor: pointer; font-size: var(--el-text-sm); }
.plan-card__header:hover { background-color: var(--el-surface-raised); }
.plan-card__title { display: flex; align-items: center; gap: var(--el-space-2); }
.plan-card__symbol { font-weight: 700; font-family: var(--el-font-mono); }
.plan-card__summary-right { display: flex; align-items: center; gap: var(--el-space-2); color: var(--el-text-muted); }

.trade-direction { font-size: var(--el-text-xs); font-weight: 600; letter-spacing: 0.04em; padding: 2px var(--el-space-2); border-radius: var(--el-radius-sm); }
.trade-direction--long { color: var(--el-positive); border: 1px solid var(--el-positive); }
.trade-direction--short { color: var(--el-negative); border: 1px solid var(--el-negative); }

.plan-status { font-size: var(--el-text-xs); font-weight: 600; letter-spacing: 0.05em; padding: 2px var(--el-space-2); border-radius: var(--el-radius-sm); }
.plan-status--pending { color: var(--el-copper); background-color: rgba(184, 115, 51, 0.12); }
.plan-status--approved { color: var(--el-positive); background-color: var(--el-bg); }
.plan-status--rejected, .plan-status--invalidated, .plan-status--canceled, .plan-status--expired { color: var(--el-text-subtle); background-color: var(--el-bg); }

.plan-card__body { padding: 0 var(--el-space-4) var(--el-space-4); border-top: 1px solid var(--el-border); }
.plan-card__info { display: flex; flex-wrap: wrap; gap: var(--el-space-4); padding: var(--el-space-3) var(--el-space-4); margin: var(--el-space-3) 0; background-color: var(--el-bg); border-radius: var(--el-radius-sm); }
.info-item { display: flex; flex-direction: column; gap: 2px; font-size: var(--el-text-sm); }
.info-label { font-size: var(--el-text-xs); text-transform: uppercase; letter-spacing: 0.05em; color: var(--el-text-subtle); }
.info-value { color: var(--el-text); font-variant-numeric: tabular-nums; }
.info-value--positive { color: var(--el-positive); }
.info-value--negative { color: var(--el-negative); }

.plan-card__section { margin-bottom: var(--el-space-3); }
.plan-card__section-label { font-size: var(--el-text-xs); text-transform: uppercase; letter-spacing: 0.05em; color: var(--el-text-subtle); margin-bottom: var(--el-space-1); }
.plan-card__actions { display: flex; gap: var(--el-space-2); flex-wrap: wrap; margin-top: var(--el-space-3); }
.trade-notes { color: var(--el-text); font-size: var(--el-text-sm); margin: 0; }
.approved-hint { color: var(--el-text-muted); font-size: var(--el-text-sm); margin: 0; }
.decision-note-input { width: 100%; margin-top: var(--el-space-2); padding: var(--el-space-2); background-color: var(--el-surface); border: 1px solid var(--el-border); border-radius: var(--el-radius-sm); color: var(--el-text); font-size: var(--el-text-sm); font-family: inherit; resize: vertical; }
.revise-form { margin-top: var(--el-space-3); padding-top: var(--el-space-3); border-top: 1px solid var(--el-border); }
.revise-grid { display: flex; flex-wrap: wrap; gap: var(--el-space-2); }
.revise-grid input { flex: 1 1 110px; padding: var(--el-space-2); background-color: var(--el-surface); border: 1px solid var(--el-border); border-radius: var(--el-radius-sm); color: var(--el-text); font-size: var(--el-text-sm); }
</style>
