import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TradesSection from './TradesSection.vue'
import { useTradesStore } from '@/stores/trades'
import { useInstrumentsStore } from '@/stores/instruments'

function mountTradesSection() {
  setActivePinia(createPinia())

  const tradesStore = useTradesStore()
  const instrumentsStore = useInstrumentsStore()
  // Replace the network-backed actions so the component's onMounted hooks
  // never attempt a real HTTP call in this jsdom environment.
  tradesStore.fetchTrades = vi.fn().mockResolvedValue([])
  tradesStore.fetchSetups = vi.fn().mockResolvedValue([])
  instrumentsStore.fetchMultipliers = vi.fn().mockResolvedValue({})

  const wrapper = mount(TradesSection, {
    props: { date: '2026-01-01', locked: false }
  })
  return { wrapper, tradesStore, instrumentsStore }
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
