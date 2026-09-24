import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FinancialBulkImport from './FinancialBulkImport.vue'
import { useFinancialEntriesStore } from '@/stores/financialEntries'

function mountPanel() {
  setActivePinia(createPinia())
  const store = useFinancialEntriesStore()
  store.parseFinancialScreenshotBulk = vi.fn()
  store.bulkCreateEntries = vi.fn().mockResolvedValue([])

  const wrapper = mount(FinancialBulkImport)
  return { wrapper, store }
}

// Same DOM-event-driven approach as FinancialEntryForm.spec.js's pasteImage
// helper -- <script setup> internals aren't reachable via wrapper.vm.
async function pasteImage(wrapper, file) {
  await wrapper.find('.screenshot-dropzone').trigger('paste', {
    clipboardData: { items: [{ type: 'image/png', getAsFile: () => file }] }
  })
  await flushPromises()
}

const threeRowExtraction = [
  { entry_type: 'income', category: 'payout', amount: '450.00', date: '2026-06-18', firm: null, notes: null },
  { entry_type: 'income', category: 'payout', amount: '480.00', date: '2026-06-12', firm: null, notes: null },
  {
    entry_type: 'income',
    category: 'payout',
    amount: '295.00',
    date: '2026-05-01',
    firm: null,
    notes: 'Requested amount differed from the finalized payout amount.'
  }
]

describe('FinancialBulkImport', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders one draft row per extracted entry, all included by default', async () => {
    const { wrapper, store } = mountPanel()
    store.parseFinancialScreenshotBulk.mockResolvedValue(threeRowExtraction)
    const file = new File(['x'], 'payouts.png', { type: 'image/png' })

    await pasteImage(wrapper, file)

    expect(store.parseFinancialScreenshotBulk).toHaveBeenCalledWith(file)
    const rows = wrapper.findAll('.draft-table tbody tr')
    expect(rows).toHaveLength(3)
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    expect(checkboxes.every((c) => c.element.checked)).toBe(true)
    expect(wrapper.find('.import-button').text()).toBe('Import 3 entries')
  })

  it('applies sane defaults for null fields while keeping the row editable', async () => {
    const { wrapper, store } = mountPanel()
    store.parseFinancialScreenshotBulk.mockResolvedValue([
      { entry_type: null, category: null, amount: null, date: null, firm: null, notes: null }
    ])

    await pasteImage(wrapper, new File(['x'], 'shot.png', { type: 'image/png' }))

    const categoryInput = wrapper.find('.draft-input--category')
    expect(categoryInput.element.value).toBe('')
    expect(wrapper.find('.type-toggle-btn--expense').classes()).toContain('type-toggle-btn--active')
    expect(wrapper.find('input[type="date"]').element.value).not.toBe('')
  })

  it('excludes an unchecked row from the submitted payload', async () => {
    const { wrapper, store } = mountPanel()
    store.parseFinancialScreenshotBulk.mockResolvedValue(threeRowExtraction)
    await pasteImage(wrapper, new File(['x'], 'payouts.png', { type: 'image/png' }))

    await wrapper.findAll('input[type="checkbox"]')[1].setValue(false)
    expect(wrapper.find('.import-button').text()).toBe('Import 2 entries')

    await wrapper.find('.import-button').trigger('click')
    await flushPromises()

    expect(store.bulkCreateEntries).toHaveBeenCalledWith([
      expect.objectContaining({ amount: '450.00' }),
      expect.objectContaining({ amount: '295.00' })
    ])
  })

  it('clears the draft rows and resets the dropzone after a successful import', async () => {
    const { wrapper, store } = mountPanel()
    store.parseFinancialScreenshotBulk.mockResolvedValue(threeRowExtraction)
    await pasteImage(wrapper, new File(['x'], 'payouts.png', { type: 'image/png' }))

    await wrapper.find('.import-button').trigger('click')
    await flushPromises()

    expect(wrapper.find('.draft-table').exists()).toBe(false)
  })

  it('shows a submit error and keeps the draft rows when the bulk-create call fails', async () => {
    const { wrapper, store } = mountPanel()
    store.parseFinancialScreenshotBulk.mockResolvedValue(threeRowExtraction)
    store.bulkCreateEntries.mockRejectedValue({ response: { data: { detail: 'Bad request' } } })
    await pasteImage(wrapper, new File(['x'], 'payouts.png', { type: 'image/png' }))

    await wrapper.find('.import-button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Bad request')
    expect(wrapper.find('.draft-table').exists()).toBe(true)
  })

  it('falls back gracefully when extraction fails, without crashing', async () => {
    const { wrapper, store } = mountPanel()
    store.parseFinancialScreenshotBulk.mockRejectedValue({
      response: { data: { detail: 'Screenshot capture is not configured on this server' } }
    })

    await pasteImage(wrapper, new File(['x'], 'payouts.png', { type: 'image/png' }))

    expect(wrapper.text()).toContain('not configured')
    expect(wrapper.find('.draft-table').exists()).toBe(false)
  })

  it('disables the import button when a checked row is missing a required field', async () => {
    const { wrapper, store } = mountPanel()
    store.parseFinancialScreenshotBulk.mockResolvedValue(threeRowExtraction)
    await pasteImage(wrapper, new File(['x'], 'payouts.png', { type: 'image/png' }))

    await wrapper.find('.draft-input--category').setValue('')

    expect(wrapper.find('.import-button').attributes('disabled')).toBeDefined()
  })
})
