<template>
  <div class="relative w-full">
    <UInput
      v-if="field.field_type === 'string' || field.field_type === 'String'"
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      :placeholder="field.placeholder ?? `Enter ${field.label.toLowerCase()}`"
      :required="!!field.required"
      :disabled="disabled"
      :loading="props.loading"
      class="w-full"
      size="lg"
    />

    <UInputNumber
      v-else-if="
        field.field_type === 'integer' ||
        field.field_type === 'int' ||
        field.field_type === 'float'
      "
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      :step="field.field_type === 'float' ? 0.01 : 1"
      :placeholder="field.placeholder ?? `Enter ${field.label.toLowerCase()}`"
      :required="!!field.required"
      :disabled="disabled"
      :loading="props.loading"
      class="w-full"
      size="lg"
    />

    <UInputDate
      v-else-if="field.field_type === 'date'"
      :ref="setDateInputRef"
      :model-value="dateModel as any"
      @update:model-value="updateDateValue"
      :required="!!field.required"
      :disabled="disabled"
      class="w-full"
      size="lg"
    >
      <template #trailing>
        <UPopover :reference="dateInputRef?.inputsRef?.[3]?.$el">
          <UButton
            color="neutral"
            variant="link"
            size="sm"
            icon="i-lucide-calendar"
            aria-label="Select a date"
            class="px-0"
            :disabled="disabled"
          />

          <template #content>
            <UCalendar
              :model-value="dateModel as any"
              @update:model-value="updateDateValue"
              class="p-2"
            />
          </template>
        </UPopover>
      </template>
    </UInputDate>

    <UInputDate
      v-else-if="field.field_type === 'datetime'"
      :model-value="datetimeModel as any"
      @update:model-value="updateDatetimeValue"
      :required="!!field.required"
      :disabled="disabled"
      class="w-full"
      size="lg"
    >
      <template #trailing>
        <UPopover>
          <UButton
            color="neutral"
            variant="link"
            size="sm"
            icon="i-lucide-calendar"
            aria-label="Select a date and time"
            class="px-0"
            :disabled="disabled"
          />

          <template #content>
            <UCalendar
              :model-value="datetimeModel as any"
              @update:model-value="updateDatetimeValue"
              class="p-2"
            />
          </template>
        </UPopover>
      </template>
    </UInputDate>

    <UCheckbox
      v-else-if="field.field_type === 'boolean'"
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      :disabled="disabled"
      size="lg"
    />

    <div
      v-else-if="field.field_type === 'attach_image'"
      class="space-y-3 w-full"
    >
      <div class="flex items-center gap-2 w-full">
        <UFileUpload
          :key="imageUploadKey"
          v-model="imageUploadModel"
          accept="image/*"
          icon="i-lucide-image"
          color="neutral"
          variant="button"
          :multiple="false"
          :disabled="disabled || !recordId"
          :loading="imageUploading"
          @update:model-value="handleAttachImageSelection"
        />

        <UInput
          :model-value="imageFileName"
          readonly
          :disabled="disabled"
          class="flex-1"
          size="md"
          placeholder="No file selected"
        />

        <UButton
          icon="i-lucide-x"
          color="neutral"
          variant="outline"
          size="md"
          class="shrink-0"
          :loading="imageDeleting"
          :disabled="disabled || !modelValue"
          @click="clearAttachImage"
        />
      </div>

      <UAlert
        v-if="!recordId"
        color="neutral"
        variant="subtle"
        icon="i-lucide-info"
        title="Save required before upload"
        description="Create the record first, then upload the image."
      />
    </div>

    <div
      v-else-if="field.field_type === 'link' && field.link_entity"
      class="flex items-center gap-1 w-full"
    >
      <USelectMenu
        :model-value="normalizedModelValue"
        @update:model-value="$emit('update:modelValue', $event)"
        v-model:search-term="linkSearchTerm"
        :placeholder="
          field.placeholder ?? `Select ${field.label.toLowerCase()}`
        "
        :required="!!field.required"
        :items="linkItems"
        :clear="canSelectLink"
        :disabled="!canSelectLink"
        :loading="isLoadingLinkOptions || props.loading"
        ignore-filter
        value-key="value"
        class="flex-1"
        size="lg"
        color="primary"
        variant="outline"
        :create-item="canCreateLinkRecord ? true : undefined"
        @update:open="handleLinkMenuOpen"
        @create="handleCreateLinkRecord"
      >
        <template #default="{ modelValue: value }">
          <span v-if="value" class="truncate">
            {{ getLinkDisplayLabel(value) }}
          </span>
          <span v-else class="text-muted truncate">
            Select {{ field.label.toLowerCase() }}
          </span>
        </template>

        <template #item="{ item }">
          <div class="flex flex-col gap-0.5">
            <span class="font-semibold">{{ item.label }}</span>
            <span v-if="item.description" class="text-sm text-muted">
              {{ item.description }}
            </span>
          </div>
        </template>
      </USelectMenu>
      <UButton
        icon="i-lucide-chevron-right"
        variant="outline"
        size="lg"
        color="neutral"
        class="shrink-0"
        :disabled="!canNavigateToLink"
        @click="navigateToLinkedRecord"
      />
    </div>

    <div
      v-else-if="field.field_type === 'parent_child_link' && field.child_entity"
      class="flex items-center gap-1 w-full"
    >
      <USelectMenu
        :model-value="normalizedModelValue"
        @update:model-value="$emit('update:modelValue', $event)"
        v-model:search-term="parentChildSearchTerm"
        :placeholder="`Select ${field.label.toLowerCase()}`"
        :required="!!field.required"
        :items="parentChildItems"
        :disabled="disabled"
        :loading="isLoadingParentChildOptions || props.loading"
        ignore-filter
        value-key="value"
        class="flex-1"
        size="lg"
        color="primary"
        variant="outline"
        :clear="!disabled"
        @update:open="handleParentChildMenuOpen"
      >
        <template #default="{ modelValue: value }">
          <span v-if="value">
            {{ getParentChildDisplayLabel(value) }}
          </span>
          <span v-else class="text-muted">
            Select {{ field.label.toLowerCase() }}
          </span>
        </template>

        <template #item="{ item }">
          <div
            v-if="item.type === 'label'"
            class="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase"
          >
            {{ item.label }}
          </div>
          <div
            v-else-if="item.type === 'separator'"
            class="h-px bg-border my-1"
          />
          <div v-else class="flex flex-col gap-0.5">
            <span class="font-semibold">{{ item.label }}</span>
          </div>
        </template>
      </USelectMenu>
    </div>

    <div
      v-else-if="field.field_type === 'query_link' && field.query?.key"
      class="flex flex-col gap-1 w-full"
    >
      <div class="flex items-center gap-1 w-full">
        <USelectMenu
          :model-value="normalizedModelValue"
          @update:model-value="$emit('update:modelValue', $event)"
          v-model:search-term="queryLinkSearchTerm"
          :placeholder="`Select ${field.label.toLowerCase()}`"
          :required="!!field.required"
          :items="queryLinkItems"
          :disabled="disabled"
          :loading="isLoadingQueryOptions || props.loading"
          ignore-filter
          value-key="value"
          class="flex-1"
          size="lg"
          color="primary"
          variant="outline"
          :clear="!disabled"
          @update:open="handleQueryLinkMenuOpen"
        >
          <template #default="{ modelValue: value }">
            <span v-if="value">
              {{ getQueryLinkDisplayLabel(value) }}
            </span>
            <span v-else class="text-muted">
              Select {{ field.label.toLowerCase() }}
            </span>
          </template>

          <template #item="{ item }">
            <div class="flex flex-col gap-0.5">
              <span class="font-semibold">{{ item.label }}</span>
              <span v-if="item.description" class="text-sm text-muted">
                {{ item.description }}
              </span>
            </div>
          </template>
        </USelectMenu>
        <UButton
          icon="i-lucide-chevron-right"
          variant="outline"
          size="lg"
          color="neutral"
          class="shrink-0"
          :disabled="!modelValue || disabled"
          @click="navigateToQueryLinkedRecord"
        />
      </div>
    </div>

    <USelectMenu
      v-else-if="field.field_type === 'select'"
      :model-value="selectValueForUi"
      @update:model-value="handleSelectUpdate"
      :placeholder="`Select ${field.label.toLowerCase()}`"
      :required="!!field.required"
      :items="selectItems"
      :disabled="disabled"
      :loading="props.loading"
      value-key="value"
      class="w-full"
      size="lg"
      color="primary"
      variant="outline"
      :clear="!disabled"
    >
      <template #default="{ modelValue: value }">
        <span v-if="value">
          {{ getSelectDisplayLabel(value) }}
        </span>
        <span v-else class="text-muted">
          Select {{ field.label.toLowerCase() }}
        </span>
      </template>
    </USelectMenu>

    <UTextarea
      v-else-if="field.field_type === 'text'"
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      :placeholder="`Enter ${field.label.toLowerCase()}`"
      :required="!!field.required"
      :rows="4"
      :disabled="disabled"
      :loading="props.loading"
      class="w-full"
      size="lg"
    />

    <UInput
      v-else
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      :placeholder="`Enter ${field.label.toLowerCase()}`"
      :required="!!field.required"
      :disabled="disabled"
      :loading="props.loading"
      class="w-full"
      size="lg"
    />
  </div>
</template>

<script setup lang="ts">
import { refDebounced } from "@vueuse/core";
import {
  parseDate,
  parseDateTime,
  type CalendarDate,
} from "@internationalized/date";
import type {
  FieldMeta,
  LinkFieldPermissions,
} from "~/composables/useApiTypes";
import { useApi } from "~/composables/useApi";
import { useAttachmentApi } from "~/composables/useAttachmentApi";
import { useEntityModalStore } from "~/stores/entityModal";

interface Props {
  field: FieldMeta;
  modelValue: any;
  recordId?: string;
  disabled?: boolean;
  loading?: boolean;
  linkOptions?: Record<string, any[]>;
  linkTitles?: Record<string, string>;
  onLoadLinkOptions?: (fieldName: string, linkEntity: string) => void;
  entityName?: string;
  formState?: Record<string, any>;
  linkFieldPermissions?: Record<string, LinkFieldPermissions>;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  loading: false,
  linkOptions: () => ({}),
  linkTitles: () => ({}),
  linkFieldPermissions: () => ({}),
});

const entityModalStore = useEntityModalStore();
const router = useRouter();
const toast = useToast();
const { uploadAttachment, deleteAttachment, getAttachmentDownloadUrl } =
  useAttachmentApi();

// Link field permission helpers
const linkPerms = computed(() => {
  const entity = props.field.link_entity || props.field.child_entity;
  if (!entity) return { can_read: true, can_select: true, can_create: true };
  return (
    props.linkFieldPermissions[entity] || {
      can_read: true,
      can_select: true,
      can_create: true,
    }
  );
});

const canNavigateToLink = computed(
  () => linkPerms.value.can_read && !!props.modelValue,
);
const canSelectLink = computed(
  () => linkPerms.value.can_select !== false && !props.disabled,
);
const canCreateLinkRecord = computed(
  () => linkPerms.value.can_create && canSelectLink.value,
);

const navigateToLinkedRecord = () => {
  const entity = props.field.link_entity;
  if (entity && props.modelValue) {
    router.push(`/${entity}/${props.modelValue}`);
  }
};

const navigateToQueryLinkedRecord = () => {
  if (!props.modelValue || !props.field.query?.key) return;

  // For query links, we need to determine the target entity from the selected option
  const selectedOption = queryLinkOptions.value.find(
    (opt) => opt.value === props.modelValue,
  );
  if (selectedOption?.entity) {
    // If the option includes the entity name, use it
    router.push(`/${selectedOption.entity}/${props.modelValue}`);
  } else {
    // Default fallback - try to determine from query configuration or use a default
    // This might need to be enhanced based on your query_link configuration
    console.warn("Cannot determine target entity for query link navigation", {
      queryKey: props.field.query?.key,
      value: props.modelValue,
      option: selectedOption,
    });
  }
};

const handleCreateLinkRecord = async (searchTerm: string) => {
  const entity = props.field.link_entity;
  if (!entity) return;

  // Get entity metadata to find the title field
  let titleField = "name"; // Default fallback

  try {
    const metaResponse = await getEntityMeta(entity);
    if (metaResponse?.data?.title_field) {
      titleField = metaResponse.data.title_field;
    }
  } catch (error) {
    console.warn("Failed to fetch entity metadata for title field:", error);
  }

  const prefillData: Record<string, any> = {
    [titleField]: searchTerm,
  };

  entityModalStore.open(entity, prefillData, (response: any) => {
    if (response?.status === "success" && response?.data?.id) {
      const newId = response.data.id;
      const displayValue =
        response.data[titleField] ||
        response.data.name ||
        response.data.title ||
        response.data.label ||
        newId;
      // Add to search results so it appears immediately
      linkSearchResults.value.unshift({
        value: String(newId),
        label: String(displayValue),
      });
      emit("update:modelValue", String(newId));
    }
  });
};

const emit = defineEmits<{
  "update:modelValue": [value: any];
}>();

const imageUploadModel = ref<File | null>(null);
const imageUploading = ref(false);
const imageDeleting = ref(false);
const imageUploadKey = ref(0);

const imageFileName = computed(() => {
  if (imageUploadModel.value?.name) return imageUploadModel.value.name;
  if (props.modelValue) return String(props.modelValue);
  return "";
});

const currentImageUrl = computed(() => {
  if (!props.entityName || !props.recordId || !props.modelValue) return "";
  const url = getAttachmentDownloadUrl(
    props.entityName,
    props.recordId,
    String(props.modelValue),
  );
  if (typeof localStorage === "undefined") return url;
  const token = localStorage.getItem("auth_token");
  return token ? `${url}?token=${encodeURIComponent(token)}` : url;
});

const downloadCurrentImage = () => {
  if (!currentImageUrl.value) return;
  window.open(currentImageUrl.value, "_blank");
};

const clearAttachImage = async () => {
  if (!props.entityName || !props.recordId || !props.modelValue) return;
  imageDeleting.value = true;
  try {
    await deleteAttachment(
      props.entityName,
      props.recordId,
      String(props.modelValue),
    );
    emit("update:modelValue", null);
    toast.add({ title: `${props.field.label} removed`, color: "success" });
  } catch (err: any) {
    toast.add({
      title:
        err?.message || `Failed to remove ${props.field.label.toLowerCase()}`,
      color: "error",
    });
  } finally {
    imageDeleting.value = false;
  }
};

const handleAttachImageSelection = async (
  value: File | File[] | null | undefined,
) => {
  const file = Array.isArray(value) ? value[0] : value;
  if (!file) return;
  if (!props.entityName || !props.recordId) {
    imageUploadModel.value = null;
    return;
  }

  imageUploading.value = true;
  const oldAttachmentId = props.modelValue ? String(props.modelValue) : null;
  try {
    const res = await uploadAttachment(props.entityName, props.recordId, file);
    if (res.status !== "success" || !res.data?.id) {
      throw new Error(
        res.message || `Failed to upload ${props.field.label.toLowerCase()}`,
      );
    }

    emit("update:modelValue", res.data.id);

    if (oldAttachmentId && oldAttachmentId !== res.data.id) {
      try {
        await deleteAttachment(
          props.entityName,
          props.recordId,
          oldAttachmentId,
        );
      } catch {
        // best effort cleanup
      }
    }

    toast.add({ title: `${props.field.label} uploaded`, color: "success" });
  } catch (err: any) {
    toast.add({
      title:
        err?.message || `Failed to upload ${props.field.label.toLowerCase()}`,
      color: "error",
    });
  } finally {
    imageUploading.value = false;
    imageUploadModel.value = null;
    imageUploadKey.value += 1;
  }
};

const { getGroupedOptions, postQueryOptions, getEntityOptions, getEntityMeta } =
  useApi();

const selectItems = computed(() => {
  const raw: any = (props.field as any).options;
  if (!raw) return [];

  // Backward compatible:
  // - array of strings: ["A", "B"]
  // - array of items: [{ value, label }]
  // - string with newline delimiters: "A\nB\nC" (Frappe-style)
  if (Array.isArray(raw)) {
    if (raw.length === 0) return [];
    if (typeof raw[0] === "string") {
      return raw.map((v: string) => ({ value: v, label: v }));
    }
    return raw;
  }

  if (typeof raw === "string") {
    return raw
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((v) => ({ value: v, label: v }));
  }

  return [];
});

const selectValueForUi = computed(() => {
  if (props.modelValue === null || props.modelValue === undefined) return null;
  const option = selectItems.value.find((item: any) => {
    return (
      item.label === props.modelValue ||
      String(item.value) === String(props.modelValue)
    );
  });
  if (option) return option.value;
  return props.modelValue;
});

const handleSelectUpdate = (value: any) => {
  const option = selectItems.value.find(
    (item: any) => String(item.value) === String(value),
  );
  if (option) {
    emit("update:modelValue", option.label ?? option.value);
  } else {
    emit("update:modelValue", value);
  }
};

const getSelectDisplayLabel = (value: any): string => {
  if (!value) return "";
  const option = selectItems.value.find((item: any) => {
    return item.label === value || String(item.value) === String(value);
  });
  return option?.label || String(value);
};

const dateInputRef = ref<any>(null);
const setDateInputRef = (el: any) => {
  dateInputRef.value = el;
};

const dateModel = computed<any>(() => {
  if (!props.modelValue) return undefined;
  try {
    return parseDate(String(props.modelValue));
  } catch {
    return undefined;
  }
});

const updateDateValue = (val: any) => {
  emit("update:modelValue", val ? val.toString() : null);
};

const datetimeModel = computed<any>(() => {
  if (!props.modelValue) return undefined;
  try {
    return parseDateTime(String(props.modelValue));
  } catch {
    return undefined;
  }
});

const normalizedModelValue = computed(() => {
  if (props.modelValue === null || props.modelValue === undefined) return null;
  return String(props.modelValue);
});

const updateDatetimeValue = (val: any) => {
  emit("update:modelValue", val ? val.toString() : null);
};

// ── Link field: async search with debounce ──
const linkSearchTerm = ref("");
const linkSearchTermDebounced = refDebounced(linkSearchTerm, 300);
const linkSearchResults = ref<any[]>([]);
const isLoadingLinkOptions = ref(false);

const handleLinkMenuOpen = (isOpen: boolean) => {
  if (isOpen && props.field.link_entity) {
    // Load initial options (empty search = top 10)
    fetchLinkOptions("");
  }
};

const resolveLinkFilters = (): Record<string, any> | undefined => {
  const filterBy = props.field.filter_by;
  if (!filterBy) return undefined;
  const filterValue = (props.formState || {})[filterBy];
  if (filterValue == null || filterValue === "") return undefined;
  return { [filterBy]: filterValue };
};

const fetchLinkOptions = async (search: string) => {
  if (!props.field.link_entity) return;
  isLoadingLinkOptions.value = true;
  try {
    const filters = resolveLinkFilters();
    const response = await getEntityOptions(
      props.field.link_entity,
      search || undefined,
      10,
      filters,
    );
    if (response.status === "success") {
      linkSearchResults.value = (response.options || []).map((o: any) => ({
        ...o,
        value:
          o?.value === null || o?.value === undefined
            ? o?.value
            : String(o.value),
      }));
    }
  } catch (error) {
    console.error("Failed to search link options:", error);
    linkSearchResults.value = [];
  } finally {
    isLoadingLinkOptions.value = false;
  }
};

watch(linkSearchTermDebounced, (term) => {
  fetchLinkOptions(term);
});

// Re-fetch when filter_by source field changes (clear current selection implicitly)
watch(
  () =>
    props.field.filter_by
      ? (props.formState || {})[props.field.filter_by]
      : undefined,
  (newVal, oldVal) => {
    if (newVal !== oldVal && props.field.link_entity) {
      linkSearchResults.value = [];
      fetchLinkOptions("");
    }
  },
);

const linkItems = computed(() => {
  return linkSearchResults.value;
});

const getLinkDisplayLabel = (value: any): string => {
  if (!value || !props.field.link_entity) return "";
  const key = `${props.field.link_entity}::${value}`;
  if (props.linkTitles[key]) return props.linkTitles[key];
  // Also check search results for label
  const opt = linkSearchResults.value.find((o) => o.value === String(value));
  if (opt?.label) return opt.label;
  // If we have the value but no label, return the value as last resort
  return String(value);
};

// ── Parent-Child Link: async search with debounce ──
const parentChildGroups = ref<any[]>([]);
const isLoadingParentChildOptions = ref(false);
const parentChildSearchTerm = ref("");
const parentChildSearchTermDebounced = refDebounced(parentChildSearchTerm, 300);
const parentChildSearchResults = ref<any[]>([]);

const parentChildItems = computed(() => {
  const items: any[] = [];
  const groups = parentChildSearchTerm.value
    ? parentChildSearchResults.value
    : parentChildGroups.value;

  groups.forEach((group, index) => {
    items.push({ type: "label", label: group.label });
    group.options.forEach((option: any) => {
      items.push(option);
    });
    if (index < groups.length - 1) {
      items.push({ type: "separator" });
    }
  });
  return items;
});

const handleParentChildMenuOpen = async (isOpen: boolean) => {
  if (!isOpen || !props.field.child_entity) return;
  if (!props.field.parent_entity || !props.field.child_parent_fk_field) return;
  if (parentChildGroups.value.length > 0) return;

  isLoadingParentChildOptions.value = true;
  try {
    const response = await getGroupedOptions(props.field.child_entity, {
      parent_entity: props.field.parent_entity,
      child_parent_fk_field: props.field.child_parent_fk_field,
    });
    if (response.status === "success") {
      parentChildGroups.value = (response.groups || []).map((g: any) => ({
        ...g,
        options: (g?.options || []).map((o: any) => ({
          ...o,
          value:
            o?.value === null || o?.value === undefined
              ? o?.value
              : String(o.value),
        })),
      }));
    }
  } catch (error) {
    console.error("Failed to load parent-child options:", error);
  } finally {
    isLoadingParentChildOptions.value = false;
  }
};

watch(parentChildSearchTermDebounced, async (term) => {
  if (
    !props.field.child_entity ||
    !props.field.parent_entity ||
    !props.field.child_parent_fk_field
  )
    return;

  if (!term) {
    parentChildSearchResults.value = [];
    return;
  }

  isLoadingParentChildOptions.value = true;
  try {
    const response = await getGroupedOptions(props.field.child_entity, {
      parent_entity: props.field.parent_entity,
      child_parent_fk_field: props.field.child_parent_fk_field,
      search: term,
    });
    if (response.status === "success") {
      parentChildSearchResults.value = (response.groups || []).map(
        (g: any) => ({
          ...g,
          options: (g?.options || []).map((o: any) => ({
            ...o,
            value:
              o?.value === null || o?.value === undefined
                ? o?.value
                : String(o.value),
          })),
        }),
      );
    }
  } catch (error) {
    console.error("Failed to search parent-child options:", error);
    parentChildSearchResults.value = [];
  } finally {
    isLoadingParentChildOptions.value = false;
  }
});

const getParentChildDisplayLabel = (value: any): string => {
  if (!value) return "";
  const key = `${props.field.child_entity}::${value}`;
  return props.linkTitles[key] || String(value);
};

// ── Query Link: async search with debounce ──
const queryLinkOptions = ref<any[]>([]);
const isLoadingQueryOptions = ref(false);
const queryLinkSearchTerm = ref("");
const queryLinkSearchTermDebounced = refDebounced(queryLinkSearchTerm, 300);

const queryLinkItems = computed(() => {
  const selected = normalizedModelValue.value;
  const items = queryLinkOptions.value || [];

  const filterBy = (props.field as any).filter_by as string | undefined;
  const filterValue = filterBy ? (props.formState || {})[filterBy] : undefined;
  const filterLabel = filterBy
    ? `Filtered by ${filterBy.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())} = ${filterValue ?? ""}`
    : null;

  const prefixItems = filterLabel
    ? ([{ type: "label", label: filterLabel }, { type: "separator" }] as any[])
    : ([] as any[]);

  if (!selected) return [...prefixItems, ...items];

  const exists = items.some((o) => String(o?.value) === selected);
  if (exists) return [...prefixItems, ...items];

  return [
    ...prefixItems,
    {
      value: selected,
      label: getQueryLinkDisplayLabel(selected),
    },
    ...items,
  ];
});

const handleQueryLinkMenuOpen = async (isOpen: boolean) => {
  if (!isOpen || !props.field.query?.key) return;
  // Always fetch fresh options for query_fields (no caching)
  await fetchQueryOptions("");
};

const fetchQueryOptions = async (search: string) => {
  if (!props.field.query?.key) return;
  isLoadingQueryOptions.value = true;
  try {
    const sendFormState = props.field.query?.send_form_state !== false;

    const minimalFormState = (() => {
      const filterBy = (props.field as any).filter_by as string | undefined;
      if (!filterBy) return null;
      const v = (props.formState || {})[filterBy];
      return { [filterBy]: v ?? null };
    })();

    const response = await postQueryOptions({
      key: props.field.query.key,
      entity: props.entityName || "",
      field: props.field.name,
      form_state: sendFormState
        ? minimalFormState || props.formState || {}
        : {},
      static_params: {
        ...props.field.query.static_params,
        search: search,
      },
    });
    if (response.status === "success") {
      queryLinkOptions.value = (response.options || []).map((o: any) => ({
        ...o,
        value:
          o?.value === null || o?.value === undefined
            ? o?.value
            : String(o.value),
      }));
    }
  } catch (error) {
    console.error("Failed to search query link options:", error);
    queryLinkOptions.value = [];
  } finally {
    isLoadingQueryOptions.value = false;
  }
};

watch(queryLinkSearchTermDebounced, (term) => {
  fetchQueryOptions(term || "");
});

const getQueryLinkDisplayLabel = (value: any): string => {
  if (!value) return "";

  const stringValue = String(value);
  const option = queryLinkOptions.value.find(
    (opt) => String(opt.value) === stringValue,
  );
  if (option?.label) return option.label;

  const titles = props.linkTitles || {};
  const direct = titles[stringValue];
  if (direct) return direct;

  const suffix = `::${stringValue}`;
  for (const k in titles) {
    if (k.endsWith(suffix)) {
      const v = titles[k];
      if (v) return v;
    }
  }

  return stringValue;
};
</script>
