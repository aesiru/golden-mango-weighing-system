<script setup lang="ts">
import type {
  EntityMetadata,
  FieldDefinition,
  LinkDefinition,
  ChildDefinition,
  ChangeItem,
  ModelEditorEntity,
  SyncResultData,
} from "~/composables/useApiTypes";

// Static field types - no API call needed
const FIELD_TYPES = [
  { value: "string", label: "String", description: "Text field" },
  { value: "text", label: "Text", description: "Long text field" },
  { value: "int", label: "Integer", description: "Whole number" },
  { value: "float", label: "Float", description: "Decimal number" },
  { value: "boolean", label: "Boolean", description: "True/False" },
  { value: "date", label: "Date", description: "Date only" },
  { value: "datetime", label: "DateTime", description: "Date and time" },
  {
    value: "link",
    label: "Link",
    description: "Foreign key to another entity",
  },
  {
    value: "parent_child_link",
    label: "Parent-Child Link",
    description: "Grouped selection by parent",
  },
  {
    value: "query_link",
    label: "Query Link",
    description: "Dynamic query-based options",
  },
  { value: "select", label: "Select", description: "Dropdown selection" },
  { value: "email", label: "Email", description: "Email address" },
  { value: "phone", label: "Phone", description: "Phone number" },
  { value: "currency", label: "Currency", description: "Money value" },
  { value: "percent", label: "Percent", description: "Percentage value" },
  { value: "image", label: "Image", description: "Image upload" },
  { value: "file", label: "File", description: "File attachment" },
];

const route = useRoute();
const router = useRouter();
const api = useApi();
const toast = useToast();

const entityName = computed(() => route.params.entity as string);

const metadata = ref<EntityMetadata | null>(null);
const originalMetadata = ref<EntityMetadata | null>(null);
const loading = ref(true);
const saving = ref(false);
const lastSyncResult = ref<SyncResultData | null>(null);
const previewChanges = ref<ChangeItem[]>([]);
const showPreview = ref(false);
const selectedFieldIndex = ref<number | null>(null);
const selectedLinkIndex = ref<number | null>(null);
const selectedChildIndex = ref<number | null>(null);
const activeTab = ref("fields");
const allEntities = ref<ModelEditorEntity[]>([]);
const searchFieldsText = ref("");
const editableWhenText = ref("");
const canAddChildrenWhenText = ref("");

// Helper methods for search_fields
const formatSearchFieldsForEdit = (fields: string[] | undefined): string => {
  if (!fields || !Array.isArray(fields)) return "";
  return fields.join(", ");
};

const updateSearchFields = (text: string) => {
  if (!metadata.value) return;
  const fields = text
    .split(",")
    .map((f) => f.trim())
    .filter((f) => f);
  metadata.value.search_fields = fields.length ? fields : undefined;
};

// Helper methods for form_state
const formatWorkflowStatesForEdit = (
  states:
    | string[]
    | { workflow_state?: string[] }
    | Record<string, string[]>
    | null
    | undefined,
): string => {
  if (!states) return "";
  if (Array.isArray(states)) return states.join(", ");
  const wf = (states as any).workflow_state;
  if (Array.isArray(wf)) return wf.join(", ");
  const firstKey = Object.keys(states)[0];
  if (firstKey && Array.isArray((states as any)[firstKey])) {
    return ((states as any)[firstKey] as string[]).join(", ");
  }
  return "";
};

const parseWorkflowStatesFromEdit = (text: string): string[] => {
  if (!text) return [];
  return text
    .split(",")
    .map((f) => f.trim())
    .filter((f) => f);
};

const updateEditableWhen = (text: string) => {
  if (!metadata.value) return;
  if (!metadata.value.form_state) metadata.value.form_state = {};
  const states = parseWorkflowStatesFromEdit(text);
  metadata.value.form_state.editable_when = states.length ? states : undefined;
};

const updateCanAddChildrenWhen = (text: string) => {
  if (!metadata.value) return;
  if (!metadata.value.form_state) metadata.value.form_state = {};
  const states = parseWorkflowStatesFromEdit(text);
  metadata.value.form_state.can_add_children_when = states.length
    ? states
    : undefined;
};

const updateRelationShowWhen = (text: string) => {
  if (!selectedLinkForEditing.value) return;
  const states = parseWorkflowStatesFromEdit(text);
  selectedLinkForEditing.value.show_when = states.length
    ? ({ workflow_state: states } as any)
    : undefined;
};

const updateRelationHideWhen = (text: string) => {
  if (!selectedLinkForEditing.value) return;
  const states = parseWorkflowStatesFromEdit(text);
  selectedLinkForEditing.value.hide_when = states.length
    ? ({ workflow_state: states } as any)
    : undefined;
};

const updateFieldShowWhen = (text: string) => {
  if (!selectedFieldForEditing.value) return;
  const states = parseWorkflowStatesFromEdit(text);
  selectedFieldForEditing.value.show_when = states.length
    ? ({ workflow_state: states } as any)
    : undefined;
};

const updateFieldEditableWhen = (text: string) => {
  if (!selectedFieldForEditing.value) return;
  const states = parseWorkflowStatesFromEdit(text);
  (selectedFieldForEditing.value as any).editable_when = states.length
    ? { workflow_state: states }
    : undefined;
};

const updateFieldRequiredWhen = (text: string) => {
  if (!selectedFieldForEditing.value) return;
  const states = parseWorkflowStatesFromEdit(text);
  (selectedFieldForEditing.value as any).required_when = states.length
    ? { workflow_state: states }
    : undefined;
};

// Initialize form state texts when metadata loads
watch(
  metadata,
  (newMetadata) => {
    if (!newMetadata) return;

    // Update form_state texts
    if (newMetadata.form_state) {
      editableWhenText.value = formatWorkflowStatesForEdit(
        newMetadata.form_state.editable_when,
      );
      canAddChildrenWhenText.value = formatWorkflowStatesForEdit(
        newMetadata.form_state.can_add_children_when,
      );
    } else {
      // Initialize empty form_state if it doesn't exist
      newMetadata.form_state = {
        editable_when: undefined,
        can_add_children_when: undefined,
      };
      editableWhenText.value = "";
      canAddChildrenWhenText.value = "";
    }
  },
  { immediate: true },
);

// Computed states
const hasChanges = computed(() => {
  if (!metadata.value || !originalMetadata.value) return false;
  return (
    JSON.stringify(metadata.value) !== JSON.stringify(originalMetadata.value)
  );
});

// Computed properties for safe selected item access
const selectedFieldForEditing = computed(() => {
  if (selectedFieldIndex.value === null || !metadata.value?.fields) return null;
  return metadata.value.fields[selectedFieldIndex.value] ?? null;
});

const selectedLinkForEditing = computed(() => {
  if (selectedLinkIndex.value === null || !metadata.value?.links) return null;
  return metadata.value.links[selectedLinkIndex.value] ?? null;
});

// Entity options for link fields
const entityOptions = computed(() => {
  return allEntities.value.map((e) => ({
    value: e.name,
    label: e.label,
    module: e.module,
  }));
});

// Computed property for the selected link entity object
const selectedLinkEntity = computed({
  get: () => {
    if (!selectedFieldForEditing.value?.link_entity) return undefined;
    return (
      entityOptions.value.find(
        (opt) => opt.value === selectedFieldForEditing.value!.link_entity,
      ) || undefined
    );
  },
  set: (value) => {
    if (selectedFieldForEditing.value) {
      selectedFieldForEditing.value.link_entity = value?.value || "";
    }
  },
});

// Watch for tab changes to clear selections
watch(activeTab, (newTab) => {
  if (newTab !== "fields") {
    selectedFieldIndex.value = null;
  }
  if (newTab !== "links") {
    selectedLinkIndex.value = null;
  }
  if (newTab !== "children") {
    selectedChildIndex.value = null;
  }
});

// Primary action button logic
const primaryAction = computed(() => {
  if (hasChanges.value) {
    return {
      label: "Save",
      action: save,
      icon: "i-lucide-save",
      loading: saving.value,
    };
  }
  return {
    label: "In Sync",
    action: () => {},
    icon: "i-lucide-check",
    loading: false,
    disabled: true,
  };
});

const secondaryActions = computed(() => {
  if (!hasChanges.value) return [];
  return [
    {
      label: "Save & Sync",
      icon: "i-lucide-database",
      click: saveAndSync,
    },
  ];
});

const loadEntity = async () => {
  loading.value = true;
  try {
    const [entityResponse, entitiesResponse] = await Promise.all([
      api.getModelEditorEntity(entityName.value),
      api.getModelEditorEntities(),
    ]);

    if (entityResponse.status === "success") {
      metadata.value = JSON.parse(JSON.stringify(entityResponse.data.metadata));

      // Convert numeric boolean values to actual booleans
      if (metadata.value && metadata.value.fields) {
        metadata.value.fields.forEach((field) => {
          if ("required" in field) field.required = Boolean(field.required);
          if ("readonly" in field) field.readonly = Boolean(field.readonly);
          if ("hidden" in field) field.hidden = Boolean(field.hidden);
          if ("unique" in field) field.unique = Boolean(field.unique);
          if ("nullable" in field) field.nullable = Boolean(field.nullable);
          if ("in_list_view" in field)
            field.in_list_view = Boolean(field.in_list_view);
        });
      }

      // Ensure links and children arrays exist for reactivity
      if (metadata.value && !metadata.value.links) {
        metadata.value.links = [];
      }
      if (metadata.value && !metadata.value.children) {
        metadata.value.children = [];
      }

      originalMetadata.value = JSON.parse(
        JSON.stringify(entityResponse.data.metadata),
      );

      // Also convert in original metadata
      if (originalMetadata.value && originalMetadata.value.fields) {
        originalMetadata.value.fields.forEach((field) => {
          if ("required" in field) field.required = Boolean(field.required);
          if ("readonly" in field) field.readonly = Boolean(field.readonly);
          if ("hidden" in field) field.hidden = Boolean(field.hidden);
          if ("unique" in field) field.unique = Boolean(field.unique);
          if ("nullable" in field) field.nullable = Boolean(field.nullable);
          if ("in_list_view" in field)
            field.in_list_view = Boolean(field.in_list_view);
        });
      }

      // Ensure links and children arrays exist in original as well
      if (originalMetadata.value && !originalMetadata.value.links) {
        originalMetadata.value.links = [];
      }
      if (originalMetadata.value && !originalMetadata.value.children) {
        originalMetadata.value.children = [];
      }

      // Initialize search_fields text
      searchFieldsText.value = formatSearchFieldsForEdit(
        metadata.value?.search_fields,
      );
    } else {
      toast.add({
        title: "Error",
        description: "Failed to load entity",
        color: "error",
      });
    }

    if (entitiesResponse.status === "success") {
      allEntities.value = entitiesResponse.data;
    }
  } catch (error: any) {
    toast.add({
      title: "Error",
      description: error.message || "Failed to load entity",
      color: "error",
    });
  } finally {
    loading.value = false;
  }
};

const preview = async () => {
  if (!metadata.value) return;
  try {
    const response = await api.previewEntityChanges(
      entityName.value,
      metadata.value,
    );
    if (response.status === "success") {
      previewChanges.value = response.data.changes;
      showPreview.value = true;
    }
  } catch (error: any) {
    toast.add({
      title: "Error",
      description: error.message || "Failed to preview changes",
      color: "error",
    });
  }
};

const save = async () => {
  if (!metadata.value) return;
  saving.value = true;
  try {
    const response = await api.saveEntityDraft(
      entityName.value,
      metadata.value,
    );
    if (response.status === "success") {
      lastSyncResult.value = response.data;
      toast.add({
        title: "Saved",
        description:
          "JSON saved & registry reloaded. Run 'Save & Sync' or restart to apply schema changes.",
        color: "success",
      });
      if (response.data.warnings?.length) {
        toast.add({
          title: "Warnings",
          description: response.data.warnings.join("; "),
          color: "warning",
        });
      }
      originalMetadata.value = JSON.parse(JSON.stringify(metadata.value));
      showPreview.value = false;
      await loadEntity();
    } else {
      toast.add({
        title: "Error",
        description: response.message || "Failed to save",
        color: "error",
      });
    }
  } catch (error: any) {
    toast.add({
      title: "Error",
      description: error.message || "Failed to save",
      color: "error",
    });
  } finally {
    saving.value = false;
  }
};

const saveAndSync = async () => {
  if (!metadata.value) return;
  saving.value = true;
  try {
    const response = await api.saveEntity(entityName.value, metadata.value);
    if (response.status === "success") {
      lastSyncResult.value = response.data;
      const steps: string[] = [];
      if (response.data.json_saved) steps.push("JSON saved");
      if (response.data.registry_reloaded) steps.push("registry reloaded");
      if (response.data.model_updated) steps.push("model updated");
      if (response.data.migration_generated) steps.push("migration generated");
      if (response.data.migration_applied) steps.push("migration applied");
      toast.add({
        title: "Synced",
        description: steps.length
          ? steps.join(" → ")
          : "Metadata saved (no schema changes)",
        color: "success",
      });
      if (response.data.warnings?.length) {
        toast.add({
          title: "Warnings",
          description: response.data.warnings.join("; "),
          color: "warning",
        });
      }
      originalMetadata.value = JSON.parse(JSON.stringify(metadata.value));
      showPreview.value = false;
      await loadEntity();
    } else {
      toast.add({
        title: "Error",
        description: response.message || "Failed to save",
        color: "error",
      });
    }
  } catch (error: any) {
    toast.add({
      title: "Error",
      description: error.message || "Failed to save",
      color: "error",
    });
  } finally {
    saving.value = false;
  }
};

// Helper functions for SELECT field options editing
const formatOptionsForEdit = (options: any[] | undefined): string => {
  if (!options || !Array.isArray(options)) return "";
  return options
    .map((opt: any) => {
      if (typeof opt === "object" && opt !== null) {
        return (opt.label ?? opt.value ?? "").toString();
      }
      return String(opt ?? "");
    })
    .filter((val: string) => val.trim().length > 0)
    .join("\n");
};

const parseOptionsFromEdit = (text: string, field: any) => {
  if (!field) return;
  const lines = text
    .split(/\r?\n/)
    .map((line: string) => line.trim())
    .filter((line: string) => line.length > 0);
  field.options = lines.length ? lines : undefined;
};

const addField = () => {
  if (!metadata.value) return;
  const newField: FieldDefinition = {
    name: "",
    label: "",
    field_type: "string",
    required: false,
    readonly: false,
    hidden: false,
  };
  metadata.value.fields.push(newField);
  selectedFieldIndex.value = metadata.value.fields.length - 1;
};

const addLink = () => {
  if (!metadata.value) return;
  if (!metadata.value.links) {
    metadata.value.links = [];
  }
  const newLink: LinkDefinition = {
    entity: "",
    fk_field: "",
    label: "",
  };
  metadata.value.links.push(newLink);
  selectedLinkIndex.value = metadata.value.links.length - 1;
};

const removeField = (index: number) => {
  if (!metadata.value) return;
  metadata.value.fields.splice(index, 1);
  if (selectedFieldIndex.value === index) {
    selectedFieldIndex.value = null;
  } else if (
    selectedFieldIndex.value !== null &&
    selectedFieldIndex.value > index
  ) {
    selectedFieldIndex.value--;
  }
};

const removeLink = (index: number) => {
  if (!metadata.value?.links) return;
  metadata.value.links.splice(index, 1);
  if (selectedLinkIndex.value === index) {
    selectedLinkIndex.value = null;
  } else if (
    selectedLinkIndex.value !== null &&
    selectedLinkIndex.value > index
  ) {
    selectedLinkIndex.value--;
  }
};

const moveField = (index: number, direction: "up" | "down") => {
  if (!metadata.value) return;
  const newIndex = direction === "up" ? index - 1 : index + 1;
  if (newIndex < 0 || newIndex >= metadata.value.fields.length) return;

  const fields = metadata.value.fields;
  const temp = fields[index]!;
  fields[index] = fields[newIndex]!;
  fields[newIndex] = temp;

  if (selectedFieldIndex.value === index) {
    selectedFieldIndex.value = newIndex;
  } else if (selectedFieldIndex.value === newIndex) {
    selectedFieldIndex.value = index;
  }
};

const addChild = () => {
  if (!metadata.value) return;
  if (!metadata.value.children) {
    metadata.value.children = [];
  }
  const newChild: ChildDefinition = {
    entity: "",
    fk_field: "",
    label: "",
  };
  metadata.value.children.push(newChild);
  selectedChildIndex.value = metadata.value.children.length - 1;
};

const removeChild = (index: number) => {
  if (!metadata.value?.children) return;
  metadata.value.children.splice(index, 1);
  if (selectedChildIndex.value === index) {
    selectedChildIndex.value = null;
  } else if (
    selectedChildIndex.value !== null &&
    selectedChildIndex.value > index
  ) {
    selectedChildIndex.value--;
  }
};

const selectedChildForEditing = computed(() => {
  if (selectedChildIndex.value === null || !metadata.value?.children)
    return null;
  return metadata.value.children[selectedChildIndex.value] ?? null;
});

const revertChanges = () => {
  if (originalMetadata.value) {
    metadata.value = JSON.parse(JSON.stringify(originalMetadata.value));
    selectedFieldIndex.value = null;
    selectedLinkIndex.value = null;
    selectedChildIndex.value = null;
  }
};

const selectField = (index: number) => {
  selectedFieldIndex.value = index;
};

const selectLink = (index: number) => {
  selectedLinkIndex.value = index;
};

const selectChild = (index: number) => {
  selectedChildIndex.value = index;
};

onMounted(() => {
  loadEntity();
});

definePageMeta({ middleware: "auth" as any });
</script>

<template>
  <div class="space-y-4 p-6">
    <!-- Header with Status Bar -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <UButton
          icon="i-lucide-arrow-left"
          variant="ghost"
          @click="router.push('/model-editor')"
        />
        <div>
          <h1 class="text-2xl font-bold text-foreground">
            {{ metadata?.label || entityName }}
          </h1>
          <p class="text-muted-foreground text-sm">
            {{ entityName }} · {{ metadata?.module }}
          </p>
        </div>
      </div>

      <!-- Status Badges -->
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <UBadge v-if="hasChanges" color="warning" variant="subtle">
            <UIcon name="i-lucide-edit" class="w-3 h-3 mr-1" />
            Unsaved Changes
          </UBadge>
          <UBadge v-if="!hasChanges" color="success" variant="subtle">
            <UIcon name="i-lucide-check-circle" class="w-3 h-3 mr-1" />
            In Sync
          </UBadge>
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-2">
          <UButton
            v-if="hasChanges"
            icon="i-lucide-undo"
            variant="outline"
            size="sm"
            @click="revertChanges"
          >
            Revert
          </UButton>
          <UButton
            v-if="hasChanges"
            icon="i-lucide-eye"
            variant="outline"
            size="sm"
            @click="preview"
          >
            Preview
          </UButton>
          <UButton
            :icon="primaryAction.icon"
            :loading="primaryAction.loading"
            :disabled="primaryAction.disabled"
            @click="primaryAction.action"
          >
            {{ primaryAction.label }}
          </UButton>
          <UButton
            v-for="action in secondaryActions"
            :key="action.label"
            :icon="action.icon"
            :loading="saving"
            variant="outline"
            @click="action.click"
          >
            {{ action.label }}
          </UButton>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-12">
      <UIcon
        name="i-lucide-loader-2"
        class="h-8 w-8 animate-spin text-primary"
      />
    </div>

    <!-- Content with Tabs -->
    <div v-else-if="metadata">
      <!-- Tabs -->
      <UTabs
        v-model="activeTab"
        :items="[
          { label: 'Fields', value: 'fields', slot: 'fields' },
          { label: 'Relations', value: 'links', slot: 'links' },
          { label: 'Children', value: 'children', slot: 'children' },
          { label: 'Entity Settings', value: 'settings', slot: 'settings' },
        ]"
        class="w-full"
        variant="link"
        size="md"
      >
        <template #fields>
          <div
            class="flex justify-between border border-muted rounded-lg overflow-hidden max-h-[72vh]"
          >
            <!-- Left: Field List (3/4 width) -->
            <div class="w-5/8 flex flex-col">
              <div
                class="flex p-4 items-center justify-between border-b border-muted"
              >
                <h3 class="font-semibold">
                  Fields ({{ metadata.fields.length }})
                </h3>
                <UButton size="md" icon="i-lucide-plus" @click="addField">
                  Add Field
                </UButton>
              </div>

              <div class="space-y-1 overflow-y-auto p-4 flex-1">
                <div
                  v-for="(field, index) in metadata.fields"
                  :key="index"
                  class="flex items-center justify-between p-2 rounded cursor-pointer transition-colors border border-muted"
                  :class="{
                    'bg-primary/10 border border-primary':
                      selectedFieldIndex === index,
                    'hover:bg-muted/50': selectedFieldIndex !== index,
                  }"
                  @click="selectField(index)"
                >
                  <div class="flex items-center gap-2">
                    <div class="flex flex-col">
                      <UButton
                        size="xs"
                        variant="ghost"
                        icon="i-lucide-chevron-up"
                        :disabled="index === 0"
                        class="h-4 w-4 p-0"
                        @click.stop="moveField(index, 'up')"
                      />
                      <UButton
                        size="xs"
                        variant="ghost"
                        icon="i-lucide-chevron-down"
                        :disabled="index === metadata.fields.length - 1"
                        class="h-4 w-4 p-0"
                        @click.stop="moveField(index, 'down')"
                      />
                    </div>
                    <div>
                      <div class="font-medium text-sm">
                        {{ field.label || field.name || "(unnamed)" }}
                      </div>
                      <div class="text-xs text-muted-foreground">
                        {{ field.name }} · {{ field.field_type }}
                        <span v-if="field.required" class="text-red-500"
                          >*</span
                        >
                        <span v-if="field.hidden" class="text-orange-500 ml-1"
                          >👁️‍🗨️</span
                        >
                        <span v-if="field.readonly" class="text-blue-500 ml-1"
                          >🔒</span
                        >
                      </div>
                    </div>
                  </div>
                  <UButton
                    size="xs"
                    variant="ghost"
                    color="error"
                    icon="i-lucide-trash-2"
                    @click.stop="removeField(index)"
                  />
                </div>

                <div
                  v-if="metadata.fields.length === 0"
                  class="text-center py-8 text-muted-foreground"
                >
                  No fields. Click "Add Field" to create one.
                </div>
              </div>
            </div>

            <!-- Right: Field Editor (1/4 width with left border) -->
            <div class="w-3/8 border-l border-muted p-4 flex flex-col">
              <div
                v-if="selectedFieldForEditing"
                class="space-y-4 overflow-y-auto overflow-x-hidden flex-1"
              >
                <UFormField label="Label" name="label">
                  <UInput
                    v-model="selectedFieldForEditing.label"
                    placeholder="Field Label"
                    class="w-full"
                  />
                </UFormField>

                <UFormField label="Field Name" name="name">
                  <UInput
                    v-model="selectedFieldForEditing.name"
                    placeholder="field_name"
                    class="w-full"
                  />
                </UFormField>

                <UFormField label="Field Type" name="field_type">
                  <USelect
                    v-model="selectedFieldForEditing.field_type"
                    :items="FIELD_TYPES"
                    value-attribute="value"
                    option-attribute="label"
                    class="w-full"
                    size="md"
                    color="primary"
                    variant="outline"
                  />
                </UFormField>

                <UFormField
                  v-if="
                    (selectedFieldForEditing.field_type as string) === 'link'
                  "
                  label="Link Entity"
                  name="link_entity"
                >
                  <USelectMenu
                    v-model="selectedLinkEntity"
                    :items="entityOptions"
                    placeholder="Select entity..."
                    class="w-full"
                    size="md"
                    color="primary"
                    variant="outline"
                  >
                    <template #default="{ modelValue: value }">
                      <span v-if="value">
                        {{ value.label }}
                      </span>
                      <span v-else class="text-muted-foreground">
                        Select entity...
                      </span>
                    </template>

                    <template #item="{ item }">
                      <div class="flex flex-col gap-0.5">
                        <span class="font-medium">{{ item.label }}</span>
                        <span
                          v-if="item.module"
                          class="text-sm text-muted-foreground"
                        >
                          {{ item.module }}
                        </span>
                      </div>
                    </template>
                  </USelectMenu>
                </UFormField>

                <UFormField
                  v-if="
                    (selectedFieldForEditing.field_type as string) === 'select'
                  "
                  label="Options (one label per line)"
                  name="options"
                >
                  <UTextarea
                    :model-value="
                      formatOptionsForEdit(selectedFieldForEditing.options)
                    "
                    @update:model-value="
                      (val: string) =>
                        parseOptionsFromEdit(val, selectedFieldForEditing)
                    "
                    placeholder="Urgent&#10;High&#10;Medium&#10;Low"
                    :rows="4"
                    class="w-full font-mono text-sm"
                  />
                </UFormField>

                <template
                  v-if="
                    (selectedFieldForEditing.field_type as string) ===
                    'parent_child_link'
                  "
                >
                  <UFormField label="Child Entity" name="child_entity">
                    <USelect
                      v-model="selectedFieldForEditing.child_entity"
                      :items="entityOptions"
                      value-attribute="value"
                      option-attribute="label"
                      placeholder="Select child entity..."
                      class="w-full"
                      size="md"
                      color="primary"
                      variant="outline"
                    />
                  </UFormField>

                  <UFormField label="Parent Entity" name="parent_entity">
                    <USelect
                      v-model="selectedFieldForEditing.parent_entity"
                      :items="entityOptions"
                      value-attribute="value"
                      option-attribute="label"
                      placeholder="Select parent entity..."
                      class="w-full"
                      size="md"
                      color="primary"
                      variant="outline"
                    />
                  </UFormField>

                  <UFormField
                    label="Child Parent FK Field"
                    name="child_parent_fk_field"
                  >
                    <UInput
                      v-model="selectedFieldForEditing.child_parent_fk_field"
                      placeholder="parent_field_id"
                      class="w-full"
                    />
                  </UFormField>

                  <UFormField label="Field Name" name="name">
                    <UInput
                      v-model="selectedFieldForEditing.name"
                      placeholder="field_name"
                      class="w-full"
                    />
                  </UFormField>

                  <UFormField label="Field Type" name="field_type">
                    <USelect
                      v-model="selectedFieldForEditing.field_type"
                      :items="FIELD_TYPES"
                      value-attribute="value"
                      option-attribute="label"
                      class="w-full"
                      size="md"
                      color="primary"
                      variant="outline"
                    />
                  </UFormField>

                  <UFormField
                    v-if="
                      (selectedFieldForEditing.field_type as string) === 'link'
                    "
                    label="Link Entity"
                    name="link_entity"
                  >
                    <USelectMenu
                      v-model="selectedLinkEntity"
                      :items="entityOptions"
                      placeholder="Select entity..."
                      class="w-full"
                      size="md"
                      color="primary"
                      variant="outline"
                    >
                      <template #default="{ modelValue: value }">
                        <span v-if="value">
                          {{ value.label }}
                        </span>
                        <span v-else class="text-muted-foreground">
                          Select entity...
                        </span>
                      </template>

                      <template #item="{ item }">
                        <div class="flex flex-col gap-0.5">
                          <span class="font-medium">{{ item.label }}</span>
                          <span
                            v-if="item.module"
                            class="text-sm text-muted-foreground"
                          >
                            {{ item.module }}
                          </span>
                        </div>
                      </template>
                    </USelectMenu>
                  </UFormField>

                  <UFormField
                    v-if="
                      (selectedFieldForEditing.field_type as string) ===
                      'select'
                    "
                    label="Options (one per line: value|label)"
                    name="options"
                  >
                    <UTextarea
                      :model-value="
                        formatOptionsForEdit(selectedFieldForEditing.options)
                      "
                      @update:model-value="
                        (val) => {
                          if (!selectedFieldForEditing) return;
                          if (!selectedFieldForEditing.query) {
                            selectedFieldForEditing.query = { key: '' };
                          }
                          selectedFieldForEditing.query!.key = val;
                        }
                      "
                      placeholder="e.g., sample_test"
                      class="w-full"
                    />
                  </UFormField>
                  <p class="text-xs text-muted-foreground">
                    Whitelisted backend query key
                  </p>
                </template>

                <UFormField
                  label="Show When (workflow states)"
                  name="field_show_when"
                  hint="Comma-separated workflow states (e.g. draft, release)"
                >
                  <UTextarea
                    :model-value="
                      formatWorkflowStatesForEdit(
                        selectedFieldForEditing.show_when,
                      )
                    "
                    placeholder="draft, pending_approval"
                    :rows="2"
                    class="w-full font-mono text-sm"
                    @update:model-value="updateFieldShowWhen"
                  />
                </UFormField>

                <UFormField
                  label="Editable When (workflow states)"
                  name="field_editable_when"
                  hint="Field is editable only in these workflow states"
                >
                  <UTextarea
                    :model-value="
                      formatWorkflowStatesForEdit(
                        (selectedFieldForEditing as any).editable_when,
                      )
                    "
                    placeholder="draft, pending_review"
                    :rows="2"
                    class="w-full font-mono text-sm"
                    @update:model-value="updateFieldEditableWhen"
                  />
                </UFormField>

                <UFormField
                  label="Required When (workflow states)"
                  name="field_required_when"
                  hint="Field becomes mandatory in these workflow states"
                >
                  <UTextarea
                    :model-value="
                      formatWorkflowStatesForEdit(
                        (selectedFieldForEditing as any).required_when,
                      )
                    "
                    placeholder="pending_approval, approved"
                    :rows="2"
                    class="w-full font-mono text-sm"
                    @update:model-value="updateFieldRequiredWhen"
                  />
                </UFormField>

                <UFormField
                  label="Display Depends On"
                  name="display_depends_on"
                  hint="Expression to control field visibility, e.g. eval:doc.status=='draft'"
                >
                  <UInput
                    :model-value="
                      selectedFieldForEditing.display_depends_on ?? ''
                    "
                    @update:model-value="
                      (val: string) => {
                        if (selectedFieldForEditing)
                          selectedFieldForEditing.display_depends_on =
                            val || undefined;
                      }
                    "
                    placeholder="eval:doc.field_name=='value'"
                    class="w-full font-mono text-sm"
                  />
                </UFormField>

                <UFormField
                  label="Mandatory Depends On"
                  name="mandatory_depends_on"
                  hint="Expression to control when field is required, e.g. eval:doc.status=='approved'"
                >
                  <UInput
                    :model-value="
                      selectedFieldForEditing.mandatory_depends_on ?? ''
                    "
                    @update:model-value="
                      (val: string) => {
                        if (selectedFieldForEditing)
                          selectedFieldForEditing.mandatory_depends_on =
                            val || undefined;
                      }
                    "
                    placeholder="eval:doc.field_name=='value'"
                    class="w-full font-mono text-sm"
                  />
                </UFormField>

                <UFormField label="Default Value" name="default">
                  <UInput
                    :model-value="selectedFieldForEditing.default ?? ''"
                    @update:model-value="
                      (val: string) => {
                        if (selectedFieldForEditing)
                          selectedFieldForEditing.default = val || undefined;
                      }
                    "
                    placeholder="Default value (optional)"
                    class="w-full"
                  />
                </UFormField>

                <UFormField
                  label="Fetch From"
                  name="fetch_from"
                  hint="Use format source_field.remote_field (e.g. item.uom)"
                >
                  <UInput
                    :model-value="selectedFieldForEditing.fetch_from ?? ''"
                    @update:model-value="
                      (val: string) => {
                        if (selectedFieldForEditing)
                          selectedFieldForEditing.fetch_from = val || undefined;
                      }
                    "
                    placeholder="item.remote_field"
                    class="w-full font-mono text-sm"
                  />
                </UFormField>

                <div class="border border-muted rounded-lg p-3">
                  <p
                    class="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide"
                  >
                    Field Options
                  </p>
                  <div class="grid grid-cols-1 gap-2.5">
                    <label class="flex items-center gap-2 cursor-pointer">
                      <UCheckbox v-model="selectedFieldForEditing.required" />
                      <span class="text-sm font-medium">Required</span>
                      <span class="text-xs text-muted-foreground ml-auto"
                        >Must have a value</span
                      >
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer">
                      <UCheckbox v-model="selectedFieldForEditing.readonly" />
                      <span class="text-sm font-medium">Read Only</span>
                      <span class="text-xs text-muted-foreground ml-auto"
                        >Cannot be edited</span
                      >
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer">
                      <UCheckbox v-model="selectedFieldForEditing.hidden" />
                      <span class="text-sm font-medium">Hidden</span>
                      <span class="text-xs text-muted-foreground ml-auto"
                        >Not visible in form</span
                      >
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer">
                      <UCheckbox
                        v-model="selectedFieldForEditing.in_list_view"
                      />
                      <span class="text-sm font-medium">In List View</span>
                      <span class="text-xs text-muted-foreground ml-auto"
                        >Show in table/list</span
                      >
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer">
                      <UCheckbox v-model="selectedFieldForEditing.unique" />
                      <span class="text-sm font-medium">Unique</span>
                      <span class="text-xs text-muted-foreground ml-auto"
                        >No duplicates</span
                      >
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer">
                      <UCheckbox
                        v-model="selectedFieldForEditing.nullable"
                        :default-value="true"
                      />
                      <span class="text-sm font-medium">Nullable</span>
                      <span class="text-xs text-muted-foreground ml-auto"
                        >Allow null in DB</span
                      >
                    </label>
                  </div>
                </div>
              </div>

              <div v-else class="text-center py-12 text-muted-foreground">
                <UIcon
                  name="i-lucide-mouse-pointer-click"
                  class="h-8 w-8 mx-auto mb-2"
                />
                <p class="text-sm">Select a field to edit</p>
              </div>
            </div>
          </div>
        </template>

        <template #links>
          <div class="flex justify-between border border-muted rounded-lg">
            <!-- Left: Links List (3/4 width) -->
            <div class="w-3/4">
              <div
                class="flex p-4 items-center justify-between border-b border-muted"
              >
                <h3 class="font-semibold">
                  Relations ({{ (metadata.links || []).length }})
                </h3>
                <UButton size="md" icon="i-lucide-plus" @click="addLink">
                  Add Relation
                </UButton>
              </div>

              <div class="space-y-1 max-h-[60vh] overflow-y-auto p-4">
                <div
                  v-for="(link, index) in metadata.links || []"
                  :key="index"
                  class="flex items-center justify-between p-2 rounded cursor-pointer transition-colors border border-muted"
                  :class="{
                    'bg-primary/10 border border-primary':
                      selectedLinkIndex === index,
                    'hover:bg-muted/50': selectedLinkIndex !== index,
                  }"
                  @click="selectLink(index)"
                >
                  <div class="flex items-center gap-2">
                    <div>
                      <div class="font-medium text-sm">
                        {{ link.label || "(unnamed)" }}
                      </div>
                      <div class="text-xs text-muted-foreground">
                        {{ link.entity }} · {{ link.fk_field }}
                      </div>
                    </div>
                  </div>
                  <UButton
                    size="xs"
                    variant="ghost"
                    color="error"
                    icon="i-lucide-trash-2"
                    @click.stop="removeLink(index)"
                  />
                </div>

                <div
                  v-if="!metadata.links || metadata.links.length === 0"
                  class="text-center py-8 text-muted-foreground"
                >
                  No relations. Click "Add Relation" to create one.
                </div>
              </div>
            </div>

            <!-- Right: Link Editor (1/4 width with left border) -->
            <div class="w-1/4 border-l border-muted p-4">
              <div v-if="selectedLinkForEditing" class="space-y-4">
                <UFormField label="Label" name="label">
                  <UInput
                    v-model="selectedLinkForEditing.label"
                    placeholder="Link Label"
                    class="w-full"
                  />
                </UFormField>

                <UFormField label="Entity" name="entity">
                  <USelect
                    v-model="selectedLinkForEditing.entity"
                    :items="entityOptions"
                    value-attribute="value"
                    option-attribute="label"
                    placeholder="Select entity..."
                    class="w-full"
                    size="md"
                    color="primary"
                    variant="outline"
                  />
                </UFormField>

                <UFormField label="Foreign Key Field" name="fk_field">
                  <UInput
                    v-model="selectedLinkForEditing.fk_field"
                    placeholder="e.g., asset"
                    class="w-full"
                  />
                </UFormField>

                <UFormField
                  label="Show When (workflow states)"
                  name="relation_show_when"
                >
                  <UTextarea
                    :model-value="
                      formatWorkflowStatesForEdit(
                        selectedLinkForEditing.show_when,
                      )
                    "
                    placeholder="draft, pending_review"
                    hint="Enter workflow states separated by comma"
                    :rows="2"
                    class="w-full font-mono text-sm"
                    @update:model-value="updateRelationShowWhen"
                  />
                </UFormField>

                <UFormField
                  label="Hide When (workflow states)"
                  name="relation_hide_when"
                >
                  <UTextarea
                    :model-value="
                      formatWorkflowStatesForEdit(
                        selectedLinkForEditing.hide_when,
                      )
                    "
                    placeholder="cancelled, rejected"
                    hint="Enter workflow states separated by comma"
                    :rows="2"
                    class="w-full font-mono text-sm"
                    @update:model-value="updateRelationHideWhen"
                  />
                </UFormField>

                <UFormField label="Require Data" name="relation_require_data">
                  <USelect
                    v-model="selectedLinkForEditing.require_data"
                    :items="[
                      { label: 'None', value: null },
                      { label: 'Has Lines (count > 0)', value: 'has_lines' },
                    ]"
                    value-attribute="value"
                    option-attribute="label"
                    class="w-full"
                    size="sm"
                  />
                </UFormField>

                <div class="text-xs text-muted-foreground mt-4">
                  <p class="mb-2">
                    <strong>Tip:</strong> The foreign key field is the field in
                    the linked entity that references back to this entity.
                  </p>
                  <p>
                    For example, if linking to "asset_property", the fk_field
                    might be "asset".
                  </p>
                </div>
              </div>

              <div v-else class="text-center py-12 text-muted-foreground">
                <UIcon
                  name="i-lucide-mouse-pointer-click"
                  class="h-8 w-8 mx-auto mb-2"
                />
                <p class="text-sm">Select a link to edit</p>
              </div>
            </div>
          </div>
        </template>

        <template #children>
          <div class="flex justify-between border border-muted rounded-lg">
            <!-- Left: Children List (3/4 width) -->
            <div class="w-3/4">
              <div
                class="flex p-4 items-center justify-between border-b border-muted"
              >
                <h3 class="font-semibold">
                  Children ({{ (metadata.children || []).length }})
                </h3>
                <UButton size="md" icon="i-lucide-plus" @click="addChild">
                  Add Child
                </UButton>
              </div>

              <div class="space-y-1 max-h-[60vh] overflow-y-auto p-4">
                <div
                  v-for="(child, index) in metadata.children || []"
                  :key="index"
                  class="flex items-center justify-between p-2 rounded cursor-pointer transition-colors border border-muted"
                  :class="{
                    'bg-primary/10 border border-primary':
                      selectedChildIndex === index,
                    'hover:bg-muted/50': selectedChildIndex !== index,
                  }"
                  @click="selectChild(index)"
                >
                  <div class="flex items-center gap-2">
                    <div>
                      <div class="font-medium text-sm">
                        {{ child.label || "(unnamed)" }}
                      </div>
                      <div class="text-xs text-muted-foreground">
                        {{ child.entity }} · FK: {{ child.fk_field }}
                      </div>
                    </div>
                  </div>
                  <UButton
                    size="xs"
                    variant="ghost"
                    color="error"
                    icon="i-lucide-trash-2"
                    @click.stop="removeChild(index)"
                  />
                </div>

                <div
                  v-if="!metadata.children || metadata.children.length === 0"
                  class="text-center py-8 text-muted-foreground"
                >
                  No child tables. Click "Add Child" to define inline child
                  tables (e.g., line items).
                </div>
              </div>
            </div>

            <!-- Right: Child Editor (1/4 width with left border) -->
            <div class="w-1/4 border-l border-muted p-4">
              <div v-if="selectedChildForEditing" class="space-y-4">
                <UFormField label="Label" name="child_label">
                  <UInput
                    v-model="selectedChildForEditing.label"
                    placeholder="e.g., Lines"
                    class="w-full"
                  />
                </UFormField>

                <UFormField label="Child Entity" name="child_entity">
                  <USelect
                    v-model="selectedChildForEditing.entity"
                    :items="entityOptions"
                    value-attribute="value"
                    option-attribute="label"
                    placeholder="Select entity..."
                    class="w-full"
                    size="md"
                    color="primary"
                    variant="outline"
                  />
                </UFormField>

                <UFormField label="Foreign Key Field" name="child_fk_field">
                  <UInput
                    v-model="selectedChildForEditing.fk_field"
                    placeholder="e.g., po_id"
                    class="w-full"
                  />
                </UFormField>

                <div class="text-xs text-muted-foreground mt-4">
                  <p class="mb-2">
                    <strong>Tip:</strong> Child tables are rendered inline
                    within the parent form as editable grids (e.g., purchase
                    order lines).
                  </p>
                  <p>
                    The FK field is the column in the child entity that
                    references this parent entity's ID.
                  </p>
                </div>
              </div>

              <div v-else class="text-center py-12 text-muted-foreground">
                <UIcon
                  name="i-lucide-mouse-pointer-click"
                  class="h-8 w-8 mx-auto mb-2"
                />
                <p class="text-sm">Select a child to edit</p>
              </div>
            </div>
          </div>
        </template>

        <template #settings>
          <div class="pt-4 space-y-6">
            <!-- General Settings -->
            <div class="border border-muted rounded-lg p-4 space-y-4">
              <h3 class="text-sm font-semibold flex items-center gap-2">
                <UIcon name="i-lucide-settings" class="w-4 h-4" />
                General
              </h3>
              <div class="grid grid-cols-2 gap-4">
                <UFormField label="Label">
                  <UInput v-model="metadata.label" class="w-full" />
                </UFormField>
                <UFormField label="Title Field">
                  <USelect
                    v-model="metadata.title_field"
                    :items="
                      metadata.fields.map((f) => ({
                        label: f.label || f.name,
                        value: f.name,
                      }))
                    "
                    value-attribute="value"
                    option-attribute="label"
                    class="w-full"
                  />
                </UFormField>
                <UFormField label="Icon">
                  <UInput
                    v-model="metadata.icon"
                    placeholder="e.g., box, wrench"
                    class="w-full"
                  />
                </UFormField>
                <UFormField label="Group">
                  <UInput v-model="metadata.group" class="w-full" />
                </UFormField>
              </div>
              <UFormField
                label="Search Fields"
                hint="Comma-separated field names"
              >
                <UInput
                  v-model="searchFieldsText"
                  placeholder="asset_tag, description"
                  class="w-full font-mono text-sm"
                  @update:model-value="updateSearchFields"
                />
              </UFormField>
              <div class="flex items-center gap-4">
                <div class="flex items-center gap-2">
                  <UCheckbox
                    :model-value="!!metadata.in_sidebar"
                    @update:model-value="metadata.in_sidebar = $event ? 1 : 0"
                  />
                  <span class="text-sm">Show in Sidebar</span>
                </div>
                <div class="flex items-center gap-2">
                  <UCheckbox
                    :model-value="!!metadata.is_child_table"
                    @update:model-value="
                      (val: boolean | 'indeterminate') => {
                        if (metadata) metadata.is_child_table = val === true;
                      }
                    "
                  />
                  <span class="text-sm">Is Child Table</span>
                  <span class="text-xs text-muted-foreground"
                    >(inline line items, not standalone)</span
                  >
                </div>
              </div>
            </div>

            <!-- View Modes -->
            <div class="border border-muted rounded-lg p-4 space-y-4">
              <h3 class="text-sm font-semibold flex items-center gap-2">
                <UIcon name="i-lucide-layout-grid" class="w-4 h-4" />
                View Modes
              </h3>
              <div class="flex items-center gap-6">
                <div class="flex items-center gap-2">
                  <UCheckbox
                    :model-value="!!metadata.is_tree"
                    @update:model-value="
                      (val: boolean | 'indeterminate') => {
                        if (metadata) metadata.is_tree = val === true;
                      }
                    "
                  />
                  <span class="text-sm">Tree View</span>
                </div>
                <div class="flex items-center gap-2">
                  <UCheckbox
                    :model-value="!!metadata.is_diagram"
                    @update:model-value="
                      (val: boolean | 'indeterminate') => {
                        if (metadata) metadata.is_diagram = val === true;
                      }
                    "
                  />
                  <span class="text-sm">Diagram View</span>
                </div>
              </div>
              <UFormField
                v-if="metadata.is_tree"
                label="Tree Parent Field"
                hint="The self-referencing FK field used for nesting"
              >
                <USelect
                  :model-value="metadata.tree_parent_field || ''"
                  @update:model-value="
                    (val: string) => {
                      if (metadata) metadata.tree_parent_field = val || null;
                    }
                  "
                  :items="
                    metadata.fields
                      .filter(
                        (f) =>
                          f.field_type === 'link' &&
                          f.link_entity === metadata?.name,
                      )
                      .map((f) => ({ label: f.label || f.name, value: f.name }))
                  "
                  value-attribute="value"
                  option-attribute="label"
                  placeholder="Select parent field..."
                  class="w-full"
                />
              </UFormField>
              <p class="text-xs text-muted-foreground">
                Tree view requires a self-referencing link field. Diagram view
                uses Cytoscape.js to render entity relationships.
              </p>
            </div>

            <!-- Form State -->
            <div class="border border-muted rounded-lg p-4 space-y-4">
              <h3 class="text-sm font-semibold flex items-center gap-2">
                <UIcon name="i-lucide-workflow" class="w-4 h-4" />
                Form State
              </h3>
              <div class="grid grid-cols-2 gap-4">
                <UFormField
                  label="Editable When"
                  hint="Comma-separated workflow states"
                >
                  <UInput
                    v-model="editableWhenText"
                    placeholder="draft, pending_review"
                    class="w-full font-mono text-sm"
                    @update:model-value="updateEditableWhen"
                  />
                </UFormField>
                <UFormField
                  label="Can Add Children When"
                  hint="Comma-separated workflow states"
                >
                  <UInput
                    v-model="canAddChildrenWhenText"
                    placeholder="draft, pending_review"
                    class="w-full font-mono text-sm"
                    @update:model-value="updateCanAddChildrenWhen"
                  />
                </UFormField>
              </div>
            </div>

            <!-- Attachments -->
            <div class="border border-muted rounded-lg p-4 space-y-4">
              <h3 class="text-sm font-semibold flex items-center gap-2">
                <UIcon name="i-lucide-paperclip" class="w-4 h-4" />
                Attachments
              </h3>
              <div class="flex items-center gap-2">
                <UCheckbox
                  :model-value="
                    !!metadata?.attachment_config?.allow_attachments
                  "
                  @update:model-value="
                    (val: boolean | 'indeterminate') => {
                      if (!metadata) return;
                      if (!metadata.attachment_config) {
                        metadata.attachment_config = {
                          allow_attachments: false,
                          max_attachments: 10,
                          max_file_size_mb: 10,
                        };
                      }
                      metadata.attachment_config.allow_attachments =
                        val === true;
                    }
                  "
                />
                <span class="text-sm">Enable Attachments</span>
              </div>
              <template v-if="metadata?.attachment_config?.allow_attachments">
                <div class="grid grid-cols-3 gap-4">
                  <UFormField label="Max Files">
                    <UInput
                      type="number"
                      :model-value="
                        metadata.attachment_config?.max_attachments ?? 10
                      "
                      @update:model-value="
                        (val: any) => {
                          if (metadata?.attachment_config)
                            metadata.attachment_config.max_attachments =
                              Number(val) || 10;
                        }
                      "
                      :min="1"
                      :max="100"
                      class="w-full"
                    />
                  </UFormField>
                  <UFormField label="Max Size (MB)">
                    <UInput
                      type="number"
                      :model-value="
                        metadata.attachment_config?.max_file_size_mb ?? 10
                      "
                      @update:model-value="
                        (val: any) => {
                          if (metadata?.attachment_config)
                            metadata.attachment_config.max_file_size_mb =
                              Number(val) || 10;
                        }
                      "
                      :min="1"
                      :max="100"
                      class="w-full"
                    />
                  </UFormField>
                  <UFormField label="Extensions" hint="e.g. pdf, jpg">
                    <UInput
                      :model-value="
                        metadata.attachment_config?.allowed_extensions?.join(
                          ', ',
                        ) || ''
                      "
                      @update:model-value="
                        (val: string) => {
                          if (metadata?.attachment_config) {
                            const exts = val
                              .split(',')
                              .map((e: string) => e.trim().toLowerCase())
                              .filter((e: string) => e);
                            metadata.attachment_config.allowed_extensions =
                              exts.length ? exts : null;
                          }
                        }
                      "
                      placeholder="pdf, jpg, png"
                      class="w-full font-mono text-sm"
                    />
                  </UFormField>
                </div>
              </template>
            </div>

            <!-- Sync Status -->
            <div class="border border-muted rounded-lg p-4 space-y-4">
              <h3 class="text-sm font-semibold flex items-center gap-2">
                <UIcon name="i-lucide-database" class="w-4 h-4" />
                Sync Status
              </h3>
              <p class="text-xs text-muted-foreground">
                Save &amp; Sync automatically: validates → backs up → saves JSON
                → reloads registry → updates model → generates &amp; applies
                migration. No manual steps needed.
              </p>
              <div
                v-if="lastSyncResult"
                class="flex items-center gap-2 flex-wrap text-sm"
              >
                <UBadge
                  :color="lastSyncResult.json_saved ? 'success' : 'neutral'"
                  size="sm"
                  variant="subtle"
                >
                  JSON
                </UBadge>
                <UIcon
                  name="i-lucide-chevron-right"
                  class="w-3 h-3 text-muted-foreground"
                />
                <UBadge
                  :color="
                    lastSyncResult.registry_reloaded ? 'success' : 'neutral'
                  "
                  size="sm"
                  variant="subtle"
                >
                  Registry
                </UBadge>
                <UIcon
                  name="i-lucide-chevron-right"
                  class="w-3 h-3 text-muted-foreground"
                />
                <UBadge
                  :color="lastSyncResult.model_updated ? 'success' : 'neutral'"
                  size="sm"
                  variant="subtle"
                >
                  Model
                </UBadge>
                <UIcon
                  name="i-lucide-chevron-right"
                  class="w-3 h-3 text-muted-foreground"
                />
                <UBadge
                  :color="
                    lastSyncResult.migration_applied
                      ? 'success'
                      : lastSyncResult.migration_generated
                        ? 'warning'
                        : 'neutral'
                  "
                  size="sm"
                  variant="subtle"
                >
                  DB
                </UBadge>
              </div>
              <div
                v-if="lastSyncResult?.warnings?.length"
                class="text-xs text-yellow-600 dark:text-yellow-400"
              >
                <span
                  v-for="(w, i) in lastSyncResult.warnings"
                  :key="i"
                  class="block"
                >
                  ⚠ {{ w }}
                </span>
              </div>
              <div class="flex gap-2">
                <UButton
                  variant="ghost"
                  icon="i-lucide-git-branch"
                  size="sm"
                  to="/model-editor/migrations"
                >
                  Migration History
                </UButton>
              </div>
            </div>
          </div>
        </template>
      </UTabs>
    </div>

    <!-- Preview Modal -->
    <UModal v-model:open="showPreview" title="Preview Changes">
      <template #body>
        <div class="space-y-4">
          <div v-if="previewChanges.length === 0" class="text-muted-foreground">
            No changes detected.
          </div>

          <div v-else class="space-y-2">
            <div
              v-for="(change, index) in previewChanges"
              :key="index"
              class="flex items-start gap-2 p-2 rounded"
              :class="{
                'bg-green-50 dark:bg-green-950': change.type === 'safe',
                'bg-red-50 dark:bg-red-950': change.type === 'dangerous',
              }"
            >
              <UIcon
                :name="
                  change.type === 'safe'
                    ? 'i-lucide-check-circle'
                    : 'i-lucide-alert-triangle'
                "
                :class="{
                  'text-green-600': change.type === 'safe',
                  'text-red-600': change.type === 'dangerous',
                }"
              />
              <div>
                <div class="font-medium">{{ change.field }}</div>
                <div class="text-sm text-muted-foreground">
                  {{ change.description }}
                </div>
              </div>
            </div>
          </div>

          <div
            v-if="previewChanges.some((c) => c.type === 'dangerous')"
            class="p-3 bg-yellow-50 dark:bg-yellow-950 rounded border border-yellow-200 dark:border-yellow-800"
          >
            <div
              class="flex items-center gap-2 text-yellow-700 dark:text-yellow-300"
            >
              <UIcon name="i-lucide-alert-triangle" />
              <span class="font-medium">Warning</span>
            </div>
            <p class="text-sm mt-1 text-yellow-600 dark:text-yellow-400">
              This change includes dangerous modifications that may affect
              existing data.
            </p>
          </div>
        </div>
      </template>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="outline" @click="showPreview = false"
            >Cancel</UButton
          >
          <UButton :loading="saving" @click="save">Save Changes</UButton>
        </div>
      </template>
    </UModal>
  </div>
</template>
