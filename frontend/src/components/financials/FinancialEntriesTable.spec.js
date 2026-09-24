import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import FinancialEntriesTable from './FinancialEntriesTable.vue'
import { useFinancialEntriesStore } from '@/stores/financialEntries'

const incomeEntry = {
  id: 1,
  entry_type: 'income',
  category: 'Payout',
  amount: '500.00',
  date: '2026-02-10',
  firm: 'TopStep',
  has_screenshot: false
}

const expenseEntry = {
  id: 2,
  entry_type: 'expense',
  category: 'Evaluation fee',
  amount: '150.00',
  date: '2026-02-12',
  firm: null,
  has_screenshot: true
}

function mountTable(entries) {
  setActivePinia(createPinia())
  const store = useFinancialEntriesStore()
  store.deleteEntry = vi.fn().mockResolvedValue()
  store.deleteEntryScreenshot = vi.fn().mockResolvedValue()
  store.uploadEntryScreenshot = vi.fn().mockResolvedValue()
  store.fetchEntryScreenshotObjectUrl = vi.fn().mockResolvedValue('blob:mock-url')

  const wrapper = mount(FinancialEntriesTable, { props: { entries } })
  return { wrapper, store }
}

describe('FinancialEntriesTable', () => {
  beforeEach(() => {
    global.URL.revokeObjectURL = vi.fn()
    global.window.open = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('signs and colors amounts by entry type: income positive, expense negative', () => {
    const { wrapper } = mountTable([incomeEntry, expenseEntry])
    const amountCells = wrapper.findAll('.amount-cell')

    expect(amountCells[0].text()).toBe('+$500.00')
    expect(amountCells[0].classes()).toContain('result-positive')
    expect(amountCells[1].text()).toBe('-$150.00')
    expect(amountCells[1].classes()).toContain('result-negative')
  })

  it('shows an empty-state row when there are no entries', () => {
    const { wrapper } = mountTable([])
    expect(wrapper.text()).toContain('No entries yet this year.')
  })

  it('emits edit with the entry when its Edit button is clicked', async () => {
    const { wrapper } = mountTable([incomeEntry])
    await wrapper.findAll('.btn-chip--ghost')[0].trigger('click')

    expect(wrapper.emitted('edit')).toBeTruthy()
    expect(wrapper.emitted('edit')[0][0]).toEqual(incomeEntry)
  })

  it('confirms and deletes an entry via the store, revoking any cached screenshot URL', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const { wrapper, store } = mountTable([incomeEntry])

    await wrapper.findAll('.btn-chip--danger')[0].trigger('click')
    await flushPromises()

    expect(store.deleteEntry).toHaveBeenCalledWith(1)
  })

  it('does not delete when the confirm dialog is declined', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const { wrapper, store } = mountTable([incomeEntry])

    await wrapper.findAll('.btn-chip--danger')[0].trigger('click')
    await flushPromises()

    expect(store.deleteEntry).not.toHaveBeenCalled()
  })

  it('lazily loads a screenshot object URL only when View is clicked', async () => {
    const { wrapper, store } = mountTable([expenseEntry])

    expect(store.fetchEntryScreenshotObjectUrl).not.toHaveBeenCalled()
    await wrapper.find('.link-button').trigger('click')
    await flushPromises()

    expect(store.fetchEntryScreenshotObjectUrl).toHaveBeenCalledWith(2)
    expect(wrapper.find('.entry-screenshot-thumb').attributes('src')).toBe('blob:mock-url')
  })

  it('removes a screenshot via the store and clears the cached preview', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const { wrapper, store } = mountTable([expenseEntry])

    await wrapper.find('.link-button').trigger('click')
    await flushPromises()
    expect(wrapper.find('.entry-screenshot-thumb').exists()).toBe(true)

    await wrapper.find('.link-button--danger').trigger('click')
    await flushPromises()

    expect(store.deleteEntryScreenshot).toHaveBeenCalledWith(2)
    expect(wrapper.find('.entry-screenshot-thumb').exists()).toBe(false)
  })
})
