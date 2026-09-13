import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

// Per-point dollar multipliers, keyed by symbol -- fetched once from the
// backend's single source of truth (app/core/instruments.py) rather than
// hard-coded here, per VS3's rule against scattering instrument values
// through Vue components.
export const useInstrumentsStore = defineStore('instruments', () => {
  const multipliers = ref({})

  async function fetchMultipliers() {
    const { data } = await api.get('/instruments/multipliers')
    const parsed = {}
    for (const [symbol, value] of Object.entries(data)) {
      parsed[symbol] = Number(value)
    }
    multipliers.value = parsed
    return parsed
  }

  function getMultiplier(symbol) {
    if (!symbol) return null
    const known = multipliers.value[symbol.trim().toUpperCase()]
    return known === undefined ? null : known
  }

  return { multipliers, fetchMultipliers, getMultiplier }
})
