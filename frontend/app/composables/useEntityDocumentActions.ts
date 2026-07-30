/**
 * useEntityDocumentActions
 * ========================
 * Manages document-level actions (the "Actions" dropdown on the form header).
 * Mirrors the FormPage pattern exactly — any action result from a child related
 * grid should be forwarded to `handleActionResult` so side-effects (modals, etc.)
 * are triggered consistently regardless of where the action originates.
 *
 * Handles:
 *  - Filtering visible actions via show_when + permissions
 *  - Confirmation dialog before execution
 *  - Blocking overlay (saving ref drives savingOverlay from parent)
 *  - Nested error payloads (e.g. generate_rfq failure inside success envelope)
 *  - Serial number modal trigger (need_update_serial_num)
 *  - Redirect on nested path result
 *
 * Usage:
 *   const { visibleDocumentActions, handleDocumentAction, handleActionResult,
 *           serialModalOpen, serialModalInventoryIds, serialModalReceiptId,
 *           onSerialNumbersSubmitted }
 *     = useEntityDocumentActions(entityName, recordId, entityMeta, formData,
 *                                permissions, permissionsLoading, isNew,
 *                                saving, loadData, loadRelated)
 */
import type { Ref, ComputedRef } from "vue";
import type { DocumentAction, EntityMeta } from "~/composables/useApiTypes";
import { matchesCondition } from "~/composables/useFormState";

export function useEntityDocumentActions(
  entityName: ComputedRef<string>,
  recordId: ComputedRef<string>,
  entityMeta: Ref<EntityMeta | null>,
  formData: Ref<Record<string, any>>,
  permissions: Ref<Record<string, boolean> | null>,
  permissionsLoading: Ref<boolean>,
  isNew: ComputedRef<boolean>,
  saving: Ref<boolean>,
  loadData: () => Promise<void>,
  loadRelated: () => Promise<void>,
) {
  const { postDocumentAction } = useApi();
  const toast = useToast();
  const confirmDialog = useConfirmDialog();
  const router = useRouter();

  // Serial number modal state — triggered by confirm_receipt on serialized items
  const serialModalOpen = ref(false);
  const serialModalInventoryIds = ref<string[]>([]);
  const serialModalReceiptId = ref("");
  const serialModalEntityName = ref("");

  /**
   * Filtered list of actions visible to the current user in the current form state.
   * Depends on permissions, show_when conditions, and whether the record is new.
   */
  const visibleDocumentActions = computed((): DocumentAction[] => {
    if (isNew.value || !entityMeta.value?.actions) return [];
    if (permissionsLoading.value) return [];
    const perms = permissions.value;
    if (!perms) return [];
    if (perms?.can_update === false) return [];

    return entityMeta.value.actions.filter((action: DocumentAction) => {
      if (!action.show_when) return true;
      return matchesCondition(action.show_when, formData.value, entityMeta.value);
    });
  });

  /**
   * Processes the nested data payload returned by any document action.
   * Called both from the form-page header actions AND from child grid @action-result
   * so both paths trigger the same side-effects (modals, redirects, toasts).
   */
  const handleActionResult = async (
    nested: any,
    successMessage?: string,
  ): Promise<void> => {
    // Nested error inside a success envelope
    if (nested?.status === "error") {
      const msg = nested.message || successMessage;
      if (msg) toast.add({ title: msg, color: "error", type: "foreground" });
      return;
    }

    // Serial number modal (confirm_receipt on serialized items)
    if (nested?.action === "need_update_serial_num" && nested?.inventory_ids?.length) {
      if (successMessage) {
        toast.add({ title: successMessage, color: "success", type: "foreground" });
      }
      await loadData();
      await loadRelated();
      serialModalInventoryIds.value = nested.inventory_ids;
      serialModalReceiptId.value = nested?._sourceId || recordId.value;
      serialModalEntityName.value = nested?._sourceEntity || entityName.value;
      serialModalOpen.value = true;
      return;
    }

    // Default success path
    if (successMessage) {
      toast.add({ title: successMessage, color: "success", type: "foreground" });
    }
    await loadData();
    await loadRelated();

    // Redirect if action returns a path
    if (nested?.path) {
      router.push(nested.path);
    }
  };

  /**
   * Executes a document action by calling the backend and delegating result
   * handling to handleActionResult.
   */
  const executeDocumentAction = async (action: DocumentAction): Promise<void> => {
    if (saving.value) return;
    try {
      saving.value = true;
      const response = await postDocumentAction(
        entityName.value,
        recordId.value,
        action.action,
      );

      if (response.status === "success") {
        const nested = (response as any).data;
        await handleActionResult(nested, response.message ?? undefined);
      } else {
        if (response.message) {
          toast.add({ title: response.message, color: "error", type: "foreground" });
        }
      }
    } catch (err: any) {
      if (err?.message) {
        toast.add({ title: err.message, color: "error", type: "foreground" });
      }
    } finally {
      saving.value = false;
    }
  };

  /**
   * Entry point for header Actions dropdown.
   * Shows confirmation dialog if action.confirm is set, then executes.
   */
  const handleDocumentAction = async (action: DocumentAction): Promise<void> => {
    if (saving.value) return;
    if (action.confirm) {
      const confirmed = await confirmDialog({
        title: "Confirm Action",
        description: action.confirm,
        confirmLabel: "Proceed",
      });
      if (!confirmed) return;
    }
    await executeDocumentAction(action);
  };

  /**
   * Handles action-result events emitted by child EntityRelatedDataGrid components.
   * Delegates to the shared handleActionResult so modals/redirects work the same
   * as when the action is triggered from the form header.
   */
  const handleRelatedGridActionResult = async (result: any): Promise<void> => {
    if (!result) return;
    await handleActionResult(result, undefined);
  };

  /**
   * Called when the SerialNumberModal submits successfully.
   */
  const onSerialNumbersSubmitted = async (message: string): Promise<void> => {
    serialModalOpen.value = false;
    toast.add({ title: message, color: "success", type: "foreground" });
    await loadData();
    await loadRelated();
  };

  return {
    visibleDocumentActions,
    handleDocumentAction,
    handleRelatedGridActionResult,
    onSerialNumbersSubmitted,
    serialModalOpen,
    serialModalInventoryIds,
    serialModalReceiptId,
    serialModalEntityName,
  };
}
