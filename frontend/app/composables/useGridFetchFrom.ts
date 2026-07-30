/**
 * useGridFetchFrom Composable
 * ============================
 * Implements declarative `fetch_from` for inline data grids (ChildDataGrid,
 * RelatedDataGrid). When a source link cell value changes in a row, the
 * composable fetches the remote field(s) from the linked entity and patches
 * them directly into that row.
 *
 * fetch_from format: "source_link_field.remote_field_name"
 * Example:   "item.uom"
 *   → when row.item changes
 *   → GET /api/entity/item/fetch_from/{id}?fields=uom
 *   → row.unit_of_measure = response.data.uom
 *
 * Usage:
 *   const gridFetchFrom = useGridFetchFrom(childMetaRef, gridDataRef)
 *   // In onCellValueChanged:
 *   await gridFetchFrom.applyForRow(rowId, changedFieldName, newValue)
 */
import type { EntityMeta, FieldMeta } from '~/composables/useApiTypes'

interface FetchFromRule {
  sourceField: string
  linkEntity: string
  targets: Array<{ targetField: string; remoteField: string }>
}

interface ApplyResult {
  applied: boolean
  patches: Record<string, any>
  linkTitles: Record<string, string>
}

export function useGridFetchFrom(
  entityMeta: Ref<EntityMeta | null>,
  gridData: Ref<Record<string, any>[]>,
) {
  const { getFetchFromFields } = useApi()

  /**
   * Build rules index: sourceField → FetchFromRule.
   * Mirrors the same logic as useFetchFrom but in computed form so it
   * automatically reacts when entityMeta changes (e.g. hot-reload).
   */
  const fetchFromRules = computed<Record<string, FetchFromRule>>(() => {
    const fields = entityMeta.value?.fields ?? []
    const rules: Record<string, FetchFromRule> = {}

    for (const field of fields) {
      if (!field.fetch_from) continue

      const parts = field.fetch_from.split('.')
      if (parts.length !== 2) continue

      const [sourceField, remoteField] = parts as [string, string]

      if (!rules[sourceField]) {
        const sourceMeta = fields.find((f: FieldMeta) => f.name === sourceField)
        const linkEntity = sourceMeta?.link_entity
        if (!linkEntity) continue
        rules[sourceField] = { sourceField, linkEntity, targets: [] }
      }

      rules[sourceField]!.targets.push({ targetField: field.name, remoteField })
    }

    return rules
  })

  /** Short-lived dedup cache — prevents duplicate in-flight requests */
  const fetchCache = new Map<
    string,
    Promise<{ data: Record<string, any>; linkTitles: Record<string, string> } | null>
  >()

  function fetchRemoteFields(
    entity: string,
    id: string,
    fields: string[],
  ): Promise<{ data: Record<string, any>; linkTitles: Record<string, string> } | null> {
    const key = `${entity}:${id}:${[...fields].sort().join(',')}`
    if (fetchCache.has(key)) return fetchCache.get(key)!

    const promise = getFetchFromFields(entity, id, fields)
      .then(res =>
        res?.status === 'success'
          ? {
              data: res.data ?? {},
              linkTitles: (res as any)?._link_titles ?? {},
            }
          : null,
      )
      .catch(() => null)

    fetchCache.set(key, promise)
    setTimeout(() => fetchCache.delete(key), 5_000)
    return promise
  }

  /**
   * Called after a cell value changes.
   * Finds the affected row, checks if the changed field is a fetch_from source,
   * fetches the remote values and patches the row in-place.
   *
   * Returns the patches applied so the caller can react (e.g. mark dirty).
   */
  async function applyForRow(
    rowId: string,
    changedField: string,
    newValue: any,
  ): Promise<ApplyResult> {
    const rule = fetchFromRules.value[changedField]
    if (!rule) return { applied: false, patches: {}, linkTitles: {} }

    const row = gridData.value.find(r => String(r.id) === String(rowId))
    if (!row) return { applied: false, patches: {}, linkTitles: {} }

    const patches: Record<string, any> = {}
    const linkTitles: Record<string, string> = {}

    if (!newValue) {
      for (const { targetField } of rule.targets) {
        row[targetField] = null
        patches[targetField] = null
      }
      return { applied: true, patches, linkTitles }
    }

    const remoteFields = rule.targets.map(t => t.remoteField)
    const res = await fetchRemoteFields(rule.linkEntity, String(newValue), remoteFields)

    if (!res) return { applied: false, patches: {}, linkTitles: {} }

    Object.assign(linkTitles, res.linkTitles || {})

    for (const { targetField, remoteField } of rule.targets) {
      if (remoteField in res.data) {
        row[targetField] = res.data[remoteField] ?? null
        patches[targetField] = res.data[remoteField] ?? null
      }
    }

    return { applied: Object.keys(patches).length > 0, patches, linkTitles }
  }

  /**
   * Returns true if a given field name is a fetch_from source field
   * (i.e. changing it should trigger an autofill).
   */
  function isFetchFromSource(fieldName: string): boolean {
    return fieldName in fetchFromRules.value
  }

  return {
    fetchFromRules,
    applyForRow,
    isFetchFromSource,
  }
}
