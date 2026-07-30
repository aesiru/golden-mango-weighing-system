# Backend — FastAPI Nuxt Starter

> **For new developers:** Read this document first, then navigate to the layer README that matches your task.

This backend follows **Clean Architecture** with SOLID principles. All code lives in one of six layers, each with a strict responsibility. Layers depend inward only — outer layers know about inner ones, never the reverse.

---

## Layer Map

```
┌─────────────────────────────────────────────────────┐
│  API Layer          (api/)                          │  ← HTTP boundary, FastAPI routes
├─────────────────────────────────────────────────────┤
│  Modules Layer      (modules/)                      │  ← Domain feature units
├─────────────────────────────────────────────────────┤
│  Application Layer  (application/)                  │  ← Use-case orchestration
├─────────────────────────────────────────────────────┤
│  Infrastructure Layer (infrastructure/)             │  ← DB, email, storage, scheduler
├─────────────────────────────────────────────────────┤
│  Core Layer         (core/)                         │  ← Config, security, framework
├─────────────────────────────────────────────────────┤
│  Domain Layer       (domain/)                       │  ← Pure Python: protocols, exceptions
└─────────────────────────────────────────────────────┘
```

**Dependency Rule:** `API → Application → Infrastructure → Domain`. Domain has zero external imports. Infrastructure never imports from Application.

---

## Directory Structure

```
backend/app/
├── README.md               ← You are here
│
├── main.py                 # FastAPI app factory, lifespan, middleware
├── forge.py                # Forge CLI (entity generation, migrations)
│
├── domain/                 # LAYER 1 — Innermost layer
│   ├── README.md
│   ├── exceptions.py       # Business exception hierarchy
│   └── protocols/          # typed Protocol interfaces (dependency inversion)
│
├── core/                   # LAYER 2 — Foundation (config, security, ORM base)
│   ├── README.md
│   ├── config.py           # Pydantic settings from env
│   ├── database.py         # SQLAlchemy async engine + session
│   ├── security.py         # JWT auth, CurrentUser
│   ├── base_model.py       # ORM base with id/created_at/updated_at
│   ├── exceptions.py       # HTTP exception wrappers
│   ├── error_handlers.py   # @handle_api_errors decorator
│   ├── feature_flags.py    # Runtime feature toggles
│   ├── loader.py           # Dynamic module import
│   ├── sanitization.py     # XSS string cleaning
│   ├── seed.py             # Seed facade
│   ├── serialization.py    # record_to_dict
│   ├── framework/          # Core entity models (User, Role, Workflow…)
│   └── seeds/              # Idempotent DB seeders
│
├── infrastructure/         # LAYER 3 — External adapters
│   ├── README.md
│   ├── auth/               # JWTService, PasswordService
│   ├── cache/              # TTLCache, PermissionCache
│   ├── database/           # SQLAlchemy repos + UoW
│   │   └── repositories/   # Repository implementations
│   ├── email/              # SmtpEmailService, notification_factory
│   ├── events/             # DomainEventBus
│   ├── logging/            # email_logger, job_logger
│   ├── metadata/           # JSON reader/writer/validator, model generator
│   ├── print/              # Print assemblers
│   ├── scheduler/          # APScheduler adapter
│   ├── settings/           # BrandingStore (JSON file)
│   └── storage/            # LocalStorage / S3 (pluggable)
│
├── application/            # LAYER 4 — Use-case orchestration
│   ├── README.md
│   ├── dto.py              # PaginatedResult, ActionResult
│   ├── hooks/              # @before_save, @after_save, @workflow registry
│   ├── email_notifications/ # Event catalog + dispatcher
│   ├── utils/              # Shared doc helpers
│   └── services/           # Business service implementations
│
├── modules/                # LAYER 5 — Domain feature units
│   ├── README.md
│   └── core/               # Core framework entities and workflow support
│
├── api/                    # LAYER 6 — HTTP boundary
│   ├── README.md
│   ├── dependencies.py     # All FastAPI Depends() factories
│   ├── router.py           # Route group consolidation
│   ├── entries/            # Generic entity CRUD kernel
│   ├── features/           # Product features
│   ├── system/             # Admin & infrastructure endpoints
│   └── schemas/            # Pydantic request/response models
│
├── entities/               # Entity metadata loader
├── meta/                   # Metadata registry
└── templates/              # Jinja2 email + print templates
```

---

## Dependency Injection Pattern

All services are wired at the API boundary via `api/dependencies.py`. No service instantiates its own dependencies.

```python
# api/dependencies.py
async def get_entity_service(db: AsyncSession = Depends(get_db)):
    repo = EntityRepository(db)
    rbac = RBACAppService(AuthRepository(db), PermissionCache())
    return EntityService(repo, rbac)
```

Routes receive fully wired services via `Depends()`. Services never know where their dependencies come from.

---

## Hook System

Business rules that react to record saves and workflow transitions are registered as hooks — not hardcoded in routes.

```python
# modules/<module>/hooks.py
from app.application.hooks.registry import hook_registry

@hook_registry.before_save("my_entity")
async def validate_my_entity(ctx: SaveContext):
    ...

@hook_registry.workflow("work_order")
async def on_work_order_approved(ctx: WorkflowContext):
    ...
```

Hooks are auto-discovered by the module loader on startup.

---

## Adding a New Entity

```bash
# 1. Scaffold the entity
python -m app.forge new-entity my_entity \
  --module my_module \
  --fields "name:string,status:select,quantity:float"

# 2. Apply the migration
python -m app.forge sync
```

The JSON definition drives: API routing, list/detail views, form fields, workflow, permissions. No route code is needed for standard CRUD.

---

## Forge CLI Reference

Run from `backend/` with the virtualenv active.

| Command | Description |
|---|---|
| `python -m app.forge sync` | Generate models + migration + apply (one step) |
| `python -m app.forge new-entity NAME --module MOD --fields "..."` | Scaffold new entity |
| `python -m app.forge migrate --status` | View pending migrations |
| `python -m app.forge migrate --apply-only` | Apply without generating |
| `python -m app.forge migrate --rollback N` | Roll back N migrations |
| `python -m app.forge status` | System status (modules, entities, DB) |

**Field types:** `string`, `int`, `float`, `boolean`, `date`, `datetime`, `text`, `select`, `multiselect`, `link`, `json`

---

## Layer READMEs

Each layer has its own README with conventions, rules, and examples:

| Layer | README |
|---|---|
| Domain | [domain/README.md](domain/README.md) |
| Core | [core/README.md](core/README.md) |
| Infrastructure | [infrastructure/README.md](infrastructure/README.md) |
| Application | [application/README.md](application/README.md) |
| Modules | [modules/README.md](modules/README.md) |
| API | [api/README.md](api/README.md) |

---

## Key Rules (Quick Reference)

| Rule | Detail |
|---|---|
| **No infrastructure in application** | Application services receive repos/services via constructor injection |
| **No application in infrastructure** | Infrastructure adapters may consume application formatters/resolvers, not services |
| **Domain has zero imports** | `domain/` contains only `typing`, `dataclasses`, `abc` |
| **All DB access via repositories** | Never write SQLAlchemy queries outside `infrastructure/database/repositories/` |
| **All DI wired in `dependencies.py`** | Routes never instantiate services; always use `Depends()` |
| **Hooks over if/elif** | Business logic on save/workflow must use the hook registry |
| **One source of truth for utilities** | Shared doc helpers live in `application/utils/doc_utils.py` only |
