<script setup lang="ts">
definePageMeta({
  middleware: ["auth"],
});

const authStore = useAuthStore();
if (!authStore.isSuperuser) {
  throw createError({ statusCode: 403 });
}

import { useBrandingSettings } from "~/composables/useBrandingSettings";

const toast = useToast();
const brandingLoading = ref(false);
const brandingSaving = ref(false);
const logoUploading = ref(false);
const logoDeleting = ref(false);
const logoUploadModel = ref<File | null>(null);

const {
  branding,
  refreshBrandingSettings,
  updateBrandingSettings,
  uploadBrandingLogo,
  deleteBrandingLogo,
} = useBrandingSettings();

const brandingForm = reactive({
  organization_name: "",
  description: "",
});

type ThemeConfig = {
  colors: {
    primary: string;
    neutral: string;
  };
};

// Theme editor
const appConfig = useAppConfig();
const colorMode = useColorMode();
const themeConfig = appConfig.ui as ThemeConfig;

const primaryColors = [
  "red",
  "orange",
  "amber",
  "yellow",
  "lime",
  "green",
  "emerald",
  "teal",
  "cyan",
  "sky",
  "blue",
  "indigo",
  "violet",
  "purple",
  "fuchsia",
  "pink",
  "rose",
];
const neutralColors = ["slate", "gray", "zinc", "neutral", "stone"];

const colorSwatches: Record<string, string> = {
  red: "#ef4444",
  orange: "#f97316",
  amber: "#f59e0b",
  yellow: "#eab308",
  lime: "#84cc16",
  green: "#22c55e",
  emerald: "#10b981",
  teal: "#14b8a6",
  cyan: "#06b6d4",
  sky: "#0ea5e9",
  blue: "#3b82f6",
  indigo: "#6366f1",
  violet: "#8b5cf6",
  purple: "#a855f7",
  fuchsia: "#d946ef",
  pink: "#ec4899",
  rose: "#f43f5e",
  slate: "#64748b",
  gray: "#6b7280",
  zinc: "#71717a",
  neutral: "#737373",
  stone: "#78716c",
};

const currentPrimary = ref(themeConfig.colors.primary || "green");
const currentNeutral = ref(themeConfig.colors.neutral || "slate");
const isDark = ref(colorMode.preference === "dark");

const logoUrl = computed(() => branding.value.logo_url || null);

const syncBrandingForm = () => {
  brandingForm.organization_name = branding.value.organization_name || "";
  brandingForm.description = branding.value.description || "";
};

const loadBrandingSettings = async () => {
  brandingLoading.value = true;
  try {
    const response = await refreshBrandingSettings();
    if (response.status !== "success") {
      throw new Error(response.message || "Failed to load branding settings");
    }
    syncBrandingForm();
  } catch (error: any) {
    toast.add({
      title: "Failed to load branding",
      description: error?.message || "Please try again",
      color: "error",
    });
  } finally {
    brandingLoading.value = false;
  }
};

onMounted(() => {
  const saved = localStorage.getItem("app:theme");
  if (saved) {
    try {
      const theme = JSON.parse(saved);
      if (theme.primary) {
        currentPrimary.value = theme.primary;
        themeConfig.colors.primary = theme.primary;
      }
      if (theme.neutral) {
        currentNeutral.value = theme.neutral;
        themeConfig.colors.neutral = theme.neutral;
      }
      if (theme.dark !== undefined) {
        isDark.value = theme.dark;
        colorMode.preference = theme.dark ? "dark" : "light";
      }
    } catch {}
  }

  loadBrandingSettings();
});

const onLogoSelected = async (value: File | File[] | null | undefined) => {
  const file = Array.isArray(value) ? value[0] : value;
  if (!file) return;

  logoUploading.value = true;
  try {
    const response = await uploadBrandingLogo(file);
    if (response.status !== "success") {
      throw new Error(response.message || "Failed to upload logo");
    }
    toast.add({
      title: "Logo Uploaded",
      description: "Organization logo updated successfully",
      color: "success",
    });
  } catch (error: any) {
    toast.add({
      title: "Failed to upload logo",
      description: error?.message || "Please try again",
      color: "error",
    });
  } finally {
    logoUploadModel.value = null;
    logoUploading.value = false;
  }
};

const removeLogo = async () => {
  logoDeleting.value = true;
  try {
    const response = await deleteBrandingLogo();
    if (response.status !== "success") {
      throw new Error(response.message || "Failed to remove logo");
    }
    toast.add({
      title: "Logo Removed",
      description: "Organization logo removed successfully",
      color: "success",
    });
  } catch (error: any) {
    toast.add({
      title: "Failed to remove logo",
      description: error?.message || "Please try again",
      color: "error",
    });
  } finally {
    logoDeleting.value = false;
  }
};

const applyBrandingAndTheme = async () => {
  brandingSaving.value = true;
  try {
    const response = await updateBrandingSettings({
      organization_name: brandingForm.organization_name,
      description: brandingForm.description,
    });
    if (response.status !== "success") {
      throw new Error(response.message || "Failed to save branding settings");
    }

    themeConfig.colors.primary = currentPrimary.value;
    themeConfig.colors.neutral = currentNeutral.value;
    colorMode.preference = isDark.value ? "dark" : "light";
    localStorage.setItem(
      "app:theme",
      JSON.stringify({
        primary: currentPrimary.value,
        neutral: currentNeutral.value,
        dark: isDark.value,
      }),
    );

    syncBrandingForm();
    toast.add({
      title: "Settings Updated",
      description: "Branding and theme changes have been applied",
      color: "success",
    });
  } catch (error: any) {
    toast.add({
      title: "Failed to apply settings",
      description: error?.message || "Please try again",
      color: "error",
    });
  } finally {
    brandingSaving.value = false;
  }
};

const resetTheme = () => {
  currentPrimary.value = "green";
  currentNeutral.value = "slate";
  isDark.value = false;
  themeConfig.colors.primary = "green";
  themeConfig.colors.neutral = "slate";
  colorMode.preference = "light";
  localStorage.removeItem("app:theme");
  toast.add({
    title: "Theme Reset",
    description: "Restored default theme",
    color: "success",
  });
};
</script>

<template>
  <div class="p-6 space-y-6">
    <div
      class="flex flex-col gap-2 md:flex-row md:items-end md:justify-between"
    >
      <div>
        <h1 class="text-2xl md:text-3xl font-bold">Settings</h1>
        <p class="text-muted-foreground">
          Manage branding, visual theme, and local application behavior.
        </p>
      </div>

      <UBadge color="neutral" variant="subtle" class="w-fit">
        Superuser only
      </UBadge>
    </div>

    <div class="space-y-6">
      <UCard variant="subtle">
        <template #header>
          <div class="flex items-start justify-between gap-3 flex-wrap">
            <div>
              <h2 class="text-lg font-semibold">Branding + Theme</h2>
              <p class="text-sm text-muted-foreground">
                Update organization identity and apply local appearance settings
                together.
              </p>
            </div>

            <div class="flex gap-2">
              <UButton variant="outline" @click="syncBrandingForm">
                Reset Branding
              </UButton>
              <UButton variant="outline" @click="resetTheme">
                Reset Theme
              </UButton>
              <UButton :loading="brandingSaving" @click="applyBrandingAndTheme">
                Apply Changes
              </UButton>
            </div>
          </div>
        </template>

        <div class="space-y-6">
          <UAlert
            v-if="brandingLoading"
            color="neutral"
            variant="subtle"
            icon="i-lucide-loader-circle"
            title="Loading branding settings"
            description="Please wait while the current branding is fetched."
          />

          <div
            class="grid grid-cols-1 xl:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.8fr)] gap-6 items-start"
          >
            <div class="space-y-6">
              <UCard variant="outline">
                <template #header>
                  <div>
                    <h3 class="font-semibold">Organization Branding</h3>
                    <p class="text-sm text-muted-foreground">
                      Control the name, description, and logo shown in the
                      sidebar.
                    </p>
                  </div>
                </template>

                <UForm :state="brandingForm" class="space-y-4">
                  <UFormField label="Organization Name" required>
                    <UInput
                      v-model="brandingForm.organization_name"
                      placeholder="Enter organization name"
                      class="w-full"
                    />
                  </UFormField>

                  <UFormField label="Description">
                    <UTextarea
                      v-model="brandingForm.description"
                      :rows="4"
                      placeholder="Describe your organization or system"
                      class="w-full"
                    />
                  </UFormField>
                </UForm>
              </UCard>

              <UCard variant="outline">
                <template #header>
                  <div>
                    <h3 class="font-semibold">Theme</h3>
                    <p class="text-sm text-muted-foreground">
                      Choose your local primary and neutral colors.
                    </p>
                  </div>
                </template>

                <div class="space-y-6">
                  <div class="space-y-2">
                    <label class="text-sm font-medium block"
                      >Primary Color</label
                    >
                    <div class="flex flex-wrap gap-3">
                      <button
                        v-for="color in primaryColors"
                        :key="color"
                        class="w-10 h-10 rounded-full border-2 transition-all hover:scale-110"
                        :class="[
                          currentPrimary === color
                            ? 'border-black dark:border-white ring-2 ring-offset-2 ring-current scale-110'
                            : 'border-transparent',
                        ]"
                        :style="{ backgroundColor: colorSwatches[color] }"
                        :title="color"
                        @click="currentPrimary = color"
                      />
                    </div>
                  </div>

                  <div class="space-y-2">
                    <label class="text-sm font-medium block"
                      >Neutral Color</label
                    >
                    <div class="flex flex-wrap gap-3">
                      <button
                        v-for="color in neutralColors"
                        :key="color"
                        class="w-10 h-10 rounded-full border-2 transition-all hover:scale-110"
                        :class="[
                          currentNeutral === color
                            ? 'border-black dark:border-white ring-2 ring-offset-2 ring-current scale-110'
                            : 'border-transparent',
                        ]"
                        :style="{ backgroundColor: colorSwatches[color] }"
                        :title="color"
                        @click="currentNeutral = color"
                      />
                    </div>
                  </div>

                  <div
                    class="flex items-center gap-3 rounded-lg border border-accented p-3"
                  >
                    <UCheckbox v-model="isDark" />
                    <span class="text-sm font-medium">Enable dark mode</span>
                  </div>

                  <div class="rounded-lg border border-accented p-4 space-y-3">
                    <div class="text-sm font-medium">Theme Preview</div>
                    <div class="flex flex-wrap items-center gap-3">
                      <UButton>Primary</UButton>
                      <UButton variant="outline">Outline</UButton>
                      <UBadge>Badge</UBadge>
                      <UBadge variant="subtle">Subtle</UBadge>
                    </div>
                  </div>
                </div>
              </UCard>
            </div>

            <div class="space-y-6">
              <UCard variant="outline">
                <template #header>
                  <div>
                    <h3 class="font-semibold">Sidebar Preview</h3>
                    <p class="text-sm text-muted-foreground">
                      See how the saved branding appears in the sidebar.
                    </p>
                  </div>
                </template>

                <div
                  class="rounded-lg border border-accented bg-card p-4 flex items-center gap-3"
                >
                  <img
                    v-if="logoUrl"
                    :src="logoUrl"
                    alt="Logo preview"
                    class="w-12 h-12 rounded-lg object-cover border border-accented shrink-0"
                  />
                  <div
                    v-else
                    class="w-12 h-12 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0"
                  >
                    <Icon name="i-lucide-building-2" class="w-6 h-6" />
                  </div>

                  <div class="min-w-0 overflow-hidden">
                    <div class="font-semibold truncate">
                      {{ brandingForm.organization_name || "ManGO" }}
                    </div>
                    <div
                      class="text-sm text-muted-foreground break-words line-clamp-2"
                    >
                      {{ brandingForm.description || "A modular application framework" }}
                    </div>
                  </div>
                </div>
              </UCard>

              <UCard variant="outline">
                <template #header>
                  <div>
                    <h3 class="font-semibold">Logo Upload</h3>
                    <p class="text-sm text-muted-foreground">
                      Upload a square logo image for best results.
                    </p>
                  </div>
                </template>

                <div class="space-y-4">
                  <UFileUpload
                    :key="logoUrl || 'branding-logo-upload'"
                    v-model="logoUploadModel"
                    accept="image/*"
                    icon="i-lucide-image-up"
                    label="Drop logo here or click to browse"
                    description="PNG, JPG, SVG, or WEBP"
                    :multiple="false"
                    :loading="logoUploading"
                    class="w-full"
                    @update:model-value="onLogoSelected"
                  />

                  <div class="flex gap-3">
                    <UButton
                      color="error"
                      variant="outline"
                      :disabled="!logoUrl"
                      :loading="logoDeleting"
                      @click="removeLogo"
                    >
                      Remove Logo
                    </UButton>
                  </div>
                </div>
              </UCard>
            </div>
          </div>
        </div>
      </UCard>
    </div>
  </div>
</template>
