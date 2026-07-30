<script setup lang="ts">
defineProps<{
  title?: string;
}>();
</script>

<template>
  <UModal
    :title="title || 'Please wait'"
    :description="'A task is currently running'"
    :dismissible="false"
    :close="false"
    :ui="{ content: 'sm:max-w-xs' }"
  />
</template>
