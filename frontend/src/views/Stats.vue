<script setup>
import WorkspaceHeader from '@/components/common/WorkspaceHeader.vue'
</script>
<template>
  <div class="stats-page el-page">
    <WorkspaceHeader title="Stats" eyebrow="Performance" />
    <section class="stats-placeholder">
      <span class="el-badge el-badge--neutral">Planned feature</span>
      <h2>Build the journal behind your edge.</h2>
      <p>Analytics are not available yet. Keep recording your setups, execution, and reflections so you have a useful history to review.</p>
      <router-link to="/trades">Review trade history</router-link>
    </section>
  </div>
</template>

<style scoped>
h1 { font-size: 26px; margin: 8px 0 24px; }
.stats-placeholder { border-top: 1px solid var(--el-border); padding: 24px 0; }
h2 { font-size: 18px; margin: 16px 0 12px; }
p { color: var(--el-text-muted); font-size: 14px; max-width: 560px; }
a { display: inline-block; margin-top: 20px; font-size: 14px; }
@media(max-width: 640px) { .stats-page { padding: 20px 16px; } }
</style>
