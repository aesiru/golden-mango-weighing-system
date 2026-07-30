/**
 * useNotificationCenter - In-App Notification Store
 * ====================================================
 * Stores notifications from socket.io events (workflow approvals,
 * entity changes, etc.) with unread count and persistence.
 */

const STORAGE_KEY = 'eam_notifications'
const MAX_NOTIFICATIONS = 50

export interface AppNotification {
  id: string
  title: string
  description?: string
  entity?: string
  recordId?: string
  type: 'info' | 'success' | 'warning' | 'error'
  read: boolean
  createdAt: string
}

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6)
}

export const useNotificationCenter = () => {
  const notifications = useState<AppNotification[]>('app_notifications', () => {
    if (!import.meta.client) return []
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? JSON.parse(raw) : []
    } catch {
      return []
    }
  })

  const unreadCount = computed(() => notifications.value.filter(n => !n.read).length)

  function persist() {
    if (!import.meta.client) return
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications.value))
  }

  function add(notification: Omit<AppNotification, 'id' | 'read' | 'createdAt'>) {
    notifications.value.unshift({
      ...notification,
      id: generateId(),
      read: false,
      createdAt: new Date().toISOString(),
    })
    // Trim to max
    if (notifications.value.length > MAX_NOTIFICATIONS) {
      notifications.value = notifications.value.slice(0, MAX_NOTIFICATIONS)
    }
    persist()
  }

  function markRead(id: string) {
    const n = notifications.value.find(n => n.id === id)
    if (n) {
      n.read = true
      persist()
    }
  }

  function markAllRead() {
    notifications.value.forEach(n => { n.read = true })
    persist()
  }

  function remove(id: string) {
    notifications.value = notifications.value.filter(n => n.id !== id)
    persist()
  }

  function clearAll() {
    notifications.value = []
    persist()
  }

  return { notifications, unreadCount, add, markRead, markAllRead, remove, clearAll }
}
