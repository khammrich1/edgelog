import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

// Thin read access to the broker-accounts registry (issue #95) for the
// Plan form's account picker. Registering/deleting accounts has its own
// settings-page UI elsewhere -- this store only lists them.
export const useBrokerAccountsStore = defineStore('brokerAccounts', () => {
  const accounts = ref([])

  async function fetchAccounts() {
    const { data } = await api.get('/broker-accounts')
    accounts.value = data
    return data
  }

  async function createAccount(payload) {
    const { data } = await api.post('/broker-accounts', payload)
    accounts.value = [...accounts.value, data]
    return data
  }

  return { accounts, fetchAccounts, createAccount }
})
