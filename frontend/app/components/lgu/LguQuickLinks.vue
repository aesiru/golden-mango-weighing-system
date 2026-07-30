<template>
  <UPageSection
    headline="Services"
    title="Quick Access to Municipal Services"
    description="Access essential government services and information online with our digital platform."
    :features="[
      {
        title: 'Business Permits',
        description: 'Apply and manage business permits online',
        icon: 'i-lucide-file-text',
        to: '#business-permits',
      },
      {
        title: 'Property Tax',
        description: 'Pay and inquire about real property taxes',
        icon: 'i-lucide-home',
        to: '#property-tax',
      },
      {
        title: 'Online Payments',
        description: 'Secure payment gateway for municipal services',
        icon: 'i-lucide-credit-card',
        to: '#payments',
      },
      {
        title: 'Citizen Services',
        description: 'Access various citizen services online',
        icon: 'i-lucide-users',
        to: '#services',
      },
    ]"
  />
</template>

<script setup lang="ts">
// Component setup can be added here if needed
</script>
