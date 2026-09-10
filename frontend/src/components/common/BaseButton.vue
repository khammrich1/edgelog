<template>
  <button
    :class="['base-button', `base-button--${variant}`]"
    :type="type"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<script setup>
defineProps({
  variant: {
    type: String,
    default: 'primary', // primary, secondary, ghost
    validator: (value) => ['primary', 'secondary', 'ghost'].includes(value)
  },
  type: {
    type: String,
    default: 'button'
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

defineEmits(['click'])
</script>

<style scoped>
.base-button {
  padding: var(--el-space-3) var(--el-space-6);
  border-radius: var(--el-radius-md);
  font-weight: 500;
  font-size: var(--el-text-base);
  transition: all var(--el-transition-fast);
  cursor: pointer;
  border: none;
}

.base-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Primary - Copper */
.base-button--primary {
  background-color: var(--el-copper);
  color: var(--el-bg);
}

.base-button--primary:hover:not(:disabled) {
  background-color: var(--el-copper-hover);
}

.base-button--primary:active:not(:disabled) {
  background-color: var(--el-copper-active);
}

/* Secondary - Steel outline */
.base-button--secondary {
  background-color: transparent;
  color: var(--el-text);
  border: 1px solid var(--el-steel);
}

.base-button--secondary:hover:not(:disabled) {
  background-color: var(--el-surface);
  border-color: var(--el-steel-light);
}

/* Ghost - Minimal */
.base-button--ghost {
  background-color: transparent;
  color: var(--el-text-muted);
}

.base-button--ghost:hover:not(:disabled) {
  color: var(--el-text);
  background-color: var(--el-surface);
}
</style>
