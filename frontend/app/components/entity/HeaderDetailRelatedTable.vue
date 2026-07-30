<script setup lang="ts">
import { h, resolveComponent } from "vue";
import type { DropdownMenuItem, TableColumn, TableRow } from "@nuxt/ui";
import type { EntityMeta, FieldMeta } from "~/composables/useApiTypes";

interface Props {
  parentEntity: string;
  parentId: string;
  childEntity: string;
  fkField: string;
  childMeta: EntityMeta | null;
  canAdd?: boolean;
  canDelete?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  canAdd: false,
  canDelete: false,
});

const emit = defineEmits<{
  (e: "add-clicked"): void;
  (e: "loading-change", isLoading: boolean): void;
}>();

const { getEntityList, deleteEntity } = useApi();
const router = useRouter();
const toast = useToast();
const confirmDialog = useConfirmDialog();
const UCheckbox = resolveComponent("UCheckbox");
const UButton = resolveComponent("UButton");

const loading = ref(false);
const data = ref<Record<string, any>[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const rowSelection = ref<Record<string, boolean>>({});
const columnVisibility = ref<Record<string, boolean>>({});
const sorting = ref<{ id: string; desc: boolean }[]>([]);
const table = useTemplateRef<{ tableApi?: any }>("table");

const pageSizeOptions = [10, 20, 50, 100].map((size) => ({
  label: `${size} / page`,
  value: size,
}));

const currentPage = computed(() => page.value);
const pageStart = computed(() => {
  if (!total.value || data.value.length === 0) return 0;
  return (page.value - 1) * pageSize.value + 1;
});
const pageEnd = computed(() => {
  if (!total.value || data.value.length === 0) return 0;
  return Math.min(
    total.value,
    (page.value - 1) * pageSize.value + data.value.length,
  );
});
const selectedCount = computed(
  () => table.value?.tableApi?.getFilteredSelectedRowModel().rows.length || 0,
);

watch(loading, (val) => emit("loading-change", val));

const visibleFields = computed(() => {
  if (!props.childMeta?.fields) return [];
  let fields = props.childMeta.fields.filter((f) => f.in_list_view);
  if (fields.length === 0) {
    fields = props.childMeta.fields
      .filter((f) => !f.hidden && f.name !== "id")
      .slice(0, 6);
  }
  return fields
    .filter((f) => {
      if (["id", "created_at", "updated_at"].includes(f.name)) return false;
      if (f.name === props.fkField) return false;
      return true;
    })
    .sort((a, b) => {
      // workflow_state always goes last
      if (a.name === "workflow_state" && b.name !== "workflow_state") return 1;
      if (b.name === "workflow_state" && a.name !== "workflow_state") return -1;
      // Then editable fields first, then readonly
      if (a.readonly && !b.readonly) return 1;
      if (!a.readonly && b.readonly) return -1;
      return 0;
    })
    .map((f) => ({
      id: f.name,
      accessorKey: f.name,
      header: f.name === "workflow_state" ? "Status" : f.label,
      fieldName: f.name,
      field: f,
    }));
});

const columnVisibilityItems = computed((): DropdownMenuItem[] =>
  visibleFields.value.map((f) => ({
    label: f.header,
    type: "checkbox" as const,
    checked: columnVisibility.value[f.id] !== false,
    onUpdateChecked(checked: boolean) {
      columnVisibility.value = {
        ...columnVisibility.value,
        [f.id]: !!checked,
      };
    },
    onSelect(e: Event) {
      e.preventDefault();
    },
  })),
);

const tableColumns = computed<TableColumn<any>[]>(() => {
  const selectionColumn: TableColumn<any> = {
    id: "select",
    header: ({ table }) =>
      h(UCheckbox, {
        modelValue: table.getIsSomePageRowsSelected()
          ? "indeterminate"
          : table.getIsAllPageRowsSelected(),
        "onUpdate:modelValue": (value: boolean | "indeterminate") =>
          table.toggleAllPageRowsSelected(!!value),
        "aria-label": "Select all",
      }),
    cell: ({ row }) =>
      h(UCheckbox, {
        modelValue: row.getIsSelected(),
        "onUpdate:modelValue": (value: boolean | "indeterminate") =>
          row.toggleSelected(!!value),
        "aria-label": "Select row",
      }),
    enableSorting: false,
    enableHiding: false,
  };

  const fieldColumns = visibleFields.value.map(
    ({ id, accessorKey, header }) => ({
      id,
      accessorKey,
      header: ({ column }: { column: any }) =>
        h(UButton, {
          color: "neutral",
          variant: "ghost",
          label: header,
          icon: column.getIsSorted()
            ? column.getIsSorted() === "asc"
              ? "i-lucide-arrow-up-narrow-wide"
              : "i-lucide-arrow-down-wide-narrow"
            : "i-lucide-arrow-up-down",
          class:
            "-mx-2.5 data-[state=open]:bg-elevated max-w-[320px] truncate justify-start",
          onClick: () => column.toggleSorting(column.getIsSorted() === "asc"),
        }),
    }),
  );

  return [selectionColumn, ...fieldColumns];
});

const getCellValue = (row: Record<string, any>, field: FieldMeta) => {
  const value = row[field.name];

  if (field.field_type === "link" && value) {
    const linkTitles = row._link_titles || {};
    const key = `${field.link_entity}::${value}`;
    return linkTitles[key] || value;
  }

  if (field.field_type === "date" && value) {
    return new Date(value).toLocaleDateString();
  }

  return value ?? "";
};

async function loadData() {
  if (!props.parentId || props.parentId === "new") return;
  loading.value = true;
  try {
    const sort = sorting.value[0];
    const res = await getEntityList(props.childEntity, {
      page: page.value,
      pageSize: pageSize.value,
      sortField: sort?.id || undefined,
      sortOrder: sort ? (sort.desc ? "desc" : "asc") : undefined,
      filterField: props.fkField,
      filterValue: props.parentId,
    });

    if (res.status === "success") {
      data.value = res.data || [];
      total.value = res.total || 0;
    }
  } catch (err) {
    console.error("[HeaderDetailRelatedTable] load failed:", err);
  } finally {
    loading.value = false;
  }
}

function handleAddClick() {
  emit("add-clicked");
}

async function handleDeleteSelected(): Promise<void> {
  const selectedRows =
    table.value?.tableApi?.getFilteredSelectedRowModel().rows || [];
  if (!selectedRows.length) return;

  const count = selectedRows.length;
  const confirmed = await confirmDialog({
    title: `Delete ${props.childMeta?.label || props.childEntity}`,
    description: `Are you sure you want to delete ${count} record${count > 1 ? "s" : ""}? This action cannot be undone.`,
    confirmLabel: "Delete",
    confirmColor: "error",
  });
  if (!confirmed) return;

  try {
    const responses = await Promise.all(
      selectedRows.map((row: any) =>
        deleteEntity(props.childEntity, row.original.id),
      ),
    );

    const failed = responses.find(
      (response: any) => response?.status !== "success",
    );
    if (failed) {
      // Preserve full response data for referencing records
      const error = new Error(failed.message || "Delete failed") as any;
      error.data = failed.data;
      throw error;
    }

    const messages = Array.from(
      new Set(
        responses
          .map((response: any) => response?.message)
          .filter(
            (message: any) =>
              typeof message === "string" && message.trim().length,
          ),
      ),
    );

    if (messages.length) {
      toast.add({
        title: messages.join(" "),
        color: "success",
        type: "foreground",
      });
    }

    rowSelection.value = {};
    await loadData();
  } catch (error: any) {
    toast.add({
      title: error.message || "Delete failed",
      color: "error",
      type: "foreground",
    });
  }
}

const handleRowSelect = (event: Event, row: TableRow<any>) => {
  const target = event.target as HTMLElement;
  if (target?.closest("input[type='checkbox']")) return;
  router.push(`/${props.childEntity}/${row.original.id}`);
};

const handlePageSizeChange = (value: number | string | null) => {
  const nextSize = Number(value || pageSize.value);
  if (!Number.isFinite(nextSize) || nextSize === pageSize.value) return;

  pageSize.value = nextSize;
  page.value = 1;
  loadData();
};

async function setPage(newPage: number) {
  page.value = newPage;
  await loadData();
}

defineExpose({ loadData });

watch(sorting, () => {
  page.value = 1;
  loadData();
});

watch(
  () => [props.parentId, props.childEntity, props.fkField] as const,
  async ([parentId, childEntity, fkField]) => {
    if (parentId && parentId !== "new" && childEntity && fkField) {
      page.value = 1;
      await loadData();
    }
  },
  { immediate: true },
);
</script>

<template>
  <div class="flex flex-1 min-h-0 flex-col">
    <div
      class="flex flex-wrap items-center gap-2 px-5 py-4.5 border border-muted rounded-t-lg"
    >
      <UButton
        v-if="selectedCount > 0 && canDelete"
        icon="i-lucide-trash-2"
        color="error"
        size="md"
        @click="handleDeleteSelected"
      >
        Delete
      </UButton>
      <UButton
        v-else-if="canAdd"
        icon="i-lucide-plus"
        size="md"
        @click="handleAddClick"
      >
        Add {{ childMeta?.label || childEntity }}
      </UButton>
      <UButton
        variant="outline"
        icon="i-lucide-refresh-cw"
        :loading="loading"
        @click="loadData"
      />
      <UDropdownMenu :items="columnVisibilityItems" :content="{ align: 'end' }">
        <UButton
          label="Columns"
          color="neutral"
          variant="outline"
          trailing-icon="i-lucide-chevron-down"
          class="ml-auto"
          aria-label="Columns select dropdown"
        />
      </UDropdownMenu>
    </div>

    <div
      class="flex-1 min-h-0 flex flex-col border-l border-r border-b border-muted rounded-b-lg"
    >
      <UTable
        ref="table"
        v-model:row-selection="rowSelection"
        v-model:sorting="sorting"
        v-model:column-visibility="columnVisibility"
        :data="data"
        :columns="tableColumns"
        :loading="loading"
        loading-color="primary"
        loading-animation="carousel"
        manual-sorting
        sticky
        class="flex-1 min-h-0 max-h-full"
        @select="handleRowSelect"
      >
        <template
          v-for="col in visibleFields"
          :key="col.id"
          #[`${col.id}-cell`]="{ row }"
        >
          <div class="max-w-[320px] truncate">
            <template v-if="col.field.field_type === 'boolean'">
              <UIcon
                :name="
                  getCellValue(row.original, col.field)
                    ? 'i-lucide-check'
                    : 'i-lucide-x'
                "
                :class="
                  getCellValue(row.original, col.field)
                    ? 'text-success'
                    : 'text-muted'
                "
              />
            </template>
            <template v-else>
              {{ getCellValue(row.original, col.field) }}
            </template>
          </div>
        </template>
        <template #loading>
          <div class="w-full px-4 space-y-8">
            <USkeleton class="h-4 w-full rounded-lg" />
            <USkeleton class="h-4 w-full rounded-lg" />
            <USkeleton class="h-4 w-full rounded-lg" />
          </div>
        </template>
        <template #empty>
          <div
            class="text-center py-12 flex items-center justify-center h-full"
          >
            <div>
              <UIcon
                name="i-lucide-inbox"
                class="h-12 w-12 mx-auto text-muted-foreground mb-4"
              />
              <h3 class="text-lg font-medium mb-2">No records found</h3>
              <p class="text-muted-foreground mb-4">
                Click Add to create a new {{ childMeta?.label || childEntity }}.
              </p>
              <UButton
                v-if="canAdd"
                icon="i-lucide-plus"
                @click="handleAddClick"
              >
                Create New
              </UButton>
            </div>
          </div>
        </template>
      </UTable>

      <div
        class="flex justify-between items-center gap-3 border-t border-default py-3.5 px-4"
      >
        <div class="text-sm text-muted space-y-1">
          <div>{{ selectedCount }} row(s) selected.</div>
          <div>Showing {{ pageStart }}-{{ pageEnd }} of {{ total }}.</div>
        </div>
        <div class="flex items-center gap-3">
          <USelect
            :model-value="pageSize"
            :items="pageSizeOptions"
            value-key="value"
            class="w-28"
            @update:model-value="handlePageSizeChange"
          />
          <UPagination
            :page="currentPage"
            :items-per-page="pageSize"
            :total="total"
            @update:page="setPage"
          />
        </div>
      </div>
    </div>
  </div>
</template>
