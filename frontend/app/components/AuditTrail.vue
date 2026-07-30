<script setup lang="ts">
import { useAuditApi } from "~/composables/useAuditApi";
import type { AuditEntry } from "~/composables/useApiTypes";

const props = defineProps<{
  entity: string;
  recordId: string;
}>();

const { getAuditTrail } = useAuditApi();

const entries = ref<AuditEntry[]>([]);
const loading = ref(false);
const total = ref(0);
const page = ref(1);
const pageSize = 10;

const actionColors: Record<string, string> = {
  create: "text-green-600 dark:text-green-400",
  update: "text-blue-600 dark:text-blue-400",
  delete: "text-red-600 dark:text-red-400",
  workflow: "text-purple-600 dark:text-purple-400",
};

const actionIcons: Record<string, string> = {
  create: "i-lucide-plus-circle",
  update: "i-lucide-pencil",
  delete: "i-lucide-trash-2",
  workflow: "i-lucide-git-branch",
};

async function load() {
  loading.value = true;
  try {
    const res = await getAuditTrail(
      props.entity,
      props.recordId,
      page.value,
      pageSize,
    );
    entries.value = res.data || [];
    total.value = res.total || 0;
  } catch {
    entries.value = [];
  } finally {
    loading.value = false;
  }
}

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function changedFieldsSummary(fields: string[] | null): string {
  if (!fields || fields.length === 0) return "";
  if (fields.length <= 3) return fields.join(", ");
  return `${fields.slice(0, 3).join(", ")} +${fields.length - 3} more`;
}

watch(
  () => props.recordId,
  () => {
    page.value = 1;
    load();
  },
  { immediate: true },
);
watch(page, load);
</script>

<template>
  <div class="space-y-3">
    <div
      v-if="loading"
      class="flex items-center gap-2 py-8 justify-center text-muted-foreground"
    >
      <UIcon name="i-lucide-loader-2" class="animate-spin" />
      <span>Loading audit trail…</span>
    </div>

    <div
      v-else-if="entries.length === 0"
      class="text-center py-8 text-muted-foreground"
    >
      No audit history available.
    </div>

    <div v-else class="space-y-2">
      <div
        v-for="entry in entries"
        :key="entry.id"
        class="border rounded-lg p-3 bg-card border-accented"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="flex items-center gap-2">
            <UIcon
              :name="actionIcons[entry.action] || 'i-lucide-activity'"
              :class="actionColors[entry.action] || 'text-muted-foreground'"
              size="18"
            />
            <span
              class="font-medium capitalize"
              :class="actionColors[entry.action]"
            >
              {{ entry.action }}
            </span>
            <span v-if="entry.username" class="text-sm text-muted-foreground">
              by {{ entry.username }}
            </span>
          </div>
          <span class="text-xs text-muted-foreground whitespace-nowrap">
            {{ formatDate(entry.created_at) }}
          </span>
        </div>

        <div
          v-if="entry.changed_fields && entry.changed_fields.length"
          class="mt-1 text-sm text-muted-foreground"
        >
          Changed: {{ changedFieldsSummary(entry.changed_fields) }}
        </div>

        <details
          v-if="entry.before_snapshot || entry.after_snapshot"
          class="mt-2"
        >
          <summary
            class="text-xs text-muted-foreground cursor-pointer hover:text-foreground"
          >
            Show details
          </summary>
          <div class="mt-1 grid grid-cols-2 gap-2 text-xs">
            <div v-if="entry.before_snapshot">
              <div class="font-medium text-muted-foreground mb-1">Before</div>
              <pre
                class="bg-muted p-2 rounded overflow-auto max-h-40 text-[11px]"
                >{{ JSON.stringify(entry.before_snapshot, null, 2) }}</pre
              >
            </div>
            <div v-if="entry.after_snapshot">
              <div class="font-medium text-muted-foreground mb-1">After</div>
              <pre
                class="bg-muted p-2 rounded overflow-auto max-h-40 text-[11px]"
                >{{ JSON.stringify(entry.after_snapshot, null, 2) }}</pre
              >
            </div>
          </div>
        </details>
      </div>

      <div v-if="total > pageSize" class="flex justify-center pt-2">
        <UPagination v-model="page" :total="total" :items-per-page="pageSize" />
      </div>
    </div>
  </div>
</template>
