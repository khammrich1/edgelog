import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TradesSection from './TradesSection.vue'
import { useTradesStore } from '@/stores/trades'
import { useInstrumentsStore } from '@/stores/instruments'

function mountTradesSection({ trades = [] } = {}) {
  setActivePinia(createPinia())

  const tradesStore = useTradesStore()
  const instrumentsStore = useInstrumentsStore()
  // Replace the network-backed actions so the component's onMounted hooks
  // never attempt a real HTTP call in this jsdom environment.
  tradesStore.fetchTrades = vi.fn().mockResolvedValue(trades)
  tradesStore.fetchSetups = vi.fn().mockResolvedValue([])
  instrumentsStore.fetchMultipliers = vi.fn().mockResolvedValue({})
  if (trades.length) {
    tradesStore.tradesByDate = { '2026-01-01': trades }
  }

  const wrapper = mount(TradesSection, {
    props: { date: '2026-01-01', locked: false }
  })
  return { wrapper, tradesStore, instrumentsStore }
}

function openTrade() {
  return {
    id: 1,
    symbol: 'MNQ',
    direction: 'long',
    status: 'open',
    initial_quantity: 5,
    total_quantity: 5,
    remaining_quantity: 5,
    entry_price: '29780',
    average_entry_price: '29780',
    stop_price: '29755',
    target_price: null,
    setup: null,
    notes: null,
    planned_risk_dollars: '250',
    planned_risk_points: null,
    multiplier_known: true,
    has_screenshot: false,
    realized_pnl: null,
    realized_points: null,
    entries: [],
    exits: []
  }
}

describe('TradesSection direction toggle', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('defaults to LONG selected', () => {
    const { wrapper } = mountTradesSection()
    const buttons = wrapper.findAll('.direction-toggle-btn')
    const long = buttons.find((b) => b.text() === 'LONG')
    const short = buttons.find((b) => b.text() === 'SHORT')

    expect(long.classes()).toContain('direction-toggle-btn--active')
    expect(short.classes()).not.toContain('direction-toggle-btn--active')
  })

  it('switches to SHORT when clicked, deselecting LONG', async () => {
    const { wrapper } = mountTradesSection()
    const buttons = wrapper.findAll('.direction-toggle-btn')
    const long = buttons.find((b) => b.text() === 'LONG')
    const short = buttons.find((b) => b.text() === 'SHORT')

    await short.trigger('click')

    expect(short.classes()).toContain('direction-toggle-btn--active')
    expect(long.classes()).not.toContain('direction-toggle-btn--active')
  })

  it('colors LONG green and SHORT red, distinct from the shared P&L result classes', () => {
    const { wrapper } = mountTradesSection()
    const buttons = wrapper.findAll('.direction-toggle-btn')
    const long = buttons.find((b) => b.text() === 'LONG')
    const short = buttons.find((b) => b.text() === 'SHORT')

    expect(long.classes()).toContain('direction-toggle-btn--long')
    expect(short.classes()).toContain('direction-toggle-btn--short')
    // Direction coloring is its own class, not the trade-result P&L classes
    // (those stay reserved for actual profit/loss figures elsewhere).
    expect(long.classes()).not.toContain('result-positive')
    expect(short.classes()).not.toContain('result-negative')
  })
})

describe('TradesSection add-contracts / add-trim forms', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  async function mountExpandedOpenTrade() {
    const result = mountTradesSection({ trades: [openTrade()] })
    await result.wrapper.vm.$nextTick()
    await result.wrapper.find('.trade-card__header').trigger('click')
    return result
  }

  it('keeps the add-contracts and add-trim forms collapsed by default', async () => {
    const { wrapper } = await mountExpandedOpenTrade()

    expect(wrapper.find('input[placeholder="Entry price"]').exists()).toBe(false)
    expect(wrapper.find('input[placeholder="Exit price"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('+ Add contracts')
    expect(wrapper.text()).toContain('+ Add trim')
  })

  it('reveals the add-contracts form only after its toggle button is clicked', async () => {
    const { wrapper } = await mountExpandedOpenTrade()
    const buttons = wrapper.findAll('.btn-chip--ghost')
    const addContracts = buttons.find((b) => b.text() === '+ Add contracts')

    await addContracts.trigger('click')

    expect(wrapper.find('input[placeholder="Entry price"]').exists()).toBe(true)
    expect(wrapper.find('input[placeholder="Exit price"]').exists()).toBe(false)
  })

  it('reveals the add-trim form only after its toggle button is clicked, independently of add-contracts', async () => {
    const { wrapper } = await mountExpandedOpenTrade()
    const buttons = wrapper.findAll('.btn-chip--ghost')
    const addTrim = buttons.find((b) => b.text() === '+ Add trim')

    await addTrim.trigger('click')

    expect(wrapper.find('input[placeholder="Exit price"]').exists()).toBe(true)
    expect(wrapper.find('input[placeholder="Entry price"]').exists()).toBe(false)
  })

  it('collapses the add-contracts form again when its toggle is clicked a second time', async () => {
    const { wrapper } = await mountExpandedOpenTrade()
    const toggle = wrapper.findAll('.btn-chip--ghost').find((b) => b.text().includes('Add contracts'))

    await toggle.trigger('click')
    expect(wrapper.find('input[placeholder="Entry price"]').exists()).toBe(true)

    await toggle.trigger('click')
    expect(wrapper.find('input[placeholder="Entry price"]').exists()).toBe(false)
  })
})

describe('TradesSection new-trade form target field', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows Target directly on the primary form, not behind More fields', () => {
    const { wrapper } = mountTradesSection()
    expect(wrapper.find('input[placeholder="Target"]').exists()).toBe(true)
  })
})

describe('TradesSection trade screenshot storage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('offers "+ Add screenshot" for a trade with none yet, and never fetches one', async () => {
    const trade = openTrade()
    const { wrapper, tradesStore } = mountTradesSection({ trades: [trade] })
    tradesStore.fetchTradeScreenshotObjectUrl = vi.fn()

    await wrapper.find('.trade-card__header').trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('+ Add screenshot')
    expect(wrapper.text()).not.toContain('Remove screenshot')
    expect(tradesStore.fetchTradeScreenshotObjectUrl).not.toHaveBeenCalled()
  })

  it('fetches and displays the screenshot when expanding a trade that has one', async () => {
    const trade = { ...openTrade(), has_screenshot: true }
    const objectUrl = 'blob:mock-url'
    const { wrapper, tradesStore } = mountTradesSection({ trades: [trade] })
    tradesStore.fetchTradeScreenshotObjectUrl = vi.fn().mockResolvedValue(objectUrl)

    await wrapper.find('.trade-card__header').trigger('click')
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(tradesStore.fetchTradeScreenshotObjectUrl).toHaveBeenCalledWith('2026-01-01', trade.id)
    const img = wrapper.find('.trade-screenshot-preview')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe(objectUrl)
    expect(wrapper.text()).toContain('Replace screenshot')
    expect(wrapper.text()).toContain('Remove screenshot')
  })
})
