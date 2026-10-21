import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

// Thin, read-only client for the existing reconciliation preview endpoint
// (issue #80 / PR #91). This store makes no write calls and holds the
// last preview only in memory -- it is never persisted to localStorage,
// sessionStorage, or any app store, per issue #97's requirement to avoid
// retaining raw execution data anywhere but the current page session.
export const useReconciliationStore = defineStore('reconciliation', () => {
  const lastPreview = ref(null)

  async function previewReconciliation(payload) {
    const { data } = await api.post('/journal/reconciliation/preview', payload)
    lastPreview.value = data
    return data
  }

  function clearPreview() {
    lastPreview.value = null
  }

  return { lastPreview, previewReconciliation, clearPreview }
})
