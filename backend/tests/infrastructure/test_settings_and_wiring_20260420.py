"""Infrastructure tests for settings, middleware, and application wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.responses import Response

from app.api import dependencies
from app.application.services.access_control.rbac_service import RBACAppService
from app.application.services.documents.document_service import DocumentAppService
from app.application.services.entity_service import EntityService
from app.core.config import Settings, settings
from app.infrastructure.database.repositories.auth_repository import AuthRepository
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.entity_repository import EntityRepository
from app.main import TimingMiddleware, fastapi_app


def test_sync_database_url_property_converts_async_urls():
    """Assert that Settings.sync_database_url converts async SQLAlchemy URLs into the sync variants required by migration tooling."""
    config = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/eam")

    assert config.sync_database_url == "postgresql://user:pass@localhost:5432/eam"


def test_socketio_cors_origins_falls_back_to_http_cors_origins():
    """Assert that socket.io CORS origins default to the standard HTTP CORS origin list when no dedicated override is configured."""
    config = Settings(CORS_ORIGINS=["http://localhost:3000"], SOCKETIO_CORS_ORIGINS=None)

    assert config.socketio_cors_origins == ["http://localhost:3000"]


@pytest.mark.asyncio
async def test_timing_middleware_passes_through_response():
    """Assert that TimingMiddleware returns the downstream response unchanged after timing the request."""
    middleware = TimingMiddleware(app=AsyncMock())
    request = Request({"type": "http", "method": "GET", "path": "/health", "headers": []})

    async def call_next(_: Request) -> Response:
        return Response(content="ok", status_code=204)

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 204


def test_dependency_factories_return_expected_service_types(db_session):
    """Assert that the API dependency builders wire infrastructure repositories into the expected application service types."""
    entity_repo = EntityRepository(db_session)
    document_repo = DocumentRepository(db_session)
    auth_repo = AuthRepository(db_session)

    entity_service = dependencies.get_entity_service(
        entity_repo=entity_repo,
        naming_repo=dependencies.get_naming_repo(db=db_session),
        workflow_repo=dependencies.get_workflow_repo(db=db_session),
        auth_repo=auth_repo,
    )
    document_service = dependencies.get_document_service(document_repo=document_repo)
    rbac_service = dependencies.get_rbac_service(auth_repo=auth_repo)

    assert isinstance(entity_service, EntityService)
    assert isinstance(document_service, DocumentAppService)
    assert isinstance(rbac_service, RBACAppService)


def test_fastapi_app_mounts_uploads_and_api_routes():
    """Assert that the main FastAPI application exposes both the static uploads mount and the consolidated API router."""
    route_paths = [route.path for route in fastapi_app.routes if isinstance(route, APIRoute)]
    mount_paths = [route.path for route in fastapi_app.routes if not isinstance(route, APIRoute)]

    assert "/uploads" in mount_paths
    assert any(path.startswith("/api/") for path in route_paths)
    assert settings.UPLOAD_DIR
