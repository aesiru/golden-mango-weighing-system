"""Real-database integration tests for HTTP endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_db_endpoint_reports_live_database_connection(client):
    """Assert that the database health probe can reach the configured local PostgreSQL instance without any mocking."""
    response = await client.get("/api/health/db")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["version"]


@pytest.mark.asyncio
async def test_profile_endpoint_reads_user_from_real_database(authenticated_client, authenticated_user):
    """Assert that the profile route reads the authenticated user record from the real database session bound into the test client."""
    response = await authenticated_client.get("/api/profile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["email"] == authenticated_user.email


@pytest.mark.asyncio
async def test_meta_modules_endpoint_roundtrips_against_live_application_state(client):
    """Assert that the modules metadata endpoint returns the current label and icon registry using the live app and database wiring."""
    response = await client.get("/api/meta/modules")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["labels"]["core"] == "Core"
