<template>
  <div class="edgelog-logo">
    <img src="/edgelog-mark.svg" alt="" aria-hidden="true" class="logo-mark" />
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
  font-family: var(--el-font-heading);
  font-size: 22px;
  font-weight: 650;
  letter-spacing: -0.02em;
}

.logo-edge {
  color: var(--el-copper);
}

.logo-log {
  color: var(--el-text);
}
</style>
