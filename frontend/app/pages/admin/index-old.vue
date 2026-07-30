<script setup lang="ts">
import { useAuthStore } from "~/stores/auth";
import { useBootInfo } from "~/composables/useBootInfo";
import { useUserActivity } from "~/composables/useUserActivity";

const authStore = useAuthStore();
const { bootInfo } = useBootInfo();
const { getHomeData } = useUserActivity();

const loading = ref(false);
const frequentEntities = ref<any[]>([]);
const frequentPages = ref<any[]>([]);
const recentRecords = ref<any[]>([]);
const entityIcons = ref<Record<string, string>>({});

// Get today's date
const today = new Date();
const dateOptions: Intl.DateTimeFormatOptions = {
  weekday: "long",
  year: "numeric",
  month: "long",
  day: "numeric",
};
const todayDate = today.toLocaleDateString("en-US", dateOptions);

const moduleIcons: Record<string, string> = {
  core: "i-lucide-settings",
};

const formatLabel = (str: string) =>
  str
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

const getModuleIcon = (mod: string) => moduleIcons[mod] || "i-lucide-folder";

const entities = computed(() => bootInfo.value?.sidebar?.entities || []);

const branding = computed(
  () =>
    bootInfo.value?.branding_settings || {
      organization_name: "ManGO",
      description: "A modular application framework",
      logo_url: null,
    },
);

const groupedEntities = computed(() => {
  const groups: Record<string, any[]> = {};
  entities.value.forEach((e) => {
    const mod = e.module || "Other";
    if (!groups[mod]) groups[mod] = [];
    groups[mod].push(e);
  });
  return groups;
});

// Convert frequent entities to page card format
const entityPageCards = computed(() => {
  return frequentEntities.value.slice(0, 3).map((item) => {
    const entity = entities.value.find((e) => e.name === item.entity_name);
    const icon = entityIcons.value[item.entity_name] || "i-lucide-file-text";
    return {
      title: item.page_label,
      description: entity ? formatLabel(entity.module || "Other") : "System",
      to: `/${item.entity_name}`,
      icon: icon,
    };
  });
});

// Quick actions - last 4 pages visited (excluding home page)
const quickActions = computed(() => {
  return frequentPages.value
    .filter((item) => item.page_path !== "/")
    .slice(0, 4)
    .map((item) => {
      // Extract entity name from path if it's an entity page
      const pathParts = item.page_path.split("/").filter(Boolean);
      const entityName = pathParts[0];
      const entity = entities.value.find((e) => e.name === entityName);
      const icon = entity
        ? entityIcons.value[entityName] || "i-lucide-folder"
        : "i-lucide-arrow-right";

      return {
        title: item.page_label || formatLabel(entityName),
        description: "Quick access",
        to: item.page_path,
        icon: icon,
      };
    });
});

// Load user's frequent activities and recent records
onMounted(async () => {
  try {
    const data = await getHomeData(5, 5, 10, 30);
    frequentEntities.value = data.frequentEntities;
    frequentPages.value = data.frequentPages;
    recentRecords.value = data.recentRecords;
    entityIcons.value = data.entityIcons;
  } catch (error) {
    console.error("[Home] Failed to load data:", error);
  }
});

definePageMeta({
  title: "Home",
  middleware: "auth" as any,
});
</script>

<template>
  <div class="space-y-8 p-6">
    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <UIcon
        name="i-lucide-loader-2"
        class="animate-spin h-8 w-8 text-primary"
      />
    </div>

    <template v-else>
      <!-- PageCard with welcome message and date -->
      <div
        class="bg-gradient-to-br from-primary-800 to-primary-400 p-6 rounded-lg"
      >
        <div class="flex flex-col gap-3">
          <!-- left top -->
          <div class="">
            <p class="text-white text-sm">{{ todayDate }}</p>
            <h1 class="text-2xl font-bold text-white">
              Welcome, {{ authStore.displayName }}
            </h1>
          </div>
          <div>
            <!-- TODO: fetch from boot -->
            <UBadge
              :label="authStore.user?.roles?.[0] || 'User'"
              color="neutral"
              variant="solid"
              size="md"
            ></UBadge>
          </div>
        </div>
      </div>

      <!-- Quick Actions - last 4-5 pages visited -->
      <div v-if="quickActions.length > 0" class="space-y-3">
        <h2 class="text-lg font-semibold">Quick Actions</h2>
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          <UPageCard
            v-for="action in quickActions"
            :key="action.to"
            v-bind="action"
            variant="subtle"
          />
        </div>
      </div>

      <!-- Frequently Visited - using PageCard component -->
      <div v-if="entityPageCards.length > 0" class="space-y-2">
        <h2 class="text-lg font-semibold">Frequently Visited</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <UPageCard
            v-for="(card, index) in entityPageCards"
            :key="index"
            v-bind="card"
            variant="subtle"
          />
        </div>
      </div>

      <!-- What's next? - latest records created by user -->
      <div class="space-y-3">
        <h2 class="text-lg font-semibold">What's next?</h2>
        <div
          v-if="recentRecords.length > 0"
          class="border border-accented rounded-lg bg-card overflow-hidden"
        >
          <table class="w-full text-sm">
            <thead class="bg-muted/50">
              <tr>
                <th class="text-left p-3 font-medium">Record</th>
                <th class="text-left p-3 font-medium">Entity</th>
                <th class="text-left p-3 font-medium">Created</th>
                <th class="text-right p-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="record in recentRecords"
                :key="`${record.entity_name}-${record.record_id}`"
                class="border-t border-accented"
              >
                <td class="p-3">{{ record.record_title }}</td>
                <td class="p-3">{{ record.entity_label }}</td>
                <td class="p-3 text-muted-foreground">
                  {{
                    record.created_at
                      ? new Date(record.created_at).toLocaleDateString()
                      : "-"
                  }}
                </td>
                <td class="p-3 text-right">
                  <UButton
                    :to="`/${record.entity_name}/${record.record_id}`"
                    variant="ghost"
                    size="xs"
                    icon="i-lucide-external-link"
                  >
                    View
                  </UButton>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="border border-accented rounded-lg bg-card">
          <div class="p-4 text-center text-muted-foreground text-sm">
            No recent records created by you
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
