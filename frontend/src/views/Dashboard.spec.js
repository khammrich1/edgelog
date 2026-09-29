import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Dashboard from './Dashboard.vue'
import { useJournalStore } from '@/stores/journal'
import { useTradesStore } from '@/stores/trades'

const pushMock = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock })
}))

function fakeDaySummary(overrides = {}) {
  return { status: 'draft', has_bias_chart: false, checklist_completed_count: 0, checklist_total_count: 0, ...overrides }
}

function fakeTrade(overrides = {}) {
  return {
    id: 1,
    status: 'closed',
    realized_pnl: 0,
    realized_points: 0,
    multiplier_known: true,
    setup: null,
    ...overrides
  }
}

async function mountDashboard({ daysByDate = {}, tradesByDate = {} } = {}) {
  setActivePinia(createPinia())

  const journalStore = useJournalStore()
  journalStore.fetchDaysInRange = vi.fn().mockResolvedValue([])
  journalStore.daysByDate = daysByDate

  const tradesStore = useTradesStore()
  tradesStore.fetchTradesInWeek = vi.fn().mockResolvedValue([])
  tradesStore.tradesByDate = tradesByDate

  const wrapper = mount(Dashboard)
  await flushPromises()
  return { wrapper, journalStore, tradesStore }
}

describe('Dashboard', () => {
  beforeEach(() => {
    // A fixed Thursday so "today", "this week", and "recent activity" are
    // deterministic across the whole file.
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 1, 5))
    pushMock.mockClear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows "Not Started" and a Start CTA when today has no journal entry yet, without inventing a result', async () => {
    const { wrapper } = await mountDashboard()

    expect(wrapper.text()).toContain('Not Started')
    expect(wrapper.text()).toContain("Start Today's Journal")
    // No trades logged today -> the result field must read as unknown, not $0.
    expect(wrapper.find('.dashboard-stat-row').text()).toContain('—')
  })

  it('routes to today\'s journal entry when the primary CTA is clicked', async () => {
    const { wrapper } = await mountDashboard()

    await wrapper.find('.el-btn-primary').trigger('click')

    expect(pushMock).toHaveBeenCalledWith('/journal/2026-02-05')
  })

  it('shows "Draft" and a Continue CTA when today is in progress, with today\'s real trade count and result', async () => {
    const { wrapper } = await mountDashboard({
      daysByDate: { '2026-02-05': fakeDaySummary({ status: 'draft' }) },
      tradesByDate: {
        '2026-02-05': [fakeTrade({ id: 1, realized_pnl: 150, realized_points: 15, setup: 'ORB Retest' })]
      }
    })

    expect(wrapper.text()).toContain('Draft')
    expect(wrapper.text()).toContain("Continue Today's Journal")
    expect(wrapper.text()).toContain('+$150.00')
    expect(wrapper.text()).toContain('ORB Retest')
  })

  it('shows "Locked" and a non-primary Review CTA when today is already locked', async () => {
    const { wrapper } = await mountDashboard({
      daysByDate: { '2026-02-05': fakeDaySummary({ status: 'locked' }) }
    })

    expect(wrapper.text()).toContain('Locked')
    expect(wrapper.text()).toContain("Review Today's Journal")
    expect(wrapper.find('.el-btn-primary').exists()).toBe(false)
  })

  it('renders a truthful empty state for recent activity when no journal entries exist yet', async () => {
    const { wrapper } = await mountDashboard()

    expect(wrapper.text()).toContain('No trading days yet')
    expect(wrapper.find('.dashboard-activity-list').exists()).toBe(false)
  })

  it('lists recent trading days newest-first and navigates to a day on click', async () => {
    const { wrapper } = await mountDashboard({
      daysByDate: {
        '2026-02-05': fakeDaySummary({ status: 'draft' }),
        '2026-02-03': fakeDaySummary({ status: 'locked' })
      },
      tradesByDate: {
        '2026-02-03': [fakeTrade({ id: 2, realized_pnl: -50, realized_points: -5 })]
      }
    })

    const rows = wrapper.findAll('.dashboard-activity-row')
    expect(rows).toHaveLength(2)
    expect(rows[0].text()).toContain('Today')
    expect(rows[1].text()).toContain('-$50.00')

    await rows[1].trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/journal/2026-02-03')
  })

  it('shows the truthful no-closed-trades state for the weekly snapshot rather than a fabricated $0', async () => {
    const { wrapper } = await mountDashboard()

    expect(wrapper.find('.dashboard-snapshot').text()).toContain('No closed trades yet this week')
  })

  it('sums this week\'s closed trades in dollars when every multiplier is known', async () => {
    const { wrapper } = await mountDashboard({
      daysByDate: { '2026-02-04': fakeDaySummary() },
      tradesByDate: {
        '2026-02-04': [
          fakeTrade({ id: 1, realized_pnl: 200, realized_points: 20, setup: 'ORB Retest' }),
          fakeTrade({ id: 2, realized_pnl: -75, realized_points: -7.5, setup: 'ORB Retest' })
        ]
      }
    })

    const snapshot = wrapper.find('.dashboard-snapshot')
    expect(snapshot.text()).toContain('+$125.00')
    expect(snapshot.text()).toContain('1') // wins
    expect(snapshot.text()).toContain('ORB Retest ×2')
  })

  it('falls back to points and shows a caveat when a trade this week is missing its instrument multiplier', async () => {
    const { wrapper } = await mountDashboard({
      daysByDate: { '2026-02-04': fakeDaySummary() },
      tradesByDate: {
        '2026-02-04': [
          fakeTrade({ id: 1, realized_pnl: 200, realized_points: 20 }),
          fakeTrade({ id: 2, multiplier_known: false, realized_pnl: null, realized_points: -5 })
        ]
      }
    })

    const snapshot = wrapper.find('.dashboard-snapshot')
    expect(snapshot.text()).toContain('+15 pts')
    expect(snapshot.text()).toContain('missing instrument $ conversion')
    // Never presents a dollar figure when it would be partial/misleading.
    expect(snapshot.text()).not.toContain('$200')
  })

  it('nudges toward the most recent unfinished past day, distinct from today\'s own CTA', async () => {
    const { wrapper } = await mountDashboard({
      daysByDate: {
        '2026-02-05': fakeDaySummary({ status: 'draft' }),
        '2026-02-03': fakeDaySummary({ status: 'draft' })
      }
    })

    const nudge = wrapper.find('.dashboard-btn-link')
    expect(nudge.exists()).toBe(true)
    expect(nudge.text()).toContain('Feb 3')

    await nudge.trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/journal/2026-02-03')
  })

  it('shows an error state instead of the dashboard sections when the initial fetch fails', async () => {
    setActivePinia(createPinia())
    const journalStore = useJournalStore()
    journalStore.fetchDaysInRange = vi.fn().mockRejectedValue({ response: { data: { detail: 'Server error' } } })
    const tradesStore = useTradesStore()
    tradesStore.fetchTradesInWeek = vi.fn().mockResolvedValue([])

    const wrapper = mount(Dashboard)
    await flushPromises()

    expect(wrapper.find('.el-error-state').text()).toBe('Server error')
    expect(wrapper.find('.dashboard-top-grid').exists()).toBe(false)
  })
})
