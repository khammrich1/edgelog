import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import FinancialChart from './FinancialChart.vue'

function mockMatchMedia(matches) {
  window.matchMedia = vi.fn().mockImplementation((query) => ({
    matches,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn()
  }))
}

function mountChart(entries) {
  return mount(FinancialChart, { props: { entries, year: 2026 } })
}

describe('FinancialChart', () => {
  beforeEach(() => {
    mockMatchMedia(false)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('aggregates entries into monthly income/cost buckets on one shared axis', () => {
    const wrapper = mountChart([
      { id: 1, entry_type: 'income', amount: '100', date: '2026-01-05' },
      { id: 2, entry_type: 'expense', amount: '50', date: '2026-01-20' },
      { id: 3, entry_type: 'income', amount: '200', date: '2026-03-10' }
    ])

    const incomeBars = wrapper.findAll('.bar--income')
    const costBars = wrapper.findAll('.bar--cost')
    expect(incomeBars).toHaveLength(12)
    expect(costBars).toHaveLength(12)

    const janIncomeHeight = Number(incomeBars[0].attributes('height'))
    const janCostHeight = Number(costBars[0].attributes('height'))
    const marIncomeHeight = Number(incomeBars[2].attributes('height'))

    // Jan income (100) is double Jan cost (50) -- both on the same axis.
    expect(janIncomeHeight).toBeGreaterThan(janCostHeight)
    expect(janCostHeight).toBeGreaterThan(0)
    // March income (200) is the year's max value, so its bar is the tallest.
    expect(marIncomeHeight).toBeGreaterThan(janIncomeHeight)
    // A month with no entries renders a zero-height bar in both series.
    expect(Number(incomeBars[5].attributes('height'))).toBe(0)
    expect(Number(costBars[5].attributes('height'))).toBe(0)

    expect(wrapper.text()).toContain('Income +$300.00')
    expect(wrapper.text()).toContain('Expenses -$50.00')

    // The axis top gridline reflects the shared max (200), not either series alone.
    const axisLabels = wrapper.findAll('.axis-label').map((l) => l.text())
    expect(axisLabels).toContain('$200.00')
  })

  it('renders 3-letter month labels at a normal viewport width', () => {
    const wrapper = mountChart([])
    const labels = wrapper.findAll('.month-label').map((l) => l.text())
    expect(labels[0]).toBe('Jan')
    expect(labels).toHaveLength(12)
  })

  it('switches to 1-letter month labels under the narrow-viewport media query', async () => {
    mockMatchMedia(true)
    const wrapper = mountChart([])
    await wrapper.vm.$nextTick()
    const labels = wrapper.findAll('.month-label').map((l) => l.text())
    expect(labels[0]).toBe('J')
  })

  it('shows a hover tooltip on a bar and hides it again on mouse leave', async () => {
    const wrapper = mountChart([{ id: 1, entry_type: 'income', amount: '100', date: '2026-01-05' }])

    expect(wrapper.find('.chart-tooltip').exists()).toBe(false)

    await wrapper.find('.bar--income').trigger('mouseenter', { clientX: 50, clientY: 40 })
    const tooltip = wrapper.find('.chart-tooltip')
    expect(tooltip.exists()).toBe(true)
    expect(tooltip.text()).toContain('Jan Income')
    expect(tooltip.text()).toContain('$100.00')

    await wrapper.find('.bar--income').trigger('mouseleave')
    expect(wrapper.find('.chart-tooltip').exists()).toBe(false)
  })
})
