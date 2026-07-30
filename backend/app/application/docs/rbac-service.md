<!-- SCOPE: Application service documentation for role-based access control orchestration -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding RBAC architecture, implementing permission checks, configuring role-based access -->
<!-- SKIP_WHEN: Quick API reference - use the Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/services/rbac_service.py, backend/app/api/routes/admin/permissions.py, backend/app/models/auth.py -->

# RBAC Service

## Quick Navigation

- [Architecture](#architecture) - Service design and cache strategy
- [Permission Model](#permission-model) - Actions and resolution logic
- [API Integration](#api-integration) - Middleware and route protection
- [Core Operations](#core-operations) - Permission checking and cache management
- [Frontend Integration](#frontend-integration) - Permission composables and UI components
- [Database Schema](#database-schema) - Roles and permissions tables
- [Configuration](#configuration) - Default roles and assignment
- [Performance](#performance) - Cache metrics and optimization
- [Testing](#testing) - Test strategies and coverage
- [Security](#security) - Best practices and vulnerability prevention

## Agent Entry

**Purpose**: The RBAC (Role-Based Access Control) Service provides permission checking orchestration for entity operations. It delegates database access to AuthRepository and implements an in-memory cache for performance optimization.

**When to Read**:

- Implementing permission checks in API endpoints
- Configuring role-based access control
- Understanding permission caching strategy
- Troubleshooting permission issues
- Setting up admin permission management

**When to Skip**: Quick permission API lookup - use the Quick Navigation section above

**Canonical**: This is the primary reference for RBAC service architecture and integration patterns

**Next**: Read Architecture section to understand cache strategy, then Permission Model for resolution logic

**Primary Sources**:

- `backend/app/application/services/rbac_service.py` - Core service implementation
- `backend/app/api/routes/admin/permissions.py` - Admin permission management
- `backend/app/models/auth.py` - Database schema definitions

## Overview

The RBAC (Role-Based Access Control) Service provides permission checking orchestration for entity operations. It delegates database access to the AuthRepository and implements an in-memory cache for performance optimization.

## Architecture

### Domain Model

```
┌─────────────────────────────────────┐
│   RBACAppService                    │
├─────────────────────────────────────┤
│   auth_repo: AuthRepository         │
│   _cache: dict[str, dict]           │
└─────────────────────────────────────┘

Cache Entry Structure:
{
  "{role_id}:{entity}": {
    "can_read": bool,
    "can_create": bool,
    "can_update": bool,
    "can_delete": bool
  }
}
```

**Key Characteristics:**

- **Superuser Bypass:** Superusers bypass all permission checks
- **In-Memory Cache:** Role permissions cached per entity for performance
- **Cache Invalidation:** Manual clear or TTL-based expiration
- **Multiple Roles:** Users with multiple roles get union of permissions

## Permission Model

### Actions

| Action   | Description             |
| -------- | ----------------------- |
| `read`   | View entity records     |
| `create` | Create new records      |
| `update` | Modify existing records |
| `delete` | Remove records          |

### Permission Resolution

```
User → Role(s) → Entity Permissions → Action Check
```

**Rules:**

1. Superuser = ALL permissions granted
2. No roles = NO permissions granted
3. Multiple roles = Union of permissions (OR logic)
4. Cache hit = Use cached permission
5. Cache miss = Query database, populate cache

## API Integration

### Middleware Protection

**Location:** `backend/app/api/middleware/rbac_middleware.py`

```python
async def check_permission(
    request: Request,
    entity: str,
    action: str
) -> None:
    user = request.state.user

    has_permission = await rbac_service.check_permission(
        user_id=user.id,
        entity=entity,
        action=action,
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )

    if not has_permission:
        raise PermissionDeniedError(
            f"User lacks {action} permission for {entity}"
        )
```

### Route Decorator

```python
@router.get("/entity/{entity_type}")
async def list_entities(
    entity_type: str,
    request: Request,
    rbac: RBACAppService = Depends(get_rbac_service)
):
    await rbac.check_permission(
        request.state.user.id,
        entity_type,
        "read",
        request.state.user.role_ids,
        request.state.user.is_superuser
    )
    # ... handle request
```

## Core Operations

### Check Permission

```python
async def check_permission(
    user_id: str,
    entity: str,
    action: str,
    role_ids: Optional[list[str]] = None,
    is_superuser: bool = False,
) -> bool
```

**Algorithm:**

1. If `is_superuser`: Return `True`
2. If no `role_ids`: Return `False`
3. Check cache for each role → entity combination
4. Cache hit: Return cached permission
5. Cache miss: Query database for permissions
6. Populate cache with results
7. Return permission value

### Cache Management

**Load Cache:**

```python
async def load_cache(role_ids: list[str]):
    """Pre-load all permissions for given roles."""
    permissions = await self.auth_repo.get_entity_permissions(role_ids)
    for perm in permissions:
        for role_id in role_ids:
            cache_key = f"{role_id}:{perm.entity_name}"
            self._cache[cache_key] = {
                "can_read": perm.can_read,
                "can_create": perm.can_create,
                "can_update": perm.can_update,
                "can_delete": perm.can_delete,
            }
```

**Clear Cache:**

```python
def clear_cache(self):
    """Clear all cached permissions."""
    self._cache.clear()
```

**Cache Strategy:**

- Pre-load on application startup for active roles
- Clear on permission configuration changes
- Lazy loading for new/unseen role-entity combinations

## Frontend Integration

### Permission Checking

**Composables:** `frontend/app/composables/usePermissions.ts`

```typescript
const { canRead, canCreate, canUpdate, canDelete } = usePermissions('purchase_request');

// Template usage
<UButton v-if="canCreate">Create Purchase Request</UButton>
<UButton v-if="canUpdate" @click="edit">Edit</UButton>
<UButton v-if="canDelete" @click="delete">Delete</UButton>
```

### Route Guards

```typescript
// Require specific permission
definePageMeta({
  middleware: ["auth"],
  requiredPermission: {
    entity: "work_order",
    action: "create",
  },
});
```

### UI Components

**PermissionWrapper Component:**

```vue
<template>
  <slot v-if="hasPermission" />
  <slot v-else name="fallback">
    <UAlert color="warning" title="Permission Denied" />
  </slot>
</template>
```

## Database Schema

### Tables

**roles:**

- `id`: Primary key
- `name`: Role name (Administrator, Manager, User)
- `is_active`: Boolean

**role_permissions:**

- `id`: Primary key
- `role_id`: Foreign key to roles
- `entity_name`: Entity slug (e.g., "purchase_request")
- `can_read`: Boolean
- `can_create`: Boolean
- `can_update`: Boolean
- `can_delete`: Boolean

**user_roles:**

- `user_id`: Foreign key to users
- `role_id`: Foreign key to roles

## Configuration

### Default Roles

Created during system initialization:

| Role          | Permissions                        |
| ------------- | ---------------------------------- |
| Administrator | All entities: CRUD                 |
| Manager       | Most entities: CRUD (except users) |
| User          | Read-only on assigned entities     |
| Guest         | Read-only on public entities       |

### Permission Assignment

**Via Admin UI:** `frontend/app/pages/admin/permissions.vue`

- Matrix view: Roles × Entities
- Toggle buttons for each action
- Bulk assign across entities
- Copy permissions from existing role

## Performance

### Cache Metrics

- Cache hits: ~95% for typical workloads
- Cache miss penalty: 1-2 DB queries
- Memory usage: ~50KB per 100 role-entity combinations

### Optimization Strategies

1. **Pre-loading:** Load all permissions at startup
2. **Lazy Loading:** On-demand for dynamic roles
3. **Background Refresh:** Update cache without blocking
4. **Selective Invalidation:** Clear only changed roles

## Testing

**Unit Tests:** `backend/tests/test_rbac_service.py`

Test scenarios:

- Superuser bypass permission check
- User with single role permission
- User with multiple roles (union of permissions)
- User with no roles denied access
- Cache hit performance
- Cache miss population
- Cache clear functionality

**Integration Tests:**

- API endpoints with permission middleware
- Frontend permission composables
- Admin permission configuration UI

## Security

### Best Practices

- Never trust client-side permission checks
- Always validate at API layer
- Cache does not expose sensitive data (only booleans)
- Role changes invalidate cache immediately
- Audit log for permission changes

### Common Vulnerabilities Prevented

- **IDOR:** Entity-level permission checks
- **Privilege Escalation:** Role assignment restrictions
- **Cache Poisoning:** Cache only stores permission booleans

## Future Enhancements

- Field-level permissions (hide sensitive fields)
- Row-level permissions (access only assigned records)
- Permission inheritance (role hierarchy)
- Time-based permissions (temporary access)
- Conditional permissions (based on record state)
- Permission templates for quick role creation

## Maintenance

**Update Triggers**:

- Permission model changes
- New entity types added
- Role hierarchy modifications
- Cache strategy updates
- Security requirement changes

**Verification**:

- Run `pytest tests/test_rbac_service.py` - all tests must pass
- Verify superuser bypass functionality
- Test cache hit/miss performance
- Validate role union logic
- Check admin permission UI functionality
- Confirm frontend permission composables work correctly

**Last Updated**: 2026-04-05
