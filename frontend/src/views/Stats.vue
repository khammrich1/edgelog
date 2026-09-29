<template>
  <div class="stats-page">
    <h1>Stats</h1>
    <div class="el-empty-state stats-placeholder">
      <p class="stats-placeholder-title">Edge analytics are on the way.</p>
      <p>Win rate, expectancy, and per-setup performance will live here once enough trades are logged.</p>
    </div>
  </div>
</template>

<style scoped>
.stats-page {
  padding: var(--el-space-8);
  max-width: 640px;
  margin: 0 auto;
}

.stats-page h1 {
  font-size: var(--el-text-xl);
  margin: 0 0 var(--el-space-3);
}

.stats-placeholder {
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-lg);
  background-color: var(--el-surface);
}

.stats-placeholder-title {
  color: var(--el-text);
  font-weight: 500;
  margin-bottom: var(--el-space-1);
}
</style>
