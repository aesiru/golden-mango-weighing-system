<script setup lang="ts">
import { z } from "zod";
import type { FormError, FormSubmitEvent } from "@nuxt/ui";

interface FieldMeta {
  name: string;
  label: string;
  field_type: string;
  required?: boolean;
  readonly?: boolean;
  default?: any;
  max_length?: number;
  link_entity?: string;
}

interface EntityMeta {
  entity: string;
  label: string;
  title_field: string;
  fields: FieldMeta[];
}

const props = defineProps<{
  modelValue: boolean;
  entityType: "users" | "role";
  editingItem: any;
  metadata: EntityMeta | null;
  roles?: any[];
  loading?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  save: [data: any];
}>();

const showPassword = ref(false);
const showConfirmPassword = ref(false);
const formRef = ref<any>(null);

// Create Zod schema for user validation
const userSchema = computed(() => {
  if (props.editingItem) {
    // Update mode - all fields optional except those being changed
    return z.object({
      username: z.string().min(1, "Username is required").optional(),
      email: z.string().email("Invalid email address").optional(),
      full_name: z.string().min(1, "Full name is required").optional(),
      first_name: z.string().optional(),
      last_name: z.string().optional(),
      contact_number: z.string().optional(),
      department: z.string().optional(),
      site: z.string().optional(),
      employee_id: z.string().optional(),
      password: z
        .string()
        .min(6, "Password must be at least 6 characters")
        .optional()
        .or(z.literal("")),
      password_confirmation: z.string().optional(),
      is_active: z.boolean().optional(),
      is_superuser: z.boolean().optional(),
      role_ids: z.array(z.string()).optional(),
    });
  } else {
    // Create mode - required fields
    return z.object({
      username: z.string().min(1, "Username is required"),
      email: z.string().email("Invalid email address"),
      full_name: z.string().min(1, "Full name is required"),
      first_name: z.string().optional(),
      last_name: z.string().optional(),
      contact_number: z.string().optional(),
      department: z.string().optional(),
      site: z.string().optional(),
      employee_id: z.string().optional(),
      password: z.string().min(6, "Password must be at least 6 characters"),
      password_confirmation: z.string().optional(),
      is_active: z.boolean().optional(),
      is_superuser: z.boolean().optional(),
      role_ids: z.array(z.string()).optional(),
    });
  }
});

type UserSchema = z.output<typeof userSchema.value>;

const state = reactive<Partial<UserSchema>>({
  username: "",
  email: "",
  full_name: "",
  first_name: "",
  last_name: "",
  contact_number: "",
  department: "",
  site: "",
  employee_id: "",
  password: "",
  password_confirmation: "",
  is_active: true,
  is_superuser: false,
  role_ids: [],
});

// Initialize state when modal opens or editing item changes
watch(
  () => [props.modelValue, props.editingItem],
  () => {
    if (props.modelValue) {
      if (props.editingItem) {
        // Editing mode
        state.username = props.editingItem.username;
        state.email = props.editingItem.email;
        state.full_name = props.editingItem.full_name;
        state.first_name = props.editingItem.first_name || "";
        state.last_name = props.editingItem.last_name || "";
        state.contact_number = props.editingItem.contact_number || "";
        state.department = props.editingItem.department || "";
        state.site = props.editingItem.site || "";
        state.employee_id = props.editingItem.employee_id || "";
        state.password = "";
        state.password_confirmation = "";
        state.is_active = props.editingItem.is_active;
        state.is_superuser = props.editingItem.is_superuser;
        state.role_ids = props.editingItem.roles?.map((r: any) => r.id) || [];
      } else {
        // Create mode - reset to defaults
        state.username = "";
        state.email = "";
        state.full_name = "";
        state.first_name = "";
        state.last_name = "";
        state.contact_number = "";
        state.department = "";
        state.site = "";
        state.employee_id = "";
        state.password = "";
        state.password_confirmation = "";
        state.is_active = true;
        state.is_superuser = false;
        state.role_ids = [];
      }
      // Clear form errors
      formRef.value?.clear();
    }
  },
  { immediate: true },
);

async function onSubmit(event: FormSubmitEvent<UserSchema>) {
  const dataToSave = { ...event.data };

  // Remove empty password fields for updates
  if (props.editingItem && !dataToSave.password) {
    delete dataToSave.password;
  }
  delete dataToSave.password_confirmation;

  emit("save", dataToSave);
}

const handleError = (errorResponse: any) => {
  // Handle backend validation errors by setting form errors
  if (errorResponse.data?.errors) {
    const errors: FormError[] = [];
    const backendErrors = errorResponse.data.errors;

    Object.keys(backendErrors).forEach((field) => {
      if (field !== "_form") {
        errors.push({
          name: field,
          message: backendErrors[field],
        });
      }
    });

    // Set errors on the form
    formRef.value?.setErrors(errors);
  }
};

// Expose handleError method to parent
defineExpose({
  handleError,
});
</script>

<template>
  <UModal
    :open="modelValue"
    :title="
      editingItem ? `Edit ${metadata?.label}` : `Create ${metadata?.label}`
    "
    description=""
    :ui="{ footer: 'justify-end' }"
    :aria-describedby="undefined"
    @update:open="emit('update:modelValue', $event)"
    class="w-[800px]"
  >
    <template #body>
      <UForm
        v-if="modelValue && metadata"
        ref="formRef"
        :schema="userSchema"
        :state="state"
        class="space-y-4"
        @submit="onSubmit"
      >
        <UFormField label="Username" name="username" required>
          <UInput
            v-model="state.username"
            placeholder="Enter username"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Email" name="email" required>
          <UInput
            v-model="state.email"
            type="email"
            placeholder="Enter email"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Full Name" name="full_name" required>
          <UInput
            v-model="state.full_name"
            placeholder="Enter full name"
            class="w-full"
          />
        </UFormField>

        <div class="grid grid-cols-2 gap-4">
          <UFormField label="First Name" name="first_name">
            <UInput
              v-model="state.first_name"
              placeholder="Enter first name"
              class="w-full"
            />
          </UFormField>

          <UFormField label="Last Name" name="last_name">
            <UInput
              v-model="state.last_name"
              placeholder="Enter last name"
              class="w-full"
            />
          </UFormField>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <UFormField label="Contact Number" name="contact_number">
            <UInput
              v-model="state.contact_number"
              placeholder="Enter contact number"
              class="w-full"
            />
          </UFormField>

          <UFormField label="Employee ID" name="employee_id">
            <UInput
              v-model="state.employee_id"
              placeholder="Enter employee ID"
              class="w-full"
            />
          </UFormField>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <UFormField label="Department" name="department">
            <UInput
              v-model="state.department"
              placeholder="Enter department"
              class="w-full"
            />
          </UFormField>

          <UFormField label="Site" name="site">
            <UInput
              v-model="state.site"
              placeholder="Enter site"
              class="w-full"
            />
          </UFormField>
        </div>

        <UFormField label="Password" name="password" :required="!editingItem">
          <UInput
            v-model="state.password"
            :type="showPassword ? 'text' : 'password'"
            :placeholder="
              editingItem
                ? 'Leave blank to keep current password'
                : 'Enter password'
            "
            class="w-full"
          >
            <template #trailing>
              <UButton
                color="neutral"
                variant="link"
                icon="i-heroicons-eye"
                size="xs"
                @click="showPassword = !showPassword"
              />
            </template>
          </UInput>
        </UFormField>

        <UFormField label="Active" name="is_active">
          <UCheckbox v-model="state.is_active" label="User is active" />
        </UFormField>

        <UFormField label="Superuser" name="is_superuser">
          <UCheckbox v-model="state.is_superuser" label="User is superuser" />
        </UFormField>

        <UFormField label="Roles" name="role_ids">
          <UInputMenu
            v-model="state.role_ids"
            :items="roles?.map((r) => ({ value: r.id, label: r.name })) || []"
            value-key="value"
            placeholder="Select roles"
            multiple
            class="w-full"
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
      />
      <UButton
        :loading="loading"
        :label="editingItem ? 'Update' : 'Create'"
        color="neutral"
        type="submit"
        @click="formRef?.submit()"
      />
    </template>
  </UModal>
</template>
