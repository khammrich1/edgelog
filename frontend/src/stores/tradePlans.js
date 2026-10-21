import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

// Pre-trade plans (issue #59): independent of tradesByDate/TradingDay --
// plans aren't scoped to a calendar day, so this store holds one flat list
// rather than mirroring trades.js's date-keyed map.
export const useTradePlansStore = defineStore('tradePlans', () => {
  const plans = ref([])

  function _replace(plan) {
    const existing = plans.value.findIndex((p) => p.id === plan.id)
    if (existing === -1) {
      plans.value = [plan, ...plans.value]
    } else {
      plans.value = plans.value.map((p) => (p.id === plan.id ? plan : p))
    }
  }

  async function fetchPlans() {
    const { data } = await api.get('/trade-plans')
    plans.value = data
    return data
  }

  async function createPlan(payload) {
    const { data } = await api.post('/trade-plans', payload)
    _replace(data)
    return data
  }

  async function approvePlan(planId, decisionNote) {
    const { data } = await api.post(`/trade-plans/${planId}/approve`, { decision_note: decisionNote || null })
    _replace(data)
    return data
  }

  async function rejectPlan(planId, decisionNote) {
    const { data } = await api.post(`/trade-plans/${planId}/reject`, { decision_note: decisionNote || null })
    _replace(data)
    return data
  }

  async function invalidatePlan(planId, decisionNote) {
    const { data } = await api.post(`/trade-plans/${planId}/invalidate`, { decision_note: decisionNote || null })
    _replace(data)
    return data
  }

  async function cancelPlan(planId, decisionNote) {
    const { data } = await api.post(`/trade-plans/${planId}/cancel`, { decision_note: decisionNote || null })
    _replace(data)
    return data
  }

  async function revisePlan(planId, payload) {
    const { data } = await api.post(`/trade-plans/${planId}/revise`, payload)
    // The revised plan is a new row; the one it supersedes stays in the
    // list too (fetchPlans with include_superseded would show it) but its
    // is_latest_revision flips server-side -- refetch to stay accurate.
    await fetchPlans()
    return data
  }

  return { plans, fetchPlans, createPlan, approvePlan, rejectPlan, invalidatePlan, cancelPlan, revisePlan }
})
