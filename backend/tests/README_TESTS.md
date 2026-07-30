# Backend Test Suite

## Scope

This suite is organized around the backend architecture rather than end-to-end workflow scenarios.

Covered groups:

- `api/`: FastAPI route registration, public endpoint contracts, auth and profile error paths.
- `integration/`: Real local database round trips through HTTP and repository seams.
- `repositories/`: CRUD and query behavior for repository classes.
- `schemas/`: Pydantic request and payload validation.
- `infrastructure/`: Settings, middleware, application wiring, and mount configuration.

## Environment Requirements

The suite uses a real local PostgreSQL database.

By default, the shared fixtures use a configurable connection string. Override with:

- `EAM_TEST_DATABASE_URL` environment variable

The backend imports metadata and models dynamically during fixture bootstrap, so the application code must be importable from the backend root.

## Running the Suite

Run the full backend suite:

```bash
cd backend
pytest tests
```

Run a single group:

```bash
cd backend
pytest tests/api
pytest tests/integration
pytest tests/repositories
pytest tests/schemas
pytest tests/infrastructure
```

Run a single file:

```bash
cd backend
pytest tests/api/test_auth_api_20260420.py
```

## Fixture Model

The root `conftest.py` provides:

- `db_engine`: function-scoped async SQLAlchemy engine.
- `db_session`: function-scoped async session with rollback on teardown.
- `client`: async HTTP client bound to the function-scoped DB session.
- `authenticated_user`: transient superuser-backed DB record for authenticated endpoint tests.
- `authenticated_client`: async client with current-user dependency override.
- `record_id_factory`: unique ID helper for idempotent inserts.

## Design Notes

- Every test function contains a docstring describing what it asserts.
- DB-backed tests avoid permanent commits where possible to remain safe across repeated runs.
- Repository tests target stable core models such as roles, users, permissions, and workflow tables.
- API tests emphasize route contracts, auth handling, and response shape rather than business workflows.
