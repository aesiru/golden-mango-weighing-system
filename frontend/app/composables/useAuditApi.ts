/**
 * Audit API Composable
 * ====================
 * Audit trail for entity records.
 */
import { useApiFetch } from './useApiFetch'
import type { AuditEntry } from './useApiTypes'

export const useAuditApi = () => {
  const { apiFetch, baseURL } = useApiFetch()

  return {
    async getAuditTrail(
      entity: string,
      recordId: string,
      page: number = 1,
      pageSize: number = 20
    ): Promise<{ status: string; data: AuditEntry[]; total: number; page: number; page_size: number }> {
      const params = new URLSearchParams()
      params.append('page', page.toString())
      params.append('page_size', pageSize.toString())
      return apiFetch(`${baseURL}/entity/${entity}/${recordId}/audit?${params.toString()}`)
    },
  }
}
