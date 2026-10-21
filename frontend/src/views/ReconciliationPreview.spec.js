import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ReconciliationPreview from './ReconciliationPreview.vue'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: { post: vi.fn() }
}))

const VALID_EXECUTIONS = [
  {
    id: 1,
    accountId: 123,
    contractId: 'CON.F.US.MNQ.Z25',
    creationTimestamp: '2026-02-04T14:31:00Z',
    orderId: 55,
    price: 21050.25,
    size: 1,
    side: 0
  }
]

const FIXTURE_RESPONSE = {
  account_id: 123,
  date: '2026-02-04',
  executions: [
    {
      id: 1,
      order_id: 55,
      contract_id: 'CON.F.US.MNQ.Z25',
      account_id: 123,
      creation_timestamp: '2026-02-04T14:31:00Z',
      price: '21050.25',
      size: 1,
      side: 0,
      fees: '0.50',
      commissions: '1.24',
      broker_profit_and_loss: null,
      voided: false,
      already_imported: false,
      already_imported_trade_id: null
    },
    {
      id: 2,
      order_id: 55,
      contract_id: 'CON.F.US.MNQ.Z25',
      account_id: 123,
      creation_timestamp: '2026-02-04T14:45:00Z',
      price: '21075.00',
      size: 1,
      side: 1,
      fees: '0.50',
      commissions: '1.24',
      broker_profit_and_loss: '24.75',
      voided: false,
      already_imported: false,
      already_imported_trade_id: null
    },
    {
      id: 3,
      order_id: null,
      contract_id: 'CON.F.US.MES.Z25',
      account_id: 123,
      creation_timestamp: '2026-02-04T15:00:00Z',
      price: '5900.00',
      size: 2,
      side: 0,
      fees: null,
      commissions: null,
      broker_profit_and_loss: null,
      voided: true,
      already_imported: false,
      already_imported_trade_id: null
    },
    {
      id: 4,
      order_id: 99,
      contract_id: 'CON.F.US.MGC.Z25',
      account_id: 123,
      creation_timestamp: '2026-02-04T15:10:00Z',
      price: '2650.10',
      size: 1,
      side: 0,
      fees: '0.50',
      commissions: '1.24',
      broker_profit_and_loss: null,
      voided: false,
      already_imported: true,
      already_imported_trade_id: 42
    }
  ],
  fill_groups: [
    {
      execution_ids: [1, 2],
      grouping_basis: 'shared_order_id',
      grouping_status: 'confident',
      grouping_note: 'Shared order 55.',
      plan_match_status: 'candidate_match',
      candidate_trade_ids: [10],
      plan_match_note: 'One candidate trade matched by symbol/date.',
      pnl_status: 'candidate',
      candidate_gross_pnl: '24.75',
      pnl_unresolved_reason: null,
      voided: false
    },
    {
      execution_ids: [3],
      grouping_basis: 'ungrouped_single',
      grouping_status: 'needs_confirmation',
      grouping_note: 'Voided execution.',
      plan_match_status: 'unplanned',
      candidate_trade_ids: [],
      plan_match_note: 'No candidate trade found.',
      pnl_status: 'unresolved',
      candidate_gross_pnl: null,
      pnl_unresolved_reason: 'Execution is voided.',
      voided: true
    },
    {
      execution_ids: [4],
      grouping_basis: 'shared_order_id',
      grouping_status: 'confident',
      grouping_note: 'Already imported under Trade #42.',
      plan_match_status: 'already_imported',
      candidate_trade_ids: [42],
      plan_match_note: 'Matches an already-imported trade.',
      pnl_status: 'unresolved',
      candidate_gross_pnl: null,
      pnl_unresolved_reason: 'Already imported.',
      voided: false
    },
    {
      execution_ids: [5, 6],
      grouping_basis: 'ambiguous',
      grouping_status: 'needs_confirmation',
      grouping_note: 'Multiple possible pairings.',
      plan_match_status: 'ambiguous_candidate_match',
      candidate_trade_ids: [11, 12],
      plan_match_note: 'Multiple trades match.',
      pnl_status: 'unresolved',
      candidate_gross_pnl: null,
      pnl_unresolved_reason: 'Ambiguous grouping.',
      voided: false
    }
  ],
  summary: {
    total_executions: 4,
    voided_count: 1,
    already_imported_count: 1,
    confident_groups: 2,
    needs_confirmation_groups: 2,
    candidate_plan_matches: 1,
    ambiguous_plan_matches: 1,
    unplanned_groups: 1,
    groups_with_candidate_pnl: 1
  }
}

async function mountView() {
  setActivePinia(createPinia())
  const wrapper = mount(ReconciliationPreview)
  await flushPromises()
  return wrapper
}

async function fillValidInput(wrapper, { accountId = '123', date = '2026-02-04', executions = VALID_EXECUTIONS } = {}) {
  const inputs = wrapper.findAll('.base-input')
  await inputs[0].setValue(accountId)
  await inputs[1].setValue(date)
  await wrapper.find('#executions-input').setValue(JSON.stringify(executions))
}

async function submit(wrapper) {
  await wrapper.find('form').trigger('submit')
  await flushPromises()
}

describe('ReconciliationPreview', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows an empty-state hint before any preview has run, with no results and no write controls', async () => {
    const wrapper = await mountView()

    expect(wrapper.find('.el-empty-state').text()).toMatch(/Paste or upload execution JSON/)
    expect(wrapper.text()).not.toMatch(/Confirm/)
    expect(wrapper.text()).not.toMatch(/\bImport\b/)
    expect(api.post).not.toHaveBeenCalled()
  })

  it('rejects submission with a validation error when the account ID is missing, without calling the API', async () => {
    const wrapper = await mountView()
    await fillValidInput(wrapper, { accountId: '' })

    await submit(wrapper)

    expect(wrapper.find('.input-error').text()).toMatch(/positive whole-number account ID/)
    expect(api.post).not.toHaveBeenCalled()
  })

  it('rejects submission with a validation error for malformed execution JSON', async () => {
    const wrapper = await mountView()
    const inputs = wrapper.findAll('.base-input')
    await inputs[0].setValue('123')
    await inputs[1].setValue('2026-02-04')
    await wrapper.find('#executions-input').setValue('{not valid')

    await submit(wrapper)

    expect(wrapper.find('.input-error').text()).toMatch(/isn't valid JSON/)
    expect(api.post).not.toHaveBeenCalled()
  })

  it('rejects submission when the executions array is empty', async () => {
    const wrapper = await mountView()
    await fillValidInput(wrapper, { executions: [] })

    await submit(wrapper)

    expect(wrapper.find('.input-error').text()).toMatch(/empty/)
    expect(api.post).not.toHaveBeenCalled()
  })

  it('sends the entered account id, date, and parsed executions to the existing preview endpoint', async () => {
    api.post.mockResolvedValue({ data: FIXTURE_RESPONSE })
    const wrapper = await mountView()
    await fillValidInput(wrapper)

    await submit(wrapper)

    expect(api.post).toHaveBeenCalledWith('/journal/reconciliation/preview', {
      account_id: 123,
      date: '2026-02-04',
      executions: VALID_EXECUTIONS
    })
  })

  it('shows a loading state while the request is in flight', async () => {
    let resolveRequest
    api.post.mockReturnValue(new Promise((resolve) => { resolveRequest = resolve }))
    const wrapper = await mountView()
    await fillValidInput(wrapper)

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toMatch(/Running preview/)

    resolveRequest({ data: FIXTURE_RESPONSE })
    await flushPromises()
    expect(wrapper.text()).not.toMatch(/Running preview/)
  })

  it('renders broker facts, grouping proposals, and journal candidates as three distinct sections, never as confirmed', async () => {
    api.post.mockResolvedValue({ data: FIXTURE_RESPONSE })
    const wrapper = await mountView()
    await fillValidInput(wrapper)
    await submit(wrapper)

    const text = wrapper.text()

    // Section A: broker facts, including voided and duplicate/already-imported flags.
    expect(text).toContain('Broker execution facts')
    expect(text).toContain('Voided')
    expect(text).toContain('Already imported')
    expect(text).toContain('Trade #42')

    // Section B: grouping proposals, both confident and needs-confirmation/ambiguous.
    expect(text).toContain('Grouping proposals')
    expect(text).toContain('Shared order ID')
    expect(text).toContain('Ambiguous grouping')
    expect(text).toContain('Confident')
    expect(text).toContain('Needs confirmation')

    // Section C: journal candidates, covering candidate/ambiguous/unplanned/already-imported match states.
    expect(text).toContain('Journal trade candidates')
    expect(text).toContain('Candidate match')
    expect(text).toContain('Ambiguous candidate match')
    expect(text).toContain('No journal match')

    // P&L: candidate gross is explicitly labeled, unresolved is explicit and never a number.
    expect(text).toMatch(/\(candidate gross\)/)
    expect(text).toContain('Unresolved -- Execution is voided.')
    expect(text).toContain('Unresolved -- Ambiguous grouping.')

    // Never a confirm/import action anywhere in the rendered result --
    // "confirmed" legitimately appears as prose (section A is confirmed
    // broker fact, as opposed to B/C's inferred proposals), but no button
    // ever offers to confirm, import, or otherwise act on the preview.
    const buttonLabels = wrapper.findAll('button').map((b) => b.text())
    expect(buttonLabels.some((label) => /confirm|import/i.test(label))).toBe(false)
  })

  it('shows a readable message on request failure and lets the user retry', async () => {
    api.post.mockRejectedValueOnce({ response: { status: 400, data: { detail: 'Execution(s) [1] report a different accountId.' } } })
    const wrapper = await mountView()
    await fillValidInput(wrapper)
    await submit(wrapper)

    expect(wrapper.find('.result-error').text()).toContain('Execution(s) [1] report a different accountId.')

    api.post.mockResolvedValueOnce({ data: FIXTURE_RESPONSE })
    await wrapper.find('.result-error button').trigger('click')
    await flushPromises()

    expect(wrapper.find('.result-error').exists()).toBe(false)
    expect(wrapper.text()).toContain('Broker execution facts')
  })

  it('shows a network-error message when the request never gets a response', async () => {
    api.post.mockRejectedValueOnce(new Error('network down'))
    const wrapper = await mountView()
    await fillValidInput(wrapper)
    await submit(wrapper)

    expect(wrapper.find('.result-error').text()).toMatch(/Network error/)
  })

  it('never calls anything other than the read-only preview endpoint', async () => {
    api.post.mockResolvedValue({ data: FIXTURE_RESPONSE })
    const wrapper = await mountView()
    await fillValidInput(wrapper)
    await submit(wrapper)
    await submit(wrapper)

    for (const call of api.post.mock.calls) {
      expect(call[0]).toBe('/journal/reconciliation/preview')
    }
    expect(Object.keys(api)).not.toContain('put')
    expect(Object.keys(api)).not.toContain('delete')
  })

  it('Clear resets the input fields and the displayed result back to the empty state', async () => {
    api.post.mockResolvedValue({ data: FIXTURE_RESPONSE })
    const wrapper = await mountView()
    await fillValidInput(wrapper)
    await submit(wrapper)
    expect(wrapper.text()).toContain('Broker execution facts')

    await wrapper.find('.form-actions button[type="button"]').trigger('click')

    expect(wrapper.text()).not.toContain('Broker execution facts')
    expect(wrapper.find('.el-empty-state').text()).toMatch(/Paste or upload execution JSON/)
    expect(wrapper.find('#executions-input').element.value).toBe('')
  })
})
