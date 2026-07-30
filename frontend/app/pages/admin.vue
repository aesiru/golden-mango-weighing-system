<script setup lang="ts">
import type { NavigationMenuItem } from "@nuxt/ui";

const links = [
  [
    {
      label: "Users",
      icon: "i-lucide-users",
      to: "/admin",
      exact: true,
    },
    {
      label: "Roles",
      icon: "i-lucide-shield",
      to: "/admin/roles",
    },
    {
      label: "Permissions",
      icon: "i-lucide-lock",
      to: "/admin/permissions",
    },
  ],
] satisfies NavigationMenuItem[][];

definePageMeta({ middleware: "auth" as any });
</script>

<template>
  <UDashboardPanel id="admin">
    <template #header>
      <UDashboardNavbar title="Admin Panel">
        <template #leading>
          <!-- TODO: Add here admin-specific info if needed -->
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <!-- NOTE: The `-mx-1` class is used to align with the `DashboardSidebarCollapse` button here. -->
        <UNavigationMenu :items="links" highlight class="-mx-1 flex-1" />
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="mx-auto flex w-full flex-col gap-4 sm:gap-6 lg:gap-12">
        <NuxtPage />
      </div>
    </template>
  </UDashboardPanel>
</template>
