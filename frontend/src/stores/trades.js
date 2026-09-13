import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useTradesStore = defineStore('trades', () => {
  // State: date (YYYY-MM-DD) -> array of TradeRead
  const tradesByDate = ref({})
  // Configured trade setups (quick-pick options for the trade form's Setup
  // dropdown) -- same shortcut-not-restriction relationship SYMBOL_PRESETS
  // has to Trade.symbol.
  const setups = ref([])

  function _setTrades(date, trades) {
    tradesByDate.value = { ...tradesByDate.value, [date]: trades }
  }

  function _replaceTrade(date, trade) {
    const existing = tradesByDate.value[date] || []
    _setTrades(
      date,
      existing.map((t) => (t.id === trade.id ? trade : t))
    )
  }

  async function fetchTrades(date) {
    const { data } = await api.get(`/journal/days/${date}/trades`)
    _setTrades(date, data)
    return data
  }

  async function createTrade(date, payload) {
    const { data } = await api.post(`/journal/days/${date}/trades`, payload)
    const existing = tradesByDate.value[date] || []
    _setTrades(date, [...existing, data])
    return data
  }

  async function updateTrade(date, tradeId, payload) {
    const { data } = await api.put(`/journal/days/${date}/trades/${tradeId}`, payload)
    _replaceTrade(date, data)
    return data
  }

  async function deleteTrade(date, tradeId) {
    await api.delete(`/journal/days/${date}/trades/${tradeId}`)
    const existing = tradesByDate.value[date] || []
    _setTrades(
      date,
      existing.filter((t) => t.id !== tradeId)
    )
  }

  async function addExit(date, tradeId, payload) {
    const { data } = await api.post(`/journal/days/${date}/trades/${tradeId}/exits`, payload)
    _replaceTrade(date, data)
    return data
  }

  async function deleteExit(date, tradeId, exitId) {
    const { data } = await api.delete(`/journal/days/${date}/trades/${tradeId}/exits/${exitId}`)
    _replaceTrade(date, data)
    return data
  }

  async function addEntry(date, tradeId, payload) {
    const { data } = await api.post(`/journal/days/${date}/trades/${tradeId}/entries`, payload)
    _replaceTrade(date, data)
    return data
  }

  async function deleteEntry(date, tradeId, entryId) {
    const { data } = await api.delete(`/journal/days/${date}/trades/${tradeId}/entries/${entryId}`)
    _replaceTrade(date, data)
    return data
  }

  async function cancelTrade(date, tradeId) {
    const { data } = await api.post(`/journal/days/${date}/trades/${tradeId}/cancel`)
    _replaceTrade(date, data)
    return data
  }

  async function parseScreenshot(file) {
    const formData = new FormData()
    formData.append('file', file)
    // The api instance defaults Content-Type to application/json; that has
    // to be cleared so the browser can set the multipart boundary itself.
    const { data } = await api.post('/trades/parse-screenshot', formData, {
      headers: { 'Content-Type': undefined }
    })
    return data
  }

  async function fetchSetups() {
    const { data } = await api.get('/journal/trade-setups')
    setups.value = data
    return data
  }

  async function createSetup(name) {
    const { data } = await api.post('/journal/trade-setups', { name })
    setups.value = [...setups.value, data]
    return data
  }

  async function deleteSetup(setupId) {
    await api.delete(`/journal/trade-setups/${setupId}`)
    setups.value = setups.value.filter((s) => s.id !== setupId)
  }

  return {
    tradesByDate,
    setups,
    fetchTrades,
    createTrade,
    updateTrade,
    deleteTrade,
    addExit,
    deleteExit,
    addEntry,
    deleteEntry,
    cancelTrade,
    parseScreenshot,
    fetchSetups,
    createSetup,
    deleteSetup
  }
})
