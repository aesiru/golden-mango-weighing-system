/**
 * Audit Log API Composable
 * =======================
 * System-wide audit log viewer for administrators.
 * Provides access to all audit events across the system with filtering capabilities.
 */
import { useApiFetch } from './useApiFetch'
import type { ActionResponse, AuditEntry } from './useApiTypes'

export interface AuditLogFilters {
  entity?: string
  user_id?: string
  action?: string
  record_id?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export interface AuditLogResponse {
  status: string
  data: AuditEntry[]
  page: number
  page_size: number
}

export interface AuditLogEntryResponse {
  status: string
  data: AuditEntry & {
    before_snapshot: Record<string, unknown> | null
    after_snapshot: Record<string, unknown> | null
  }
}

export const useAuditLogApi = () => {
  const { apiFetch, baseURL } = useApiFetch()

  return {
    /**
     * Get paginated audit log with filters
     */
    async getAuditLog(filters: AuditLogFilters = {}): Promise<AuditLogResponse> {
      const params = new URLSearchParams()
      
      if (filters.entity) params.append('entity', filters.entity)
      if (filters.user_id) params.append('user_id', filters.user_id)
      if (filters.action) params.append('action', filters.action)
      if (filters.record_id) params.append('record_id', filters.record_id)
      if (filters.date_from) params.append('date_from', filters.date_from)
      if (filters.date_to) params.append('date_to', filters.date_to)
      if (filters.page) params.append('page', filters.page.toString())
      if (filters.page_size) params.append('page_size', filters.page_size.toString())
      
      const query = params.toString()
      return apiFetch<AuditLogResponse>(`${baseURL}/audit-log${query ? `?${query}` : ''}`)
    },

    /**
     * Get single audit log entry with full snapshots
     */
    async getAuditLogEntry(logId: number): Promise<AuditLogEntryResponse> {
      return apiFetch<AuditLogEntryResponse>(`${baseURL}/audit-log/${logId}`)
    },

    /**
     * Export audit log as CSV (admin-only)
     */
    async exportAuditLog(filters: Omit<AuditLogFilters, 'page' | 'page_size'> = {}): Promise<Blob> {
      const params = new URLSearchParams()
      
      if (filters.entity) params.append('entity', filters.entity)
      if (filters.user_id) params.append('user_id', filters.user_id)
      if (filters.action) params.append('action', filters.action)
      if (filters.record_id) params.append('record_id', filters.record_id)
      if (filters.date_from) params.append('date_from', filters.date_from)
      if (filters.date_to) params.append('date_to', filters.date_to)
      
      const query = params.toString()
      return apiFetch(`${baseURL}/audit-log/export${query ? `?${query}` : ''}`, {
        responseType: 'blob'
      }) as Promise<Blob>
    },

    /**
     * Get audit log statistics (summary data)
     */
    async getAuditLogStats(): Promise<ActionResponse<{
      total_events: number
      events_by_action: Record<string, number>
      events_by_entity: Record<string, number>
      events_by_user: Record<string, number>
      recent_activity: AuditEntry[]
    }>> {
      return apiFetch(`${baseURL}/audit-log/stats`)
    }
  }
}
