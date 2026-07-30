<script setup lang="ts">
import { useConfirmModalStore } from "~/stores/confirmModal";
import { storeToRefs } from "pinia";

const confirmModalStore = useConfirmModalStore();
const { isOpen, config, loading } = storeToRefs(confirmModalStore);
</script>

<template>
  <UModal
    v-model:open="isOpen"
    :title="config?.title || 'Confirm'"
    :description="config?.message"
  >
    <template #body>
      <p v-if="config?.message">{{ config.message }}</p>
    </template>

    <template #footer>
      <div class="flex gap-2 justify-end">
        <UButton
          color="neutral"
          variant="outline"
          @click="confirmModalStore.cancel"
          :disabled="loading"
        >
          {{ config?.cancelLabel || "Cancel" }}
        </UButton>
        <UButton
          :color="(config?.confirmColor as any) || 'primary'"
          @click="confirmModalStore.confirm"
          :loading="loading"
        >
          {{ config?.confirmLabel || "Confirm" }}
        </UButton>
      </div>
    </template>
  </UModal>
</template>
