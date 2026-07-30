<!-- SCOPE: Application service documentation for generic CRUD operations orchestration -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding entity CRUD architecture, implementing generic entity operations, troubleshooting data access issues -->
<!-- SKIP_WHEN: Quick API reference - use the Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/services/entity_service.py, backend/app/api/routes/entity_crud.py, backend/app/meta/registry.py -->

# Entity Service

## Quick Navigation

- [Architecture](#architecture) - Service design and dependencies
- [API Endpoints](#api-endpoints) - Generic CRUD REST API specifications
- [Core Operations](#core-operations) - Data type coercion and CRUD flows
- [Frontend Integration](#frontend-integration) - Generic pages and state management
- [Metadata Integration](#metadata-integration) - MetaRegistry and validation
- [Hooks System](#hooks-system) - Lifecycle hooks and extensibility
- [Configuration](#configuration) - Entity metadata and behavior
- [Testing](#testing) - Test strategies and coverage
- [Security](#security) - Permission checks and audit logging
- [Performance](#performance) - Async operations and optimization

## Agent Entry

**Purpose**: The Entity Service orchestrates generic CRUD operations for all entities in system. It provides a unified interface for creating, reading, updating, and deleting records across any entity type, with automatic handling of metadata, naming conventions, workflow states, and data type coercion.

**When to Read**:

- Understanding generic entity CRUD patterns
- Implementing new entity operations
- Troubleshooting data type coercion issues
- Learning about metadata-driven architecture
- Understanding workflow state initialization
- Implementing hooks for entity lifecycle events

**When to Skip**: Quick CRUD API reference - use the Quick Navigation section above

**Canonical**: This is the primary reference for entity service architecture and generic CRUD patterns

**Next**: Read Architecture section to understand dependencies, then API Endpoints for integration details

**Primary Sources**:

- `backend/app/application/services/entity_service.py` - Core service implementation
- `backend/app/api/routes/entity_crud.py` - Generic CRUD endpoints
- `backend/app/meta/registry.py` - Entity metadata and validation

## Overview

The Entity Service orchestrates generic CRUD operations for all entities in the system. It provides a unified interface for creating, reading, updating, and deleting records across any entity type, with automatic handling of metadata, naming conventions, workflow states, and data type coercion.

## Architecture

### Domain Model

```
┌─────────────────────────────────────┐
│   EntityService                     │
├─────────────────────────────────────┤
│   entity_repo: EntityRepository     │
│   naming_repo: NamingRepository     │
│   rbac: RBACAppService              │
│   workflow_repo: WorkflowRepository │
│   socket_manager: SocketManager     │
└─────────────────────────────────────┘
```

**Dependencies:**

- `entity_repo`: Data access layer for entity records
- `naming_repo`: Auto-generates IDs based on naming conventions
- `rbac`: Permission checking for operations
- `workflow_repo`: Workflow state management
- `socket_manager`: Real-time WebSocket notifications

## API Endpoints

**Base:** `/api/v1/entity/{entity_type}`

| Endpoint              | Method | Description                                       |
| --------------------- | ------ | ------------------------------------------------- |
| `/{entity_type}`      | GET    | List entities with pagination, sorting, filtering |
| `/{entity_type}/{id}` | GET    | Get single entity by ID                           |
| `/{entity_type}`      | POST   | Create new entity record                          |
| `/{entity_type}/{id}` | PUT    | Update existing entity record                     |
| `/{entity_type}/{id}` | DELETE | Delete entity record                              |

### Request/Response Patterns

**List Response:**

```json
{
  "data": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

**Query Parameters (List):**

- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20)
- `sort_field`: Field to sort by
- `sort_order`: "asc" or "desc" (default: "desc")
- `filter_field`: Field to filter on
- `filter_value`: Value to filter by

## Core Operations

### Data Type Coercion

The service automatically coerces incoming request values based on SQLAlchemy column types:

| Source Type  | Target Type                   | Conversion                 |
| ------------ | ----------------------------- | -------------------------- |
| `string`     | `Integer`, `BigInteger`       | `int(value)`               |
| `string`     | `Float`, `Numeric`, `DECIMAL` | `float(value)`             |
| `string`     | `DateTime`                    | `datetime.fromisoformat()` |
| `string`     | `Date`                        | `date.fromisoformat()`     |
| empty string | nullable column               | `None`                     |
| empty string | non-nullable String           | `""`                       |

### Create Operation

**Auto-Generated ID:**

```python
if meta.naming and meta.naming.enabled and not data.get("id"):
    generated_id = await self.naming_repo.get_next_id(
        meta.naming.prefix, meta.naming.digits
    )
    data["id"] = generated_id
```

**Initial Workflow State:**

```python
if meta.workflow and meta.workflow.enabled and not data.get("workflow_state"):
    data["workflow_state"] = meta.workflow.initial_state
```

### Update Operation

**System Fields Stripping:**

```python
system_fields = {"id", "created_at", "updated_at"}
clean_data = {k: v for k, v in data.items() if k not in system_fields}
```

## Frontend Integration

### Generic Entity Pages

**Location:** `frontend/app/pages/[entity]/index.vue`

Standard data table with:

- UTable with pagination
- Column visibility controls
- Global search filter
- Action dropdown (View, Edit, Delete)
- Create button

**Location:** `frontend/app/pages/[entity]/[id]/index.vue`

Detail view with:

- Form fields based on entity metadata
- Workflow state display (if enabled)
- Related entities tabs
- History/audit log (if enabled)

### State Management

**Pinia Store:** `useEntityStore()`

```typescript
// List loading
const { data, total } = await entityStore.fetchList(entityType, {
  page: 1,
  page_size: 20,
  sort_field: "created_at",
  sort_order: "desc",
});

// Single record
const record = await entityStore.fetchOne(entityType, id);

// CRUD operations
await entityStore.create(entityType, data);
await entityStore.update(entityType, id, data);
await entityStore.delete(entityType, id);
```

## Metadata Integration

### MetaRegistry

All entities are registered in `MetaRegistry` with:

- `label`: Display name
- `naming`: ID generation rules (prefix, digits, enabled)
- `workflow`: Workflow configuration (states, transitions, initial_state)
- `fields`: Field definitions with types and constraints
- `relations`: Related entity configurations

### Validation

Service validates against metadata:

- Entity existence in registry
- Field data type matching
- Required field presence
- Workflow state validity

## Hooks System

Operations trigger hooks for extensibility:

| Hook            | When Fired             | Payload                |
| --------------- | ---------------------- | ---------------------- |
| `before_create` | Before record creation | entity, data, user     |
| `after_create`  | After record creation  | entity, record, user   |
| `before_update` | Before record update   | entity, id, data, user |
| `after_update`  | After record update    | entity, record, user   |
| `before_delete` | Before record deletion | entity, id, user       |
| `after_delete`  | After record deletion  | entity, id, user       |

## Configuration

No special configuration required. Entity behavior is driven by metadata in:

- `backend/app/modules/*/entities/*.json`
- Database `entity_metadata` table (for runtime overrides)

## Testing

**Unit Tests:** `backend/tests/test_entity_service.py`

Test scenarios:

- CRUD operations for each entity type
- Data type coercion edge cases
- Naming convention ID generation
- Workflow state initialization
- Permission denied handling
- Entity not found handling

**Integration Tests:**

- End-to-end entity lifecycle
- Hook execution order
- WebSocket event emission

## Security

- All operations check RBAC permissions
- Superusers bypass permission checks
- Field-level permissions evaluated at API layer
- Audit logging for all write operations

## Performance

- Repository layer uses async SQLAlchemy
- Connection pooling via asyncpg
- Caching for frequently accessed metadata
- Pagination for all list operations

## Future Enhancements

- Bulk import/export operations
- Entity versioning/history
- Soft delete with recovery
- Custom field validation rules
- Field-level encryption
- Advanced filtering operators (>, <, LIKE, etc.)

## Maintenance

**Update Triggers**:

- CRUD operation changes
- New entity types added
- Metadata schema updates
- Hook system modifications
- Data type coercion changes
- Workflow integration updates

**Verification**:

- Run `pytest tests/test_entity_service.py` - all tests must pass
- Test CRUD operations for all entity types
- Verify data type coercion edge cases
- Test naming convention ID generation
- Validate workflow state initialization
- Check hook execution order
- Confirm WebSocket event emission

**Last Updated**: 2026-04-05
