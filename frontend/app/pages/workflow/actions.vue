<script setup lang="ts">
import { h, resolveComponent } from "vue";
import type { TableColumn } from "@nuxt/ui";
import { useDeleteModalStore } from "~/stores/deleteModal";

const UButton = resolveComponent("UButton");
const UBadge = resolveComponent("UBadge");
const UCheckbox = resolveComponent("UCheckbox");
const UDropdownMenu = resolveComponent("UDropdownMenu");

const api = useApi();
const toast = useToast();
const deleteModalStore = useDeleteModalStore();

const actions = ref<any[]>([]);
const loading = ref(true);

const pagination = ref({
  page: 1,
  pageSize: 10,
  total: 0,
});

// Computed property for paginated actions
const paginatedActions = computed(() => {
  const start = (pagination.value.page - 1) * pagination.value.pageSize;
  const end = start + pagination.value.pageSize;
  return actions.value.slice(start, end);
});

const showActionModal = ref(false);
const editingAction = ref<any>(null);
const isModalLoading = ref(false);

const rowSelection = ref<Record<string, boolean>>({});

const formData = ref<{ label: string }>({
  label: "",
});

const actionColumns = computed<TableColumn<any>[]>(() => {
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

const loadActions = async () => {
  try {
    loading.value = true;
    const res = await api.getWorkflowActions();
    if (res.status === "success") {
      actions.value = res.data || [];
      pagination.value.total = actions.value.length;
    }
  } catch (err: any) {
    toast.add({
      title: err.message || "Failed to load actions",
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
  editingAction.value = null;
  showActionModal.value = true;
};

const openEditModal = (action: any) => {
  editingAction.value = action;
  showActionModal.value = true;
};

watch(
  () => [showActionModal.value, editingAction.value],
  () => {
    if (!showActionModal.value) return;
    if (editingAction.value) {
      formData.value = { label: editingAction.value.label };
      return;
    }
    formData.value = { label: "" };
  },
  { immediate: true },
);

const openDeleteModal = (action: any) => {
  deleteModalStore.open({
    entityName: "Workflow Action",
    itemName: action.name,
    itemId: action.id,
    onConfirm: async () => {
      const res = await api.deleteWorkflowAction(action.id);
      if (res.status === "success") {
        toast.add({ title: res.message, color: "success" });
        await loadActions();
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
    if (editingAction.value) {
      res = await api.updateWorkflowAction(editingAction.value.id, data);
    } else {
      res = await api.createWorkflowAction(data);
    }
    if (res.status === "success") {
      toast.add({
        title: res.message,
        color: "success",
      });
      showActionModal.value = false;
      await loadActions();
    } else {
      toast.add({ title: res.message, color: "error" });
    }
  } catch (err: any) {
    toast.add({ title: err.message, color: "error" });
  } finally {
    isModalLoading.value = false;
  }
};

onMounted(loadActions);

definePageMeta({ title: "Global Workflow Actions" });
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold">Global Workflow Actions</h2>
        <p class="text-sm text-muted-foreground">
          Manage reusable workflow actions
        </p>
      </div>
      <UButton icon="i-lucide-plus" @click="openCreateModal">
        New Action
      </UButton>
    </div>

    <div class="border rounded-lg border-gray-200">
      <div class="overflow-x-auto">
        <UTable
          v-model:row-selection="rowSelection"
          :columns="actionColumns"
          :data="paginatedActions"
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
      :open="showActionModal"
      :title="editingAction ? 'Edit Action' : 'Create Action'"
      :ui="{ footer: 'justify-end' }"
      @update:open="(val) => (showActionModal = val)"
      class="w-[300px]"
    >
      <template #body>
        <UForm :state="formData" class="space-y-4">
          <UFormField label="Label" required>
            <UInput
              v-model="formData.label"
              placeholder="e.g. Review"
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
          :label="editingAction ? 'Update' : 'Create'"
          color="neutral"
          @click="handleInlineSave"
          :loading="isModalLoading"
        />
      </template>
    </UModal>
  </div>
</template>
