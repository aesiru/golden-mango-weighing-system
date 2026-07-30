"""Repository tests for the generic entity repository."""

from __future__ import annotations

import pytest

from app.core.framework.models.auth import Role
from app.infrastructure.database.repositories.entity_repository import EntityRepository


@pytest.mark.asyncio
async def test_entity_repository_creates_updates_and_deletes_roles(db_session, record_id_factory):
    """Assert that EntityRepository can create, mutate, and delete a registered core entity within a single database session."""
    repository = EntityRepository(db_session)
    role_name = record_id_factory("Role")

    created = await repository.create(
        "role",
        {"id": record_id_factory("role"), "name": role_name, "description": "Created by repository test."},
    )
    await repository.update("role", created.id, {"description": "Updated description."})
    fetched = await repository.get_by_id("role", created.id)
    deleted = await repository.delete("role", created.id)
    missing = await repository.get_by_id("role", created.id)

    assert fetched is not None
    assert fetched.description == "Updated description."
    assert deleted is True
    assert missing is None


@pytest.mark.asyncio
async def test_entity_repository_applies_filters_and_pagination(db_session, record_id_factory):
    """Assert that EntityRepository list queries honor field filters and return total-count metadata for paginated list views."""
    repository = EntityRepository(db_session)
    matching_name = record_id_factory("Role")
    db_session.add_all(
        [
            Role(id=record_id_factory("role"), name=matching_name, description="Match"),
            Role(id=record_id_factory("role"), name=record_id_factory("Role"), description="Other"),
        ]
    )
    await db_session.flush()

    rows, total = await repository.get_list("role", filters={"name": matching_name}, page=1, page_size=10)

    assert total == 1
    assert len(rows) == 1
    assert rows[0]["name"] == matching_name


@pytest.mark.asyncio
async def test_entity_repository_bulk_delete_reports_partial_failures(db_session, record_id_factory):
    """Assert that EntityRepository bulk deletion reports deleted rows and missing rows separately instead of failing the whole operation."""
    repository = EntityRepository(db_session)
    role = Role(id=record_id_factory("role"), name=record_id_factory("Role"), description="Bulk delete target")
    db_session.add(role)
    await db_session.flush()

    deleted_count, failures, summary = await repository.bulk_delete(
        "role",
        [role.id, record_id_factory("missing")],
    )

    assert deleted_count == 1
    assert len(failures) == 1
    assert summary["Record not found"] == 1
