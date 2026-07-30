<script setup lang="ts">
import type { NavigationMenuItem } from "@nuxt/ui";

const links = [
  [
    {
      label: "Details",
      icon: "i-lucide-user",
      to: "/profile",
      exact: true,
    },
    {
      label: "Notifications",
      icon: "i-lucide-bell",
      to: "/profile/notifications",
    },
    {
      label: "Security",
      icon: "i-lucide-shield",
      to: "/profile/security",
    },
    {
      label: "Local Data",
      icon: "i-lucide-database-zap",
      to: "/profile/local-data",
    },
  ],
] satisfies NavigationMenuItem[][];

definePageMeta({ middleware: "auth" as any });
</script>

<template>
  <UDashboardPanel id="profile">
    <template #header>
      <UDashboardNavbar title="Profile">
        <template #leading>
          <!-- TODO: Add here name of user -->
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <!-- NOTE: The `-mx-1` class is used to align with the `DashboardSidebarCollapse` button here. -->
        <UNavigationMenu :items="links" highlight class="-mx-1 flex-1" />
      </UDashboardToolbar>
    </template>

    <template #body>
      <div
        class="mx-auto flex w-full max-w-4xl flex-col gap-4 sm:gap-6 lg:gap-12"
      >
        <NuxtPage />
      </div>
    </template>
  </UDashboardPanel>
</template>
