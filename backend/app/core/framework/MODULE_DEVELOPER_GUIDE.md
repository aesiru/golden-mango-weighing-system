<!-- SCOPE: Core Framework Module Developer Guide - Public API documentation for module developers -->

# Core Framework Module Developer Guide

Quick Navigation: [Overview](#overview) | [Importing Entities](#importing-core-entities) | [Using Schemas](#using-schemas) | [API Reference](#api-reference) | [Best Practices](#best-practices) | [Troubleshooting](#troubleshooting)

---

## Overview

The Core Framework provides foundational entities that are automatically available to all modules without explicit installation.

### Available Core Entities

| Category           | Entities                                  | Purpose                         |
| ------------------ | ----------------------------------------- | ------------------------------- |
| **Auth**           | User, Role, EntityPermission              | Authentication & authorization  |
| **Infrastructure** | ErrorLog, AuditLog, Attachment, EmailLog, | System logging, file storage,   |
|                    | NotificationSubscription, ScheduledJobLog | notifications, job scheduling   |
| **Ordering**       | ModuleOrder, EntityOrder                  | Module/entity display order     |
| **Workflow**       | WorkflowState, WorkflowAction, Workflow,  | State machine & workflow engine |
|                    | WorkflowStateLink, WorkflowTransition     |                                 |

### Key Features

- **Auto-Availability**: Entities available immediately on import
- **No Side Effects**: Importing does not trigger database operations
- **Stable API**: Public API guaranteed stable across versions
- **Developer Protection**: Core entities require `DEVELOPER_MODE=1` to edit

---

## Importing Core Entities

### Method 1: Direct Import (Recommended)

```python
from app.core.framework import User, Role
from app.core.framework import AuditLog, Attachment

# Use directly
user = User(username='john', email='john@example.com', ...)
```

### Method 2: Runtime Lookup

```python
from app.core.framework import get_core_entity

# Retrieve by name
User = get_core_entity('user')
user = User(username='john', ...)
```

### Method 3: List Available Entities

```python
from app.core.framework import list_core_entities

entities = list_core_entities()
# Returns: ['user', 'role', 'entity_permission', 'error_log', 'audit_log', 'attachment',
#           'email_log', 'notification_subscription', 'scheduled_job_log',
#           'module_order', 'entity_order',
#           'workflow_state', 'workflow_action', 'workflow',
#           'workflow_state_link', 'workflow_transition']
```

---

## Using Schemas

Pydantic schemas are available for validation:

```python
from app.core.framework.schemas import UserCreate, UserUpdate
from app.core.framework.schemas import AuditLogCreate

# Validate user creation data
user_data = UserCreate(
    username='john',
    email='john@example.com',
    full_name='John Doe',
    password='secure_password'
)
```

---

## API Reference

### Entity Access Functions

| Function             | Signature                          | Description                       |
| -------------------- | ---------------------------------- | --------------------------------- |
| `get_core_entity`    | `(entity_name: str) -> Type[Base]` | Retrieve entity class by name     |
| `list_core_entities` | `() -> List[str]`                  | List all available entity names   |
| `is_initialized`     | `() -> bool`                       | Check if framework is initialized |

### Exported Entities

```python
from app.core.framework import (
    # Auth Entities
    User,                    # User model (table: core_users)
    Role,                    # Role model (table: core_roles)
    EntityPermission,        # Permission model (table: core_entity_permissions)
    user_roles,              # Association table

    # Infrastructure Entities
    ErrorLog,                # Error logging (table: core_error_log)
    AuditLog,                # Audit trail (table: core_audit_log)
    Attachment,              # File attachments (table: core_attachment)
    EmailLog,                # Email logging (table: core_email_log)
    NotificationSubscription, # User notification subscriptions (table: core_notification_subscription)
    ScheduledJobLog,         # Scheduled job execution logs (table: core_scheduled_job_log)

    # Ordering Entities
    ModuleOrder,             # Module display order (table: core_module_orders)
    EntityOrder,             # Entity display order (table: core_entity_orders)

    # Workflow Entities
    WorkflowState,           # Global workflow state (table: core_workflow_states)
    WorkflowAction,          # Global workflow action (table: core_workflow_actions)
    Workflow,                # Per-entity workflow config (table: core_workflows)
    WorkflowStateLink,       # State-workflow junction (table: core_workflow_state_links)
    WorkflowTransition,      # State transitions (table: core_workflow_transitions)
    generate_slug,           # Utility: convert label to slug
```

### Schema Exports

```python
from app.core.framework.schemas import (
    # User Schemas
    UserBase, UserCreate, UserUpdate, UserInDB, User, UserWithRoles,

    # Role Schemas
    RoleBase, RoleCreate, RoleUpdate, RoleInDB, Role,

    # Permission Schemas
    EntityPermissionBase, EntityPermissionCreate, EntityPermissionUpdate,
    EntityPermissionInDB, EntityPermission,

    # Infrastructure Schemas
    ErrorLogBase, ErrorLogCreate, ErrorLogInDB, ErrorLog,
    AuditLogBase, AuditLogCreate, AuditLogInDB, AuditLog,
    AttachmentBase, AttachmentCreate, AttachmentUpdate, AttachmentInDB, Attachment
)
```

---

## Best Practices

| Practice          | Recommendation                                               |
| ----------------- | ------------------------------------------------------------ |
| **Import Method** | Prefer direct imports: `from app.core.framework import User` |
| **Validation**    | Use Pydantic schemas for input validation                    |
| **Extension**     | Extend via modules, never modify core entities               |
| **Legacy Code**   | Update old imports to use new paths                          |

### Core Framework Contract

1. **Auto-Availability**: Core entities available immediately on import
2. **No Side Effects**: Importing does not trigger database operations
3. **Stable API**: `app.core.framework` public API is version-stable
4. **Developer Protection**: Core entities require `DEVELOPER_MODE=1` to edit
5. **Immutable Structure**: Entity structure changes only in major versions

### Migration from Old Imports

| Old Import (Deprecated)                       | New Import (Recommended)                     |
| --------------------------------------------- | -------------------------------------------- |
| `from app.models import User`                 | `from app.core.framework import User`        |
| `from app.models.auth import User`            | `from app.core.framework import User`        |
| `from app.models.workflow import Workflow`    | `from app.core.framework import Workflow`    |
| `from app.models.ordering import ModuleOrder` | `from app.core.framework import ModuleOrder` |
| `from app.models.email_log import EmailLog`   | `from app.core.framework import EmailLog`    |

**Note:** Old imports still work with deprecation warnings but will be removed in a future version.

### Example: Module Using Core Entities

```python
# my_module/models/custom_entity.py
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.framework import User  # Import core entity


class CustomEntity(Base):
    __tablename__ = 'custom_entity'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_by = Column(String, ForeignKey('core_users.id'))  # Reference core table

    # Relationship to core User (optional)
    creator = relationship('User', backref='custom_entities')
```

---

## Troubleshooting

### Entity not found in get_core_entity()

Ensure correct entity name:

| ✅ Correct                     | ❌ Incorrect                            |
| ------------------------------ | --------------------------------------- |
| `get_core_entity('user')`      | `get_core_entity('User')` (wrong case)  |
| `get_core_entity('error_log')` | `get_core_entity('users')` (wrong name) |

### Import errors

| ✅ Correct Path                                     | ❌ Incorrect Path                            |
| --------------------------------------------------- | -------------------------------------------- |
| `from app.core.framework import User`               | `from app.core.framework.models import User` |
| `from app.core.framework.schemas import UserCreate` | `from app.models import UserCreate`          |

---

## Maintenance

**Owner:** Backend Architecture Team  
**Review Cycle:** Per major release  
**Last Updated:** 2026-04-06 (Story 6 Extended - All Core Entities Consolidated)

<!-- Agent Entry: Use this guide when implementing modules that depend on core framework entities. Refer to architecture docs for system-wide patterns. -->
