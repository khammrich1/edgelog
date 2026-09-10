<template>
  <div class="auth-page">
    <div class="auth-container">
      <EdgeLogLogo class="auth-logo" />

      <div class="auth-card">
        <h1>Welcome back</h1>
        <p class="auth-subtitle">Sign in to your trading journal</p>

        <form @submit.prevent="handleLogin" class="auth-form">
          <BaseInput
            v-model="email"
            label="Email"
            type="email"
            placeholder="your@email.com"
            autocomplete="email"
            required
            :error="errors.email"
          />

          <BaseInput
            v-model="password"
            label="Password"
            type="password"
            placeholder="••••••••"
            autocomplete="current-password"
            required
            :error="errors.password"
          />

          <BaseButton
            type="submit"
            variant="primary"
            :disabled="authStore.loading"
            class="auth-submit"
          >
            {{ authStore.loading ? 'Signing in...' : 'Sign In' }}
          </BaseButton>

          <p v-if="errors.general" class="auth-error">{{ errors.general }}</p>
        </form>

        <p class="auth-footer">
          Don't have an account?
          <router-link to="/register">Create one free</router-link>
        </p>
      </div>

      <p class="auth-tagline">Find Your Edge.</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import EdgeLogLogo from '@/components/common/EdgeLogLogo.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseButton from '@/components/common/BaseButton.vue'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const errors = ref({})

async function handleLogin() {
  errors.value = {}

  const result = await authStore.login(email.value, password.value)

  if (result.success) {
    router.push('/journal')
  } else {
    errors.value.general = result.error
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--el-space-4);
  background-color: var(--el-bg);
}

.auth-container {
  width: 100%;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  gap: var(--el-space-8);
}

.auth-logo {
  justify-content: center;
}

.auth-card {
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-lg);
  padding: var(--el-space-8);
  display: flex;
  flex-direction: column;
  gap: var(--el-space-6);
}

.auth-card h1 {
  font-size: var(--el-text-2xl);
  text-align: center;
}

.auth-subtitle {
  text-align: center;
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  margin-top: calc(var(--el-space-2) * -1);
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: var(--el-space-4);
}

.auth-submit {
  margin-top: var(--el-space-2);
}

.auth-error {
  text-align: center;
  color: var(--el-negative);
  font-size: var(--el-text-sm);
}

.auth-footer {
  text-align: center;
  font-size: var(--el-text-sm);
  color: var(--el-text-muted);
}

.auth-tagline {
  text-align: center;
  font-size: var(--el-text-sm);
  color: var(--el-steel);
  font-weight: 500;
  letter-spacing: 0.05em;
}
</style>
