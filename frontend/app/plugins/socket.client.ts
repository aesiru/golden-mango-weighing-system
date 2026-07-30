import { io, type Socket } from 'socket.io-client'
import { useAuthStore } from '~/stores/auth'
import { useCacheStore } from '~/stores/cache'

export default defineNuxtPlugin(() => {
  const authStore = useAuthStore()
  const cacheStore = useCacheStore()
  const config = useRuntimeConfig()
  const toast = useToast()

  const logPrefix = '[socket]'

  const apiUrl = String(config.public.apiUrl || '')
  const socketUrl = apiUrl.endsWith('/api') ? apiUrl.slice(0, -4) : apiUrl

  let socket: Socket | null = null

  const disconnect = () => {
    if (!socket) return
    console.info(logPrefix, 'disconnecting')
    socket.disconnect()
    socket = null
  }

  const connect = () => {
    if (socket) return

    console.info(logPrefix, 'connecting', { socketUrl })

    socket = io(socketUrl, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 500,
      reconnectionDelayMax: 5000,
      timeout: 20000,
      auth: {
        token: authStore.token || undefined
      }
    })

    socket.on('connect', () => {
      console.info(logPrefix, 'connected', { id: socket?.id })
    })

    socket.on('disconnect', (reason) => {
      console.info(logPrefix, 'disconnected', { reason })
    })

    socket.io.on('reconnect_attempt', (attempt) => {
      console.info(logPrefix, 'reconnect_attempt', { attempt })
    })

    socket.io.on('reconnect_error', (err) => {
      console.error(logPrefix, 'reconnect_error', err)
    })

    socket.io.on('reconnect_failed', () => {
      console.error(logPrefix, 'reconnect_failed')
    })

    socket.on('entity:change', (payload: unknown) => {
      const p = (payload && typeof payload === 'object') ? payload as Record<string, unknown> : null
      const entity = typeof p?.entity === 'string' ? p.entity : null
      const recordId = typeof p?.record_id === 'string' ? p.record_id : null

      console.info(logPrefix, 'entity:change received', { entity, recordId, payload })

      const userPrefix = authStore.user?.id ? `user:${authStore.user.id}:` : ""

      if (entity) {
        cacheStore.invalidatePrefix(`meta:entity:${entity}`)
        cacheStore.invalidatePrefix(`${userPrefix}meta:entity:v2:${entity}`)
        cacheStore.invalidatePrefix(`entity:list:${entity}:`)
        cacheStore.invalidatePrefix(`entity:options:${entity}:`)

        if (recordId) {
          cacheStore.invalidatePrefix(`entity:detail:${entity}:${recordId}`)
        }
      }

      cacheStore.invalidatePrefix('meta:list')
      cacheStore.invalidatePrefix(`${userPrefix}meta:list`)
    })

    socket.on('meta:change', (payload: unknown) => {
      const p = (payload && typeof payload === 'object') ? payload as Record<string, unknown> : null
      const scope = typeof p?.scope === 'string' ? p.scope : null

      console.info(logPrefix, 'meta:change received', { scope, payload })

      const userPrefix = authStore.user?.id ? `user:${authStore.user.id}:` : ""

      // Conservative invalidation for config changes.
      // This covers entity ordering changes and model-editor metadata edits.
      cacheStore.invalidatePrefix('meta:list')
      cacheStore.invalidatePrefix(`${userPrefix}meta:list`)
      cacheStore.invalidatePrefix('meta:entity:')
      cacheStore.invalidatePrefix(`${userPrefix}meta:entity:v2:`)
      cacheStore.invalidatePrefix('model-editor:entities')
      cacheStore.invalidatePrefix('admin:ordering:')
    })

    socket.on('post_save', (payload: unknown) => {
      const p = (payload && typeof payload === 'object') ? payload as Record<string, unknown> : null
      const entity = typeof p?.entity === 'string' ? p.entity : null
      const action = typeof p?.action === 'string' ? p.action : null
      const message = typeof p?.message === 'string' ? p.message : null
      const hookResult = p?.hook_result
      const recordId = typeof p?.record_id === 'string' ? p.record_id : undefined

      if (entity && action && message) {
        const notificationsEnabled = false

        let toastColor: 'success' | 'error' | 'info' | 'warning' = 'success'
        let toastTitle = message
        let notificationType: 'success' | 'error' | 'info' | 'warning' = 'success'

        if (hookResult && typeof hookResult === 'object' && hookResult !== null) {
          if ('status' in hookResult && hookResult.status === 'error') {
            toastColor = 'error'
            notificationType = 'error'
            toastTitle = (hookResult as any).message || 'Post-save hook failed'
          } else if ('message' in hookResult) {
            toastTitle = (hookResult as any).message || message
          }
        }

        toast.add({ title: toastTitle, color: toastColor, type: 'background' })

        if (notificationsEnabled) {
          const { add: addNotification } = useNotificationCenter()
          addNotification({
            title: toastTitle,
            entity,
            recordId,
            type: notificationType,
          })
        }
      }
    })

    socket.on('connect_error', (err) => {
      console.error(logPrefix, 'connect_error', err)
    })
  }

  watch(
    () => authStore.token,
    (token) => {
      if (!token) {
        disconnect()
        cacheStore.clear()
        return
      }

      if (socket) {
        socket.auth = { token }
      }

      connect()
    },
    { immediate: true }
  )

  return {
    provide: {
      socket: computed(() => socket)
    }
  }
})
