<script setup lang="ts">
import type { EntityMeta, AttachmentItem } from "~/composables/useApiTypes";
import { useFormState } from "~/composables/useFormState";
import { useAttachmentApi } from "~/composables/useAttachmentApi";
import { useAuthStore } from "~/stores/auth";

// ---------------------------------------------------------------------------
// Services / composables
// ---------------------------------------------------------------------------
const { apiFetch, baseURL } = useApiFetch();
const { getEntityMeta } = useEntityApi();
const {
  getAttachments,
  uploadAttachment,
  deleteAttachment,
  getAttachmentViewUrl,
} = useAttachmentApi();
const authStore = useAuthStore();
const toast = useToast();

// ---------------------------------------------------------------------------
// Page state
// ---------------------------------------------------------------------------
const entityMeta = ref<EntityMeta | null>(null);
const formData = ref<Record<string, any>>({});
const originalData = ref<Record<string, any>>({});
const roles = ref<string[]>([]);

const loading = ref(true);
const saving = ref(false);
const isEditMode = ref(false);

const avatarAttachment = ref<AttachmentItem | null>(null);
const avatarUploading = ref(false);
const avatarDeleting = ref(false);
const avatarUploadModel = ref<File | null>(null);

// ---------------------------------------------------------------------------
// Form state — same pattern as [id].vue.
// useFormState handles show_when / depends_on / readonly_depends_on from meta.
// isNew is always false for a profile (current user always exists).
// ---------------------------------------------------------------------------
const linkedCounts = ref<Record<string, number>>({});
const isNew = ref(false);

const { visibleFields: formStateVisibleFields, fieldStates } = useFormState(
  entityMeta,
  formData,
  linkedCounts,
  isNew,
);

// When in view mode: show all visible fields.
// When in edit mode: hide readonly fields (they are rendered disabled via isFieldDisabled).
const visibleFields = computed(() => {
  return formStateVisibleFields.value.filter((field) => {
    // Hide is_active field from non-superusers
    if (field.name === "is_active" && !authStore.isSuperuser) {
      return false;
    }
    return true;
  });
});

// is_active may only be toggled by superusers.
const isFieldDisabled = (fieldName: string): boolean => {
  if (!isEditMode.value) return true;
  if (fieldName === "is_active" && !authStore.isSuperuser) return true;
  const state = fieldStates.value[fieldName];
  return state?.editable === false;
};

// ---------------------------------------------------------------------------
// Avatar
// ---------------------------------------------------------------------------
const attachmentConfig = computed(
  () => entityMeta.value?.attachment_config ?? null,
);

const avatarUrl = computed(() => {
  if (!formData.value.id || !avatarAttachment.value) return undefined;
  return getAttachmentViewUrl(
    "user",
    String(formData.value.id),
    avatarAttachment.value.id,
    authStore.token || undefined,
  );
});

const loadAvatar = async () => {
  if (!formData.value.id || !attachmentConfig.value?.allow_attachments) {
    avatarAttachment.value = null;
    return;
  }
  try {
    const res = await getAttachments("user", String(formData.value.id));
    if (res.status !== "success") return;
    avatarAttachment.value =
      res.data.find((a) => a.mime_type?.startsWith("image/")) ?? null;
  } catch {
    avatarAttachment.value = null;
  }
};

const onAvatarSelected = async (value: File | File[] | null | undefined) => {
  const file = Array.isArray(value) ? value[0] : value;
  if (!file || !formData.value.id) return;
  avatarUploading.value = true;
  try {
    if (avatarAttachment.value) {
      await deleteAttachment(
        "user",
        String(formData.value.id),
        avatarAttachment.value.id,
      );
    }
    const res = await uploadAttachment(
      "user",
      String(formData.value.id),
      file,
      "Profile avatar",
    );
    if (res.status !== "success")
      throw new Error(res.message || "Upload failed");
    toast.add({
      title: res.message || "Profile photo updated",
      color: "success",
    });
    await loadAvatar();
  } catch (err: any) {
    toast.add({
      title: "Failed to update profile photo",
      description: err?.message,
      color: "error",
    });
  } finally {
    avatarUploadModel.value = null;
    avatarUploading.value = false;
  }
};

const removeAvatar = async () => {
  if (!formData.value.id || !avatarAttachment.value) return;
  avatarDeleting.value = true;
  try {
    const res = await deleteAttachment(
      "user",
      String(formData.value.id),
      avatarAttachment.value.id,
    );
    if (res.status !== "success")
      throw new Error(res.message || "Delete failed");
    avatarAttachment.value = null;
    toast.add({
      title: res.message || "Profile photo removed",
      color: "success",
    });
  } catch (err: any) {
    toast.add({
      title: "Failed to remove profile photo",
      description: err?.message,
      color: "error",
    });
  } finally {
    avatarDeleting.value = false;
  }
};

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------
const loadProfile = async () => {
  loading.value = true;
  try {
    const [profileRes, metaRes] = await Promise.all([
      apiFetch<{ status: string; message?: string; data: Record<string, any> }>(
        `${baseURL}/profile`,
      ),
      getEntityMeta("user"),
    ]);

    if (profileRes.status !== "success")
      throw new Error(profileRes.message || "Failed to load profile");

    entityMeta.value = metaRes.data;
    formData.value = { ...profileRes.data };
    originalData.value = { ...profileRes.data };
    roles.value = profileRes.data.roles ?? [];

    await loadAvatar();
  } catch (err: any) {
    toast.add({
      title: "Failed to load profile",
      description: err?.message,
      color: "error",
    });
  } finally {
    loading.value = false;
  }
};

// ---------------------------------------------------------------------------
// Save / cancel
// ---------------------------------------------------------------------------
const handleSave = async () => {
  saving.value = true;
  try {
    const updatableFields = (entityMeta.value?.fields ?? [])
      .filter((f) => !f.readonly && !f.hidden)
      .map((f) => f.name);

    const payload: Record<string, unknown> = {};
    for (const key of updatableFields) {
      if (key in formData.value) payload[key] = formData.value[key];
    }
    if (!authStore.isSuperuser) delete payload.is_active;

    const res = await apiFetch<{
      status: string;
      message: string;
      data: Record<string, any>;
    }>(`${baseURL}/profile`, { method: "PUT", body: payload });

    if (res.status !== "success") throw new Error(res.message || "Save failed");

    toast.add({ title: res.message || "Profile updated", color: "success" });
    isEditMode.value = false;
    formData.value = { ...res.data, roles: formData.value.roles };
    originalData.value = { ...formData.value };

    if (authStore.user) {
      authStore.setUser({
        ...authStore.user,
        full_name: res.data.full_name,
        email: res.data.email,
      });
    }
  } catch (err: any) {
    toast.add({
      title: "Failed to update profile",
      description: err?.message,
      color: "error",
    });
  } finally {
    saving.value = false;
  }
};

const handleCancel = () => {
  formData.value = { ...originalData.value };
  isEditMode.value = false;
};

onMounted(loadProfile);

definePageMeta({ title: "Profile details" });
</script>

<template>
  <div class="space-y-6">
    <!-- Skeleton -->
    <template v-if="loading">
      <div class="space-y-4">
        <USkeleton class="h-24 rounded-xl" />
        <USkeleton class="h-96 rounded-xl" />
      </div>
    </template>

    <template v-else>
      <div
        class="flex w-full flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"
      >
        <!-- Avatar block -->
        <div class="flex items-center gap-4 w-full">
          <div class="flex justify-between items-center w-full">
            <div class="flex gap-4 items-center">
              <UAvatar
                :src="avatarUrl"
                :alt="formData.full_name || formData.username"
                icon="i-lucide-user"
                size="3xl"
              />
              <div>
                <p class="text-sm text-muted">{{ formData.username }}</p>
                <p class="font-medium text-highlighted">
                  {{ formData.full_name || formData.username }}
                </p>
                <div class="mt-1 flex flex-wrap gap-1">
                  <UBadge
                    v-for="role in roles"
                    :key="role"
                    color="neutral"
                    variant="subtle"
                    size="sm"
                  >
                    {{ role }}
                  </UBadge>
                </div>
              </div>
            </div>

            <div
              v-if="attachmentConfig?.allow_attachments"
              class="flex flex-wrap items-center gap-2"
            >
              <UFileUpload
                :key="avatarAttachment?.id || 'profile-avatar-upload'"
                v-model="avatarUploadModel"
                variant="button"
                accept="image/*"
                icon="i-lucide-image-up"
                label="Upload photo"
                :multiple="false"
                :loading="avatarUploading"
                @update:model-value="onAvatarSelected"
              />
              <UButton
                v-if="avatarAttachment"
                color="error"
                variant="outline"
                size="sm"
                :loading="avatarDeleting"
                @click="removeAvatar"
              >
                Remove
              </UButton>
            </div>
          </div>
        </div>
      </div>
      <!-- Header: avatar + edit controls -->

      <USeparator />

      <UPageCard
        title="Profile"
        description="Manage your personal details and account settings."
        variant="naked"
        orientation="horizontal"
        class="mb-4"
      >
        <!-- Edit / Save / Cancel -->
        <div class="flex flex-wrap justify-end gap-2">
          <template v-if="isEditMode">
            <UButton variant="outline" :disabled="saving" @click="handleCancel"
              >Cancel</UButton
            >
            <UButton :loading="saving" @click="handleSave"
              >Save changes</UButton
            >
          </template>
          <UButton
            v-else
            icon="i-lucide-pencil"
            color="neutral"
            @click="isEditMode = true"
          >
            Edit profile
          </UButton>
        </div>
      </UPageCard>

      <!-- Fields: driven entirely by entity metadata via useFormState -->
      <UPageCard variant="subtle">
        <UForm :state="formData" class="space-y-4">
          <template v-for="(field, index) in visibleFields" :key="field.name">
            <UFormField
              :name="field.name"
              :label="field.label"
              :required="
                !!(fieldStates[field.name]?.required ?? field.required)
              "
              class="flex items-start justify-between max-sm:flex-col"
              :ui="{ container: 'w-full sm:max-w-md' }"
            >
              <EntityFieldRenderer
                :field="field"
                :model-value="formData[field.name]"
                :record-id="String(formData.id)"
                :disabled="isFieldDisabled(field.name)"
                entity-name="user"
                :form-state="formData"
                @update:model-value="
                  (val) => {
                    formData[field.name] = val;
                    formData = { ...formData };
                  }
                "
              />
            </UFormField>
          </template>
        </UForm>
      </UPageCard>
    </template>
  </div>
</template>
