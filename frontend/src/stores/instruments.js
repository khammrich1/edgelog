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

  // Mirrors backend/app/core/instruments.py's _DATED_CONTRACT_RE: a dated
  // futures contract like "MNQZ26" is root "MNQ" + single-letter month code
  // + 1-4 digit year. Only this parsing pattern is duplicated here -- the
  // multiplier values themselves still come from the fetched table above,
  // the one source of truth for those.
  const DATED_CONTRACT_RE = /^([A-Z]{1,3})[FGHJKMNQUVXZ]\d{1,4}$/

  function getMultiplier(symbol) {
    if (!symbol) return null
    const normalized = symbol.trim().toUpperCase()
    const known = multipliers.value[normalized]
    if (known !== undefined) return known

    const match = normalized.match(DATED_CONTRACT_RE)
    if (match) {
      const rootKnown = multipliers.value[match[1]]
      if (rootKnown !== undefined) return rootKnown
    }
    return null
  }

  return { multipliers, fetchMultipliers, getMultiplier }
})
