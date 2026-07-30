<script setup lang="ts">
import type { NotificationCatalogEntry } from "~/composables/useNotificationSubscriptionsApi";
import { useNotificationSubscriptionsApi } from "~/composables/useNotificationSubscriptionsApi";
import { useAuthStore } from "~/stores/auth";

const api = useNotificationSubscriptionsApi();
const authStore = useAuthStore();
const toast = useToast();

const loading = ref(true);
const savingId = ref<string | null>(null);
const catalog = ref<NotificationCatalogEntry[]>([]);
const mine = ref<any[]>([]);

function subscriptionActive(s: any): boolean {
  return s.is_active === true || s.is_active === 1;
}

/** Match subscription by routing keys so UI works even if API omits catalog_id. */
function rowForEntry(entry: NotificationCatalogEntry) {
  const match = mine.value.find(
    (s) =>
      subscriptionActive(s) &&
      s.entity_type === entry.entity_type &&
      s.event === entry.event,
  );
  return match;
}

function isSubscribed(entry: NotificationCatalogEntry) {
  return !!rowForEntry(entry);
}

const deliveryEmail = computed(
  () => authStore.user?.email || "Add an email address to your profile",
);

const tableColumns = [
  {
    accessorKey: "category",
    header: "Category",
  },
  {
    accessorKey: "title",
    header: "Notification",
  },
  {
    accessorKey: "status",
    header: "Status",
  },
  {
    accessorKey: "action",
    header: "Action",
  },
];

const loadAll = async () => {
  try {
    loading.value = true;
    const [catRes, subRes] = await Promise.all([
      api.getCatalog(),
      api.listMySubscriptions(),
    ]);
    catalog.value = (catRes as any)?.data ?? [];
    mine.value = (subRes as any)?.data ?? [];
  } catch (error: any) {
    toast.add({
      title: error?.message || error?.detail || "Failed to load notifications",
      color: "error",
    });
  } finally {
    loading.value = false;
  }
};

const toggle = async (entry: NotificationCatalogEntry) => {
  const existing = rowForEntry(entry);
  try {
    savingId.value = entry.catalog_id;
    if (existing) {
      await api.unsubscribe(existing.id);
      mine.value = mine.value.filter((s) => s.id !== existing.id);
      toast.add({ title: "Unsubscribed", color: "success" });
    } else {
      const res = await api.subscribe(entry.catalog_id);
      const row = (res as any)?.data;
      if (row?.id) {
        // Optimistically update local state
        mine.value = mine.value.filter((s) => s.id !== row.id);
        mine.value.push(row);
      }
      toast.add({ title: "Subscribed", color: "success" });
    }
  } catch (error: any) {
    toast.add({
      title: error?.message || error?.detail || "Could not update subscription",
      color: "error",
    });
  } finally {
    savingId.value = null;
  }
};

onMounted(() => {
  loadAll();
});

definePageMeta({
  title: "Email notifications",
  middleware: "auth" as any,
});
</script>

<template>
  <div class="space-y-6">
    <UPageCard
      title="Notifications"
      description="Choose which activity emails should be delivered to your account."
      variant="naked"
      orientation="horizontal"
      class="mb-4"
    >
      <UBadge color="neutral" variant="subtle" class="w-fit lg:ms-auto">
        {{ deliveryEmail }}
      </UBadge>
    </UPageCard>

    <div class="overflow-hidden rounded-lg border border-default">
      <UTable
        :data="catalog"
        :columns="tableColumns"
        :loading="loading"
        loading-color="primary"
        loading-animation="carousel"
        class="w-full"
      >
        <template #title-header>
          <span class="text-sm font-semibold">Notification</span>
        </template>

        <template #title-cell="{ row }">
          <div>
            <h3 class="text-md font-semibold text-highlighted">
              {{ row.getValue("title") || "No title" }}
            </h3>
            <p class="text-sm text-muted">
              {{ row.original?.description || "No description" }}
            </p>
          </div>
        </template>

        <template #category-cell="{ row }">
          <UBadge
            color="neutral"
            variant="subtle"
            size="md"
            :label="row.original?.category || row.original?.entity_type"
          />
        </template>

        <template #status-cell="{ row }">
          <UBadge
            v-if="isSubscribed(row.original)"
            color="success"
            variant="subtle"
            size="md"
            label="Active"
          />
          <UBadge
            v-else
            color="neutral"
            variant="subtle"
            size="md"
            label="Inactive"
          />
        </template>

        <template #action-cell="{ row }">
          <UButton
            :loading="savingId === row.original.catalog_id"
            :color="isSubscribed(row.original) ? 'neutral' : 'primary'"
            :variant="isSubscribed(row.original) ? 'soft' : 'solid'"
            :disabled="savingId !== null"
            size="sm"
            @click="toggle(row.original)"
          >
            {{ isSubscribed(row.original) ? "Unsubscribe" : "Subscribe" }}
          </UButton>
        </template>
      </UTable>
    </div>
  </div>
</template>
