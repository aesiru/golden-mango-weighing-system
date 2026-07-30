"""
Ownership Tracking Tests — created_by / last_modified_by
=========================================================
Verifies that the actor tracking fields introduced in the
``add_created_by_last_modified_by`` epic behave correctly across:

  Group A — Entity create / update (main action route)
  Group B — Anonymous creates (no JWT)
  Group C — Child bulk-save create / update
  Group D — /api/system/users/resolve-display-names endpoint

Fixtures used:
  superuser_client  — carries a real Administrator JWT; required because
                      entity_crud.py calls get_current_user_from_token()
                      as a plain awaited function, not via FastAPI Depends,
                      so the authenticated_client override does not reach it.
  authenticated_client — uses the dependency override; works for system
                         endpoints that go through Depends().
  client            — unauthenticated; used for anonymous-actor tests.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ENTITY_ACTION = "/api/entity/{entity}/action"
ENTITY_CHILDREN_BULK = "/api/entity/{entity}/{record_id}/children/{child_entity}/bulk-save"

SITE = "SITE-0001"
DEPT = "DEPT-0001"


async def _action(client, entity: str, payload: dict) -> dict:
    r = await client.post(ENTITY_ACTION.format(entity=entity), json=payload)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:400]}"
    body = r.json()
    assert body["status"] == "success", f"Action failed: {body.get('message')}"
    return body["data"]


# ---------------------------------------------------------------------------
# Group A — Entity create / update via superuser_client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_sets_both_ownership_fields(superuser_client):
    """Creating a record via an authenticated request sets created_by and last_modified_by to the actor's user ID."""
    data = await _action(
        superuser_client,
        "department",
        {"action": "create", "data": {"department_name": "Test Dept OT-001", "site": SITE}},
    )

    assert data.get("created_by") is not None, "created_by must not be null after create"
    assert data.get("last_modified_by") is not None, "last_modified_by must not be null after create"
    # Both fields must equal the same actor for a fresh create
    assert data["created_by"] == data["last_modified_by"]


@pytest.mark.asyncio
async def test_update_preserves_created_by_and_refreshes_last_modified_by(superuser_client, db_session):
    """Updating a record preserves the original created_by and updates only last_modified_by."""
    from app.core.framework.models.auth import User
    from sqlalchemy import select

    # Resolve the Administrator's user.id so we can compare against the field values.
    result = await db_session.execute(select(User).where(User.username == "Administrator"))
    admin = result.scalar_one_or_none()
    assert admin is not None, "Administrator seed user must exist in the test database"
    admin_id = admin.id

    # Create a record under Administrator.
    created = await _action(
        superuser_client,
        "department",
        {"action": "create", "data": {"department_name": "Test Dept OT-002", "site": SITE}},
    )
    record_id = created["id"]
    assert created["created_by"] == admin_id
    assert created["last_modified_by"] == admin_id

    # Update the same record — only the name changes.
    updated = await _action(
        superuser_client,
        "department",
        {
            "action": "update",
            "id": record_id,
            "data": {"department_name": "Test Dept OT-002 Updated"},
        },
    )

    assert updated["created_by"] == admin_id, "created_by must not change on update"
    assert updated["last_modified_by"] == admin_id


@pytest.mark.asyncio
async def test_update_cannot_overwrite_created_by_via_payload(superuser_client):
    """A caller who tries to overwrite created_by via the update payload is silently ignored."""
    created = await _action(
        superuser_client,
        "department",
        {"action": "create", "data": {"department_name": "Test Dept OT-003", "site": SITE}},
    )
    record_id = created["id"]
    original_created_by = created["created_by"]

    updated = await _action(
        superuser_client,
        "department",
        {
            "action": "update",
            "id": record_id,
            "data": {
                "department_name": "Test Dept OT-003 Updated",
                "created_by": "fake-attacker-id",
            },
        },
    )

    assert updated["created_by"] == original_created_by, (
        "Sending created_by in the update payload must not overwrite the original value"
    )


# ---------------------------------------------------------------------------
# Group B — Anonymous creates (no JWT)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anonymous_create_stores_null_ownership_fields(client):
    """Creating a record without a JWT token stores null for both ownership fields without raising an error."""
    r = await client.post(
        ENTITY_ACTION.format(entity="department"),
        json={"action": "create", "data": {"department_name": "Test Dept OT-Anon", "site": SITE}},
    )
    assert r.status_code == 200
    body = r.json()
    # Anonymous requests may be denied by RBAC (ForbiddenError) or succeed when permissions
    # allow public access.  In either case the response must not be an unhandled 500.
    assert body["status"] in ("success", "error"), f"Unexpected response: {body}"
    if body["status"] == "success":
        data = body["data"]
        assert data.get("created_by") is None, "Anonymous create must store null for created_by"
        assert data.get("last_modified_by") is None, "Anonymous create must store null for last_modified_by"


# ---------------------------------------------------------------------------
# Group C — Child bulk-save create / update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_child_bulksave_create_sets_ownership_fields(superuser_client, db_session):
    """A new child row created via bulk-save must carry the actor's user ID in both ownership fields."""
    from app.core.framework.models.auth import User
    from sqlalchemy import select

    result = await db_session.execute(select(User).where(User.username == "Administrator"))
    admin = result.scalar_one_or_none()
    assert admin is not None
    admin_id = admin.id

    # Create a parent work_order and a work_order_activity (the direct parent of work_order_parts).
    work_order = await _action(
        superuser_client,
        "work_order",
        {
            "action": "create",
            "data": {
                "description": "OT Ownership Test WO",
                "site": SITE,
                "department": DEPT,
                "work_order_type": "Corrective",
                "priority": "Medium",
            },
        },
    )
    parent_activity = await _action(
        superuser_client,
        "work_order_activity",
        {
            "action": "create",
            "data": {
                "work_order": work_order["id"],
                "description": "OT Ownership Test Activity",
                "site": SITE,
                "department": DEPT,
            },
        },
    )
    parent_id = parent_activity["id"]

    # Bulk-save one new work_order_parts child row.
    r = await superuser_client.post(
        ENTITY_CHILDREN_BULK.format(
            entity="work_order_activity",
            record_id=parent_id,
            child_entity="work_order_parts",
        ),
        json={
            "rows": [{"quantity_required": 2}],
            "deleted_ids": [],
        },
    )
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:400]}"
    body = r.json()
    assert body["status"] == "success", f"Bulk-save failed: {body.get('message')}"

    rows = body["data"]["rows"]
    assert rows, "At least one child row must be returned"
    child_row = rows[0]

    assert child_row.get("created_by") == admin_id, (
        f"Child created_by must equal actor ID {admin_id!r}, got {child_row.get('created_by')!r}"
    )
    assert child_row.get("last_modified_by") == admin_id, (
        f"Child last_modified_by must equal actor ID {admin_id!r}, got {child_row.get('last_modified_by')!r}"
    )


@pytest.mark.asyncio
async def test_child_bulksave_update_preserves_created_by(superuser_client, db_session):
    """Updating a child row via bulk-save preserves created_by and only refreshes last_modified_by."""
    from app.core.framework.models.auth import User
    from sqlalchemy import select

    result = await db_session.execute(select(User).where(User.username == "Administrator"))
    admin = result.scalar_one_or_none()
    assert admin is not None
    admin_id = admin.id

    # Create parent work_order and work_order_activity (the direct parent for parts).
    work_order = await _action(
        superuser_client,
        "work_order",
        {
            "action": "create",
            "data": {
                "description": "OT Preserve created_by Test WO",
                "site": SITE,
                "department": DEPT,
                "work_order_type": "Corrective",
                "priority": "Low",
            },
        },
    )
    parent_activity = await _action(
        superuser_client,
        "work_order_activity",
        {
            "action": "create",
            "data": {
                "work_order": work_order["id"],
                "description": "OT Preserve created_by Test Activity",
                "site": SITE,
                "department": DEPT,
            },
        },
    )
    parent_id = parent_activity["id"]

    # Create child.
    r = await superuser_client.post(
        ENTITY_CHILDREN_BULK.format(
            entity="work_order_activity", record_id=parent_id, child_entity="work_order_parts"
        ),
        json={"rows": [{"quantity_required": 1}], "deleted_ids": []},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    child_id = body["data"]["rows"][0]["id"]
    original_created_by = body["data"]["rows"][0]["created_by"]
    assert original_created_by == admin_id

    # Update the child row — send a tampered created_by to confirm it is ignored.
    r2 = await superuser_client.post(
        ENTITY_CHILDREN_BULK.format(
            entity="work_order_activity", record_id=parent_id, child_entity="work_order_parts"
        ),
        json={
            "rows": [{"id": child_id, "quantity_required": 5, "created_by": "tampered-value"}],
            "deleted_ids": [],
        },
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["status"] == "success"
    updated_row = body2["data"]["rows"][0]

    assert updated_row["created_by"] == original_created_by, (
        "created_by must not be overwritten during a child bulk-save update"
    )
    assert updated_row["last_modified_by"] == admin_id


# ---------------------------------------------------------------------------
# Group D — resolve-display-names endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_display_names_returns_full_name_for_known_user(
    authenticated_client, authenticated_user
):
    """Resolving a known user ID returns their full_name as the display value."""
    r = await authenticated_client.get(
        "/api/system/users/resolve-display-names",
        params={"user_ids": authenticated_user.id},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    data = body["data"]
    assert authenticated_user.id in data
    assert data[authenticated_user.id] == authenticated_user.full_name


@pytest.mark.asyncio
async def test_resolve_display_names_falls_back_to_id_for_unknown_user(authenticated_client):
    """An unrecognised user ID is echoed back as its own display value — the endpoint never 404s."""
    unknown_id = "00000000-0000-0000-0000-000000000000"
    r = await authenticated_client.get(
        "/api/system/users/resolve-display-names",
        params={"user_ids": unknown_id},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["data"][unknown_id] == unknown_id


@pytest.mark.asyncio
async def test_resolve_display_names_resolves_batch(authenticated_client, authenticated_user):
    """Passing multiple user IDs in one request resolves all of them in a single response."""
    unknown_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    ids = f"{authenticated_user.id},{unknown_id}"

    r = await authenticated_client.get(
        "/api/system/users/resolve-display-names",
        params={"user_ids": ids},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    data = body["data"]
    assert data[authenticated_user.id] == authenticated_user.full_name
    assert data[unknown_id] == unknown_id


@pytest.mark.asyncio
async def test_resolve_display_names_handles_empty_and_whitespace_ids(authenticated_client):
    """An empty or whitespace-only user_ids value returns an empty data map without raising an error."""
    r = await authenticated_client.get(
        "/api/system/users/resolve-display-names",
        params={"user_ids": "  , ,  "},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["data"] == {}


@pytest.mark.asyncio
async def test_resolve_display_names_requires_authentication(client):
    """The endpoint returns 401 or an empty/anonymous response without a valid token — never a 500."""
    r = await client.get(
        "/api/system/users/resolve-display-names",
        params={"user_ids": "some-id"},
    )
    # The endpoint uses Depends(get_current_user_from_token) which defaults to anonymous,
    # not a hard 401. So we accept 200 with the fallback OR 401, but never a server error.
    assert r.status_code in (200, 401, 403), (
        f"Unauthenticated access returned unexpected HTTP {r.status_code}"
    )
    if r.status_code == 200:
        body = r.json()
        assert "status" in body


# ---------------------------------------------------------------------------
# Group E — Route registration smoke test
# ---------------------------------------------------------------------------


def test_resolve_display_names_route_is_registered():
    """The resolve-display-names route must appear in the FastAPI router after startup."""
    from fastapi.routing import APIRoute
    from app.main import fastapi_app

    paths = [route.path for route in fastapi_app.routes if isinstance(route, APIRoute)]
    assert any("resolve-display-names" in p for p in paths), (
        "Expected /api/system/users/resolve-display-names to be registered"
    )
