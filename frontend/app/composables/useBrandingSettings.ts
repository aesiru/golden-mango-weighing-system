import type { ActionResponse } from "~/composables/useApiTypes"
import { useApiFetch } from "~/composables/useApiFetch"
import { useBootInfo } from "~/composables/useBootInfo"

interface BrandingSettings {
  organization_name: string
  description: string | null
  logo_url: string | null
}

export const useBrandingSettings = () => {
  const { apiFetch, baseURL } = useApiFetch()
  const { bootInfo } = useBootInfo()
  
  const branding = useState<BrandingSettings>("branding-settings", () => {
    // Initialize from boot info if available, otherwise use defaults
    if (bootInfo.value?.branding_settings) {
      return bootInfo.value.branding_settings
    }
    return {
      organization_name: "My App",
      description: "A modular FastAPI + Nuxt application",
      logo_url: null,
    }
  })

  const normalizeBranding = (data: BrandingSettings): BrandingSettings => {
    let logoUrl = data.logo_url
    if (logoUrl && logoUrl.startsWith('/')) {
      // logo_url is root-relative (e.g. /uploads/...). Prefix with API origin
      // so it resolves correctly when frontend and backend are on different ports.
      try {
        const apiOrigin = baseURL.startsWith('http')
          ? new URL(baseURL).origin
          : (typeof window !== 'undefined' ? window.location.origin : '')
        logoUrl = `${apiOrigin}${logoUrl}`
      } catch {
        // keep as-is
      }
    }
    return { ...data, logo_url: logoUrl }
  }

  const getBrandingSettings = async (): Promise<ActionResponse<BrandingSettings>> => {
    return apiFetch(`${baseURL}/settings/branding`)
  }

  const refreshBrandingSettings = async () => {
    const response = await getBrandingSettings()
    if (response.status === "success" && response.data) {
      branding.value = normalizeBranding(response.data)
    }
    return response
  }

  const updateBrandingSettings = async (
    payload: Pick<BrandingSettings, "organization_name" | "description">
  ): Promise<ActionResponse<BrandingSettings>> => {
    const response = await apiFetch<ActionResponse<BrandingSettings>>(`${baseURL}/settings/branding`, {
      method: "PUT",
      body: payload,
    })
    if (response.status === "success" && response.data) {
      branding.value = normalizeBranding(response.data)
    }
    return response
  }

  const uploadBrandingLogo = async (file: File): Promise<ActionResponse<BrandingSettings>> => {
    const form = new FormData()
    form.append("file", file)
    const response = await apiFetch<ActionResponse<BrandingSettings>>(`${baseURL}/settings/branding/logo`, {
      method: "POST",
      body: form,
    })
    if (response.status === "success" && response.data) {
      branding.value = normalizeBranding(response.data)
    }
    return response
  }

  const deleteBrandingLogo = async (): Promise<ActionResponse<BrandingSettings>> => {
    const response = await apiFetch<ActionResponse<BrandingSettings>>(`${baseURL}/settings/branding/logo`, {
      method: "DELETE",
    })
    if (response.status === "success" && response.data) {
      branding.value = normalizeBranding(response.data)
    }
    return response
  }

  // Initialize branding from boot info when it loads
  watch(() => bootInfo.value?.branding_settings, (newBranding) => {
    if (newBranding) {
      branding.value = normalizeBranding(newBranding)
    }
  }, { immediate: true })

  return {
    branding,
    getBrandingSettings,
    refreshBrandingSettings,
    updateBrandingSettings,
    uploadBrandingLogo,
    deleteBrandingLogo,
  }
}
