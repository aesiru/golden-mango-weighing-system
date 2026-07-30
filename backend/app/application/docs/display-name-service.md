<!-- SCOPE: Application service documentation for human-readable display name resolution -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding display name resolution, implementing title field logic, managing link field resolution -->
<!-- SKIP_WHEN: Quick API reference - use the Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/services/display_name_service.py, backend/app/api/routes/fetch_from.py, backend/app/meta/registry.py -->

# Display Name Service

## Quick Navigation

- [Architecture](#architecture) - Service design and resolution chain
- [Core Operations](#core-operations) - Single and batch resolution
- [Title Field Configuration](#title-field-configuration) - Entity metadata setup
- [Link Field Resolution](#link-field-resolution) - Nested resolution patterns
- [API Integration](#api-integration) - Entity options and fetch endpoints
- [Frontend Integration](#frontend-integration) - UI components and composables
- [MetaRegistry Integration](#metaregistry-integration) - Title field lookup and fallback
- [Testing](#testing) - Test strategies and coverage
- [Performance](#performance) - Optimization and caching strategies
- [Error Handling](#error-handling) - Resolution scenarios and fallbacks

## Agent Entry

**Purpose**: The Display Name Service resolves human-readable display names for entity records. It uses entity's `title_field` metadata to determine best field for display, with automatic resolution of linked record titles for link fields.

**When to Read**:

- Understanding display name resolution patterns
- Implementing title field logic
- Managing link field resolution
- Troubleshooting display name issues
- Building UI components that show resolved titles
- Configuring entity title fields

**When to Skip**: Quick display name API reference - use the Quick Navigation section above

**Canonical**: This is the primary reference for display name service architecture and resolution patterns

**Next**: Read Architecture section to understand service design, then Core Operations for resolution logic

**Primary Sources**:

- `backend/app/application/services/display_name_service.py` - Core service implementation
- `backend/app/api/routes/fetch_from.py` - API endpoints with title resolution
- `backend/app/meta/registry.py` - Entity metadata and title field configuration

## Overview

The Display Name Service resolves human-readable display names for entity records. It uses the entity's `title_field` metadata to determine the best field for display, with automatic resolution of linked record titles for link fields.

## Architecture

### Domain Model

```
┌─────────────────────────────────────┐
│   DisplayNameService                │
├─────────────────────────────────────┤
│   db: AsyncSession                  │
│   _repo: EntityRepository           │
└─────────────────────────────────────┘
```

**Resolution Chain:**

1. Get entity metadata from MetaRegistry
2. Find `title_field` (or default to "id")
3. Get value from record
4. If link field → resolve linked record's title
5. Return display string

## Core Operations

### Single Record Resolution

```python
async def resolve(entity_type: str, record: Dict[str, Any]) -> str
```

**Resolution Logic:**

```python
meta = MetaRegistry.get(entity_type)
if not meta:
    return record.get('id', 'Unknown')

title_field = meta.title_field or 'id'
display_name = record.get(title_field)

if not display_name:
    display_name = record.get('id', 'Unknown')

# If link field, resolve linked record's title
if field_meta and field_meta.field_type == 'link':
    linked_record = await repo.get_by_id(link_entity, link_value)
    if linked_record:
        display_name = linked_record.get(linked_title_field, link_value)

return str(display_name) if display_name else 'Unknown'
```

### Batch Resolution

```python
async def resolve_many(
    entity_type: str,
    records: list[Dict[str, Any]]
) -> Dict[str, str]
# Returns: {record_id: display_name}
```

**Example:**

```python
records = [
    {"id": "WO-001", "title": "Fix HVAC Unit"},
    {"id": "WO-002", "title": "Replace Filter"}
]
names = await service.resolve_many("work_order", records)
# Result: {"WO-001": "Fix HVAC Unit", "WO-002": "Replace Filter"}
```

## Title Field Configuration

### Entity Metadata

```json
{
  "name": "work_order",
  "title_field": "title",
  "fields": [
    { "name": "title", "field_type": "string" },
    { "name": "description", "field_type": "text" }
  ]
}
```

### Default Behavior

If no `title_field` specified:

- Uses `id` field
- Falls back to "Unknown"

## Link Field Resolution

### Nested Resolution

For link fields used as title:

```json
{
  "name": "purchase_request",
  "title_field": "requested_by",
  "fields": [
    {
      "name": "requested_by",
      "field_type": "link",
      "link_entity": "user"
    }
  ]
}
```

**Resolution Chain:**

1. Get `requested_by` value (e.g., "USR-001")
2. Fetch user record "USR-001"
3. Get user's title_field value (e.g., "john.doe")
4. Return "john.doe" as display name

### Deep Link Resolution

```
work_order.asset → asset record → asset.title
```

## API Integration

### Entity Options Endpoint

**Location:** `backend/app/api/routes/entity_options.py`

Options automatically include display names:

```json
{
  "options": [
    { "value": "WO-001", "label": "Fix HVAC Unit" },
    { "value": "WO-002", "label": "Replace Filter" }
  ]
}
```

### Fetch From Endpoint

**Location:** `backend/app/api/routes/fetch_from.py`

Returns both data and resolved link titles:

```json
{
  "data": { "asset": "ASSET-001", "location": "LOC-001" },
  "link_titles": {
    "asset::ASSET-001": "Server Rack A",
    "location::LOC-001": "Building 1"
  }
}
```

## Frontend Integration

### Link Field Display

**Component:** `EntityFieldRenderer.vue`

```vue
<!-- Link field showing resolved title -->
<div class="link-field">
  <span class="value">{{ resolvedTitle }}</span>
  <UButton size="xs" @click="navigateTo(record.id)">
    {{ record.id }}
  </UButton>
</div>
```

### Autocomplete Options

```typescript
const options = await entityApi.getEntityOptions("work_order");
// Each option has label (display name) and value (ID)
// [{ value: 'WO-001', label: 'Fix HVAC Unit' }, ...]
```

### List View Display

**Location:** `frontend/app/pages/[entity]/index.vue`

```vue
<UTable :data="records">
  <template #title-cell="{ row }">
    <ULink :to="`/${entity}/${row.id}`">
      {{ row.title || row.id }}
    </ULink>
  </template>
</UTable>
```

## MetaRegistry Integration

### Title Field Lookup

```python
from app.meta.registry import MetaRegistry

meta = MetaRegistry.get('work_order')
title_field = meta.title_field  # "title"
```

### Fallback Chain

1. `meta.title_field` if specified
2. `"name"` field if exists
3. `"title"` field if exists
4. Record `id`
5. `"Unknown"`

## Testing

**Unit Tests:** `backend/tests/test_display_name_service.py`

Test scenarios:

- Direct title field resolution
- Link field title resolution
- Missing title field fallback
- Missing record fallback
- Batch resolution
- Circular link detection

## Performance

- Single queries for individual lookups
- Batch resolution for lists
- Caching for frequently accessed links
- N+1 prevention with eager loading

## Error Handling

| Scenario                | Result                                     |
| ----------------------- | ------------------------------------------ |
| Entity not found        | Returns record ID or "Unknown"             |
| Record not found (link) | Returns raw link value                     |
| Title field empty       | Falls back to ID                           |
| Circular reference      | Returns raw value (prevents infinite loop) |

## Future Enhancements

- Computed display names (template strings)
- Multi-field concatenation ("{first_name} {last_name}")
- Format functions (dates, numbers)
- Caching layer for frequently accessed titles
- Async batch loading optimization
- Display name change history

## Maintenance

**Update Triggers**:

- Display name resolution changes
- New title field patterns added
- Link field resolution updates
- Performance optimization needs
- Fallback chain modifications
- Caching strategy changes

**Verification**:

- Run `pytest tests/test_display_name_service.py` - all tests must pass
- Test direct title field resolution
- Verify link field title resolution
- Test missing title field fallback
- Check batch resolution performance
- Validate circular reference detection
- Confirm API integration works correctly

**Last Updated**: 2026-04-05
