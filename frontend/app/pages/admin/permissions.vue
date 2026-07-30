<script setup lang="ts">
import { h, nextTick, watch, resolveComponent } from "vue";
import { useSortable } from "@vueuse/integrations/useSortable";
import { getGroupedRowModel } from "@tanstack/vue-table";

let stopEntitySortable: (() => void) | null = null;
let stopModuleSortable: (() => void) | null = null;

const UButton = resolveComponent("UButton");
const UCheckbox = resolveComponent("UCheckbox");
const UBadge = resolveComponent("UBadge");
const UDropdownMenu = resolveComponent("UDropdownMenu");

const api = useApi();
const toast = useToast();

// Data
const roles = ref<any[]>([]);
const entityRows = ref<any[]>([]);
const globalFilter = ref("");
const permissions = ref<Record<string, any>>({});
const saving = ref(false);

// Reorder Entities Modal
const reorderEntitiesOpen = ref(false);
const reorderEntitiesSnapshot = ref<any[]>([]);
const reorderModuleSelected = ref<string | null>(null);
const reorderModuleEntities = ref<any[]>([]);
const reorderModuleEntityNames = ref<string[]>([]);
const hasEntityChanges = ref(false);
const loadingModuleEntities = ref(false);

// Reorder Modules Modal
const reorderModulesOpen = ref(false);
const reorderModulesSnapshot = ref<any[]>([]);
const reorderModuleNames = ref<string[]>([]);
const hasModuleChanges = ref(false);

const selectedRole = ref<string | null>(null);

const permissionTypes = [
  { key: "can_create", label: "C", title: "Create" },
  { key: "can_read", label: "R", title: "Read" },
  { key: "can_update", label: "U", title: "Update" },
  { key: "can_delete", label: "D", title: "Delete" },
  { key: "can_select", label: "Sel", title: "Select (Link Fields)" },
  { key: "can_export", label: "Exp", title: "Export" },
  { key: "can_import", label: "Imp", title: "Import" },
  { key: "in_sidebar", label: "S", title: "Sidebar" },
];

const groupingOptions = ref({
  groupedColumnMode: "remove" as const,
  getGroupedRowModel: getGroupedRowModel(),
});

// Methods
const loadRoles = async () => {
  try {
    const response = await api.getAdminRoles();
    roles.value = response.data || [];
  } catch (err: any) {
    toast.add({ title: "Failed to load roles", color: "error" });
  }
};

const loadEntities = async () => {
  try {
    const response = await api.getEntitiesByModule();
    entityRows.value = response.data?.rows || [];
  } catch (err: any) {
    toast.add({ title: "Failed to load entities", color: "error" });
  }
};

const loadRolePermissions = async () => {
  if (!selectedRole.value) return;
  try {
    const response = await api.getRolePermissions(selectedRole.value);
    const compact = response.data?.permissions || {};
    permissions.value = compactToMap(compact, tableRows.value);
  } catch (err: any) {
    toast.add({ title: "Failed to load permissions", color: "error" });
  }
};

const compactToMap = (
  compact: {
    can_read?: string[];
    can_create?: string[];
    can_update?: string[];
    can_delete?: string[];
    can_select?: string[];
    can_export?: string[];
    can_import?: string[];
    in_sidebar?: string[];
  },
  entities: Array<{ name?: string; label?: string }>,
) => {
  const map: Record<string, any> = {};

  const normalizeEntityKey = (incoming: string): string | null => {
    const needle = String(incoming || "").trim();
    if (!needle) return null;

    const byName = entities.find((e) => String(e?.name || "") === needle);
    if (byName?.name) return String(byName.name);

    const byLabel = entities.find((e) => String(e?.label || "") === needle);
    if (byLabel?.name) return String(byLabel.name);

    const byFormattedLabel = entities.find(
      (e) => String(e?.label || "") === formatLabel(String(e?.name || "")),
    );
    if (byFormattedLabel?.name) return String(byFormattedLabel.name);

    const lower = needle.toLowerCase();
    const byLabelCaseInsensitive = entities.find(
      (e) => String(e?.label || "").toLowerCase() === lower,
    );
    if (byLabelCaseInsensitive?.name)
      return String(byLabelCaseInsensitive.name);

    return null;
  };

  entities.forEach((entity) => {
    const entityName = String(entity?.name || "");
    if (!entityName) return;
    map[entityName] = {
      can_read: false,
      can_create: false,
      can_update: false,
      can_delete: false,
      can_select: false,
      can_export: false,
      can_import: false,
      in_sidebar: false,
    };
  });

  Object.entries(compact).forEach(([action, entityList]) => {
    if (!entityList) return;
    entityList.forEach((entity) => {
      const normalized = normalizeEntityKey(entity);
      if (normalized && map[normalized]) {
        map[normalized][action] = true;
      }
    });
  });

  return map;
};

const mapToCompact = (map: Record<string, any>) => {
  const compact = {
    can_read: [] as string[],
    can_create: [] as string[],
    can_update: [] as string[],
    can_delete: [] as string[],
    can_select: [] as string[],
    can_export: [] as string[],
    can_import: [] as string[],
    in_sidebar: [] as string[],
  };

  Object.entries(map).forEach(([entity, perms]) => {
    if (perms?.can_read) compact.can_read.push(entity);
    if (perms?.can_create) compact.can_create.push(entity);
    if (perms?.can_update) compact.can_update.push(entity);
    if (perms?.can_delete) compact.can_delete.push(entity);
    if (perms?.can_select) compact.can_select.push(entity);
    if (perms?.can_export) compact.can_export.push(entity);
    if (perms?.can_import) compact.can_import.push(entity);
    if (perms?.in_sidebar) compact.in_sidebar.push(entity);
  });

  return compact;
};

const togglePermission = (entity: string, permKey: string) => {
  if (!permissions.value[entity]) {
    permissions.value[entity] = {
      can_create: false,
      can_read: false,
      can_update: false,
      can_delete: false,
      can_select: false,
      can_export: false,
      can_import: false,
      in_sidebar: false,
    };
  }
  permissions.value[entity][permKey] = !permissions.value[entity][permKey];
};

const toggleAllForPermission = (permKey: string, value: boolean) => {
  entityNames.value.forEach((entity) => {
    if (!permissions.value[entity]) {
      permissions.value[entity] = {
        can_create: false,
        can_read: false,
        can_update: false,
        can_delete: false,
        can_select: false,
        can_export: false,
        can_import: false,
        in_sidebar: false,
      };
    }
    permissions.value[entity][permKey] = value;
  });
};

const savePermissions = async () => {
  if (!selectedRole.value) return;
  try {
    saving.value = true;
    const compact = mapToCompact(permissions.value);
    const response = await api.updateRolePermissions(
      selectedRole.value,
      compact,
    );
    if (response.status === "success") {
      toast.add({ title: response.message, color: "success" });
    } else {
      toast.add({ title: response.message, color: "error" });
    }
  } catch (err: any) {
    toast.add({ title: "Failed to save", color: "error" });
  } finally {
    saving.value = false;
  }
};

// Reorder Entities Modal
const reorderEntitiesContainer = ref<HTMLElement | null>(null);

const openReorderEntitiesModal = () => {
  reorderEntitiesSnapshot.value = JSON.parse(JSON.stringify(entityRows.value));
  reorderModuleSelected.value = null;
  reorderModuleEntities.value = [];
  reorderModuleEntityNames.value = [];
  hasEntityChanges.value = false;
  reorderEntitiesOpen.value = true;
};

const closeReorderEntitiesModal = () => {
  reorderEntitiesOpen.value = false;
  reorderModuleSelected.value = null;
  reorderModuleEntities.value = [];
  reorderModuleEntityNames.value = [];
  hasEntityChanges.value = false;
};

const loadModuleEntities = async (moduleName: string) => {
  try {
    loadingModuleEntities.value = true;
    const response = await api.getModuleEntities(moduleName);
    if (response.status === "success") {
      reorderModuleEntities.value = response.data || [];
      reorderModuleEntityNames.value = reorderModuleEntities.value.map(
        (e) => e.name,
      );
    } else {
      toast.add({ title: "Failed to load module entities", color: "error" });
      // Fallback to current data
      reorderModuleEntityNames.value = entityRows.value
        .filter((r) => (r?.module ?? "Other") === moduleName)
        .map((r) => r.name);
    }
  } catch (err: any) {
    toast.add({ title: "Failed to load module entities", color: "error" });
    // Fallback to current data
    reorderModuleEntityNames.value = entityRows.value
      .filter((r) => (r?.module ?? "Other") === moduleName)
      .map((r) => r.name);
  } finally {
    loadingModuleEntities.value = false;
  }
};

const applyEntityReordering = () => {
  const moduleName = reorderModuleSelected.value;
  if (!moduleName) return;

  const moduleRows = entityRows.value.filter(
    (r) => (r?.module ?? "Other") === moduleName,
  );
  const moduleRowsByName = new Map<string, any>(
    moduleRows.map((r) => [r.name, r]),
  );

  const reorderedModuleRows: any[] = [];
  reorderModuleEntityNames.value.forEach((name) => {
    const row = moduleRowsByName.get(name);
    if (row) reorderedModuleRows.push(row);
  });

  const firstIndex = entityRows.value.findIndex(
    (r) => (r?.module ?? "Other") === moduleName,
  );
  if (firstIndex === -1) return;

  const before = entityRows.value
    .slice(0, firstIndex)
    .filter((r) => (r?.module ?? "Other") !== moduleName);
  const after = entityRows.value
    .slice(firstIndex)
    .filter((r) => (r?.module ?? "Other") !== moduleName);

  entityRows.value = [...before, ...reorderedModuleRows, ...after];
};

const saveReorderEntitiesModal = async () => {
  const moduleName = reorderModuleSelected.value;
  if (!moduleName) return;

  try {
    saving.value = true;

    // Save using new module-scoped API
    const res = await api.updateModuleEntityOrder({
      module: moduleName,
      entity_names: reorderModuleEntityNames.value,
    });

    hasEntityChanges.value = false;

    // Reload entities to get the updated order from backend
    await loadEntities();

    toast.add({ title: res.message, color: "success" });
    closeReorderEntitiesModal();
  } catch (err: any) {
    toast.add({
      title: err.message || "Failed to save entity order",
      color: "error",
    });
  } finally {
    saving.value = false;
  }
};

const cancelReorderEntitiesModal = () => {
  entityRows.value = JSON.parse(JSON.stringify(reorderEntitiesSnapshot.value));
  hasEntityChanges.value = false;
  closeReorderEntitiesModal();
};

// Reorder Modules Modal
const openReorderModulesModal = () => {
  reorderModulesSnapshot.value = JSON.parse(JSON.stringify(entityRows.value));
  const order = getModuleOrder();
  reorderModuleNames.value = [...order];
  hasModuleChanges.value = false;
  reorderModulesOpen.value = true;
};

const closeReorderModulesModal = () => {
  reorderModulesOpen.value = false;
  reorderModuleNames.value = [];
  hasModuleChanges.value = false;
};

// Reorder Modules Modal
const reorderModulesContainer = ref<HTMLElement | null>(null);

const applyModuleReordering = () => {
  const moduleOrder = reorderModuleNames.value;
  const byModule = new Map<string, any[]>();

  entityRows.value.forEach((row) => {
    const m = row?.module ?? "Other";
    if (!byModule.has(m)) byModule.set(m, []);
    byModule.get(m)!.push(row);
  });

  entityRows.value = moduleOrder.flatMap((m) => byModule.get(m) || []);
};

const saveReorderModulesModal = async () => {
  try {
    saving.value = true;
    applyModuleReordering();

    // Update module order only
    await api.updateModuleOrder({ modules: reorderModuleNames.value });

    // Do NOT update entity order when reordering modules (entity order stays intact from last entity reorder)
    hasModuleChanges.value = false;

    // Reload entities to get the updated order from backend
    await loadEntities();

    closeReorderModulesModal();
  } catch (err: any) {
    toast.add({
      title: err.message || "Failed to save module order",
      color: "error",
    });
  } finally {
    saving.value = false;
  }
};

const cancelReorderModulesModal = () => {
  entityRows.value = JSON.parse(JSON.stringify(reorderModulesSnapshot.value));
  hasModuleChanges.value = false;
  closeReorderModulesModal();
};

const getModuleOrder = () => {
  const moduleOrder: string[] = [];
  const seen = new Set<string>();
  entityRows.value.forEach((row) => {
    const moduleName = row?.module ?? "Other";
    if (!seen.has(moduleName)) {
      moduleOrder.push(moduleName);
      seen.add(moduleName);
    }
  });
  return moduleOrder;
};

// Computed properties
const tableRows = computed({
  get: () => {
    return entityRows.value.map((entity) => ({
      ...entity,
      label: entity.label ?? formatLabel(entity.name),
    }));
  },
  set: (newRows) => {
    entityRows.value = newRows;
  },
});

const entityNames = computed(() => {
  const names = tableRows.value.map((r) => r?.name).filter(Boolean);
  return Array.from(new Set(names));
});

const moduleOptions = computed(() => {
  const mods = entityRows.value.map((r) => r?.module ?? "Other");
  return Array.from(new Set(mods)).sort();
});

const formatLabel = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (m: string) => m.toUpperCase());

const showTable = computed(() => !!selectedRole.value);

const modeMenuItems = computed(() => [
  {
    label: "Reorder Entities",
    icon: "i-lucide-move-vertical",
    onSelect: () => openReorderEntitiesModal(),
  },
  {
    label: "Reorder Modules",
    icon: "i-lucide-layers",
    onSelect: () => openReorderModulesModal(),
  },
]);

// Columns definition
const matrixColumns = computed(() => [
  {
    accessorKey: "module",
    header: "",
    cell: () => null,
  },
  {
    accessorKey: "label",
    header: "Entity",
    cell: ({ row }: { row: any }) => {
      if (row.getIsGrouped()) {
        return h("div", { class: "flex items-center" }, [
          h("span", {
            class: "inline-block",
            style: { width: `calc(${row.depth} * 1rem)` },
          }),
          h(UButton, {
            variant: "outline",
            color: "neutral",
            class: "mr-2",
            size: "xs",
            icon: row.getIsExpanded() ? "i-lucide-minus" : "i-lucide-plus",
            onClick: () => row.toggleExpanded(),
          }),
          h("strong", {}, row.original.module),
          h(
            UBadge,
            {
              color: "secondary",
              variant: "solid",
              size: "sm",
              class: "ml-2 font-bold rounded-full",
            },
            () => `${row.subRows.length}`,
          ),
        ]);
      }
      return h("span", { class: "text-sm font-medium" }, row.original.label);
    },
  },
  ...permissionTypes.map((pt) => ({
    accessorKey: pt.key,
    header: () =>
      h("div", { class: "flex items-center justify-center gap-2" }, [
        h("span", { class: "text-xs font-medium", title: pt.title }, pt.label),
        h(UCheckbox, {
          size: "sm",
          modelValue:
            Object.keys(permissions.value).length > 0 &&
            Object.keys(permissions.value).every(
              (e) => permissions.value[e]?.[pt.key],
            ),
          "onUpdate:modelValue": (v: boolean) =>
            toggleAllForPermission(pt.key, !!v),
        }),
      ]),
    class: "text-center",
    cell: ({ row }: { row: any }) => {
      if (row.getIsGrouped()) return null;
      return h("div", { class: "flex justify-center" }, [
        h(UCheckbox, {
          size: "sm",
          modelValue: permissions.value[row.original.name]?.[pt.key] || false,
          "onUpdate:modelValue": () =>
            togglePermission(row.original.name, pt.key),
        }),
      ]);
    },
  })),
]);

// Watchers
watch(selectedRole, () => loadRolePermissions());

watch(reorderModuleSelected, async (m) => {
  if (!m) return;

  await loadModuleEntities(m);
  await nextTick();

  stopEntitySortable?.();

  // Ensure container exists before initializing sortable
  if (!reorderEntitiesContainer.value) {
    return;
  }

  try {
    const { stop } = useSortable(
      reorderEntitiesContainer,
      reorderModuleEntityNames,
      {
        animation: 150,
        ghostClass: "opacity-50",
        onEnd(evt: { oldIndex: number; newIndex: number }) {
          // Manual array sync to ensure Vue reactivity
          const item = reorderModuleEntityNames.value[evt.oldIndex];
          if (item) {
            reorderModuleEntityNames.value.splice(evt.oldIndex, 1);
            reorderModuleEntityNames.value.splice(evt.newIndex, 0, item);
          }
          hasEntityChanges.value = true;
        },
      },
    );

    stopEntitySortable = stop;
  } catch (error) {
    // Silently handle sortable initialization errors
  }
});

watch(reorderModulesOpen, async (open) => {
  if (!open) return;

  // Wait for DOM to be fully rendered
  await nextTick();
  await nextTick(); // Double tick to ensure modal content is rendered

  stopModuleSortable?.();

  // Ensure container exists before initializing sortable
  if (!reorderModulesContainer.value) {
    return;
  }

  try {
    const { stop } = useSortable(reorderModulesContainer, reorderModuleNames, {
      animation: 150,
      ghostClass: "opacity-50",
      // Remove onUpdate - handle in onEnd instead for reliable array mutation
      onEnd(evt: { oldIndex: number; newIndex: number }) {
        // Manual array sync to ensure Vue reactivity
        const item = reorderModuleNames.value[evt.oldIndex];
        if (item) {
          reorderModuleNames.value.splice(evt.oldIndex, 1);
          reorderModuleNames.value.splice(evt.newIndex, 0, item);
        }
        hasModuleChanges.value = true;
      },
    });

    stopModuleSortable = stop;
  } catch (error) {
    // Silently handle sortable initialization errors
  }
});

// Load data on mount
onMounted(async () => {
  await Promise.all([loadRoles(), loadEntities()]);
  await nextTick();
  await nextTick();
});

definePageMeta({ title: "Role Permissions" });
</script>

<template>
  <div class="space-y-6">
    <!-- Reorder Entities Modal -->
    <UModal v-model:open="reorderEntitiesOpen" title="Reorder Entities">
      <template #body>
        <div class="space-y-4">
          <UInputMenu
            v-model="reorderModuleSelected"
            :items="moduleOptions.map((m) => ({ value: m, label: m }))"
            value-key="value"
            placeholder="Select a module"
            class="w-full"
          />

          <div
            v-if="reorderModuleSelected"
            ref="reorderEntitiesContainer"
            class="space-y-2 overflow-y-auto"
          >
            <div
              v-if="loadingModuleEntities"
              class="flex items-center justify-center py-4"
            >
              <span class="text-sm text-muted-foreground"
                >Loading entities...</span
              >
            </div>
            <div
              v-for="name in reorderModuleEntityNames"
              v-else
              :key="name"
              class="flex items-center gap-2 border border-accented rounded-md px-3 py-2 cursor-move hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
            >
              <span class="text-sm font-medium flex-1">
                {{
                  reorderModuleEntities.find((e) => e.name === name)?.label ||
                  entityRows.find((e) => e.name === name)?.label ||
                  formatLabel(name)
                }}
              </span>
              <span class="text-xs text-muted-foreground">⋮⋮</span>
            </div>
          </div>
        </div>
      </template>

      <template #footer="{ close }">
        <div class="flex justify-end gap-2">
          <UButton
            label="Cancel"
            color="neutral"
            variant="outline"
            size="md"
            @click="
              () => {
                cancelReorderEntitiesModal();
                close();
              }
            "
          />
          <UButton
            label="Save"
            color="neutral"
            size="md"
            :loading="saving"
            :disabled="!reorderModuleSelected || !hasEntityChanges"
            @click="saveReorderEntitiesModal"
          />
        </div>
      </template>
    </UModal>

    <!-- Reorder Modules Modal -->
    <UModal v-model:open="reorderModulesOpen" title="Reorder Modules">
      <template #body>
        <div ref="reorderModulesContainer" class="space-y-2 overflow-y-auto">
          <div
            v-for="name in reorderModuleNames"
            :key="name"
            class="flex items-center gap-2 border border-accented rounded-md px-3 py-2 cursor-move hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
          >
            <span class="text-sm font-medium flex-1">{{ name }}</span>
            <span class="text-xs text-muted-foreground">⋮⋮</span>
          </div>
        </div>
      </template>

      <template #footer="{ close }">
        <div class="flex justify-end gap-2">
          <UButton
            label="Cancel"
            color="neutral"
            variant="outline"
            size="md"
            @click="
              () => {
                cancelReorderModulesModal();
                close();
              }
            "
          />
          <UButton
            label="Save"
            color="neutral"
            size="md"
            :loading="saving"
            :disabled="!hasModuleChanges"
            @click="saveReorderModulesModal"
          />
        </div>
      </template>
    </UModal>

    <div class="space-y-4 border border-accented rounded-lg bg-card">
      <div
        class="flex items-center justify-between gap-4 border-b border-accented py-3.5 px-4"
      >
        <!-- Role Selection -->
        <div class="flex items-center gap-3">
          <UDropdownMenu
            :items="[modeMenuItems]"
            :popper="{ placement: 'bottom-start' }"
            class="flex-shrink-0"
          >
            <UButton
              icon="i-lucide-more-vertical"
              variant="soft"
              color="neutral"
              size="md"
            />
          </UDropdownMenu>
          <UInputMenu
            v-model="selectedRole"
            :items="roles.map((r) => ({ value: r.id, label: r.name }))"
            value-key="value"
            placeholder="Select a role"
            class="w-64"
          />

          <UInput
            icon="i-lucide-search"
            v-model="globalFilter"
            placeholder="Filter entities"
            class="max-w-xs"
          />
        </div>

        <UButton
          v-if="selectedRole"
          @click="savePermissions"
          size="md"
          color="primary"
          :loading="saving"
        >
          Save
        </UButton>
      </div>

      <div v-if="!showTable" class="flex items-center justify-center py-12">
        <div class="text-center">
          <p class="text-muted-foreground text-sm">No role selected</p>
          <p class="text-xs text-muted-foreground mt-1">
            Select a role to view and manage permissions
          </p>
        </div>
      </div>
      <div v-else class="overflow-x-auto">
        <UTable
          v-model:global-filter="globalFilter"
          sticky
          :grouping="['module']"
          :grouping-options="groupingOptions"
          :data="tableRows"
          :columns="matrixColumns"
          :ui="{ td: 'empty:p-0' }"
        />
      </div>
    </div>
  </div>
</template>
