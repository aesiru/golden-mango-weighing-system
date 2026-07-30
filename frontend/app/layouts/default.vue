<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { NavigationMenuItem } from "@nuxt/ui";
import { useAuthStore } from "~/stores/auth";
import type { RouteLocationMatched } from "vue-router";
import { useAttachmentApi } from "~/composables/useAttachmentApi";
import type { AttachmentItem } from "~/composables/useApiTypes";

const route = useRoute();
const authStore = useAuthStore();
const { logout } = useAuth();
const { bootInfo } = useBootInfo();

const isLogin = computed(() => route.path === "/login");

const sidebarOpen = useLocalStorage("sidebar-open", true);

const colorMode = useColorMode();

const { getAttachments, getAttachmentViewUrl } = useAttachmentApi();

const brandingTitle = computed(
  () => "Golden Mango Weighing System",
);
const brandingDescription = computed(
  () =>
    bootInfo.value?.branding_settings?.description ||
    "Proof in every reading. Every mango, accounted for.",
);
const brandingLogoUrl = computed(
  () => "/mango_logo.jpg",
);

// Avatar state
const avatarAttachment = ref<AttachmentItem | null>(null);

const avatarUrl = computed(() => {
  if (!authStore.user?.id || !avatarAttachment.value) return undefined;
  return getAttachmentViewUrl(
    "user",
    String(authStore.user.id),
    avatarAttachment.value.id,
    authStore.token || undefined,
  );
});

const loadUserAvatar = async () => {
  if (!authStore.user?.id) {
    avatarAttachment.value = null;
    return;
  }
  try {
    const res = await getAttachments("user", String(authStore.user.id));
    if (res.status !== "success") return;
    avatarAttachment.value =
      res.data.find((a) => a.mime_type?.startsWith("image/")) ?? null;
  } catch {
    avatarAttachment.value = null;
  }
};

const user = computed(() => ({
  name: authStore.displayName,
  avatar: {
    src: avatarUrl.value || brandingLogoUrl.value || undefined,
    alt: authStore.displayName,
  },
}));

const userItems = computed(() => [
  [
    {
      label: "Profile",
      icon: "i-lucide-user",
      to: "/profile",
    },
    {
      label: "Logout",
      icon: "i-lucide-log-out",
      onSelect: logout,
    },
  ],
]);

const sidebarEntities = computed(() => bootInfo.value?.sidebar?.entities || []);
const sidebarNavigation = computed(
  () => bootInfo.value?.sidebar?.navigation || [],
);

const formatLabel = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (m: string) => m.toUpperCase());

type SidebarNavigationItem = NavigationMenuItem;
type SidebarNavigationGroup = SidebarNavigationItem[];

const isDefined = <T,>(value: T | null | undefined): value is T =>
  value != null;

const moduleNavigationGroups = computed(() => {
  return sidebarNavigation.value
    .map((moduleConfig) => {
      const items = moduleConfig.items
        .map((item) => {
          if (item.type === "entity") {
            return {
              label: item.label,
              icon: item.icon,
              to: item.to,
            } satisfies SidebarNavigationItem;
          }
          return {
            label: item.label,
            icon: item.icon,
            children: item.children.map((child) => ({
              label: child.label,
              icon: child.icon,
              to: child.to,
            })),
            defaultOpen: item.defaultOpen ?? true,
          } satisfies SidebarNavigationItem;
        })
        .filter(isDefined);

      if (!items.length) return null;

      return [
        {
          label: moduleConfig.label,
          type: "label",
          slot: `${moduleConfig.key}-label`,
        },
        ...items,
      ] satisfies SidebarNavigationGroup;
    })
    .filter(isDefined);
});

const navigationItems = computed(() => {
  const baseGroup: SidebarNavigationGroup = [
    { label: "Navigation", type: "label", slot: "navigation-label" },
    { label: "Home", icon: "i-lucide-home", to: "/" },
    {
      label: "Dashboard",
      icon: "i-lucide-layout-dashboard",
      to: "/dashboard",
    },
    // {
    //   label: "Calendar",
    //   icon: "i-lucide-calendar",
    //   to: "/calendar",
    //   slot: "calendar",
    // },
    // {
    //   label: "Diagram",
    //   icon: "i-lucide-network",
    //   to: "/diagram",
    // },
    {
      label: "Reports",
      icon: "i-lucide-file-bar-chart",
      to: "/reports",
      slot: "reports",
    },
    // {
    //   label: "Notification Manager",
    //   icon: "i-lucide-bell-ring",
    //   to: "/notifications",
    // },
  ];

  const adminGroup: SidebarNavigationGroup = authStore.isSuperuser
    ? [
        { label: "Settings", type: "label", slot: "settings-label" },
        { label: "General", icon: "i-lucide-cog", to: "/settings" },
        { label: "Admin", icon: "i-lucide-shield", to: "/admin" },
        { label: "Workflow", icon: "i-lucide-git-branch", to: "/workflow" },
        {
          label: "Model Editor",
          icon: "i-lucide-database",
          to: "/model-editor",
        },
        {
          label: "Import & Export",
          icon: "i-lucide-arrow-up-down",
          to: "/import-export",
        },
      ]
    : [];

  const moduleGroups = moduleNavigationGroups.value.filter(isDefined);

  const allGroups = [baseGroup, ...moduleGroups];
  if (adminGroup.length > 0) {
    allGroups.push(adminGroup);
  }

  return allGroups;
});

const getEntityLabel = (name: string) =>
  sidebarEntities.value.find((m) => m.name === name)?.label;

const getMetaLabel = (record?: RouteLocationMatched) => {
  const meta = record?.meta as
    | { breadcrumb?: string | ((r: typeof route) => string); title?: string }
    | undefined;
  if (!meta) return "";
  if (typeof meta.breadcrumb === "function") return meta.breadcrumb(route);
  if (meta.breadcrumb) return String(meta.breadcrumb);
  if (record?.path?.includes(":")) return "";
  return meta.title ? String(meta.title) : "";
};

const getCrumbLabel = (segment: string, record?: RouteLocationMatched) => {
  const metaLabel = getMetaLabel(record);
  if (metaLabel) return metaLabel;
  if (record?.path?.includes(":entity")) {
    const entityName = String(route.params.entity || segment);
    return getEntityLabel(entityName) || formatLabel(entityName);
  }
  if (record?.path?.includes(":id") && segment === "new") return "New";
  return getEntityLabel(segment) || formatLabel(segment);
};

const crumbs = computed(() => {
  const raw = (route.path || "").split("?")[0];
  const parts = raw?.split("/").filter(Boolean) || [];
  const matched = route.matched.filter((record) => record.path !== "/");
  return parts.map((seg, idx) => ({
    key: seg,
    label: getCrumbLabel(seg, matched[idx]),
    href: "/" + parts.slice(0, idx + 1).join("/"),
  }));
});

const { notifications, unreadCount, markRead, markAllRead } =
  useNotificationCenter();

onMounted(() => {
  loadUserAvatar();
});
</script>

<template>
  <div v-if="isLogin" class="w-full">
    <slot />
  </div>

  <div v-else class="flex flex-col h-screen">
    <UHeader
      toggle-side="left"
      :ui="{ container: 'w-full max-w-full mx-0 px-4!' }"
    >
      <template #toggle>
        <UButton
          icon="i-lucide-panel-left"
          color="neutral"
          variant="ghost"
          aria-label="Toggle sidebar"
          @click="sidebarOpen = !sidebarOpen"
        />
      </template>

      <template #title>
        <div class="flex items-center gap-2">
          <img
            v-if="brandingLogoUrl"
            :src="brandingLogoUrl"
            alt="Organization logo"
            class="w-8 h-8 rounded-md object-contain"
          />
          <UIcon v-else name="i-lucide-package" class="size-8 text-primary" />
          <div class="flex flex-col">
            <div class="text-sm font-bold leading-tight">
              {{ brandingTitle }}
            </div>
            <div
              class="text-xs text-muted-foreground leading-tight font-normal"
            >
              {{ brandingDescription }}
            </div>
          </div>
        </div>
      </template>

      <template #right>
        <UPopover>
          <div class="relative">
            <UButton variant="outline" icon="i-lucide-bell" size="sm" />
            <span
              v-if="unreadCount > 0"
              class="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white"
            >
              {{ unreadCount > 9 ? "9+" : unreadCount }}
            </span>
          </div>

          <template #content>
            <div class="w-80 p-3 space-y-3">
              <div class="flex items-center justify-between">
                <p class="text-sm font-semibold">Notifications</p>
                <UButton
                  v-if="unreadCount > 0"
                  variant="link"
                  size="xs"
                  @click="markAllRead"
                >
                  Mark all read
                </UButton>
              </div>
              <div
                v-if="notifications.length"
                class="space-y-2 max-h-64 overflow-y-auto"
              >
                <div
                  v-for="note in notifications.slice(0, 20)"
                  :key="note.id"
                  class="rounded-md border border-accented p-2 cursor-pointer transition-colors"
                  :class="note.read ? 'opacity-60' : 'bg-primary/5'"
                  @click="markRead(note.id)"
                >
                  <p class="text-sm font-medium">{{ note.title }}</p>
                  <p
                    v-if="note.description"
                    class="text-xs text-muted-foreground"
                  >
                    {{ note.description }}
                  </p>
                </div>
              </div>
              <p v-else class="text-xs text-muted-foreground text-center py-4">
                No notifications
              </p>
            </div>
          </template>
        </UPopover>
      </template>
    </UHeader>

    <div class="flex flex-1 min-h-0 overflow-hidden">
      <USidebar
        v-model:open="sidebarOpen"
        collapsible="icon"
        :ui="{
          gap: 'h-[calc(100%-var(--ui-header-height))]',
          container:
            'absolute top-(--ui-header-height) bottom-0 h-[calc(100%-var(--ui-header-height))]',
        }"
      >
        <template #default="{ state }">
          <UNavigationMenu
            :key="state"
            orientation="vertical"
            :items="navigationItems"
            :collapsed="state === 'collapsed'"
            :tooltip="true"
            :ui="{ link: 'p-1.5 overflow-hidden' }"
          >
            <template #navigation-label-trailing>
              <UBadge label="MENU" color="neutral" variant="soft" size="sm" />
            </template>
            <template #reports-trailing>
              <UBadge
                label="BETA"
                color="neutral"
                variant="outline"
                size="sm"
              />
            </template>
            <template #settings-label-trailing>
              <UBadge label="ADMIN" color="neutral" variant="soft" size="sm" />
            </template>
          </UNavigationMenu>
        </template>

        <template #footer>
          <UDropdownMenu
            :items="userItems"
            :content="{ align: 'center', collisionPadding: 12 }"
            :ui="{ content: 'w-(--reka-dropdown-menu-trigger-width) min-w-48' }"
          >
            <UButton
              v-bind="user"
              :label="user?.name"
              trailing-icon="i-lucide-chevrons-up-down"
              color="neutral"
              variant="ghost"
              square
              class="w-full data-[state=open]:bg-elevated overflow-hidden"
              :ui="{
                trailingIcon: 'text-dimmed ms-auto',
              }"
            />
          </UDropdownMenu>
        </template>
      </USidebar>

      <!-- <div class="flex items-center space-x-2 min-w-0 mb-4">
          <UBreadcrumb
            :items="[
              { label: 'Home', to: '/' },
              ...crumbs.map((c) => ({ label: c.label, to: c.href })),
            ]"
            separator-icon="i-lucide-chevron-right"
          />
        </div> -->

      <main class="flex-1 overflow-y-auto min-h-0">
        <slot />
      </main>
    </div>
  </div>
</template>
