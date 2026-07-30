<script setup lang="ts">
const props = defineProps<{
  modelValue: boolean;
  workflow: any;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  refresh: [];
}>();

const api = useApi();
const toast = useToast();

const formData = ref<{ state_id: string; is_initial: boolean }>({
  state_id: "",
  is_initial: false,
});

const globalStates = ref<any[]>([]);
const isLoading = ref(false);

const availableStates = computed(() => {
  if (!props.workflow?.state_links) return globalStates.value;
  const linkedIds = new Set(
    props.workflow.state_links.map((sl: any) => sl.state_id),
  );
  return globalStates.value.filter((s: any) => !linkedIds.has(s.id));
});

const stateOptions = computed(() => {
  return availableStates.value
    .filter((s: any) => s.id)
    .map((s: any) => ({
      value: s.id,
      label: s.label,
    }));
});

const loadStates = async () => {
  try {
    const res = await api.getWorkflowStates();
    if (res.status === "success") {
      globalStates.value = [...(res.data || [])];
    }
  } catch (err) {
    console.error(err);
  }
};

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      formData.value = { state_id: "", is_initial: false };
      loadStates();
    }
  },
);

const handleSave = async () => {
  if (!formData.value.state_id || !props.workflow) return;
  try {
    isLoading.value = true;
    const res = await api.addStateToWorkflow(props.workflow.id, formData.value);
    if (res.status === "success") {
      toast.add({ title: res.message, color: "success" });
      emit("update:modelValue", false);
      emit("refresh");
    } else {
      toast.add({ title: res.message, color: "error" });
    }
  } catch (err: any) {
    toast.add({ title: err.message, color: "error" });
  } finally {
    isLoading.value = false;
  }
};

const modalOpen = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit("update:modelValue", v),
});
</script>

<template>
  <UModal
    :open="modalOpen"
    title="Add State to Workflow"
    :ui="{ footer: 'justify-end' }"
    @update:open="(val) => (modalOpen = val)"
  >
    <template #body>
      <UForm :state="formData" class="space-y-4">
        <UFormField label="State" required>
          <USelect
            v-model="formData.state_id"
            :items="stateOptions"
            placeholder="Select state..."
            class="w-full"
          />
        </UFormField>

        <UFormField label="Initial State">
          <UCheckbox
            v-model="formData.is_initial"
            label="Set as initial state"
          />
        </UFormField>
      </UForm>
    </template>

    <template #footer="{ close }">
      <UButton
        label="Cancel"
        color="neutral"
        variant="outline"
        @click="close"
        :disabled="isLoading"
      />
      <UButton
        label="Add State"
        color="neutral"
        @click="handleSave"
        :loading="isLoading"
      />
    </template>
  </UModal>
</template>
