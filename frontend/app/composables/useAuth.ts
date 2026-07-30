import { useAuthStore, type User } from '~/stores/auth'
import { useCacheStore } from '~/stores/cache'
import { resetApiFetch } from '~/composables/useApiFetch'
import { useBootInfo } from '~/composables/useBootInfo'

export const useAuth = () => {
  const authStore = useAuthStore()
  const cacheStore = useCacheStore()
  const { boot } = useBootInfo()

  const authState = computed(() => ({
    user: authStore.user,
    token: authStore.token,
    refreshToken: authStore.refreshToken,
    isAuthenticated: authStore.isAuthenticated
  }))

  const login = async (username: string, password: string) => {
    try {
      const result = await boot(username, password)

      if (result.success) {
        // Boot API now returns all necessary data (sidebar, workflow_states, branding_settings, allowed_dashboards)
        // No need for separate prefetch calls
        return { success: true }
      }
      return { success: false, message: result.message || 'Invalid credentials' }
    } catch (error: any) {
      return {
        success: false,
        message: error.data?.detail || 'Login failed'
      }
    }
  }

  const logout = () => {
    cacheStore.clear()
    resetApiFetch()
    authStore.logout()
    if (import.meta.client) {
      navigateTo('/login')
    }
  }

  return {
    authState,
    authStore,
    login,
    logout
  }
}
