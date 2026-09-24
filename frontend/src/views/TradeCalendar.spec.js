import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TradeCalendar from './TradeCalendar.vue'
import { useTradesStore } from '@/stores/trades'
import { useInstrumentsStore } from '@/stores/instruments'

let routeParams = { date: '2026-02-05' } // a Thursday
const replaceMock = vi.fn()

function fakeTrade(overrides = {}) {
  return {
    id: 1,
    symbol: 'MNQ',
    direction: 'long',
    status: 'open',
    entry_time: '2026-02-04T09:00:00Z',
    entries: [],
    exits: [],
    has_screenshot: false,
    ...overrides
  }
}

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: routeParams }),
  useRouter: () => ({ push: vi.fn(), replace: replaceMock })
}))

async function mountTradeCalendar(tradesByDate = {}) {
  setActivePinia(createPinia())
  const tradesStore = useTradesStore()
  tradesStore.fetchTradesInWeek = vi.fn().mockResolvedValue([])
  tradesStore.tradesByDate = tradesByDate

  const instrumentsStore = useInstrumentsStore()
  instrumentsStore.fetchMultipliers = vi.fn().mockResolvedValue({})

  const wrapper = mount(TradeCalendar)
  await flushPromises()
  return { wrapper, tradesStore }
}

describe('TradeCalendar', () => {
  beforeEach(() => {
    routeParams = { date: '2026-02-05' }
    replaceMock.mockClear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('loads the Monday-Sunday week containing the route date', async () => {
    const { tradesStore } = await mountTradeCalendar()
    expect(tradesStore.fetchTradesInWeek).toHaveBeenCalledWith('2026-02-02', '2026-02-08')
  })

  it('renders the week heading', async () => {
    const { wrapper } = await mountTradeCalendar()
    expect(wrapper.find('h1').text()).toBe('Feb 2 – Feb 8, 2026')
  })

  it('renders trade cards under the correct day column', async () => {
    const { wrapper } = await mountTradeCalendar({ '2026-02-04': [fakeTrade()] })

    const columns = wrapper.findAll('.day-column')
    const wednesday = columns[2] // Mon, Tue, Wed -> index 2
    expect(wednesday.text()).toContain('MNQ')
  })

  it('moves to the previous week and re-fetches', async () => {
    const { wrapper, tradesStore } = await mountTradeCalendar()
    tradesStore.fetchTradesInWeek.mockClear()

    await wrapper.find('.nav-button[aria-label="Previous week"]').trigger('click')
    await flushPromises()

    // Navigation always lands on the new week's Monday, regardless of which
    // weekday within the current week was originally being viewed.
    expect(replaceMock).toHaveBeenCalledWith('/trades/2026-01-26')
    expect(tradesStore.fetchTradesInWeek).toHaveBeenCalledWith('2026-01-26', '2026-02-01')
  })

  it('moves to the next week and re-fetches', async () => {
    const { wrapper, tradesStore } = await mountTradeCalendar()
    tradesStore.fetchTradesInWeek.mockClear()

    await wrapper.find('.nav-button[aria-label="Next week"]').trigger('click')
    await flushPromises()

    expect(replaceMock).toHaveBeenCalledWith('/trades/2026-02-09')
    expect(tradesStore.fetchTradesInWeek).toHaveBeenCalledWith('2026-02-09', '2026-02-15')
  })

  it('returns to the current week on Today', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 5, 17)) // a Wednesday
    const { wrapper, tradesStore } = await mountTradeCalendar()
    tradesStore.fetchTradesInWeek.mockClear()

    await wrapper.find('.nav-today').trigger('click')
    await flushPromises()

    expect(replaceMock).toHaveBeenCalledWith('/trades/2026-06-17')
    expect(tradesStore.fetchTradesInWeek).toHaveBeenCalledWith('2026-06-15', '2026-06-21')
  })

  it('jumps to the week containing a picked date', async () => {
    const { wrapper, tradesStore } = await mountTradeCalendar()
    tradesStore.fetchTradesInWeek.mockClear()

    const input = wrapper.find('.jump-input')
    await input.setValue('2026-03-10')
    await flushPromises()

    expect(replaceMock).toHaveBeenCalledWith('/trades/2026-03-10')
    expect(tradesStore.fetchTradesInWeek).toHaveBeenCalledWith('2026-03-09', '2026-03-15')
  })

  it('opens the detail drawer for a selected trade and closes it', async () => {
    const { wrapper } = await mountTradeCalendar({ '2026-02-04': [fakeTrade()] })

    expect(wrapper.find('.drawer-panel').exists()).toBe(false)

    await wrapper.find('.calendar-trade-card').trigger('click')
    expect(wrapper.find('.drawer-panel').exists()).toBe(true)

    await wrapper.find('.close-button').trigger('click')
    expect(wrapper.find('.drawer-panel').exists()).toBe(false)
  })
})
