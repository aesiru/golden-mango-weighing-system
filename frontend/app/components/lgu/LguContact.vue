<template>
  <UPageSection
    :ui="{
      container: 'relative z-10 flex items-center py-8 sm:py-12 lg:py-16',
    }"
  >
    <UPageCTA
      title="Contact Us"
      description="Municipal Hall Building, National Highway, Poblacion"
      x
      :links="[
        {
          label: 'Visit Municipal Hall',
          color: 'primary',
          variant: 'solid',
          size: 'lg',
          icon: 'i-lucide-map-pin',
          to: '#contact',
        },
        {
          label: 'Call Emergency Hotline',
          color: 'secondary',
          variant: 'outline',
          size: 'lg',
          icon: 'i-lucide-phone',
          to: 'tel:032-265-7398',
        },
      ]"
      variant="soft"
    >
      <UPageGrid cols="1" sm="2" lg="3">
        <UPageCard
          v-for="(number, name) in contactNumbers"
          :key="name"
          :title="name"
          :description="number"
          icon="i-lucide-phone"
          :to="`tel:${number}`"
        />
      </UPageGrid>
    </UPageCTA>
  </UPageSection>
</template>

<script setup lang="ts">
// turn into name: number object
const contactNumbers = {
  "Municipal Hall": "(032) 123-4567",
  "Police Station": "(032) 123-4568",
  "Fire Station": "(032) 123-4569",
};
</script>
