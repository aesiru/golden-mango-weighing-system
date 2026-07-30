"""
Workflow Service (Application Layer)
======================================
Orchestrates workflow transitions.
Delegates DB access to WorkflowRepository.
"""
from typing import Any, Optional

from app.domain.exceptions import WorkflowError, EntityNotFoundError


class WorkflowAppService:
    """Application-layer workflow orchestration."""

    def __init__(self, workflow_repo, entity_repo):
        self.workflow_repo = workflow_repo
        self.entity_repo = entity_repo

    async def get_workflow_meta(self, entity: str) -> Optional[dict]:
        """Get workflow metadata for frontend."""
        workflow = await self.workflow_repo.get_workflow(entity)
        if not workflow:
            return None

        initial_link = next((sl for sl in workflow.state_links if sl.is_initial), None)
        initial_state_slug = initial_link.state.slug if initial_link else None

        states_dict = {}
        for sl in workflow.state_links:
            state = sl.state
            actions = []
            for t in workflow.transitions:
                if t.from_state_id == state.id:
                    actions.append({
                        "slug": t.action_ref.slug,
                        "label": t.action_ref.label,
                        "target_slug": t.to_state.slug,
                        "target_label": t.to_state.label,
                    })
            states_dict[state.slug] = {
                "slug": state.slug,
                "label": state.label,
                "color": state.color,
                "is_initial": sl.is_initial,
                "actions": actions,
            }

        return {
            "enabled": True,
            "initial_state": initial_state_slug,
            "states": states_dict,
        }

    async def get_initial_state(self, entity: str) -> Optional[str]:
        return await self.workflow_repo.get_initial_state(entity)

    async def get_available_actions(
        self, entity: str, current_state: str, user: Any = None
    ) -> list[dict]:
        return await self.workflow_repo.get_available_actions(entity, current_state, user)

    async def validate_and_transition(
        self,
        entity: str,
        record_id: str,
        action: str,
        current_state: str,
        user: Any = None,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """Validate transition. Returns (is_valid, target_state, error)."""
        return await self.workflow_repo.validate_transition(
            entity, current_state, action, user
        )
