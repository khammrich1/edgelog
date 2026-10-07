import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import Settings from './Settings.vue'
import { useTradesStore } from '@/stores/trades'

function setup() {
  setActivePinia(createPinia())
  const store = useTradesStore()
  store.fetchSetups = vi.fn().mockResolvedValue([])
  store.createSetup = vi.fn().mockResolvedValue({})
  store.deleteSetup = vi.fn().mockResolvedValue()
  return store
}

describe('Settings request recovery', () => {
  it('distinguishes failed loading from an empty list and supports retry', async () => {
    const store = setup()
    store.fetchSetups.mockRejectedValueOnce(new Error('offline'))
    const wrapper = mount(Settings)
    expect(wrapper.text()).toContain('Loading your setups')
    await flushPromises()
    expect(wrapper.text()).toContain('Could not load your setups')
    expect(wrapper.text()).not.toContain('No setups configured')
    await wrapper.find('.retry-button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('No setups configured')
  })

  it('preserves input after a failed save and allows another attempt', async () => {
    const store = setup()
    store.createSetup.mockRejectedValueOnce(new Error('offline'))
    const wrapper = mount(Settings)
    await flushPromises()
    await wrapper.find('input').setValue('Breakout')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Could not add')
    expect(wrapper.find('input').element.value).toBe('Breakout')
    expect(wrapper.find('button[type="submit"]').element.disabled).toBe(false)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('input').element.value).toBe('')
  })

  it('keeps the setup visible when deletion fails', async () => {
    const store = setup()
    store.setups = [{ id: 1, name: 'Reversal' }]
    store.deleteSetup.mockRejectedValue(new Error('offline'))
    const wrapper = mount(Settings)
    await flushPromises()
    await wrapper.find('[aria-label="Remove Reversal"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Could not remove')
    expect(wrapper.find('.setup-name').text()).toBe('Reversal')
  })
})
