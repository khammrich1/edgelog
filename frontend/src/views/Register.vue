<template>
  <div class="auth-page">
    <div class="auth-container">
      <EdgeLogLogo class="auth-logo" />

      <div class="auth-card">
        <h1>Create your account</h1>
        <p class="auth-subtitle">Start finding your edge today</p>

        <form @submit.prevent="handleRegister" class="auth-form">
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
            autocomplete="new-password"
            required
            :error="errors.password"
          />

          <BaseButton
            type="submit"
            variant="primary"
            :disabled="authStore.loading"
            class="auth-submit"
          >
            {{ authStore.loading ? 'Creating account...' : 'Create Account' }}
          </BaseButton>

          <p v-if="errors.general" class="auth-error">{{ errors.general }}</p>
        </form>

        <p class="auth-footer">
          Already have an account?
          <router-link to="/login">Sign in</router-link>
        </p>
      </div>

      <p class="auth-tagline">Trade. Reflect. Improve.</p>
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

async function handleRegister() {
  errors.value = {}

  // Basic validation
  if (password.value.length < 8) {
    errors.value.password = 'Password must be at least 8 characters'
    return
  }

  const result = await authStore.register(email.value, password.value)

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
