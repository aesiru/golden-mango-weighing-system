<script setup lang="ts">
import { h, resolveComponent } from "vue";
import type { TableColumn } from "@nuxt/ui";
import WorkflowAddStateModal from "~/components/workflow/WorkflowAddStateModal.vue";
import WorkflowAddTransitionModal from "~/components/workflow/WorkflowAddTransitionModal.vue";

const UButton = resolveComponent("UButton");
const UCheckbox = resolveComponent("UCheckbox");
const UBadge = resolveComponent("UBadge");
const UDropdownMenu = resolveComponent("UDropdownMenu");

const route = useRoute();
const router = useRouter();
const api = useApi();
const toast = useToast();

const workflowId = computed(() => route.params.id as string);
const isNew = computed(() => workflowId.value === "new");

definePageMeta({ title: "Workflow", middleware: "auth" as any });

const loading = ref(true);
const saving = ref(false);

const workflow = ref<any>(null);

const formData = ref<{
  name: string;
  target_entity: string;
  is_active: boolean;
}>({
  name: "",
  target_entity: "",
  is_active: true,
});

const entities = ref<any[]>([]);
const workflows = ref<any[]>([]);

const showAddStateModal = ref(false);
const showAddTransitionModal = ref(false);
const showEditTransitionModal = ref(false);

const editingTransition = ref<any>(null);

const globalStates = ref<any[]>([]);
const globalActions = ref<any[]>([]);
const allRoles = ref<any[]>([]);

const editTransitionFormData = ref<{
  from_state_id: string;
  action_id: string;
  to_state_id: string;
  allowed_roles: string[];
}>({
  from_state_id: "",
  action_id: "",
  to_state_id: "",
  allowed_roles: [],
});

const stateRowSelection = ref<Record<string, boolean>>({});
const transitionRowSelection = ref<Record<string, boolean>>({});

const getSelectedStateLinkIds = () => {
  const selectedRowIds = Object.keys(stateRowSelection.value).filter(
    (k) => stateRowSelection.value[k],
  );

  const rows = workflow.value?.state_links || [];
  return selectedRowIds
    .map((rowId) => {
      const idx = Number(rowId);
      if (Number.isFinite(idx) && rows[idx]?.id) return rows[idx].id;
      return rowId;
    })
    .filter(Boolean);
};

const availableEntityOptions = computed(() => {
  const usedEntities = new Set(
    workflows.value.map((w: any) => w.target_entity),
  );
  return entities.value
    .filter((e: any) => !usedEntities.has(e.name) && e.name)
    .map((e: any) => ({ value: e.name, label: e.label }));
});

const statusBadge = computed<{ label: string; color: "success" | "neutral" }>(
  () => {
    const active = !!formData.value.is_active;
    return {
      label: active ? "Active" : "Inactive",
      color: active ? "success" : "neutral",
    };
  },
);

const stateTableColumns = computed<TableColumn<any>[]>(() => {
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
      accessorKey: "state_label",
      header: "State",
    },
    {
      accessorKey: "is_initial",
      header: "Initial",
      cell: ({ row }) =>
        row.original.is_initial
          ? h(UBadge, { color: "primary", size: "md" }, () => "Yes")
          : null,
    },
  ];
});

const transitionTableColumns = computed<TableColumn<any>[]>(() => {
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
      accessorKey: "from_state_label",
      header: "From",
    },
    {
      accessorKey: "action_label",
      header: "Action",
    },
    {
      accessorKey: "to_state_label",
      header: "To",
    },
    {
      id: "allowed_roles",
      header: "Allowed",
      cell: ({ row }) => {
        const roles = row.original.allowed_roles || [];
        if (!roles.length)
          return h("span", { class: "text-xs text-muted-foreground" }, "All");
        return h(
          "div",
          { class: "flex flex-wrap gap-1" },
          roles.map((r: string) =>
            h(UBadge, { size: "sm", variant: "subtle" }, () => r),
          ),
        );
      },
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
          h(
            UDropdownMenu,
            {
              items: [
                [
                  {
                    label: "Edit",
                    icon: "i-lucide-edit",
                    onSelect: () => openEditTransitionModal(row.original),
                  },
                ],
                [
                  {
                    label: "Delete",
                    icon: "i-lucide-trash-2",
                    color: "error",
                    onSelect: () => handleDeleteTransition(row.original.id),
                  },
                ],
              ],
            },
            {
              default: () =>
                h(UButton, {
                  variant: "ghost",
                  size: "sm",
                  icon: "i-lucide-ellipsis-vertical",
                }),
            },
          ),
        ),
    },
  ];
});

const hasStateSelection = computed(() =>
  Object.values(stateRowSelection.value).some((v) => v),
);

const stateSelectionCount = computed(() => getSelectedStateLinkIds().length);

const singleSelectedStateLinkId = computed(() => {
  if (stateSelectionCount.value !== 1) return null;
  return getSelectedStateLinkIds()[0] || null;
});

const stateActionsMenuItems = computed(() => {
  if (stateSelectionCount.value <= 0) return [];

  const deleteItem = {
    label: "Delete",
    icon: "i-lucide-trash-2",
    color: "error",
    onSelect: () => deleteSelectedStates(),
  };

  if (stateSelectionCount.value === 1 && singleSelectedStateLinkId.value) {
    return [
      [
        {
          label: "Make Initial",
          icon: "i-lucide-flag",
          onSelect: () => handleSetInitial(singleSelectedStateLinkId.value!),
        },
      ],
      [deleteItem],
    ];
  }

  return [[deleteItem]];
});

const hasTransitionSelection = computed(() =>
  Object.values(transitionRowSelection.value).some((v) => v),
);

const deleteSelectedStates = async () => {
  const selectedIds = getSelectedStateLinkIds();

  for (const id of selectedIds) {
    await handleDeleteStateLink(id);
  }
  stateRowSelection.value = {};
};

const deleteSelectedTransitions = async () => {
  const selectedIds = Object.entries(transitionRowSelection.value)
    .filter(([, selected]) => selected)
    .map(([id]) => id);

  for (const id of selectedIds) {
    await handleDeleteTransition(id);
  }
  transitionRowSelection.value = {};
};

const openEditTransitionModal = async (transition: any) => {
  editingTransition.value = transition;
  editTransitionFormData.value = {
    from_state_id: transition.from_state_id,
    action_id: transition.action_id,
    to_state_id: transition.to_state_id,
    allowed_roles: transition.allowed_roles || [],
  };
  await loadGlobalStatesAndActions();
  showEditTransitionModal.value = true;
};

const loadGlobalStatesAndActions = async () => {
  try {
    const [statesRes, actionsRes, rolesRes] = await Promise.all([
      api.getWorkflowStates(),
      api.getWorkflowActions(),
      api.getAdminRoles(),
    ]);
    if (statesRes.status === "success") {
      globalStates.value = [...(statesRes.data || [])];
    }
    if (actionsRes.status === "success") {
      globalActions.value = actionsRes.data || [];
    }
    if (rolesRes.status === "success") {
      allRoles.value = rolesRes.data || [];
    }
  } catch (err: any) {
    toast.add({ title: err.message, color: "error" });
  }
};

const handleSaveTransitionEdit = async () => {
  if (!editingTransition.value || !workflow.value) return;
  try {
    saving.value = true;
    const res = await api.updateTransition(
      workflow.value.id,
      editingTransition.value.id,
      editTransitionFormData.value,
    );
    if (res.status === "success") {
      toast.add({ title: res.message, color: "success" });
      showEditTransitionModal.value = false;
      await refreshWorkflow();
    } else {
      toast.add({ title: res.message, color: "error" });
    }
  } catch (err: any) {
    toast.add({ title: err.message, color: "error" });
  } finally {
    saving.value = false;
  }
};

const loadMetaForCreate = async () => {
  const [entitiesRes, workflowsRes] = await Promise.all([
    api.getMeta(),
    api.getWorkflows(),
  ]);
  entities.value = entitiesRes.data || [];
  workflows.value = workflowsRes.data || [];
};

const loadWorkflow = async () => {
  if (isNew.value) {
    workflow.value = null;
    formData.value = { name: "", target_entity: "", is_active: true };
    await loadMetaForCreate();
    return;
  }

  const res = await api.getWorkflow(workflowId.value);
  if (res.status !== "success")
    throw new Error(res.message || "Failed to load workflow");

  workflow.value = res.data;
  formData.value = {
    name: res.data?.name || "",
    target_entity: res.data?.target_entity || "",
    is_active: !!res.data?.is_active,
  };
};

const refreshWorkflow = async () => {
  if (isNew.value) return;
  const res = await api.getWorkflow(workflowId.value);
  if (res.status === "success") workflow.value = res.data;
};

const handleSave = async () => {
  if (!formData.value.name || !formData.value.target_entity) return;

  try {
    saving.value = true;

    if (isNew.value) {
      const res = await api.createWorkflow(formData.value);
      if (res.status === "success") {
        toast.add({ title: res.message, color: "success" });
        const newId = (res as any).data?.id;
        if (newId) {
          await router.replace(`/workflow/${newId}`);
        } else {
          await router.replace(`/workflow`);
        }
      } else {
        toast.add({ title: res.message || "Create failed", color: "error" });
      }
    } else {
      const res = await api.updateWorkflow(workflowId.value, {
        name: formData.value.name,
        is_active: formData.value.is_active,
      });
      if (res.status === "success") {
        toast.add({ title: res.message, color: "success" });
        await refreshWorkflow();
      } else {
        toast.add({ title: res.message || "Update failed", color: "error" });
      }
    }
  } catch (err: any) {
    toast.add({ title: err.message || "Save failed", color: "error" });
  } finally {
    saving.value = false;
  }
};

const handleDeleteStateLink = async (stateLinkId: string) => {
  if (!workflow.value?.id) return;
  try {
    saving.value = true;
    const res = await api.removeStateFromWorkflow(
      workflow.value.id,
      stateLinkId,
    );
    if (res.status === "success") {
      toast.add({ title: res.message, color: "success" });
      await refreshWorkflow();
    } else {
      toast.add({ title: res.message, color: "error" });
    }
  } catch (err: any) {
    toast.add({ title: err.message, color: "error" });
  } finally {
    saving.value = false;
  }
};

const handleSetInitial = async (stateLinkId: string) => {
  if (!workflow.value?.id) return;
  try {
    saving.value = true;
    const res = await api.setInitialState(workflow.value.id, stateLinkId);
    if (res.status === "success") {
      toast.add({ title: res.message, color: "success" });
      await refreshWorkflow();
    } else {
      toast.add({ title: res.message, color: "error" });
    }
  } catch (err: any) {
    toast.add({ title: err.message, color: "error" });
  } finally {
    saving.value = false;
  }
};

const handleDeleteTransition = async (transitionId: string) => {
  if (!workflow.value?.id) return;
  try {
    saving.value = true;
    const res = await api.removeTransitionFromWorkflow(
      workflow.value.id,
      transitionId,
    );
    if (res.status === "success") {
      toast.add({ title: res.message, color: "success" });
      await refreshWorkflow();
    } else {
      toast.add({ title: res.message, color: "error" });
    }
  } catch (err: any) {
    toast.add({ title: err.message, color: "error" });
  } finally {
    saving.value = false;
  }
};

watch(
  workflowId,
  async () => {
    try {
      loading.value = true;
      await loadWorkflow();
    } catch (err: any) {
      toast.add({
        title: err.message || "Failed to load workflow",
        color: "error",
      });
    } finally {
      loading.value = false;
    }
  },
  { immediate: true },
);
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center gap-2">
      <UButton
        variant="ghost"
        icon="i-lucide-arrow-left"
        @click="router.push('/workflow')"
      />
      <div class="flex-1">
        <h1 class="text-2xl font-bold">
          {{ isNew ? "New Workflow" : formData.name || "Workflow" }}
        </h1>
      </div>

      <!-- Actions -->
      <UButton :loading="saving" @click="handleSave">
        {{ isNew ? "Create" : "Save" }}
      </UButton>
      <div class="flex gap-2">
        <UButton
          variant="outline"
          :disabled="saving"
          @click="router.push('/workflow')"
        >
          Cancel
        </UButton>
      </div>
    </div>

    <div class="rounded-lg border border-accented p-4">
      <UForm :state="formData" class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <UFormField label="Workflow Name" required>
          <UInput
            v-model="formData.name"
            placeholder="e.g. Asset Lifecycle"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Target Entity" required>
          <USelect
            v-if="isNew"
            v-model="formData.target_entity"
            :items="availableEntityOptions"
            placeholder="Select entity..."
            :ui="{ content: 'min-w-fit' }"
            class="w-full"
          />

          <USelect
            v-else
            :model-value="formData.target_entity || ''"
            disabled
            class="w-full"
          />
        </UFormField>

        <UFormField label="Active">
          <UCheckbox v-model="formData.is_active" label="Workflow is active" />
        </UFormField>
      </UForm>
    </div>

    <div v-if="!isNew" class="space-y-8">
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold">States</h2>
          <UButton
            v-if="stateSelectionCount === 0"
            size="md"
            icon="i-lucide-plus"
            @click="showAddStateModal = true"
          >
            Add State
          </UButton>

          <UDropdownMenu
            v-else
            :items="stateActionsMenuItems"
            :content="{ align: 'end', side: 'bottom', sideOffset: 8 }"
          >
            <UButton
              size="md"
              icon="i-lucide-chevron-down"
              variant="outline"
              :loading="saving"
            >
              Actions
            </UButton>
          </UDropdownMenu>
        </div>

        <div class="border border-accented rounded-lg">
          <div
            v-if="(workflow?.state_links || []).length === 0"
            class="text-sm text-muted-foreground"
          >
            No states linked yet.
          </div>

          <div v-else>
            <UTable
              v-model:row-selection="stateRowSelection"
              :columns="stateTableColumns"
              :data="workflow?.state_links || []"
            />
          </div>
        </div>
      </div>

      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold">Transitions</h2>
          <UButton
            v-if="!hasTransitionSelection"
            size="md"
            icon="i-lucide-plus"
            :disabled="(workflow?.state_links || []).length < 2"
            @click="showAddTransitionModal = true"
          >
            Add Transition
          </UButton>
          <UButton
            v-else
            size="md"
            icon="i-lucide-trash-2"
            color="error"
            @click="deleteSelectedTransitions"
            :loading="saving"
          >
            Delete
          </UButton>
        </div>

        <div class="border border-accented rounded-lg">
          <div
            v-if="(workflow?.transitions || []).length === 0"
            class="text-sm text-muted-foreground"
          >
            No transitions yet.
          </div>

          <div v-else>
            <UTable
              v-model:row-selection="transitionRowSelection"
              :columns="transitionTableColumns"
              :data="workflow?.transitions || []"
            />
          </div>
        </div>
      </div>
    </div>

    <WorkflowAddStateModal
      v-model="showAddStateModal"
      :workflow="workflow"
      @refresh="refreshWorkflow"
    />

    <WorkflowAddTransitionModal
      v-model="showAddTransitionModal"
      :workflow="workflow"
      @refresh="refreshWorkflow"
    />

    <UModal
      :open="showEditTransitionModal"
      title="Edit Transition"
      :ui="{ footer: 'justify-end' }"
      @update:open="(val) => (showEditTransitionModal = val)"
    >
      <template #body>
        <UForm :state="editTransitionFormData" class="space-y-4">
          <UFormField label="From State" required>
            <USelect
              v-model="editTransitionFormData.from_state_id"
              :items="
                (workflow?.state_links || []).map((sl: any) => ({
                  value: sl.state_id,
                  label: sl.state_label,
                }))
              "
              placeholder="Select from state"
              class="w-full"
            />
          </UFormField>

          <UFormField label="Action" required>
            <USelect
              v-model="editTransitionFormData.action_id"
              :items="
                globalActions.map((a: any) => ({
                  value: a.id,
                  label: a.label,
                }))
              "
              placeholder="Select action"
              class="w-full"
            />
          </UFormField>

          <UFormField label="To State" required>
            <USelect
              v-model="editTransitionFormData.to_state_id"
              :items="
                (workflow?.state_links || []).map((sl: any) => ({
                  value: sl.state_id,
                  label: sl.state_label,
                }))
              "
              placeholder="Select to state"
              class="w-full"
            />
          </UFormField>

          <UFormField
            label="Allowed Roles"
            hint="Leave empty to allow all roles"
          >
            <div
              class="flex flex-wrap gap-2 p-2 border border-muted rounded-md min-h-[38px]"
            >
              <template v-for="role in allRoles" :key="role.id">
                <label class="flex items-center gap-1.5 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    :checked="
                      editTransitionFormData.allowed_roles.includes(
                        role.name || role.id,
                      )
                    "
                    @change="
                      (e: Event) => {
                        const name = role.name || role.id;
                        const checked = (e.target as HTMLInputElement).checked;
                        if (checked) {
                          editTransitionFormData.allowed_roles.push(name);
                        } else {
                          editTransitionFormData.allowed_roles =
                            editTransitionFormData.allowed_roles.filter(
                              (r: string) => r !== name,
                            );
                        }
                      }
                    "
                    class="rounded"
                  />
                  {{ role.name || role.id }}
                </label>
              </template>
              <span
                v-if="!allRoles.length"
                class="text-xs text-muted-foreground"
                >No roles found</span
              >
            </div>
          </UFormField>
        </UForm>
      </template>

      <template #footer="{ close }">
        <UButton
          label="Cancel"
          color="neutral"
          variant="outline"
          @click="close"
          :disabled="saving"
        />
        <UButton
          label="Save"
          color="neutral"
          @click="handleSaveTransitionEdit"
          :loading="saving"
        />
      </template>
    </UModal>
  </div>
</template>
