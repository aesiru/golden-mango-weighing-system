"""
Global Workflow Management API.

Design:
1. WorkflowState - Global entity representing a status (e.g., "Open", "Closed")
2. WorkflowAction - Global entity representing a trigger/verb (e.g., "Approve", "Submit")
3. Workflow - Per-entity workflow configuration
4. WorkflowStateLink - Junction: which global states belong to which workflow
5. WorkflowTransition - Flow: from_state -> action -> to_state within a workflow
"""
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.framework.models.workflow import (
    WorkflowState, WorkflowAction, Workflow, WorkflowStateLink, WorkflowTransition, generate_slug
)
from app.application.services.workflows.workflow_service import WorkflowAppService
from app.api.dependencies import get_workflow_service

router = APIRouter(prefix="/workflow", tags=["workflow"])


@router.get("/{entity}/transitions", name="get_workflow_transitions")
async def get_workflow_transitions(
    entity: str,
    current_state: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    workflow_service: WorkflowAppService = Depends(get_workflow_service),
):
    """
    Get available workflow transitions for an entity.
    Returns transitions available from the current state.
    """
    from app.core.security import get_current_user_from_token
    
    user = await get_current_user_from_token(authorization, db)
    
    if not current_state:
        # Get initial state if no current state provided
        initial_state = await workflow_service.get_initial_state(entity)
        current_state = initial_state
    else:
        current_state = generate_slug(current_state)

    if not current_state:
        return api_response(
            status="success",
            message="No workflow configured for this entity",
            data=[]
        )
    
    # Get available transitions
    transitions = await workflow_service.get_available_actions(entity, current_state, user)
    
    return api_response(
        status="success",
        message="Transitions retrieved successfully",
        data=transitions
    )


def api_response(status: str, message: str, data: Any = None) -> dict:
    response = {"status": status, "message": message}
    if data is not None:
        response["data"] = data
    return response


def require_superuser(current_user: CurrentUser):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required")


# ============================================================================
# Pydantic Models
# ============================================================================

class StateCreate(BaseModel):
    label: str
    color: Optional[str] = "neutral"

class StateUpdate(BaseModel):
    label: Optional[str] = None
    color: Optional[str] = None

class ActionCreate(BaseModel):
    label: str

class ActionUpdate(BaseModel):
    label: Optional[str] = None

class StateLinkInput(BaseModel):
    state_id: str
    is_initial: bool = False

class TransitionInput(BaseModel):
    from_state_id: str
    action_id: str
    to_state_id: str
    allowed_roles: Optional[List[str]] = None

class WorkflowCreate(BaseModel):
    name: str
    target_entity: str
    is_active: bool = True
    state_links: List[StateLinkInput] = []
    transitions: List[TransitionInput] = []

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    state_links: Optional[List[StateLinkInput]] = None
    transitions: Optional[List[TransitionInput]] = None


# ============================================================================
# Global Workflow States CRUD
# ============================================================================

@router.get("/states")
async def list_states(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """List all global workflow states."""
    result = await db.execute(select(WorkflowState).order_by(WorkflowState.label.asc()))
    states = result.scalars().all()
    return api_response("success", "States retrieved", [
        {"id": s.id, "label": s.label, "slug": s.slug, "color": s.color}
        for s in states
    ])


@router.post("/states")
async def create_state(
    payload: StateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Create a new global workflow state."""
    require_superuser(current_user)
    
    slug = generate_slug(payload.label)
    existing = await db.execute(select(WorkflowState).where(WorkflowState.slug == slug))
    if existing.scalar_one_or_none():
        return api_response("error", f"State with slug '{slug}' already exists")
    
    state = WorkflowState(label=payload.label, slug=slug, color=payload.color or "neutral")
    db.add(state)
    await db.commit()
    await db.refresh(state)
    
    return api_response("success", "State created", {"id": state.id, "slug": state.slug})


@router.put("/states/{state_id}")
async def update_state(
    state_id: str,
    payload: StateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Update a global workflow state."""
    require_superuser(current_user)
    
    result = await db.execute(select(WorkflowState).where(WorkflowState.id == state_id))
    state = result.scalar_one_or_none()
    if not state:
        return api_response("error", "State not found")
    
    if payload.label is not None:
        new_slug = generate_slug(payload.label)
        if new_slug != state.slug:
            existing = await db.execute(select(WorkflowState).where(WorkflowState.slug == new_slug))
            if existing.scalar_one_or_none():
                return api_response("error", f"State with slug '{new_slug}' already exists")
        state.label = payload.label
        state.slug = new_slug
    if payload.color is not None:
        state.color = payload.color
    
    await db.commit()
    return api_response("success", "State updated", {"id": state.id, "slug": state.slug})


@router.delete("/states/{state_id}")
async def delete_state(
    state_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Delete a global workflow state. Fails if referenced by any workflow."""
    require_superuser(current_user)
    
    result = await db.execute(select(WorkflowState).where(WorkflowState.id == state_id))
    state = result.scalar_one_or_none()
    if not state:
        return api_response("error", "State not found")
    
    # Check if referenced by any workflow
    link_count = await db.execute(
        select(func.count()).select_from(WorkflowStateLink).where(WorkflowStateLink.state_id == state_id)
    )
    if link_count.scalar() > 0:
        return api_response("error", "Cannot delete: state is used by one or more workflows")
    
    trans_count = await db.execute(
        select(func.count()).select_from(WorkflowTransition).where(
            (WorkflowTransition.from_state_id == state_id) | (WorkflowTransition.to_state_id == state_id)
        )
    )
    if trans_count.scalar() > 0:
        return api_response("error", "Cannot delete: state is used in workflow transitions")
    
    await db.delete(state)
    await db.commit()
    return api_response("success", "State deleted")


# ============================================================================
# Global Workflow Actions CRUD
# ============================================================================

@router.get("/actions")
async def list_actions(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """List all global workflow actions."""
    result = await db.execute(select(WorkflowAction).order_by(WorkflowAction.label.asc()))
    actions = result.scalars().all()
    return api_response("success", "Actions retrieved", [
        {"id": a.id, "label": a.label, "slug": a.slug}
        for a in actions
    ])


@router.post("/actions")
async def create_action(
    payload: ActionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Create a new global workflow action."""
    require_superuser(current_user)
    
    slug = generate_slug(payload.label)
    existing = await db.execute(select(WorkflowAction).where(WorkflowAction.slug == slug))
    if existing.scalar_one_or_none():
        return api_response("error", f"Action with slug '{slug}' already exists")
    
    action = WorkflowAction(label=payload.label, slug=slug)
    db.add(action)
    await db.commit()
    await db.refresh(action)
    
    return api_response("success", "Action created", {"id": action.id, "slug": action.slug})


@router.put("/actions/{action_id}")
async def update_action(
    action_id: str,
    payload: ActionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Update a global workflow action."""
    require_superuser(current_user)
    
    result = await db.execute(select(WorkflowAction).where(WorkflowAction.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        return api_response("error", "Action not found")
    
    if payload.label is not None:
        new_slug = generate_slug(payload.label)
        if new_slug != action.slug:
            existing = await db.execute(select(WorkflowAction).where(WorkflowAction.slug == new_slug))
            if existing.scalar_one_or_none():
                return api_response("error", f"Action with slug '{new_slug}' already exists")
        action.label = payload.label
        action.slug = new_slug
    
    await db.commit()
    return api_response("success", "Action updated", {"id": action.id, "slug": action.slug})


@router.delete("/actions/{action_id}")
async def delete_action(
    action_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Delete a global workflow action. Fails if referenced by any workflow transition."""
    require_superuser(current_user)
    
    result = await db.execute(select(WorkflowAction).where(WorkflowAction.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        return api_response("error", "Action not found")
    
    trans_count = await db.execute(
        select(func.count()).select_from(WorkflowTransition).where(WorkflowTransition.action_id == action_id)
    )
    if trans_count.scalar() > 0:
        return api_response("error", "Cannot delete: action is used in workflow transitions")
    
    await db.delete(action)
    await db.commit()
    return api_response("success", "Action deleted")


# ============================================================================
# Workflow CRUD
# ============================================================================

@router.get("")
async def list_workflows(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """List all workflows."""
    require_superuser(current_user)
    
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.state_links), selectinload(Workflow.transitions))
        .order_by(Workflow.name.asc())
    )
    workflows = result.scalars().all()
    
    return api_response("success", "Workflows retrieved", [
        {
            "id": w.id,
            "name": w.name,
            "target_entity": w.target_entity,
            "is_active": w.is_active,
            "states_count": len(w.state_links),
            "transitions_count": len(w.transitions),
        }
        for w in workflows
    ])


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Get workflow with states and transitions."""
    require_superuser(current_user)
    
    result = await db.execute(
        select(Workflow)
        .where(Workflow.id == workflow_id)
        .options(
            selectinload(Workflow.state_links).selectinload(WorkflowStateLink.state),
            selectinload(Workflow.transitions).selectinload(WorkflowTransition.from_state),
            selectinload(Workflow.transitions).selectinload(WorkflowTransition.action_ref),
            selectinload(Workflow.transitions).selectinload(WorkflowTransition.to_state),
        )
    )
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        return api_response("error", "Workflow not found")
    
    return api_response("success", "Workflow retrieved", {
        "id": workflow.id,
        "name": workflow.name,
        "target_entity": workflow.target_entity,
        "is_active": workflow.is_active,
        "state_links": [
            {
                "id": sl.id,
                "state_id": sl.state_id,
                "state_label": sl.state.label,
                "state_slug": sl.state.slug,
                "state_color": sl.state.color,
                "is_initial": sl.is_initial,
                "sort_order": sl.sort_order,
            }
            for sl in sorted(workflow.state_links, key=lambda x: x.sort_order)
        ],
        "transitions": [
            {
                "id": t.id,
                "from_state_id": t.from_state_id,
                "from_state_label": t.from_state.label,
                "from_state_slug": t.from_state.slug,
                "action_id": t.action_id,
                "action_label": t.action_ref.label,
                "action_slug": t.action_ref.slug,
                "to_state_id": t.to_state_id,
                "to_state_label": t.to_state.label,
                "to_state_slug": t.to_state.slug,
                "sort_order": t.sort_order,
                "allowed_roles": t.get_allowed_roles(),
            }
            for t in sorted(workflow.transitions, key=lambda x: x.sort_order)
        ],
    })


@router.get("/by-entity/{target_entity}")
async def get_workflow_by_entity(
    target_entity: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Get workflow by target entity name."""
    result = await db.execute(
        select(Workflow)
        .where(Workflow.target_entity == target_entity)
        .options(
            selectinload(Workflow.state_links).selectinload(WorkflowStateLink.state),
            selectinload(Workflow.transitions).selectinload(WorkflowTransition.from_state),
            selectinload(Workflow.transitions).selectinload(WorkflowTransition.action_ref),
            selectinload(Workflow.transitions).selectinload(WorkflowTransition.to_state),
        )
    )
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        return api_response("error", f"No workflow for entity '{target_entity}'")
    
    initial_state = next((sl for sl in workflow.state_links if sl.is_initial), None)
    
    return api_response("success", "Workflow retrieved", {
        "id": workflow.id,
        "name": workflow.name,
        "target_entity": workflow.target_entity,
        "is_active": workflow.is_active,
        "initial_state": initial_state.state.slug if initial_state else None,
        "state_links": [
            {
                "id": sl.id,
                "state_id": sl.state_id,
                "state_label": sl.state.label,
                "state_slug": sl.state.slug,
                "state_color": sl.state.color,
                "is_initial": sl.is_initial,
            }
            for sl in sorted(workflow.state_links, key=lambda x: x.sort_order)
        ],
        "transitions": [
            {
                "id": t.id,
                "from_state_slug": t.from_state.slug,
                "action_slug": t.action_ref.slug,
                "action_label": t.action_ref.label,
                "to_state_slug": t.to_state.slug,
            }
            for t in sorted(workflow.transitions, key=lambda x: x.sort_order)
        ],
    })


@router.post("")
async def create_workflow(
    payload: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Create a new workflow for an entity."""
    require_superuser(current_user)
    
    existing = await db.execute(select(Workflow).where(Workflow.target_entity == payload.target_entity))
    if existing.scalar_one_or_none():
        return api_response("error", f"Workflow for '{payload.target_entity}' already exists")
    
    workflow = Workflow(
        name=payload.name,
        target_entity=payload.target_entity,
        is_active=payload.is_active,
    )
    db.add(workflow)
    await db.flush()
    
    # Add state links
    initial_count = sum(1 for sl in payload.state_links if sl.is_initial)
    if initial_count > 1:
        return api_response("error", "Only one state can be marked as initial")
    
    for i, sl in enumerate(payload.state_links):
        link = WorkflowStateLink(
            workflow_id=workflow.id,
            state_id=sl.state_id,
            is_initial=sl.is_initial,
            sort_order=i,
        )
        db.add(link)
    
    # Add transitions
    for i, t in enumerate(payload.transitions):
        transition = WorkflowTransition(
            workflow_id=workflow.id,
            from_state_id=t.from_state_id,
            action_id=t.action_id,
            to_state_id=t.to_state_id,
            sort_order=i,
        )
        db.add(transition)
    
    await db.commit()
    return api_response("success", f"Workflow created for '{payload.target_entity}'", {"id": workflow.id})


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Update a workflow. Replaces state_links/transitions if provided."""
    require_superuser(current_user)
    
    result = await db.execute(
        select(Workflow)
        .where(Workflow.id == workflow_id)
        .options(selectinload(Workflow.state_links), selectinload(Workflow.transitions))
    )
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        return api_response("error", "Workflow not found")
    
    if payload.name is not None:
        workflow.name = payload.name
    if payload.is_active is not None:
        workflow.is_active = payload.is_active
    
    # Replace state links if provided
    if payload.state_links is not None:
        initial_count = sum(1 for sl in payload.state_links if sl.is_initial)
        if initial_count > 1:
            return api_response("error", "Only one state can be marked as initial")
        
        for sl in workflow.state_links:
            await db.delete(sl)
        
        for i, sl in enumerate(payload.state_links):
            link = WorkflowStateLink(
                workflow_id=workflow.id,
                state_id=sl.state_id,
                is_initial=sl.is_initial,
                sort_order=i,
            )
            db.add(link)
    
    # Replace transitions if provided
    if payload.transitions is not None:
        for t in workflow.transitions:
            await db.delete(t)
        
        for i, t in enumerate(payload.transitions):
            transition = WorkflowTransition(
                workflow_id=workflow.id,
                from_state_id=t.from_state_id,
                action_id=t.action_id,
                to_state_id=t.to_state_id,
                sort_order=i,
            )
            db.add(transition)
    
    await db.commit()
    return api_response("success", "Workflow updated")


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Delete a workflow (cascades to state_links and transitions)."""
    require_superuser(current_user)
    
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        return api_response("error", "Workflow not found")
    
    await db.delete(workflow)
    await db.commit()
    return api_response("success", "Workflow deleted")


# ============================================================================
# Workflow State Link CRUD (add/remove states from a workflow)
# ============================================================================

@router.post("/{workflow_id}/states")
async def add_state_to_workflow(
    workflow_id: str,
    payload: StateLinkInput,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Add a global state to a workflow."""
    require_superuser(current_user)
    
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id).options(selectinload(Workflow.state_links))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        return api_response("error", "Workflow not found")
    
    # Check state exists
    state_result = await db.execute(select(WorkflowState).where(WorkflowState.id == payload.state_id))
    if not state_result.scalar_one_or_none():
        return api_response("error", "State not found")
    
    # Check duplicate
    if any(sl.state_id == payload.state_id for sl in workflow.state_links):
        return api_response("error", "State already linked to this workflow")
    
    # If setting as initial, unset others
    if payload.is_initial:
        for sl in workflow.state_links:
            if sl.is_initial:
                sl.is_initial = False
    
    link = WorkflowStateLink(
        workflow_id=workflow.id,
        state_id=payload.state_id,
        is_initial=payload.is_initial,
        sort_order=len(workflow.state_links),
    )
    db.add(link)
    await db.commit()
    
    return api_response("success", "State added to workflow", {"id": link.id})


@router.delete("/{workflow_id}/states/{state_link_id}")
async def remove_state_from_workflow(
    workflow_id: str,
    state_link_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Remove a state link from a workflow (does not delete the global state)."""
    require_superuser(current_user)
    
    result = await db.execute(
        select(WorkflowStateLink)
        .where(WorkflowStateLink.id == state_link_id, WorkflowStateLink.workflow_id == workflow_id)
    )
    link = result.scalar_one_or_none()
    
    if not link:
        return api_response("error", "State link not found")
    
    await db.delete(link)
    await db.commit()
    return api_response("success", "State removed from workflow")


@router.put("/{workflow_id}/states/{state_link_id}")
async def update_state_link(
    workflow_id: str,
    state_link_id: str,
    payload: StateLinkInput,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Update a state link."""
    require_superuser(current_user)
    
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id).options(selectinload(Workflow.state_links))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        return api_response("error", "Workflow not found")
    
    target_link = None
    for sl in workflow.state_links:
        if sl.id == state_link_id:
            target_link = sl
            break
    
    if not target_link:
        return api_response("error", "State link not found")
    
    if payload.is_initial:
        for sl in workflow.state_links:
            sl.is_initial = False
        target_link.is_initial = True
    else:
        target_link.is_initial = False
    
    await db.commit()
    return api_response("success", "State link updated")


@router.put("/{workflow_id}/states/{state_link_id}/set-initial")
async def set_initial_state(
    workflow_id: str,
    state_link_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Set a state as the initial state for a workflow."""
    require_superuser(current_user)
    
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id).options(selectinload(Workflow.state_links))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        return api_response("error", "Workflow not found")
    
    target_link = None
    for sl in workflow.state_links:
        if sl.id == state_link_id:
            target_link = sl
        sl.is_initial = False
    
    if not target_link:
        return api_response("error", "State link not found")
    
    target_link.is_initial = True
    await db.commit()
    return api_response("success", "Initial state updated")


# ============================================================================
# Workflow Transition CRUD
# ============================================================================

@router.post("/{workflow_id}/transitions")
async def add_transition_to_workflow(
    workflow_id: str,
    payload: TransitionInput,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Add a transition to a workflow."""
    require_superuser(current_user)
    
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id).options(selectinload(Workflow.transitions))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        return api_response("error", "Workflow not found")
    
    transition = WorkflowTransition(
        workflow_id=workflow.id,
        from_state_id=payload.from_state_id,
        action_id=payload.action_id,
        to_state_id=payload.to_state_id,
        sort_order=len(workflow.transitions),
    )
    transition.set_allowed_roles(payload.allowed_roles)
    db.add(transition)
    await db.commit()
    
    return api_response("success", "Transition added", {"id": transition.id})


@router.put("/{workflow_id}/transitions/{transition_id}")
async def update_transition(
    workflow_id: str,
    transition_id: str,
    payload: TransitionInput,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Update a transition."""
    require_superuser(current_user)
    
    result = await db.execute(
        select(WorkflowTransition)
        .where(WorkflowTransition.id == transition_id, WorkflowTransition.workflow_id == workflow_id)
    )
    transition = result.scalar_one_or_none()
    
    if not transition:
        return api_response("error", "Transition not found")
    
    transition.from_state_id = payload.from_state_id
    transition.action_id = payload.action_id
    transition.to_state_id = payload.to_state_id
    transition.set_allowed_roles(payload.allowed_roles)
    
    await db.commit()
    return api_response("success", "Transition updated")


@router.delete("/{workflow_id}/transitions/{transition_id}")
async def remove_transition_from_workflow(
    workflow_id: str,
    transition_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Remove a transition from a workflow."""
    require_superuser(current_user)
    
    result = await db.execute(
        select(WorkflowTransition)
        .where(WorkflowTransition.id == transition_id, WorkflowTransition.workflow_id == workflow_id)
    )
    transition = result.scalar_one_or_none()
    
    if not transition:
        return api_response("error", "Transition not found")
    
    await db.delete(transition)
    await db.commit()
    return api_response("success", "Transition removed")
