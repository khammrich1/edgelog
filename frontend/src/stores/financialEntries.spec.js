import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useFinancialEntriesStore } from './financialEntries'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }
}))

describe('financialEntries store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('fetchEntriesForYear requests the full-year range', async () => {
    api.get.mockResolvedValue({ data: [] })
    const store = useFinancialEntriesStore()

    await store.fetchEntriesForYear(2026)

    expect(api.get).toHaveBeenCalledWith('/financial-entries', {
      params: { start: '2026-01-01', end: '2026-12-31' }
    })
  })

  it('fetchEntriesForYear populates the correct year bucket', async () => {
    const entry = { id: 1, date: '2026-06-15', entry_type: 'income' }
    api.get.mockResolvedValue({ data: [entry] })
    const store = useFinancialEntriesStore()

    await store.fetchEntriesForYear(2026)

    expect(store.entriesByYear[2026]).toEqual([entry])
  })

  it('createEntry places the new entry in the year derived from its own date, not the currently viewed year', async () => {
    const entry = { id: 5, date: '2027-01-10', entry_type: 'expense' }
    api.post.mockResolvedValue({ data: entry })
    const store = useFinancialEntriesStore()
    store.entriesByYear = { 2026: [] }

    await store.createEntry({ entry_type: 'expense', category: 'fee', amount: '10', date: '2027-01-10' })

    expect(store.entriesByYear[2027]).toEqual([entry])
    expect(store.entriesByYear[2026]).toEqual([])
  })

  it('updateEntry moves an entry out of its old year bucket into the new one when the date changes years', async () => {
    const original = { id: 7, date: '2026-03-01', entry_type: 'expense' }
    const updated = { id: 7, date: '2027-03-01', entry_type: 'expense' }
    const store = useFinancialEntriesStore()
    store.entriesByYear = { 2026: [original] }

    api.put.mockResolvedValue({ data: updated })
    await store.updateEntry(7, { date: '2027-03-01' })

    expect(store.entriesByYear[2026]).toEqual([])
    expect(store.entriesByYear[2027]).toEqual([updated])
  })

  it('deleteEntry removes the entry from whichever year bucket holds it', async () => {
    const entry = { id: 9, date: '2026-05-01', entry_type: 'income' }
    const store = useFinancialEntriesStore()
    store.entriesByYear = { 2026: [entry] }

    api.delete.mockResolvedValue({})
    await store.deleteEntry(9)

    expect(store.entriesByYear[2026]).toEqual([])
  })

  it('parseFinancialScreenshot posts multipart with the Content-Type override cleared', async () => {
    api.post.mockResolvedValue({ data: { category: 'payout' } })
    const store = useFinancialEntriesStore()
    const file = new File(['x'], 'shot.png', { type: 'image/png' })

    await store.parseFinancialScreenshot(file)

    expect(api.post).toHaveBeenCalledWith(
      '/financial-entries/parse-screenshot',
      expect.any(FormData),
      { headers: { 'Content-Type': undefined } }
    )
  })

  it('uploadEntryScreenshot updates the entry in place', async () => {
    const entry = { id: 3, date: '2026-01-01', entry_type: 'expense', has_screenshot: true }
    api.post.mockResolvedValue({ data: entry })
    const store = useFinancialEntriesStore()
    const file = new File(['x'], 'shot.png', { type: 'image/png' })

    await store.uploadEntryScreenshot(3, file)

    expect(store.entriesByYear[2026]).toEqual([entry])
  })

  it('fetchEntryScreenshotObjectUrl requests a blob and returns an object URL', async () => {
    const blob = new Blob(['fake'])
    api.get.mockResolvedValue({ data: blob })
    const originalCreateObjectURL = URL.createObjectURL
    URL.createObjectURL = vi.fn().mockReturnValue('blob:mock-url')

    const store = useFinancialEntriesStore()
    const url = await store.fetchEntryScreenshotObjectUrl(3)

    expect(api.get).toHaveBeenCalledWith('/financial-entries/3/screenshot', { responseType: 'blob' })
    expect(url).toBe('blob:mock-url')

    URL.createObjectURL = originalCreateObjectURL
  })
})
