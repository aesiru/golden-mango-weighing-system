<script setup lang="ts">
import type { EntityMeta, FieldMeta } from "~/composables/useApiTypes";

interface Props {
  open: boolean;
  row: Record<string, any>;
  childMeta: EntityMeta | null;
  fkField: string;
  editable?: boolean;
  linkOptions?: Record<string, { value: string; label: string }[]>;
}

const props = withDefaults(defineProps<Props>(), {
  editable: false,
  linkOptions: () => ({}),
});

const emit = defineEmits<{
  "update:open": [val: boolean];
  save: [row: Record<string, any>];
}>();

const { getEntityOptions } = useApi();
const localLinkOptions = ref<Record<string, { value: string; label: string }[]>>({});
const form = ref<Record<string, any>>({});

// Visible fields — same filtering as ChildDataGrid
const visibleFields = computed<FieldMeta[]>(() => {
  if (!props.childMeta?.fields) return [];
  return props.childMeta.fields.filter((f) => {
    if (f.hidden) return false;
    if (["id", "created_at", "updated_at"].includes(f.name)) return false;
    if (f.name === props.fkField) return false;
    if (f.name === "workflow_state") return false;
    return true;
  });
});

// Sync row data into form when row changes
watch(
  () => props.row,
  (newRow) => {
    form.value = { ...newRow };
  },
  { immediate: true, deep: true },
);

// Merge parent + local link options
const mergedLinkOptions = computed(() => ({
  ...props.linkOptions,
  ...localLinkOptions.value,
}));

const loadLinkOptions = async (_fieldName: string, linkEntity: string) => {
  if (mergedLinkOptions.value[linkEntity]) return;
  try {
    const res = await getEntityOptions(linkEntity, undefined, 200);
    if (res.status === "success") {
      localLinkOptions.value[linkEntity] = res.options || [];
    }
  } catch (err) {
    console.error(`Failed to load options for ${linkEntity}:`, err);
  }
};

const handleSave = () => {
  emit("save", { ...form.value });
  emit("update:open", false);
};

const handleClose = () => {
  emit("update:open", false);
};

const modalTitle = computed(() => {
  const label = props.childMeta?.label || "Row";
  const isNew = String(props.row?.id || "").startsWith("__new__");
  return isNew ? `New ${label}` : `${label} Details`;
});
</script>

<template>
  <UModal :open="open" :title="modalTitle" @update:open="handleClose">
    <template #body>
      <div v-if="childMeta" class="space-y-4">
        <UFormField
          v-for="field in visibleFields"
          :key="field.name"
          :label="field.label"
          :name="field.name"
          :required="field.required"
        >
          <EntityFieldRenderer
            :field="field"
            v-model="form[field.name]"
            :disabled="!editable || field.readonly"
            :link-options="mergedLinkOptions"
            :on-load-link-options="loadLinkOptions"
            :entity-name="childMeta.name"
            :form-state="form"
          />
        </UFormField>
      </div>
    </template>
    <template #footer>
      <div class="flex justify-end gap-2">
        <UButton
          label="Cancel"
          color="neutral"
          variant="outline"
          @click="handleClose"
        />
        <UButton
          v-if="editable"
          label="Apply"
          @click="handleSave"
        />
      </div>
    </template>
  </UModal>
</template>
