import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FinancialEntryForm from './FinancialEntryForm.vue'
import { useFinancialEntriesStore } from '@/stores/financialEntries'

function mountForm(entry = null) {
  setActivePinia(createPinia())
  const store = useFinancialEntriesStore()
  store.createEntry = vi.fn().mockResolvedValue({ id: 1, date: '2026-02-01' })
  store.updateEntry = vi.fn().mockResolvedValue({ id: 1, date: '2026-02-01' })
  store.parseFinancialScreenshot = vi.fn()
  store.uploadEntryScreenshot = vi.fn().mockResolvedValue({ id: 1 })

  const wrapper = mount(FinancialEntryForm, { props: { entry } })
  return { wrapper, store }
}

// The dropzone only listens for real DOM events (paste/drop/change) -- drive
// it that way rather than reaching into <script setup> internals, which
// aren't exposed on wrapper.vm without an explicit defineExpose (matching
// how TradesSection.spec.js also never unit-tests the dropzone's drag/drop
// interaction directly, leaving that to the project's Playwright passes).
async function pasteImage(wrapper, file) {
  await wrapper.find('.screenshot-dropzone').trigger('paste', {
    clipboardData: { items: [{ type: 'image/png', getAsFile: () => file }] }
  })
  await flushPromises()
}

describe('FinancialEntryForm manual entry', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('submits a manual entry with no screenshot interaction at all', async () => {
    const { wrapper, store } = mountForm()

    await wrapper.find('input[placeholder*="Category"]').setValue('Evaluation fee')
    await wrapper.find('input[placeholder="Amount"]').setValue('150')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(store.createEntry).toHaveBeenCalledWith(
      expect.objectContaining({ entry_type: 'expense', category: 'Evaluation fee', amount: 150 })
    )
    expect(store.parseFinancialScreenshot).not.toHaveBeenCalled()
    expect(store.uploadEntryScreenshot).not.toHaveBeenCalled()
  })

  it('toggles entry type to income', async () => {
    const { wrapper, store } = mountForm()
    await wrapper.findAll('.type-toggle-btn').find((b) => b.text() === 'INCOME').trigger('click')
    await wrapper.find('input[placeholder*="Category"]').setValue('Payout')
    await wrapper.find('input[placeholder="Amount"]').setValue('800')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(store.createEntry).toHaveBeenCalledWith(expect.objectContaining({ entry_type: 'income' }))
  })

  it('emits saved after a successful submit', async () => {
    const { wrapper } = mountForm()
    await wrapper.find('input[placeholder*="Category"]').setValue('Payout')
    await wrapper.find('input[placeholder="Amount"]').setValue('100')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.emitted('saved')).toBeTruthy()
  })

  it('shows a submit error and does not emit saved when the API call fails', async () => {
    const { wrapper, store } = mountForm()
    store.createEntry.mockRejectedValue({ response: { data: { detail: 'Bad request' } } })

    await wrapper.find('input[placeholder*="Category"]').setValue('Payout')
    await wrapper.find('input[placeholder="Amount"]').setValue('100')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Bad request')
    expect(wrapper.emitted('saved')).toBeFalsy()
  })
})

describe('FinancialEntryForm screenshot capture', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('extraction only prefills the form, never auto-submits', async () => {
    const { wrapper, store } = mountForm()
    store.parseFinancialScreenshot.mockResolvedValue({
      entry_type: 'income',
      category: 'Payout',
      amount: '500',
      date: '2026-03-01',
      firm: 'TopStep',
      notes: null
    })

    const file = new File(['x'], 'shot.png', { type: 'image/png' })
    await pasteImage(wrapper, file)

    expect(store.parseFinancialScreenshot).toHaveBeenCalledWith(file)
    expect(store.createEntry).not.toHaveBeenCalled()
    expect(wrapper.find('input[placeholder*="Category"]').element.value).toBe('Payout')
    expect(wrapper.find('input[placeholder="Amount"]').element.value).toBe('500')
  })

  it('falls back gracefully when extraction fails, keeping manual entry available', async () => {
    const { wrapper, store } = mountForm()
    store.parseFinancialScreenshot.mockRejectedValue({
      response: { data: { detail: 'Screenshot capture is not configured on this server' } }
    })

    const file = new File(['x'], 'shot.png', { type: 'image/png' })
    await pasteImage(wrapper, file)

    expect(wrapper.text()).toContain('not configured')
    expect(wrapper.find('input[placeholder="Amount"]').attributes('disabled')).toBeUndefined()
  })

  it('auto-attaches the staged screenshot to the entry once created', async () => {
    const { wrapper, store } = mountForm()
    store.parseFinancialScreenshot.mockResolvedValue({ category: 'Payout', amount: '500' })

    const file = new File(['x'], 'shot.png', { type: 'image/png' })
    await pasteImage(wrapper, file)

    await wrapper.find('input[placeholder="Amount"]').setValue('500')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(store.uploadEntryScreenshot).toHaveBeenCalledWith(1, file)
  })
})

describe('FinancialEntryForm edit mode', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('prefills from the entry prop', () => {
    const { wrapper } = mountForm({
      id: 5,
      entry_type: 'income',
      category: 'Payout',
      amount: '250',
      date: '2026-04-01',
      firm: 'FTMO',
      notes: null
    })

    expect(wrapper.find('input[placeholder*="Category"]').element.value).toBe('Payout')
    expect(wrapper.find('input[placeholder="Amount"]').element.value).toBe('250')
    expect(wrapper.find('input[placeholder*="Firm"]').element.value).toBe('FTMO')
  })

  it('calls updateEntry instead of createEntry on submit', async () => {
    const { wrapper, store } = mountForm({
      id: 5,
      entry_type: 'expense',
      category: 'Fee',
      amount: '50',
      date: '2026-04-01',
      firm: null,
      notes: null
    })

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(store.updateEntry).toHaveBeenCalledWith(5, expect.objectContaining({ category: 'Fee' }))
    expect(store.createEntry).not.toHaveBeenCalled()
  })

  it('emits cancel when the Cancel button is clicked', async () => {
    const { wrapper } = mountForm({
      id: 5,
      entry_type: 'expense',
      category: 'Fee',
      amount: '50',
      date: '2026-04-01',
      firm: null,
      notes: null
    })

    await wrapper.find('.toggle-more-button').trigger('click')
    expect(wrapper.emitted('cancel')).toBeTruthy()
  })
})
