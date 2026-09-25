import { defineStore } from 'pinia'
import api from '@/services/api'

export const useFeedbackStore = defineStore('feedback', () => {
  async function submitFeedback(message) {
    await api.post('/feedback', { message })
  }

  return {
    submitFeedback
  }
})
