/**
 * Model Editor API Composable
 * ============================
 * Model editor CRUD, migrations, backups.
 *
 * Architecture: Frappe-inspired atomic save.
 * The PUT endpoint does everything in one request:
 *   validate → backup → save JSON → reload registry → update model → migrate DB
 */
import { useCacheStore } from '~/stores/cache'
import { useApiFetch } from './useApiFetch'
import type {
  ModelEditorEntity,
  FieldTypeOption,
  EntityMetadata,
  ChangeItem,
  BackupItem,
  SyncResultData,
} from './useApiTypes'

const TTL_MODEL_EDITOR = 5 * 60 * 1000

export const useModelEditorApi = () => {
  const { apiFetch, baseURL } = useApiFetch()
  const cache = useCacheStore()

  return {
    async getModelEditorEntities() {
      return cache.fetchCached(
        'model-editor:entities',
        () => apiFetch<{ status: string; message: string; data: ModelEditorEntity[] }>(`${baseURL}/admin/model-editor/entities`),
        TTL_MODEL_EDITOR
      )
    },

    async getModelEditorFieldTypes() {
      return apiFetch<{ status: string; message: string; data: FieldTypeOption[] }>(`${baseURL}/admin/model-editor/field-types`)
    },

    async getModelEditorEntity(entityName: string) {
      return apiFetch<{ status: string; message: string; data: { metadata: EntityMetadata; model_status: { exists: boolean; has_changes: boolean } } }>(
        `${baseURL}/admin/model-editor/entity/${entityName}`
      )
    },

    /**
     * Atomic save: validate → backup → save JSON → reload registry
     * → update model → generate migration → apply migration.
     * Single endpoint replaces the old multi-step workflow.
     */
    async saveEntity(entityName: string, metadata: EntityMetadata) {
      cache.invalidate('model-editor:entities')
      return apiFetch<{ status: string; message: string; data: SyncResultData }>(
        `${baseURL}/admin/model-editor/entity/${entityName}`,
        { method: 'PUT', body: metadata }
      )
    },

    /**
     * Draft save: validate → backup → save JSON → reload registry.
     * Skips model update and migration — deferred to restart or 'Sync All'.
     */
    async saveEntityDraft(entityName: string, metadata: EntityMetadata) {
      cache.invalidate('model-editor:entities')
      return apiFetch<{ status: string; message: string; data: SyncResultData }>(
        `${baseURL}/admin/model-editor/entity/${entityName}/save-draft`,
        { method: 'PUT', body: metadata }
      )
    },

    /**
     * Sync all entities: update model files + generate/apply migration.
     * Like Frappe's `bench migrate`.
     */
    async syncAllEntities() {
      cache.invalidate('model-editor:entities')
      return apiFetch<{ status: string; message: string; data: { updated_models: string[]; migration_applied: boolean; migration_file: string | null; warnings: string[]; message: string } }>(
        `${baseURL}/admin/model-editor/sync-all`,
        { method: 'POST' }
      )
    },

    async previewEntityChanges(entityName: string, metadata: EntityMetadata) {
      return apiFetch<{ status: string; message: string; data: { valid?: boolean; is_safe: boolean; changes: ChangeItem[]; model_has_changes: boolean; errors?: string[] } }>(
        `${baseURL}/admin/model-editor/entity/${entityName}/preview-changes`,
        { method: 'POST', body: metadata }
      )
    },

    async applyMigrations(revision: string = 'head') {
      return apiFetch<{ status: string; message: string; data: any }>(`${baseURL}/admin/model-editor/migration/apply`, { method: 'POST', body: { revision } })
    },

    async rollbackMigrations(steps: number = 1) {
      return apiFetch<{ status: string; message: string; data: any }>(`${baseURL}/admin/model-editor/migration/rollback`, { method: 'POST', body: { steps } })
    },

    async getMigrationStatus() {
      return apiFetch<{ status: string; message: string; data: { current_revision: string | null; migrations: any[]; needs_migration: boolean | null } }>(
        `${baseURL}/admin/model-editor/migration/status`
      )
    },

    async getEntityBackups(entityName: string) {
      return apiFetch<{ status: string; message: string; data: BackupItem[] }>(`${baseURL}/admin/model-editor/entity/${entityName}/backups`)
    },

    async restoreEntityBackup(entityName: string, backupFilename: string) {
      cache.invalidate('model-editor:entities')
      return apiFetch<{ status: string; message: string; data: SyncResultData }>(
        `${baseURL}/admin/model-editor/entity/${entityName}/restore`,
        { method: 'POST', body: { backup_filename: backupFilename } }
      )
    },

    async reloadMetadataRegistry() {
      cache.invalidate('model-editor:entities')
      return apiFetch<{ status: string; message: string; data: { entity_count: number } }>(`${baseURL}/admin/model-editor/reload-metadata`, { method: 'POST' })
    },
  }
}
