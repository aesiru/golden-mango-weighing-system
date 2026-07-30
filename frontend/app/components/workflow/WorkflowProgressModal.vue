<script setup lang="ts">
import type { WorkflowProgressResponse } from '~/composables/useApiTypes'

const props = defineProps<{
  open: boolean
  loading: boolean
  progress: WorkflowProgressResponse | null
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

const isOpen = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
})
</script>

<template>
  <UModal
    v-model:open="isOpen"
    title="Workflow Progress"
    description="Backend-generated workflow timeline and related process status."
    :ui="{ content: 'sm:max-w-4xl' }"
  >
    <template #body>
      <div class="min-h-40">
        <div v-if="loading" class="flex min-h-40 items-center justify-center">
          <UIcon name="i-lucide-loader-2" class="h-8 w-8 animate-spin text-primary" />
        </div>

        <div v-else-if="progress?.node" class="space-y-4">
          <div>
            <div class="text-lg font-semibold">{{ progress.title }}</div>
            <p v-if="progress.summary" class="text-sm text-muted">
              {{ progress.summary }}
            </p>
          </div>

          <WorkflowProgressTree :node="progress.node" />
        </div>

        <UAlert
          v-else
          color="warning"
          variant="subtle"
          title="No workflow progress available"
          description="This record does not currently have workflow progress data to display."
        />
      </div>
    </template>

    <template #footer>
      <div class="flex justify-end">
        <UButton variant="outline" color="neutral" @click="isOpen = false">
          Close
        </UButton>
      </div>
    </template>
  </UModal>
</template>
