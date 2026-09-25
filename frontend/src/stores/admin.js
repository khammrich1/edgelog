import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useAdminStore = defineStore('admin', () => {
  const roster = ref([])
  const traffic = ref([])
  const feedback = ref([])

  async function fetchRoster() {
    const { data } = await api.get('/admin/roster')
    roster.value = data
    return data
  }

  async function fetchTraffic() {
    const { data } = await api.get('/admin/traffic')
    traffic.value = data
    return data
  }

  async function fetchFeedback() {
    const { data } = await api.get('/admin/feedback')
    feedback.value = data
    return data
  }

  return {
    roster,
    traffic,
    feedback,
    fetchRoster,
    fetchTraffic,
    fetchFeedback
  }
})
