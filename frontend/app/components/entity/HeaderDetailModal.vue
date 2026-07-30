<script setup lang="ts">
import type {
  EntityMeta,
  FieldMeta,
  ChildTableMeta,
} from "~/composables/useApiTypes";
import { useFetchFrom } from "~/composables/useFetchFrom";

interface Props {
  modelValue: boolean;
  entity: string;
  fkField: string;
  parentId: string;
  parentEntity: string;
  meta?: EntityMeta | null;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:modelValue", val: boolean): void;
  (e: "created", payload: { id: string }): void;
}>();

const open = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit("update:modelValue", val),
});

const { getEntityMeta, getEntityPrefill, postEntityAction, getEntityOptions } =
  useApi();
const toast = useToast();

const loadingMeta = ref(false);
const saving = ref(false);
const meta = ref<EntityMeta | null>(props.meta || null);
const formData = ref<Record<string, any>>({});
const fieldErrors = ref<Record<string, string>>({});
const createdId = ref<string | null>(null);
const childEntityMeta = ref<Record<string, EntityMeta>>({});
const childRefs = ref<Record<string, any>>({});
const fetchFromLoading = ref<Record<string, boolean>>({});
const fetchFromEnabled = ref(false);
const localLinkOptions = ref<
  Record<string, { value: string; label: string }[]>
>({});
const linkTitles = ref<Record<string, string>>({});

const visibleFields = computed<FieldMeta[]>(() => {
  if (!meta.value?.fields) return [];
  return meta.value.fields.filter((f) => !f.hidden && f.name !== "id");
});

const children = computed<ChildTableMeta[]>(() => meta.value?.children || []);

const modalTitle = computed(() => {
  const label = meta.value?.label || props.entity;
  return createdId.value ? `${label} — ${createdId.value}` : `New ${label}`;
});

const getChildSectionLabel = (child: any): string => {
  const childEntity = child?.entity;
  if (!childEntity) return child?.label || "Items";
  return (
    childEntityMeta.value[childEntity]?.label || child?.label || childEntity
  );
};

const mergedLinkOptions = computed(() => localLinkOptions.value);

function clearFieldError(fieldName: string) {
  if (!fieldErrors.value[fieldName]) return;
  const next = { ...fieldErrors.value };
  delete next[fieldName];
  fieldErrors.value = next;
}

function onFieldUpdate(fieldName: string, value: any) {
  formData.value[fieldName] = value;
  formData.value = { ...formData.value };
  clearFieldError(fieldName);
}

function setFetchFromLoading(fieldName: string, isLoading: boolean) {
  fetchFromLoading.value = {
    ...fetchFromLoading.value,
    [fieldName]: isLoading,
  };
}

function setFetchFromLinkTitle(linkEntity: string, id: string, title: string) {
  linkTitles.value[`${linkEntity}::${id}`] = title;
}

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

useFetchFrom(meta, formData, {
  setLoading: setFetchFromLoading,
  setLinkTitle: setFetchFromLinkTitle,
  enabled: fetchFromEnabled,
});

async function loadMeta() {
  if (meta.value || loadingMeta.value) return;
  loadingMeta.value = true;
  try {
    const res = await getEntityMeta(props.entity);
    if (res.status === "success") {
      meta.value = res.data;
    }
  } finally {
    loadingMeta.value = false;
  }
}

async function loadPrefill() {
  formData.value = {};
  formData.value[props.fkField] = props.parentId;
  try {
    const res = await getEntityPrefill(props.entity);
    if (res.status === "success" && res.data) {
      formData.value = { ...res.data, [props.fkField]: props.parentId };
    }
  } catch (err) {
    console.warn("[HeaderDetailModal] prefill failed", err);
  }
}

async function ensureChildMeta(entity: string) {
  if (childEntityMeta.value[entity]) return;
  try {
    const res = await getEntityMeta(entity);
    if (res.status === "success") {
      childEntityMeta.value[entity] = res.data;
    }
  } catch (err) {
    console.error(`Failed to load child meta for ${entity}`, err);
  }
}

async function createRecord() {
  fieldErrors.value = {};
  saving.value = true;
  try {
    // Collect child grid data into the children dict for atomic save
    const childrenPayload: Record<
      string,
      { rows: any[]; deleted_ids: string[] }
    > = {};
    for (const child of children.value) {
      const childRef = childRefs.value[child.entity];
      if (!childRef?.getChildData) continue;
      const rows = childRef.getChildData() || [];
      const deletedIds = childRef?.getDeletedIds
        ? childRef.getDeletedIds()
        : [];
      if (rows.length === 0 && deletedIds.length === 0) continue;
      childrenPayload[child.entity] = { rows, deleted_ids: deletedIds };
    }

    const res = await postEntityAction(props.entity, {
      action: "create",
      data: formData.value,
      children:
        Object.keys(childrenPayload).length > 0 ? childrenPayload : undefined,
    });

    if (res.status === "success") {
      const newId =
        (res.data as any)?.id || (res as any)?.id || (res as any)?.data?.name;
      if (newId) {
        const savedId = String(newId);
        createdId.value = savedId;

        for (const child of children.value) {
          const childRef = childRefs.value[child.entity];
          if (childRef?.markAsSaved) childRef.markAsSaved();
        }

        emit("created", { id: savedId });
        if (res.message) {
          toast.add({
            title: res.message,
            color: "success",
            type: "foreground",
          });
        }

        // Auto-close modal after successful creation
        await nextTick();
        closeModal();
      } else {
        if (res.message) {
          toast.add({
            title: res.message,
            color: "success",
            type: "foreground",
          });
        }
        await nextTick();
        closeModal();
      }
    } else {
      if (res.errors) {
        // Strip field name prefix from error messages (e.g., "Asset Tag: " -> "")
        const cleanedErrors: Record<string, string> = {};
        for (const [field, message] of Object.entries(
          res.errors as Record<string, string>,
        )) {
          cleanedErrors[field] = message.replace(/^[^:]+:\s*/, "");
        }
        fieldErrors.value = cleanedErrors;
      }
      toast.add({
        title: res.message || "Save failed",
        color: "error",
        type: "foreground",
      });
    }
  } catch (err: any) {
    toast.add({
      title: err?.message || "Save failed",
      color: "error",
      type: "foreground",
    });
  } finally {
    saving.value = false;
  }
}

function closeModal() {
  open.value = false;
  createdId.value = null;
  formData.value = {};
  fieldErrors.value = {};
  fetchFromEnabled.value = false;
  fetchFromLoading.value = {};
  localLinkOptions.value = {};
  linkTitles.value = {};
}

watch(
  () => open.value,
  async (isOpen) => {
    if (isOpen) {
      fetchFromEnabled.value = false;
      await loadMeta();
      await loadPrefill();
      await nextTick();
      fetchFromEnabled.value = true;
    }
  },
);

watch(
  () => children.value,
  async (list) => {
    for (const child of list) await ensureChildMeta(child.entity);
  },
  { immediate: true },
);
</script>

<template>
  <UModal
    v-model:open="open"
    :title="modalTitle"
    fullscreen
    scrollable
    :ui="{
      content: 'w-full h-full flex flex-col',
      body: 'flex-1 min-h-0 overflow-hidden',
      footer: 'shrink-0',
    }"
  >
    <template #body>
      <div class="flex-1 min-h-0 overflow-y-auto p-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div
            v-for="field in visibleFields"
            :key="field.name"
            class="space-y-2"
          >
            <UFormField
              :label="field.label"
              :required="!!field.required"
              :name="field.name"
              :error="fieldErrors[field.name]"
            >
              <EntityFieldRenderer
                :field="field"
                v-model="formData[field.name]"
                :loading="fetchFromLoading[field.name] === true"
                :record-id="createdId || undefined"
                :disabled="saving || !!createdId"
                :link-options="mergedLinkOptions"
                :link-titles="linkTitles"
                :on-load-link-options="loadLinkOptions"
                :entity-name="entity"
                :form-state="formData"
                :link-field-permissions="meta?.link_field_permissions || {}"
                @update:model-value="
                  (val: any) => onFieldUpdate(field.name, val)
                "
              />
            </UFormField>
          </div>
        </div>
        <div v-if="children.length" class="space-y-4 mt-4">
          <div v-for="child in children" :key="child.entity">
            <USeparator
              :label="getChildSectionLabel(child)"
              size="lg"
              class="mb-4"
            />
            <div class="min-h-0">
              <EntityChildDataGrid
                :ref="
                  (el: any) => {
                    if (el) childRefs[child.entity] = el;
                  }
                "
                :parent-entity="entity"
                :parent-id="createdId || 'new'"
                :child-entity="child.entity"
                :fk-field="child.fk_field"
                :child-meta="childEntityMeta[child.entity] || null"
                :editable="true"
                :can-add="true"
                :can-delete="true"
                :parent-form-data="formData"
              />
            </div>
          </div>
        </div>
      </div>
    </template>

    <template #footer>
      <div class="flex justify-end gap-2">
        <UButton variant="outline" @click="closeModal" size="md"
          >Cancel</UButton
        >
        <UButton
          color="primary"
          :loading="saving"
          :disabled="!!createdId"
          @click="createRecord"
          size="md"
        >
          Save & Continue
        </UButton>
      </div>
    </template>
  </UModal>
</template>
