<script setup lang="ts">
import { h, resolveComponent } from "vue";
import type { TableColumn } from "@nuxt/ui";
import type { ModelEditorEntity } from "~/composables/useApiTypes";

const UButton = resolveComponent("UButton");
const UBadge = resolveComponent("UBadge");

const api = useApi();
const toast = useToast();
const router = useRouter();

const entities = ref<ModelEditorEntity[]>([]);
const loading = ref(true);
const searchQuery = ref("");
const selectedModule = ref<string | null>(null);

const modules = computed(() => {
  const moduleSet = new Set(entities.value.map((e) => e.module));
  return Array.from(moduleSet).sort();
});

const filteredEntities = computed(() => {
  let result = entities.value;

  if (selectedModule.value) {
    result = result.filter((e) => e.module === selectedModule.value);
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    result = result.filter(
      (e) =>
        e.name.toLowerCase().includes(query) ||
        e.label.toLowerCase().includes(query),
    );
  }

  return result;
});

// Table columns
const columns: TableColumn<ModelEditorEntity>[] = [
  {
    accessorKey: "label",
    header: "Entity",
  },
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) =>
      h(
        "code",
        { class: "text-xs bg-muted px-1.5 py-0.5 rounded" },
        row.original.name,
      ),
  },
  {
    accessorKey: "module",
    header: "Module",
    cell: ({ row }) =>
      h(UBadge, { variant: "subtle", color: "neutral", size: "sm" }, () =>
        row.original.module.replace(/_/g, " "),
      ),
  },
  {
    accessorKey: "field_count",
    header: "Fields",
  },
  {
    id: "actions",
    header: "",
    cell: ({ row }) =>
      h(UButton, {
        icon: "i-lucide-pencil",
        variant: "ghost",
        size: "xs",
        onClick: () => editEntity(row.original.name),
      }),
  },
];

const loadEntities = async () => {
  loading.value = true;
  try {
    const response = await api.getModelEditorEntities();
    if (response.status === "success") {
      entities.value = response.data;
    } else {
      toast.add({
        title: "Error",
        description: "Failed to load entities",
        color: "error",
      });
    }
  } catch (error: any) {
    toast.add({
      title: "Error",
      description: error.message || "Failed to load entities",
      color: "error",
    });
  } finally {
    loading.value = false;
  }
};

const reloadMetadata = async () => {
  try {
    const response = await api.reloadMetadataRegistry();
    if (response.status === "success") {
      toast.add({
        title: "Success",
        description: `Reloaded ${response.data.entity_count} entities`,
        color: "success",
      });
      await loadEntities();
    }
  } catch (error: any) {
    toast.add({
      title: "Error",
      description: error.message || "Failed to reload metadata",
      color: "error",
    });
  }
};

const editEntity = (entityName: string) => {
  router.push(`/model-editor/${entityName}`);
};

onMounted(() => {
  loadEntities();
});

definePageMeta({ middleware: "auth" as any });
</script>

<template>
  <div class="space-y-6 p-6">
    <!-- Header -->
    <div class="flex items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <h2 class="text-xl font-bold">Entity Models</h2>
        <UBadge variant="subtle">
          {{ filteredEntities.length }}
        </UBadge>
      </div>

      <div class="flex items-center gap-3">
        <UButton
          icon="i-lucide-refresh-cw"
          variant="outline"
          @click="reloadMetadata"
        >
          Reload Metadata
        </UButton>
        <UButton
          icon="i-lucide-git-branch"
          variant="outline"
          to="/model-editor/migrations"
        >
          Migrations
        </UButton>
      </div>
    </div>

    <div class="">
      <!-- Table Toolbar -->
      <div
        class="flex flex-wrap items-center gap-3 px-4 py-3.5 border border-muted rounded-t-lg"
      >
        <UInput
          v-model="searchQuery"
          placeholder="Search entities..."
          icon="i-lucide-search"
          class="flex-1 min-w-[150px] max-w-[300px]"
        />
        <USelectMenu
          v-model="selectedModule"
          :options="[
            { label: 'All Modules', value: null },
            ...modules.map((m) => ({ label: m.replace(/_/g, ' '), value: m })),
          ]"
          value-attribute="value"
          option-attribute="label"
          placeholder="Filter by module"
          class="w-48"
        />
        <UButton
          variant="outline"
          icon="i-lucide-refresh-cw"
          :loading="loading"
          @click="loadEntities"
        />
      </div>

      <!-- Data Table -->
      <div
        v-if="!loading && filteredEntities.length > 0"
        class="border-l border-r border-b border-muted rounded-b-lg"
      >
        <UTable
          :columns="columns"
          :data="filteredEntities"
          :loading="loading"
          class="flex-1"
        />
      </div>

      <!-- Empty State -->
      <div
        v-if="!loading && filteredEntities.length === 0"
        class="border-r border-l border-b border-muted rounded-b-lg"
      >
        <div class="text-center py-12">
          <UIcon
            name="i-lucide-inbox"
            class="h-12 w-12 mx-auto text-muted-foreground mb-4"
          />
          <h3 class="text-lg font-medium mb-2">No entities found</h3>
          <p class="text-muted-foreground mb-4">
            No entities match your current search criteria.
          </p>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div
      v-if="loading"
      class="border-r border-l border-b border-muted rounded-b-lg"
    >
      <div class="flex items-center justify-center py-12">
        <UIcon
          name="i-lucide-loader-2"
          class="animate-spin h-8 w-8 text-primary"
        />
      </div>
    </div>
  </div>
</template>
