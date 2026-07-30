import { useAuthStore } from "~/stores/auth";

export default defineNuxtRouteMiddleware(async (to, _from) => {
  const authStore = useAuthStore();

  // /setup is a manual fallback — always accessible, no redirect logic
  if (to.path === "/setup") {
    return;
  }

  // Login page: redirect away if already authenticated
  if (to.path === "/login") {
    if (authStore.isAuthenticated) {
      return navigateTo("/");
    }
    return;
  }

  // All other routes: require authentication
  if (!authStore.isAuthenticated) {
    return navigateTo("/login");
  }
});
