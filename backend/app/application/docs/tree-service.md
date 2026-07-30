<!-- SCOPE: Application service documentation for hierarchical data management -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding tree architecture, implementing hierarchical operations, managing parent-child relationships -->
<!-- SKIP_WHEN: Quick API reference - use the Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/services/tree_service.py, backend/app/api/routes/entity_tree.py, backend/app/meta/registry.py -->

# Tree Service

## Quick Navigation

- [Architecture](#architecture) - Service design and domain model
- [Entity Configuration](#entity-configuration) - Tree entity metadata setup
- [API Endpoints](#api-endpoints) - Tree REST API specifications
- [Core Operations](#core-operations) - Tree data building and validation
- [Frontend Integration](#frontend-integration) - Tree view components and navigation
- [Validation](#validation) - Structure validation and cycle detection
- [MetaRegistry Integration](#metaregistry-integration) - Tree metadata lookup
- [Testing](#testing) - Test strategies and coverage
- [Performance](#performance) - Optimization and loading strategies
- [Database Schema](#database-schema) - Tree entity pattern

## Agent Entry

**Purpose**: The Tree Service manages hierarchical data structures for entities configured as trees. It provides operations for building tree views with parent-child relationships, enabling visual representation of organizational structures like Locations, Asset Classes, and Systems.

**When to Read**:

- Understanding hierarchical data management
- Implementing tree view operations
- Configuring tree entity metadata
- Troubleshooting tree building issues
- Building tree visualization components
- Managing parent-child relationships

**When to Skip**: Quick tree API reference - use the Quick Navigation section above

**Canonical**: This is the primary reference for tree service architecture and hierarchical operations

**Next**: Read Architecture section to understand service design, then Entity Configuration for metadata setup

**Primary Sources**:

- `backend/app/application/services/tree_service.py` - Core service implementation
- `backend/app/api/routes/entity_tree.py` - Tree API endpoints
- `backend/app/meta/registry.py` - Entity metadata and tree configuration

## Overview

The Tree Service manages hierarchical data structures for entities configured as trees. It provides operations for building tree views with parent-child relationships, enabling visual representation of organizational structures like Locations, Asset Classes, and Systems.

## Architecture

### Domain Model

```
┌─────────────────────────────────────┐
│   TreeService                       │
├─────────────────────────────────────┤
│   tree_repository: TreeRepository   │
└─────────────────────────────────────┘

Tree Node Structure:
{
  "id": "LOC-001",
  "label": "Building A",
  "children": [
    {
      "id": "LOC-002",
      "label": "Floor 1",
      "children": [...]
    }
  ]
}
```

**Entity Configuration:**

- `is_tree`: Boolean flag in entity metadata
- `tree_parent_field`: Field name for parent reference (e.g., "parent_location")

## Entity Configuration

### Tree Entity JSON

```json
{
  "name": "location",
  "label": "Location",
  "is_tree": true,
  "tree_parent_field": "parent_location",
  "fields": [
    {
      "name": "parent_location",
      "field_type": "link",
      "link_entity": "location"
    }
  ]
}
```

### Standard Tree Entities

| Entity        | Parent Field         | Use Case                      |
| ------------- | -------------------- | ----------------------------- |
| `location`    | `parent_location`    | Physical location hierarchy   |
| `asset_class` | `parent_asset_class` | Asset classification taxonomy |
| `system`      | `parent_system`      | System/subsystem hierarchy    |

## API Endpoints

**Base:** `/api/v1/entity/{entity_type}`

| Endpoint | Method | Description                |
| -------- | ------ | -------------------------- |
| `/tree`  | GET    | Get hierarchical tree data |

### Query Parameters

- `parent_field`: Override default parent field
- `title_field`: Field to use for node labels

### Tree Response

```json
[
  {
    "id": "LOC-001",
    "label": "Corporate HQ",
    "data": {
      "id": "LOC-001",
      "name": "Corporate HQ",
      "type": "building"
    },
    "children": [
      {
        "id": "LOC-002",
        "label": "Floor 1",
        "data": { ... },
        "children": [
          {
            "id": "LOC-003",
            "label": "Room 101",
            "data": { ... },
            "children": []
          }
        ]
      }
    ]
  }
]
```

## Core Operations

### Get Tree Data

```python
async def get_tree_data(
    entity_name: str,
    parent_field: Optional[str] = None,
    title_field: Optional[str] = None
) -> List[Dict[str, Any]]
```

**Algorithm:**

1. Validate entity exists and `is_tree` is true
2. Get all records for entity
3. Build parent → children mapping
4. Identify root nodes (no parent or parent not in set)
5. Recursively build tree structure
6. Return root-level array

### Tree Repository

```python
class TreeRepository:
    async def get_tree_data(
        self,
        entity_name: str,
        parent_field: Optional[str] = None,
        title_field: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        # Fetch all records
        records = await self.entity_repo.get_all(entity_name)

        # Build lookup maps
        record_map = {r['id']: r for r in records}
        children_map: Dict[str, List[Dict]] = defaultdict(list)

        # Map children to parents
        for record in records:
            parent_id = record.get(parent_field)
            if parent_id and parent_id in record_map:
                children_map[parent_id].append(record)

        # Build tree recursively
        def build_node(record):
            return {
                "id": record["id"],
                "label": record.get(title_field, record["id"]),
                "data": record,
                "children": [build_node(c) for c in children_map[record["id"]]]
            }

        # Return root nodes
        roots = [r for r in records if not r.get(parent_field) or r.get(parent_field) not in record_map]
        return [build_node(r) for r in roots]
```

## Frontend Integration

### Tree View Component

**Location:** `frontend/app/components/TreeView.vue`

```vue
<template>
  <UTree :items="treeData" @select="handleSelect" @expand="handleExpand">
    <template #item="{ item }">
      <div class="flex items-center gap-2">
        <UIcon name="i-heroicons-folder" />
        <span>{{ item.label }}</span>
        <UBadge size="xs">{{ item.children?.length || 0 }}</UBadge>
      </div>
    </template>
  </UTree>
</template>

<script setup>
const props = defineProps<{
  entity: string;
  parentField?: string;
}>();

const { data: treeData } = await useAsyncData(
  'tree',
  () => entityApi.getTreeData(props.entity, props.parentField)
);
</script>
```

### Entity List View Modes

**Location:** `frontend/app/pages/[entity]/index.vue`

```vue
<template>
  <div class="view-modes">
    <UButtonGroup>
      <UButton
        :color="viewMode === 'list' ? 'primary' : 'gray'"
        @click="viewMode = 'list'"
      >
        List
      </UButton>
      <UButton
        v-if="metadata.is_tree"
        :color="viewMode === 'tree' ? 'primary' : 'gray'"
        @click="viewMode = 'tree'"
      >
        Tree
      </UButton>
      <UButton
        v-if="metadata.is_diagram"
        :color="viewMode === 'diagram' ? 'primary' : 'gray'"
        @click="viewMode = 'diagram'"
      >
        Diagram
      </UButton>
    </UButtonGroup>
  </div>

  <!-- List View -->
  <EntityDataTable v-if="viewMode === 'list'" :entity="entity" />

  <!-- Tree View -->
  <TreeView
    v-else-if="viewMode === 'tree'"
    :entity="entity"
    :parent-field="metadata.tree_parent_field"
    @select="navigateToNode"
  />

  <!-- Diagram View -->
  <DiagramView v-else-if="viewMode === 'diagram'" :entity="entity" />
</template>
```

### Parent Field Selector

**Location:** `frontend/app/pages/model-editor/[entity].vue`

```vue
<UFormGroup label="Tree Parent Field">
  <USelect
    v-model="entityConfig.tree_parent_field"
    :options="selfReferencingLinkFields"
    :disabled="!entityConfig.is_tree"
  />
</UFormGroup>
```

## Validation

### Tree Structure Validation

Prevent circular references:

```python
def validate_no_cycles(entity_name: str, record_id: str, new_parent_id: str) -> bool:
    """Ensure setting new_parent_id wouldn't create a cycle."""
    current = new_parent_id
    while current:
        if current == record_id:
            return False  # Cycle detected
        parent = get_parent(current)
        current = parent
    return True
```

### Entity Tree Validation

```python
if not entity_meta.is_tree:
    raise ValueError(f"Entity {entity_name} is not configured as a tree")
```

## MetaRegistry Integration

### Tree Metadata

```python
from app.meta.registry import MetaRegistry

meta = MetaRegistry.get('location')
print(meta.is_tree)              # True
print(meta.tree_parent_field)    # "parent_location"
```

## Testing

**Unit Tests:** `backend/tests/test_tree_service.py`

Test scenarios:

- Tree building with 3 levels
- Empty tree (no records)
- Single root no children
- Multiple roots
- Missing parent references (orphaned nodes)
- Circular reference detection
- Custom title field

## Performance

- Single query for all records
- O(N) tree building
- Efficient parent→children mapping
- Lazy loading for deep trees (frontend)

## Database Schema

### Tree Entities Pattern

Self-referencing link field:

```sql
CREATE TABLE location (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    parent_location VARCHAR REFERENCES location(id),
    -- other fields
);
```

## Future Enhancements

- Drag-and-drop reordering
- Lazy loading for large trees
- Tree search/filtering
- Expand/collapse state persistence
- Tree node actions (add child, delete)
- Multiple parent support (DAG vs Tree)
- Tree path enumeration (materialized path)
- Tree depth limits
- Animated transitions

## Maintenance

**Update Triggers**:

- Tree building algorithm changes
- New hierarchy patterns added
- Performance optimization requirements
- Validation rule updates
- Frontend component changes
- Database schema modifications

**Verification**:

- Run `pytest tests/test_tree_service.py` - all tests must pass
- Test tree building with multiple levels
- Verify empty tree handling
- Check single root scenarios
- Validate circular reference detection
- Test custom title field usage
- Confirm parent-child mapping accuracy
- Check lazy loading performance

**Last Updated**: 2026-04-05
