# Application Layer

**Clean Architecture Position:** Layer 4 — Use-case orchestration. The "brain" of the system.

The application layer coordinates business workflows. It receives intent (from API routes or hooks), calls repositories and services, enforces business rules, and returns results. It has no knowledge of HTTP, SQL, or SMTP — only domain protocols.

**Import rule:** Application services depend on domain protocols and other application services. They **never** import concrete infrastructure classes directly. All infrastructure is injected through constructors.

---

## Contents

```
application/
├── dto.py                       # Shared data transfer objects
├── hooks/
│   ├── context.py               # SaveContext, WorkflowContext, HookContext
│   └── registry.py              # @before_save, @after_save, @workflow decorators
├── email_notifications/
│   ├── catalog.py               # Developer-maintained event catalog
│   ├── dispatcher.py            # EmailNotificationDispatcher
│   └── document_notify.py       # Document-triggered email hooks
├── utils/
│   └── doc_utils.py             # Shared document helper functions
└── services/
    ├── entity_service.py         # Generic CRUD orchestrator
    ├── base_entity_api.py        # Template method base for per-entity APIs
    ├── branding_service.py       # Org branding (logo, org name)
    ├── fetch_from_service.py     # Link field title resolution service
    ├── tree_service.py           # Hierarchical data queries
    ├── setup_service.py          # First-run system initialization
    ├── import_export_service.py  # CSV import / export
    ├── access_control/
    │   └── rbac_service.py       # RBACAppService — permission checking
    ├── auth/
    │   └── auth_service.py       # AuthAppService — login, token creation
    ├── dashboards/
    │   └── dashboard_service.py  # DashboardAppService — metrics aggregation
    ├── documents/                # Document operations
    │   ├── document_query.py     # get_doc, get_list, get_value
    │   ├── document_mutation.py  # new_doc, save_doc, delete_doc
    │   ├── document_service.py   # DocumentAppService (CQRS-split)
    │   ├── link_title_service.py # get_link_title, build_link_titles_batch
    │   ├── naming.py             # ID naming logic (series-based)
    │   ├── naming_service.py     # NamingAppService
    │   ├── print.py              # Print orchestration
    │   ├── print_formatters.py   # Display formatting
    │   ├── print_resolver.py     # Link display name resolution for print
    │   ├── query_link.py         # Link options queries
    │   └── server_actions.py     # Server-side document action dispatch
    ├── integrations/
    │   ├── audit.py              # Audit log writer
    │   ├── error_logger.py       # Application error persistence
    │   ├── import_export.py      # Bulk CSV import/export logic
    │   └── metadata_sync_service.py  # Atomic metadata sync orchestration
    ├── maintenance/
    │   ├── constants.py          # Domain-specific constants
    │   └── job_service.py        # Scheduled job orchestration
    ├── notifications/
    │   ├── email_notification_service.py  # Sends notifications by subscription
    │   ├── notification_subscription_service.py  # Manages user subscriptions
    │   └── socketio.py           # Real-time Socket.IO manager
    ├── scheduling/
    │   ├── scheduler.py          # SchedulerAppService (job registration)
    │   └── app_initialization_service.py  # Wires scheduler on app startup
    └── workflows/
        ├── workflow_service.py          # WorkflowAppService (state transitions)
        └── workflow_progress_service.py # WorkflowProgressService (history, timeline)
```

---

## DTOs (`dto.py`)

Data objects passed between layers and returned to the API.

```python
from app.application.dto import PaginatedResult, ActionResult

result = PaginatedResult(data=[...], total=42, page=1, page_size=20)
result = ActionResult(status="success", message="Record created", data=record)
result = ActionResult(status="error", message="Validation failed", errors={"title": "Required"})
```

---

## Hook System (`hooks/`)

Hooks let modules react to save and workflow events without modifying the generic CRUD code (Open/Closed Principle).

### Context Objects (`context.py`)

| Context | Available In | Key Fields |
|---|---|---|
| `SaveContext` | `@before_save`, `@after_save` | `db`, `user`, `entity`, `action` (`create`/`update`), `doc` |
| `WorkflowContext` | `@workflow` | `db`, `user`, `entity`, `doc`, `action`, `from_state`, `to_state` |

### Registering Hooks (`registry.py`)

```python
from app.application.hooks.registry import hook_registry
from app.application.hooks.context import SaveContext, WorkflowContext

@hook_registry.before_save("my_entity")
async def set_defaults(ctx: SaveContext) -> None:
    if ctx.action == "create" and not ctx.doc.get("status"):
        ctx.doc["status"] = "Active"

@hook_registry.workflow("my_entity", action="Approve")
async def notify_on_approval(ctx: WorkflowContext) -> None:
    ...
```

Hooks accept a `priority` keyword (default `0`). Higher priority runs first.

```python
@hook_registry.before_save("my_entity", priority=10)
async def high_priority_hook(ctx: SaveContext) -> None:
    ...
```

---

## Email Notifications (`email_notifications/`)

### Event Catalog (`catalog.py`)

The catalog maps event IDs to recipient resolution logic and template names. Add new notification events here.

```python
# catalog.py — example entry
register_notification(
    catalog_id="entity.approved",
    template="record_approved.html",
    subject="Record {id} Approved",
    resolve_recipients=lambda doc, db: get_assigned_users(doc, db),
)
```

### Dispatching (`dispatcher.py`)

```python
from app.application.email_notifications.dispatcher import EmailNotificationDispatcher

await dispatcher.dispatch("entity.approved", record_id="REC-001", db=db)
```

---

## Entity Service (`entity_service.py`)

The generic CRUD orchestrator used by all entity API routes. Handles pagination, validation, type coercion, before/after hooks, and audit logging.

```python
from app.application.services.entity_service import EntityService

svc = EntityService(repo=entity_repo, rbac=rbac_service)
record = await svc.get_detail("my_entity", "REC-001", user=current_user)
records, total = await svc.get_list("my_entity", filters={}, user=current_user, page=1)
new_record = await svc.create("my_entity", data={"title": "New record"}, user=current_user)
updated = await svc.update("my_entity", "REC-001", data={"status": "Active"}, user=current_user)
```

---

## Base Entity API (`base_entity_api.py`)

Template method base class for per-entity APIs (module `apis/` files). Inherit this to get hook integration and context automatically.

```python
from app.application.services.base_entity_api import BaseEntityAPI, Context

class MyEntityAPI(BaseEntityAPI):
    entity = "my_entity"

    async def before_save(self, ctx: Context) -> None:
        if ctx.action == "create":
            await self._generate_id(ctx)

    async def after_save(self, ctx: Context) -> None:
        await self._notify_assignees(ctx)
```

---

## Shared Utilities (`utils/doc_utils.py`)

Helper functions for working with SQLAlchemy model instances or plain dicts interchangeably.

```python
from app.application.utils.doc_utils import get_id, get_attr, to_float, to_int, display_label, meta_title_value, fmt_qty

record_id = get_id(doc)
qty = to_float(doc.get("quantity"))
label = display_label(doc.get("name"), doc.get("id"))
title = meta_title_value("my_entity", doc)
```

---

## Workflow Service (`services/workflows/`)

```python
from app.application.services.workflows.workflow_service import WorkflowAppService

svc = WorkflowAppService(workflow_repo=..., entity_repo=..., rbac=...)
result = await svc.apply_action(
    entity="my_entity",
    record_id="REC-001",
    action="Approve",
    user=current_user,
    db=db,
)
```

---

## Rules for This Layer

| Rule | Detail |
|---|---|
| **No direct infrastructure imports** | All infrastructure is injected — never `from app.infrastructure.database import ...` in a service |
| **No SQLAlchemy queries** | Use repository protocols, not raw `select()` |
| **No FastAPI** | Services must not import `Request`, `Response`, `Depends`, or any FastAPI construct |
| **One responsibility per service** | EntityService does CRUD; WorkflowService does transitions — not both |
| **Hooks over conditionals** | Cross-cutting behavior belongs in hooks, not in service methods |
| **Shared utilities in `doc_utils.py`** | Do not define helpers inline in module files |
