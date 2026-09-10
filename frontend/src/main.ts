import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "@/App.vue";
import "@/assets/tokens.css";
import { router } from "@/router";
import { useAuthStore } from "@/stores/auth";

const app = createApp(App);

app.use(createPinia());
app.use(router);

const authStore = useAuthStore();
authStore
  .restoreSession()
  .catch(() => {
    /* no active session on load; user will see the login view */
  })
  .finally(() => {
    app.mount("#app");
  });
