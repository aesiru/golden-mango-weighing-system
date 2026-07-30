<script setup lang="ts">
import type { NavigationMenuItem } from "@nuxt/ui";

const links = [
  [
    {
      label: "Workflows",
      icon: "i-lucide-git-branch",
      to: "/workflow",
      exact: true,
    },
    {
      label: "States",
      icon: "i-lucide-circle-dot",
      to: "/workflow/states",
    },
    {
      label: "Actions",
      icon: "i-lucide-bolt",
      to: "/workflow/actions",
    },
  ],
] satisfies NavigationMenuItem[][];

definePageMeta({ middleware: "auth" as any });
</script>

<template>
  <UDashboardPanel id="workflow">
    <template #header>
      <UDashboardNavbar title="Workflow">
        <template #leading>
          <!-- TODO: Add here workflow-specific info if needed -->
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <!-- NOTE: The `-mx-1` class is used to align with the `DashboardSidebarCollapse` button here. -->
        <UNavigationMenu :items="links" highlight class="-mx-1 flex-1" />
      </UDashboardToolbar>
    </template>

    <template #body>
      <div
        class="mx-auto flex w-full flex-col gap-4 sm:gap-6 lg:gap-12"
      >
        <NuxtPage />
      </div>
    </template>
  </UDashboardPanel>
</template>
