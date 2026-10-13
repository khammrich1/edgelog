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

  it('supports arrow, Home, and End navigation with one tab stop and linked panels', async () => {
    const wrapper = await mountJournalDay()
    const tabs = wrapper.findAll('[role="tab"]')
    expect(tabs.map(tab => tab.attributes('tabindex'))).toEqual(['0', '-1', '-1'])
    await tabs[0].trigger('keydown', { key: 'ArrowRight' })
    expect(wrapper.find('.day-tab--active').text()).toBe('Trades')
    expect(wrapper.find('#trades-panel').isVisible()).toBe(true)
    await tabs[1].trigger('keydown', { key: 'End' })
    expect(wrapper.find('#overview-panel').isVisible()).toBe(true)
    await tabs[2].trigger('keydown', { key: 'ArrowRight' })
    expect(wrapper.find('#preparation-panel').isVisible()).toBe(true)
    await tabs[0].trigger('keydown', { key: 'ArrowLeft' })
    expect(wrapper.find('#overview-panel').isVisible()).toBe(true)
    await tabs[2].trigger('keydown', { key: 'Home' })
    expect(wrapper.find('.day-tab--active').text()).toBe('Mood & Bias')
    for (const tab of tabs) {
      expect(wrapper.find(`#${tab.attributes('aria-controls')}`).attributes('aria-labelledby')).toBe(tab.attributes('id'))
    }
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

describe('JournalDay loadDay request parallelism (issue #71)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches checklist items and the day record concurrently, not one after the other', async () => {
    setActivePinia(createPinia())

    let resolveChecklist
    const journalStore = useJournalStore()
    journalStore.fetchChecklistItems = vi.fn().mockImplementation(
      () => new Promise((resolve) => { resolveChecklist = resolve })
    )
    journalStore.fetchDay = vi.fn().mockImplementation(async () => {
      journalStore.currentDay = { ...FAKE_DAY }
      return FAKE_DAY
    })

    const tradesStore = useTradesStore()
    tradesStore.fetchTrades = vi.fn().mockResolvedValue([])
    tradesStore.fetchSetups = vi.fn().mockResolvedValue([])
    const instrumentsStore = useInstrumentsStore()
    instrumentsStore.fetchMultipliers = vi.fn().mockResolvedValue({})

    mount(JournalDay)
    await flushPromises()

    // fetchChecklistItems is still pending (never resolved) -- if the two
    // calls were serialized (await fetchChecklistItems() before calling
    // fetchDay()), fetchDay would never have been reached yet.
    expect(journalStore.fetchChecklistItems).toHaveBeenCalledTimes(1)
    expect(journalStore.fetchDay).toHaveBeenCalledTimes(1)

    resolveChecklist([])
    await flushPromises()
  })
})

describe('JournalDay Mood/Sleep optimistic selection (issue #73)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  function sleepButton(wrapper, value) {
    return wrapper.find(`button[aria-label="Sleep quality ${value} of 5"]`)
  }
  function moodButton(wrapper, value) {
    return wrapper.find(`button[aria-label="Mood ${value} of 5"]`)
  }

  it('highlights the clicked sleep-quality button immediately, before the save resolves', async () => {
    const wrapper = await mountJournalDay()
    const journalStore = useJournalStore()
    let resolveSave
    journalStore.updateDay = vi.fn().mockImplementation(() => new Promise((resolve) => { resolveSave = resolve }))

    await sleepButton(wrapper, 4).trigger('click')
    await wrapper.vm.$nextTick()

    expect(sleepButton(wrapper, 4).classes()).toContain('scale-button--selected')
    expect(journalStore.updateDay).toHaveBeenCalledWith('2026-01-01', { sleep_quality: 4 })

    resolveSave({ ...FAKE_DAY, sleep_quality: 4 })
    await flushPromises()
    expect(sleepButton(wrapper, 4).classes()).toContain('scale-button--selected')
  })

  it('rolls back and shows an error when the save fails', async () => {
    const wrapper = await mountJournalDay({ mood: 2 })
    const journalStore = useJournalStore()
    let rejectSave
    journalStore.updateDay = vi.fn().mockImplementation(() => new Promise((_, reject) => { rejectSave = reject }))

    await moodButton(wrapper, 5).trigger('click')
    await wrapper.vm.$nextTick()
    expect(moodButton(wrapper, 5).classes()).toContain('scale-button--selected')

    rejectSave({ response: { data: { detail: 'Network error' } } })
    await flushPromises()

    // Rolled back to the pre-click value, and the original selection is
    // the only one highlighted again.
    expect(moodButton(wrapper, 5).classes()).not.toContain('scale-button--selected')
    expect(moodButton(wrapper, 2).classes()).toContain('scale-button--selected')
    expect(wrapper.text()).toContain('Network error')
  })

  it('rapid clicks: the latest click wins even if its response arrives before an earlier one', async () => {
    const wrapper = await mountJournalDay()
    const journalStore = useJournalStore()
    const resolvers = []
    journalStore.updateDay = vi.fn().mockImplementation(
      () => new Promise((resolve) => resolvers.push(resolve))
    )

    await sleepButton(wrapper, 2).trigger('click')
    await sleepButton(wrapper, 5).trigger('click')
    await wrapper.vm.$nextTick()

    // The second click is the latest intent -- must be the one shown,
    // immediately, regardless of what either save ends up returning.
    expect(sleepButton(wrapper, 5).classes()).toContain('scale-button--selected')

    // The *first* (now-stale) request resolves after the second: it must
    // not be allowed to visually override the newer click.
    resolvers[0]({ ...FAKE_DAY, sleep_quality: 2 })
    await flushPromises()
    expect(sleepButton(wrapper, 5).classes()).toContain('scale-button--selected')
    expect(sleepButton(wrapper, 2).classes()).not.toContain('scale-button--selected')

    resolvers[1]({ ...FAKE_DAY, sleep_quality: 5 })
    await flushPromises()
    expect(sleepButton(wrapper, 5).classes()).toContain('scale-button--selected')
  })

  it('sleep-quality and mood saves are independent -- an error on one does not touch the other', async () => {
    const wrapper = await mountJournalDay()
    const journalStore = useJournalStore()
    journalStore.updateDay = vi.fn().mockImplementation(async (date, payload) => {
      if ('sleep_quality' in payload) throw { response: { data: { detail: 'Could not save.' } } }
      return { ...FAKE_DAY, ...payload }
    })

    await sleepButton(wrapper, 3).trigger('click')
    await moodButton(wrapper, 4).trigger('click')
    await flushPromises()

    expect(sleepButton(wrapper, 3).classes()).not.toContain('scale-button--selected')
    expect(moodButton(wrapper, 4).classes()).toContain('scale-button--selected')
  })
})
