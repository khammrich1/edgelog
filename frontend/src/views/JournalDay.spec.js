import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import JournalDay from './JournalDay.vue'
import { useJournalStore } from '@/stores/journal'
import { useTradesStore } from '@/stores/trades'
import { useInstrumentsStore } from '@/stores/instruments'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { date: '2026-01-01' } }),
  useRouter: () => ({ push: vi.fn() })
}))

const FAKE_DAY = {
  date: '2026-01-01',
  status: 'draft',
  sleep_quality: null,
  mood: null,
  market_bias: null,
  has_bias_chart: false,
  checklist: []
}

async function mountJournalDay(dayOverrides = {}) {
  setActivePinia(createPinia())
  const day = { ...FAKE_DAY, ...dayOverrides }

  const journalStore = useJournalStore()
  journalStore.fetchChecklistItems = vi.fn().mockResolvedValue([])
  journalStore.fetchDay = vi.fn().mockImplementation(async () => {
    journalStore.currentDay = day
    return day
  })

  const tradesStore = useTradesStore()
  tradesStore.fetchTrades = vi.fn().mockResolvedValue([])
  tradesStore.fetchSetups = vi.fn().mockResolvedValue([])

  const instrumentsStore = useInstrumentsStore()
  instrumentsStore.fetchMultipliers = vi.fn().mockResolvedValue({})

  const wrapper = mount(JournalDay)
  await flushPromises()
  return wrapper
}

describe('JournalDay tab navigation', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('defaults to the Mood & Bias tab, showing prep content', async () => {
    const wrapper = await mountJournalDay()

    expect(wrapper.find('.day-tab--active').text()).toBe('Mood & Bias')
    expect(wrapper.text()).toContain('Readiness')
    expect(wrapper.text()).toContain('Sleep Quality')
    expect(wrapper.text()).toContain('Morning Checklist')
  })

  it('switches to the Trades tab when clicked', async () => {
    const wrapper = await mountJournalDay()
    const tabs = wrapper.findAll('.day-tab')
    const tradesTab = tabs.find((t) => t.text() === 'Trades')

    await tradesTab.trigger('click')

    expect(wrapper.find('.day-tab--active').text()).toBe('Trades')
    expect(wrapper.findComponent({ name: 'TradesSection' }).exists() || wrapper.find('.trades-section').exists()).toBe(
      true
    )
  })

  it('switches to the Overview tab and shows the day summary', async () => {
    const wrapper = await mountJournalDay()
    const tabs = wrapper.findAll('.day-tab')
    const overviewTab = tabs.find((t) => t.text() === 'Overview')

    await overviewTab.trigger('click')

    expect(wrapper.find('.day-tab--active').text()).toBe('Overview')
    expect(wrapper.find('.day-overview').isVisible()).toBe(true)
    expect(wrapper.text()).toContain('Day Summary')
  })

  it('still disables trade mutation on a locked day inside the Trades tab', async () => {
    const wrapper = await mountJournalDay({ status: 'locked' })

    const tabs = wrapper.findAll('.day-tab')
    await tabs.find((t) => t.text() === 'Trades').trigger('click')

    // TradesSection only renders its "new trade" form when !locked.
    expect(wrapper.find('.trade-form').exists()).toBe(false)
    expect(wrapper.find('.locked-hint').exists()).toBe(true)
  })

  it('shows zero trades and a neutral P&L on an empty day', async () => {
    const wrapper = await mountJournalDay()
    const tabs = wrapper.findAll('.day-tab')
    await tabs.find((t) => t.text() === 'Overview').trigger('click')

    const overview = wrapper.find('.day-overview')
    expect(overview.text()).toContain('Trades')
    // No trades recorded for this day -- P&L must read as neutral, not $0.00
    // (which would misleadingly imply a trade broke exactly even).
    expect(overview.text()).toContain('—')
  })

  it('derives trade count, wins/losses, and day P&L from actual recorded trades', async () => {
    setActivePinia(createPinia())
    const journalStore = useJournalStore()
    journalStore.fetchChecklistItems = vi.fn().mockResolvedValue([])
    journalStore.fetchDay = vi.fn().mockImplementation(async () => {
      journalStore.currentDay = FAKE_DAY
      return FAKE_DAY
    })

    const tradesStore = useTradesStore()
    tradesStore.fetchTrades = vi.fn().mockResolvedValue([])
    tradesStore.fetchSetups = vi.fn().mockResolvedValue([])
    // A win, a loss, a still-open trade with an already-realized partial
    // trim, and a canceled trade that must be excluded entirely.
    tradesStore.tradesByDate = {
      '2026-01-01': [
        { id: 1, status: 'closed', multiplier_known: true, realized_pnl: 100, realized_points: 50 },
        { id: 2, status: 'closed', multiplier_known: true, realized_pnl: -40, realized_points: -20 },
        { id: 3, status: 'open', multiplier_known: true, realized_pnl: 20, realized_points: 10 },
        { id: 4, status: 'canceled', multiplier_known: true, realized_pnl: 0, realized_points: 0 }
      ]
    }

    const instrumentsStore = useInstrumentsStore()
    instrumentsStore.fetchMultipliers = vi.fn().mockResolvedValue({})

    const wrapper = mount(JournalDay)
    await flushPromises()
    await wrapper.findAll('.day-tab').find((t) => t.text() === 'Overview').trigger('click')

    // Read the Day Summary panel's fields by label rather than position, so
    // this doesn't silently break if panel order changes -- the canceled
    // trade (id 4) must not appear anywhere in these counts.
    const panel = wrapper
      .findAll('.el-workstation')
      .find((p) => p.find('.el-workstation-title').text() === 'Day Summary')
    const fields = {}
    for (const field of panel.findAll('.el-field')) {
      fields[field.find('.el-field-label').text()] = field.find('.overview-value').text()
    }

    expect(fields['Trades']).toBe('3')
    expect(fields['Wins']).toBe('1')
    expect(fields['Losses']).toBe('1')
    expect(fields['Day P&L']).toContain('+$80.00')
  })

  it('shows an empty state for the Overview trade recap when nothing was logged', async () => {
    const wrapper = await mountJournalDay()
    await wrapper.findAll('.day-tab').find((t) => t.text() === 'Overview').trigger('click')

    expect(wrapper.find('.overview-trades-panel').text()).toContain('No trades logged today.')
    expect(wrapper.find('.overview-trade-list').exists()).toBe(false)
  })

  it('lists each logged trade in the Overview recap with its setup and result, excluding canceled trades', async () => {
    setActivePinia(createPinia())
    const journalStore = useJournalStore()
    journalStore.fetchChecklistItems = vi.fn().mockResolvedValue([])
    journalStore.fetchDay = vi.fn().mockImplementation(async () => {
      journalStore.currentDay = FAKE_DAY
      return FAKE_DAY
    })

    const tradesStore = useTradesStore()
    tradesStore.fetchTrades = vi.fn().mockResolvedValue([])
    tradesStore.fetchSetups = vi.fn().mockResolvedValue([])
    tradesStore.tradesByDate = {
      '2026-01-01': [
        {
          id: 1,
          symbol: 'MNQ',
          direction: 'long',
          status: 'closed',
          setup: 'ORB Retest',
          multiplier_known: true,
          realized_pnl: 100,
          realized_points: 10
        },
        {
          id: 2,
          symbol: 'MES',
          direction: 'short',
          status: 'open',
          setup: null,
          multiplier_known: true,
          realized_pnl: 0,
          realized_points: 0
        },
        {
          id: 3,
          symbol: 'MGC',
          direction: 'long',
          status: 'canceled',
          setup: 'Breakout',
          multiplier_known: true,
          realized_pnl: 0,
          realized_points: 0
        }
      ]
    }

    const instrumentsStore = useInstrumentsStore()
    instrumentsStore.fetchMultipliers = vi.fn().mockResolvedValue({})

    const wrapper = mount(JournalDay)
    await flushPromises()
    await wrapper.findAll('.day-tab').find((t) => t.text() === 'Overview').trigger('click')

    const rows = wrapper.findAll('.overview-trade-row')
    expect(rows).toHaveLength(2)
    expect(rows[0].text()).toContain('MNQ')
    expect(rows[0].text()).toContain('ORB Retest')
    expect(rows[0].text()).toContain('+$100.00')
    expect(rows[1].text()).toContain('MES')
    expect(rows[1].text()).toContain('OPEN')
    // The canceled MGC trade must not appear in the recap at all.
    expect(wrapper.find('.overview-trades-panel').text()).not.toContain('MGC')
  })
})
