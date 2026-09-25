import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Admin from './Admin.vue'
import { useAdminStore } from '@/stores/admin'

async function mountAdmin({ roster = [], traffic = [], feedback = [] } = {}) {
  setActivePinia(createPinia())
  const store = useAdminStore()
  store.fetchRoster = vi.fn().mockImplementation(async () => {
    store.roster = roster
  })
  store.fetchTraffic = vi.fn().mockImplementation(async () => {
    store.traffic = traffic
  })
  store.fetchFeedback = vi.fn().mockImplementation(async () => {
    store.feedback = feedback
  })

  const wrapper = mount(Admin)
  await flushPromises()
  return { wrapper, store }
}

describe('Admin', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches all three sections on mount', async () => {
    const { store } = await mountAdmin()
    expect(store.fetchRoster).toHaveBeenCalled()
    expect(store.fetchTraffic).toHaveBeenCalled()
    expect(store.fetchFeedback).toHaveBeenCalled()
  })

  it('renders the account roster with last-activity and admin flag', async () => {
    const { wrapper } = await mountAdmin({
      roster: [
        { id: 1, email: 'admin@example.com', is_admin: true, created_at: '2026-01-01T00:00:00Z', last_activity_at: null, last_activity_path: null },
        { id: 2, email: 'trader@example.com', is_admin: false, created_at: '2026-02-01T00:00:00Z', last_activity_at: '2026-09-24T00:00:00Z', last_activity_path: '/financials' }
      ]
    })

    const rows = wrapper.findAll('.admin-table')[0].findAll('tbody tr')
    expect(rows[0].text()).toContain('admin@example.com')
    expect(rows[0].text()).toContain('Yes')
    expect(rows[0].text()).toContain('No activity yet')
    expect(rows[1].text()).toContain('trader@example.com')
    expect(rows[1].text()).toContain('/financials')
  })

  it('renders the traffic table', async () => {
    const { wrapper } = await mountAdmin({
      traffic: [{ path: '/journal', hits: 42, unique_auth_users: 3, auth_hits: 40, unauth_hits: 2 }]
    })

    const trafficTable = wrapper.findAll('.admin-table')[1]
    expect(trafficTable.text()).toContain('/journal')
    expect(trafficTable.text()).toContain('42')
    expect(trafficTable.text()).toContain('40 / 2')
  })

  it('renders submitted feedback', async () => {
    const { wrapper } = await mountAdmin({
      feedback: [{ id: 1, user_email: 'trader@example.com', message: 'Great app', created_at: '2026-09-24T00:00:00Z' }]
    })

    const feedbackTable = wrapper.findAll('.admin-table')[2]
    expect(feedbackTable.text()).toContain('trader@example.com')
    expect(feedbackTable.text()).toContain('Great app')
  })

  it('shows empty-state hints when there is no data yet', async () => {
    const { wrapper } = await mountAdmin()
    expect(wrapper.text()).toContain('No accounts yet.')
    expect(wrapper.text()).toContain('No traffic recorded yet.')
    expect(wrapper.text()).toContain('No feedback submitted yet.')
  })
})
