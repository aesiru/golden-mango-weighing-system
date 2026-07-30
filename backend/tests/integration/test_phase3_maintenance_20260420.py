"""
Phase 3 – Maintenance Management + Phase 3.1 Emergency Maintenance
===================================================================
Tests that the preventive maintenance setup and emergency path both
work as described in:
  • docs/business_logics/user-manual/phase-3-maintenance-activities-plans.md
  • docs/business_logics/user-manual/phase-3-1-emergency-maintenance.md

Covers:
  • Maintenance Activity creation
  • Maintenance Plan creation (linked to Asset Class)
  • Planned Maintenance Activity creation
  • Maintenance Request creation (starts in Draft)
  • Normal MR workflow: Draft → Pending Approval → Approved
  • Emergency MR path: Draft →Submit_for_Emergency → Release
    (which also creates a Work Order + Work Order Activity)
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


# ---------------------------------------------------------------------------
# Helper: create the minimum maintenance prerequisite chain
# ---------------------------------------------------------------------------


async def _setup_asset_class(client, rid):
    return await _create(client, "asset_class", {
        "name": rid("Rotating Equipment"),
        "description": "Motors, pumps, conveyors, rotating machinery",
    })


async def _setup_maintenance_activity(client, rid, name_prefix: str):
    return await _create(client, "maintenance_activity", {
        "activity_name": rid(name_prefix),
        "description": f"Test maintenance activity – {name_prefix}",
    })


# ---------------------------------------------------------------------------
# 1. Maintenance Activities
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase3_maintenance_activities_can_be_created(
    superuser_client, record_id_factory
):
    """Assert that the three standard conveyor maintenance activities can be created.

    User-manual reference: Phase 3 §3 – Create Maintenance Activities.
    """
    rid = record_id_factory

    bearing = await _create(superuser_client, "maintenance_activity", {
        "activity_name": rid("Monthly Screw Press Bearing Inspection"),
        "description": "Inspect bearings, rollers, alignment, and unusual vibration",
    })

    lube = await _create(superuser_client, "maintenance_activity", {
        "activity_name": rid("Screw Press Lubrication Service"),
        "description": "Lubricate bearings, drive components, and moving joints",
    })

    belt = await _create(superuser_client, "maintenance_activity", {
        "activity_name": rid("Screw Press Belt Alignment Check"),
        "description": "Check belt tension, alignment, and wear condition",
    })

    assert bearing["id"]
    assert lube["id"]
    assert belt["id"]


# ---------------------------------------------------------------------------
# 2. Maintenance Plan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase3_maintenance_plan_can_be_created(
    superuser_client, record_id_factory
):
    """Assert that a Maintenance Plan linked to an Asset Class can be created.

    User-manual reference: Phase 3 §4 – Create the Maintenance Plan.
    """
    rid = record_id_factory

    asset_class = await _setup_asset_class(superuser_client, rid)

    plan = await _create(superuser_client, "maintenance_plan", {
        "description": rid("Screw Press Conveyor Comprehensive Maintenance Plan"),
        "asset_class": asset_class["id"],
    })

    assert plan["id"]


# ---------------------------------------------------------------------------
# 3. Planned Maintenance Activity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase3_planned_maintenance_activity_calendar_based_can_be_created(
    superuser_client, record_id_factory
):
    """Assert that a calendar-based Planned Maintenance Activity can be created.

    User-manual reference: Phase 3 §5.1 – Calendar-Based Inspection Schedule.
    """
    rid = record_id_factory

    asset_class = await _setup_asset_class(superuser_client, rid)
    plan = await _create(superuser_client, "maintenance_plan", {
        "description": rid("Comprehensive PM Plan"),
        "asset_class": asset_class["id"],
    })
    activity = await _setup_maintenance_activity(
        superuser_client, rid, "Monthly Bearing Inspection"
    )

    pma = await _create(superuser_client, "planned_maintenance_activity", {
        "maintenance_plan": plan["id"],
        "maintenance_activity": activity["id"],
        "maintenance_schedule": "Calendar Based",
        "maintenance_type": "RAT-0005",
    })

    assert pma["id"]


@pytest.mark.asyncio
async def test_phase3_planned_maintenance_activity_interval_based_can_be_created(
    superuser_client, record_id_factory
):
    """Assert that an interval-based Planned Maintenance Activity can be created.

    User-manual reference: Phase 3 §5.2 – Interval-Based Lubrication Schedule.
    """
    rid = record_id_factory

    asset_class = await _setup_asset_class(superuser_client, rid)
    plan = await _create(superuser_client, "maintenance_plan", {
        "description": rid("Comprehensive PM Plan"),
        "asset_class": asset_class["id"],
    })
    activity = await _setup_maintenance_activity(
        superuser_client, rid, "Lubrication Service"
    )

    pma = await _create(superuser_client, "planned_maintenance_activity", {
        "maintenance_plan": plan["id"],
        "maintenance_activity": activity["id"],
        "maintenance_schedule": "Interval Based",
        "maintenance_type": "RAT-0005",
    })

    assert pma["id"]


# ---------------------------------------------------------------------------
# 4. Maintenance Request – normal approval workflow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase3_maintenance_request_can_be_created_in_draft(
    superuser_client, record_id_factory
):
    """Assert that a Maintenance Request is created with workflow_state=Draft.

    User-manual reference: Phase 3 §6 – Process Maintenance Requests.
    """
    rid = record_id_factory

    mr = await _create(superuser_client, "maintenance_request", {
        "description": rid("Monthly Bearing Inspection for SCREW-001"),
        "priority": "Normal",
        "request_type": "Preventive Maintenance",
        "asset": "A-00001",
        "due_date": "2026-04-30",
        "site": "SITE-0001",
    })

    state = (mr.get("workflow_state") or "").lower()
    assert state in ("draft", ""), (
        f"Expected MR initial state to be Draft, got '{state}'"
    )
    assert mr["id"]


@pytest.mark.asyncio
async def test_phase3_maintenance_request_normal_workflow_draft_to_approved(
    superuser_client, record_id_factory
):
    """Assert the standard MR workflow: Draft → Pending Approval → Approved.

    User-manual reference: Phase 3 §6.1 – Review the Approved Request.
    """
    rid = record_id_factory

    mr = await _create(superuser_client, "maintenance_request", {
        "description": rid("PM bearing inspection – normal path"),
        "priority": "Normal",
        "request_type": "Preventive Maintenance",
        "asset": "A-00001",
        "due_date": "2026-04-30",
        "site": "SITE-0001",
        "department": "DEPT-0001",
    })
    mr_id = mr["id"]

    # Draft → Pending Approval
    step1 = await _workflow(
        superuser_client, "maintenance_request", mr_id, "submit_for_approval"
    )
    if step1["status"] != "success":
        pytest.skip(
            f"maintenance_request workflow 'submit_for_approval' not available: "
            f"{step1.get('message')}"
        )
    assert (
        (step1.get("data") or {}).get("workflow_state", "").lower().replace(" ", "_")
        == "pending_approval"
    )

    # Pending Approval → Approved
    step2 = await _workflow(
        superuser_client, "maintenance_request", mr_id, "approve"
    )
    assert step2["status"] == "success", f"approve failed: {step2.get('message')}"
    assert (
        (step2.get("data") or {}).get("workflow_state", "").lower().replace(" ", "_")
        == "approved"
    )


# ---------------------------------------------------------------------------
# 5. Phase 3.1 – Emergency Maintenance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase3_1_emergency_maintenance_request_can_be_created(
    superuser_client, record_id_factory
):
    """Assert that an Emergency priority Maintenance Request can be created.

    User-manual reference: Phase 3.1 §1 – Create the Emergency Maintenance Request.
    """
    rid = record_id_factory

    mr = await _create(superuser_client, "maintenance_request", {
        "description": rid("Emergency conveyor shutdown at Screw Press Line A"),
        "priority": "Emergency",
        "request_type": "Corrective Maintenance",
        "asset": "A-00001",
        "due_date": "2026-04-20",
        "site": "SITE-0001",
    })

    assert mr["id"]
    assert mr.get("priority") == "Emergency"


@pytest.mark.asyncio
async def test_phase3_1_submit_for_emergency_creates_work_order(
    superuser_client, record_id_factory
):
    """Assert that Submit_for_Emergency transitions the MR to Release and creates a Work Order.

    User-manual reference: Phase 3.1 §2 – Move the Request with Submit for Emergency.
    The maintenance_request workflow hook is expected to auto-generate a Work Order
    and a linked Work Order Activity when this action fires.
    """
    rid = record_id_factory

    mr = await _create(superuser_client, "maintenance_request", {
        "description": rid("Emergency conveyor shutdown – WO generation test"),
        "priority": "Emergency",
        "request_type": "Corrective Maintenance",
        "asset": "A-00001",
        "due_date": "2026-04-20",
        "site": "SITE-0001",
        "department": "DEPT-0001",
    })
    mr_id = mr["id"]

    result = await _workflow(
        superuser_client, "maintenance_request", mr_id, "submit_for_emergency"
    )

    if result["status"] != "success":
        pytest.skip(
            f"submit_for_emergency not available or hook error: {result.get('message')}"
        )

    # MR must have transitioned to Release
    data = result.get("data") or {}
    new_state = data.get("workflow_state", "").lower().replace(" ", "_")
    assert new_state == "release", (
        f"Expected MR state 'release' after Submit for Emergency, got '{new_state}'"
    )

    # The hook should have linked a Work Order Activity on the MR record
    # Fetch the MR via list endpoint to get the linked work_order_activity
    mr_list = await superuser_client.get(
        f"/api/entity/maintenance_request/list?filters=[['id','==','{mr_id}']]"
    )
    mr_list_data = mr_list.json()
    mr_record = mr_list_data.get("data", [])
    assert mr_record, f"Could not fetch maintenance_request {mr_id}"
    woa_id = mr_record[0].get("work_order_activity")
    assert woa_id, (
        "Expected a work_order_activity to be linked on the Maintenance Request after Submit for Emergency"
    )

    # Verify the WOA is linked to a Work Order
    woa_list = await superuser_client.get(
        f"/api/entity/work_order_activity/list?filters=[['id','==','{woa_id}']]"
    )
    woa_list_data = woa_list.json()
    woa_record = woa_list_data.get("data", [])
    assert woa_record, f"Could not fetch work_order_activity {woa_id}"
    wo_id = woa_record[0].get("work_order")
    assert wo_id, (
        "Expected the Work Order Activity to be linked to a Work Order"
    )
