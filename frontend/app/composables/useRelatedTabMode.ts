import type { EntityMeta } from "~/composables/useApiTypes";

/**
 * Determines if a related tab should render as a header-detail table
 * instead of the standard related grid.
 * 
 * A related tab is header-detail if:
 * - The related entity metadata exists
 * - The related entity has children (is a header/parent entity)
 */
export function useRelatedTabMode() {
  function isHeaderDetailTab(relatedMeta: EntityMeta | null | undefined): boolean {
    if (!relatedMeta) return false;
    return Array.isArray(relatedMeta.children) && relatedMeta.children.length > 0;
  }

  return {
    isHeaderDetailTab,
  };
}
