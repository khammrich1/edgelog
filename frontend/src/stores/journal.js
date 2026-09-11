import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useJournalStore = defineStore('journal', () => {
  // State
  const daysByDate = ref({}) // calendar summaries keyed by 'YYYY-MM-DD'
  const currentDay = ref(null) // the currently open TradingDayRead
  const checklistItems = ref([]) // active checklist item config
  const loading = ref(false)

  // Calendar month view
  async function fetchDaysInRange(start, end) {
    const { data } = await api.get('/journal/days', { params: { start, end } })
    const map = {}
    for (const summary of data) {
      map[summary.date] = summary
    }
    daysByDate.value = map
    return data
  }

  // Single day
  async function fetchDay(date) {
    loading.value = true
    try {
      const { data } = await api.get(`/journal/days/${date}`)
      currentDay.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function updateDay(date, payload) {
    const { data } = await api.put(`/journal/days/${date}`, payload)
    currentDay.value = data
    return data
  }

  async function toggleChecklistItem(date, itemId, completed) {
    const { data } = await api.put(`/journal/days/${date}/checklist/${itemId}`, { completed })
    currentDay.value = data
    return data
  }

  async function lockDay(date) {
    const { data } = await api.post(`/journal/days/${date}/lock`)
    currentDay.value = data
    return data
  }

  async function unlockDay(date) {
    const { data } = await api.post(`/journal/days/${date}/unlock`)
    currentDay.value = data
    return data
  }

  async function uploadBiasChart(date, file) {
    const formData = new FormData()
    formData.append('file', file)
    // The api instance defaults Content-Type to application/json; that has
    // to be cleared here so the browser can set multipart/form-data with the
    // correct boundary itself.
    const { data } = await api.post(`/journal/days/${date}/bias-chart`, formData, {
      headers: { 'Content-Type': undefined }
    })
    currentDay.value = data
    return data
  }

  async function deleteBiasChart(date) {
    const { data } = await api.delete(`/journal/days/${date}/bias-chart`)
    currentDay.value = data
    return data
  }

  /**
   * The bias chart endpoint requires the in-memory bearer token, so a plain
   * <img src> can't be used (the browser sends no Authorization header for
   * it). Fetch it through the authenticated api client and hand back an
   * object URL instead; callers are responsible for revoking it.
   */
  async function fetchBiasChartObjectUrl(date) {
    const response = await api.get(`/journal/days/${date}/bias-chart`, { responseType: 'blob' })
    return URL.createObjectURL(response.data)
  }

  // Checklist configuration
  async function fetchChecklistItems() {
    const { data } = await api.get('/journal/checklist-items')
    checklistItems.value = data
    return data
  }

  async function createChecklistItem(label) {
    const { data } = await api.post('/journal/checklist-items', { label })
    checklistItems.value = [...checklistItems.value, data]
    return data
  }

  async function deleteChecklistItem(itemId) {
    await api.delete(`/journal/checklist-items/${itemId}`)
    checklistItems.value = checklistItems.value.filter((item) => item.id !== itemId)
  }

  return {
    daysByDate,
    currentDay,
    checklistItems,
    loading,
    fetchDaysInRange,
    fetchDay,
    updateDay,
    toggleChecklistItem,
    lockDay,
    unlockDay,
    uploadBiasChart,
    deleteBiasChart,
    fetchBiasChartObjectUrl,
    fetchChecklistItems,
    createChecklistItem,
    deleteChecklistItem
  }
})
