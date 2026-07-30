<script setup lang="ts">
import { CalendarDate } from "@internationalized/date";
import type { NuGridColumn } from "#nu-grid/types";
import type { EntityMeta, FieldMeta } from "~/composables/useApiTypes";
import { evaluateDependsOn } from "~/composables/useFormState";
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
  parentFormData?: Record<string, any>;
}

const props = withDefaults(defineProps<Props>(), {
  editable: false,
  canAdd: false,
  canDelete: false,
  parentFormData: () => ({}),
});

const emit = defineEmits<{
  "dirty-change": [isDirty: boolean];
  "save-complete": [];
  "loading-change": [isLoading: boolean];
}>();

const router = useRouter();
const cache = useCacheStore();
const { getChildRecords, bulkSaveChildren, getEntityOptions } = useApi();

const gridRef = ref<any>(null);
const gridData = ref<Record<string, any>[]>([]);
const linkTitles = ref<Record<string, string>>({});
const loading = ref(false);
const dirty = ref(false);
const deletedIds = ref<string[]>([]);
const columnPinning = ref<any>({ left: ["__item_no"], right: ["_actions"] });
const columnVisibilityState = ref<Record<string, boolean>>({});

// Create a reactive reference to parentFormData for proper deep reactivity
const parentFormDataRef = toRef(props, "parentFormData");

// Track only issue_type to avoid deep-watching the entire parent form object.
// A deep watch fires on every parent field edit which can interrupt NuGrid's
// editor commit cycle and discard the in-progress cell value.
const parentIssueType = computed(() => parentFormDataRef.value?.issue_type);

// When the parent's issue_type changes on an *existing* record, clear child lines
// so the grid reloads for the new type.  Skip this when parentId is "new" — the
// user is still filling in the form and we must not destroy their edits.
watch(
  parentIssueType,
  (nextIssueType, prevIssueType) => {
    if (prevIssueType !== nextIssueType) {
      if (props.parentId !== "new" && gridData.value.length) {
        gridData.value = [];
        deletedIds.value = [];
        dirty.value = false;
      }
    }
  },
  { immediate: true },
);

const auth = useAuthStore();
const userPrefix = computed(() => auth.user?.id ? `user:${auth.user.id}:` : "");
const childMeta = computed(() => props.childMeta);
const cachedMetaKey = computed(() => `${userPrefix.value}meta:entity:v2:${props.childEntity}`);
const gridFetchFrom = useGridFetchFrom(childMeta, gridData);
const linkFilterResolver = useGridLinkFilterResolver(childMeta, {
  parentFormData: parentFormDataRef,
  gridRows: gridData,
});

watch(dirty, (val) => emit("dirty-change", val));
watch(loading, (val) => emit("loading-change", val));

// ── Lookup options ────────────────────────────────────────────────────────────
// Plain reactive arrays, one per entity. These are passed directly into
// cellDataTypeOptions.options in the column defs. When options arrive we
// splice() into the same array — Vue's proxy propagates the mutation to
// NuGrid's dropdown without touching the column definitions at all, so the
// columns computed never re-runs and the grid never remounts.

const lookupArrays: Record<string, any[]> = reactive({});
const lookupVersions: Record<string, number> = reactive({});
const lookupLabelCache: Record<string, Record<string, string>> = reactive({});
const linkFetchInFlight = new Set<string>();

// Important: this custom editor keeps the original on-open option loading and
// label rendering behavior, but now also emits NuGrid's editor lifecycle events.
// That explicit stop-editing path is what makes link selections commit reliably
// inside HeaderDetailModal, where the old editor would emit a value but never
// finalize the edit session.
const GridLinkEditor = defineComponent({
  name: "GridLinkEditor",
  props: {
    modelValue: { type: [String, Number, null] as any, default: null },
    cell: { type: null as any, required: false },
    row: { type: Object as any, required: false },
    isNavigating: { type: Boolean, default: false },
    shouldFocus: { type: Boolean, default: false },
    interactionRouter: { type: Object as any, required: false },
    entity: { type: String, required: true },
    disabled: { type: Boolean, default: false },
    labelKey: { type: String, default: "label" },
    valueKey: { type: String, default: "value" },
    linkFilter: {
      type: Object as () => Record<string, any> | null,
      default: null,
    },
    fieldName: { type: String, required: false, default: "" },
    parentFormData: {
      type: Object as () => Record<string, any>,
      default: () => ({}),
    },
  },
  emits: [
    "update:modelValue",
    "stop-editing",
    "cancel-editing",
    "update:isNavigating",
  ],
  setup(props, { emit }) {
    const searchTerm = ref("");
    const debounced = refDebounced(searchTerm, 250);
    const items = ref<any[]>([]);
    const loadingItems = ref(false);
    const containerRef = ref<HTMLElement | null>(null);
    const isOpen = ref(false);
    const valueJustChanged = ref(false);

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

    function focusTrigger() {
      nextTick(() => {
        const trigger = containerRef.value?.querySelector(
          "button, [tabindex]",
        ) as HTMLElement | null;
        trigger?.focus?.({ preventScroll: true });
      });
    }

    function handleOpen(open: boolean) {
      isOpen.value = open;
      if (open) {
        loadOptions("");
      } else if (!valueJustChanged.value) {
        setTimeout(() => emit("stop-editing"), 0);
      }
    }

    watch(debounced, (term) => {
      if (term === undefined) return;
      loadOptions(term || "");
    });

    watch(
      () => props.shouldFocus,
      (shouldFocus) => {
        if (shouldFocus) focusTrigger();
      },
      { immediate: true },
    );

    onMounted(() => {
      if (props.shouldFocus) focusTrigger();
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

      valueJustChanged.value = true;
      emit("update:modelValue", normalizedValue);
      setTimeout(() => {
        valueJustChanged.value = false;
        emit("stop-editing");
      }, 0);
    }

    function onKeydown(e: KeyboardEvent) {
      e.stopPropagation();
      if (e.key === "Escape") {
        e.preventDefault();
        emit("cancel-editing");
        return;
      }
      if (e.key === "Tab") {
        e.preventDefault();
        emit("update:isNavigating", true);
        emit("stop-editing", e.shiftKey ? "previous" : "next");
        return;
      }
      if (e.key === "Enter" && !isOpen.value) {
        e.preventDefault();
        emit("stop-editing");
      }
    }

    return () =>
      h("div", { ref: containerRef, class: "w-full" }, [
        h(resolveComponent("USelectMenu") as any, {
          modelValue: props.modelValue,
          open: isOpen.value,
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
          onKeydown,
        }),
      ]);
  },
});

const GridDateEditor = defineComponent({
  name: "GridDateEditor",
  props: {
    modelValue: { type: String as any, default: null },
    disabled: { type: Boolean, default: false },
    withTime: { type: Boolean, default: false },
  },
  emits: ["update:modelValue", "stop-editing"],
  setup(props, { emit }) {
    const inputDateRef = useTemplateRef("inputDateRef");

    function commitValue(value: string | null) {
      emit("update:modelValue", value);
      setTimeout(() => {
        emit("stop-editing");
      }, 0);
    }

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
          commitValue(null);
          return;
        }
        const iso = props.withTime
          ? new Date(val.year, val.month - 1, val.day).toISOString()
          : `${String(val.year)}-${String(val.month).padStart(2, "0")}-${String(val.day).padStart(2, "0")}`;
        commitValue(iso);
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
    shouldFocus: { type: Boolean, default: false },
  },
  emits: ["update:modelValue", "stop-editing", "cancel-editing"],
  setup(p, { emit }) {
    const searchTerm = ref("");
    const containerRef = ref<HTMLElement | null>(null);
    const isOpen = ref(false);
    const valueJustChanged = ref(false);

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

    function focusTrigger() {
      nextTick(() => {
        const trigger = containerRef.value?.querySelector(
          "button, [tabindex]",
        ) as HTMLElement | null;
        trigger?.focus?.({ preventScroll: true });
      });
    }

    function handleOpen(open: boolean) {
      isOpen.value = open;
      if (!open && !valueJustChanged.value) {
        setTimeout(() => emit("stop-editing"), 0);
      }
    }

    watch(
      () => p.shouldFocus,
      (shouldFocus) => {
        if (shouldFocus) focusTrigger();
      },
      { immediate: true },
    );

    onMounted(() => {
      if (p.shouldFocus) focusTrigger();
    });

    function update(val: any) {
      valueJustChanged.value = true;
      emit("update:modelValue", val);
      setTimeout(() => {
        valueJustChanged.value = false;
        emit("stop-editing");
      }, 0);
    }

    function onKeydown(e: KeyboardEvent) {
      e.stopPropagation();
      if (e.key === "Escape") {
        e.preventDefault();
        emit("cancel-editing");
        return;
      }
      if (e.key === "Enter" && !isOpen.value) {
        e.preventDefault();
        emit("stop-editing");
      }
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
      h("div", { ref: containerRef, class: "w-full" }, [
        h(resolveComponent("USelectMenu") as any, {
          modelValue: displayValue.value,
          open: isOpen.value,
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
          "onUpdate:open": handleOpen,
          "onUpdate:searchTerm": (t: string) => {
            searchTerm.value = t || "";
          },
          onKeydown,
        }),
      ]);
  },
});

function ensureLookupArray(entity: string): any[] {
  if (!lookupArrays[entity]) lookupArrays[entity] = [];
  if (lookupVersions[entity] === undefined) lookupVersions[entity] = 0;
  return lookupArrays[entity];
}

async function loadLookupItems(
  entity: string,
  linkFilter?: Record<string, any> | null,
  rowData?: Record<string, any>,
): Promise<any[]> {
  const filters = await linkFilterResolver.resolveLinkFilters(
    linkFilter,
    rowData,
    entity,
  );
  const res = await getEntityOptions(entity, undefined, 200, filters);
  if (res.status !== "success") return [];

  const opts = (res.options ?? []).map((o: any) => ({ ...o }));
  const arr = ensureLookupArray(entity);
  arr.splice(0, arr.length, ...opts);
  lookupVersions[entity] = (lookupVersions[entity] ?? 0) + 1;

  if (!lookupLabelCache[entity]) lookupLabelCache[entity] = {};
  const cache = lookupLabelCache[entity];
  for (const o of opts) {
    const v = o.value;
    const l = o.label;
    if (v !== undefined && l !== undefined && cache) {
      cache[String(v)] = String(l);
    }
  }

  return opts;
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
    console.error(`[ChildDataGrid] fetch failed for "${entity}":`, err);
  } finally {
    linkFetchInFlight.delete(entity);
  }
}

function getColumnHeader(field: FieldMeta): string {
  const rawLabel =
    field.label && field.label.trim().length ? field.label : field.name;
  const baseLabel = field.required ? `${rawLabel} *` : rawLabel;
  return field.readonly ? `${baseLabel} · 🔒` : baseLabel;
}

// ── Stable field list (metadata only, no reactive parent data) ────────────────
// This list is stable and only changes when childMeta changes, NOT on parent form updates.
// This prevents NuGrid column rebuilds that destroy edit state.

const childFields = computed<FieldMeta[]>(() => {
  if (!props.childMeta?.fields) return [];

  const filtered = props.childMeta.fields.filter((f) => {
    if (!f.in_list_view && !f.required) return false;
    if (
      ["id", "created_at", "updated_at", "total_amount", "row_no"].includes(
        f.name,
      )
    )
      return false;
    if (f.name === props.fkField) return false;
    if (f.label === "#") return false;
    // DO NOT evaluate list_view_depends_on here - that would make this reactive to parent form changes
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

// ── Column visibility based on list_view_depends_on (reactive to parent form) ──
// TEMPORARILY DISABLED FOR DEBUGGING - show all columns to test if this is causing the value loss issue

const columnVisibility = computed<Record<string, boolean>>(() => {
  const visibility: Record<string, boolean> = {};
  const parentData = parentFormDataRef.value ?? {};

  for (const field of childFields.value) {
    visibility[field.name] = field.list_view_depends_on
      ? evaluateDependsOn(field.list_view_depends_on, parentData)
      : true;
  }

  return visibility;
});

// Sync columnVisibility computed to NuGrid's column visibility state.
// Only write when something actually changed — writing an identical object
// causes NuGrid to cancel any in-progress cell edit (column-state change
// during the editor commit cycle stops editing without committing).
// Important: only push visibility state into NuGrid when it actually changes.
// Rewriting identical column state during modal reactivity caused NuGrid to
// cancel in-progress popup edits before cell-value-changed could fire.
watch(
  columnVisibility,
  (vis) => {
    const current = columnVisibilityState.value;
    const changed =
      Object.keys(vis).some((k) => current[k] !== vis[k]) ||
      Object.keys(current).some((k) => !(k in vis));
    if (!changed) return;
    columnVisibilityState.value = { ...vis };
  },
  { immediate: true },
);

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

// ── Columns ───────────────────────────────────────────────────────────────────
// Depends ONLY on childFields — never on options data or props.editable.
// Lookup columns get a reference to their lookupArrays[entity] array.
// That array is mutated in-place when options load, so no rebuild happens.

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
        if (field.readonly || field.computed_from) return false;
        const isNewRow = String(row.original?.id).startsWith("__new__");
        return isNewRow ? props.canAdd : props.editable;
      },
      enableSorting: false,
      enableResizing: true,
      enableHiding: !!field.list_view_depends_on, // Allow hiding for dynamic columns
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
          parentFormData: parentFormDataRef.value ?? {},
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
      const isNewRow = String(row.original.id).startsWith("__new__");
      const items: any[] = [];

      // View Details - only for saved rows
      if (!isNewRow) {
        items.push({
          label: "View Details",
          icon: "i-lucide-external-link",
          onSelect: () => {
            router.push(`/${props.childEntity}/${row.original.id}`);
          },
        });
      }

      // Delete - visible when canDelete is true
      if (props.canDelete) {
        items.push({
          label: "Delete",
          icon: "i-lucide-trash-2",
          onSelect: () => {
            const rowId = row.original.id;
            // Remove from grid
            const idx = gridData.value.findIndex((r) => r.id === rowId);
            if (idx >= 0) {
              gridData.value.splice(idx, 1);
            }
            // Track deletion if it's a saved row
            if (!isNewRow) {
              deletedIds.value.push(String(rowId));
            }
            dirty.value = true;
          },
        });
      }

      if (items.length === 0) return null;

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
                variant: "ghost",
                color: "gray",
                size: "sm",
                "aria-label": "Actions",
              }),
          },
        ),
      ]);
    },
  } as NuGridColumn<Record<string, any>>);

  return cols;
});

// ── NuGrid events ─────────────────────────────────────────────────────────────

function onCellEditingStarted(_event: any): void {}

function onCellEditingStopped(_event: any): void {}

function onCellEditingCancelled(_event: any): void {}

/**
 * Evaluate a computed_from expression against a row's data.
 * Supports: "eval:doc.field_a * doc.field_b", "eval:doc.qty * doc.unit_cost"
 * Returns the computed value or null on error.
 */
function evaluateComputedFrom(
  expression: string,
  row: Record<string, any>,
): any {
  let expr = expression.trim();
  if (expr.startsWith("eval:")) expr = expr.slice(5).trim();
  // Normalize python-style logical operators to JS
  expr = expr.replace(/\bor\b/g, "||").replace(/\band\b/g, "&&");
  try {
    // Replace doc.xxx references with actual values
    const resolved = expr.replace(/doc\.([\w]+)/g, (_match, field) => {
      const val = row[field];
      if (val == null) return "0";
      if (typeof val === "number") return String(val);
      const num = Number(val);
      return isNaN(num) ? "0" : String(num);
    });
    // Safe numeric eval using Function (no access to globals)
    const result = new Function(`"use strict"; return (${resolved});`)();
    return typeof result === "number" && isFinite(result)
      ? Math.round(result * 100) / 100
      : null;
  } catch (err) {
    return null;
  }
}

function recalculateComputedFields(row: Record<string, any>): void {
  if (!props.childMeta?.fields) return;
  for (const field of props.childMeta.fields) {
    if (!field.computed_from) continue;
    // Only recalculate if the computed field is null/undefined
    // This preserves backend values for existing records
    if (row[field.name] != null && row[field.name] !== undefined) continue;
    const computed = evaluateComputedFrom(field.computed_from, row);
    if (computed !== null) {
      row[field.name] = computed;
    }
  }
}

async function onCellValueChanged(event: any): Promise<void> {
  if (!event.row?.original || !event.column?.id) return;
  const rowId = String(event.row.original.id);
  const fieldName = String(event.column.id);
  const newValue = event.newValue;

  event.row.original[fieldName] = newValue;
  dirty.value = true;

  // Recalculate computed fields in this row
  recalculateComputedFields(event.row.original);

  // Apply fetch_from rules if this field is a source
  if (gridFetchFrom.isFetchFromSource(fieldName)) {
    const res = await gridFetchFrom.applyForRow(rowId, fieldName, newValue);
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

// ── Data ──────────────────────────────────────────────────────────────────────

async function loadData(): Promise<void> {
  if (!props.parentId || props.parentId === "new") return;
  loading.value = true;
  const timeout = setTimeout(() => {
    loading.value = false;
  }, 10_000);
  try {
    const res = await getChildRecords(
      props.parentEntity,
      props.parentId,
      props.childEntity,
    );
    if (res.status === "success") {
      gridData.value = (res.data ?? []).map((r: any) => ({ ...r }));
      const linkTitlesData = (res as any)._link_titles ?? {};
      linkTitles.value = linkTitlesData as Record<string, string>;

      // Seed label cache from linkTitles so display uses labels immediately
      for (const [key, label] of Object.entries(
        linkTitlesData as Record<string, unknown>,
      )) {
        const [entityKey, value] = key.split("::");
        if (!entityKey || !value) continue;
        if (!lookupLabelCache[entityKey]) lookupLabelCache[entityKey] = {};
        lookupLabelCache[entityKey][value] = String(label ?? value);
      }
    }
  } catch (err) {
    console.error("[ChildDataGrid] load failed:", err);
  } finally {
    clearTimeout(timeout);
    loading.value = false;
  }
}

function createEmptyRow(): Record<string, any> {
  const row: Record<string, any> = {
    id: `__new__${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    [props.fkField]: props.parentId,
  };
  const parentData = parentFormDataRef.value ?? {};
  for (const field of childFields.value) {
    if (field.name === props.fkField) continue;
    if (field.copy_from_parent) {
      row[field.name] =
        parentData[field.copy_from_parent] ?? field.default ?? null;
      continue;
    }
    row[field.name] = field.default ?? null;
  }
  return row;
}

function sanitizeRowForSave(row: Record<string, any>): Record<string, any> {
  const next = { ...row };
  if (!props.childMeta?.fields) return next;

  const validFieldNames = new Set(
    props.childMeta.fields
      .map((field) => field.name)
      .concat(["id", props.fkField]),
  );

  for (const key of Object.keys(next)) {
    if (!validFieldNames.has(key)) {
      delete next[key];
    }
  }

  return next;
}

function addRow(): void {
  gridData.value.push(createEmptyRow());
  dirty.value = true;
}

function getChildData(): Record<string, any>[] {
  return gridData.value.map((row) => sanitizeRowForSave(row));
}
function getDeletedIds(): string[] {
  return deletedIds.value;
}
function markAsSaved(): void {
  dirty.value = false;
  deletedIds.value = [];
}

async function saveAll(): Promise<void> {
  if (!dirty.value) return;
  loading.value = true;
  try {
    const res = await bulkSaveChildren(
      props.parentEntity,
      props.parentId,
      props.childEntity,
      gridData.value,
      deletedIds.value,
    );
    if (res.status === "success") {
      dirty.value = false;
      await loadData();
      emit("save-complete");
    }
  } catch (err) {
    console.error("[ChildDataGrid] save failed:", err);
  } finally {
    loading.value = false;
  }
}

defineExpose({ loadData, saveAll, getChildData, getDeletedIds, markAsSaved });

watch(
  () => [props.parentId, props.childEntity] as const,
  ([parentId, childEntity]) => {
    if (parentId && parentId !== "new" && childEntity) loadData();
  },
  { immediate: true },
);
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <div
      class="flex flex-wrap items-center gap-2 px-4 py-3 border border-muted rounded-t-lg"
    >
      <UButton
        v-if="canAdd"
        icon="i-lucide-plus"
        size="md"
        variant="solid"
        :disabled="loading"
        @click="addRow"
      >
        Add Line
      </UButton>
      <UButton
        variant="outline"
        icon="i-lucide-refresh-cw"
        :loading="loading"
        @click="loadData"
      />
      <div class="ml-auto flex items-center gap-2">
        <UBadge v-if="dirty" color="warning" variant="subtle" size="sm">
          Unsaved changes
        </UBadge>
      </div>
    </div>

    <div
      class="flex-1 min-h-0 flex flex-col border-l border-r border-b border-muted rounded-b-lg"
    >
      <div
        v-if="loading && gridData.length === 0"
        class="flex items-center justify-center py-12"
      >
        <UIcon
          name="i-lucide-loader-2"
          class="animate-spin h-6 w-6 text-primary"
        />
      </div>

      <div
        v-else-if="!loading && gridData.length === 0"
        class="flex items-center justify-center h-full"
      >
        <UEmpty
          variant="naked"
          icon="i-lucide-bell"
          title="No records found."
          description="Create a record to show data."
        />
      </div>

      <div v-if="gridData.length > 0" class="flex-1 min-h-0 overflow-x-auto">
        <div class="w-full h-full">
          <NuGrid
            ref="gridRef"
            v-model:column-pinning="columnPinning"
            v-model:column-visibility="columnVisibilityState"
            :data="gridData"
            :columns="columns"
            virtualization
            :scroll-options="{
              behavior: 'smooth',
            }"
            :ui="{
              base: 'w-full border-separate border-spacing-0',
              thead: '[&>tr]:bg-elevated/50',
              th: 'py-2 border-y border-default first:border-l last:border-r first:rounded-l-lg last:rounded-r-lg',
              td: 'border-b border-default',
            }"
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
                    startClicks: 'single',
                    startKeys: ['enter', 'f2', 'bs', 'alpha', 'numeric'],
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
            @cell-editing-stopped="onCellEditingStopped"
            @cell-editing-cancelled="onCellEditingCancelled"
            @cell-value-changed="onCellValueChanged"
          />
        </div>
      </div>
      <div class="border-t border-default py-3.5 px-4">
        <div class="text-sm text-muted">
          Showing {{ gridData.length }} row(s).
        </div>
      </div>
    </div>
  </div>
</template>
