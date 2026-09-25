import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Feedback from './Feedback.vue'
import { useFeedbackStore } from '@/stores/feedback'

function mountFeedback() {
  setActivePinia(createPinia())
  const store = useFeedbackStore()
  store.submitFeedback = vi.fn().mockResolvedValue()

  const wrapper = mount(Feedback)
  return { wrapper, store }
}

describe('Feedback', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('disables submit until a message is entered', async () => {
    const { wrapper } = mountFeedback()
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()

    await wrapper.find('textarea').setValue('Something broke')
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })

  it('submits the trimmed message and shows a success state', async () => {
    const { wrapper, store } = mountFeedback()
    await wrapper.find('textarea').setValue('  Love the new chart  ')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(store.submitFeedback).toHaveBeenCalledWith('Love the new chart')
    expect(wrapper.text()).toContain('Thanks -- your feedback was sent.')
    expect(wrapper.find('textarea').element.value).toBe('')
  })

  it('shows an error and keeps the message when submission fails', async () => {
    const { wrapper, store } = mountFeedback()
    store.submitFeedback.mockRejectedValue({ response: { data: { detail: 'Bad request' } } })

    await wrapper.find('textarea').setValue('Testing failure path')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Bad request')
    expect(wrapper.text()).not.toContain('Thanks -- your feedback was sent.')
  })
})
