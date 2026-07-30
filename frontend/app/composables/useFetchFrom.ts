/**
 * useFetchFrom Composable
 * =======================
 * Implements the declarative `fetch_from` metadata attribute.
 *
 * When a source link field changes, this composable calls the dedicated
 * GET /api/entity/{entity}/fetch_from/{id}?fields=a,b,c endpoint which
 * returns ONLY the required fields — no full document fetch needed.
 *
 * fetch_from format: "source_link_field.remote_field_name"
 * Example: "property.unit_of_measure"
 *   → watch formData.property
 *   → GET /api/entity/property/fetch_from/{id}?fields=unit_of_measure
 *   → formData.unit_of_measure = response.data.unit_of_measure
 */
import type { EntityMeta } from '~/composables/useApiTypes'

export function useFetchFrom(
  entityMeta: Ref<EntityMeta | null>,
  formData: Ref<Record<string, any>>,
  opts?: {
    setLoading?: (fieldName: string, isLoading: boolean) => void
    setLinkTitle?: (linkEntity: string, id: string, title: string) => void
    enabled?: Ref<boolean> | ComputedRef<boolean>
  },
) {
  const { getFetchFromFields } = useApi()

  const debug = (..._args: any[]) => {}

  const setLoading = (fieldName: string, isLoading: boolean) => {
    opts?.setLoading?.(fieldName, isLoading)
  }

  const setLinkTitle = (linkEntity: string, id: string, title: string) => {
    opts?.setLinkTitle?.(linkEntity, id, title)
  }

  const isEnabled = computed(() => opts?.enabled?.value ?? true)

  /**
   * Build a map of: sourceField → { linkEntity, targets: [{ targetField, remoteField }] }
   * from all fields that have a fetch_from attribute.
   */
  const fetchFromRules = computed(() => {
    const fields = entityMeta.value?.fields || []
    const rules: Record<string, { linkEntity: string; targets: Array<{ targetField: string; remoteField: string }> }> = {}

    for (const field of fields) {
      if (!field.fetch_from) continue

      const parts = field.fetch_from.split('.')
      if (parts.length !== 2) continue

      const [sourceField, remoteField] = parts as [string, string]

      if (!rules[sourceField]) {
        // Resolve link_entity for this source field
        const sourceMeta = fields.find(f => f.name === sourceField)
        const linkEntity = sourceMeta?.link_entity
        if (!linkEntity) continue
        rules[sourceField] = { linkEntity, targets: [] }
      }

      rules[sourceField].targets.push({ targetField: field.name, remoteField })
    }

    debug('rules computed', { entity: entityMeta.value?.name, rules })
    return rules
  })

  /**
   * Short-lived per-source cache so rapid consecutive changes don't fire
   * duplicate requests while the first one is still in-flight.
   */
  const fetchCache = new Map<string, Promise<{ data: Record<string, any>; _link_titles: Record<string, string> } | null>>()

  const fetchFields = (
    entity: string,
    id: string,
    fields: string[],
  ) => {
    const cacheKey = `${entity}:${id}:${fields.sort().join(',')}`
    if (fetchCache.has(cacheKey)) return fetchCache.get(cacheKey)!

    debug('fetch_from API call', { entity, id, fields })

    const promise = getFetchFromFields(entity, id, fields)
      .then(res => {
        if (res?.status === 'success') {
          return { data: res.data || {}, _link_titles: res._link_titles || {} }
        }
        return null
      })
      .catch(err => {
        debug('fetch_from error', { entity, id, err })
        return null
      })

    fetchCache.set(cacheKey, promise)
    setTimeout(() => fetchCache.delete(cacheKey), 5000)
    return promise
  }

  /**
   * Apply fetch_from rules when a source field changes.
   */
  const applyFetchFrom = async (sourceField: string, newValue: any) => {
    const rule = fetchFromRules.value[sourceField]
    if (!rule) return

    const { linkEntity, targets } = rule

    debug('apply', { entity: entityMeta.value?.name, sourceField, newValue, targets })

    for (const { targetField } of targets) setLoading(targetField, true)

    try {
      if (!newValue) {
        for (const { targetField } of targets) {
          debug('clear target', { targetField })
          formData.value[targetField] = null
        }
        return
      }

      // Only request the specific remote fields we need
      const remoteFields = targets.map(t => t.remoteField)
      const result = await fetchFields(linkEntity, String(newValue), remoteFields)

      if (!result) {
        debug('skip: no result from fetch_from API', { linkEntity, id: String(newValue) })
        return
      }

      // Push display titles into the link titles cache
      for (const [key, title] of Object.entries(result._link_titles)) {
        if (key.includes('::')) {
          const sep = key.indexOf('::')
          const entity = key.slice(0, sep)
          const id = key.slice(sep + 2)
          if (entity && id) setLinkTitle(entity, id, title)
        }
      }

      for (const { targetField, remoteField } of targets) {
        const value = result.data[remoteField]
        if (value === undefined) {
          debug('skip: remote field missing', { targetField, remoteField })
          continue
        }
        debug('set target', { targetField, value })
        formData.value[targetField] = value ?? null
      }
    } finally {
      for (const { targetField } of targets) setLoading(targetField, false)
    }
  }

  /**
   * Set up watchers for all source fields that have fetch_from rules.
   * Watchers are recreated whenever entityMeta changes.
   */
  const stopHandles: (() => void)[] = []

  const setupWatchers = () => {
    stopHandles.forEach(stop => stop())
    stopHandles.length = 0

    const rules = fetchFromRules.value
    debug('setup watchers', { entity: entityMeta.value?.name, sourceFields: Object.keys(rules) })

    for (const sourceField of Object.keys(rules)) {
      const stop = watch(
        () => formData.value[sourceField],
        (newVal, oldVal) => {
          debug('watch fired', { sourceField, oldVal, newVal })
          if (!isEnabled.value) return
          if (newVal === oldVal) return
          applyFetchFrom(sourceField, newVal)
        },
      )
      stopHandles.push(stop)
    }
  }

  watch(
    () => entityMeta.value?.name,
    () => setupWatchers(),
    { immediate: true },
  )

  watch(
    isEnabled,
    () => {
      if (!isEnabled.value) return
      setupWatchers()
    },
  )

  onUnmounted(() => {
    stopHandles.forEach(stop => stop())
  })

  return {
    fetchFromRules,
    applyFetchFrom,
  }
}
