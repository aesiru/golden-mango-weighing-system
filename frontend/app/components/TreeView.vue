<script setup lang="ts">
import type { TreeItem } from "@nuxt/ui";
import type { EntityMeta, FieldMeta } from "~/composables/useApiTypes";

const props = defineProps<{
  data: any[];
  entityMeta: EntityMeta | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  view: [row: any];
  edit: [row: any];
  delete: [row: any];
}>();

const { getParentFieldName } = useTreeView();
const itemMap = ref<Map<string | number, any>>(new Map());

const titleField = computed(() => props.entityMeta?.title_field || "name");
const parentField = computed(() => {
  return (
    props.entityMeta?.tree_parent_field ||
    getParentFieldName(props.entityMeta) ||
    "parent_id"
  );
});

const treeItems = computed<TreeItem[]>(() => {
  if (!props.data.length) return [];

  itemMap.value.clear();
  const roots: any[] = [];

  props.data.forEach((item) => {
    itemMap.value.set(item.id, {
      ...item,
      children: [],
    });
  });

  props.data.forEach((item) => {
    const parentId = item[parentField.value];
    if (!parentId) {
      roots.push(itemMap.value.get(item.id));
    } else {
      const parent = itemMap.value.get(parentId);
      if (parent) {
        if (!parent.children) parent.children = [];
        parent.children.push(itemMap.value.get(item.id));
      }
    }
  });

  return buildTreeItems(roots);
});

const buildTreeItems = (items: any[]): TreeItem[] => {
  return items.map((item) => ({
    label: item[titleField.value] || `Item ${item.id}`,
    id: item.id,
    defaultExpanded: true,
    children:
      item.children?.length > 0 ? buildTreeItems(item.children) : undefined,
  }));
};

const handleSelect = (item: TreeItem) => {
  const originalItem = itemMap.value.get(item.id);
  if (originalItem) {
    emit("view", originalItem);
  }
};
</script>

<template>
  <div class="h-full min-h-0 flex flex-col gap-4">
    <div v-if="loading" class="space-y-3">
      <USkeleton class="h-10 w-full" />
      <USkeleton class="h-10 w-11/12" />
      <USkeleton class="h-10 w-10/12" />
    </div>

    <div
      v-else-if="treeItems.length === 0"
      class="text-center py-12 rounded-lg border border-muted"
    >
      <UIcon
        name="i-lucide-inbox"
        class="h-12 w-12 mx-auto text-muted-foreground mb-4"
      />
      <h3 class="text-lg font-medium mb-2">No records found</h3>
      <p class="text-muted-foreground">
        Get started by creating a new {{ entityMeta?.label || "record" }}.
      </p>
    </div>

    <div
      v-else
      class="flex-1 min-h-0 rounded-lg border border-muted p-4 overflow-y-auto"
    >
      <UTree :items="treeItems" @select="handleSelect" />
    </div>
  </div>
</template>
