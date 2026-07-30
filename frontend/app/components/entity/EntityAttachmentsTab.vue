<script setup lang="ts">
import type {
  AttachmentItem,
  AttachmentConfig,
} from "~/composables/useApiTypes";
import { useAttachmentApi } from "~/composables/useAttachmentApi";

const props = defineProps<{
  entity: string;
  recordId: string;
  attachmentConfig?: AttachmentConfig | null;
}>();

const emit = defineEmits<{
  (e: "count-change", count: number): void;
}>();

const {
  getAttachments,
  uploadAttachment,
  getAttachmentDownloadUrl,
  deleteAttachment,
} = useAttachmentApi();
const toast = useToast();

const attachments = ref<AttachmentItem[]>([]);
const loading = ref(false);
const uploading = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

const maxAttachments = computed(
  () => props.attachmentConfig?.max_attachments || 10,
);

async function load() {
  loading.value = true;
  try {
    const res = await getAttachments(props.entity, props.recordId);
    if (res.status === "success") {
      attachments.value = res.data || [];
      emit("count-change", attachments.value.length);
    }
  } catch (err) {
    console.error("Failed to load attachments", err);
  } finally {
    loading.value = false;
  }
}

async function handleUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  if (!input.files?.length) return;
  uploading.value = true;
  try {
    for (const file of Array.from(input.files)) {
      const res = await uploadAttachment(props.entity, props.recordId, file);
      if (res.status === "success") {
        toast.add({ title: `Uploaded ${file.name}`, color: "success" });
      } else {
        toast.add({
          title: `Failed to upload ${file.name}`,
          description: res.message,
          color: "error",
        });
      }
    }
    await load();
  } catch (err: any) {
    toast.add({ title: err.message || "Upload failed", color: "error" });
  } finally {
    uploading.value = false;
    if (fileInput.value) fileInput.value.value = "";
  }
}

function handleDownload(att: AttachmentItem) {
  const url = getAttachmentDownloadUrl(props.entity, props.recordId, att.id);
  window.open(url, "_blank");
}

async function handleDelete(att: AttachmentItem) {
  try {
    const res = await deleteAttachment(props.entity, props.recordId, att.id);
    if (res.status === "success") {
      toast.add({ title: res.message, color: "success" });
      await load();
    } else {
      toast.add({ title: res.message || "Delete failed", color: "error" });
    }
  } catch (err: any) {
    toast.add({ title: err.message || "Delete failed", color: "error" });
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileIcon(mimeType: string | null): string {
  if (mimeType?.startsWith("image/")) return "i-lucide-image";
  if (mimeType === "application/pdf") return "i-lucide-file-text";
  return "i-lucide-file";
}

defineExpose({ load });

watch(
  () => props.recordId,
  () => load(),
  { immediate: true },
);
</script>

<template>
  <div class="border rounded-lg border-accented mt-4">
    <!-- Toolbar -->
    <div
      class="flex items-center justify-between gap-2 p-4 border-b border-accented"
    >
      <div class="flex items-center gap-2">
        <UButton
          icon="i-lucide-upload"
          size="md"
          :loading="uploading"
          :disabled="uploading"
          @click="fileInput?.click()"
        >
          Upload File
        </UButton>
        <input
          ref="fileInput"
          type="file"
          multiple
          class="hidden"
          @change="handleUpload"
        />
        <UButton
          icon="i-lucide-refresh-cw"
          variant="outline"
          size="md"
          :loading="loading"
          @click="load"
        />
      </div>
      <span class="text-sm text-muted">
        {{ attachments.length }} / {{ maxAttachments }} files
      </span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-8">
      <UIcon
        name="i-lucide-loader-2"
        class="animate-spin h-6 w-6 text-primary"
      />
    </div>

    <!-- Empty -->
    <div
      v-else-if="attachments.length === 0"
      class="text-center py-12 text-muted-foreground"
    >
      <UIcon name="i-lucide-paperclip" class="h-8 w-8 mx-auto mb-2" />
      <p class="text-sm">No attachments yet</p>
      <p class="text-xs mt-1">Click "Upload File" to add attachments</p>
    </div>

    <!-- List -->
    <div v-else class="divide-y divide-accented">
      <div
        v-for="att in attachments"
        :key="att.id"
        class="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
      >
        <div class="flex items-center gap-3 min-w-0 flex-1">
          <UIcon
            :name="fileIcon(att.mime_type)"
            class="h-5 w-5 text-muted-foreground shrink-0"
          />
          <div class="min-w-0">
            <div class="font-medium text-sm truncate">{{ att.file_name }}</div>
            <div class="text-xs text-muted-foreground">
              {{ formatFileSize(att.file_size) }}
              <span v-if="att.uploaded_by"> · by {{ att.uploaded_by }}</span>
              <span v-if="att.created_at">
                ·
                {{
                  new Date(att.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })
                }}
              </span>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-1 shrink-0">
          <UButton
            icon="i-lucide-download"
            variant="ghost"
            size="xs"
            @click="handleDownload(att)"
          />
          <UButton
            icon="i-lucide-trash-2"
            variant="ghost"
            size="xs"
            color="error"
            @click="handleDelete(att)"
          />
        </div>
      </div>
    </div>
  </div>
</template>
