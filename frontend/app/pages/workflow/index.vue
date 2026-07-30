<script setup lang="ts">
import { h, resolveComponent } from "vue";
import type { TableColumn } from "@nuxt/ui";
import { useDeleteModalStore } from "~/stores/deleteModal";

const UButton = resolveComponent("UButton");
const UBadge = resolveComponent("UBadge");
const UCheckbox = resolveComponent("UCheckbox");

const api = useApi();
const toast = useToast();
const router = useRouter();
const deleteModalStore = useDeleteModalStore();

const workflows = ref<any[]>([]);
const loading = ref(true);

const pagination = ref({
  page: 1,
  pageSize: 10,
  total: 0,
});

// Computed property for paginated workflows
const paginatedWorkflows = computed(() => {
  const start = (pagination.value.page - 1) * pagination.value.pageSize;
  const end = start + pagination.value.pageSize;
  return workflows.value.slice(start, end);
});

const showDetailModal = ref(false);
const viewingWorkflow = ref<any>(null);
const isModalLoading = ref(false);

const rowSelection = ref<Record<string, boolean>>({});

const workflowColumns = computed<TableColumn<any>[]>(() => {
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

  return [
    selectionColumn,
    {
      accessorKey: "name",
      header: "Name",
    },
    {
      accessorKey: "target_entity",
      header: "Target Entity",
      cell: ({ row }) =>
        h(
          "span",
          { class: "text-sm text-foreground/80" },
          row.original.target_entity,
        ),
    },
    {
      accessorKey: "is_active",
      header: "Status",
      cell: ({ row }) =>
        h(
          UBadge,
          {
            color: row.original.is_active ? "success" : "neutral",
            variant: "outline",
            size: "md",
          },
          () => (row.original.is_active ? "Active" : "Inactive"),
        ),
    },
  ];
});

const loadWorkflows = async () => {
  try {
    loading.value = true;
    const res = await api.getWorkflows();
    if (res.status === "success") {
      workflows.value = res.data || [];
      pagination.value.total = workflows.value.length;
    }
  } catch (err: any) {
    toast.add({
      title: err.message || "Failed to load workflows",
      color: "error",
    });
  } finally {
    loading.value = false;
  }
};

const openCreateModal = () => {
  router.push("/workflow/new");
};

const openDetailModal = async (workflow: any) => {
  try {
    const res = await api.getWorkflow(workflow.id);
    if (res.status === "success") {
      viewingWorkflow.value = res.data;
      showDetailModal.value = true;
    }
  } catch (err: any) {
    toast.add({ title: err.message, color: "error" });
  }
};

const openDeleteModal = (workflow: any) => {
  deleteModalStore.open({
    entityName: "Workflow",
    itemName: workflow.name,
    itemId: workflow.id,
    onConfirm: async () => {
      const res = await api.deleteWorkflow(workflow.id);
      if (res.status === "success") {
        toast.add({ title: res.message, color: "success" });
        await loadWorkflows();
      } else {
        throw new Error(res.message || "Delete failed");
      }
    },
  });
};

onMounted(loadWorkflows);

const getSelectedWorkflowId = () => {
  const selectedRowIds = Object.keys(rowSelection.value).filter(
    (k) => rowSelection.value[k],
  );
  if (selectedRowIds.length !== 1) return null;

  const idx = Number(selectedRowIds[0]);
  const selected = Number.isFinite(idx)
    ? paginatedWorkflows.value[idx]
    : undefined;
  return selected?.id || null;
};

watch(
  rowSelection,
  async () => {
    const selectedId = getSelectedWorkflowId();
    if (!selectedId) return;
    // Selection is for future bulk actions; do not navigate on checkbox select.
  },
  { deep: true },
);

const handleRowSelect = (event: Event, row: any) => {
  const target = event.target as HTMLElement;
  if (target?.closest("input[type='checkbox']")) return;
  router.push(`/workflow/${row.original.id}`);
};

definePageMeta({ title: "Workflows" });
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold">Workflows</h2>
        <p class="text-sm text-muted-foreground">
          Manage entity-specific workflows
        </p>
      </div>
      <UButton icon="i-lucide-plus" @click="openCreateModal">
        New Workflow
      </UButton>
    </div>

    <div class="border border-gray-200 rounded-lg">
      <div class="overflow-x-auto">
        <UTable
          v-model:row-selection="rowSelection"
          :columns="workflowColumns"
          :data="paginatedWorkflows"
          :loading="loading"
          @select="handleRowSelect"
        />
      </div>

      <div class="flex justify-end border-t border-gray-200 py-3.5 px-4">
        <UPagination
          :page="pagination.page"
          :items-per-page="pagination.pageSize"
          :total="pagination.total"
          @update:page="(p) => (pagination.page = p)"
        />
      </div>
    </div>
  </div>
</template>
