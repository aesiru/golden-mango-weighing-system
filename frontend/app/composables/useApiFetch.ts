/**
 * API Fetch Factory
 * =================
 * Provides the authenticated $fetch instance with token refresh logic.
 * All domain API composables use this as their base.
 */
import { $fetch } from 'ofetch'
import { useAuthStore } from '~/stores/auth'

let _apiFetch: ReturnType<typeof $fetch.create> | null = null
let _baseURL: string = ''
let _refreshPromise: Promise<string> | null = null

export const resetApiFetch = () => {
  _apiFetch = null
  _refreshPromise = null
}

export const useApiFetch = () => {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiUrl as string
  const isClient = typeof window !== 'undefined'
  const authStore = useAuthStore()

  _baseURL = baseURL

  if (!_apiFetch) {
    _apiFetch = $fetch.create({
      baseURL: baseURL,
      credentials: 'include',
      onRequest({ options }) {
        if (isClient) {
          const token = localStorage.getItem('auth_token')
          if (token) {
            const headers = new Headers(options.headers)
            headers.set('Authorization', `Bearer ${token}`)
            options.headers = headers
          }
        }
      },

      async onResponseError({ request, options, response }) {
        if (!isClient) throw response._data

        const status = response.status
        if (status !== 401 && status !== 403) throw response._data

        const alreadyRetried = (options as any)._authRetried === true
        if (alreadyRetried) {
          // If we already retried and still got 403, treat as real permission denial
          if (status === 403) {
            const data = response._data
            if (typeof sessionStorage !== 'undefined') {
              sessionStorage.setItem('forbidden_message', data?.message || 'Permission denied')
            }
            if (window.location.pathname !== '/forbidden') {
              window.location.href = '/forbidden'
            }
          }
          // If 401 after retry, both tokens are expired — go to login
          if (status === 401) {
            authStore.logout()
            if (window.location.pathname !== '/login') {
              window.location.href = '/login'
            }
          }
          throw response._data
        }

        const refreshAccessToken = async (): Promise<string> => {
          if (!_refreshPromise) {
            _refreshPromise = (async () => {
              try {
                const refreshed = await $fetch<{ access_token: string; token_type: string }>(`${baseURL}/auth/refresh`, {
                  method: 'POST',
                  credentials: 'include'
                })
                authStore.setToken(refreshed.access_token)
                return refreshed.access_token
              } catch {
                // Refresh failed — both tokens expired, redirect to login silently
                authStore.logout()
                if (window.location.pathname !== '/login') {
                  window.location.href = '/login'
                }
                throw new Error('Session expired')
              }
            })().finally(() => {
              _refreshPromise = null
            })
          }
          return _refreshPromise
        }

        const newToken = await refreshAccessToken()

        const retryOptions: any = { ...options, _authRetried: true }
        const headers = new Headers(retryOptions.headers)
        headers.set('Authorization', `Bearer ${newToken}`)
        retryOptions.headers = headers

        return _apiFetch!(request, retryOptions)
      }
    })
  }

  return { apiFetch: _apiFetch, baseURL }
}
