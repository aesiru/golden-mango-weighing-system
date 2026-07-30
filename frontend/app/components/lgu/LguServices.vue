<template>
  <UPageSection
    title="Comprehensive Municipal Services"
    description="Access a wide range of government services designed to serve our community efficiently and transparently."
    :ui="{
      root: 'bg-secondary-50',
      container: 'relative z-10 flex items-center py-8 sm:py-12 lg:py-16',
      headline: 'text-center mb-8',
    }"
  >
    <template #headline>
      <UBadge size="xl" color="primary">Services</UBadge>
    </template>
    <UPageGrid>
      <UPageCard v-for="(card, index) in cards" :key="index" v-bind="card" />
    </UPageGrid>
  </UPageSection>
</template>

<script setup lang="ts">
const cards = ref([
  {
    title: "Business Permits",
    description:
      "Apply for business permits and licenses online with our streamlined process.",
    icon: "i-lucide-clipboard-list",
    to: "/services/business-permits",
  },
  {
    title: "Health Services",
    description:
      "Access medical facilities, health programs, and emergency services.",
    icon: "i-lucide-heart",
    to: "/services/health",
  },
  {
    title: "Education Services",
    description:
      "Access public schools, scholarships, and educational programs.",
    icon: "i-lucide-graduation-cap",
    to: "/services/education",
  },
]);
</script>
