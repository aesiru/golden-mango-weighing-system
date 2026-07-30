"""Repository tests for auth and workflow persistence helpers."""

from __future__ import annotations

import pytest

from app.core.framework.models.auth import EntityPermission, Role, User
from app.core.framework.models.workflow import Workflow, WorkflowAction, WorkflowState, WorkflowStateLink, WorkflowTransition, generate_slug
from app.infrastructure.database.repositories.auth_repository import AuthRepository
from app.infrastructure.database.repositories.workflow_repository import WorkflowRepository


@pytest.mark.asyncio
async def test_auth_repository_loads_user_roles_and_permissions(db_session, record_id_factory):
    """Assert that AuthRepository returns a user together with the linked roles and matching entity permission rows."""
    role = Role(id=record_id_factory("role"), name=record_id_factory("Role"), description="Auth repository role")
    user = User(
        id=record_id_factory("user"),
        username=record_id_factory("authuser"),
        email=f"{record_id_factory('mail')}@example.com",
        full_name="Auth Repository User",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
    )
    permission = EntityPermission(
        id=record_id_factory("perm"),
        role_id=role.id,
        entity_name="role",
        can_read=True,
        can_create=True,
    )
    user.roles.append(role)
    db_session.add_all([role, user, permission])
    await db_session.flush()

    repository = AuthRepository(db_session)
    loaded_user = await repository.get_user_by_username(user.username)
    role_names = await repository.get_user_roles(user.id)
    loaded_permission = await repository.get_permission_for_role_and_entity(role.id, "role")

    assert loaded_user is not None
    assert loaded_user.username == user.username
    assert role.name in role_names
    assert loaded_permission is not None
    assert loaded_permission.can_create is True


@pytest.mark.asyncio
async def test_workflow_repository_returns_initial_state_and_valid_transition(db_session, record_id_factory):
    """Assert that WorkflowRepository reads the initial state and validates a configured transition for an entity workflow."""
    draft = WorkflowState(id=record_id_factory("state"), label=record_id_factory("Draft"), slug=record_id_factory("draft"))
    approved = WorkflowState(id=record_id_factory("state"), label=record_id_factory("Approved"), slug=record_id_factory("approved"))
    action_label = record_id_factory("Approve")
    action_slug = generate_slug(action_label)
    action = WorkflowAction(id=record_id_factory("action"), label=action_label, slug=action_slug)
    workflow = Workflow(id=record_id_factory("workflow"), name=record_id_factory("Workflow"), target_entity=record_id_factory("entity"), is_active=True)
    draft_link = WorkflowStateLink(id=record_id_factory("link"), workflow_id=workflow.id, state_id=draft.id, is_initial=True, sort_order=1)
    approved_link = WorkflowStateLink(id=record_id_factory("link"), workflow_id=workflow.id, state_id=approved.id, is_initial=False, sort_order=2)
    transition = WorkflowTransition(
        id=record_id_factory("transition"),
        workflow_id=workflow.id,
        from_state_id=draft.id,
        action_id=action.id,
        to_state_id=approved.id,
        sort_order=1,
    )
    db_session.add_all([draft, approved, action, workflow, draft_link, approved_link, transition])
    await db_session.flush()

    repository = WorkflowRepository(db_session)
    initial_state = await repository.get_initial_state(workflow.target_entity)
    is_valid, target_state, error = await repository.validate_transition(workflow.target_entity, draft.slug, action_slug)

    assert initial_state == draft.slug
    assert is_valid is True
    assert target_state == approved.slug
    assert error is None
