import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TradeDetailDrawer from './TradeDetailDrawer.vue'
import { useTradesStore } from '@/stores/trades'

const pushMock = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock })
}))

function baseTrade(overrides = {}) {
  return {
    id: 1,
    symbol: 'MNQ',
    direction: 'long',
    status: 'closed',
    setup: 'Breakout',
    notes: null,
    average_entry_price: '20000',
    entry_price: '20000',
    initial_quantity: 5,
    total_quantity: 5,
    stop_price: '19980',
    target_price: '20040',
    realized_pnl: '150',
    realized_points: '15',
    planned_risk_dollars: '100',
    multiplier_known: true,
    has_screenshot: false,
    entries: [],
    exits: [],
    ...overrides
  }
}

function mountDrawer(tradeOverrides = {}, date = '2026-02-02') {
  setActivePinia(createPinia())
  const tradesStore = useTradesStore()
  tradesStore.fetchTradeScreenshotObjectUrl = vi.fn().mockResolvedValue('blob:mock-url')

  const wrapper = mount(TradeDetailDrawer, {
    props: { trade: baseTrade(tradeOverrides), date }
  })
  return { wrapper, tradesStore }
}

describe('TradeDetailDrawer', () => {
  beforeEach(() => {
    pushMock.mockClear()
  })

  it('renders entry/stop/target/contracts/setup and realized P&L with R-multiple', () => {
    const { wrapper } = mountDrawer()
    const text = wrapper.text()
    expect(text).toContain('20,000')
    expect(text).toContain('19,980')
    expect(text).toContain('20,040')
    expect(text).toContain('5')
    expect(text).toContain('Breakout')
    expect(text).toContain('+$150.00')
    expect(text).toContain('+1.5R')
  })

  it('renders entries and trims lists when present', () => {
    const { wrapper } = mountDrawer({
      entries: [{ id: 2, quantity: 2, entry_price: '20010' }],
      exits: [{ id: 3, quantity: 3, exit_price: '20050' }]
    })
    expect(wrapper.text()).toContain('Entries')
    expect(wrapper.text()).toContain('Trims')
  })

  it('never renders reasoning, emotional state, or grade sections', () => {
    const { wrapper } = mountDrawer()
    const text = wrapper.text().toLowerCase()
    expect(text).not.toContain('reasoning')
    expect(text).not.toContain('emotional')
    expect(text).not.toContain('grade')
  })

  it('lazily fetches and displays the screenshot only when has_screenshot is true', async () => {
    const { wrapper, tradesStore } = mountDrawer({ has_screenshot: true })
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(tradesStore.fetchTradeScreenshotObjectUrl).toHaveBeenCalledWith('2026-02-02', 1)
    expect(wrapper.find('.drawer-screenshot').attributes('src')).toBe('blob:mock-url')
  })

  it('does not fetch a screenshot when has_screenshot is false', async () => {
    const { wrapper, tradesStore } = mountDrawer({ has_screenshot: false })
    await wrapper.vm.$nextTick()

    expect(tradesStore.fetchTradeScreenshotObjectUrl).not.toHaveBeenCalled()
    expect(wrapper.find('.drawer-screenshot').exists()).toBe(false)
  })

  it('navigates to the Daily Journal for the trade date on click', async () => {
    const { wrapper } = mountDrawer()
    await wrapper.find('.journal-link').trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/journal/2026-02-02')
  })

  it('emits close when the close button is clicked', async () => {
    const { wrapper } = mountDrawer()
    await wrapper.find('.close-button').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits close when the backdrop is clicked but not when the panel itself is clicked', async () => {
    const { wrapper } = mountDrawer()
    await wrapper.find('.drawer-panel').trigger('click')
    expect(wrapper.emitted('close')).toBeFalsy()

    await wrapper.find('.drawer-backdrop').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits close on Escape keydown', async () => {
    const { wrapper } = mountDrawer()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
