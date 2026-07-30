<!-- SCOPE: Core Framework Architecture Decision Record - Documents the rationale for separating core framework entities -->

# ADR-001: Core Framework Entity Separation

## Status
**Accepted** — Implemented in Core Framework Refactor Epic (Stories 1-7)

## Context

The FastAPI backend had core infrastructure entities scattered across multiple locations:
- `app/models/` — Auth, Workflow, Infrastructure models
- `app/core/` — Some base classes
- No clear ownership rules for what qualifies as "core" vs "module-specific"

This led to:
- Unclear import paths for developers
- Risk of circular dependencies
- No standardized way for modules to access foundational entities
- Difficulty in maintaining system-wide contracts

## Decision

We will consolidate all core framework entities into a single location: `app/core/framework/`

### Core Framework Definition

Core entities are those that:
1. Are required by multiple business modules
2. Provide system-wide infrastructure (auth, logging, workflow)
3. Have stable APIs that rarely change
4. Require DEVELOPER_MODE protection to prevent accidental modification

### Entity Categories

| Category | Entities | Purpose |
|----------|----------|---------|
| **Auth** | User, Role, EntityPermission | Authentication & authorization |
| **Infrastructure** | ErrorLog, AuditLog, Attachment, EmailLog, NotificationSubscription, ScheduledJobLog | System logging, storage, notifications |
| **Ordering** | ModuleOrder, EntityOrder | Display order management |
| **Workflow** | WorkflowState, WorkflowAction, Workflow, WorkflowStateLink, WorkflowTransition | State machine engine |

## Directory Structure

```
app/core/framework/
├── __init__.py              # Public API exports
├── models/
│   ├── auth.py              # User, Role, EntityPermission
│   ├── infrastructure.py    # ErrorLog, AuditLog, Attachment, etc.
│   ├── ordering.py          # ModuleOrder, EntityOrder
│   └── workflow.py          # WorkflowState, WorkflowAction, etc.
├── schemas/
│   ├── auth.py              # Pydantic schemas for auth
│   └── infrastructure.py    # Pydantic schemas for infrastructure
└── MODULE_DEVELOPER_GUIDE.md # Developer documentation
```

## Consequences

### Positive

1. **Single Source of Truth** — All core entities in one location
2. **Clear Import Patterns** — `from app.core.framework import User, Role`
3. **Auto-Availability** — Core entities available immediately on import
4. **Stable Contract** — Public API guaranteed stable across versions
5. **Developer Protection** — Core entities require DEVELOPER_MODE=1 to edit
6. **No Circular Dependencies** — Clean separation between core and modules

### Negative

1. **Migration Effort** — All imports across backend needed updating
2. **Table Name Changes** — Core tables prefixed with `core_` (e.g., `core_users`)
3. **Legacy Import Paths** — Old imports in `app.models` kept temporarily for compatibility

## Migration Path

### Old Import (Deprecated)
```python
from app.models import User
from app.models.workflow import WorkflowState
from app.models.ordering import ModuleOrder
```

### New Import (Recommended)
```python
from app.core.framework import User, WorkflowState, ModuleOrder
```

### Module Loader Integration

The `app/core/loader.py` now initializes core framework before loading any modules:

```python
def load_modules():
    # Initialize core framework FIRST
    from app.core.framework import initialize_core_framework
    initialize_core_framework()
    
    # Then load business modules...
```

## Related Documents

- [MODULE_DEVELOPER_GUIDE.md](../framework/MODULE_DEVELOPER_GUIDE.md) — Developer usage guide
- [CORE_FRAMEWORK_REFACTOR_EPIC.md](../../_core_refactor_tmp/CORE_FRAMEWORK_REFACTOR_EPIC.md) — Implementation stories

## Decision Date

2026-04-06

## Owner

Backend Architecture Team
