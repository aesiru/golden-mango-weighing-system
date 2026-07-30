import type { TreeItem } from '@nuxt/ui'
import type { EntityMeta, FieldMeta } from '~/composables/useApiTypes'

export const useTreeView = () => {
  const getParentFieldName = (entityMeta: EntityMeta | null): string | null => {
    if (!entityMeta?.fields) return null
    
    const parentField = entityMeta.fields.find((field: FieldMeta) => 
      field.name === 'parent' || 
      field.name === 'parent_id'
    )
    
    return parentField?.name || null
  }

  const hasParentField = (entityMeta: EntityMeta | null): boolean => {
    return getParentFieldName(entityMeta) !== null
  }

  const buildTreeStructure = (
    items: any[],
    titleField: string = 'name',
    parentField: string = 'parent_id',
  ): TreeItem[] => {
    const itemMap = new Map<string | number, any>()
    const roots: TreeItem[] = []

    items.forEach((item) => {
      itemMap.set(item.id, {
        ...item,
        children: [],
      })
    })

    items.forEach((item) => {
      const parentId = item[parentField]
      if (!parentId) {
        roots.push({
          label: item[titleField] || `Item ${item.id}`,
          id: item.id,
          defaultExpanded: false,
          children: itemMap.get(item.id)?.children || [],
          class: 'cursor-pointer',
        })
      } else {
        const parent = itemMap.get(parentId)
        if (parent) {
          if (!parent.children) parent.children = []
          parent.children.push({
            label: item[titleField] || `Item ${item.id}`,
            id: item.id,
            defaultExpanded: false,
            children: itemMap.get(item.id)?.children || [],
            class: 'cursor-pointer',
          })
        }
      }
    })

    return buildTreeItems(roots, itemMap)
  }

  const buildTreeItems = (roots: any[], itemMap: Map<string | number, any>): TreeItem[] => {
    return roots.map((root) => ({
      label: root.label,
      id: root.id,
      defaultExpanded: root.defaultExpanded,
      children: root.children?.length > 0 ? buildTreeItems(root.children, itemMap) : undefined,
      class: root.class,
    }))
  }

  return {
    hasParentField,
    getParentFieldName,
    buildTreeStructure,
  }
}
