import { defineStore } from 'pinia'

type CacheKey = string

interface CacheEntry<T = unknown> {
  value: T
  expiresAt: number
}

const META_ENTITY_PREFIX = 'meta:entity:v2:'
const USER_META_REGEX = /^user:[^:]+:meta:entity:v2:(.+)$/

const toLocalStorageKey = (key: CacheKey): string => {
  // Handle user-prefixed meta keys: user:{userId}:meta:entity:v2:{entity}
  const userMetaMatch = key.match(USER_META_REGEX)
  if (userMetaMatch) {
    const entity = userMetaMatch[1]
    return `eam_${entity}`
  }
  // Legacy format: meta:entity:v2:{entity}
  if (key.startsWith(META_ENTITY_PREFIX)) {
    const entity = key.slice(META_ENTITY_PREFIX.length)
    return `eam_${entity}`
  }
  return key
}

// Helper to safely access localStorage
const getLocalStorage = (): Storage | null => {
  if (typeof window !== 'undefined' && window.localStorage) {
    return window.localStorage
  }
  return null
}

export const useCacheStore = defineStore('cache', {
  state: () => ({
    entries: {} as Record<CacheKey, CacheEntry>
  }),

  actions: {
    get<T = unknown>(key: CacheKey): T | null {
      const entry = this.entries[key]
      if (!entry) return null

      if (Date.now() >= entry.expiresAt) {
        const { [key]: _expired, ...rest } = this.entries
        this.entries = rest
        return null
      }

      return entry.value as T
    },

    set<T = unknown>(key: CacheKey, value: T, ttlMs: number) {
      this.entries[key] = {
        value,
        expiresAt: Date.now() + ttlMs
      }
    },

    invalidate(key: CacheKey) {
      const { [key]: _invalidated, ...rest } = this.entries
      this.entries = rest
    },

    invalidatePrefix(prefix: string) {
      const next: Record<CacheKey, CacheEntry> = {}
      for (const [k, v] of Object.entries(this.entries)) {
        if (!k.startsWith(prefix)) next[k] = v
      }
      this.entries = next

      // Also clear matching localStorage entries
      this.clearLocalStoragePrefix(prefix)
    },

    clear() {
      this.entries = {}
      // Also clear all localStorage cache entries
      const storage = getLocalStorage()
      if (storage) {
        const keysToRemove: string[] = []
        for (let i = 0; i < storage.length; i++) {
          const key = storage.key(i)
          if (
            key?.startsWith('meta:') ||
            key?.startsWith('entity:') ||
            key?.startsWith('model-editor:') ||
            key?.startsWith('eam_')
          ) {
            keysToRemove.push(key)
          }
        }
        keysToRemove.forEach((k) => storage.removeItem(k))
      }
    },

    async fetchCached<T>(key: CacheKey, fetcher: () => Promise<T>, ttlMs: number): Promise<T> {
      const cached = this.get<T>(key)
      if (cached !== null) return cached

      const value = await fetcher()
      this.set(key, value, ttlMs)
      return value
    },

    // localStorage-backed cache for persistent data like entity metadata
    getFromLocalStorage<T = unknown>(key: CacheKey): T | null {
      const storage = getLocalStorage()
      if (!storage) return null

      try {
        const raw = storage.getItem(toLocalStorageKey(key))
        if (!raw) return null

        const entry: CacheEntry<T> = JSON.parse(raw)
        if (Date.now() >= entry.expiresAt) {
          storage.removeItem(toLocalStorageKey(key))
          return null
        }

        return entry.value
      } catch {
        return null
      }
    },

    setToLocalStorage<T = unknown>(key: CacheKey, value: T, ttlMs: number) {
      const storage = getLocalStorage()
      if (!storage) return

      try {
        const entry: CacheEntry<T> = {
          value,
          expiresAt: Date.now() + ttlMs
        }
        storage.setItem(toLocalStorageKey(key), JSON.stringify(entry))
      } catch {
        // localStorage might be full or disabled
      }
    },

    invalidateLocalStorage(key: CacheKey) {
      const storage = getLocalStorage()
      if (!storage) return
      storage.removeItem(toLocalStorageKey(key))
    },

    clearLocalStoragePrefix(prefix: string) {
      const storage = getLocalStorage()
      if (!storage) return

      // Special-case: metadata entries are stored under `eam_{entity}`
      if (prefix.startsWith(META_ENTITY_PREFIX)) {
        const entity = prefix.slice(META_ENTITY_PREFIX.length)
        if (entity) {
          storage.removeItem(`eam_${entity}`)
        }
      }

      // Handle user-prefixed meta keys: user:{userId}:meta:entity:v2:{entity}
      const userMetaMatch = prefix.match(USER_META_REGEX)
      if (userMetaMatch) {
        const entity = userMetaMatch[1]
        if (entity) {
          storage.removeItem(`eam_${entity}`)
        }
      }

      const keysToRemove: string[] = []
      for (let i = 0; i < storage.length; i++) {
        const key = storage.key(i)
        if (key?.startsWith(prefix)) {
          keysToRemove.push(key)
        }
      }
      keysToRemove.forEach((k) => storage.removeItem(k))
    },

    async fetchCachedWithLocalStorage<T>(
      key: CacheKey,
      fetcher: () => Promise<T>,
      ttlMs: number
    ): Promise<T> {
      // First check memory cache
      const memoryCached = this.get<T>(key)
      if (memoryCached !== null) return memoryCached

      // Then check localStorage
      const localCached = this.getFromLocalStorage<T>(key)
      if (localCached !== null) {
        // Also set in memory for faster access
        this.set(key, localCached, ttlMs)
        return localCached
      }

      // Fetch from API
      const value = await fetcher()
      this.set(key, value, ttlMs)
      this.setToLocalStorage(key, value, ttlMs)
      return value
    }
  }
})
