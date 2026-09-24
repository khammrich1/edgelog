import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Financials from './Financials.vue'
import { useFinancialEntriesStore } from '@/stores/financialEntries'

let routeParams = { year: '2026' }
const replaceMock = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: routeParams }),
  useRouter: () => ({ push: vi.fn(), replace: replaceMock })
}))

function fakeEntry(overrides = {}) {
  return {
    id: 1,
    entry_type: 'income',
    category: 'Payout',
    amount: '500.00',
    date: '2026-02-10',
    firm: null,
    has_screenshot: false,
    ...overrides
  }
}

async function mountFinancials(entriesByYear = {}) {
  setActivePinia(createPinia())
  const store = useFinancialEntriesStore()
  store.fetchEntriesForYear = vi.fn().mockResolvedValue([])
  store.entriesByYear = entriesByYear
  store.parseFinancialScreenshot = vi.fn()
  store.createEntry = vi.fn().mockResolvedValue({ id: 99 })
  store.updateEntry = vi.fn().mockResolvedValue({ id: 99 })
  store.uploadEntryScreenshot = vi.fn()
  store.deleteEntry = vi.fn()
  store.deleteEntryScreenshot = vi.fn()
  store.fetchEntryScreenshotObjectUrl = vi.fn()

  const wrapper = mount(Financials)
  await flushPromises()
  return { wrapper, store }
}

describe('Financials', () => {
  beforeEach(() => {
    routeParams = { year: '2026' }
    replaceMock.mockClear()
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn()
    }))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('seeds the viewed year from the route param and fetches it', async () => {
    const { wrapper, store } = await mountFinancials()
    expect(wrapper.find('h1').text()).toContain('2026')
    expect(store.fetchEntriesForYear).toHaveBeenCalledWith(2026)
  })

  it('falls back to the current year when no route param is present', async () => {
    routeParams = {}
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2027, 3, 1))
    const { wrapper, store } = await mountFinancials()

    expect(wrapper.find('h1').text()).toContain('2027')
    expect(store.fetchEntriesForYear).toHaveBeenCalledWith(2027)
  })

  it('moves to the previous year via replace (not push) and re-fetches', async () => {
    const { wrapper, store } = await mountFinancials()
    store.fetchEntriesForYear.mockClear()

    await wrapper.find('.nav-button[aria-label="Previous year"]').trigger('click')
    await flushPromises()

    expect(replaceMock).toHaveBeenCalledWith('/financials/2025')
    expect(store.fetchEntriesForYear).toHaveBeenCalledWith(2025)
  })

  it('moves to the next year via replace and re-fetches, crossing a Dec-to-Jan-style year boundary', async () => {
    const { wrapper, store } = await mountFinancials()
    store.fetchEntriesForYear.mockClear()

    await wrapper.find('.nav-button[aria-label="Next year"]').trigger('click')
    await flushPromises()

    expect(replaceMock).toHaveBeenCalledWith('/financials/2027')
    expect(store.fetchEntriesForYear).toHaveBeenCalledWith(2027)
  })

  it('returns to the current year via This year', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2030, 0, 15))
    const { wrapper, store } = await mountFinancials()
    store.fetchEntriesForYear.mockClear()

    await wrapper.find('.nav-today').trigger('click')
    await flushPromises()

    expect(replaceMock).toHaveBeenCalledWith('/financials/2030')
    expect(store.fetchEntriesForYear).toHaveBeenCalledWith(2030)
  })

  it('jumps to a manually picked year via replace', async () => {
    const { wrapper, store } = await mountFinancials()
    store.fetchEntriesForYear.mockClear()

    const input = wrapper.find('.jump-input')
    await input.setValue('2030')
    await flushPromises()

    expect(replaceMock).toHaveBeenCalledWith('/financials/2030')
    expect(store.fetchEntriesForYear).toHaveBeenCalledWith(2030)
  })

  it('computes income, expense, and net P&L summary tiles from the current year entries', async () => {
    const { wrapper } = await mountFinancials({
      2026: [
        fakeEntry({ id: 1, entry_type: 'income', amount: '500.00' }),
        fakeEntry({ id: 2, entry_type: 'expense', amount: '150.00' })
      ]
    })

    const tiles = wrapper.findAll('.summary-value')
    expect(tiles[0].text()).toBe('+$500.00') // Income
    expect(tiles[1].text()).toBe('-$150.00') // Expenses
    expect(tiles[2].text()).toBe('+$350.00') // Net P&L
    expect(tiles[2].classes()).toContain('result-positive')
  })
})
