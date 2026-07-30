<script setup lang="ts">
import { useDeleteModalStore } from "~/stores/deleteModal";
import { storeToRefs } from "pinia";

const deleteModalStore = useDeleteModalStore();
const { isOpen, config, loading } = storeToRefs(deleteModalStore);

const modalTitle = computed(() => {
  if (!config.value) return "Delete";
  return `Delete ${config.value.entityName}`;
});

const displayName = computed(() => {
  if (!config.value?.itemName || config.value.itemName === "undefined") {
    return "";
  }
  return config.value.itemName;
});

const modalDescription = computed(() => {
  if (!config.value) return "This action cannot be undone.";
  const target = displayName.value
    ? `${config.value.entityName} ${displayName.value}`
    : config.value.entityName;
  return `Are you sure you want to delete ${target}? This action cannot be undone.`;
});
</script>

<template>
  <UModal
    v-model:open="isOpen"
    :title="modalTitle"
    :description="modalDescription"
  >
    <template #body>
      <div v-if="config">
        <p>
          Are you sure you want to delete {{ config.entityName }}
          <span v-if="displayName" class="font-semibold">{{ displayName }}</span
          >? This action cannot be undone.
        </p>
      </div>
    </template>

    <template #footer>
      <div class="flex gap-2 justify-end">
        <UButton
          color="neutral"
          variant="outline"
          @click="deleteModalStore.close"
          :disabled="loading"
        >
          Cancel
        </UButton>
        <UButton
          color="error"
          @click="deleteModalStore.confirm"
          :loading="loading"
          :disabled="!config"
        >
          Delete
        </UButton>
      </div>
    </template>
  </UModal>
</template>
