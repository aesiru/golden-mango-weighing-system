<script setup lang="ts">
import { CalendarDate } from "@internationalized/date";
import type { NuGridColumn } from "#nu-grid/types";
import { LazyBlockingLoadingOverlay } from "#components";
import type {
  DocumentAction,
  EntityMeta,
  FieldMeta,
} from "~/composables/useApiTypes";
import { matchesCondition } from "~/composables/useFormState";
import { useAuthStore } from "~/stores/auth";

interface Props {
  parentEntity: string;
  parentId: string;
  childEntity: string;
  fkField: string;
  childMeta: EntityMeta | null;
  editable?: boolean;
  canAdd?: boolean;
  canDelete?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  editable: false,
  canAdd: false,
  canDelete: false,
});

const emit = defineEmits<{
  "loading-change": [isLoading: boolean];
  "refresh-needed": [];
  "action-result": [result: any];
}>();

const router = useRouter();
const cache = useCacheStore();
const {
  getEntityList,
  bulkSaveChildren,
  getEntityOptions,
  postEntityAction,
  postDocumentAction,
  getEntityMeta,
} = useApi();
const toast = useToast();
const deleteDialog = useDeleteDialog();
const confirmDialog = useConfirmDialog();
const overlay = useOverlay();

const gridRef = ref<any>(null);
const gridData = ref<Record<string, any>[]>([]);
const linkTitles = ref<Record<string, string>>({});
const loading = ref(false);
const initialLoaded = ref(false);
const metadataLoading = ref(false);
const childMetaFromApi = ref<EntityMeta | null>(null);
const dirty = ref(false);
const dirtyRows = ref<Set<string>>(new Set());
const deletedIds = ref<string[]>([]);
const total = ref(0);
const columnPinning = ref({ left: [] as string[], right: ["_actions"] });
const overlayBusy = ref(false);
const blockingOverlay = overlay.create(LazyBlockingLoadingOverlay, {
  destroyOnClose: false,
  props: {
    title: "Executing...",
  },
});

watch(loading, (val) => emit("loading-change", val));

// Lookup options management (same pattern as ChildDataGrid)
const lookupArrays: Record<string, any[]> = reactive({});
const lookupVersions: Record<string, number> = reactive({});
const lookupLabelCache: Record<string, Record<string, string>> = reactive({});
const linkFetchInFlight = new Set<string>();

const auth = useAuthStore();
const userPrefix = computed(() => auth.user?.id ? `user:${auth.user.id}:` : "");

const cachedMetaKey = computed(() => `${userPrefix.value}meta:entity:v2:${props.childEntity}`);

const resolvedChildMeta = computed<EntityMeta | null>(() => {
  if (props.childMeta) return props.childMeta;
  if (childMetaFromApi.value) return childMetaFromApi.value;
  const metaRaw = cache.getFromLocalStorage<any>(cachedMetaKey.value);
  return (metaRaw as any)?.data ?? metaRaw ?? null;
});
const gridFetchFrom = useGridFetchFrom(resolvedChildMeta, gridData);
const linkFilterResolver = useGridLinkFilterResolver(resolvedChildMeta, {
  gridRows: gridData,
});

const visibleRowActions = (rowData: Record<string, any>): DocumentAction[] => {
  const actions = resolvedChildMeta.value?.actions || [];
  return actions.filter((action: DocumentAction) => {
    if (!action?.action) return false;
    if (!action.show_when) return true;
    return matchesCondition(action.show_when, rowData, resolvedChildMeta.value);
  });
};

// Ensure metadata is available in localStorage
async function ensureMetadata(): Promise<void> {
  if (metadataLoading.value) {
    console.log(
      "[RelatedDataGrid] skip meta fetch: already loading",
      props.childEntity,
    );
    return;
  }

  // If parent already provided metadata, do nothing (page-level owns fetch)
  if (props.childMeta) {
    console.log(
      "[RelatedDataGrid] skip meta fetch: childMeta prop present",
      props.childEntity,
    );
    return;
  }

  // If cached locally, hydrate from cache and skip network
  const existingMeta = cache.getFromLocalStorage<any>(cachedMetaKey.value);
  if (existingMeta) {
    console.log("[RelatedDataGrid] hydrate meta from cache", props.childEntity);
    childMetaFromApi.value =
      (existingMeta as any)?.data ?? existingMeta ?? null;
    return;
  }

  metadataLoading.value = true;
  try {
    console.log("[RelatedDataGrid] fetch meta", props.childEntity);
    const metaRes = await getEntityMeta(props.childEntity);
    childMetaFromApi.value = metaRes.data;
  } catch (error) {
    console.error(
      "[RelatedDataGrid] failed to fetch meta",
      props.childEntity,
      error,
    );
  } finally {
    metadataLoading.value = false;
  }
}

function getColumnHeader(field: FieldMeta): string {
  const baseLabel = field.required
    ? `${field.label} *`
    : field.label || field.name;
  return field.readonly ? `${baseLabel} · 🔒` : baseLabel;
}

function getCachedSelectOptions(
  fieldName: string,
): Array<{ label: string; value: string }> {
  const metaRaw = cache.getFromLocalStorage<any>(cachedMetaKey.value);
  const meta = (metaRaw as any)?.data ?? metaRaw;
  const fields = (meta as any)?.fields || [];
  const f: any = fields.find((x: any) => x?.name === fieldName);
  const raw = f?.options;
  if (!Array.isArray(raw)) return [];
  const normalized = raw
    .map((o: any) => (typeof o === "string" ? { label: o, value: o } : o))
    .filter(Boolean)
    .map((o: any) => ({
      label:
        o?.label === null || o?.label === undefined
          ? String(o?.value)
          : String(o.label),
      value: o?.value === null || o?.value === undefined ? "" : String(o.value),
    }))
    .filter((o: any) => o.value !== "");

  return normalized;
}

const GridLinkEditor = defineComponent({
  name: "GridLinkEditor",
  props: {
    modelValue: { type: [String, Number, null] as any, default: null },
    cell: { type: null as any, required: false },
    row: { type: Object as any, required: false },
    entity: { type: String, required: true },
    disabled: { type: Boolean, default: false },
    labelKey: { type: String, default: "label" },
    valueKey: { type: String, default: "value" },
    linkFilter: {
      type: Object as () => Record<string, any> | null,
      default: null,
    },
    fieldName: { type: String, required: false, default: "" },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const searchTerm = ref("");
    const debounced = refDebounced(searchTerm, 250);
    const items = ref<any[]>([]);
    const loadingItems = ref(false);

    async function loadOptions(search?: string) {
      loadingItems.value = true;
      try {
        const rowData =
          (props.row as Record<string, any> | undefined) ??
          props.cell?.row?.original;
        const filters = await linkFilterResolver.resolveLinkFilters(
          props.linkFilter,
          rowData,
          props.fieldName,
        );
        const res = await getEntityOptions(
          props.entity,
          search || undefined,
          5,
          filters,
        );
        if (res.status === "success") {
          const opts = (res.options ?? []).map((o: any) => ({ ...o }));
          items.value = opts;
          if (!lookupLabelCache[props.entity])
            lookupLabelCache[props.entity] = {};
          const cache = lookupLabelCache[props.entity];
          for (const o of opts) {
            const v = o[props.valueKey];
            const l = o[props.labelKey];
            if (v !== undefined && l !== undefined && cache) {
              cache[String(v)] = String(l);
            }
          }
        } else {
          items.value = [];
        }
      } catch (e) {
        console.error("[GridLinkEditor] options fetch error", props.entity, e);
        items.value = [];
      } finally {
        loadingItems.value = false;
      }
    }

    function handleOpen(isOpen: boolean) {
      if (isOpen) {
        loadOptions("");
      }
    }

    watch(debounced, (term) => {
      if (term === undefined) return;
      loadOptions(term || "");
    });

    function update(val: any) {
      const rowData =
        (props.row as Record<string, any> | undefined) ??
        props.cell?.row?.original;
      const normalizedValue =
        val && typeof val === "object"
          ? (val[props.valueKey] ?? val.value ?? val)
          : val;
      const selectedItem = items.value.find(
        (item: any) =>
          String(item?.[props.valueKey] ?? item?.value) ===
          String(normalizedValue),
      );

      if (rowData && props.fieldName) {
        rowData[props.fieldName] = normalizedValue;
      }

      emit("update:modelValue", normalizedValue);
    }

    return () =>
      h(resolveComponent("USelectMenu") as any, {
        modelValue: props.modelValue,
        "onUpdate:modelValue": update,
        items: items.value,
        disabled: props.disabled,
        loading: loadingItems.value,
        ignoreFilter: true,
        labelKey: props.labelKey,
        valueKey: props.valueKey,
        searchable: true,
        class: "w-full",
        size: "md",
        "onUpdate:open": handleOpen,
        "onUpdate:searchTerm": (t: string) => {
          searchTerm.value = t || "";
        },
      });
  },
});

const GridDateEditor = defineComponent({
  name: "GridDateEditor",
  props: {
    modelValue: { type: String as any, default: null },
    disabled: { type: Boolean, default: false },
    withTime: { type: Boolean, default: false },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const inputDateRef = useTemplateRef("inputDateRef");

    const calValue = computed({
      get() {
        if (!props.modelValue) return undefined;
        try {
          const d = new Date(props.modelValue);
          return new CalendarDate(
            d.getFullYear(),
            d.getMonth() + 1,
            d.getDate(),
          );
        } catch {
          return undefined;
        }
      },
      set(val: any) {
        if (!val) {
          emit("update:modelValue", null);
          return;
        }
        const iso = props.withTime
          ? new Date(val.year, val.month - 1, val.day).toISOString()
          : `${String(val.year)}-${String(val.month).padStart(2, "0")}-${String(val.day).padStart(2, "0")}`;
        emit("update:modelValue", iso);
      },
    });

    return () =>
      h(
        resolveComponent("UInputDate") as any,
        {
          ref: "inputDateRef",
          modelValue: calValue.value,
          "onUpdate:modelValue": (v: any) => {
            calValue.value = v;
          },
          disabled: props.disabled,
          class: "w-full",
        },
        {
          trailing: () =>
            h(
              resolveComponent("UPopover") as any,
              {
                reference: (inputDateRef as any)?.value?.inputsRef?.[3]?.$el,
              },
              {
                default: () =>
                  h(resolveComponent("UButton") as any, {
                    color: "neutral",
                    variant: "link",
                    size: "sm",
                    icon: "i-lucide-calendar",
                    "aria-label": "Select a date",
                    class: "px-0",
                  }),
                content: () =>
                  h(resolveComponent("UCalendar") as any, {
                    modelValue: calValue.value,
                    "onUpdate:modelValue": (v: any) => {
                      calValue.value = v;
                    },
                    class: "p-2",
                  }),
              },
            ),
        },
      );
  },
});

const GridSelectEditor = defineComponent({
  name: "GridSelectEditor",
  props: {
    modelValue: { type: [String, Number, null] as any, default: null },
    fieldName: { type: String, required: true },
    disabled: { type: Boolean, default: false },
  },
  emits: ["update:modelValue"],
  setup(p, { emit }) {
    const searchTerm = ref("");

    const items = computed(() => {
      const metaRaw = cache.getFromLocalStorage<any>(cachedMetaKey.value);
      const meta = (metaRaw as any)?.data ?? metaRaw;
      const fields = (meta as any)?.fields || [];
      const field = fields.find((f: any) => f?.name === p.fieldName);
      const raw = (field as any)?.options;
      const opts = Array.isArray(raw)
        ? raw.map((o: any) =>
            typeof o === "string" ? { label: o, value: o } : o,
          )
        : [];

      const normalized = opts
        .filter(Boolean)
        .map((o: any) => ({
          ...o,
          value:
            o?.value === null || o?.value === undefined ? "" : String(o.value),
          label:
            o?.label === null || o?.label === undefined
              ? String(o?.value)
              : String(o.label),
        }))
        .filter((o: any) => o.value !== "");

      const term = (searchTerm.value || "").toLowerCase();
      if (!term) return normalized;
      return normalized.filter((o: any) =>
        String(o?.label || "")
          .toLowerCase()
          .includes(term),
      );
    });

    function update(val: any) {
      emit("update:modelValue", val);
    }

    const displayValue = computed(() => {
      if (p.modelValue === null || p.modelValue === undefined) return null;
      const stringValue = String(p.modelValue);
      const option = items.value.find(
        (o: any) =>
          String(o.value) === stringValue || String(o.label) === stringValue,
      );
      return option ? option.value : stringValue;
    });

    return () =>
      h(resolveComponent("USelectMenu") as any, {
        modelValue: displayValue.value,
        "onUpdate:modelValue": (selected: any) => {
          const selectedOption = items.value.find(
            (o: any) => String(o.value) === String(selected),
          );
          update(selectedOption?.label ?? selected);
        },
        items: items.value,
        disabled: p.disabled,
        searchable: true,
        ignoreFilter: true,
        valueKey: "value",
        labelKey: "label",
        class: "w-full",
        size: "md",
        "onUpdate:searchTerm": (t: string) => {
          searchTerm.value = t || "";
        },
      });
  },
});

function ensureLookupArray(entity: string): any[] {
  if (!lookupArrays[entity]) lookupArrays[entity] = [];
  if (lookupVersions[entity] === undefined) lookupVersions[entity] = 0;
  return lookupArrays[entity];
}

async function fetchLookupOptions(entity: string): Promise<void> {
  if (linkFetchInFlight.has(entity)) return;
  if (lookupArrays[entity]?.length) return;
  linkFetchInFlight.add(entity);
  try {
    const res = await getEntityOptions(entity, undefined, 5);
    if (res.status === "success") {
      const arr = ensureLookupArray(entity);
      arr.splice(0, arr.length, ...(res.options ?? []));
      lookupVersions[entity] = (lookupVersions[entity] ?? 0) + 1;
    }
  } catch (err) {
    console.error(`[RelatedDataGrid] fetch failed for "${entity}":`, err);
  } finally {
    linkFetchInFlight.delete(entity);
  }
}

async function cancelDirtyChanges(): Promise<void> {
  overlayBusy.value = true;
  try {
    dirty.value = false;
    dirtyRows.value.clear();
    deletedIds.value = [];
    await loadData();
  } finally {
    overlayBusy.value = false;
  }
}

// Visible fields — sorted so editable fields come first, readonly at end
const childFields = computed<FieldMeta[]>(() => {
  if (!props.childMeta?.fields) {
    // If no props metadata, try to get from cache
    const metaRaw = cache.getFromLocalStorage<any>(cachedMetaKey.value);
    const meta = (metaRaw as any)?.data ?? metaRaw;
    if (!meta?.fields) return [];

    // Use cached metadata - show if in_list_view OR required
    const fields = meta.fields.filter(
      (f: FieldMeta) => f.in_list_view || f.required,
    );
    if (fields.length === 0) {
      return meta.fields
        .filter((f: FieldMeta) => !f.hidden && f.name !== "id")
        .slice(0, 6);
    }
    return fields.filter((f: FieldMeta) => {
      if (["id", "created_at", "updated_at"].includes(f.name)) return false;
      if (f.name === props.fkField) return false;
      return true;
    });
  }

  // Use props metadata if available - show if in_list_view OR required
  let fields = props.childMeta.fields.filter(
    (f) => f.in_list_view || f.required,
  );
  if (fields.length === 0) {
    fields = props.childMeta.fields
      .filter((f) => !f.hidden && f.name !== "id")
      .slice(0, 6);
  }

  const filtered = fields.filter((f) => {
    if (["id", "created_at", "updated_at"].includes(f.name)) return false;
    if (f.name === props.fkField) return false;
    return true;
  });

  // Sort: editable fields first, then readonly fields, workflow_state always last
  return [...filtered].sort((a, b) => {
    // workflow_state always goes last
    if (a.name === "workflow_state" && b.name !== "workflow_state") return 1;
    if (b.name === "workflow_state" && a.name !== "workflow_state") return -1;
    // Then editable fields first, then readonly
    if (a.readonly && !b.readonly) return 1;
    if (!a.readonly && b.readonly) return -1;
    return 0;
  });
});

function getColumnSize(field: FieldMeta): number {
  switch (field.field_type) {
    case "link":
      return 280;
    case "text":
      return 240;
    case "int":
    case "integer":
      return 100;
    case "float":
      return 120;
    case "boolean":
      return 90;
    case "date":
      return 140;
    case "datetime":
      return 180;
    default:
      return 160;
  }
}

// Columns
const columns = computed<NuGridColumn<Record<string, any>>[]>(() => {
  const cols: NuGridColumn<Record<string, any>>[] = [];

  // Row-number column
  cols.push({
    accessorKey: "__item_no",
    header: "#",
    size: 50,
    minSize: 50,
    maxSize: 50,
    enableEditing: false,
    enableSorting: false,
    enableResizing: false,
    enableHiding: false,
    enableFocusing: false,
    cell: ({ row }: { row: { original: Record<string, any> } }) => {
      const idx = gridData.value.findIndex((r) => r.id === row.original.id);
      return idx >= 0 ? idx + 1 : "";
    },
  } as NuGridColumn<Record<string, any>>);

  for (const field of childFields.value) {
    const col: any = {
      accessorKey: field.name,
      header:
        field.name === "workflow_state" ? "Status" : getColumnHeader(field),
      size: getColumnSize(field),
      enableEditing: (row: { original: Record<string, any> }) => {
        if (field.readonly) return false;
        const isNewRow = String(row.original?.id).startsWith("__new__");
        return isNewRow ? props.canAdd : props.editable;
      },
      enableSorting: false,
      enableResizing: true,
      enableHiding: false,
    };

    const ft = field.field_type;

    if (ft === "boolean") {
      col.cellDataType = "boolean";
    } else if (ft === "date" || ft === "datetime") {
      col.cellDataType = "text";
      col.cell = ({ row }: { row: { original: Record<string, any> } }) => {
        const v = row.original[field.name];
        if (!v) return "";
        const d = new Date(v);
        return ft === "datetime" ? d.toLocaleString() : d.toLocaleDateString();
      };
      col.editor = {
        component: GridDateEditor,
        props: {
          withTime: ft === "datetime",
        },
      };
    } else if (["int", "integer", "float", "number"].includes(ft)) {
      col.cellDataType = "number";
    } else if (ft === "select") {
      // Force plain-text rendering with custom editor.
      // NuGrid's built-in selection renderer can appear as a checkbox.
      col.cellDataType = "text";
      const rawOptions =
        Array.isArray(field.options) && field.options.length
          ? field.options
          : getCachedSelectOptions(field.name);
      const selectOptions = rawOptions.map((o: any) =>
        typeof o === "string" ? { label: o, value: o } : o,
      );
      col.cell = ({ row }: { row: { original: Record<string, any> } }) => {
        const v = row.original[field.name];
        if (v === null || v === undefined || v === "") return "";
        return String(v);
      };
      col.editor = {
        component: GridSelectEditor,
        props: {
          fieldName: field.name,
        },
      };
    } else if (ft === "link" && field.link_entity) {
      const entity = field.link_entity;
      col.cellDataType = "text";
      col.cell = ({ row }: { row: { original: Record<string, any> } }) => {
        const v = row.original[field.name];
        if (!v) return "";
        const key = `${entity}::${v}`;
        const cachedLabel = lookupLabelCache[entity]?.[String(v)];
        return linkTitles.value[key] ?? cachedLabel ?? v;
      };
      col.editor = {
        component: GridLinkEditor,
        props: {
          entity,
          fieldName: field.name,
          labelKey: "label",
          valueKey: "value",
          linkFilter: field.link_filter ?? null,
          limit: 5,
        },
      };
    } else {
      col.cellDataType = "text";
    }

    cols.push(col as NuGridColumn<Record<string, any>>);
  }

  // Row action menu column
  cols.push({
    accessorKey: "_actions",
    header: "",
    size: 48,
    minSize: 48,
    maxSize: 48,
    enableEditing: false,
    enableSorting: false,
    enableResizing: false,
    enableHiding: false,
    enableFocusing: false,
    cell: ({ row }: { row: { original: Record<string, any> } }) => {
      const items: any[] = [];
      const isNewRow = String(row.original.id).startsWith("__new__");

      if (!isNewRow) {
        const entityActions = visibleRowActions(row.original).map(
          (action: DocumentAction) => ({
            label: action.label,
            icon: "i-lucide-play",
            onSelect: () => executeRowAction(row.original, action),
          }),
        );

        if (entityActions.length) {
          items.push(...entityActions);
          items.push({
            type: "separator",
          });
        }

        items.push({
          label: "View Details",
          icon: "i-lucide-external-link",
          onSelect: () => {
            router.push(`/${props.childEntity}/${row.original.id}`);
          },
        });
      }

      if (!isNewRow && props.canDelete) {
        items.push({
          label: "Delete",
          icon: "i-lucide-trash-2",
          color: "error",
          onSelect: () => handleDeleteRow(row.original),
        });
      }

      return h("div", { class: "flex items-center justify-center" }, [
        h(
          resolveComponent("UDropdownMenu"),
          {
            items: [items],
          },
          {
            default: () =>
              h(resolveComponent("UButton"), {
                icon: "i-lucide-ellipsis-vertical",
                variant: "outline",
                color: "gray",
                size: "md",
                "aria-label": "Actions",
              }),
          },
        ),
      ]);
    },
  } as NuGridColumn<Record<string, any>>);

  return cols;
});

// NuGrid events — options are loaded only when the editor dropdown opens
function onCellEditingStarted(event: any): void {
  // Intentionally no option prefetch here.
  // Lookup options are fetched by GridLinkEditor only when the USelectMenu opens.
}

async function onCellValueChanged(event: any): Promise<void> {
  if (!event.row?.original || !event.column?.id) return;
  const rowId = String(event.row.original.id);
  const fieldName = String(event.column.id);
  const newValue = event.newValue;

  event.row.original[fieldName] = newValue;
  dirtyRows.value.add(rowId);
  dirty.value = true;

  // Apply fetch_from rules if this field is a source
  if (gridFetchFrom.isFetchFromSource(fieldName)) {
    console.info(
      "[RelatedDataGrid] fetch_from source change",
      fieldName,
      "value",
      newValue,
      "row",
      rowId,
    );
    const res = await gridFetchFrom.applyForRow(rowId, fieldName, newValue);
    console.info("[RelatedDataGrid] fetch_from result", fieldName, res);
    if (res?.linkTitles && Object.keys(res.linkTitles).length) {
      linkTitles.value = { ...linkTitles.value, ...res.linkTitles };
      for (const [key, label] of Object.entries(res.linkTitles)) {
        const [entityKey, value] = key.split("::");
        if (!entityKey || !value) continue;
        if (!lookupLabelCache[entityKey]) lookupLabelCache[entityKey] = {};
        lookupLabelCache[entityKey][value] = String(label ?? value);
      }
    }
  }
}

async function executeRowAction(
  rowData: Record<string, any>,
  action: DocumentAction,
): Promise<void> {
  if (!rowData?.id || String(rowData.id).startsWith("__new__")) return;

  if (action.confirm) {
    const confirmed = await confirmDialog({
      title: "Confirm Action",
      description: action.confirm,
      confirmLabel: "Proceed",
    });
    if (!confirmed) return;
  }

  try {
    const res = await postDocumentAction(
      props.childEntity,
      rowData.id,
      action.action,
    );
    if (res.status === "success") {
      const nested = (res as any).data;
      emit(
        "action-result",
        nested
          ? {
              ...nested,
              _sourceEntity: props.childEntity,
              _sourceId: String(rowData.id),
            }
          : null,
      );

      if (res.message) {
        toast.add({
          title: res.message,
          color: "success",
          type: "foreground",
        });
      }
      emit("refresh-needed");
      await loadData();
    } else if (res.message) {
      toast.add({ title: res.message, color: "error", type: "foreground" });
    }
  } catch (err: any) {
    if (err?.message) {
      toast.add({ title: err.message, color: "error", type: "foreground" });
    }
  }
}

// Delete handler — kept outside render function to avoid inject() context loss
async function handleDeleteRow(rowData: Record<string, any>): Promise<void> {
  const isNewRow = String(rowData.id).startsWith("__new__");
  if (isNewRow) {
    const idx = gridData.value.findIndex((r) => r.id === rowData.id);
    if (idx >= 0) gridData.value.splice(idx, 1);
    dirty.value = true;
    return;
  }

  const confirmed = await deleteDialog({
    entityName: props.childMeta?.label || props.childEntity,
    itemName: String(rowData.id),
  });
  if (!confirmed) return;

  try {
    const res = await postEntityAction(props.childEntity, {
      action: "delete",
      id: rowData.id,
    });
    if (res.status === "success") {
      if (res.message) {
        toast.add({ title: res.message, color: "success", type: "foreground" });
      }
      await loadData();
    } else {
      if (res.message) {
        const toastOptions: any = {
          title: h("span", { innerHTML: res.message }),
          color: "error",
          type: "foreground",
        };

        // Add clickable actions for referencing records
        const referencingRecords = res.data?.referencing_records;
        if (referencingRecords && referencingRecords.length > 0) {
          toastOptions.actions = referencingRecords
            .slice(0, 3)
            .map((ref: any) => ({
              label: `View ${ref.entity_display}`,
              to: `/${ref.entity}/${ref.id}`,
            }));
        }

        toast.add(toastOptions);
      }
    }
  } catch (err: any) {
    if (err?.message) {
      const toastOptions: any = {
        title: h("span", { innerHTML: err.message }),
        color: "error",
        type: "foreground",
      };

      // Add clickable actions for referencing records
      const referencingRecords = err?.data?.referencing_records;
      if (referencingRecords && referencingRecords.length > 0) {
        toastOptions.actions = referencingRecords
          .slice(0, 3)
          .map((ref: any) => ({
            label: `View ${ref.entity_display}`,
            to: `/${ref.entity}/${ref.id}`,
          }));
      }

      toast.add(toastOptions);
    }
  }
}

// Data loading
async function loadData(): Promise<void> {
  if (!props.parentId || props.parentId === "new") return;
  loading.value = true;
  try {
    // Backend enforces page_size <= 100; use 100-chunk paging for virtualization fetch
    const pageSize = 100;
    let currentPage = 1;
    let accumulatedRows: Record<string, any>[] = [];
    let fetchedTotal = 0;

    while (true) {
      const res = await getEntityList(props.childEntity, {
        page: currentPage,
        pageSize,
        filterField: props.fkField,
        filterValue: props.parentId,
      });

      if (res.status !== "success") {
        break;
      }

      const rows = (res.data ?? []).map((r: any) => ({ ...r }));
      accumulatedRows = accumulatedRows.concat(rows);
      fetchedTotal = Number(res.total || accumulatedRows.length);

      if (rows.length === 0 || accumulatedRows.length >= fetchedTotal) {
        break;
      }

      currentPage += 1;
    }

    gridData.value = accumulatedRows;
    total.value = fetchedTotal || accumulatedRows.length;

    const linkTitlesData: Record<string, string> = {};
    for (const row of gridData.value) {
      const perRow = (row as any)?._link_titles;
      if (perRow && typeof perRow === "object") {
        Object.assign(linkTitlesData, perRow as Record<string, string>);
      }
    }
    linkTitles.value = linkTitlesData;

    // Seed label cache
    for (const [key, label] of Object.entries(
      linkTitlesData as Record<string, unknown>,
    )) {
      const [entityKey, value] = key.split("::");
      if (!entityKey || !value) continue;
      if (!lookupLabelCache[entityKey]) lookupLabelCache[entityKey] = {};
      lookupLabelCache[entityKey][value] = String(label ?? value);
    }
  } catch (err) {
    console.error("[RelatedDataGrid] load failed:", err);
  } finally {
    loading.value = false;
    // Safety: ensure blocking overlay never stays open after data load
    overlayBusy.value = false;
  }
}

// Create an empty row for inline adding
function createEmptyRow(): Record<string, any> {
  const row: Record<string, any> = {
    id: `__new__${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    [props.fkField]: props.parentId,
  };
  for (const field of childFields.value) {
    if (field.name === props.fkField) continue;
    row[field.name] = field.default ?? null;
  }
  return row;
}

function addRow(): void {
  gridData.value.push(createEmptyRow());
  dirty.value = true;
}

// Save dirty rows + new rows
async function saveDirtyRows(): Promise<void> {
  if (!dirty.value) return;

  // Collect new rows and changed existing rows
  const rowsToSave = gridData.value.filter((r) => {
    const id = String(r.id);
    return id.startsWith("__new__") || dirtyRows.value.has(id);
  });
  if (rowsToSave.length === 0 && deletedIds.value.length === 0) return;

  loading.value = true;
  overlayBusy.value = true;
  try {
    const res = await bulkSaveChildren(
      props.parentEntity,
      props.parentId,
      props.childEntity,
      rowsToSave,
      deletedIds.value,
    );
    if (res.status === "success") {
      dirty.value = false;
      dirtyRows.value.clear();
      deletedIds.value = [];
      if (res.message) {
        toast.add({
          title: res.message,
          color: "success",
          type: "foreground",
        });
      }
      // Refetch to get computed/readonly fields updated by post-save hooks
      await loadData();
    } else {
      if (res.message) {
        toast.add({
          title: res.message,
          color: "error",
          type: "foreground",
        });
      }
    }
  } catch (err: any) {
    console.error("[RelatedDataGrid] save failed:", err);
    if (err?.message) {
      toast.add({
        title: err.message,
        color: "error",
        type: "foreground",
      });
    }
  } finally {
    loading.value = false;
    overlayBusy.value = false;
  }
}

// Expose methods
defineExpose({ loadData, saveDirtyRows, addRow });

// Watch for child entity changes and ensure metadata is loaded
watch(
  () => props.childEntity,
  async (newChildEntity) => {
    if (newChildEntity) {
      childMetaFromApi.value = null;
      await ensureMetadata();
    }
  },
  { immediate: true },
);

// Watch for parent/child changes
watch(
  () => [props.parentId, props.childEntity, props.fkField] as const,
  async ([parentId, childEntity, fkField]) => {
    if (parentId && parentId !== "new" && childEntity && fkField) {
      await ensureMetadata();
      loadData().then(() => {
        initialLoaded.value = true;
      });
    }
  },
  { immediate: true },
);

watch(overlayBusy, (isOpen) => {
  if (isOpen) {
    blockingOverlay.open();
  } else {
    blockingOverlay.close();
  }
});

onUnmounted(() => {
  blockingOverlay.close();
});
// Auto-save on tab blur
</script>

<template>
  <div class="flex flex-1 min-h-0 flex-col">
    <div
      class="flex flex-wrap items-center gap-2 px-5 py-4.5 border border-muted rounded-t-lg"
    >
      <UButton
        v-if="canAdd && !loading && !metadataLoading"
        icon="i-lucide-plus"
        size="md"
        @click="addRow"
      >
        Add Record
      </UButton>
      <USkeleton v-else-if="canAdd" class="h-8 w-28" />
      <UButton
        variant="outline"
        icon="i-lucide-refresh-cw"
        :loading="loading"
        @click="loadData"
      />
      <div class="ml-auto flex items-center gap-2">
        <UChip v-if="dirty" variant="neutral" color="warning">
          <UButton
            v-if="dirty"
            icon="i-lucide-save"
            size="md"
            variant="soft"
            color="primary"
            :loading="loading"
            @click="saveDirtyRows"
          >
            Save
          </UButton>
        </UChip>
        <UButton
          v-if="dirty"
          icon="i-lucide-x"
          size="md"
          variant="outline"
          :loading="loading"
          @click="cancelDirtyChanges"
        />
      </div>
    </div>

    <div
      class="flex-1 min-h-0 flex flex-col border-l border-r border-b border-muted rounded-b-lg"
    >
      <!-- Initial loading state (content only) -->
      <div
        v-if="metadataLoading || (loading && !initialLoaded)"
        class="flex items-center justify-center"
      >
        <div class="w-full px-4 mt-4 space-y-2">
          <USkeleton class="h-4" />
          <USkeleton class="h-16" />
          <USkeleton class="h-16" />
          <USkeleton class="h-16" />
        </div>
      </div>

      <template v-else>
        <!-- Empty state -->
        <div
          v-if="gridData.length === 0 && !loading"
          class="flex items-center justify-center h-full"
        >
          <UEmpty
            variant="naked"
            icon="i-lucide-bell"
            title="No records found."
            description="Create a record to show data."
          />
        </div>

        <!-- Grid -->
        <div v-if="gridData.length > 0" class="flex-1 min-h-0 overflow-x-auto">
          <div class="w-full h-full">
            <NuGrid
              ref="gridRef"
              v-model:column-pinning="columnPinning"
              :data="gridData"
              :columns="columns"
              :tooltip="{
                truncatedOnly: true,
                showDelay: 500,
              }"
              virtualization
              :estimated-row-height="44"
              :get-row-id="(row: Record<string, any>) => String(row.id)"
              :layout="{
                autoSize: 'fill',
                resizeMode: 'shift',
              }"
              :editing="
                (editable || canAdd)
                  ? {
                      enabled: true,
                      startClicks: 'double',
                      startKeys: ['enter', 'f2'],
                    }
                  : { enabled: false }
              "
              :focus="{ mode: 'cell' }"
              :column-defaults="{
                resize: true,
                reorder: false,
                wrapText: false,
                menu: undefined,
              }"
              @cell-editing-started="onCellEditingStarted"
              @cell-value-changed="onCellValueChanged"
              :ui="{
                root: 'w-full h-full',
                base: 'w-full h-full',
              }"
            />
          </div>
        </div>

        <div class="border-t border-default py-3.5 px-4">
          <div class="text-sm text-muted">
            Showing {{ gridData.length }} of {{ total }}.
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
