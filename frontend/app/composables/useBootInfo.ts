import { useAuthStore, type User } from "~/stores/auth";
import type { MetaListItem } from "~/composables/useApiTypes";

export interface SidebarNavigationLeaf {
  label: string;
  icon: string;
  to: string;
  entity: string;
}

export interface SidebarNavigationGroupItem {
  type: "group";
  label: string;
  icon: string;
  children: SidebarNavigationLeaf[];
  defaultOpen?: boolean;
}

export interface SidebarNavigationEntityItem {
  type: "entity";
  label: string;
  icon: string;
  to: string;
  entity: string;
}

export interface SidebarNavigationModule {
  key: string;
  label: string;
  icon: string;
  items: Array<SidebarNavigationGroupItem | SidebarNavigationEntityItem>;
}

export interface BootInfo {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
  sidebar: {
    entities: MetaListItem[];
    navigation: SidebarNavigationModule[];
  };
  allowed_dashboards: Array<{
    key: string;
    label: string;
    description: string;
    icon: string;
    stats: Array<{
      title: string;
      icon: string;
      source: string;
      field: string;
    }>;
    charts: Array<{
      title: string;
      subtitle: string;
      badge_color: string;
      source: string;
      total_field: string;
      data_field: string;
      preferred_order?: string[];
      custom_data?: boolean;
    }>;
  }>;
  workflow_states: Array<{
    id: string;
    label: string;
    slug: string;
    color: string;
  }>;
  branding_settings: {
    organization_name: string;
    description: string | null;
    logo_url: string | null;
  };
}

export const useBootInfo = () => {
  const config = useRuntimeConfig();
  const baseURL = config.public.apiUrl;
  const authStore = useAuthStore();

  const bootInfo = ref<BootInfo | null>(null);
  const isLoaded = ref(false);

  const loadFromStorage = () => {
    if (typeof window === "undefined") return;

    const stored = localStorage.getItem("boot_info");
    if (stored) {
      try {
        bootInfo.value = JSON.parse(stored);
        isLoaded.value = true;
      } catch (error) {
        console.error("Failed to parse boot info from storage:", error);
        localStorage.removeItem("boot_info");
      }
    }
  };

  const saveToStorage = (info: BootInfo) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("boot_info", JSON.stringify(info));
    }
  };

  const clearStorage = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("boot_info");
    }
  };

  const boot = async (username: string, password: string) => {
    try {
      const formData = new FormData();
      formData.append("username", username);
      formData.append("password", password);

      const response = await $fetch<BootInfo>(`${baseURL}/auth/boot`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      bootInfo.value = response;
      saveToStorage(response);
      isLoaded.value = true;

      // Update auth store
      authStore.setAuth({
        token: response.access_token,
        refreshToken: response.refresh_token,
        user: response.user,
      });

      return { success: true, data: response };
    } catch (error: any) {
      return {
        success: false,
        message: error.data?.detail || "Boot failed",
      };
    }
  };

  const refresh = async () => {
    try {
      const response = await $fetch<{
        access_token: string;
        token_type: string;
      }>(`${baseURL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });

      authStore.setToken(response.access_token);
      return { success: true };
    } catch (error: any) {
      return {
        success: false,
        message: error.data?.detail || "Refresh failed",
      };
    }
  };

  const clear = () => {
    bootInfo.value = null;
    isLoaded.value = false;
    clearStorage();
  };

  // Initialize from storage on client side
  onMounted(() => {
    if (!isLoaded.value && authStore.isAuthenticated) {
      loadFromStorage();
    }
  });

  // Clear on logout
  watch(
    () => authStore.isAuthenticated,
    (isAuth) => {
      if (!isAuth) {
        clear();
      }
    },
  );

  return {
    bootInfo: readonly(bootInfo),
    isLoaded: readonly(isLoaded),
    boot,
    refresh,
    clear,
    loadFromStorage,
  };
};
