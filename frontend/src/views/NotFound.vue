<template>
  <div class="not-found-view">
    <div class="not-found-content">
      <p class="not-found-code">404</p>
      <h1>Page not found.</h1>
      <p class="not-found-message">The EdgeLog page you're looking for doesn't exist.</p>
      <RouterLink to="/journal" class="back-link">Back to Journal</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.not-found-view {
  min-height: calc(100vh - 64px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--el-space-8);
}

.not-found-content {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--el-space-2);
  max-width: 400px;
}

.not-found-code {
  font-family: var(--el-font-mono);
  font-size: var(--el-text-sm);
  color: var(--el-steel-light);
  letter-spacing: 0.1em;
  margin: 0 0 var(--el-space-2);
}

.not-found-content h1 {
  font-size: var(--el-text-2xl);
  color: var(--el-text);
  margin: 0;
}

.not-found-message {
  color: var(--el-text-muted);
  font-size: var(--el-text-base);
  margin: 0 0 var(--el-space-6);
}

.back-link {
  padding: var(--el-space-2) var(--el-space-6);
  background-color: transparent;
  color: var(--el-copper);
  border: 1px solid var(--el-copper);
  border-radius: var(--el-radius-sm);
  font-size: var(--el-text-sm);
  font-weight: 500;
  text-decoration: none;
  transition: all var(--el-transition-fast);
}

.back-link:hover {
  background-color: var(--el-copper);
  color: var(--el-bg);
}
</style>
