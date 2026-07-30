import { useAuthStore } from '~/stores/auth'

export default defineNuxtPlugin(async () => {
  const authStore = useAuthStore()
  const config = useRuntimeConfig()
  const baseURL = config.public.apiUrl

  authStore.initFromStorage()

  if (authStore.isAuthenticated && authStore.token) {
    try {
      // Single request: /auth/me validates access token OR falls back to
      // refresh cookie, returning user + optional new_token in one round-trip.
      const response = await $fetch<{ status: string; user: any; new_token?: string }>(`${baseURL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${authStore.token}`
        },
        credentials: 'include'
      })

      if (response.user) {
        authStore.setUser(response.user)
      }
      if (response.new_token) {
        authStore.setToken(response.new_token)
      }
    } catch {
      authStore.logout()
    }
  }
})
