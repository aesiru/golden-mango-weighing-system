<script setup lang="ts">
import type { StepperItem } from '@nuxt/ui'
import type { WorkflowProgressNode } from '~/composables/useApiTypes'

const props = defineProps<{
  node: WorkflowProgressNode
  level?: number
}>()

const level = computed(() => props.level ?? 0)

const stepItems = computed<StepperItem[]>(() => {
  return (props.node.steps || []).map((step) => ({
    title: step.title,
    description: step.description,
    value: step.key,
    icon: step.status === 'completed'
      ? 'i-lucide-check'
      : step.status === 'current'
        ? 'i-lucide-circle-dot'
        : 'i-lucide-circle',
  }))
})

const activeStep = computed(() => {
  const current = props.node.steps?.find((step) => step.current)
  return current?.key ?? props.node.steps?.[0]?.key
})
</script>

<template>
  <div class="space-y-4 rounded-lg border border-accented bg-default p-4">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <div class="text-xs uppercase tracking-wide text-muted">{{ node.label }}</div>
        <div class="font-semibold break-words">{{ node.title }}</div>
        <p v-if="node.summary" class="mt-1 text-sm text-muted">
          {{ node.summary }}
        </p>
      </div>
      <UBadge variant="subtle" color="primary">
        {{ node.current_state_label }}
      </UBadge>
    </div>

    <UStepper
      v-if="stepItems.length"
      :items="stepItems"
      :model-value="activeStep"
      orientation="vertical"
      disabled
      class="w-full"
    />

    <div v-if="node.next_actions?.length" class="space-y-2">
      <div class="text-sm font-medium">Next</div>
      <div class="grid gap-2">
        <div
          v-for="action in node.next_actions"
          :key="`${node.entity}-${node.record_id}-${action.action}`"
          class="rounded-md border border-accented bg-muted/30 px-3 py-2"
        >
          <div class="text-sm font-medium">
            {{ action.label }} → {{ action.target_label }}
          </div>
          <div class="text-xs text-muted">
            {{ action.description }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="node.children?.length" class="space-y-3">
      <div class="text-sm font-medium">Related workflow progress</div>
      <div class="space-y-3">
        <WorkflowProgressTree
          v-for="child in node.children"
          :key="`${child.entity}-${child.record_id}`"
          :node="child"
          :level="level + 1"
        />
      </div>
    </div>
  </div>
</template>
