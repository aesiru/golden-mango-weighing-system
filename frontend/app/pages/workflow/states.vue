<script setup lang="ts">
import { h, resolveComponent } from "vue";
import type { TableColumn } from "@nuxt/ui";
import { useDeleteModalStore } from "~/stores/deleteModal";

const UButton = resolveComponent("UButton");
const UBadge = resolveComponent("UBadge");
const UCheckbox = resolveComponent("UCheckbox");
const UDropdownMenu = resolveComponent("UDropdownMenu");

const api = useApi();
const cache = useCacheStore();
const toast = useToast();
const deleteModalStore = useDeleteModalStore();

const states = ref<any[]>([]);
const loading = ref(true);

const pagination = ref({
  page: 1,
  pageSize: 10,
  total: 0,
});

// Computed property for paginated states
const paginatedStates = computed(() => {
  const start = (pagination.value.page - 1) * pagination.value.pageSize;
  const end = start + pagination.value.pageSize;
  return states.value.slice(start, end);
});

const showStateModal = ref(false);
const editingState = ref<any>(null);
const isModalLoading = ref(false);

const rowSelection = ref<Record<string, boolean>>({});

const formData = ref<{ label: string; color: string }>({
  label: "",
  color: "neutral",
});

const colorOptions = [
  { value: "primary", label: "Primary" },
  { value: "secondary", label: "Secondary" },
  { value: "success", label: "Success" },
  { value: "info", label: "Info" },
  { value: "warning", label: "Warning" },
  { value: "error", label: "Error" },
  { value: "neutral", label: "Neutral" },
];

const stateColumns = computed<TableColumn<any>[]>(() => {
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
      accessorKey: "label",
      header: "Label",
    },
    {
      accessorKey: "color",
      header: "Color",
      cell: ({ row }) =>
        h(
          UBadge,
          {
            color: row.original.color || "neutral",
            variant: "solid",
            size: "md",
          },
          () => row.original.color,
        ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) =>
        h(
          "div",
          {
            class: "flex items-center justify-end",
            onClick: (e: Event) => e.stopPropagation(),
          },
          [
            h(
              UDropdownMenu,
              {
                items: [
                  [
                    {
                      label: "Edit",
                      icon: "i-lucide-edit",
                      onSelect: () => openEditModal(row.original),
                    },
                  ],
                  [
                    {
                      label: "Delete",
                      icon: "i-lucide-trash-2",
                      color: "error",
                      onSelect: () => openDeleteModal(row.original),
                    },
                  ],
                ],
              },
              {
                default: () =>
                  h(UButton, {
                    variant: "ghost",
                    size: "xs",
                    icon: "i-lucide-ellipsis-vertical",
                  }),
              },
            ),
          ],
        ),
    },
  ];
});

const loadStates = async () => {
  try {
    loading.value = true;
    // Always invalidate so admin sees fresh data (not 24h-cached boot data)
    cache.invalidate("workflow:states");
    cache.invalidateLocalStorage("workflow:states");
    const res = await api.getWorkflowStates();
    states.value = [...(res?.data || [])];
    pagination.value.total = states.value.length;
  } catch (err: any) {
    toast.add({
      title: err.message || "Failed to load states",
      color: "error",
    });
  } finally {
    loading.value = false;
  }
};

const handleInlineSave = () => {
  if (!formData.value.label) return;
  handleSave(formData.value);
};

const openCreateModal = () => {
  editingState.value = null;
  showStateModal.value = true;
};

const openEditModal = (state: any) => {
  editingState.value = state;
  showStateModal.value = true;
};

watch(
  () => [showStateModal.value, editingState.value],
  () => {
    if (!showStateModal.value) return;
    if (editingState.value) {
      formData.value = {
        label: editingState.value.label,
        color: editingState.value.color,
      };
      return;
    }
    formData.value = { label: "", color: "neutral" };
  },
  { immediate: true },
);

const openDeleteModal = (state: any) => {
  deleteModalStore.open({
    entityName: "Workflow State",
    itemName: state.name,
    itemId: state.id,
    onConfirm: async () => {
      const res = await api.deleteWorkflowState(state.id);
      if (res.status === "success") {
        toast.add({ title: res.message, color: "success" });
        await loadStates();
      } else {
        throw new Error(res.message || "Delete failed");
      }
    },
  });
};

const handleSave = async (data: any) => {
  try {
    isModalLoading.value = true;
    let res;
    if (editingState.value) {
      res = await api.updateWorkflowState(editingState.value.id, data);
    } else {
      res = await api.createWorkflowState(data);
    }
    if (res.status === "success") {
      toast.add({
        title: res.message,
        color: "success",
      });
      showStateModal.value = false;
      await loadStates();
    } else {
      toast.add({ title: res.message || "Save failed", color: "error" });
    }
  } catch (err: any) {
    toast.add({ title: err.message, color: "error" });
  } finally {
    isModalLoading.value = false;
  }
};

onMounted(loadStates);

definePageMeta({ title: "Global Workflow States" });
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold">Global Workflow States</h2>
        <p class="text-sm text-muted-foreground">
          Manage reusable workflow states
        </p>
      </div>
      <UButton icon="i-lucide-plus" @click="openCreateModal">
        New State
      </UButton>
    </div>

    <div class="border rounded-lg border-gray-200">
      <div class="overflow-x-auto">
        <UTable
          v-model:row-selection="rowSelection"
          :columns="stateColumns"
          :data="paginatedStates"
          :loading="loading"
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

    <UModal
      :open="showStateModal"
      :title="editingState ? 'Edit State' : 'Create State'"
      :ui="{ footer: 'justify-end' }"
      @update:open="(val) => (showStateModal = val)"
      class="w-[300px]"
    >
      <template #body>
        <UForm :state="formData" class="space-y-4">
          <UFormField label="Label" required>
            <UInput
              v-model="formData.label"
              placeholder="e.g. Under Review"
              class="w-full"
            />
          </UFormField>

          <UFormField label="Color">
            <USelect
              v-model="formData.color"
              :items="colorOptions"
              class="w-full"
            />
          </UFormField>
        </UForm>
      </template>

      <template #footer="{ close }">
        <UButton
          label="Cancel"
          color="neutral"
          variant="outline"
          @click="close"
          :disabled="isModalLoading"
        />
        <UButton
          :label="editingState ? 'Update' : 'Create'"
          color="neutral"
          @click="handleInlineSave"
          :loading="isModalLoading"
        />
      </template>
    </UModal>
  </div>
</template>
