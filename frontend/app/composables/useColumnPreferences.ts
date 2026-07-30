/**
 * useColumnPreferences - Persisted Column Visibility
 * ====================================================
 * Stores per-entity column visibility preferences in localStorage.
 * Used by entity list views to let users choose which columns to show.
 */

const STORAGE_KEY_PREFIX = 'eam_columns_'

export interface ColumnPref {
  name: string
  visible: boolean
}

export const useColumnPreferences = (entityName: Ref<string> | string) => {
  const entity = typeof entityName === 'string' ? ref(entityName) : entityName

  const storageKey = computed(() => `${STORAGE_KEY_PREFIX}${entity.value}`)

  /**
   * Load saved column preferences from localStorage.
   * Returns null if no preferences saved (use defaults).
   */
  function load(): ColumnPref[] | null {
    if (!import.meta.client) return null
    try {
      const raw = localStorage.getItem(storageKey.value)
      if (!raw) return null
      return JSON.parse(raw) as ColumnPref[]
    } catch {
      return null
    }
  }

  /**
   * Save column preferences to localStorage.
   */
  function save(prefs: ColumnPref[]) {
    if (!import.meta.client) return
    localStorage.setItem(storageKey.value, JSON.stringify(prefs))
  }

  /**
   * Clear saved preferences (revert to defaults).
   */
  function clear() {
    if (!import.meta.client) return
    localStorage.removeItem(storageKey.value)
  }

  /**
   * Given all available columns, return the visible subset
   * based on saved preferences (or all if no prefs saved).
   */
  function getVisibleColumns(allColumns: string[]): string[] {
    const prefs = load()
    if (!prefs) return allColumns

    const prefMap = new Map(prefs.map(p => [p.name, p.visible]))
    return allColumns.filter(col => prefMap.get(col) !== false)
  }

  /**
   * Toggle a column's visibility and persist.
   */
  function toggleColumn(allColumns: string[], columnName: string): ColumnPref[] {
    const prefs = load() || allColumns.map(name => ({ name, visible: true }))
    const idx = prefs.findIndex(p => p.name === columnName)
    if (idx >= 0 && prefs[idx]) {
      prefs[idx]!.visible = !prefs[idx]!.visible
    } else {
      prefs.push({ name: columnName, visible: false })
    }
    save(prefs)
    return prefs
  }

  return { load, save, clear, getVisibleColumns, toggleColumn }
}
