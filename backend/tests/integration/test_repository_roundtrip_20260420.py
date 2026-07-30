"""Real-database integration tests for repository round trips."""

from __future__ import annotations

import pytest

from app.core.framework.models.workflow import generate_slug
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.entity_repository import EntityRepository
from app.infrastructure.database.repositories.workflow_repository import WorkflowRepository
from app.core.framework.models.workflow import Workflow, WorkflowAction, WorkflowState, WorkflowStateLink, WorkflowTransition


@pytest.mark.asyncio
async def test_entity_and_document_repositories_share_the_same_transaction(db_session, record_id_factory):
    """Assert that a row created through EntityRepository is immediately visible to DocumentRepository inside the same database session."""
    entity_repository = EntityRepository(db_session)
    document_repository = DocumentRepository(db_session)
    created = await entity_repository.create(
        "role",
        {
            "id": record_id_factory("role"),
            "name": record_id_factory("Role"),
            "description": "Round-trip through two repository abstractions.",
        },
    )

    document = await document_repository.get_doc("core_roles", created.id, as_dict=True)

    assert document is not None
    assert document["name"] == created.name


@pytest.mark.asyncio
async def test_workflow_repository_validates_transitions_against_real_rows(db_session, record_id_factory):
    """Assert that WorkflowRepository validates a transition using workflow rows inserted into the real local database."""
    entity_name = record_id_factory("entity")
    draft = WorkflowState(id=record_id_factory("state"), label=record_id_factory("Draft"), slug=record_id_factory("draft"))
    complete = WorkflowState(id=record_id_factory("state"), label=record_id_factory("Complete"), slug=record_id_factory("complete"))
    action_label = record_id_factory("Complete")
    action = WorkflowAction(id=record_id_factory("action"), label=action_label, slug=generate_slug(action_label))
    workflow = Workflow(id=record_id_factory("workflow"), name=record_id_factory("Workflow"), target_entity=entity_name, is_active=True)
    db_session.add_all(
        [
            draft,
            complete,
            action,
            workflow,
            WorkflowStateLink(id=record_id_factory("link"), workflow_id=workflow.id, state_id=draft.id, is_initial=True, sort_order=1),
            WorkflowStateLink(id=record_id_factory("link"), workflow_id=workflow.id, state_id=complete.id, is_initial=False, sort_order=2),
            WorkflowTransition(
                id=record_id_factory("transition"),
                workflow_id=workflow.id,
                from_state_id=draft.id,
                action_id=action.id,
                to_state_id=complete.id,
                sort_order=1,
            ),
        ]
    )
    await db_session.flush()

    repository = WorkflowRepository(db_session)
    is_valid, target_state, error = await repository.validate_transition(entity_name, draft.slug, action.slug)

    assert is_valid is True
    assert target_state == complete.slug
    assert error is None
