# Base Entity API

## Overview

The Base Entity API provides a foundation class for per-entity API layers with lifecycle hooks. It enables entities to implement custom validation and business logic through method overrides, supporting Clean Architecture by keeping entity-specific code organized and testable.

## Architecture

### Clean Architecture Position

```
┌─────────────────────────────────────┐
│   BaseEntityAPI                     │
├─────────────────────────────────────┤
│   Abstract base class for entity    │
│   lifecycle hooks and validation    │
└─────────────────────────────────────┘

Per-Entity Implementation:
┌─────────────────────────────────────┐
│   AssetAPI(BaseEntityAPI)           │
│   WorkOrderAPI(BaseEntityAPI)       │
│   PurchaseRequestAPI(BaseEntityAPI) │
└─────────────────────────────────────┘
```

**Moved from:** `app/apis/` to `app/application/services/` for Clean Architecture compliance.

## Context Object

```python
@dataclass
class Context:
    db: AsyncSession      # Database session
    user: CurrentUser     # Authenticated user
    meta: EntityMeta      # Entity metadata
```

Passed to all hook methods for access to database, user context, and entity configuration.

## Hook Methods

### Validation Hooks

#### Validate Create

```python
async def validate_create(
    self,
    data: dict[str, Any],
    ctx: Context
) -> Optional[dict[str, str]]
```

**Purpose:** Validate data before creating a new record.

**Returns:**

- `None` - Validation passed
- `dict[str, str]` - Field errors: `{"field_name": "error message"}`

**Example:**

```python
class PurchaseRequestAPI(BaseEntityAPI):
    async def validate_create(self, data, ctx):
        errors = {}

        # Required field validation
        if not data.get("description"):
            errors["description"] = "Description is required"

        # Business rule validation
        if data.get("total_amount", 0) <= 0:
            errors["total_amount"] = "Total amount must be greater than zero"

        return errors if errors else None
```

#### Validate Update

```python
async def validate_update(
    self,
    id: str,
    data: dict[str, Any],
    ctx: Context
) -> Optional[dict[str, str]]
```

**Purpose:** Validate data before updating an existing record.

**Example:**

```python
class WorkOrderAPI(BaseEntityAPI):
    async def validate_update(self, id, data, ctx):
        # Prevent changing certain fields on closed work orders
        record = await ctx.db.get(WorkOrder, id)
        if record and record.workflow_state == "Closed":
            if "description" in data:
                return {"description": "Cannot modify closed work order"}

        return None
```

### Lifecycle Hooks

#### Before Create

```python
async def before_create(
    self,
    data: dict[str, Any],
    ctx: Context
) -> dict[str, Any]
```

**Purpose:** Modify data before creating the record.

**Returns:** Modified data dictionary

**Example:**

```python
class AssetAPI(BaseEntityAPI):
    async def before_create(self, data, ctx):
        # Auto-generate asset code
        if not data.get("asset_code"):
            data["asset_code"] = await generate_asset_code(ctx.db)

        # Set default location from user
        if not data.get("location") and ctx.user.default_location:
            data["location"] = ctx.user.default_location

        return data
```

#### After Create

```python
async def after_create(
    self,
    record: Any,
    ctx: Context
) -> None
```

**Purpose:** Execute logic after record is created.

**Example:**

```python
class MaintenanceRequestAPI(BaseEntityAPI):
    async def after_create(self, record, ctx):
        # Create notification
        await create_notification(
            entity="maintenance_request",
            record_id=record.id,
            action="created"
        )

        # Log activity
        await log_activity(
            user=ctx.user,
            action="created",
            entity="maintenance_request",
            record_id=record.id
        )
```

#### Before Update

```python
async def before_update(
    self,
    record: Any,
    data: dict[str, Any],
    ctx: Context
) -> dict[str, Any]
```

**Purpose:** Modify data before updating the record.

**Example:**

```python
class ItemAPI(BaseEntityAPI):
    async def before_update(self, record, data, ctx):
        # Track quantity changes for stock movements
        if "quantity" in data:
            old_qty = record.quantity
            new_qty = data["quantity"]

            if old_qty != new_qty:
                await create_stock_movement(
                    item_id=record.id,
                    from_qty=old_qty,
                    to_qty=new_qty,
                    user=ctx.user
                )

        return data
```

#### After Update

```python
async def after_update(
    self,
    record: Any,
    ctx: Context
) -> None
```

**Purpose:** Execute logic after record is updated.

**Example:**

```python
class PurchaseRequestAPI(BaseEntityAPI):
    async def after_update(self, record, ctx):
        # Check for approval and create purchase order
        if record.workflow_state == "Approved":
            await create_purchase_order_from_request(record, ctx)
```

#### Before Delete

```python
async def before_delete(
    self,
    record: Any,
    ctx: Context
) -> None
```

**Purpose:** Execute logic before deleting the record (validation/cleanup).

**Example:**

```python
class WorkOrderAPI(BaseEntityAPI):
    async def before_delete(self, record, ctx):
        # Prevent deleting active work orders
        if record.workflow_state in ["In Progress", "Started"]:
            raise ValueError("Cannot delete active work order")

        # Archive related data
        await archive_work_order_data(record.id, ctx.db)
```

#### After Delete

```python
async def after_delete(
    self,
    ctx: Context
) -> None
```

**Purpose:** Execute logic after record is deleted.

**Example:**

```python
class AssetAPI(BaseEntityAPI):
    async def after_delete(self, ctx):
        # Clean up related files
        await cleanup_asset_files(ctx.meta.id)

        # Log deletion
        await log_activity(
            user=ctx.user,
            action="deleted",
            entity="asset",
            record_id=ctx.meta.id
        )
```

## Usage Pattern

### Entity API Implementation

```python
# app/application/services/entity_api.py
from app.application.services.base_entity_api import BaseEntityAPI, Context

class MyEntityAPI(BaseEntityAPI):
    """Entity-specific API layer with custom business logic."""

    async def validate_create(self, data, ctx):
        # Add custom validation for this entity
        if not data.get("name"):
            return {"name": "Name is required"}
        return None

    async def before_create(self, data, ctx):
        # Transform or enrich data before save
        data["slug"] = slugify(data["name"])
        return data

    async def after_create(self, record, ctx):
        # Perform follow-up work after record creation
        await notify_record_created(record, ctx)
```

### Registration with Entity Routes

```python
# app/api/routes/entity_crud.py
from app.application.services.entity_api import MyEntityAPI

# Map entity names to API implementations
ENTITY_APIS = {
    "my_entity": MyEntityAPI(),
}

async def create_entity(entity: str, data: dict, db: AsyncSession, user: CurrentUser):
    api = ENTITY_APIS.get(entity)
    meta = MetaRegistry.get(entity)
    ctx = Context(db=db, user=user, meta=meta)

    if api:
        errors = await api.validate_create(data, ctx)
        if errors:
            raise ValidationError(errors)

        # Run before_create hook
        data = await api.before_create(data, ctx)

    # Create record via repository
    record = await entity_repo.create(entity, data)

    # Run after_create hook
    if api:
        await api.after_create(record, ctx)

    return record
```

## Integration with Hook Registry

BaseEntityAPI works alongside the decorator-based HookRegistry:

```python
# Module-level hooks (global)
@hook_registry.before_save("my_entity")
async def global_my_entity_validation(doc, ctx):
    # Runs for all my_entity saves
    return doc

# Entity API hooks (specific to CRUD)
class MyEntityAPI(BaseEntityAPI):
    async def validate_create(self, data, ctx):
        # Runs only for my_entity creation via API
        return errors
```

**Execution Order:**

1. BaseEntityAPI.validate_create
2. HookRegistry.before_save
3. Database operation
4. HookRegistry.after_save
5. BaseEntityAPI.after_create

## Testing

**Unit Tests:** `backend/tests/test_base_entity_api.py`

Test scenarios:

- Hook method chaining
- Validation error handling
- Data modification in before hooks
- Context object access
- Async hook execution

**Example Test:**

```python
async def test_validate_create_returns_errors():
    api = TestEntityAPI()
    ctx = Context(db=mock_db, user=mock_user, meta=mock_meta)

    errors = await api.validate_create(
        {"name": ""},
        ctx
    )

    assert errors == {"name": "Name is required"}

async def test_before_create_modifies_data():
    api = TestEntityAPI()
    ctx = Context(db=mock_db, user=mock_user, meta=mock_meta)

    result = await api.before_create(
        {"name": "Test"},
        ctx
    )

    assert result["modified_by_hook"] is True
```

## Benefits

1. **Clean Architecture**: Keeps entity logic in dedicated classes
2. **Testability**: Each hook can be tested in isolation
3. **Extensibility**: New entities follow the same pattern
4. **Composability**: Multiple hooks can be chained
5. **Type Safety**: Clear method signatures with type hints

## Future Enhancements

- Generic API factory for simple entities
- Hook composition (multiple APIs per entity)
- Async batch hooks
- Hook result caching
- Automatic API registration via decorators
- API versioning support

## Maintenance

**Update Triggers**:

- New hook types added
- Context object changes
- Hook execution order modifications
- Base class signature changes

**Verification**:

- Run `pytest tests/test_base_entity_api.py` - all tests must pass
- Test validation hook error handling
- Verify data modification in before hooks
- Check context object access patterns
- Test async hook execution
- Confirm integration with entity routes

**Last Updated**: 2026-04-05
