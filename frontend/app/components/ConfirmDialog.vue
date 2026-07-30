<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string;
    description?: string;
    confirmLabel?: string;
    cancelLabel?: string;
    confirmColor?:
      | "primary"
      | "secondary"
      | "success"
      | "info"
      | "warning"
      | "error"
      | "neutral";
  }>(),
  {
    title: "Confirm",
    description: "Are you sure you want to continue?",
    confirmLabel: "Confirm",
    cancelLabel: "Cancel",
    confirmColor: "primary",
  },
);

const emit = defineEmits<{
  close: [value: boolean];
}>();
</script>

<template>
  <UModal :title="title" :description="description" :dismissible="false" :ui="{ footer: 'justify-end' }">
    <template #footer>
      <UButton color="neutral" variant="outline" @click="emit('close', false)">
        {{ cancelLabel }}
      </UButton>
      <UButton :color="confirmColor" @click="emit('close', true)">
        {{ confirmLabel }}
      </UButton>
    </template>
  </UModal>
</template>
