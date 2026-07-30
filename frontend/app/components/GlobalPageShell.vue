<script setup lang="ts">
import { computed } from "vue";

const route = useRoute();
const isLogin = computed(() => route.path === "/login");

const publicNavigationItems = [
  {
    label: "About Us",
    children: [
      { label: "About Us", to: "#about", icon: "i-lucide-info" },
      {
        label: "Mission and Vision",
        to: "#mission-vision",
        icon: "i-lucide-target",
      },
      { label: "Our Barangays", to: "#barangays", icon: "i-lucide-map" },
      { label: "Maps and Directions", to: "#maps", icon: "i-lucide-map-2" },
      { label: "Official Seal", to: "#seal", icon: "i-lucide-shield" },
      { label: "Official Hymn", to: "#hymn", icon: "i-lucide-music" },
    ],
  },
  {
    label: "The Executive",
    children: [
      { label: "Mayor's Corner", to: "#mayors-corner", icon: "i-lucide-user" },
      {
        label: "Offices and Their Services",
        to: "#offices",
        icon: "i-lucide-building-2",
      },
      {
        label: "Awards and Recognitions",
        to: "#awards",
        icon: "i-lucide-award",
      },
      { label: "Past Mayors", to: "#past-mayors", icon: "i-lucide-history" },
    ],
  },
  {
    label: "Tourism",
    children: [
      {
        label: "Discover Our Town",
        to: "#discover",
        icon: "i-lucide-compass",
      },
      {
        label: "Flagship Destinations",
        to: "#destinations",
        icon: "i-lucide-map-pin",
      },
      {
        label: "Events & Festivals",
        to: "#festivals",
        icon: "i-lucide-sparkles",
      },
      { label: "Where to Eat", to: "#dining", icon: "i-lucide-utensils" },
    ],
  },
  {
    label: "Transparency",
    children: [
      {
        label: "Bids and Awards",
        to: "/transparency/bids-awards",
        icon: "i-lucide-gavel",
      },
      {
        label: "Full Disclosure Policy",
        to: "/transparency/full-disclosure",
        icon: "i-lucide-file-text",
      },
      {
        label: "Ordinances",
        to: "/transparency/ordinances",
        icon: "i-lucide-scale",
      },
      {
        label: "Resolutions",
        to: "/transparency/resolutions",
        icon: "i-lucide-stamp",
      },
      {
        label: "Downloadable Forms",
        to: "/transparency/forms",
        icon: "i-lucide-download",
      },
    ],
  },
  {
    label: "Connect",
    children: [
      { label: "Contact Us", to: "#contact", icon: "i-lucide-phone" },
      {
        label: "Career Opportunities",
        to: "#careers",
        icon: "i-lucide-briefcase",
      },
      {
        label: "Citizen's Charter",
        to: "#charter",
        icon: "i-lucide-book-open",
      },
    ],
  },
];

const footerColumns = [
  {
    label: "Government",
    children: [
      { label: "About Us", to: "#" },
      { label: "Municipal Officials", to: "#" },
      { label: "Organizational Chart", to: "#" },
    ],
  },
  {
    label: "Services",
    children: [
      { label: "Business Permit", to: "#" },
      { label: "Real Property Tax", to: "#" },
      { label: "Civil Registry", to: "#" },
    ],
  },
  {
    label: "Transparency",
    children: [
      { label: "Full Disclosure Policy", to: "#" },
      { label: "Bids and Awards", to: "#" },
      { label: "Citizen's Charter", to: "#" },
    ],
  },
];
</script>

<template>
  <div v-if="isLogin" class="w-full">
    <slot />
  </div>

  <div v-else class="flex flex-col min-h-screen">
    <UHeader :ui="{ root: 'h-24' }">
      <template #title>
        <div class="flex items-center space-x-4">
          <div class="flex items-center space-x-4">
            <div class="flex flex-col -space-y-1">
              <span
                class="text-xs uppercase font-medium text-foreground dark:text-gray-100"
              >
                Municipality of
              </span>
              <span class="text-xl font-bold text-foreground dark:text-gray-300">
                Consolacion
              </span>
            </div>
          </div>
        </div>
      </template>

      <UNavigationMenu
        :items="publicNavigationItems"
        content-orientation="vertical"
        class="ml-24"
      />

      <template #right>
        <UColorModeButton />
      </template>
    </UHeader>

    <UMain class="flex-1 overflow-hidden min-h-0">
      <slot />
    </UMain>

    <UFooter
      class="bg-slate-950 text-slate-100"
      :ui="{ top: 'border-b border-slate-700' }"
    >
      <template #top>
        <UContainer>
          <UFooterColumns :columns="footerColumns" />
        </UContainer>
      </template>
      <template #left>
        <div class="text-sm text-slate-400">
          <span>© 2026 Municipality.</span>
        </div>
      </template>
      <template #right>
        <UButton
          icon="i-simple-icons-facebook"
          color="neutral"
          variant="ghost"
          to="#"
          target="_blank"
          aria-label="Facebook"
        />
      </template>
    </UFooter>
  </div>
</template>
