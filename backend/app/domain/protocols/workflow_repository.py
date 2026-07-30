"""
Workflow Repository Protocol
=============================
Abstract interface for workflow data access.
"""
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class WorkflowRepositoryProtocol(Protocol):
    """Interface for workflow data access."""

    async def get_workflow(self, entity: str) -> Optional[Any]:
        """Get workflow configuration for an entity."""
        ...

    async def get_initial_state(self, entity: str) -> Optional[str]:
        """Get the initial workflow state slug for an entity."""
        ...

    async def get_available_actions(
        self,
        entity: str,
        current_state: str,
        user: Any = None,
    ) -> list[dict[str, Any]]:
        """Get available workflow actions from the current state."""
        ...

    async def validate_transition(
        self,
        entity: str,
        current_state: str,
        action: str,
        user: Any = None,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """Validate a workflow transition. Returns (is_valid, target_state, error_message)."""
        ...
