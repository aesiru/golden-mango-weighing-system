# Modules Layer

**Clean Architecture Position:** Layer 5 — Domain feature units. Self-contained vertical slices of business functionality.

Each module owns its SQLAlchemy models, entity JSON metadata, business-specific API logic, lifecycle hooks, and workflow routing for one domain area. Modules are loaded dynamically by the core loader — they register themselves at startup rather than being statically imported everywhere.

---

## Available Modules

| Module | Domain | Key Entities |
|---|---|---|
| `core` | Framework | User, Role, EntityPermission, WorkflowState, WorkflowAction, AuditLog |

---

## Module Structure

Every module follows the same layout:

```
{module_name}/
├── __init__.py             # Module docstring — what this module contains
├── hooks.py                # Lifecycle hooks using @hook_registry decorators
├── workflow_router.py      # Workflow action dispatch (if the module has workflows)
├── models/                 # SQLAlchemy ORM model files (one entity per file)
│   ├── __init__.py         # Imports and registers all models
│   └── {entity}.py         # e.g., my_entity.py
├── entities/               # Entity JSON metadata (if customized beyond defaults)
│   └── {entity}/
│       └── {entity}.json
└── apis/                   # Business logic specific to this module
    └── {entity}.py         # Handler functions called by hooks or workflow_router
```

---

## Module Loading

Modules are loaded dynamically by `core/loader.py` at application startup. The load order is deterministic (defined in `MODULE_LOAD_ORDER` in `loader.py`). Never import modules directly in route files or services — use the hook registry or dependency injection.

```python
# core/loader.py controls the order
MODULE_LOAD_ORDER = [
    "core",
]
```

---

## Models

Each model file defines one SQLAlchemy model. Keep models pure — no methods, no business logic.

```python
# modules/my_module/models/my_entity.py
from sqlalchemy import Column, String, ForeignKey
from app.core.base_model import BaseModel

class MyEntity(BaseModel):
    __tablename__ = "my_entity"

    title = Column(String)
    status = Column(String, default="Draft")
    assigned_to = Column(String, ForeignKey("user.id"))
```

All models are collected in `models/__init__.py` and auto-registered with the entity repository at startup.

---

## Hooks (`hooks.py`)

Hooks are business reactions to save and workflow events. Use the `hook_registry` decorators — never put this logic in route handlers or services.

```python
# modules/<module>/hooks.py
from app.application.hooks.registry import hook_registry
from app.application.hooks.context import SaveContext, WorkflowContext

@hook_registry.before_save("my_entity")
async def validate_my_entity(ctx: SaveContext) -> None:
    """Validate entity data before saving."""
    if not ctx.doc.get("required_field"):
        from app.domain.exceptions import ValidationError
        raise ValidationError("Required field missing", field_errors={"required_field": "Required"})

@hook_registry.after_save("my_entity", action="create")
async def on_my_entity_created(ctx: SaveContext) -> None:
    """Perform follow-up work after entity creation."""
    await send_creation_notification(ctx.doc, ctx.db)

@hook_registry.workflow("my_entity", action="Submit")
async def on_my_entity_submitted(ctx: WorkflowContext) -> None:
    """React to workflow transitions for this entity."""
    ...
```

---

## Workflow Router (`workflow_router.py`)

Defines which API function handles each workflow action for entities in this module.

```python
# modules/my_module/workflow_router.py
from app.application.utils.doc_utils import get_id, get_attr

WORKFLOW_ROUTES = {
    "my_entity": {
        "Submit":  handle_submit,
        "Approve": handle_approve,
        "Reject":  handle_reject,
        "Cancel":  handle_cancel,
    }
}

async def handle_submit(doc, action, db, user):
    entity_id = get_id(doc)
    # validate, update status, notify
    ...
```

The generic workflow endpoint (`api/entries/entity_workflow.py`) looks up the correct handler here.

---

## Module APIs (`apis/`)

Business-specific logic that doesn't fit in hooks goes here. These are plain async functions — not FastAPI route handlers.

```python
# modules/<module>/apis/my_entity.py
from app.application.utils.doc_utils import get_id, get_attr

async def calculate_score(entity_id: str, db) -> dict:
    """Compute derived values for this entity."""
    record = await get_doc("my_entity", entity_id, db)
    return {"score": compute_score(record)}
```

Module APIs are called from:

- `hooks.py` via `@hook_registry` decorators
- `workflow_router.py` via workflow action handlers
- Application services for shared business behavior

---

## Adding a New Module

1. **Create the directory** under `modules/`:

   ```
   modules/my_module/
   ├── __init__.py
   ├── hooks.py
   ├── models/__init__.py
   └── entities/__init__.py
   ```

2. **Register the module** in `core/loader.py`:

   ```python
   MODULE_LOAD_ORDER = [..., "my_module"]
   ```

3. **Define models** in `models/`:

   ```python
   # models/my_entity.py
   from app.core.base_model import BaseModel

   class MyEntity(BaseModel):
       __tablename__ = "my_entity"
       name = Column(String)
   ```

4. **Register all models** in `models/__init__.py`:

   ```python
   from app.modules.my_module.models.my_entity import MyEntity
   ```

5. **Run `python -m app.forge sync`** to generate and apply the migration.

---

## Inter-Module Dependencies

Modules must **not import from each other's `apis/` or `models/`** directly. If module A needs data from module B, it should:

- Use the generic `get_doc` / `get_list` document query functions
- Or use a domain protocol implemented in infrastructure

```python
# Correct — use generic document access
from app.application.services.documents.document_query import get_doc

record = await get_doc("my_entity", record_id, db)

# Wrong — direct cross-module model import
from app.modules.other_module.models.other_entity import OtherEntity  # ❌
```

---

## Rules for This Layer

| Rule | Detail |
|---|---|
| **Models are pure** | No methods, no business logic in model files |
| **Hooks over inline logic** | Business reactions go in `hooks.py`, not in route handlers |
| **Use `doc_utils` for common helpers** | Never redefine helpers locally |
| **No cross-module model imports** | Use `get_doc`/`get_list` for cross-module data access |
| **Module APIs are called by hooks/workflow_router** | Not directly by route handlers |
| **No FastAPI in module APIs** | Module API functions are plain async functions |
