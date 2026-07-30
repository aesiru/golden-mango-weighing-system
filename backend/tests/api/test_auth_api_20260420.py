"""API tests for authentication and profile routes."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(client):
    """Assert that the login handler returns HTTP 401 when credentials do not match a user."""
    response = await client.post(
        "/api/auth/login",
        data={"username": "missing-user", "password": "bad-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_boot_rejects_invalid_credentials(client):
    """Assert that the boot endpoint enforces the same credential checks as the login endpoint."""
    response = await client.post(
        "/api/auth/boot",
        data={"username": "missing-user", "password": "bad-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_refresh_requires_refresh_token(client):
    """Assert that the refresh endpoint rejects requests that provide neither a cookie nor a request-body token."""
    response = await client.post("/api/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing refresh token"


@pytest.mark.asyncio
async def test_validate_requires_bearer_header(client):
    """Assert that token validation returns HTTP 401 when the authorization header is missing."""
    response = await client.get("/api/auth/validate")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid authorization header"


@pytest.mark.asyncio
async def test_auth_me_requires_access_or_refresh_token(client):
    """Assert that the auth bootstrap probe returns HTTP 401 when neither access nor refresh authentication is present."""
    response = await client.get("/api/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_profile_returns_authenticated_user_payload(authenticated_client, authenticated_user):
    """Assert that the profile handler returns the current user payload when authentication is resolved through the dependency override."""
    response = await authenticated_client.get("/api/profile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["id"] == authenticated_user.id
    assert payload["data"]["username"] == authenticated_user.username
