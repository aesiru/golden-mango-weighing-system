/**
 * Admin API Composable
 * ====================
 * User management, role management, permissions, ordering.
 */
import { useApiFetch } from './useApiFetch'

export const useAdminApi = () => {
  const { apiFetch, baseURL } = useApiFetch()

  return {
    async getAdminRoles() {
      return apiFetch<{ status: string; data: any[] }>(`${baseURL}/admin/roles`)
    },

    async getAdminUsers(skip = 0, limit = 50, search?: string) {
      const params = new URLSearchParams()
      params.append('skip', skip.toString())
      params.append('limit', limit.toString())
      if (search) params.append('search', search)
      return apiFetch<{ status: string; data: { users: any[]; total: number; skip: number; limit: number } }>(
        `${baseURL}/admin/users?${params.toString()}`
      )
    },

    async assignRoleToUser(userId: string, roleId: string) {
      return apiFetch<{ status: string; message: string }>(`${baseURL}/admin/users/${userId}/roles/${roleId}`, { method: 'POST' })
    },

    async removeRoleFromUser(userId: string, roleId: string) {
      return apiFetch<{ status: string; message: string }>(`${baseURL}/admin/users/${userId}/roles/${roleId}`, { method: 'DELETE' })
    },

    async createUser(userData: { username: string; email: string; full_name: string; password: string; is_active: boolean; is_superuser: boolean }) {
      return apiFetch<{ status: string; message: string; data: any }>(`${baseURL}/admin/users`, { method: 'POST', body: userData })
    },

    async updateUser(userId: string, userData: { username?: string; email?: string; full_name?: string; password?: string; is_active?: boolean; is_superuser?: boolean }) {
      return apiFetch<{ status: string; message: string; data: any }>(`${baseURL}/admin/users/${userId}`, { method: 'PUT', body: userData })
    },

    async deleteUser(userId: string) {
      return apiFetch<{ status: string; message: string }>(`${baseURL}/admin/users/${userId}`, { method: 'DELETE' })
    },

    async createRole(roleData: { name: string; description: string; is_active: boolean }) {
      return apiFetch<{ status: string; message: string; data: any }>(`${baseURL}/admin/roles`, { method: 'POST', body: roleData })
    },

    async updateRole(roleId: string, roleData: { name?: string; description?: string; is_active?: boolean }) {
      return apiFetch<{ status: string; message: string; data: any }>(`${baseURL}/admin/roles/${roleId}`, { method: 'PUT', body: roleData })
    },

    async deleteRole(roleId: string) {
      return apiFetch<{ status: string; message: string }>(`${baseURL}/admin/roles/${roleId}`, { method: 'DELETE' })
    },

    async getAdminUserMeta() {
      return apiFetch<{ status: string; message: string; data: any }>(`${baseURL}/admin/meta/user`)
    },

    async getAdminRoleMeta() {
      return apiFetch<{ status: string; message: string; data: any }>(`${baseURL}/admin/meta/role`)
    },

    async getAdminPermissionMatrix() {
      return apiFetch<{ status: string; data: { entities: string[]; matrix: any[] } }>(`${baseURL}/admin/permissions/matrix`)
    },

    async getEntitiesByModule() {
      return apiFetch<{ status: string; data: { rows: any[]; total_entities: number } }>(`${baseURL}/admin/permissions/entities`)
    },

    async getRolePermissions(roleId: string) {
      return apiFetch<{
        status: string
        data: {
          role: any
          permissions: {
            can_read: string[]
            can_create: string[]
            can_update: string[]
            can_delete: string[]
            can_select?: string[]
            can_export?: string[]
            can_import?: string[]
            in_sidebar?: string[]
          }
        }
      }>(
        `${baseURL}/admin/permissions/role/${roleId}`
      )
    },

    async updateRolePermissions(
      roleId: string,
      permissions: {
        can_read: string[]
        can_create: string[]
        can_update: string[]
        can_delete: string[]
        can_select?: string[]
        can_export?: string[]
        can_import?: string[]
        in_sidebar?: string[]
      }
    ) {
      return apiFetch<{ status: string; message: string }>(`${baseURL}/admin/permissions/role/${roleId}`, { method: 'PUT', body: { permissions } })
    },

    async updateModuleOrder(orderData: { modules: string[] }) {
      return apiFetch<{ status: string; message: string }>(`${baseURL}/admin/ordering/modules`, { method: 'PUT', body: orderData })
    },

    async updateEntityOrder(orderData: { entities: { name: string; module: string; sort_order: number }[] }) {
      return apiFetch<{ status: string; message: string }>(`${baseURL}/admin/ordering/entities`, { method: 'PUT', body: orderData })
    },

    async getModuleEntities(module: string) {
      return apiFetch<{ status: string; message: string; data: { name: string; label: string; module: string; sort_order: number }[] }>(
        `${baseURL}/admin/ordering/entities?module=${encodeURIComponent(module)}`
      )
    },

    async updateModuleEntityOrder(orderData: { module: string; entity_names: string[] }) {
      return apiFetch<{ status: string; message: string }>(`${baseURL}/admin/ordering/entities`, { method: 'PUT', body: orderData })
    },
  }
}
