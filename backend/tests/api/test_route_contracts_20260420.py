"""API tests for route registration and public HTTP contracts."""

from __future__ import annotations

from fastapi.routing import APIRoute
import pytest


def test_api_routes_are_registered_under_expected_prefixes():
    """Assert that the FastAPI application mounts the consolidated backend routes under the expected API namespaces."""
    from app.main import fastapi_app

    api_paths = [route.path for route in fastapi_app.routes if isinstance(route, APIRoute) and route.path.startswith("/api")]

    assert api_paths
    assert any(path.startswith("/api/entity") for path in api_paths)
    assert any(path.startswith("/api/auth") for path in api_paths)
    assert any(path.startswith("/api/meta") for path in api_paths)
    assert any(path.startswith("/api/health") for path in api_paths)
    assert any(path.startswith("/api/version") for path in api_paths)
    assert any(path.startswith("/api/features") for path in api_paths)


def test_api_route_names_are_unique():
    """Assert that API route names remain unique so reverse lookups and diagnostics stay deterministic."""
    from app.main import fastapi_app

    route_names = [route.name for route in fastapi_app.routes if isinstance(route, APIRoute) and route.path.startswith("/api")]

    assert len(route_names) == len(set(route_names))


@pytest.mark.asyncio
async def test_health_endpoint_exposes_status_and_database_check(client):
    """Assert that the health endpoint returns the aggregate readiness payload expected by monitoring checks."""
    response = await client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"healthy", "degraded"}
    assert "database" in payload["checks"]


@pytest.mark.asyncio
async def test_version_endpoint_exposes_runtime_metadata(client):
    """Assert that the version endpoint returns the application name, semantic version, and environment marker."""
    response = await client.get("/api/version")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"name", "version", "environment"}


@pytest.mark.asyncio
async def test_meta_modules_endpoint_returns_module_metadata(client):
    """Assert that the modules metadata endpoint exposes the label and icon maps used by the frontend shell."""
    response = await client.get("/api/meta/modules")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert "labels" in payload["data"]
    assert "icons" in payload["data"]


@pytest.mark.asyncio
async def test_meta_list_returns_empty_data_for_anonymous_requests(client):
    """Assert that anonymous metadata listing requests return a successful empty payload instead of leaking entity definitions."""
    response = await client.get("/api/meta")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"] == []
