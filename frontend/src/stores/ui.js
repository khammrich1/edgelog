import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  // State
  const toast = ref(null)

  // Actions
  function showToast(message, type = 'info', duration = 3000) {
    toast.value = { message, type }
    setTimeout(() => {
      toast.value = null
    }, duration)
  }

  return {
    toast,
    showToast
  }
})
