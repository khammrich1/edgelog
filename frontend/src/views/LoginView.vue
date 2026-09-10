<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ApiError } from "@/api/client";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const email = ref("");
const password = ref("");
const error = ref<string | null>(null);
const submitting = ref(false);

async function handleSubmit() {
  error.value = null;
  submitting.value = true;
  try {
    await auth.login(email.value, password.value);
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/";
    router.push(redirect);
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="auth-page">
    <form class="auth-card" @submit.prevent="handleSubmit">
      <img src="/edgelog-mark.svg" alt="EdgeLog" width="40" height="40" class="auth-card__mark" />
      <h1 class="auth-card__title">EdgeLog</h1>
      <p class="auth-card__subtitle">Find Your Edge.</p>

      <label class="field">
        <span class="field__label">Email</span>
        <input v-model="email" type="email" required autocomplete="email" />
      </label>

      <label class="field">
        <span class="field__label">Password</span>
        <input v-model="password" type="password" required autocomplete="current-password" />
      </label>

      <p v-if="error" class="auth-card__error">{{ error }}</p>

      <button type="submit" class="button-primary" :disabled="submitting">
        {{ submitting ? "Signing in…" : "Log in" }}
      </button>

      <RouterLink to="/register" class="auth-card__link">Need an account? Register</RouterLink>
    </form>
  </div>
</template>

<style scoped>
@import "@/assets/auth-page.css";
</style>
