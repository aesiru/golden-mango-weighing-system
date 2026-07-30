<!-- SCOPE: Application service documentation for partial field fetching with link resolution -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding partial field fetching, implementing link title resolution, managing query links -->
<!-- SKIP_WHEN: Quick API reference - use the Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/services/fetch_from_service.py, backend/app/api/routes/fetch_from.py, backend/app/services/query_link_handlers.py -->

# Fetch From Service

## Quick Navigation

- [Architecture](#architecture) - Service design and domain model
- [API Endpoints](#api-endpoints) - Fetch from REST API specifications
- [Core Operations](#core-operations) - Field fetching and link resolution
- [Field Type Handling](#field-type-handling) - Standard, query, and parent-child links
- [Frontend Integration](#frontend-integration) - Form population and UI components
- [Query Link Target Mapping](#query-link-target-mapping) - Handler registry
- [Repository Pattern](#repository-pattern) - Partial field access
- [Performance](#performance) - Optimization strategies
- [Testing](#testing) - Test strategies and coverage
- [Error Handling](#error-handling) - Resolution scenarios and fallbacks
- [Use Cases](#use-cases) - Form pre-fill, display fields, child context

## Agent Entry

**Purpose**: The Fetch From Service retrieves partial field data from entity records, resolving linked record titles for display purposes. It's used when populating forms with data from linked records or fetching specific fields without loading the entire record.

**When to Read**:

- Understanding partial field fetching patterns
- Implementing link title resolution
- Managing query link handlers
- Building form pre-fill functionality
- Troubleshooting fetch performance issues
- Configuring field type handling

**When to Skip**: Quick fetch API reference - use the Quick Navigation section above

**Canonical**: This is the primary reference for fetch from service architecture and partial operations

**Next**: Read Architecture section to understand service design, then Core Operations for resolution logic

**Primary Sources**:

- `backend/app/application/services/fetch_from_service.py` - Core service implementation
- `backend/app/api/routes/fetch_from.py` - Fetch from API endpoints
- `backend/app/services/query_link_handlers.py` - Query link handler registry

## Overview

The Fetch From Service retrieves partial field data from entity records, resolving linked record titles for display purposes. It's used when populating forms with data from linked records or fetching specific fields without loading the entire record.

## Architecture

### Domain Model

```
┌─────────────────────────────────────┐
│   FetchFromService                  │
├─────────────────────────────────────┤
│   repo: FetchFromRepository         │
└─────────────────────────────────────┘

Return Structure:
{
  "data": {
    "field1": "value1",
    "field2": "value2"
  },
  "link_titles": {
    "entity::id": "Display Name"
  }
}
```

**Supported Field Types:**

- `string`, `int`, `float`, `date`, `datetime`, `boolean` - Direct values
- `link` - Value + resolved title
- `query_link` - Value + resolved title via query mapping
- `parent_child_link` - Value + resolved title via child entity

## API Endpoints

**Base:** `/api/v1/entity/{entity_type}/{record_id}`

| Endpoint      | Method | Description                                  |
| ------------- | ------ | -------------------------------------------- |
| `/fetch-from` | GET    | Get partial fields with resolved link titles |

### Query Parameters

- `fields`: Comma-separated list of field names to fetch

### Response Format

```json
{
  "data": {
    "asset": "ASSET-001",
    "location": "LOC-001",
    "department": "DEPT-001",
    "status": "active"
  },
  "link_titles": {
    "asset::ASSET-001": "Server Rack A",
    "location::LOC-001": "Building 1 - Floor 2",
    "department::DEPT-001": "IT Operations"
  }
}
```

## Core Operations

### Get Fetch From Fields

```python
async def get_fetch_from_fields(
    entity: str,
    record_id: str,
    fields: list[str],
) -> tuple[Optional[dict[str, Any]], dict[str, str]]
```

**Algorithm:**

1. Get entity metadata from MetaRegistry
2. Fetch specified fields from repository (partial select)
3. For each field, determine if it's a link type
4. For link fields, resolve linked entity's title
5. Return data dict and link_titles dict

### Link Resolution Logic

```python
for field_name in fields:
    fm = field_meta_map.get(field_name)
    if not fm:
        continue

    fk_value = data.get(field_name)
    if not fk_value:
        continue

    # Determine linked entity
    link_entity_name = None

    if fm.field_type == "link" and fm.link_entity:
        link_entity_name = fm.link_entity

    elif fm.field_type == "query_link" and fm.query:
        # Look up target entity from query key
        query_key = fm.query.get("key")
        link_entity_name = QUERY_LINK_TARGET_ENTITY.get(query_key)

    elif fm.field_type == "parent_child_link" and fm.child_entity:
        link_entity_name = fm.child_entity

    # Resolve title
    if link_entity_name:
        linked_meta = MetaRegistry.get(link_entity_name)
        title_field = linked_meta.title_field or "id"
        title = await repo.get_title(link_entity_name, str(fk_value), title_field)
        link_titles[f"{link_entity_name}::{fk_value}"] = title
```

## Field Type Handling

### Standard Link Fields

```json
{
  "name": "asset",
  "field_type": "link",
  "link_entity": "asset"
}
```

→ Fetches from `asset` entity using `asset` field value

### Query Link Fields

```json
{
  "name": "work_order",
  "field_type": "query_link",
  "query": { "key": "active_work_orders_by_asset" }
}
```

→ Looks up target entity from `QUERY_LINK_TARGET_ENTITY` mapping

### Parent-Child Link Fields

```json
{
  "name": "parent_request",
  "field_type": "parent_child_link",
  "child_entity": "maintenance_request"
}
```

→ Fetches from `maintenance_request` entity

## Frontend Integration

### Form Field Link Resolution

**Location:** `frontend/app/components/EntityFieldRenderer.vue`

```vue
<!-- Link field with resolved title -->
<template v-if="field.field_type === 'link'">
  <div class="link-display">
    <span class="font-medium">{{ resolvedTitle }}</span>
    <span class="text-gray-500 text-sm">({{ fieldValue }})</span>
  </div>
</template>

<script setup>
const props = defineProps<{
  field: FieldDefinition;
  value: any;
  linkTitles?: Record<string, string>;
}>();

const resolvedTitle = computed(() => {
  const key = `${field.link_entity}::${props.value}`;
  return props.linkTitles?.[key] || props.value;
});
</script>
```

### Form Population

**Location:** `frontend/app/pages/[entity]/[id].vue`

```typescript
// Fetch linked record data
async function fetchFromLinkedRecord(
  linkEntity: string,
  linkId: string,
  fields: string[],
) {
  const result = await entityApi.fetchFrom(linkEntity, linkId, fields);

  // Populate form fields
  Object.assign(formData, result.data);

  // Store link titles for display
  linkTitles.value = { ...linkTitles.value, ...result.link_titles };
}
```

### Child Grid Copy From Parent

**Location:** `frontend/app/components/ChildDataGrid.vue`

```typescript
// Copy field from parent when creating new child row
if (fieldMeta.copy_from_parent) {
  const parentField = fieldMeta.copy_from_parent;
  newRow[fieldMeta.name] = props.parentFormData[parentField];
}
```

## Query Link Target Mapping

### Handler Registry

```python
# app/services/query_link_handlers.py
QUERY_LINK_TARGET_ENTITY = {
    "active_work_orders_by_asset": "work_order",
    "pending_purchase_requests": "purchase_request",
    "available_assets_by_location": "asset",
    # ...
}
```

Used to resolve which entity to query for `query_link` fields.

## Repository Pattern

### FetchFromRepository

```python
class FetchFromRepository:
    async def get_partial_fields(
        self,
        entity: str,
        record_id: str,
        fields: list[str]
    ) -> Optional[dict]:
        """Fetch only specified fields from record."""
        # Build SELECT with only requested fields
        # Prevents over-fetching

    async def get_title(
        self,
        entity: str,
        record_id: str,
        title_field: str
    ) -> Optional[str]:
        """Get single title field value."""
        # Optimized single-field query
```

## Performance

- Partial field selection (not SELECT \*)
- Single query per linked entity (batched)
- No N+1 for multiple link fields
- Cached title lookups

## Testing

**Unit Tests:** `backend/tests/test_fetch_from_service.py`

Test scenarios:

- Simple field fetching
- Link field title resolution
- Query link resolution
- Parent-child link resolution
- Empty/null values
- Non-existent records
- Multiple link fields

## Error Handling

| Scenario                | Behavior           |
| ----------------------- | ------------------ |
| Entity not found        | Returns `None, {}` |
| Record not found        | Returns `None, {}` |
| Field not in metadata   | Skipped            |
| Empty link value        | No title resolved  |
| Linked entity not found | Uses raw value     |

## Use Cases

### 1. Form Pre-fill

Populate fields from linked record:

```python
# User selects "Asset" in dropdown
# Fetch asset's location, department, status
fields = ["location", "department", "status"]
data, titles = await service.get_fetch_from_fields("asset", asset_id, fields)
# Pre-fill work order form with asset data
```

### 2. Display-Only Fields

Show resolved names without storing:

```python
# Show "Building 1" instead of "LOC-001"
```

### 3. Child Grid Context

Parent data in child rows:

```python
# Copy parent's "store" to child "store" field
```

## Future Enhancements

- Nested link resolution (link → link → title)
- Batch multi-record fetching
- Caching layer for frequent lookups
- Computed field resolution
- Cross-entity field mapping templates
- Async field loading (lazy resolve)

## Maintenance

**Update Triggers**:

- Field fetching logic changes
- New field type handlers added
- Link resolution updates
- Performance optimization requirements
- Query link handler modifications
- Repository pattern changes

**Verification**:

- Run `pytest tests/test_fetch_from_service.py` - all tests must pass
- Test simple field fetching scenarios
- Verify link field title resolution
- Test query link resolution
- Check parent-child link handling
- Validate empty/null value handling
- Test multiple link fields
- Confirm performance optimization works

**Last Updated**: 2026-04-05
