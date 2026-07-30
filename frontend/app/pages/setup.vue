<script setup lang="ts">
definePageMeta({
  title: "Setup",
  layout: false,
});

const config = useRuntimeConfig();
const baseURL = config.public.apiUrl as string;
const router = useRouter();

const form = reactive({
  full_name: "",
  email: "",
  username: "",
  password: "",
  confirm_password: "",
});

const isLoading = ref(false);
const errorMessage = ref("");
const isComplete = ref(false);

const passwordMismatch = computed(
  () =>
    form.confirm_password.length > 0 && form.password !== form.confirm_password,
);

const isValid = computed(() => {
  return (
    form.full_name.trim().length > 0 &&
    form.email.trim().length > 0 &&
    form.username.trim().length >= 3 &&
    form.password.length >= 6 &&
    form.password === form.confirm_password
  );
});

const handleSetup = async () => {
  if (!isValid.value) return;

  isLoading.value = true;
  errorMessage.value = "";

  try {
    await $fetch(`${baseURL}/setup/create-admin`, {
      method: "POST",
      body: {
        username: form.username,
        email: form.email,
        full_name: form.full_name,
        password: form.password,
      },
    });
    isComplete.value = true;
  } catch (error: any) {
    errorMessage.value =
      error.data?.detail ||
      error.data?.message ||
      "Setup failed. Please try again.";
  } finally {
    isLoading.value = false;
  }
};

const goToLogin = () => {
  router.push("/login");
};
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-background p-6">
    <div class="w-[480px] max-w-md p-8 border border-accented rounded-lg">
      <!-- Setup Complete State -->
      <template v-if="isComplete">
        <div class="text-center space-y-4">
          <div class="flex justify-center">
            <UIcon
              name="i-lucide-circle-check"
              class="text-5xl text-green-500"
            />
          </div>
          <h2 class="text-2xl font-bold text-foreground">Setup Complete</h2>
          <p class="text-muted-foreground">
            Your administrator account has been created. You can now log in.
          </p>
          <UButton block size="lg" class="w-full mt-4" @click="goToLogin">
            Go to Login
          </UButton>
        </div>
      </template>

      <!-- Setup Form -->
      <template v-else>
        <div class="text-center mb-6">
          <div class="flex justify-center mb-3">
            <UIcon name="i-lucide-settings" class="text-4xl text-primary" />
          </div>
          <h2 class="text-2xl font-bold text-foreground">Welcome</h2>
          <p class="text-sm text-muted-foreground mt-1">
            Create your administrator account to get started.
          </p>
        </div>

        <form class="space-y-4" @submit.prevent="handleSetup">
          <UFormField label="Full Name" required>
            <UInput
              v-model="form.full_name"
              placeholder="John Doe"
              :disabled="isLoading"
              class="w-full"
            />
          </UFormField>

          <UFormField label="Email" required>
            <UInput
              v-model="form.email"
              type="email"
              placeholder="admin@company.com"
              :disabled="isLoading"
              class="w-full"
            />
          </UFormField>

          <UFormField label="Username" required hint="Min 3 characters">
            <UInput
              v-model="form.username"
              placeholder="admin"
              :disabled="isLoading"
              class="w-full"
            />
          </UFormField>

          <UFormField label="Password" required hint="Min 6 characters">
            <UInput
              v-model="form.password"
              type="password"
              placeholder="Enter a strong password"
              :disabled="isLoading"
              class="w-full"
            />
          </UFormField>

          <UFormField
            label="Confirm Password"
            required
            :error="passwordMismatch ? 'Passwords do not match' : undefined"
          >
            <UInput
              v-model="form.confirm_password"
              type="password"
              placeholder="Re-enter your password"
              :disabled="isLoading"
              class="w-full"
            />
          </UFormField>

          <UAlert
            v-if="errorMessage"
            color="error"
            variant="subtle"
            :description="errorMessage"
          />

          <UButton
            type="submit"
            block
            size="lg"
            :loading="isLoading"
            :disabled="!isValid"
            class="w-full"
          >
            Create Administrator Account
          </UButton>
        </form>
      </template>
    </div>
  </div>
</template>
