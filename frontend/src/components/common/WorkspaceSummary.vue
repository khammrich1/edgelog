<script setup>
defineProps({ label: { type: String, required: true }, items: { type: Array, required: true } })
</script>

<template>
  <dl class="workspace-summary" :aria-label="label">
    <div v-for="item in items" :key="item.label" class="summary-item">
      <dt class="el-label">{{ item.label }}</dt>
      <dd>{{ item.value }}</dd>
    </div>
  </dl>
</template>

<style scoped>
.workspace-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); margin-bottom: 24px; background: var(--el-surface-sunken); border-block: 1px solid var(--el-border); }
.summary-item { padding: 16px 20px; min-width: 0; }
.summary-item + .summary-item { border-left: 1px solid var(--el-divider); }
dt { font-size: 10px; letter-spacing: .06em; }
dd { margin-top: 6px; font-size: 22px; font-weight: 600; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
@media (max-width: 640px) {
  .workspace-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .summary-item { padding: 12px 16px; }
  .summary-item:nth-child(odd) { border-left: none; }
  .summary-item:nth-child(n+3) { border-top: 1px solid var(--el-divider); }
  dd { font-size: 20px; }
}
</style>
