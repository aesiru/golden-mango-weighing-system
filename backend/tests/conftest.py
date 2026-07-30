"""Shared fixtures for the backend test suite."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.framework.models.auth import Role, User
from app.core.loader import load_modules
from app.core.security import CurrentUser, get_current_user_from_token, get_password_hash
from app.entities import load_all_entities
from app.infrastructure.database.repositories.entity_repository import register_core_models


load_modules()
load_all_entities()
register_core_models()


TEST_DATABASE_URL = os.getenv(
    "EAM_TEST_DATABASE_URL",
    "postgresql+asyncpg://eam_f0bca4fc7e9b:McWGzwqJFnwzM30QrJKMxpCo8eldtctmsu8lE2KFxw@localhost:5432/eam_f0bca4fc7e9b",
)


@pytest.fixture
def record_id_factory():
    """Return a helper that generates deterministic-enough unique test identifiers."""

    def factory(prefix: str) -> str:
        return f"{prefix}-{uuid4().hex[:8]}"

    return factory


@pytest_asyncio.fixture
async def db_engine():
    """Create a shared async engine for the local PostgreSQL test database."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    """Yield a function-scoped async session and roll back uncommitted state after each test."""
    session_maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """Yield an async HTTP client that uses the function-scoped database session."""
    from app.core import database as app_database
    from app.core.database import get_db
    from app.main import fastapi_app

    async def override_get_db():
        yield db_session

    await app_database.engine.dispose()
    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
    fastapi_app.dependency_overrides.clear()
    await app_database.engine.dispose()


@pytest_asyncio.fixture
async def authenticated_user(db_session: AsyncSession, record_id_factory) -> User:
    """Create a function-scoped user record that can back authenticated HTTP tests."""
    role = Role(
        id=record_id_factory("role"),
        name=record_id_factory("Role"),
        description="Role for backend test authentication.",
        is_active=True,
    )
    user = User(
        id=record_id_factory("user"),
        username=record_id_factory("tester"),
        email=f"{uuid4().hex[:10]}@example.com",
        full_name="Backend Test User",
        hashed_password=get_password_hash("secret123"),
        is_active=True,
        is_superuser=True,
    )
    user.roles.append(role)
    db_session.add_all([role, user])
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, authenticated_user: User) -> AsyncClient:
    """Yield an async client that resolves the current user from an override instead of a JWT."""
    from app.main import fastapi_app

    async def override_current_user():
        return CurrentUser(
            id=authenticated_user.id,
            username=authenticated_user.username,
            roles=[role.name for role in authenticated_user.roles],
            role_ids=[role.id for role in authenticated_user.roles],
            is_superuser=authenticated_user.is_superuser,
        )

    fastapi_app.dependency_overrides[get_current_user_from_token] = override_current_user
    try:
        yield client
    finally:
        fastapi_app.dependency_overrides.pop(get_current_user_from_token, None)


# ---------------------------------------------------------------------------
# Superuser client: logs in with the real Administrator account so every
# entity CRUD request carries a valid JWT.  The entity_crud.py handler calls
# get_current_user_from_token() as a plain function (not via Depends), so the
# authenticated_client override does not reach it.  This fixture works around
# that by obtaining a real token through the test client itself.
# ---------------------------------------------------------------------------

ADMIN_USERNAME = "Administrator"
ADMIN_PASSWORD = "yTonJATR"


@pytest_asyncio.fixture
async def superuser_client(client: AsyncClient) -> AsyncClient:
    """Yield an async client that carries a real Administrator JWT.

    The token is obtained via /api/auth/login through the same test client,
    so all requests (login + entity actions) share the same function-scoped
    database session and the session rollback still applies at test teardown.
    """
    # /api/auth/login uses OAuth2PasswordRequestForm → must send form data
    response = await client.post(
        "/api/auth/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, (
        f"superuser_client: login failed with HTTP {response.status_code}: {response.text}"
    )
    payload = response.json()
    # Login returns {"access_token": "...", ...} at the top level
    token = payload.get("access_token")
    assert token, f"superuser_client: no access_token in login response: {payload}"

    client.headers = {**client.headers, "Authorization": f"Bearer {token}"}
    return client