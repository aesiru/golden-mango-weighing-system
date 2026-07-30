import type { FieldMeta } from '~/composables/useApiTypes'
import { timeAgo } from '~/utils/timeAgo'

/**
 * Format a raw cell value based on field metadata.
 */
export function formatCellValue(value: any, field: FieldMeta): string {
  if (value === null || value === undefined) return '-'
  if (field.field_type === 'boolean') return value ? 'Yes' : 'No'
  if (field.field_type === 'datetime' || field.field_type === 'date') {
    return new Date(value).toLocaleDateString()
  }
  return String(value)
}

/**
 * Resolve a cell's display value, handling _last_edited, link titles, and formatting.
 *
 * @param row        - The data row object
 * @param fieldName  - The field name (or '_last_edited' for relative time)
 * @param fields     - The entity's field metadata array
 */
export function resolveCellValue(
  row: any,
  fieldName: string,
  fields: FieldMeta[] | undefined,
): string {
  // Special "Last Edited" column
  if (fieldName === '_last_edited') {
    return timeAgo(row?.updated_at || row?.created_at)
  }

  const field = fields?.find((f) => f.name === fieldName)
  if (!field) return row?.[fieldName] != null ? String(row[fieldName]) : '-'

  // Link fields: resolve display name from _link_titles
  if (field.field_type === 'link' && field.link_entity && row?._link_titles) {
    const key = `${field.link_entity}::${row[fieldName]}`
    const label = row._link_titles[key]
    if (label) return label
  }

  return formatCellValue(row?.[fieldName], field)
}
