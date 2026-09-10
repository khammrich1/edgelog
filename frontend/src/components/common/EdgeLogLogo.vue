<template>
  <div class="edgelog-logo">
    <img src="/edgelog-mark.svg" alt="EdgeLog" class="logo-mark" />
    <span class="logo-wordmark">
      <span class="logo-edge">Edge</span><span class="logo-log">Log</span>
    </span>
  </div>
</template>

<style scoped>
.edgelog-logo {
  display: flex;
  align-items: center;
  gap: var(--el-space-3);
}

.logo-mark {
  width: 32px;
  height: 32px;
}

.logo-wordmark {
  font-size: var(--el-text-xl);
  font-weight: 600;
  letter-spacing: -0.02em;
}

.logo-edge {
  color: var(--el-copper);
}

.logo-log {
  color: var(--el-text);
}
</style>
