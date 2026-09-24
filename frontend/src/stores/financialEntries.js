import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useFinancialEntriesStore = defineStore('financialEntries', () => {
  // State: year (number) -> array of FinancialEntryRead for that year.
  const entriesByYear = ref({})

  function _yearOf(entry) {
    return Number(entry.date.slice(0, 4))
  }

  function _upsertIntoYear(entry) {
    const year = _yearOf(entry)
    const existing = entriesByYear.value[year] || []
    const withoutThis = existing.filter((e) => e.id !== entry.id)
    entriesByYear.value = { ...entriesByYear.value, [year]: [...withoutThis, entry] }
  }

  // Editing an entry's date can move it into a different year than the one
  // it was originally fetched under -- unlike Trade (whose day is fixed at
  // creation) -- so update/removal must scan every loaded year, not just
  // whichever year is currently being viewed.
  function _removeFromAllYears(entryId) {
    const next = {}
    for (const [year, entries] of Object.entries(entriesByYear.value)) {
      next[year] = entries.filter((e) => e.id !== entryId)
    }
    entriesByYear.value = next
  }

  async function fetchEntriesForYear(year) {
    const { data } = await api.get('/financial-entries', {
      params: { start: `${year}-01-01`, end: `${year}-12-31` }
    })
    entriesByYear.value = { ...entriesByYear.value, [year]: data }
    return data
  }

  async function createEntry(payload) {
    const { data } = await api.post('/financial-entries', payload)
    _upsertIntoYear(data)
    return data
  }

  async function updateEntry(entryId, payload) {
    const { data } = await api.put(`/financial-entries/${entryId}`, payload)
    _removeFromAllYears(entryId)
    _upsertIntoYear(data)
    return data
  }

  async function deleteEntry(entryId) {
    await api.delete(`/financial-entries/${entryId}`)
    _removeFromAllYears(entryId)
  }

  async function parseFinancialScreenshot(file) {
    const formData = new FormData()
    formData.append('file', file)
    // The api instance defaults Content-Type to application/json; that has
    // to be cleared so the browser can set the multipart boundary itself.
    const { data } = await api.post('/financial-entries/parse-screenshot', formData, {
      headers: { 'Content-Type': undefined }
    })
    return data
  }

  async function uploadEntryScreenshot(entryId, file) {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post(`/financial-entries/${entryId}/screenshot`, formData, {
      headers: { 'Content-Type': undefined }
    })
    _upsertIntoYear(data)
    return data
  }

  async function deleteEntryScreenshot(entryId) {
    const { data } = await api.delete(`/financial-entries/${entryId}/screenshot`)
    _upsertIntoYear(data)
    return data
  }

  /**
   * The financial-entry screenshot endpoint requires the in-memory bearer
   * token, so a plain <img src> can't be used. Fetch it through the
   * authenticated api client and hand back an object URL instead; callers
   * must revoke it.
   */
  async function fetchEntryScreenshotObjectUrl(entryId) {
    const response = await api.get(`/financial-entries/${entryId}/screenshot`, {
      responseType: 'blob'
    })
    return URL.createObjectURL(response.data)
  }

  return {
    entriesByYear,
    fetchEntriesForYear,
    createEntry,
    updateEntry,
    deleteEntry,
    parseFinancialScreenshot,
    uploadEntryScreenshot,
    deleteEntryScreenshot,
    fetchEntryScreenshotObjectUrl
  }
})
