<template>
  <div class="stats-page">
    <header><p class="el-label">Performance</p><h1>Stats</h1></header>
    <section class="stats-placeholder">
      <h2>Edge analytics are on the way.</h2>
      <p>Win rate, expectancy, and per-setup performance will live here once enough trades are logged.</p>
      <router-link to="/trades">Review trade history</router-link>
    </section>
  </div>
</template>

<style scoped>
.stats-page { max-width: 1160px; margin: auto; padding: 32px 48px; }
h1 { font-size: 26px; margin: 8px 0 24px; }
.stats-placeholder { border-top: 1px solid var(--el-border); padding: 24px 0; }
h2 { font-size: 18px; margin-bottom: 12px; }
p { color: var(--el-text-muted); font-size: 14px; max-width: 560px; }
a { display: inline-block; margin-top: 20px; font-size: 14px; }
@media(max-width: 640px) { .stats-page { padding: 20px 16px; } }
</style>
