import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import BaseInput from './BaseInput.vue'

describe('BaseInput accessibility', () => {
  it('connects each label and validation message to its input', async () => {
    const wrapper = mount(BaseInput, { props: { label: 'Password' }, attrs: { minlength: 8 } })
    const id = wrapper.find('input').attributes('id')
    expect(wrapper.find('label').attributes('for')).toBe(id)
    expect(wrapper.find('input').attributes('minlength')).toBe('8')
    await wrapper.setProps({ error: 'Too short' })
    expect(wrapper.find('input').attributes('id')).toBe(id)
    expect(wrapper.find('input').attributes('aria-invalid')).toBe('true')
    expect(wrapper.find('input').attributes('aria-describedby')).toBe(wrapper.find('[role="alert"]').attributes('id'))
    await wrapper.setProps({ error: '' })
    expect(wrapper.find('input').attributes('aria-invalid')).toBeUndefined()
  })
})
