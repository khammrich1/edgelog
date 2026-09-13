import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useTradesStore = defineStore('trades', () => {
  // State: date (YYYY-MM-DD) -> array of TradeRead
  const tradesByDate = ref({})

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

  return {
    tradesByDate,
    fetchTrades,
    createTrade,
    updateTrade,
    deleteTrade,
    addExit,
    deleteExit
  }
})
