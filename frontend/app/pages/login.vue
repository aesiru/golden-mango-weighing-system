<script setup lang="ts">
import { useBrandingSettings } from "~/composables/useBrandingSettings";

const { login } = useAuth();
const router = useRouter();
const { branding, refreshBrandingSettings } = useBrandingSettings();

const username = ref("");
const password = ref("");
const isLoading = ref(false);
const errorMessage = ref("");

const brandingTitle = computed(
  () => "ManGO",
);
const brandingLogoUrl = computed(() => "/mango_logo.jpg");

const handleLogin = async (user?: string, pass?: string) => {
  const loginUsername = user || username.value;
  const loginPassword = pass || password.value;

  if (!loginUsername || !loginPassword) {
    errorMessage.value = "Please enter username and password";
    return;
  }

  isLoading.value = true;
  errorMessage.value = "";

  try {
    const result = await login(loginUsername, loginPassword);
    if (result.success) {
      router.push("/");
    } else {
      errorMessage.value = result.message || "Login failed";
    }
  } catch (_error) {
    errorMessage.value = "An error occurred during login";
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  refreshBrandingSettings();
});

definePageMeta({
  title: "Login",
  layout: false,
});
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-background p-6">
    <div class="w-[420px] max-w-md p-8 border border-accented rounded-lg">
      <!-- Branding Header -->
      <div class="flex flex-col items-center mb-8">
        <img
          v-if="brandingLogoUrl"
          :src="brandingLogoUrl"
          alt="Organization logo"
          class="w-14 h-14 rounded-lg object-contain mb-3"
        />
        <div
          v-else
          class="w-14 h-14 flex items-center justify-center rounded-lg bg-primary/10 text-primary mb-3"
        >
          <svg
            class="w-8 h-8"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M9 11h6M9 15h6" />
          </svg>
        </div>
        <h2 class="text-2xl font-bold text-foreground">{{ brandingTitle }}</h2>
      </div>

      <form class="space-y-4" @submit.prevent="() => handleLogin()">
        <UFormField label="Username">
          <UInput
            v-model="username"
            type="text"
            placeholder="Enter your username"
            :disabled="isLoading"
            required
            class="w-full"
          />
        </UFormField>

        <UFormField label="Password">
          <UInput
            v-model="password"
            type="password"
            placeholder="Enter your password"
            :disabled="isLoading"
            required
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
          class="w-full"
        >
          Sign In
        </UButton>
      </form>
    </div>
  </div>
</template>
