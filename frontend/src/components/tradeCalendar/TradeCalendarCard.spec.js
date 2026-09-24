import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TradeCalendarCard from './TradeCalendarCard.vue'

function baseTrade(overrides = {}) {
  return {
    id: 1,
    symbol: 'MNQ',
    direction: 'long',
    status: 'open',
    setup: 'Breakout',
    entry_time: '2026-02-02T14:30:00Z',
    average_entry_price: '20000',
    realized_pnl: null,
    realized_points: null,
    planned_risk_dollars: null,
    multiplier_known: true,
    ...overrides
  }
}

describe('TradeCalendarCard', () => {
  it('renders symbol, direction, setup, and status', () => {
    const wrapper = mount(TradeCalendarCard, { props: { trade: baseTrade() } })
    expect(wrapper.text()).toContain('MNQ')
    expect(wrapper.text()).toContain('LONG')
    expect(wrapper.text()).toContain('Breakout')
    expect(wrapper.text()).toContain('OPEN')
  })

  it('shows no P&L for an open trade', () => {
    const wrapper = mount(TradeCalendarCard, { props: { trade: baseTrade() } })
    expect(wrapper.find('.calendar-trade-card__result').exists()).toBe(false)
  })

  it('shows a green dollar result for a profitable closed trade', () => {
    const wrapper = mount(TradeCalendarCard, {
      props: { trade: baseTrade({ status: 'closed', realized_pnl: '150' }) }
    })
    const result = wrapper.find('.calendar-trade-card__result')
    expect(result.text()).toContain('+$150.00')
    expect(result.classes()).toContain('result-positive')
  })

  it('shows a red result for a losing closed trade', () => {
    const wrapper = mount(TradeCalendarCard, {
      props: { trade: baseTrade({ status: 'closed', realized_pnl: '-75' }) }
    })
    const result = wrapper.find('.calendar-trade-card__result')
    expect(result.text()).toContain('-$75.00')
    expect(result.classes()).toContain('result-negative')
  })

  it('falls back to points when the multiplier is unknown', () => {
    const wrapper = mount(TradeCalendarCard, {
      props: {
        trade: baseTrade({ status: 'closed', multiplier_known: false, realized_points: '12' })
      }
    })
    expect(wrapper.find('.calendar-trade-card__result').text()).toContain('+12 pts')
  })

  it('shows the realized R-multiple when planned risk is known', () => {
    const wrapper = mount(TradeCalendarCard, {
      props: { trade: baseTrade({ status: 'closed', realized_pnl: '200', planned_risk_dollars: '100' }) }
    })
    expect(wrapper.find('.calendar-trade-card__result').text()).toContain('+2.0R')
  })

  it('applies the selected styling when selected is true', () => {
    const wrapper = mount(TradeCalendarCard, { props: { trade: baseTrade(), selected: true } })
    expect(wrapper.classes()).toContain('calendar-trade-card--selected')
  })

  it('emits select with the trade id on click', async () => {
    const wrapper = mount(TradeCalendarCard, { props: { trade: baseTrade({ id: 42 }) } })
    await wrapper.trigger('click')
    expect(wrapper.emitted('select')[0]).toEqual([42])
  })
})
