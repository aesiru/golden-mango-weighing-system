/**
 * useSavedFilters - Persisted Filter Presets
 * ============================================
 * Stores per-entity named filter presets in localStorage.
 * Users can save, load, and delete filter configurations.
 */

const STORAGE_KEY_PREFIX = 'eam_filters_'

export interface FilterPreset {
  id: string
  name: string
  filters: Record<string, any>
  sortField?: string
  sortOrder?: 'asc' | 'desc'
  createdAt: string
}

export const useSavedFilters = (entityName: Ref<string> | string) => {
  const entity = typeof entityName === 'string' ? ref(entityName) : entityName

  const storageKey = computed(() => `${STORAGE_KEY_PREFIX}${entity.value}`)

  function loadAll(): FilterPreset[] {
    if (!import.meta.client) return []
    try {
      const raw = localStorage.getItem(storageKey.value)
      if (!raw) return []
      return JSON.parse(raw) as FilterPreset[]
    } catch {
      return []
    }
  }

  function saveAll(presets: FilterPreset[]) {
    if (!import.meta.client) return
    localStorage.setItem(storageKey.value, JSON.stringify(presets))
  }

  const presets = ref<FilterPreset[]>(loadAll())

  // Reload when entity changes
  watch(entity, () => {
    presets.value = loadAll()
  })

  function savePreset(name: string, filters: Record<string, any>, sortField?: string, sortOrder?: 'asc' | 'desc'): FilterPreset {
    const preset: FilterPreset = {
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      name,
      filters: { ...filters },
      sortField,
      sortOrder,
      createdAt: new Date().toISOString(),
    }
    presets.value.push(preset)
    saveAll(presets.value)
    return preset
  }

  function deletePreset(id: string) {
    presets.value = presets.value.filter(p => p.id !== id)
    saveAll(presets.value)
  }

  function updatePreset(id: string, updates: Partial<Pick<FilterPreset, 'name' | 'filters' | 'sortField' | 'sortOrder'>>) {
    const idx = presets.value.findIndex(p => p.id === id)
    if (idx >= 0 && presets.value[idx]) {
      Object.assign(presets.value[idx]!, updates)
      saveAll(presets.value)
    }
  }

  function getPreset(id: string): FilterPreset | undefined {
    return presets.value.find(p => p.id === id)
  }

  return { presets, savePreset, deletePreset, updatePreset, getPreset }
}
