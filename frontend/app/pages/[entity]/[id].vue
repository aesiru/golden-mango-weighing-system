<script setup lang="ts">
import { h, resolveComponent } from "vue";
import type { EntityMeta, FieldMeta } from "~/composables/useApiTypes";
import { useCacheStore } from "~/stores/cache";
import { useAuthStore } from "~/stores/auth";
import { useFormState } from "~/composables/useFormState";
import { useRelatedTabMode } from "~/composables/useRelatedTabMode";
import { resolveCellValue } from "~/utils/cellFormat";
import { LazyBlockingLoadingOverlay, USeparator } from "#components";
import { updateLinkedTitlesCache } from "~/composables/useEntityApi";
import HeaderDetailModal from "~/components/entity/HeaderDetailModal.vue";
import HeaderDetailRelatedTable from "~/components/entity/HeaderDetailRelatedTable.vue";
import WorkflowProgressModal from "~/components/workflow/WorkflowProgressModal.vue";
// Attachment state + handlers — see ~/composables/useEntityAttachments.ts
import { useEntityAttachments } from "~/composables/useEntityAttachments";
// Document actions, serial modal, child grid @action-result — see ~/composables/useEntityDocumentActions.ts
import { useEntityDocumentActions } from "~/composables/useEntityDocumentActions";
// Workflow state, transitions, menu — see ~/composables/useEntityWorkflow.ts
import { useEntityWorkflow } from "~/composables/useEntityWorkflow";
// Declarative fetch_from: auto-fills fields when a linked field changes
import { useFetchFrom } from "~/composables/useFetchFrom";

const route = useRoute();
const router = useRouter();
const {
  getEntityMeta,
  getEntityDetail,
  postEntityAction,
  getEntityOptions,
  exportEntity,
  getEntityPrefill,
} = useApi();
const toast = useToast();
const confirmDialog = useConfirmDialog();
const deleteDialog = useDeleteDialog();
const overlay = useOverlay();

// ---------------------------------------------------------------------------
// Route-derived identifiers
// ---------------------------------------------------------------------------
const entityName = computed(() => route.params.entity as string);
const recordId = computed(() => route.params.id as string);
const isNew = computed(() => recordId.value === "new");
const isEditMode = ref(false);

// ---------------------------------------------------------------------------
// Active tab — synced to ?tab= query param; defaults to "details"
// ---------------------------------------------------------------------------
const activeTab = computed({
  get() {
    const tab = route.query.tab;
    return typeof tab === "string" && tab.length ? tab : "details";
  },
  set(tab) {
    const nextTab = typeof tab === "string" && tab.length ? tab : "details";
    const nextQuery = { ...route.query };
    if (nextTab === "details") {
      delete nextQuery.tab;
    } else {
      nextQuery.tab = nextTab;
    }
    router.replace({ path: route.path, query: nextQuery, hash: route.hash });
  },
});

// ---------------------------------------------------------------------------
// Core page state
// ---------------------------------------------------------------------------
const entityMeta = ref<EntityMeta | null>(null);
const formData = ref<Record<string, any>>({});
const originalData = ref<Record<string, any>>({});
const linkedCounts = ref<Record<string, number>>({});
const relatedMeta = ref<Record<string, EntityMeta>>({});

// Related data grid refs (NuGrid-based related entity tabs)
const relatedGridRefs = ref<Record<string, any>>({});
// Header-detail related table refs (UTable-based header-detail tabs)
const relatedTableRefs = ref<Record<string, any>>({});

// Header-detail modal state
const headerDetailModalOpen = ref(false);
const headerDetailModalEntity = ref<string>("");
const headerDetailModalFkField = ref<string>("");
const headerDetailModalMeta = ref<EntityMeta | null>(null);

// Child data grid refs (NuGrid-based editable inline child tables)
const childGridRefs = ref<Record<string, any>>({});
const childGridDirty = ref<Record<string, boolean>>({});
const childGridLoading = ref<Record<string, boolean>>({});
const childEntityMeta = ref<Record<string, EntityMeta>>({});

const dataLoading = ref(true);
const metaLoading = ref(true);
const permissionsLoading = ref(true);
const permissions = ref<Record<string, boolean> | null>(null);
// Page-level loading excludes child grids (they load independently)
const loading = computed(() => dataLoading.value);

function setChildGridLoading(entity: string, isLoading: boolean) {
  childGridLoading.value[entity] = isLoading;
}
function handleChildGridLoading(isLoading: boolean, entity: string) {
  setChildGridLoading(entity, isLoading);
}
const saving = ref(false);
const error = ref("");
// savingOverlay drives the BlockingLoadingOverlay; toggled by the `saving` watcher below.
const savingOverlay = overlay.create(LazyBlockingLoadingOverlay, {
  destroyOnClose: false,
  props: { title: "Executing..." },
});

// ---------------------------------------------------------------------------
// Print preview — see usePrintPreview composable
// ---------------------------------------------------------------------------
const {
  previewHtml: printPreviewHtml,
  showPreview: showPrintPreview,
  loading: printLoading,
  openPreview: openPrintPreview,
  printDirect,
  downloadPdf,
  printFromPreview,
} = usePrintPreview();
const previewIframe = ref<HTMLIFrameElement | null>(null);

function resizeIframe() {
  const iframe = previewIframe.value;
  if (!iframe) return;
  try {
    const doc = iframe.contentDocument || iframe.contentWindow?.document;
    if (doc?.body) {
      const contentHeight =
        doc.documentElement.scrollHeight || doc.body.scrollHeight;
      if (contentHeight > 0) {
        const wrapper = iframe.parentElement;
        if (wrapper) {
          wrapper.style.paddingTop = "0";
          wrapper.style.height = `${contentHeight}px`;
        }
        iframe.style.height = `${contentHeight}px`;
      }
    }
  } catch (_error) {
    // Keep aspect-ratio wrapper fallback
  }
}

// ---------------------------------------------------------------------------
// Link options + titles for select / link fields
// ---------------------------------------------------------------------------
const linkOptions = ref<Record<string, { value: string; label: string }[]>>({});
const linkTitles = ref<Record<string, string>>({});
const loadedLinkFields = ref<Set<string>>(new Set());

const fetchFromLoading = ref<Record<string, boolean>>({});
const fetchFromEnabled = ref(false);
const setFetchFromLoading = (fieldName: string, isLoading: boolean) => {
  fetchFromLoading.value[fieldName] = isLoading;
};
const setFetchFromLinkTitle = (
  linkEntity: string,
  id: string,
  title: string,
) => {
  const key = `${linkEntity}::${id}`;
  linkTitles.value[key] = title;
  updateLinkedTitlesCache({ [key]: title });
};

// ---------------------------------------------------------------------------
// Form state management — useFormState controls field visibility, editability,
// required state, and tab visibility based on workflow/form_state rules.
// See ~/composables/useFormState.ts
// ---------------------------------------------------------------------------
const {
  isFormEditable,
  canAddChildren,
  resolveFieldState,
  resolveTabState,
  fieldStates,
  visibleFields: formStateVisibleFields,
} = useFormState(entityMeta, formData, linkedCounts, isNew);

// Related tab mode detection (header-detail vs NuGrid)
const { isHeaderDetailTab } = useRelatedTabMode();

// Declarative fetch_from: auto-fills fields when a linked field changes.
// See ~/composables/useFetchFrom.ts
useFetchFrom(entityMeta, formData, {
  setLoading: setFetchFromLoading,
  setLinkTitle: setFetchFromLinkTitle,
  enabled: fetchFromEnabled,
});

// ---------------------------------------------------------------------------
// Attachments — all state + handlers.
// Declared early because tabs/watchers/loadData read attachment state.
// See ~/composables/useEntityAttachments.ts
// ---------------------------------------------------------------------------
const attachmentFileInput = ref<HTMLInputElement | null>(null);
const {
  attachments,
  attachmentsLoading,
  attachmentUploading,
  attachmentCount,
  allowAttachments,
  loadAttachments,
  handleAttachmentUpload,
  handleDeleteAttachment,
  handleDownloadAttachment,
  formatFileSize,
} = useEntityAttachments(entityName, recordId, entityMeta, isNew);

// ---------------------------------------------------------------------------
// Field-level errors — populated by handleSave on backend validation failure.
// clearFieldError is bound to each field's @update:model-value.
// validateForm is used by UForm :validate prop for client-side required checks.
// ---------------------------------------------------------------------------
const fieldErrors = ref<Record<string, string>>({});

const clearFieldError = (fieldName: string) => {
  if (fieldErrors.value[fieldName]) {
    const { [fieldName]: _removed, ...rest } = fieldErrors.value;
    fieldErrors.value = rest;
  }
};

/**
 * Handle field value updates from EntityFieldRenderer.
 * This forces Vue reactivity by reassigning formData.value with a spread,
 * ensuring child components (like ChildDataGrid) that watch parentFormData
 * will properly react to changes in parent form fields.
 */
const onFieldUpdate = (fieldName: string, value: any) => {
  // Update the field value
  formData.value[fieldName] = value;
  // Force reactivity by reassigning the entire object
  formData.value = { ...formData.value };
  // Clear any field error
  clearFieldError(fieldName);
};

const validateForm = () => {
  const errors: { name: string; message: string }[] = [];
  for (const field of editableFields.value) {
    const isRequired =
      fieldStates.value[field.name]?.required ?? field.required;
    if (!isRequired) continue;
    const value = formData.value[field.name];
    const isEmptyString = typeof value === "string" && value.trim() === "";
    if (value === null || value === undefined || isEmptyString) {
      errors.push({ name: field.name, message: `${field.label} is required` });
    }
  }
  return errors;
};

// ---------------------------------------------------------------------------
// Computed field/permission helpers
// ---------------------------------------------------------------------------

// editableFields: filters visible fields based on edit mode and readonly flag.
// Driven by useFormState — see formStateVisibleFields.
// Keep fetch_from fields visible in edit mode even if readonly, so users can see auto-populated values.
const editableFields = computed(() => {
  return formStateVisibleFields.value.filter((f: FieldMeta) => {
    if (isNew.value) return !f.readonly;
    // Keep fetch_from fields visible in edit mode (they'll be disabled)
    if (isEditMode.value && f.fetch_from) return true;
    return isEditMode.value ? !f.readonly : true;
  });
});

const canEdit = computed(() => {
  if (permissionsLoading.value) return false;
  const perms = permissions.value;
  if (!perms) return false;
  if (isNew.value) return perms.can_create === true;
  return perms.can_update === true && isFormEditable.value;
});

const canDelete = computed(() => {
  if (permissionsLoading.value) return false;
  const perms = permissions.value;
  if (!perms) return false;
  return !isNew.value && perms.can_delete === true;
});

// Lazy-load link options when a select field is opened.
// Cached by linkEntity so multiple fields sharing the same entity share one list.
const loadLinkOptionsForField = async (
  fieldName: string,
  linkEntity: string,
) => {
  if (loadedLinkFields.value.has(linkEntity)) return;
  loadedLinkFields.value.add(linkEntity);
  try {
    const response = await getEntityOptions(linkEntity);
    if (response.status === "success") {
      linkOptions.value[linkEntity] = response.options;
    }
  } catch (err) {
    console.error(`Failed to load options for ${fieldName}:`, err);
    loadedLinkFields.value.delete(linkEntity);
  }
};

// Returns a display label for a link field using pre-fetched _link_titles.
const getLinkDisplayLabel = (
  fieldName: string,
  linkEntity: string,
  value: any,
): string => {
  if (!value) return "";
  const key = `${linkEntity}::${value}`;
  return linkTitles.value[key] || String(value);
};

// Returns permissions for a linked entity from entityMeta.links.
const getLinkPermissions = (linkEntity: string) => {
  const links = entityMeta.value?.links || [];
  const link = links.find((l: any) => l?.entity === linkEntity);
  return (
    link?.permissions || {
      can_read: true,
      can_create: true,
      can_update: true,
      can_delete: true,
    }
  );
};

// ---------------------------------------------------------------------------
// Related tabs — built from entityMeta.links + form_state tab visibility rules.
// See resolveTabState from useFormState.
// ---------------------------------------------------------------------------
const relatedTabs = computed(() => {
  const links = entityMeta.value?.links || [];
  return links
    .filter((link) => link?.entity && link?.fk_field)
    .filter((link) => resolveTabState(link.entity).visible)
    .map((link) => ({
      label: link.label || link.entity,
      icon: "i-lucide-link",
      slot: link.entity,
      value: link.entity,
      linkEntity: link.entity,
      fkField: link.fk_field,
      count: linkedCounts.value[link.entity] || 0,
      permissions: link.permissions || {
        can_read: true,
        can_create: true,
        can_update: true,
        can_delete: true,
      },
    }));
});

const getChildSectionLabel = (child: any): string => {
  const childEntity = child?.entity;
  if (!childEntity) return child?.label || "Items";
  return (
    childEntityMeta.value[childEntity]?.label || child?.label || childEntity
  );
};

const tabs = computed(() => {
  const items: any[] = [{ label: "Details", value: "details" }];
  if (isNew.value) return items;
  items.push(
    ...relatedTabs.value.map((tab) => ({
      label: tab.label,
      value: tab.value,
      linkEntity: tab.linkEntity,
      fkField: tab.fkField,
      count: tab.count,
    })),
  );
  // Attachments tab is always LAST — see useEntityAttachments for state
  if (allowAttachments.value && !isNew.value) {
    items.push({
      label: "Attachments",
      value: "attachments",
      count: attachmentCount.value || 0,
    });
  }
  return items;
});

const availableTabValues = computed(
  () => new Set((tabs.value || []).map((t: any) => String(t.value))),
);

// Guard against stale ?tab= query param after navigation
watch(
  () => route.query.tab,
  (tab) => {
    if (
      typeof tab === "string" &&
      tab.length &&
      !availableTabValues.value.has(tab)
    ) {
      const nextQuery = { ...route.query };
      delete nextQuery.tab;
      router.replace({ path: route.path, query: nextQuery, hash: route.hash });
    }
  },
  { immediate: true },
);

// Lazy-load related tab metadata when tab is first activated
watch(
  activeTab,
  async (newTab) => {
    if (newTab === "details" || isNew.value) return;
    // Lazy-load attachments on first activation — see useEntityAttachments
    if (newTab === "attachments") {
      if (attachments.value.length === 0 && !attachmentsLoading.value) {
        await loadAttachments();
      }
      return;
    }
    // Lazy-load related entity metadata when tab is clicked
    const relatedTab = relatedTabs.value.find((t) => t.value === newTab);
    if (relatedTab && !relatedMeta.value[relatedTab.linkEntity]) {
      try {
        const metaRes = await getEntityMeta(relatedTab.linkEntity);
        relatedMeta.value[relatedTab.linkEntity] = metaRes.data;
      } catch (err) {
        console.error(
          `Failed to load metadata for ${relatedTab.linkEntity}`,
          err,
        );
      }
    }
  },
  { immediate: true },
);

// ---------------------------------------------------------------------------
// Header-detail modal handlers — used by HeaderDetailRelatedTable tab
// ---------------------------------------------------------------------------
function openHeaderDetailModal(entity: string, fkField: string) {
  headerDetailModalEntity.value = entity;
  headerDetailModalFkField.value = fkField;
  headerDetailModalMeta.value = relatedMeta.value[entity] || null;
  headerDetailModalOpen.value = true;
}

async function handleHeaderDetailCreated(_payload: { id: string }) {
  const entity = headerDetailModalEntity.value;
  const tableRef = relatedTableRefs.value[entity];
  if (tableRef?.loadData) await tableRef.loadData();
  await loadRelated();
}

// ---------------------------------------------------------------------------
// Header menu (ellipsis button) — Print, Export, Duplicate, Delete
// ---------------------------------------------------------------------------
const headerMenuItems = computed(() => {
  if (isNew.value) return [];
  const items: any[] = [
    {
      label: "Print",
      icon: "i-lucide-printer",
      onSelect: () => openPrintPreview(entityName.value, recordId.value),
    },
    {
      label: "Export",
      icon: "i-lucide-download",
      onSelect: async () => {
        try {
          const blob = await exportEntity(entityName.value);
          const url = window.URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = `${entityName.value}_${recordId.value}_${new Date().toISOString().split("T")[0]}.xlsx`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          window.URL.revokeObjectURL(url);
        } catch (e: any) {
          toast.add({ title: e.message, color: "error", type: "foreground" });
        }
      },
    },
  ];

  if (canEdit.value) {
    items.push({
      label: "Duplicate",
      icon: "i-lucide-copy",
      onSelect: async () => {
        const duplicateData = { ...formData.value };
        delete duplicateData.id;
        delete duplicateData.created_at;
        delete duplicateData.updated_at;
        const uniqueFields =
          entityMeta.value?.fields?.filter((f: FieldMeta) => f.unique) || [];
        for (const field of uniqueFields) delete duplicateData[field.name];
        // Reset workflow state to initial via workflowMeta from useEntityWorkflow
        if (workflowMeta.value?.enabled && workflowMeta.value?.initial_state) {
          duplicateData.workflow_state = workflowMeta.value.initial_state;
        }
        sessionStorage.setItem(
          `duplicate_${entityName.value}`,
          JSON.stringify(duplicateData),
        );
        router.push(`/${entityName.value}/new?duplicate=true`);
      },
    });
  }

  if (canDelete.value) {
    items.push({
      label: "Delete",
      icon: "i-lucide-trash-2",
      onSelect: () => handleDelete(),
    });
  }

  return [items];
});

// ---------------------------------------------------------------------------
// Workflow — all state, transitions, menu items, and UI flags.
// See ~/composables/useEntityWorkflow.ts
// NOTE: loadData and loadRelated are passed as callbacks; they are declared
// below and captured by reference via closure — no forward-reference issue.
// ---------------------------------------------------------------------------
// Placeholder refs used as callbacks; actual functions declared below.
// The composable only *calls* them from event handlers, never at init time.
const _loadDataRef = { fn: async () => {} };
const _loadRelatedRef = { fn: async () => {} };
const loadDataCb = () => _loadDataRef.fn();
const loadRelatedCb = () => _loadRelatedRef.fn();

const {
  workflowLoading,
  workflowProgressLoading,
  workflowProgressOpen,
  workflowProgress,
  workflowMeta,
  workflowMenuItems,
  showWorkflowButton,
  showWorkflowBadge,
  showWorkflowProgressButton,
  isWorkflowDisabled,
  currentWorkflowStateLabel,
  currentWorkflowStateColor,
  loadWorkflowTransitions,
  openWorkflowProgress,
} = useEntityWorkflow(
  entityName,
  recordId,
  formData,
  entityMeta,
  permissions,
  permissionsLoading,
  isNew,
  saving,
  loadDataCb,
  loadRelatedCb,
);

// ---------------------------------------------------------------------------
// Document Actions — Actions dropdown + serial number modal.
// handleRelatedGridActionResult wired to @action-result on EntityRelatedDataGrid
// so child grid row actions trigger the same side-effects as header actions.
// See ~/composables/useEntityDocumentActions.ts
// ---------------------------------------------------------------------------
const {
  visibleDocumentActions,
  handleDocumentAction,
  handleRelatedGridActionResult,
  onSerialNumbersSubmitted,
  serialModalOpen,
  serialModalInventoryIds,
  serialModalReceiptId,
  serialModalEntityName,
} = useEntityDocumentActions(
  entityName,
  recordId,
  entityMeta,
  formData,
  permissions,
  permissionsLoading,
  isNew,
  saving,
  loadDataCb,
  loadRelatedCb,
);

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

// loadRelated: loads entityMeta for each related entity link (lazy by tab click).
const loadRelated = async () => {
  if (!entityMeta.value?.links || isNew.value) return;
  await Promise.all(
    entityMeta.value.links.map(async (link) => {
      if (!link?.entity || relatedMeta.value[link.entity]) return;
      try {
        const metaRes = await getEntityMeta(link.entity);
        relatedMeta.value[link.entity] = metaRes.data;
      } catch (err) {
        console.error(`Failed to load metadata for ${link.entity}`, err);
      }
    }),
  );
};

const getFkFieldForRelatedEntity = (linkEntity: string): string | null => {
  const links = entityMeta.value?.links || [];
  const link = links.find((l: any) => l?.entity === linkEntity);
  return link?.fk_field || null;
};

// loadMetadata: fetches entity meta + permissions + child entity metas.
// Must run before loadData (loadData depends on entityMeta for new records).
const loadMetadata = async () => {
  try {
    metaLoading.value = true;
    permissionsLoading.value = true;
    const metaRes = await getEntityMeta(entityName.value);
    entityMeta.value = metaRes.data;
    permissions.value =
      (metaRes.data?.permissions as Record<string, boolean> | undefined) ||
      null;
    const children = metaRes.data?.children || [];
    if (children.length) {
      await Promise.all(
        children.map(async (child: any) => {
          if (childEntityMeta.value[child.entity]) return;
          try {
            const childMetaRes = await getEntityMeta(child.entity);
            childEntityMeta.value[child.entity] = childMetaRes.data;
          } catch (err) {
            console.error(`Failed to load child meta for ${child.entity}`, err);
          }
        }),
      );
    }
  } catch (err: any) {
    error.value = err.message || "Failed to load metadata";
    console.error(err);
  } finally {
    metaLoading.value = false;
    permissionsLoading.value = false;
  }
};

// loadData: fetches record data. For new records, applies defaults + prefill.
// After fetch, fires loadWorkflowTransitions() from useEntityWorkflow in parallel.
const loadData = async () => {
  try {
    dataLoading.value = true;
    error.value = "";

    if (isNew.value) {
      if (!entityMeta.value) return;
      const defaults: Record<string, any> = {};
      entityMeta.value?.fields?.forEach((field: FieldMeta) => {
        if (field.default !== undefined && field.default !== null) {
          defaults[field.name] = field.default;
        }
      });
      // Set initial workflow state — workflowMeta from useEntityWorkflow
      if (workflowMeta.value?.enabled && workflowMeta.value?.initial_state) {
        defaults.workflow_state = workflowMeta.value.initial_state;
      }
      // Fetch server-side prefill (e.g. date_requested = today)
      try {
        const prefillRes = await getEntityPrefill(entityName.value);
        if (prefillRes?.status === "success" && prefillRes.data) {
          Object.assign(defaults, prefillRes.data);
        }
      } catch {
        // Prefill is best-effort
      }
      // Duplicate flow: restore data from sessionStorage
      if (route.query.duplicate === "true") {
        const duplicateKey = `duplicate_${entityName.value}`;
        const duplicateDataStr = sessionStorage.getItem(duplicateKey);
        if (duplicateDataStr) {
          try {
            formData.value = { ...defaults, ...JSON.parse(duplicateDataStr) };
            sessionStorage.removeItem(duplicateKey);
          } catch {
            formData.value = defaults;
          }
        } else {
          formData.value = defaults;
        }
      } else {
        formData.value = defaults;
      }
      isEditMode.value = true;
    } else {
      // Fire detail + attachments in parallel (attachments from useEntityAttachments)
      const detailPromise = getEntityDetail(entityName.value, recordId.value);
      const attachPromise = allowAttachments.value
        ? loadAttachments()
        : Promise.resolve();

      const detailRes = await detailPromise;
      formData.value = { ...detailRes.data };
      originalData.value = { ...detailRes.data };
      linkedCounts.value = (detailRes as any).linked_counts || {};
      linkTitles.value = (detailRes as any)._link_titles || {};

      // Load workflow transitions in parallel so form renders immediately.
      // loadWorkflowTransitions is from useEntityWorkflow — do not inline here.
      loadWorkflowTransitions();

      isEditMode.value = route.query.edit === "true";
      await attachPromise;
    }
  } catch (err: any) {
    error.value = err.message || "Failed to load data";
    console.error(err);
  } finally {
    dataLoading.value = false;
  }
};

// Wire the placeholder callbacks now that the actual functions are defined.
// This pattern avoids forward-reference errors while keeping composables above loadData.
_loadDataRef.fn = loadData;
_loadRelatedRef.fn = loadRelated;

// ---------------------------------------------------------------------------
// Save / Cancel / Delete
// ---------------------------------------------------------------------------

// handleSave: collects dirty child grid data, calls postEntityAction create/update.
// On success, invalidates entity caches so list pages refresh.
const handleSave = async () => {
  if (saving.value) return;
  try {
    saving.value = true;
    error.value = "";
    fieldErrors.value = {};

    const children: Record<string, { rows: any[]; deleted_ids: string[] }> = {};
    const dirtyGrids = Object.entries(childGridRefs.value).filter(
      ([entity]) => childGridDirty.value[entity],
    );
    for (const [childEntity, gridRef] of dirtyGrids) {
      if (gridRef?.getChildData && gridRef?.getDeletedIds) {
        children[childEntity] = {
          rows: gridRef.getChildData(),
          deleted_ids: gridRef.getDeletedIds(),
        };
      }
    }

    const action = isNew.value ? "create" : "update";
    const response = await postEntityAction(entityName.value, {
      action,
      id: isNew.value ? undefined : recordId.value,
      data: formData.value,
      children: Object.keys(children).length > 0 ? children : undefined,
    });

    if (response.status === "success") {
      for (const [, gridRef] of dirtyGrids) {
        if (gridRef?.markAsSaved) gridRef.markAsSaved();
      }
      if (response.message) {
        toast.add({
          title: response.message,
          color: "success",
          type: "foreground",
        });
      }
      const cache = useCacheStore();
      const auth = useAuthStore();
      const userPrefix = auth.user?.id ? `user:${auth.user.id}:` : "";
      cache.invalidatePrefix(`entity:options:${entityName.value}`);
      cache.invalidatePrefix(`${userPrefix}meta:entity:v2:${entityName.value}`);
      if (isNew.value && response.data?.id) {
        router.replace(`/${entityName.value}/${response.data.id}`);
      } else {
        isEditMode.value = false;
        originalData.value = { ...formData.value };
      }
    } else {
      if (response.errors) {
        // Strip field name prefix from error messages (e.g., "Asset Tag: " -> "")
        const cleanedErrors: Record<string, string> = {};
        for (const [field, message] of Object.entries(
          response.errors as Record<string, string>,
        )) {
          cleanedErrors[field] = message.replace(/^[^:]+:\s*/, "");
        }
        fieldErrors.value = cleanedErrors;
      }
      toast.add({
        title: response.message || "Save failed",
        color: "error",
        type: "foreground",
      });
    }
  } catch (err: any) {
    error.value = err.message || "Save failed";
  } finally {
    saving.value = false;
  }
};

const handleCancel = () => {
  if (isNew.value) {
    router.push(`/${entityName.value}`);
  } else {
    formData.value = { ...originalData.value };
    isEditMode.value = false;
  }
};

const handleDelete = () => {
  const itemName =
    formData.value?.[entityMeta.value?.title_field || "name"] ||
    `ID: ${recordId.value}`;
  (async () => {
    const confirmed = await deleteDialog({
      entityName: entityMeta.value?.label || "Record",
      itemName,
    });
    if (!confirmed) return;
    saving.value = true;
    try {
      const response = await postEntityAction(entityName.value, {
        action: "delete",
        id: recordId.value,
      });
      if (response.status === "success") {
        const cache = useCacheStore();
        cache.invalidatePrefix(`entity:options:${entityName.value}`);
        if (response.message) {
          toast.add({
            title: response.message,
            color: "success",
            type: "foreground",
          });
        }
        router.push(`/${entityName.value}`);
      } else {
        // Preserve full response data for referencing records
        const error = new Error(response.message || "Delete failed") as any;
        error.data = response.data;
        throw error;
      }
    } catch (err: any) {
      // Error handled in the outer catch block
      throw err;
    } finally {
      saving.value = false;
    }
  })().catch((err: any) => {
    if (err?.message) {
      const errorMessage = err.message;
      const referencingRecords = err?.data?.referencing_records;

      const toastOptions: any = {
        title: h("span", { innerHTML: errorMessage }),
        color: "error",
        type: "foreground",
      };

      console.log("referencingRecords", referencingRecords);
      console.log(
        "ref.entity, ref.id",
        referencingRecords?.map((ref: any) => ({
          entity: ref.entity,
          id: ref.id,
        })),
      );

      // Add clickable actions for referencing records
      if (referencingRecords && referencingRecords.length > 0) {
        toastOptions.actions = referencingRecords
          .slice(0, 3)
          .map((ref: any) => ({
            label: `View ${ref.entity_display}`,
            to: `/${ref.entity}/${ref.id}`,
            size: "xs" as const,
          }));
      }

      console.log("Toast options being added:", toastOptions);
      toast.add(toastOptions);
    }
  });
};

// ---------------------------------------------------------------------------
// Dirty-form detection (includes child grid changes)
// ---------------------------------------------------------------------------
const anyChildGridDirty = computed(() =>
  Object.values(childGridDirty.value).some(Boolean),
);

const isDirty = computed(() => {
  if (isNew.value) {
    return Object.values(formData.value).some(
      (v) => v !== null && v !== undefined && v !== "",
    );
  }
  return (
    JSON.stringify(formData.value) !== JSON.stringify(originalData.value) ||
    anyChildGridDirty.value
  );
});

// Navigation guard — warn before leaving with unsaved changes
onBeforeRouteLeave((_to, _from, next) => {
  if (isDirty.value && isEditMode.value && !saving.value) {
    confirmDialog({
      title: "Unsaved Changes",
      description: "You have unsaved changes. Are you sure you want to leave?",
      confirmLabel: "Leave",
      confirmColor: "error",
    }).then((confirmed: boolean) => next(confirmed));
  } else {
    next();
  }
});

// Toggle BlockingLoadingOverlay while saving (savingOverlay from overlay.create above)
watch(saving, (isSaving) => {
  if (isSaving) savingOverlay.open();
  else savingOverlay.close();
});

// Guard browser close/refresh with unsaved changes
if (import.meta.client) {
  const beforeUnload = (e: BeforeUnloadEvent) => {
    if (isDirty.value && isEditMode.value && !saving.value) {
      e.preventDefault();
      e.returnValue = "";
    }
  };
  onMounted(() => window.addEventListener("beforeunload", beforeUnload));
  onUnmounted(() => window.removeEventListener("beforeunload", beforeUnload));
}

// Keyboard shortcuts: Ctrl+S / Cmd+S = save, Escape = cancel edit
const onKeydown = (e: KeyboardEvent) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "s") {
    e.preventDefault();
    if (isEditMode.value && !saving.value) handleSave();
  }
  if (e.key === "Escape" && isEditMode.value && !isNew.value) handleCancel();
};

if (import.meta.client) {
  onMounted(() => window.addEventListener("keydown", onKeydown));
  onUnmounted(() => {
    window.removeEventListener("keydown", onKeydown);
    savingOverlay.close();
  });
}

// Route change watcher — reloads metadata + data when entity or record changes
watch(
  () => [entityName.value, recordId.value],
  async () => {
    metaLoading.value = true;
    permissionsLoading.value = true;
    error.value = "";
    fetchFromEnabled.value = false;
    await loadMetadata();
    await loadData();
    await nextTick();
    fetchFromEnabled.value = true;
  },
  { immediate: true },
);

definePageMeta({
  middleware: "auth" as any,
});
</script>

<template>
  <div class="h-full min-h-0 flex flex-col gap-6 px-6 py-6">
    <!-- Header -->
    <div class="flex items-center gap-2">
      <UButton
        variant="ghost"
        icon="i-lucide-arrow-left"
        @click="router.go(-1)"
      />
      <div class="flex-1 flex items-center gap-2">
        <h1 class="text-2xl font-bold mr-2 max-w-[400px] truncate">
          {{
            isNew
              ? "New"
              : formData[entityMeta?.title_field || "id"] ||
                recordId ||
                entityName
          }}
        </h1>

        <UFieldGroup
          v-if="
            showWorkflowButton ||
            showWorkflowBadge ||
            showWorkflowProgressButton
          "
        >
          <UDropdownMenu
            v-if="showWorkflowButton && workflowMenuItems.length"
            :items="workflowMenuItems"
          >
            <UButton
              variant="solid"
              size="md"
              :color="currentWorkflowStateColor"
              :disabled="saving || loading || workflowLoading || workflowMenuItems.length === 0"
              :loading="workflowLoading"
            >
              {{ currentWorkflowStateLabel || "Workflow" }}
            </UButton>
          </UDropdownMenu>
          <UButton
            v-else-if="showWorkflowButton"
            variant="solid"
            size="md"
            :color="currentWorkflowStateColor"
            :disabled="saving || loading || workflowLoading || workflowMenuItems.length === 0"
            :loading="workflowLoading"
          >
            {{ currentWorkflowStateLabel || "Workflow" }}
          </UButton>
          <UButton
            v-else-if="showWorkflowBadge"
            variant="solid"
            size="md"
            :color="currentWorkflowStateColor"
            :disabled="true"
          >
            {{
              currentWorkflowStateLabel ||
              String(formData.workflow_state)
                .replace(/_/g, " ")
                .replace(/\b\w/g, (c) => c.toUpperCase())
            }}
          </UButton>

          <UButton
            v-if="showWorkflowProgressButton"
            variant="solid"
            size="md"
            icon="i-lucide-workflow"
            :disabled="
              saving || loading || workflowLoading || workflowProgressLoading
            "
            :loading="workflowProgressLoading"
            @click="openWorkflowProgress"
          />
        </UFieldGroup>
      </div>

      <!-- Actions -->
      <div class="flex gap-2">
        <!-- Document Actions -->
        <UDropdownMenu
          v-if="!isEditMode && visibleDocumentActions.length > 0"
          :items="
            visibleDocumentActions.map((a) => ({
              label: a.label,
              onSelect: () => handleDocumentAction(a),
            }))
          "
        >
          <UButton
            trailing-icon="i-lucide-chevron-down"
            variant="outline"
            size="md"
            :disabled="saving || loading"
          >
            Actions
          </UButton>
        </UDropdownMenu>

        <template v-if="isEditMode">
          <UFieldGroup>
            <UButton :loading="saving" @click="handleSave">
              {{ isNew ? "Create" : "Save" }}
            </UButton>
            <UButton
              variant="outline"
              icon="i-lucide-x"
              :disabled="saving"
              @click="handleCancel"
            />
          </UFieldGroup>
        </template>
        <template v-else>
          <div class="flex gap-2">
            <div class="flex justify-end">
              <USkeleton v-if="permissionsLoading" class="h-9 w-28" />
              <UButton
                v-else
                icon="i-lucide-pencil"
                @click="isEditMode = true"
                size="md"
                :disabled="!canEdit"
              >
                Edit
              </UButton>
            </div>
            <UDropdownMenu
              v-if="headerMenuItems.length"
              :items="headerMenuItems"
            >
              <UButton
                icon="i-lucide-ellipsis-vertical"
                variant="outline"
                size="md"
                :disabled="saving || loading"
              />
            </UDropdownMenu>
          </div>
        </template>
      </div>
    </div>

    <WorkflowProgressModal
      v-model:open="workflowProgressOpen"
      :loading="workflowProgressLoading"
      :progress="workflowProgress"
    />

    <!-- Loading State - Skeleton -->
    <div v-if="loading" class="space-y-6">
      <!-- Tabs skeleton -->
      <div class="mt-3">
        <div class="flex gap-4 ml-4 mb-3">
          <USkeleton v-for="i in 4" :key="i" class="h-4 w-24" />
        </div>
        <USeparator />
      </div>

      <!-- Form skeleton -->
      <div class="space-y-6 mt-3">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div v-for="i in 8" :key="i" class="space-y-2">
            <USkeleton class="h-4 w-24" />
            <USkeleton class="h-8 w-full" />
          </div>
        </div>
      </div>
    </div>

    <UTabs
      v-else-if="!metaLoading && entityMeta"
      v-model="activeTab"
      :items="tabs"
      :unmount-on-hide="true"
      class="w-full flex-1 min-h-0 flex flex-col"
      :ui="{
        root: 'flex flex-col min-h-0',
        list: 'shrink-0',
        content: 'flex-1 min-h-0 flex flex-col',
      }"
      size="md"
      variant="link"
    >
      <template #default="{ item }">
        <div class="flex items-center gap-2">
          <span>{{ item.label }}</span>
          <UBadge
            v-if="item.count && item.count > 0"
            size="sm"
            variant="solid"
            color="primary"
            class="rounded-full w-5 justify-center font-bold"
          >
            {{ item.count }}
          </UBadge>
        </div>
      </template>
      <template #content="{ item }">
        <!-- Details Tab -->
        <div
          v-if="item.value === 'details'"
          class="flex-1 min-h-0 flex flex-col overflow-hidden"
        >
          <div class="flex-1 min-h-0 overflow-y-auto space-y-6">
            <UForm
              :state="formData"
              :validate="validateForm"
              class="space-y-6 mt-2 mb-8"
              @submit.prevent="handleSave"
            >
              <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div
                  v-for="field in editableFields"
                  :key="field.name"
                  class="space-y-2"
                >
                  <UFormField
                    :label="field.label"
                    :required="
                      !!(fieldStates[field.name]?.required ?? field.required)
                    "
                    :name="field.name"
                    :error="fieldErrors[field.name]"
                  >
                    <EntityFieldRenderer
                      :field="field"
                      v-model="formData[field.name]"
                      :loading="fetchFromLoading[field.name] === true"
                      :record-id="isNew ? undefined : recordId"
                      :disabled="
                        !isEditMode ||
                        field.readonly ||
                        (!isFormEditable && !isNew) ||
                        fieldStates[field.name]?.editable === false
                      "
                      :link-options="linkOptions"
                      :link-titles="linkTitles"
                      :on-load-link-options="loadLinkOptionsForField"
                      :entity-name="entityName"
                      :form-state="formData"
                      :link-field-permissions="
                        entityMeta?.link_field_permissions || {}
                      "
                      @update:model-value="
                        (val: any) => onFieldUpdate(field.name, val)
                      "
                    />
                  </UFormField>
                </div>
              </div>
            </UForm>

            <!-- Inline Child Tables (rendered in the form, not as tabs) -->
            <div v-if="entityMeta?.children?.length" class="mt-6">
              <div v-for="child in entityMeta.children" :key="child.entity">
                <USeparator
                  :label="getChildSectionLabel(child)"
                  size="lg"
                  class="mb-8"
                />
                <div class="px-1 h-[50vh]">
                  <EntityChildDataGrid
                    :ref="
                      (el: any) => {
                        if (el) childGridRefs[child.entity] = el;
                      }
                    "
                    :parent-entity="entityName"
                    :parent-id="recordId"
                    :child-entity="child.entity"
                    :fk-field="child.fk_field"
                    :child-meta="childEntityMeta[child.entity] || null"
                    :editable="isEditMode"
                    :can-add="isEditMode && canAddChildren"
                    :can-delete="isEditMode && canEdit"
                    :parent-form-data="formData"
                    @dirty-change="
                      (dirty: boolean) => {
                        childGridDirty[child.entity] = dirty;
                      }
                    "
                    @loading-change="
                      (isLoading: boolean) =>
                        handleChildGridLoading(isLoading, child.entity)
                    "
                    @save-complete="() => loadData()"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Attachments Tab -->
        <div
          v-else-if="item.value === 'attachments'"
          class="border rounded-lg border-accented mt-4 flex-1 min-h-0 flex flex-col overflow-hidden"
        >
          <!-- Toolbar -->
          <div
            class="flex items-center justify-between gap-2 p-4 border-b border-accented"
          >
            <div class="flex items-center gap-2">
              <UButton
                icon="i-lucide-upload"
                size="md"
                :loading="attachmentUploading"
                :disabled="attachmentUploading"
                @click="attachmentFileInput?.click()"
              >
                Upload File
              </UButton>
              <input
                ref="attachmentFileInput"
                type="file"
                multiple
                class="hidden"
                @change="handleAttachmentUpload"
              />
              <UButton
                icon="i-lucide-refresh-cw"
                variant="outline"
                size="md"
                :loading="attachmentsLoading"
                @click="loadAttachments"
              />
            </div>
            <span class="text-sm text-muted">
              {{ attachmentCount }}
              /
              {{ entityMeta?.attachment_config?.max_attachments || 10 }}
              files
            </span>
          </div>

          <!-- Attachment List -->
          <div
            v-if="attachmentsLoading"
            class="flex-1 min-h-0 flex justify-center py-8 overflow-y-auto pb-6"
          >
            <UIcon
              name="i-lucide-loader-2"
              class="animate-spin h-6 w-6 text-primary"
            />
          </div>

          <div
            v-else-if="attachments.length === 0"
            class="flex-1 min-h-0 text-center py-12 text-muted-foreground overflow-y-auto pb-6"
          >
            <UIcon name="i-lucide-paperclip" class="h-8 w-8 mx-auto mb-2" />
            <p class="text-sm">No attachments yet</p>
            <p class="text-xs mt-1">Click "Upload File" to add attachments</p>
          </div>

          <div
            v-else
            class="flex-1 min-h-0 divide-y divide-accented overflow-y-auto pb-6"
          >
            <div
              v-for="att in attachments"
              :key="att.id"
              class="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
            >
              <div class="flex items-center gap-3 min-w-0 flex-1">
                <UIcon
                  :name="
                    att.mime_type?.startsWith('image/')
                      ? 'i-lucide-image'
                      : att.mime_type === 'application/pdf'
                        ? 'i-lucide-file-text'
                        : 'i-lucide-file'
                  "
                  class="h-5 w-5 text-muted-foreground shrink-0"
                />
                <div class="min-w-0">
                  <div class="font-medium text-sm truncate">
                    {{ att.file_name }}
                  </div>
                  <div class="text-xs text-muted-foreground">
                    {{ formatFileSize(att.file_size) }}
                    <span v-if="att.uploaded_by">
                      · by {{ att.uploaded_by }}
                    </span>
                    <span v-if="att.created_at">
                      ·
                      {{
                        new Date(att.created_at).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })
                      }}
                    </span>
                  </div>
                </div>
              </div>
              <div class="flex items-center gap-1 shrink-0">
                <UButton
                  icon="i-lucide-download"
                  variant="ghost"
                  size="xs"
                  @click="handleDownloadAttachment(att)"
                />
                <UButton
                  icon="i-lucide-trash-2"
                  variant="ghost"
                  size="xs"
                  color="error"
                  @click="handleDeleteAttachment(att)"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Related Tab Panel -->
        <div
          v-else
          class="flex-1 min-h-0 flex flex-col overflow-hidden p-1 mt-2"
        >
          <!-- Header-Detail Related Table (UTable-based) -->
          <HeaderDetailRelatedTable
            v-if="isHeaderDetailTab(relatedMeta[(item as any).linkEntity])"
            :ref="
              (el: any) => {
                if (el) relatedTableRefs[(item as any).linkEntity] = el;
              }
            "
            :parent-entity="entityName"
            :parent-id="recordId"
            :child-entity="(item as any).linkEntity"
            :fk-field="(item as any).fkField"
            :child-meta="relatedMeta[(item as any).linkEntity] || null"
            :can-add="getLinkPermissions((item as any).linkEntity).can_create"
            :can-delete="
              getLinkPermissions((item as any).linkEntity).can_delete
            "
            @add-clicked="
              openHeaderDetailModal(
                (item as any).linkEntity,
                (item as any).fkField,
              )
            "
          />

          <!-- Standard Related Grid (NuGrid-based) -->
          <EntityRelatedDataGrid
            v-else
            :ref="
              (el: any) => {
                if (el) relatedGridRefs[(item as any).linkEntity] = el;
              }
            "
            :parent-entity="entityName"
            :parent-id="recordId"
            :child-entity="(item as any).linkEntity"
            :fk-field="(item as any).fkField"
            :child-meta="relatedMeta[(item as any).linkEntity] || null"
            :editable="getLinkPermissions((item as any).linkEntity).can_update"
            :can-add="getLinkPermissions((item as any).linkEntity).can_create"
            :can-delete="
              getLinkPermissions((item as any).linkEntity).can_delete
            "
            @action-result="handleRelatedGridActionResult"
          />
        </div>
      </template>
    </UTabs>
  </div>

  <!-- Serial Number Modal: shown after confirm_receipt for serialized items -->
  <SerialNumberModal
    :open="serialModalOpen"
    :inventory-ids="serialModalInventoryIds"
    :receipt-id="serialModalReceiptId"
    :entity-name="serialModalEntityName || entityName"
    @close="serialModalOpen = false"
    @submitted="onSerialNumbersSubmitted"
  />

  <!-- Header-Detail Modal: fullscreen create modal for header-detail entities -->
  <HeaderDetailModal
    v-model="headerDetailModalOpen"
    :entity="headerDetailModalEntity"
    :fk-field="headerDetailModalFkField"
    :parent-id="recordId"
    :parent-entity="entityName"
    :meta="headerDetailModalMeta"
    @created="handleHeaderDetailCreated"
  />

  <!-- Print Preview Modal -->
  <UModal
    v-model:open="showPrintPreview"
    :title="`${entityMeta?.label || entityName} — Print Preview`"
    :ui="{
      content: 'max-w-4xl w-full max-h-screen flex flex-col',
      body: 'flex-1 min-h-0 overflow-hidden',
      footer: 'shrink-0',
    }"
    scrollable
  >
    <template #body>
      <div
        class="h-full max-h-[calc(100vh-12rem)] overflow-y-auto overflow-x-hidden bg-[#e5e7eb] p-4 rounded"
      >
        <div v-if="printPreviewHtml" class="flex justify-center min-w-0">
          <div class="w-full max-w-[794px] bg-white shadow-md">
            <div
              style="
                position: relative;
                width: 100%;
                padding-top: calc(297 / 210 * 100%);
              "
            >
              <iframe
                ref="previewIframe"
                :srcdoc="printPreviewHtml"
                sandbox="allow-scripts allow-same-origin"
                class="border-0 block"
                style="
                  position: absolute;
                  top: 0;
                  left: 0;
                  width: 100%;
                  height: 100%;
                "
                @load="resizeIframe"
              />
            </div>
          </div>
        </div>
        <div v-else class="flex items-center justify-center py-16">
          <UIcon
            name="i-lucide-loader-2"
            class="animate-spin text-2xl text-gray-400"
          />
        </div>
      </div>
    </template>

    <template #footer>
      <div class="flex justify-end gap-2">
        <UButton variant="outline" @click="showPrintPreview = false">
          Close
        </UButton>
        <UButton
          icon="i-lucide-printer"
          variant="soft"
          @click="printFromPreview"
        >
          Print
        </UButton>
        <UButton
          icon="i-lucide-file-down"
          color="primary"
          :loading="printLoading"
          @click="downloadPdf(entityName, recordId)"
        >
          Download PDF
        </UButton>
      </div>
    </template>
  </UModal>
</template>
