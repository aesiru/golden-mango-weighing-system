# Core Layer

**Clean Architecture Position:** Layer 2 — Foundation. Provides framework wiring that all other layers depend on.

The core layer contains the application's load-bearing infrastructure: settings, database connection, security, ORM base class, and the framework package that bootstraps core entities (User, Role, Workflow). It sits between domain (pure Python) and infrastructure (external adapters).

---

## Contents

```
core/
├── config.py           # Pydantic settings, loaded once at startup
├── database.py         # SQLAlchemy async engine, session factory, get_db()
├── security.py         # JWT validation, CurrentUser, get_password_hash()
├── base_model.py       # BaseModel ORM class (id, created_at, updated_at)
├── exceptions.py       # HTTP exception classes (404, 400, 403, 409, 500)
├── error_handlers.py   # @handle_api_errors decorator, safe_dict_response()
├── feature_flags.py    # Runtime feature toggles
├── loader.py           # load_modules() — dynamic import of all modules
├── sanitization.py     # sanitize_string(), sanitize_dict() (XSS prevention)
├── seed.py             # run_seeds() facade
├── serialization.py    # record_to_dict() — model → plain dict
├── framework/
│   ├── __init__.py     # Public API: User, Role, Attachment, AuditLog, ErrorLog…
│   ├── contracts/      # EntityContract, ModuleContract, InitializationContract
│   ├── entities/       # JSON definitions for core entities
│   └── models/         # SQLAlchemy models: User, Role, WorkflowState, etc.
└── seeds/
    ├── __init__.py     # run_all_seeds() — ordered orchestrator
    ├── roles.py        # Default system roles
    ├── permissions.py  # RBAC matrix
    ├── workflow_states.py  # Workflow states with Nuxt UI color codes
    ├── workflow_actions.py # Action verbs (Approve, Reject, Submit…)
    ├── users.py        # Superadmin creation
    ├── workflows.py    # Entity workflow configurations
    └── request_activity_types.py
```

---

## Config (`config.py`)

Settings are loaded once via Pydantic's `BaseSettings`. All environment variables are typed and defaulted.

```python
from app.core.config import settings

db_url = settings.DATABASE_URL
smtp_host = settings.SMTP_HOST
```

**Key settings:**

| Setting | Default | Description |
|---|---|---|
| `DATABASE_URL` | required | PostgreSQL async URL |
| `SECRET_KEY` | required | JWT signing key |
| `RUN_SEEDS` | `True` | Run idempotent seeds on startup |
| `STORAGE_BACKEND` | `local` | `local` or `s3` |
| `SMTP_HOST` / `SMTP_PORT` | optional | Email sending config |

---

## Database (`database.py`)

Sets up the async SQLAlchemy engine. Use `get_db()` as a FastAPI dependency for per-request sessions.

```python
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

async def my_route(db: AsyncSession = Depends(get_db)):
    ...
```

**Never use `async_session_maker` directly in routes.** Reserve it for non-request contexts (scheduled jobs, seeds, CLI).

---

## Security (`security.py`)

Handles JWT decoding and the `CurrentUser` dataclass. All protected routes use `get_current_user_from_token`.

```python
from app.core.security import CurrentUser, get_current_user_from_token
from fastapi import Depends

async def protected_route(current_user: CurrentUser = Depends(get_current_user_from_token)):
    print(current_user.id, current_user.role, current_user.is_superadmin)
```

**`CurrentUser` fields:** `id`, `email`, `role`, `role_id`, `is_superadmin`

Password hashing is delegated to `infrastructure/auth/password_service.py`. `core/security.py` only handles token validation.

---

## Base Model (`base_model.py`)

All SQLAlchemy models inherit from `BaseModel`. Do not use SQLAlchemy's `Base` directly.

```python
from app.core.base_model import BaseModel

class MyEntity(BaseModel):
    __tablename__ = "my_entity"
    title = Column(String)
    status = Column(String, default="Draft")
```

**Auto-provided columns:** `id` (String PK), `created_at` (DateTime), `updated_at` (DateTime auto-updated).

---

## HTTP Exceptions (`exceptions.py`)

Map domain exceptions to HTTP responses. Used in `api/` error handling.

| Class | HTTP Status |
|---|---|
| `NotFoundError` | 404 |
| `BadRequestError` | 400 |
| `UnauthorizedError` | 401 |
| `ForbiddenError` | 403 |
| `ConflictError` | 409 |
| `InternalServerError` | 500 |

```python
from app.core.exceptions import NotFoundError, ForbiddenError

raise NotFoundError("Record not found")
raise ForbiddenError("You do not have permission")
```

---

## Error Handlers (`error_handlers.py`)

The `@handle_api_errors` decorator automatically converts domain exceptions to HTTP responses.

```python
from app.core.error_handlers import handle_api_errors

@router.post("/entity/{entity_name}")
@handle_api_errors
async def create_entity(...):
    ...
```

---

## Feature Flags (`feature_flags.py`)

Toggles feature availability at runtime based on environment variables.

```python
from app.core.feature_flags import is_feature_enabled

if is_feature_enabled("my_feature"):
    # Feature is active
    ...
```

---

## Framework (`framework/`)

The framework package contains the core entity models that ship with the system. These are protected — they cannot be overwritten by module entity JSON files.

**Core models exported by `framework/__init__.py`:**

| Model | Table | Purpose |
|---|---|---|
| `User` | `user` | System users |
| `Role` | `role` | RBAC roles |
| `EntityPermission` | `entity_permission` | Role → Entity → Action matrix |
| `WorkflowState` | `workflow_state` | All possible document states |
| `WorkflowAction` | `workflow_action` | All possible workflow verbs |
| `Workflow` | `workflow` | Entity workflow configurations |
| `AuditLog` | `audit_log` | Record of all mutations |
| `ErrorLog` | `error_log` | Application error log |
| `Attachment` | `attachment` | File attachments |
| `Notification` | `notification` | User notification inbox |

---

## Seeds (`seeds/`)

Seeders populate the database with required reference data. All seeders are **idempotent** — safe to run repeatedly.

Execution order (enforced by `run_all_seeds()`):

1. Roles
2. Entity permissions
3. Workflow states
4. Workflow actions
5. Users (superadmin)
6. Workflows
7. Request activity types

---

## Rules for This Layer

| Rule | Detail |
|---|---|
| **No business logic** | Core is infrastructure, not domain logic |
| **Config is read-only at runtime** | Never mutate `settings` after startup |
| **Framework models are protected** | Do not add business logic methods to core models |
| **Seeds must be idempotent** | Use `get_or_create` patterns; never `INSERT` without a check |
| **Serialization is presentation-free** | `record_to_dict()` should not apply display formatting |
