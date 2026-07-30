<!-- SCOPE: Decorator-based hook registry for entity lifecycle with OCP compliance -->
<!-- DOC_KIND: explanation -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding hook system architecture, implementing entity lifecycle hooks, extending entity functionality -->
<!-- SKIP_WHEN: Quick reference - use--> Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/hooks/ -->

# Hooks System

## Overview

The Hooks System provides a decorator-based registry for entity lifecycle hooks, replacing the old if/elif chain with an Open/Closed Principle (OCP) compliant architecture. It enables modules to register before_save, after_save, after_delete, and workflow hooks using clean decorators.

## Quick Navigation

- [Architecture](#architecture) - Hook registry and domain model
- [Hook Registration](#hook-registration) - Decorator syntax and usage
- [Hook Types](#hook-types) - Available lifecycle hooks
- [Validation Hooks](#validation-hooks) - Data validation methods
- [Workflow Hooks](#workflow-hooks) - Workflow transition methods
- [Frontend Integration](#frontend-integration) - Usage in entity services
- [Testing](#testing) - Test strategies and coverage

## Agent Entry

**Purpose**: The Hooks System provides a decorator-based registry for entity lifecycle hooks, replacing the old if/elif chain with an Open/Closed Principle (OCP) compliant architecture. It enables modules to register before_save, after_save, after_delete, and workflow hooks using clean decorators.

**When to Read**:

- Understanding hook system architecture
- Implementing custom entity lifecycle logic
- Registering hooks for new entities
- Migrating from old hook pattern to new registry

**When to Skip**:

- Simple CRUD operations without lifecycle hooks
- Direct entity manipulation without validation
- Legacy hook implementation patterns

**Canonical Status**: This document is the primary source for understanding the Hooks System architecture and implementation patterns.

**Next Steps**: After reading this, explore specific entity hook implementations and module-level hook registration patterns.

**Primary Sources**:

- `backend/app/application/hooks/` - Hook registry and decorator system
- `backend/app/modules/*/hooks.py` - Entity-specific hook implementations

## Overview

The Hooks System provides a decorator-based registry for entity lifecycle hooks, replacing the old if/elif chain with an Open/Closed Principle (OCP) compliant architecture. It enables modules to register before_save, after_save, after_delete, and workflow hooks using clean decorators.

## Architecture {#architecture}

### Domain Model

```
┌─────────────────────────────────────┐
│   HookRegistry                      │
├─────────────────────────────────────┤
│   _before_save: dict[str, list]     │
│   _after_save: dict[str, list]      │
│   _after_delete: dict[str, list]    │
│   _workflow: dict[str, list]      │
└─────────────────────────────────────┘

HookEntry:
┌─────────────────────────────────────┐
│   entity: str                       │
│   func: Callable                    │
│   priority: int                     │
└─────────────────────────────────────┘
```

**Hook Types:**

- `before_save`: Modify/validate data before persistence
- `after_save`: Execute logic after record creation/update
- `after_delete`: Cleanup or cascading operations after deletion
- `workflow`: Handle workflow state transitions

## Hook Registration {#hook-registration}

### Decorator Syntax

```python
from app.application.hooks.registry import hook_registry

@hook_registry.before_save("my_entity", priority=0)
async def my_entity_before_save(doc: dict, ctx: SaveContext) -> dict:
    """Modify data before saving my_entity."""

    ...

@hook_registry.before_save("my_entity", priority=10)   # Executes later
async def low_priority_hook(doc, ctx):
    ...
```

## Hook Context Objects

### SaveContext

```python
@dataclass
class SaveContext:
    db: AsyncSession           # Database session
    user: Any                  # Current user
    entity: str                # Entity name
    action: str                # "create" or "update"
    meta: Any = None           # Entity metadata
```

### WorkflowContext

```python
@dataclass
class WorkflowContext:
    db: AsyncSession           # Database session
    user: Any                  # Current user
    entity: str                # Entity name
    doc: Any                   # Record being processed
    record_id: str             # Record ID
    action: str                # Workflow action slug
    from_state: str            # Previous workflow state
    to_state: str              # Target workflow state
```

## Hook Execution

### Before Save Execution

```python
async def run_before_save(
    self,
    entity: str,
    doc: dict,
    ctx: SaveContext
) -> tuple[dict, Optional[dict]]:
    """Returns (modified_doc, errors)."""
    hooks = self._before_save.get(entity, [])
    for hook in hooks:
        result = await hook.func(doc, ctx)
        if isinstance(result, tuple):
            doc, errors = result
            if errors:
                return doc, errors  # Stop on error
        elif isinstance(result, dict):
            doc = result
    return doc, None
```

**Error Handling:**

- Return `(doc, errors)` to abort with validation errors
- Return `doc` to continue execution

### After Save Execution

```python
async def run_after_save(
    self,
    entity: str,
    doc: Any,
    ctx: SaveContext
) -> Optional[dict]:
    """Returns last hook result."""
    hooks = self._after_save.get(entity, [])
    last_result = None
    for hook in hooks:
        result = await hook.func(doc, ctx)
        if result is not None:
            last_result = result
    return last_result
```

### Workflow Execution

```python
async def run_workflow(
    self,
    entity: str,
    ctx: WorkflowContext
) -> dict:
    """Returns result dict."""
    hooks = self._workflow.get(entity, [])
    for hook in hooks:
        result = await hook.func(ctx)
        if result and result.get("status") == "error":
            return result  # Stop on error
        if result:
            return result   # First non-error result wins
    return {"status": "success", "message": f"No workflow hook for '{entity}'"}
```

## API Aliases

The registry provides aliases compatible with entity CRUD operations:

```python
# Alias methods used by entity_crud.py
async def execute_before_save(entity, doc, ctx) -> dict:
    """Returns {"data": modified_doc} or {"errors": errors}."""

async def execute_after_save(entity, doc, ctx) -> Any:
    """Direct pass-through to run_after_save."""

async def execute_after_delete(entity, doc, ctx) -> Any:
    """Direct pass-through to run_after_delete."""

async def execute_workflow(entity, ctx) -> dict:
    """Direct pass-through to run_workflow."""
```

## Integration Points

### Entity CRUD Integration

**Location:** `backend/app/api/routes/entity_crud.py`

```python
from app.application.hooks.registry import hook_registry

# Before creating/updating
result = await hook_registry.execute_before_save(entity, data, ctx)
if result.get("errors"):
    raise ValidationError(result["errors"])
modified_data = result["data"]

# After save
await hook_registry.execute_after_save(entity, record, ctx)

# After delete
await hook_registry.execute_after_delete(entity, record, ctx)
```

### Workflow Router Integration

**Location:** `backend/app/api/routes/entity_workflow.py`

```python
from app.application.hooks.registry import hook_registry

# Execute workflow hook
result = await hook_registry.execute_workflow(entity, workflow_context)
```

### Module-Level Hook Registration

**Example:** `backend/app/modules/<module>/hooks.py`

```python
from app.application.hooks.registry import hook_registry

@hook_registry.before_save("my_entity")
async def my_entity_before_save(doc, ctx):
    # Validation and modification logic
    return doc

@hook_registry.workflow("my_entity")
async def pr_workflow(ctx):
    # Routed to workflow_router
    from .workflow_router import route_workflow
    return await route_workflow(ctx)
```

## Introspection

### Check Entity Has Hooks

```python
has_hooks = hook_registry.has_hooks("my_entity")
# Returns True if any hooks registered for entity
```

### List Registered Entities

```python
entities = hook_registry.list_entities()
# Returns set of all entities with registered hooks
```

## Testing {#testing}

**Unit Tests:** `backend/tests/test_hooks.py`

Test scenarios:

- Hook registration and priority ordering
- Before save execution and error handling
- After save execution chain
- Workflow hook dispatch
- Introspection methods

**Example Test:**

```python
async def test_before_save_priority():
    registry = HookRegistry()
    execution_order = []

    @registry.before_save("test", priority=10)
    async def low_priority(doc, ctx):
        execution_order.append("low")
        return doc

    @registry.before_save("test", priority=-10)
    async def high_priority(doc, ctx):
        execution_order.append("high")
        return doc

    await registry.run_before_save("test", {}, None)
    assert execution_order == ["high", "low"]
```

## Migration from Old System

### Old Pattern (Deprecated)

```python
# Old services/hooks.py
if entity == "asset":
    await asset_hooks.before_save(doc)
elif entity == "work_order":
    await work_order_hooks.before_save(doc)
```

### New Pattern (Current)

```python
# Decorator-based registration
@hook_registry.before_save("asset")
async def asset_before_save(doc, ctx):
    ...
```

## Performance

- O(1) hook lookup by entity
- Priority sorting at registration time
- No conditional chains at runtime
- Minimal overhead per hook execution

## Security

- Hooks run with same privileges as calling code
- Database session passed via context
- User context available for permission checks
- No sandboxing - hooks have full system access

## Future Enhancements

- Async hook chaining with cancellation
- Hook result caching
- Conditional hook registration
- Hook execution metrics/tracing
- Pre/post hook middleware
- Hook plugin system

## Maintenance

**Update Triggers**:

- New hook types added
- Hook execution flow changes
- Context object modifications
- Registration API updates

**Verification**:

- Run `pytest tests/test_hooks.py` - all tests must pass
- Test hook priority ordering
- Verify error handling in before_save
- Check workflow hook dispatch
- Validate introspection methods
- Confirm integration with entity_crud

**Last Updated**: 2026-04-05
