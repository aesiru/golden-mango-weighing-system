# Domain Layer

**Clean Architecture Position:** Innermost layer — no external dependencies.

The domain layer defines the _language_ of the system: what can go wrong (exceptions), and what contracts other layers must satisfy (protocols). Nothing here imports from FastAPI, SQLAlchemy, or any other framework.

---

## Contents

```
domain/
├── exceptions.py       # Business exception hierarchy
└── protocols/          # Typed Protocol interfaces
    ├── auth_repository.py
    ├── branding_store.py
    ├── cache_protocol.py
    ├── document_service.py
    ├── email_service.py
    ├── entity_repository.py
    ├── event_bus.py
    ├── fetch_from_repository.py
    ├── metadata_sync.py
    ├── naming_repository.py
    ├── print_assembler.py
    ├── rbac_protocol.py
    ├── serializable.py
    ├── tree.py
    ├── unit_of_work.py
    └── workflow_repository.py
```

---

## Exceptions (`exceptions.py`)

All business errors start here. Infrastructure and application layers raise these; the API layer translates them to HTTP responses.

| Exception | When to raise |
|---|---|
| `DomainException` | Base — never raise directly |
| `EntityNotFoundError(entity, identifier)` | Record does not exist |
| `ValidationError(message, field_errors)` | Business rule violation |
| `PermissionDeniedError(message, entity, action)` | RBAC check failed |
| `DuplicateRecordError(message, details)` | Unique constraint violated |
| `WorkflowError(message, current_state, action)` | Illegal state transition |

```python
from app.domain.exceptions import EntityNotFoundError, WorkflowError

raise EntityNotFoundError("my_entity", record_id)
raise WorkflowError("Cannot approve from Closed", current_state="Closed", action="Approve")
```

The API layer (`core/exceptions.py`) maps these to HTTP status codes automatically.

---

## Protocols (`protocols/`)

Protocols are pure Python `typing.Protocol` interfaces. They describe what a collaborator must be able to do, without coupling to any implementation.

### Why protocols matter

- Application services depend on protocols, not concrete classes → easy to test with mocks
- Infrastructure implementations can be swapped without touching application code
- Circular imports become impossible

### Key protocols

#### `EntityRepositoryProtocol` — Generic CRUD

```python
class EntityRepositoryProtocol(Protocol):
    async def get_by_id(self, entity: str, record_id: str) -> Any | None: ...
    async def get_list(self, entity: str, filters: dict, ...) -> tuple[list, int]: ...
    async def create(self, entity: str, data: dict, user_id: str) -> Any: ...
    async def update(self, entity: str, record_id: str, data: dict) -> Any: ...
    async def delete(self, entity: str, record_id: str) -> None: ...
```

#### `EmailServiceProtocol` — Sending (no SMTP details)

```python
class EmailServiceProtocol(Protocol):
    async def send(self, to: list[str], subject: str, body: str, ...) -> None: ...
```

#### `CacheProtocol` — Pluggable Cache

```python
class CacheProtocol(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...
```

---

## Rules for This Layer

| Rule | Reason |
|---|---|
| **No imports from `app.*` except `app.domain`** | Domain must be framework-free |
| **No SQLAlchemy, FastAPI, Pydantic models** | Pure Python only |
| **Protocols use `typing.Protocol`, not ABC** | Structural subtyping — implementations don't need to declare inheritance |
| **Exceptions carry context** | Always include entity name, action, or field in the exception |
| **No business logic** | Domain defines contracts, not algorithms |

---

## Adding a New Protocol

When application code needs a new kind of collaborator (e.g., a PDF renderer):

1. Create `domain/protocols/pdf_renderer.py`
2. Define a `typing.Protocol` with only the methods needed
3. Write the infrastructure implementation in `infrastructure/pdf/`
4. Wire it in `api/dependencies.py`

```python
# domain/protocols/pdf_renderer.py
"""
Domain Layer: PDF Renderer Protocol
Clean Architecture Layer: Domain
Responsibility: Interface for PDF generation — no rendering engine details.
"""
from typing import Protocol

class PdfRendererProtocol(Protocol):
    async def render(self, template: str, context: dict) -> bytes: ...
```

---

## Testing

Because protocols are pure Python, application services that depend on them can be tested without a database or SMTP server:

```python
from unittest.mock import AsyncMock
from app.application.services.entity_service import EntityService

async def test_create_entity():
    mock_repo = AsyncMock()
    mock_repo.create.return_value = {"id": "REC-001", "name": "Test"}
    svc = EntityService(repo=mock_repo, rbac=AsyncMock())
    result = await svc.create("my_entity", {"name": "Test"}, user_id="1")
    assert result["id"] == "REC-001"
```
