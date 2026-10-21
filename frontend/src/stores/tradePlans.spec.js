import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useTradePlansStore } from './tradePlans'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }
}))

describe('tradePlans store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('fetchPlans replaces the flat list', async () => {
    const plan = { id: 1, status: 'pending' }
    api.get.mockResolvedValue({ data: [plan] })
    const store = useTradePlansStore()

    await store.fetchPlans()

    expect(api.get).toHaveBeenCalledWith('/trade-plans')
    expect(store.plans).toEqual([plan])
  })

  it('createPlan posts the payload and prepends the result', async () => {
    const payload = { symbol: 'MNQ' }
    const created = { id: 1, symbol: 'MNQ', status: 'pending' }
    api.post.mockResolvedValue({ data: created })
    const store = useTradePlansStore()

    const result = await store.createPlan(payload)

    expect(api.post).toHaveBeenCalledWith('/trade-plans', payload)
    expect(result).toEqual(created)
    expect(store.plans).toEqual([created])
  })

  it('approvePlan sends decision_note and replaces the plan in place', async () => {
    const store = useTradePlansStore()
    store.plans = [{ id: 1, status: 'pending' }]
    const approved = { id: 1, status: 'approved' }
    api.post.mockResolvedValue({ data: approved })

    await store.approvePlan(1, 'looks good')

    expect(api.post).toHaveBeenCalledWith('/trade-plans/1/approve', { decision_note: 'looks good' })
    expect(store.plans).toEqual([approved])
  })

  it('approvePlan sends null when no decision note is given', async () => {
    const store = useTradePlansStore()
    api.post.mockResolvedValue({ data: { id: 1, status: 'approved' } })

    await store.approvePlan(1)

    expect(api.post).toHaveBeenCalledWith('/trade-plans/1/approve', { decision_note: null })
  })

  it('revisePlan posts to the revise endpoint and refetches the list', async () => {
    const store = useTradePlansStore()
    const revised = { id: 2, status: 'pending', revision_number: 2 }
    api.post.mockResolvedValue({ data: revised })
    api.get.mockResolvedValue({ data: [revised] })

    const result = await store.revisePlan(1, { symbol: 'MNQ' })

    expect(api.post).toHaveBeenCalledWith('/trade-plans/1/revise', { symbol: 'MNQ' })
    expect(api.get).toHaveBeenCalledWith('/trade-plans')
    expect(result).toEqual(revised)
    expect(store.plans).toEqual([revised])
  })
})
