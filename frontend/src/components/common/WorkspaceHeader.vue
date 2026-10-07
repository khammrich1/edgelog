<script setup>
defineProps({ title: { type: String, required: true }, eyebrow: String, description: String })
</script>

<template>
  <header class="el-page-header">
    <div class="el-page-heading">
      <p v-if="eyebrow" class="el-label el-page-eyebrow">{{ eyebrow }}</p>
      <div class="el-page-title-row"><h1>{{ title }}</h1><slot name="status" /></div>
      <p v-if="description" class="el-page-description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="el-page-actions"><slot name="actions" /></div>
  </header>
</template>

<style scoped>
.el-page-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px; padding-bottom: 24px; margin-bottom: 24px; border-bottom: 1px solid var(--el-border); }
.el-page-heading { min-width: 0; }
.el-page-eyebrow { margin-bottom: 8px; letter-spacing: .08em; font-size: 11px; }
.el-page-title-row { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }
h1 { font-size: clamp(22px, 2.2vw, 26px); line-height: 1.3; letter-spacing: -.025em; overflow-wrap: anywhere; }
.el-page-description { margin-top: 10px; max-width: 65ch; color: var(--el-text-muted); font-size: 14px; }
.el-page-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; min-width: 0; }
@media (max-width: 640px) { .el-page-header { gap: 16px; padding-bottom: 20px; margin-bottom: 20px; } }
</style>
