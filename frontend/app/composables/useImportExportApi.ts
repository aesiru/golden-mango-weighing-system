/**
 * Import/Export API Composable
 * ============================
 * Template download, file/sheets validation, import execution, export.
 */
import { useApiFetch } from './useApiFetch'
import type { ActionResponse, ImportValidationResult, ImportResult } from './useApiTypes'

type ImportMode = 'create' | 'update'

export const useImportExportApi = () => {
  const { apiFetch, baseURL } = useApiFetch()

  return {
    async downloadImportTemplate(entity: string): Promise<Blob> {
      return apiFetch(`${baseURL}/import-export/${entity}/template`, { responseType: 'blob' }) as Promise<Blob>
    },

    async validateImportFile(entity: string, file: File, mode: ImportMode = 'create'): Promise<ActionResponse<ImportValidationResult>> {
      const form = new FormData()
      form.append('file', file)
      return apiFetch<ActionResponse<ImportValidationResult>>(`${baseURL}/import-export/${entity}/validate?mode=${mode}`, { method: 'POST', body: form })
    },

    async validateImportSheets(entity: string, sheetsUrl: string, mode: ImportMode = 'create'): Promise<ActionResponse<ImportValidationResult>> {
      return apiFetch<ActionResponse<ImportValidationResult>>(`${baseURL}/import-export/${entity}/validate/sheets?mode=${mode}`, { method: 'POST', body: { sheets_url: sheetsUrl } })
    },

    async executeImportFile(entity: string, file: File, mode: ImportMode = 'create'): Promise<ActionResponse<ImportResult>> {
      const form = new FormData()
      form.append('file', file)
      return apiFetch<ActionResponse<ImportResult>>(`${baseURL}/import-export/${entity}/execute?mode=${mode}`, { method: 'POST', body: form })
    },

    async executeImportSheets(entity: string, sheetsUrl: string, mode: ImportMode = 'create'): Promise<ActionResponse<ImportResult>> {
      return apiFetch<ActionResponse<ImportResult>>(`${baseURL}/import-export/${entity}/execute/sheets?mode=${mode}`, { method: 'POST', body: { sheets_url: sheetsUrl } })
    },

    async exportEntity(entity: string, format: 'xlsx' | 'csv' = 'xlsx'): Promise<Blob> {
      return apiFetch(`${baseURL}/import-export/${entity}/export?format=${format}`, { responseType: 'blob' }) as Promise<Blob>
    },
  }
}
