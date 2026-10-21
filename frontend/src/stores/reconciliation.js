import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

// Issue #97: a thin client for the existing read-only reconciliation
// preview endpoint (issue #80/#91/#96). This store makes exactly one kind
// of call -- POST .../reconciliation/preview -- and never writes anything;
// the result is held only in memory for as long as the tab is open (never
// persisted to localStorage/sessionStorage), matching the endpoint's own
// read-only contract.
export const useReconciliationStore = defineStore('reconciliation', () => {
  const result = ref(null)

  async function preview(payload) {
    const { data } = await api.post('/journal/reconciliation/preview', payload)
    result.value = data
    return data
  }

  function clear() {
    result.value = null
  }

  return { result, preview, clear }
})
