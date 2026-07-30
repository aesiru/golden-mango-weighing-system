"""
Phase 4 – Work Management
==========================
Tests that Work Orders and Work Order Activities can be created and
driven through the execution lifecycle as described in:
  • docs/business_logics/user-manual/phase-4-work-management.md

Covers:
  • Work Order creation (starts in Requested)
  • Work Order Activity creation (starts in Awaiting Resources)
  • Work Order Labor assignment
  • WOA workflow: Awaiting Resources → Ready (Allocate)
  • WO workflow:  Requested → Approved → In Progress (Start)
  • WOA workflow: In Progress → Completed (Complete)
  • WO workflow:  In Progress → Closed (Complete)
"""

from __future__ import annotations

import pytest

ENTITY_ACTION = "/api/entity/{entity}/action"
ENTITY_WORKFLOW = "/api/entity/{entity}/workflow"
ENTITY_LIST = "/api/entity/{entity}/list"
ENTITY_FETCH_FROM = "/api/entity/{entity}/fetch_from/{record_id}"


async def _create(client, entity: str, data: dict) -> dict:
    response = await client.post(
        ENTITY_ACTION.format(entity=entity),
        json={"action": "create", "data": data},
    )
    assert response.status_code == 200, f"HTTP {response.status_code} creating '{entity}'"
    payload = response.json()
    assert payload["status"] == "success", (
        f"Create '{entity}' failed: {payload.get('message')} | errors={payload.get('errors')}"
    )
    return payload["data"]


async def _fetch_field(client, entity: str, record_id: str, field: str):
    """GET a single field value from a record via the fetch_from endpoint."""
    resp = await client.get(
        ENTITY_FETCH_FROM.format(entity=entity, record_id=record_id),
    )
    assert resp.status_code == 200, f"HTTP {resp.status_code} fetching field '{field}' from '{entity}/{record_id}'"
    data = resp.json()
    return data.get(field)


async def _workflow(client, entity: str, record_id: str, action: str) -> dict:
    response = await client.post(
        ENTITY_WORKFLOW.format(entity=entity),
        json={"action": action, "id": record_id},
    )
    assert response.status_code == 200, (
        f"HTTP {response.status_code} on workflow '{action}' for '{entity}'"
    )
    return response.json()


def _state(payload: dict) -> str:
    return (payload.get("data") or {}).get("workflow_state", "").lower().replace(" ", "_")


# ---------------------------------------------------------------------------
# 1. Work Order creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase4_work_order_created_in_requested_state(
    superuser_client, record_id_factory
):
    """Assert that a Work Order is created in the Requested state.

    User-manual reference: Phase 4 §1 – Review the Work Order.
    """
    rid = record_id_factory

    wo = await _create(superuser_client, "work_order", {
        "description": rid("Screw Press Conveyor Assembly – bearing inspection"),
        "work_order_type": "Preventive Maintenance",
    })

    state = (wo.get("workflow_state") or "").lower().replace(" ", "_")
    assert state in ("requested", ""), (
        f"Expected WO initial state 'requested', got '{state}'"
    )
    assert wo["id"]


# ---------------------------------------------------------------------------
# 2. Work Order Activity creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase4_work_order_activity_created_awaiting_resources(
    superuser_client, record_id_factory
):
    """Assert that a Work Order Activity is created in Awaiting Resources state.

    User-manual reference: Phase 4 §2 – Review Each Work Order Activity.
    """
    rid = record_id_factory

    wo = await _create(superuser_client, "work_order", {
        "description": rid("WO for WOA state test"),
        "work_order_type": "Corrective Maintenance",
    })

    woa = await _create(superuser_client, "work_order_activity", {
        "description": rid("Inspect and replace bearings"),
        "work_order": wo["id"],
    })

    state = (woa.get("workflow_state") or "").lower().replace(" ", "_")
    assert state in ("awaiting_resources", ""), (
        f"Expected WOA initial state 'awaiting_resources', got '{state}'"
    )
    assert woa["id"]


# ---------------------------------------------------------------------------
# 3. Work Order Labor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase4_work_order_labor_can_be_added(
    superuser_client, record_id_factory
):
    """Assert that a Work Order Labor row can be assigned to a Work Order Activity.

    User-manual reference: Phase 4 §3 – Add Work Order Labor.
    """
    rid = record_id_factory

    wo = await _create(superuser_client, "work_order", {
        "description": rid("WO for labor assignment test"),
        "work_order_type": "Preventive Maintenance",
    })

    woa = await _create(superuser_client, "work_order_activity", {
        "description": rid("Lubrication service"),
        "work_order": wo["id"],
    })

    labor_row = await _create(superuser_client, "work_order_labor", {
        "work_order_activity": woa["id"],
        "lead": True,
    })

    assert labor_row["id"]
    assert labor_row.get("work_order_activity") == woa["id"]


# ---------------------------------------------------------------------------
# 4. Full Work Order lifecycle: Requested → Approved → In Progress
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase4_work_order_workflow_requested_to_in_progress(
    superuser_client, record_id_factory
):
    """Assert the WO approval and start workflow: Requested → Approved → In Progress.

    User-manual reference: Phase 4 §8–9 – Allocate WOA / Start the Work Order.
    All linked WOAs must be in Ready state before Start is allowed.
    """
    rid = record_id_factory

    # 1. Create WO
    wo = await _create(superuser_client, "work_order", {
        "description": rid("WO lifecycle test – bearing inspection"),
        "work_order_type": "Preventive Maintenance",
    })
    wo_id = wo["id"]

    # 2. Create WOA linked to WO
    woa = await _create(superuser_client, "work_order_activity", {
        "description": rid("WOA for lifecycle test"),
        "work_order": wo_id,
    })
    woa_id = woa["id"]

    # 3. Add at least one labor row (required for Allocate)
    await _create(superuser_client, "work_order_labor", {
        "work_order_activity": woa_id,
        "lead": True,
    })

    # 4. WO: Requested → Approved (must be approved before WOA can allocate)
    approve = await _workflow(superuser_client, "work_order", wo_id, "approve")
    assert approve["status"] == "success", f"WO approve failed: {approve.get('message')}"
    assert _state(approve) == "approved", (
        f"Expected WO state 'approved' after approve, got '{_state(approve)}'"
    )

    # 5. WOA: Awaiting Resources → Ready (Allocate)
    alloc = await _workflow(superuser_client, "work_order_activity", woa_id, "allocate")
    assert alloc["status"] == "success", f"WOA allocate failed: {alloc.get('message')}"
    assert _state(alloc) == "ready", (
        f"Expected WO state 'approved', got '{_state(approve)}'"
    )

    # 6. WO: Approved → In Progress (Start)
    start = await _workflow(superuser_client, "work_order", wo_id, "start")
    assert start["status"] == "success", f"WO 'start' failed: {start.get('message')}"
    assert _state(start) == "in_progress", (
        f"Expected WO state 'in_progress' after Start, got '{_state(start)}'"
    )


# ---------------------------------------------------------------------------
# 5. Work Order Activity completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase4_work_order_activity_can_be_completed(
    superuser_client, record_id_factory
):
    """Assert that a WOA can be completed and the WO can then be closed.

    User-manual reference: Phase 4 §10–11 – Complete WOA / Close WO.
    """
    rid = record_id_factory

    # Create and prepare the WO + WOA + Labor chain
    wo = await _create(superuser_client, "work_order", {
        "description": rid("WO complete test"),
        "work_order_type": "Corrective Maintenance",
    })
    wo_id = wo["id"]

    woa = await _create(superuser_client, "work_order_activity", {
        "description": rid("WOA complete test"),
        "work_order": wo_id,
    })
    woa_id = woa["id"]

    labor = await _create(superuser_client, "work_order_labor", {
        "work_order_activity": woa_id,
        "lead": True,
    })
    labor_id = labor["id"]

    # Approve WO (must be approved before WOA can allocate)
    approve_wo = await _workflow(superuser_client, "work_order", wo_id, "approve")
    assert approve_wo["status"] == "success", f"WO approve failed: {approve_wo.get('message')}"

    # Allocate WOA (requires WO to be approved)
    alloc = await _workflow(superuser_client, "work_order_activity", woa_id, "allocate")
    assert alloc["status"] == "success", f"WOA allocate failed: {alloc.get('message')}"

    # Start WO (cascades WOA to in_progress)
    start_wo = await _workflow(superuser_client, "work_order", wo_id, "start")
    assert start_wo["status"] == "success", f"WO start failed: {start_wo.get('message')}"
    assert _state(start_wo) == "in_progress"

    # WOA is now in_progress (cascaded by WO start)
    woa_list = await superuser_client.get(
        f"/api/entity/work_order_activity/list?filters=[['id','==','{woa_id}']]"
    )
    woa_list_data = woa_list.json()
    woa_record = woa_list_data.get("data", [])
    assert woa_record, f"Could not fetch work_order_activity {woa_id}"
    woa_state = woa_record[0].get("workflow_state")
    assert (woa_state or "").lower().replace(" ", "_") == "in_progress"

    # WOA: In Progress → Completed
    complete_woa = await _workflow(
        superuser_client, "work_order_activity", woa_id, "complete"
    )
    assert complete_woa["status"] == "success", (
        f"WOA 'complete' failed: {complete_woa.get('message')}"
    )
    assert _state(complete_woa) == "completed", (
        f"Expected WOA state 'completed', got '{_state(complete_woa)}'"
    )

    # Create Work Order Labor Actual Hours (required for WOA close)
    await _create(superuser_client, "work_order_labor_actual_hours", {
        "wo_labor_id": labor_id,
        "date": "2026-04-22",
        "time": "08:00",
        "reason": "Test actual hours",
        "comment": "Test comment",
    })

    # Create Work Order Activity Log (required for WOA close)
    await _create(superuser_client, "work_order_activity_logs", {
        "work_order_activity": woa_id,
        "log": "Test log entry for WOA close",
    })

    # WOA: Completed → Closed
    close_woa = await _workflow(superuser_client, "work_order_activity", woa_id, "close")
    assert close_woa["status"] == "success", f"WOA close failed: {close_woa.get('message')}"
    assert _state(close_woa) == "closed"

    # WO: In Progress → Closed (requires all WOAs closed)
    close_wo = await _workflow(superuser_client, "work_order", wo_id, "complete")
    assert close_wo["status"] == "success", (
        f"WO 'complete/close' failed: {close_wo.get('message')}"
    )
    assert _state(close_wo) == "closed", (
        f"Expected WO state 'closed', got '{_state(close_wo)}'"
    )
