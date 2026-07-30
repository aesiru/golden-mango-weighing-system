"""Schema tests for shared API request and response models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas.base import ActionRequest, ActionResponse, ListResponse, WorkflowRequest


def test_action_request_accepts_optional_children_payload():
    """Assert that ActionRequest accepts the nested children payload used by bulk child-row operations."""
    request = ActionRequest(
        action="create",
        id="ROLE-001",
        data={"name": "Planner"},
        children={"role_permission": {"rows": [], "deleted_ids": []}},
    )

    assert request.action == "create"
    assert request.children is not None
    assert "role_permission" in request.children


def test_action_response_preserves_arbitrary_data_payloads():
    """Assert that ActionResponse keeps arbitrary typed payloads so handlers can return structured result data."""
    response = ActionResponse(status="success", message="Created", data={"id": "ROLE-001"})

    assert response.status == "success"
    assert response.data == {"id": "ROLE-001"}


def test_workflow_request_requires_record_identifier():
    """Assert that WorkflowRequest rejects payloads that omit the target record identifier."""
    with pytest.raises(ValidationError):
        WorkflowRequest(action="approve")


def test_list_response_tracks_pagination_contract():
    """Assert that ListResponse stores the list payload together with total-count and pagination metadata."""
    response = ListResponse(status="success", data=[{"id": "ROLE-001"}], total=1, page=1, page_size=20)

    assert response.total == 1
    assert response.page == 1
    assert response.page_size == 20
