/**
 * Attachment API Composable
 * =========================
 * Attachment CRUD for entity records.
 */
import { useApiFetch } from "./useApiFetch";
import type { ActionResponse, AttachmentItem } from "./useApiTypes";

// In-memory cache for attachments
const attachmentsCache = new Map<string, { status: string; data: AttachmentItem[]; total: number; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

const getCacheKey = (entity: string, recordId: string): string => `${entity}:${recordId}`;

const getCachedAttachments = (entity: string, recordId: string) => {
  const key = getCacheKey(entity, recordId);
  const cached = attachmentsCache.get(key);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached;
  }
  return null;
};

const setCachedAttachments = (
  entity: string,
  recordId: string,
  data: { status: string; data: AttachmentItem[]; total: number }
) => {
  const key = getCacheKey(entity, recordId);
  attachmentsCache.set(key, { ...data, timestamp: Date.now() });
};

const invalidateAttachmentsCache = (entity: string, recordId: string) => {
  const key = getCacheKey(entity, recordId);
  attachmentsCache.delete(key);
};

export const useAttachmentApi = () => {
  const { apiFetch, baseURL } = useApiFetch();

  return {
    async getAttachments(
      entity: string,
      recordId: string,
    ): Promise<{ status: string; data: AttachmentItem[]; total: number }> {
      const cached = getCachedAttachments(entity, recordId);
      if (cached) {
        return cached;
      }

      const result = await apiFetch(`${baseURL}/entity/${entity}/${recordId}/attachments`);
      setCachedAttachments(entity, recordId, result);
      return result;
    },

    async uploadAttachment(
      entity: string,
      recordId: string,
      file: File,
      description?: string,
    ): Promise<ActionResponse<AttachmentItem>> {
      const form = new FormData();
      form.append("file", file);
      if (description) form.append("description", description);
      const result = await apiFetch<ActionResponse<AttachmentItem>>(
        `${baseURL}/entity/${entity}/${recordId}/attachments`,
        { method: "POST", body: form },
      );
      invalidateAttachmentsCache(entity, recordId);
      return result;
    },

    getAttachmentDownloadUrl(
      entity: string,
      recordId: string,
      attachmentId: string,
    ): string {
      return `${baseURL}/entity/${entity}/${recordId}/attachments/${attachmentId}/download`;
    },

    getAttachmentViewUrl(
      entity: string,
      recordId: string,
      attachmentId: string,
      token?: string,
    ): string {
      const url = new URL(
        `${baseURL}/entity/${entity}/${recordId}/attachments/${attachmentId}/view`,
        window.location.origin,
      );
      if (token) {
        url.searchParams.set("token", token);
      }
      return url.toString();
    },

    async deleteAttachment(
      entity: string,
      recordId: string,
      attachmentId: string,
    ): Promise<ActionResponse> {
      const result = await apiFetch<ActionResponse>(
        `${baseURL}/entity/${entity}/${recordId}/attachments/${attachmentId}`,
        { method: "DELETE" },
      );
      invalidateAttachmentsCache(entity, recordId);
      return result;
    },

    invalidateCache: invalidateAttachmentsCache,
  };
};
