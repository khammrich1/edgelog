import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ReconciliationPreview from './ReconciliationPreview.vue'
import { useReconciliationStore } from '@/stores/reconciliation'
import { SAMPLE_EXECUTIONS_JSON } from '@/utils/reconciliation'

const VALID_RESPONSE = {
  account_id: 28592949,
  date: '2026-10-16',
  executions: [
    {
      id: 900001,
      order_id: 500001,
      contract_id: 'CON.F.US.MNQ.Z25',
      account_id: 28592949,
      creation_timestamp: '2026-10-16T14:30:00Z',
      price: '21000.00',
      size: 2,
      side: 0,
      fees: '2.50',
      commissions: '0.62',
      broker_profit_and_loss: null,
      voided: false,
      already_imported: false,
      already_imported_trade_id: null
    },
    {
      id: 900002,
      order_id: 500001,
      contract_id: 'CON.F.US.MNQ.Z25',
      account_id: 28592949,
      creation_timestamp: '2026-10-16T14:45:00Z',
      price: '21040.00',
      size: 2,
      side: 1,
      fees: '2.50',
      commissions: '0.62',
      broker_profit_and_loss: '160.00',
      voided: false,
      already_imported: true,
      already_imported_trade_id: 42
    }
  ],
  fill_groups: [
    {
      execution_ids: [900001, 900002],
      grouping_basis: 'shared_order_id',
      grouping_status: 'confident',
      grouping_note: 'Both executions share orderId 500001.',
      plan_match_status: 'candidate_match',
      candidate_trade_ids: [77],
      plan_match_note: 'Symbol matches journal trade #77 on this date.',
      pnl_status: 'candidate',
      candidate_gross_pnl: '160.00',
      pnl_unresolved_reason: null,
      voided: false
    },
    {
      execution_ids: [900003],
      grouping_basis: 'ambiguous',
      grouping_status: 'needs_confirmation',
      grouping_note: 'Multiple open executions on this contract.',
      plan_match_status: 'unplanned',
      candidate_trade_ids: [],
      plan_match_note: 'No journaled trade matches this symbol/date.',
      pnl_status: 'unresolved',
      candidate_gross_pnl: null,
      pnl_unresolved_reason: 'No verified instrument multiplier.',
      voided: false
    }
  ],
  summary: {
    total_executions: 2,
    voided_count: 0,
    already_imported_count: 1,
    confident_groups: 1,
    needs_confirmation_groups: 1,
    candidate_plan_matches: 1,
    ambiguous_plan_matches: 0,
    unplanned_groups: 1,
    groups_with_candidate_pnl: 1
  }
}

function mountView() {
  setActivePinia(createPinia())
  const store = useReconciliationStore()
  const wrapper = mount(ReconciliationPreview)
  return { wrapper, store }
}

async function fillValidForm(wrapper, { executionsText = SAMPLE_EXECUTIONS_JSON } = {}) {
  await wrapper.find('input[type="number"]').setValue('28592949')
  await wrapper.find('input[type="date"]').setValue('2026-10-16')
  await wrapper.find('textarea').setValue(executionsText)
}

describe('ReconciliationPreview', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the input form and no results before a preview has run', () => {
    const { wrapper } = mountView()

    expect(wrapper.find('input[type="number"]').exists()).toBe(true)
    expect(wrapper.find('input[type="date"]').exists()).toBe(true)
    expect(wrapper.find('textarea').exists()).toBe(true)
    expect(wrapper.text()).toContain('No preview run yet')
    expect(wrapper.text()).toContain('Read-only preview')
  })

  it('shows validation errors and never calls the store when required fields are missing', async () => {
    const { wrapper, store } = mountView()
    store.preview = vi.fn()
    // The date field defaults to today -- clear it to exercise that
    // validation branch too, not just the account-id one.
    await wrapper.find('input[type="date"]').setValue('')

    await wrapper.find('.el-btn-primary').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Enter a positive account ID')
    expect(wrapper.text()).toContain('Pick a date')
    expect(store.preview).not.toHaveBeenCalled()
  })

  it('shows a JSON parse error and never calls the store for malformed input', async () => {
    const { wrapper, store } = mountView()
    store.preview = vi.fn()
    await wrapper.find('input[type="number"]').setValue('28592949')
    await wrapper.find('input[type="date"]').setValue('2026-10-16')
    await wrapper.find('textarea').setValue('{ not json')

    await wrapper.find('.el-btn-primary').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Not valid JSON')
    expect(store.preview).not.toHaveBeenCalled()
  })

  it('rejects an empty execution batch locally without calling the store', async () => {
    const { wrapper, store } = mountView()
    store.preview = vi.fn()
    await wrapper.find('input[type="number"]').setValue('28592949')
    await wrapper.find('input[type="date"]').setValue('2026-10-16')

    await wrapper.find('.el-btn-primary').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Paste or upload')
    expect(store.preview).not.toHaveBeenCalled()
  })

  it('"Load sample fixture" fills the textarea without sending anything', async () => {
    const { wrapper, store } = mountView()
    store.preview = vi.fn()

    const loadSampleButton = wrapper.findAll('button').find((b) => b.text() === 'Load sample fixture')
    await loadSampleButton.trigger('click')

    expect(wrapper.find('textarea').element.value).toBe(SAMPLE_EXECUTIONS_JSON)
    expect(store.preview).not.toHaveBeenCalled()
  })

  it('sends exactly the entered account/date/executions as the preview payload', async () => {
    const { wrapper, store } = mountView()
    store.preview = vi.fn().mockResolvedValue(VALID_RESPONSE)
    await fillValidForm(wrapper)

    await wrapper.find('.el-btn-primary').trigger('click')
    await flushPromises()

    expect(store.preview).toHaveBeenCalledWith({
      account_id: 28592949,
      date: '2026-10-16',
      executions: JSON.parse(SAMPLE_EXECUTIONS_JSON)
    })
  })

  it('shows a loading state while the request is in flight', async () => {
    const { wrapper, store } = mountView()
    let resolvePreview
    store.preview = vi.fn().mockReturnValue(new Promise((resolve) => { resolvePreview = resolve }))
    await fillValidForm(wrapper)

    const clickPromise = wrapper.find('.el-btn-primary').trigger('click')
    await flushPromises()

    expect(wrapper.find('.el-btn-primary').text()).toContain('Running preview')
    expect(wrapper.find('.el-btn-primary').attributes('disabled')).toBeDefined()

    resolvePreview(VALID_RESPONSE)
    await clickPromise
    await flushPromises()
    expect(wrapper.find('.el-btn-primary').text()).toBe('Run Preview')
  })

  it('renders broker execution facts (A), grouping proposals (B), and candidate matches (C) as separate sections', async () => {
    const { wrapper, store } = mountView()
    store.preview = vi.fn().mockImplementation(async (payload) => {
      store.result = VALID_RESPONSE
      return VALID_RESPONSE
    })
    await fillValidForm(wrapper)

    await wrapper.find('.el-btn-primary').trigger('click')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('A. Broker-reported execution facts')
    expect(text).toContain('B. Grouping proposals')
    expect(text).toContain('C. Candidate journal-trade association')

    // Section A: raw broker facts, including side decoding and separate fees/commissions.
    expect(text).toContain('Buy')
    expect(text).toContain('Sell')
    expect(text).toContain('Already imported')
    expect(text).toContain('trade #42')

    // Section B: grouping basis/status, distinguishing confident from needs_confirmation.
    expect(text).toContain('Shared order ID')
    expect(text).toContain('Confident')
    expect(text).toContain('Needs confirmation')

    // Section C: candidate match status is never presented as confirmed, and
    // unresolved P&L is explicit, distinct from a labeled "candidate gross" figure.
    expect(text).toContain('Candidate match')
    expect(text).toContain('Unplanned')
    expect(text).toContain('candidate gross')
    expect(text).toContain('Unresolved')
    expect(text).not.toContain('Confirmed match')

    // Never offers an actionable button to act on the preview -- the word
    // "confirm" legitimately appears in explanatory text ("never a
    // confirmed... association"), so this checks for a button, not text.
    const actionableButtons = wrapper.findAll('button').map((b) => b.text())
    expect(actionableButtons.some((label) => /confirm|import/i.test(label))).toBe(false)
  })

  it('shows a network-failure state with a working Retry action', async () => {
    const { wrapper, store } = mountView()
    store.preview = vi.fn()
      .mockRejectedValueOnce({ response: undefined })
      .mockResolvedValueOnce(VALID_RESPONSE)
    await fillValidForm(wrapper)

    await wrapper.find('.el-btn-primary').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Could not reach the server')

    const retryButton = wrapper.findAll('button').find((b) => b.text() === 'Retry')
    await retryButton.trigger('click')
    await flushPromises()

    expect(store.preview).toHaveBeenCalledTimes(2)
  })

  it('formats a 422 validation error response into readable lines', async () => {
    const { wrapper, store } = mountView()
    store.preview = vi.fn().mockRejectedValue({
      response: {
        status: 422,
        data: { detail: [{ loc: ['body', 'executions', 0, 'price'], msg: 'Input should be greater than 0' }] }
      }
    })
    await fillValidForm(wrapper)

    await wrapper.find('.el-btn-primary').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('executions.0.price: Input should be greater than 0')
  })

  it('shows an explicit auth-expired message for a 401, with no Retry button', async () => {
    const { wrapper, store } = mountView()
    store.preview = vi.fn().mockRejectedValue({ response: { status: 401, data: {} } })
    await fillValidForm(wrapper)

    await wrapper.find('.el-btn-primary').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('log in again')
    expect(wrapper.findAll('button').find((b) => b.text() === 'Retry')).toBeUndefined()
  })

  it('"Start over" clears the rendered result', async () => {
    const { wrapper, store } = mountView()
    store.preview = vi.fn().mockImplementation(async () => {
      store.result = VALID_RESPONSE
      return VALID_RESPONSE
    })
    store.clear = vi.fn(() => { store.result = null })
    await fillValidForm(wrapper)
    await wrapper.find('.el-btn-primary').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('A. Broker-reported execution facts')

    const startOverButton = wrapper.findAll('button').find((b) => b.text() === 'Start over')
    await startOverButton.trigger('click')
    await flushPromises()

    expect(store.clear).toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('A. Broker-reported execution facts')
  })
})
