import { useApiFetch } from './useApiFetch'

export interface NotificationCatalogEntry {
  catalog_id: string
  title: string
  description: string
  entity_type: string
  event: string
  category: string
}

export interface MyNotificationSubscription {
  id: string
  user_id: string
  entity_type: string
  entity_id?: string | null
  event: string
  recipient_email?: string | null
  is_active: boolean
  catalog_id?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export const useNotificationSubscriptionsApi = () => {
  const { apiFetch, baseURL } = useApiFetch()

  return {
    async getCatalog() {
      return apiFetch<{ status: string; data: NotificationCatalogEntry[] }>(
        `${baseURL}/notifications/catalog`
      )
    },

    async listMySubscriptions() {
      return apiFetch<{ status: string; data: MyNotificationSubscription[] }>(
        `${baseURL}/notifications/subscriptions/me`
      )
    },

    async subscribe(catalogId: string) {
      return apiFetch<{ status: string; message: string; data: MyNotificationSubscription }>(
        `${baseURL}/notifications/subscriptions/me`,
        { method: 'POST', body: { catalog_id: catalogId } }
      )
    },

    async unsubscribe(subscriptionId: string) {
      return apiFetch<{ status: string; message: string }>(
        `${baseURL}/notifications/subscriptions/me/${subscriptionId}`,
        { method: 'DELETE' }
      )
    },
  }
}
