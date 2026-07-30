import { defineStore } from 'pinia'
import { useCacheStore } from './cache'

export interface User {
  id: string
  username: string
  email?: string
  full_name?: string
  is_superuser?: boolean
  roles?: string[]
}

export interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
}

const STORAGE_KEYS = {
  TOKEN: 'auth_token',
  REFRESH_TOKEN: 'refresh_token',
  USER: 'auth_user'
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    token: null,
    refreshToken: null,
    isAuthenticated: false
  }),

  getters: {
    isSuperuser: (state) => state.user?.is_superuser ?? false,
    userRoles: (state) => state.user?.roles ?? [],
    displayName: (state) => state.user?.full_name || state.user?.username || 'User'
  },

  actions: {
    initFromStorage() {
      if (typeof window === 'undefined') return

      const token = localStorage.getItem(STORAGE_KEYS.TOKEN)
      const refreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN)
      const userJson = localStorage.getItem(STORAGE_KEYS.USER)

      if (token) {
        this.token = token
        this.refreshToken = refreshToken
        this.isAuthenticated = true

        if (userJson) {
          try {
            this.user = JSON.parse(userJson)
          } catch {
            this.user = null
          }
        }
      }
    },

    setAuth(payload: { token: string; refreshToken?: string | null; user: User }) {
      this.token = payload.token
      this.refreshToken = payload.refreshToken ?? this.refreshToken
      this.user = payload.user
      this.isAuthenticated = true

      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEYS.TOKEN, payload.token)
        if (payload.refreshToken) {
          localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, payload.refreshToken)
        }
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(payload.user))
      }
    },

    setToken(token: string) {
      this.token = token
      this.isAuthenticated = true
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEYS.TOKEN, token)
      }
    },

    setUser(user: User) {
      this.user = user
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user))
      }
    },

    logout() {
      this.user = null
      this.token = null
      this.refreshToken = null
      this.isAuthenticated = false

      // Clear in-memory cache (prevents stale data on same-session re-login)
      if (typeof window !== 'undefined') {
        const cache = useCacheStore()
        cache.$reset()
      }

      if (typeof window !== 'undefined') {
        // Auth tokens
        localStorage.removeItem(STORAGE_KEYS.TOKEN)
        localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN)
        localStorage.removeItem(STORAGE_KEYS.USER)

        // Boot info
        localStorage.removeItem('boot_info')

        // Linked titles cache
        localStorage.removeItem('linked_titles_cache')

        // Notification center
        localStorage.removeItem('eam_notifications')

        // Clear metadata/cache entries
        const keysToRemove: string[] = []
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i)
          if (key && (
            key.startsWith('meta:') ||
            key.startsWith('entity:') ||
            key.startsWith('model-editor:') ||
            key.startsWith('eam_') ||
            key.startsWith('eam_columns_') ||
            key.startsWith('eam_filters_')
          )) {
            keysToRemove.push(key)
          }
        }
        keysToRemove.forEach(k => localStorage.removeItem(k))

        // Session storage
        sessionStorage.removeItem('forbidden_message')
      }
    }
  }
})
