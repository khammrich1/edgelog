import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { ApiError, onSessionExpired, refreshSession, request, setAccessToken } from "@/api/client";

export interface EdgeLogUser {
  id: string;
  email: string;
  created_at: string;
}

interface AccessTokenResponse {
  access_token: string;
  token_type: string;
  user: EdgeLogUser;
}

export const useAuthStore = defineStore("auth", () => {
  const user = ref<EdgeLogUser | null>(null);
  const initialized = ref(false);

  const isAuthenticated = computed(() => user.value !== null);

  function applySession(data: AccessTokenResponse) {
    setAccessToken(data.access_token);
    user.value = data.user;
  }

  function clearSession() {
    setAccessToken(null);
    user.value = null;
  }

  async function register(email: string, password: string) {
    const data = await request<AccessTokenResponse>("/auth/register", {
      method: "POST",
      body: { email, password },
    });
    applySession(data);
  }

  async function login(email: string, password: string) {
    const data = await request<AccessTokenResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
    });
    applySession(data);
  }

  async function logout() {
    try {
      await request<void>("/auth/logout", { method: "POST" });
    } finally {
      clearSession();
    }
  }

  /** Called on app boot: tries to resume a session from the refresh cookie. */
  async function restoreSession() {
    try {
      const refreshed = await refreshSession();
      if (refreshed) {
        const me = await request<EdgeLogUser>("/auth/me");
        user.value = me;
      }
    } catch (error) {
      if (!(error instanceof ApiError)) {
        throw error;
      }
    } finally {
      initialized.value = true;
    }
  }

  onSessionExpired(() => {
    clearSession();
  });

  return {
    user,
    initialized,
    isAuthenticated,
    register,
    login,
    logout,
    restoreSession,
  };
});
