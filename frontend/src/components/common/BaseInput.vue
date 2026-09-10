<template>
  <div class="base-input-wrapper">
    <label v-if="label" :for="id" class="base-input-label">
      {{ label }}
    </label>
    <input
      :id="id"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :required="required"
      :disabled="disabled"
      :autocomplete="autocomplete"
      class="base-input"
      :class="{ 'base-input--error': error }"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <p v-if="error" class="base-input-error">{{ error }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: String,
  label: String,
  type: {
    type: String,
    default: 'text'
  },
  placeholder: String,
  required: Boolean,
  disabled: Boolean,
  error: String,
  autocomplete: String
})

defineEmits(['update:modelValue'])

const id = computed(() => {
  return `input-${Math.random().toString(36).substr(2, 9)}`
})
</script>

<style scoped>
.base-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--el-space-2);
}

.base-input-label {
  font-size: var(--el-text-sm);
  font-weight: 500;
  color: var(--el-text);
}

.base-input {
  padding: var(--el-space-3) var(--el-space-4);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-md);
  color: var(--el-text);
  font-size: var(--el-text-base);
  transition: border-color var(--el-transition-fast);
}

.base-input::placeholder {
  color: var(--el-text-subtle);
}

.base-input:hover:not(:disabled) {
  border-color: var(--el-steel);
}

.base-input:focus {
  border-color: var(--el-copper);
  outline: none;
}

.base-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.base-input--error {
  border-color: var(--el-negative);
}

.base-input-error {
  font-size: var(--el-text-sm);
  color: var(--el-negative);
}
</style>
