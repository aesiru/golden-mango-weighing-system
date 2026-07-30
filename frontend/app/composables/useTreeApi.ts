/**
 * Tree API composable for hierarchical entity data.
 */
import type { ActionResponse } from './useApiTypes'

export const useTreeApi = () => {
  const { apiFetch, baseURL } = useApiFetch()

  const getEntityTree = async (
    entity: string,
    options?: {
      parentField?: string
      titleField?: string
    }
  ): Promise<ActionResponse<any[]>> => {
    const params = new URLSearchParams()
    if (options?.parentField) params.append('parent_field', options.parentField)
    if (options?.titleField) params.append('title_field', options.titleField)

    const query = params.toString()
    const url = `${baseURL}/entity/${entity}/tree${query ? `?${query}` : ''}`
    return apiFetch(url)
  }

  return {
    getEntityTree,
  }
}
