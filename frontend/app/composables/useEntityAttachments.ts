/**
 * useEntityAttachments
 * ====================
 * Manages attachment state and handlers for an entity record.
 * Wraps useAttachmentApi — do not call the API directly from pages.
 *
 * Usage:
 *   const { attachments, attachmentsLoading, attachmentUploading, attachmentCount,
 *           allowAttachments, loadAttachments, handleAttachmentUpload,
 *           handleDeleteAttachment, handleDownloadAttachment, formatFileSize }
 *     = useEntityAttachments(entityName, recordId, entityMeta)
 */
import type { Ref, ComputedRef } from "vue";
import type { EntityMeta, AttachmentItem } from "~/composables/useApiTypes";
import { useAttachmentApi } from "~/composables/useAttachmentApi";

export function useEntityAttachments(
  entityName: ComputedRef<string>,
  recordId: ComputedRef<string>,
  entityMeta: Ref<EntityMeta | null>,
  isNew: ComputedRef<boolean>,
) {
  const { getAttachments, uploadAttachment, deleteAttachment, getAttachmentDownloadUrl } =
    useAttachmentApi();
  const toast = useToast();
  const deleteDialog = useDeleteDialog();

  const attachments = ref<AttachmentItem[]>([]);
  const attachmentsLoading = ref(false);
  const attachmentUploading = ref(false);

  const allowAttachments = computed(() => {
    const config = entityMeta.value?.attachment_config;
    return config?.allow_attachments === true;
  });

  const attachmentCount = computed(() => attachments.value.length);

  const loadAttachments = async () => {
    if (isNew.value || !allowAttachments.value) return;
    attachmentsLoading.value = true;
    try {
      const res = await getAttachments(entityName.value, recordId.value);
      if (res.status === "success") {
        attachments.value = res.data || [];
      }
    } catch (err) {
      console.error("Failed to load attachments", err);
    } finally {
      attachmentsLoading.value = false;
    }
  };

  const handleAttachmentUpload = async (event: Event) => {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (!files || files.length === 0) return;

    attachmentUploading.value = true;
    try {
      for (const file of Array.from(files)) {
        const res = await uploadAttachment(entityName.value, recordId.value, file);
        if (res.status === "success") {
          if (res.message) {
            toast.add({ title: res.message, color: "success", type: "foreground" });
          }
        } else {
          toast.add({
            title: res.message || `Upload failed: ${file.name}`,
            color: "error",
            type: "foreground",
          });
        }
      }
      await loadAttachments();
    } catch (err: any) {
      if (err?.message) {
        toast.add({ title: err.message, color: "error", type: "foreground" });
      }
    } finally {
      attachmentUploading.value = false;
      if (input) input.value = "";
    }
  };

  const handleDeleteAttachment = (attachment: AttachmentItem) => {
    (async () => {
      const confirmed = await deleteDialog({
        entityName: "Attachment",
        itemName: attachment.file_name,
      });
      if (!confirmed) return;

      try {
        const res = await deleteAttachment(
          entityName.value,
          recordId.value,
          attachment.id,
        );
        if (res.status === "success") {
          if (res.message) {
            toast.add({ title: res.message, color: "success", type: "foreground" });
          }
          await loadAttachments();
        } else {
          if (res.message) {
            toast.add({ title: res.message, color: "error", type: "foreground" });
          }
        }
      } catch (err: any) {
        if (err?.message) {
          toast.add({ title: err.message, color: "error", type: "foreground" });
        }
      }
    })();
  };

  const handleDownloadAttachment = (attachment: AttachmentItem) => {
    const url = getAttachmentDownloadUrl(entityName.value, recordId.value, attachment.id);
    const token = localStorage.getItem("auth_token");
    const link = document.createElement("a");
    link.href = url + (token ? `?token=${token}` : "");
    link.download = attachment.file_name;
    link.target = "_blank";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return {
    attachments,
    attachmentsLoading,
    attachmentUploading,
    attachmentCount,
    allowAttachments,
    loadAttachments,
    handleAttachmentUpload,
    handleDeleteAttachment,
    handleDownloadAttachment,
    formatFileSize,
  };
}
