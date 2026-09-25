import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useFeedbackStore } from './feedback'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: { post: vi.fn() }
}))

describe('feedback store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('submitFeedback posts the message', async () => {
    api.post.mockResolvedValue({})
    const store = useFeedbackStore()

    await store.submitFeedback('Love the app')

    expect(api.post).toHaveBeenCalledWith('/feedback', { message: 'Love the app' })
  })
})
