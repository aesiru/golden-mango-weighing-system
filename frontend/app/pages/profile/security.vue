<script setup lang="ts">
import * as z from "zod";
import type { FormSubmitEvent } from "@nuxt/ui";

const { apiFetch, baseURL } = useApiFetch();
const toast = useToast();

const passwordSchema = z
  .object({
    current_password: z
      .string()
      .min(6, "Current password must be at least 6 characters"),
    new_password: z
      .string()
      .min(6, "New password must be at least 6 characters"),
    confirm_password: z
      .string()
      .min(6, "Confirm password must be at least 6 characters"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match",
  });

type PasswordSchema = z.output<typeof passwordSchema>;

const passwordForm = reactive<Partial<PasswordSchema>>({
  current_password: "",
  new_password: "",
  confirm_password: "",
});

const saving = ref(false);

const updatePassword = async (event: FormSubmitEvent<PasswordSchema>) => {
  saving.value = true;

  try {
    const response = await apiFetch<{ status: string; message: string }>(
      `${baseURL}/profile/password`,
      {
        method: "PUT",
        body: event.data,
      },
    );

    if (response.status !== "success") {
      throw new Error(response.message || "Failed to update password");
    }

    toast.add({
      title: "Password Updated",
      description:
        response.message || "Your password has been updated successfully",
      color: "success",
    });
    passwordForm.current_password = "";
    passwordForm.new_password = "";
    passwordForm.confirm_password = "";
  } catch (error: any) {
    toast.add({
      title: "Failed to update password",
      description: error?.message || "Please try again",
      color: "error",
    });
  } finally {
    saving.value = false;
  }
};

definePageMeta({ title: "Profile security" });
</script>

<template>
  <div class="space-y-6">
    <UPageCard
      title="Security"
      description="Update your password using your current credentials."
      variant="naked"
      orientation="horizontal"
      class="mb-4"
    />

    <UPageCard variant="subtle">
      <UForm
        :schema="passwordSchema"
        :state="passwordForm"
        class="space-y-4"
        @submit="updatePassword"
      >
        <UFormField
          name="current_password"
          label="Current Password"
          required
          class="flex items-start justify-between gap-4 max-sm:flex-col"
          :ui="{ container: 'w-full sm:max-w-md' }"
        >
          <UInput
            v-model="passwordForm.current_password"
            type="password"
            placeholder="Current password"
            class="w-full"
          />
        </UFormField>

        <UFormField
          name="new_password"
          label="New Password"
          required
          class="flex items-start justify-between gap-4 max-sm:flex-col"
          :ui="{ container: 'w-full sm:max-w-md' }"
        >
          <UInput
            v-model="passwordForm.new_password"
            type="password"
            placeholder="New password"
            class="w-full"
          />
        </UFormField>

        <UFormField
          name="confirm_password"
          label="Confirm Password"
          required
          class="flex items-start justify-between gap-4 max-sm:flex-col"
          :ui="{ container: 'w-full sm:max-w-md' }"
        >
          <UInput
            v-model="passwordForm.confirm_password"
            type="password"
            placeholder="Confirm new password"
            class="w-full"
          />
        </UFormField>

        <div class="flex justify-end">
          <UButton :loading="saving" type="submit"> Update Password </UButton>
        </div>
      </UForm>
    </UPageCard>
  </div>
</template>
