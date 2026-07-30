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

const formData = ref<{
  from_state_id: string;
  action_id: string;
  to_state_id: string;
  allowed_roles: string[];
}>({
  from_state_id: "",
  action_id: "",
  to_state_id: "",
  allowed_roles: [],
});

const globalActions = ref<any[]>([]);
const allRoles = ref<any[]>([]);
const isLoading = ref(false);

const linkedStateOptions = computed(() => {
  if (!props.workflow?.state_links) return [];
  return props.workflow.state_links
    .filter((sl: any) => sl.state_id)
    .map((sl: any) => ({
      value: sl.state_id,
      label: sl.state_label,
    }));
});

const actionOptions = computed(() => {
  return globalActions.value
    .filter((a: any) => a.id)
    .map((a: any) => ({
      value: a.id,
      label: a.label,
    }));
});

const loadActions = async () => {
  try {
    const [actionsRes, rolesRes] = await Promise.all([
      api.getWorkflowActions(),
      api.getAdminRoles(),
    ]);
    if (actionsRes.status === "success") {
      globalActions.value = actionsRes.data || [];
    }
    if (rolesRes.status === "success") {
      allRoles.value = rolesRes.data || [];
    }
  } catch (err) {
    console.error(err);
  }
};

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      formData.value = {
        from_state_id: "",
        action_id: "",
        to_state_id: "",
        allowed_roles: [],
      };
      loadActions();
    }
  },
);

const handleSave = async () => {
  if (
    !formData.value.from_state_id ||
    !formData.value.action_id ||
    !formData.value.to_state_id ||
    !props.workflow
  )
    return;
  try {
    isLoading.value = true;
    const res = await api.addTransitionToWorkflow(
      props.workflow.id,
      formData.value,
    );
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
    title="Add Transition to Workflow"
    :ui="{ footer: 'justify-end' }"
    @update:open="(val) => (modalOpen = val)"
  >
    <template #body>
      <UForm :state="formData" class="space-y-4">
        <UFormField label="From State" required>
          <USelect
            v-model="formData.from_state_id"
            :items="linkedStateOptions"
            placeholder="Select state..."
          />
        </UFormField>

        <UFormField label="Action" required>
          <USelect
            v-model="formData.action_id"
            :items="actionOptions"
            placeholder="Select action..."
          />
        </UFormField>

        <UFormField label="To State" required>
          <USelect
            v-model="formData.to_state_id"
            :items="linkedStateOptions"
            placeholder="Select state..."
          />
        </UFormField>

        <UFormField label="Allowed Roles" hint="Leave empty to allow all roles">
          <div
            class="flex flex-wrap gap-2 p-2 border border-muted rounded-md min-h-[38px]"
          >
            <template v-for="role in allRoles" :key="role.id">
              <label class="flex items-center gap-1.5 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  :checked="
                    formData.allowed_roles.includes(role.name || role.id)
                  "
                  @change="
                    (e: Event) => {
                      const name = role.name || role.id;
                      const checked = (e.target as HTMLInputElement).checked;
                      if (checked) {
                        formData.allowed_roles.push(name);
                      } else {
                        formData.allowed_roles = formData.allowed_roles.filter(
                          (r: string) => r !== name,
                        );
                      }
                    }
                  "
                  class="rounded"
                />
                {{ role.name || role.id }}
              </label>
            </template>
            <span v-if="!allRoles.length" class="text-xs text-muted-foreground"
              >No roles found</span
            >
          </div>
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
        label="Add Transition"
        color="neutral"
        @click="handleSave"
        :loading="isLoading"
      />
    </template>
  </UModal>
</template>
