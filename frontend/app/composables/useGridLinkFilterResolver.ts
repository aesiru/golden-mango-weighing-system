import type { EntityMeta, FieldMeta } from "~/composables/useApiTypes";

type LinkFilterDefinition = Record<string, any>;

interface GridLinkFilterResolverOptions {
  parentFormData?: Ref<Record<string, any> | undefined>;
  gridRows?: Ref<Record<string, any>[]>;
}

function readNestedValue(source: any, pathParts: string[]): any {
  let current = source;
  for (const part of pathParts) {
    if (current == null) return undefined;
    current = current[part];
  }
  return current;
}

export function useGridLinkFilterResolver(
  entityMeta: Ref<EntityMeta | null>,
  options: GridLinkFilterResolverOptions,
) {
  const { getFetchFromFields } = useApi();
  const remoteValueCache = new Map<string, Promise<any>>();

  function getFieldMeta(fieldName: string): FieldMeta | undefined {
    return entityMeta.value?.fields?.find((field) => field.name === fieldName);
  }

  function getEffectiveRowData(
    rowData?: Record<string, any>,
  ): Record<string, any> | undefined {
    const rowId = rowData?.id;
    if (!rowId || !options.gridRows?.value?.length) return rowData;

    const liveRow = options.gridRows.value.find(
      (row) => String(row.id) === String(rowId),
    );
    if (!liveRow || liveRow === rowData) return rowData;
    return liveRow;
  }

  async function fetchRemoteFilterValue(
    sourceField: string,
    sourceValue: any,
    remoteField: string,
  ): Promise<any> {
    const sourceMeta = getFieldMeta(sourceField);
    const linkEntity = sourceMeta?.link_entity;
    if (!linkEntity) return undefined;

    const cacheKey = `${linkEntity}:${String(sourceValue)}:${remoteField}`;
    if (!remoteValueCache.has(cacheKey)) {
      remoteValueCache.set(
        cacheKey,
        getFetchFromFields(linkEntity, String(sourceValue), [remoteField])
          .then((response) =>
            response?.status === "success"
              ? response.data?.[remoteField]
              : undefined,
          )
          .catch(() => undefined),
      );
      setTimeout(() => remoteValueCache.delete(cacheKey), 5_000);
    }

    return remoteValueCache.get(cacheKey);
  }

  async function resolveRowReference(
    reference: string,
    rowData?: Record<string, any>,
  ): Promise<any> {
    const effectiveRowData = getEffectiveRowData(rowData);
    const pathParts = reference.split(".").filter(Boolean);
    if (pathParts.length === 0) return undefined;

    const [sourceField, ...nestedParts] = pathParts;
    if (!sourceField) return undefined;

    const sourceValue = effectiveRowData?.[sourceField];
    if (
      sourceValue === null ||
      sourceValue === undefined ||
      sourceValue === ""
    ) {
      return undefined;
    }

    if (nestedParts.length === 0) return sourceValue;

    if (typeof sourceValue === "object") {
      const nestedValue = readNestedValue(sourceValue, nestedParts);
      if (nestedValue !== undefined) return nestedValue;
    }

    return fetchRemoteFilterValue(
      sourceField,
      sourceValue,
      nestedParts.join("."),
    );
  }

  async function resolveLinkFilters(
    linkFilter: LinkFilterDefinition | null | undefined,
    rowData?: Record<string, any>,
    fieldName?: string,
  ): Promise<Record<string, any> | undefined> {
    if (!linkFilter) return undefined;

    const effectiveRowData = getEffectiveRowData(rowData);

    const resolved: Record<string, any> = {};

    for (const [key, rawValue] of Object.entries(linkFilter)) {
      if (typeof rawValue === "string" && rawValue.startsWith("parent.")) {
        const parentField = rawValue.slice("parent.".length);
        const parentValue = options.parentFormData?.value?.[parentField];
        if (
          parentValue !== null &&
          parentValue !== undefined &&
          parentValue !== ""
        ) {
          resolved[key] = parentValue;
        }
        continue;
      }

      if (typeof rawValue === "string" && rawValue.includes(".")) {
        const rowValue = await resolveRowReference(rawValue, effectiveRowData);
        if (rowValue !== null && rowValue !== undefined && rowValue !== "") {
          resolved[key] = rowValue;
        }
        continue;
      }

      resolved[key] = rawValue;
    }

    return Object.keys(resolved).length > 0 ? resolved : undefined;
  }

  return {
    resolveLinkFilters,
  };
}
