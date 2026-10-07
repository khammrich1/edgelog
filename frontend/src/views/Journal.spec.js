import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Journal from './Journal.vue'
import { useJournalStore } from '@/stores/journal'

const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

function setup() {
  setActivePinia(createPinia())
  const store = useJournalStore()
  store.fetchDaysInRange = vi.fn().mockResolvedValue([])
  return store
}

describe('Journal calendar context', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 9, 7))
    push.mockClear()
  })
  afterEach(() => vi.useRealTimers())

  it('counts recorded journals in the displayed month without treating blank dates as misses', async () => {
    const store = setup()
    store.daysByDate = {
      '2026-10-05': { status: 'locked', has_bias_chart: true },
      '2026-10-07': { status: 'draft', checklist_total_count: 3, checklist_completed_count: 1 },
      '2026-09-30': { status: 'draft' }
    }
    const wrapper = mount(Journal)
    await flushPromises()
    const counts = Object.fromEntries(wrapper.findAll('.summary-item').map(item => [item.find('dt').text(), item.find('dd').text()]))
    expect(counts).toEqual({ 'Journal days': '2', Draft: '1', Locked: '1', 'With bias chart': '1' })
    expect(wrapper.text()).toContain('Fractions show checklist progress')
    expect(wrapper.text()).toContain('It does not indicate a missed trading day')
    expect(wrapper.find('.day-cell--today').attributes('aria-current')).toBe('date')
    expect(wrapper.findAll('.day-cell').length % 7).toBe(0)
    await wrapper.find('.el-btn-primary').trigger('click')
    expect(push).toHaveBeenCalledWith('/journal/2026-10-07')
  })

  it('shows failed loading instead of an empty summary and retries', async () => {
    const store = setup()
    store.fetchDaysInRange.mockRejectedValueOnce(new Error('offline'))
    const wrapper = mount(Journal)
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Could not load')
    expect(wrapper.find('.workspace-summary').exists()).toBe(false)
    await wrapper.find('.btn-chip').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(wrapper.find('.workspace-summary').exists()).toBe(true)
  })
})
