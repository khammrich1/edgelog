<template>
  <div class="journal-view">
    <div class="journal-empty-state">
      <img src="/edgelog-mark.svg" alt="EdgeLog" class="empty-logo" />
      <h1>EdgeLog</h1>
      <p class="empty-tagline">Find Your Edge.</p>
      <p class="empty-message">Your journal starts here.</p>
    </div>
  </div>
</template>

<style scoped>
.journal-view {
  min-height: calc(100vh - 64px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--el-space-8);
}

.journal-empty-state {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--el-space-4);
  max-width: 500px;
}

.empty-logo {
  width: 80px;
  height: 80px;
  opacity: 0.6;
}

.journal-empty-state h1 {
  font-size: var(--el-text-3xl);
  margin-top: var(--el-space-2);
}

.empty-tagline {
  font-size: var(--el-text-lg);
  color: var(--el-copper);
  font-weight: 500;
  letter-spacing: 0.05em;
}

.empty-message {
  color: var(--el-text-muted);
  font-size: var(--el-text-base);
  margin-top: var(--el-space-4);
}
</style>
