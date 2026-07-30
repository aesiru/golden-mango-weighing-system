"""Repository tests for the document repository."""

from __future__ import annotations

import pytest

from app.core.framework.models.workflow import WorkflowState
from app.infrastructure.database.repositories.document_repository import DocumentRepository


@pytest.mark.asyncio
async def test_document_repository_returns_documents_as_dicts(db_session, record_id_factory):
    """Assert that DocumentRepository can fetch a concrete ORM row and serialize it to a plain dictionary payload."""
    state = WorkflowState(id=record_id_factory("state"), label=record_id_factory("Draft"), slug=record_id_factory("draft"))
    db_session.add(state)
    await db_session.flush()

    repository = DocumentRepository(db_session)
    document = await repository.get_doc("core_workflow_states", state.id, as_dict=True)

    assert document is not None
    assert document["id"] == state.id
    assert document["label"] == state.label


@pytest.mark.asyncio
async def test_document_repository_reads_scalar_and_tuple_values(db_session, record_id_factory):
    """Assert that DocumentRepository can return both a single scalar field and a grouped tuple-style field selection."""
    state = WorkflowState(id=record_id_factory("state"), label=record_id_factory("Queued"), slug=record_id_factory("queued"))
    db_session.add(state)
    await db_session.flush()

    repository = DocumentRepository(db_session)
    label = await repository.get_value("core_workflow_states", state.id, "label")
    fields = await repository.get_value("core_workflow_states", state.id, ["label", "slug"], as_dict=True)

    assert label == state.label
    assert fields == {"label": state.label, "slug": state.slug}


@pytest.mark.asyncio
async def test_document_repository_lists_and_resolves_link_titles(db_session, record_id_factory):
    """Assert that DocumentRepository list and linked-record helpers return ordered documents and title mappings for the requested identifiers."""
    first = WorkflowState(id=record_id_factory("state"), label=record_id_factory("Approved"), slug=record_id_factory("approved"))
    second = WorkflowState(id=record_id_factory("state"), label=record_id_factory("Rejected"), slug=record_id_factory("rejected"))
    db_session.add_all([first, second])
    await db_session.flush()

    repository = DocumentRepository(db_session)
    rows = await repository.get_list(
        "core_workflow_states",
        filters=None,
        fields=["label", "slug"],
        order_by="label",
        as_dict=True,
    )
    title = await repository.get_linked_record("core_workflow_states", first.id, title_field="label")
    titles = await repository.get_linked_records("core_workflow_states", [first.id, second.id], title_field="label")

    assert any(row["label"] == first.label for row in rows)
    assert title == first.label
    assert titles[first.id] == first.label
    assert titles[second.id] == second.label
