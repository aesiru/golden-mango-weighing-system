/**
 * useApi - Backward-Compatible Facade
 * ====================================
 * Composes domain API composables into a single unified interface.
 *
 * Types are exported ONLY from useApiTypes.ts (not re-exported here)
 * to avoid Nuxt auto-import duplication warnings.
 *
 * New code should import from the domain-specific composables directly:
 *   - useEntityApi     (entity CRUD, list, options, auth)
 *   - useAdminApi      (users, roles, permissions, ordering)
 *   - useWorkflowApi   (global workflow management)
 *   - useModelEditorApi (model editor, migrations, backups)
 *   - useImportExportApi (import/export)
 *   - useAttachmentApi (attachment CRUD)
 *   - useAuditApi      (audit trail)
 */

import { useEntityApi, getLinkedTitle, updateLinkedTitlesCache } from './useEntityApi'
import { useAdminApi } from './useAdminApi'
import { useWorkflowApi } from './useWorkflowApi'
import { useModelEditorApi } from './useModelEditorApi'
import { useImportExportApi } from './useImportExportApi'
import { useAttachmentApi } from './useAttachmentApi'
import { useAuditApi } from './useAuditApi'
import { useTreeApi } from './useTreeApi'

/**
 * Backward-compatible facade composable.
 * Merges all domain API composables into a single return object.
 */
export const useApi = () => {
  const entity = useEntityApi()
  const admin = useAdminApi()
  const workflow = useWorkflowApi()
  const modelEditor = useModelEditorApi()
  const importExport = useImportExportApi()
  const attachment = useAttachmentApi()
  const audit = useAuditApi()
  const tree = useTreeApi()

  return {
    ...entity,
    ...admin,
    ...workflow,
    ...modelEditor,
    ...importExport,
    ...attachment,
    ...audit,
    ...tree,
  }
}
