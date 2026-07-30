/**
 * Silent Token Refresh
 * ====================
 * Proactively refreshes the access token before it expires.
 * Reads the exp claim from the JWT and schedules a refresh
 * 60 seconds before expiry. This prevents the user from ever
 * hitting a 401 mid-work unless the refresh token itself expires.
 */
import { useAuthStore } from '~/stores/auth'

let _refreshTimer: ReturnType<typeof setTimeout> | null = null

const parseJwtExp = (token: string): number | null => {
  try {
    const part = token.split('.')[1]
    if (!part) return null
    const payload = JSON.parse(atob(part))
    return typeof payload.exp === 'number' ? payload.exp : null
  } catch {
    return null
  }
}

export const useTokenRefresh = () => {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiUrl as string
  const authStore = useAuthStore()

  const cancelRefresh = () => {
    if (_refreshTimer !== null) {
      clearTimeout(_refreshTimer)
      _refreshTimer = null
    }
  }

  const scheduleRefresh = (token: string) => {
    cancelRefresh()

    const exp = parseJwtExp(token)
    if (!exp) return

    const nowMs = Date.now()
    const expMs = exp * 1000
    // Refresh 60 seconds before expiry, minimum 5 seconds from now
    const delayMs = Math.max(expMs - nowMs - 60_000, 5_000)

    _refreshTimer = setTimeout(async () => {
      try {
        const refreshed = await $fetch<{ access_token: string; token_type: string }>(
          `${baseURL}/auth/refresh`,
          { method: 'POST', credentials: 'include' }
        )
        authStore.setToken(refreshed.access_token)
        // Schedule the next refresh using the new token
        scheduleRefresh(refreshed.access_token)
      } catch {
        // Refresh token also expired — log out cleanly
        authStore.logout()
        if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }
    }, delayMs)
  }

  return { scheduleRefresh, cancelRefresh }
}
