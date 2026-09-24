import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useTradesStore } from './trades'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }
}))

describe('trades store fetchTradesInWeek', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('requests the range with start/end params', async () => {
    api.get.mockResolvedValue({ data: [] })
    const store = useTradesStore()

    await store.fetchTradesInWeek('2026-02-02', '2026-02-08')

    expect(api.get).toHaveBeenCalledWith('/journal/trades', {
      params: { start: '2026-02-02', end: '2026-02-08' }
    })
  })

  it('populates tradesByDate for every day in range, empty array where absent', async () => {
    const mondayTrade = { id: 1, symbol: 'MNQ' }
    api.get.mockResolvedValue({ data: [{ date: '2026-02-02', trades: [mondayTrade] }] })
    const store = useTradesStore()

    await store.fetchTradesInWeek('2026-02-02', '2026-02-08')

    expect(store.tradesByDate['2026-02-02']).toEqual([mondayTrade])
    expect(store.tradesByDate['2026-02-03']).toEqual([])
    expect(store.tradesByDate['2026-02-08']).toEqual([])
  })

  it('merges into tradesByDate without clobbering dates outside the requested range', async () => {
    const store = useTradesStore()
    const priorTrade = { id: 99, symbol: 'MES' }
    store.tradesByDate = { '2026-01-15': [priorTrade] }

    api.get.mockResolvedValue({ data: [] })
    await store.fetchTradesInWeek('2026-02-02', '2026-02-08')

    expect(store.tradesByDate['2026-01-15']).toEqual([priorTrade])
  })

  it('overwrites a stale entry for a date that is back in an empty state', async () => {
    const store = useTradesStore()
    store.tradesByDate = { '2026-02-03': [{ id: 1, symbol: 'MNQ' }] }

    api.get.mockResolvedValue({ data: [] })
    await store.fetchTradesInWeek('2026-02-02', '2026-02-08')

    expect(store.tradesByDate['2026-02-03']).toEqual([])
  })
})
