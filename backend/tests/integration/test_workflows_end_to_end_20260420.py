"""
End-to-End Workflow Validation
================================
Tests every configured workflow path from start to finish with real HTTP
requests through the FastAPI test client.  No graceful skips — every
transition is asserted to succeed.

Workflows covered
-----------------
1.  Asset:               Acquired → Inspected → Active → Under Maintenance → Active → Decommissioned
2.  Purchase Request:    Draft → Pending Approval → Approved
3.  Purchase Request:    Draft → Pending Approval → Rejected → Draft  (reject + reopen)
4.  Maintenance Request: Draft → Pending Approval → Approved → Release (via submit_for_resolution)
                         + full WO/WOA execution cycle → MR Completed
5.  Maintenance Request: Draft → Release (emergency path)
                         + full WO/WOA execution cycle → MR Completed
6.  Work Order:          Requested → Approved → In Progress → Closed  (standalone, no MR)
7.  Work Order Activity: hold / resume cycle
8.  Stock Count:         Planned → In Progress → Approved → Closed
9.  Purchase Order:      disabled — assert workflow is blocked with an appropriate error

Seed FK values (from the current DB):
  - labor:     LBR-00001
  - item:      ITM-00001
  - uom:       UOM-00001
  - asset:     A-00001   (currently Active; used for MR asset field)
  - site:      SITE-0001
  - department: DEPT-0001
  - employee:  EMP-00001
  - inventory: INV-00001
"""
from __future__ import annotations

import uuid
import pytest
from app.application.services.documents.document import get_value

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ENTITY_ACTION = "/api/entity/{entity}/action"
ENTITY_WORKFLOW = "/api/entity/{entity}/workflow"
ENTITY_FETCH_FROM = "/api/entity/{entity}/fetch_from/{record_id}"

SITE = "SITE-0001"
DEPT = "DEPT-0001"
EMPLOYEE = "EMP-00001"
ASSET_ID = "A-00001"
LABOR_ID = "LBR-00001"
ITEM_ID = "ITM-00001"
UOM_ID = "UOM-00001"
INVENTORY_ID = "INV-00001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create(client, entity: str, data: dict) -> dict:
    """POST create action; assert success and return the created record dict."""
    resp = await client.post(
        ENTITY_ACTION.format(entity=entity),
        json={"action": "create", "data": data},
    )
    assert resp.status_code == 200, (
        f"HTTP {resp.status_code} creating '{entity}': {resp.text[:300]}"
    )
    payload = resp.json()
    assert payload["status"] == "success", (
        f"Create '{entity}' failed: {payload.get('message')} | errors={payload.get('errors')}"
    )
    return payload["data"]


async def _workflow(client, entity: str, record_id: str, action: str) -> dict:
    """POST workflow action; assert HTTP 200 and return the full response payload."""
    resp = await client.post(
        ENTITY_WORKFLOW.format(entity=entity),
        json={"action": action, "id": record_id},
    )
    assert resp.status_code == 200, (
        f"HTTP {resp.status_code} on workflow '{action}' for '{entity}/{record_id}': {resp.text[:300]}"
    )
    return resp.json()


def _state(payload: dict) -> str:
    """Extract and normalise workflow_state from a workflow response payload."""
    return (payload.get("data") or {}).get("workflow_state", "").lower().replace(" ", "_")


async def _fetch_field(client, entity: str, record_id: str, field: str):
    """GET a single field value from a record via the fetch_from endpoint."""
    resp = await client.get(
        ENTITY_FETCH_FROM.format(entity=entity, record_id=record_id),
        params={"fields": field},
    )
    assert resp.status_code == 200, (
        f"HTTP {resp.status_code} fetching '{field}' from '{entity}/{record_id}': {resp.text[:300]}"
    )
    payload = resp.json()
    assert payload["status"] == "success", (
        f"fetch_from '{entity}/{record_id}' failed: {payload.get('message')}"
    )
    return payload["data"].get(field)


# ============================================================================
# 1. Asset full lifecycle
# ============================================================================

@pytest.mark.asyncio
async def test_wf_asset_full_lifecycle(superuser_client):
    """
    Asset: Acquired → Inspected → Active → Under Maintenance → Active → Decommissioned.

    bypass_process=True lets install_asset skip the formal WOA/MR approval path and
    create an AssetPosition directly.  All other transitions use the normal path.
    """
    client = superuser_client

    # Create a new asset — starts in 'Acquired' state
    uid = uuid.uuid4().hex[:8]
    asset = await _create(client, "asset", {
        "asset_tag": f"E2E-{uid}",
        "description": f"E2E test asset {uid} — full lifecycle",
        "bypass_process": True,
        "site": SITE,
        "department": DEPT,
    })
    asset_id = asset["id"]
    init_state = asset.get("workflow_state", "").lower()
    assert init_state in ("acquired", ""), (
        f"Expected new asset in 'acquired' state, got '{init_state}'"
    )

    # Acquired → Inspected (creates WOA + MR side-effects but the transition proceeds)
    r = await _workflow(client, "asset", asset_id, "inspect_asset")
    assert r["status"] == "success", f"inspect_asset failed: {r.get('message')}"
    assert _state(r) == "inspected", f"Expected 'inspected', got '{_state(r)}'"

    # Inspected → Active  (bypass_process=True → AssetPosition created directly)
    r = await _workflow(client, "asset", asset_id, "install_asset")
    assert r["status"] == "success", f"install_asset failed: {r.get('message')}"
    assert _state(r) == "active", f"Expected 'active', got '{_state(r)}'"

    # Active → Under Maintenance (creates WOA + MR side-effects)
    r = await _workflow(client, "asset", asset_id, "maintain_asset")
    assert r["status"] == "success", f"maintain_asset failed: {r.get('message')}"
    assert _state(r) == "under_maintenance", (
        f"Expected 'under_maintenance', got '{_state(r)}'"
    )

    # Under Maintenance → Active  (simple transition — "Complete")
    r = await _workflow(client, "asset", asset_id, "complete")
    assert r["status"] == "success", f"complete (maintenance) failed: {r.get('message')}"
    assert _state(r) == "active", f"Expected 'active', got '{_state(r)}'"

    # Active → Decommissioned  (simple transition)
    r = await _workflow(client, "asset", asset_id, "decommission")
    assert r["status"] == "success", f"decommission failed: {r.get('message')}"
    assert _state(r) == "decommissioned", f"Expected 'decommissioned', got '{_state(r)}'"


# ============================================================================
# 2. Purchase Request — full approval path
# ============================================================================

@pytest.mark.asyncio
async def test_wf_purchase_request_full_approval(superuser_client):
    """
    PR: Draft → Pending Approval → Approved.

    At least one PR line must exist before submit_for_approval / approve.
    """
    client = superuser_client

    uid = uuid.uuid4().hex[:8]
    pr = await _create(client, "purchase_request", {
        "pr_description": f"E2E PR approval test {uid}",
        "date_requested": "2026-04-20",
        "requestor": EMPLOYEE,
        "site": SITE,
        "department": DEPT,
    })
    pr_id = pr["id"]
    assert pr.get("workflow_state", "").lower() in ("draft", ""), (
        f"Expected PR initial state 'draft', got '{pr.get('workflow_state')}'"
    )

    # Create a PR line (required before any workflow action)
    await _create(client, "purchase_request_line", {
        "purchase_request": pr_id,
        "item": ITEM_ID,
        "qty_required": 2,
        "unit_of_measure": UOM_ID,
    })

    # Draft → Pending Approval
    r = await _workflow(client, "purchase_request", pr_id, "submit_for_approval")
    assert r["status"] == "success", f"submit_for_approval failed: {r.get('message')}"
    assert _state(r) == "pending_approval", f"Expected 'pending_approval', got '{_state(r)}'"

    # Pending Approval → Approved
    r = await _workflow(client, "purchase_request", pr_id, "approve")
    assert r["status"] == "success", f"approve failed: {r.get('message')}"
    assert _state(r) == "approved", f"Expected 'approved', got '{_state(r)}'"


# ============================================================================
# 3. Purchase Request — reject and reopen path
# ============================================================================

@pytest.mark.asyncio
async def test_wf_purchase_request_reject_and_reopen(superuser_client):
    """
    PR: Draft → Pending Approval → Rejected → Draft.
    """
    client = superuser_client

    uid = uuid.uuid4().hex[:8]
    pr = await _create(client, "purchase_request", {
        "pr_description": f"E2E PR reject/reopen test {uid}",
        "date_requested": "2026-04-20",
        "requestor": EMPLOYEE,
        "site": SITE,
        "department": DEPT,
    })
    pr_id = pr["id"]

    await _create(client, "purchase_request_line", {
        "purchase_request": pr_id,
        "item": ITEM_ID,
        "qty_required": 1,
        "unit_of_measure": UOM_ID,
    })

    r = await _workflow(client, "purchase_request", pr_id, "submit_for_approval")
    assert r["status"] == "success", f"submit_for_approval failed: {r.get('message')}"
    assert _state(r) == "pending_approval"

    r = await _workflow(client, "purchase_request", pr_id, "reject")
    assert r["status"] == "success", f"reject failed: {r.get('message')}"
    assert _state(r) == "rejected", f"Expected 'rejected', got '{_state(r)}'"

    r = await _workflow(client, "purchase_request", pr_id, "reopen")
    assert r["status"] == "success", f"reopen failed: {r.get('message')}"
    assert _state(r) == "draft", f"Expected 'draft' after reopen, got '{_state(r)}'"


# ============================================================================
# 4. Maintenance Request — standard approval path (full WO/WOA cycle)
# ============================================================================

@pytest.mark.asyncio
async def test_wf_maintenance_request_standard_path(superuser_client):
    """
    MR: Draft → Pending Approval → Approved (creates WOA)
         → Release (submit_for_resolution creates WO)
         → then full WO/WOA execution: Approve → Start → Complete
         → MR: Complete → Completed.
    """
    client = superuser_client

    # -- Create MR --
    uid = uuid.uuid4().hex[:8]
    mr = await _create(client, "maintenance_request", {
        "description": f"E2E MR standard path {uid}",
        "request_type": "RAT-0005",
        "asset": ASSET_ID,
        "due_date": "2026-04-30",
        "site": SITE,
        "department": DEPT,
        "priority": "Normal",
    })
    mr_id = mr["id"]
    assert mr.get("workflow_state", "").lower() in ("draft", ""), (
        f"Expected MR initial state 'draft', got '{mr.get('workflow_state')}'"
    )

    # Draft → Pending Approval
    r = await _workflow(client, "maintenance_request", mr_id, "submit_for_approval")
    assert r["status"] == "success", f"submit_for_approval failed: {r.get('message')}"
    assert _state(r) == "pending_approval"

    # Pending Approval → Approved  (side-effect: WOA created in Awaiting Resources)
    r = await _workflow(client, "maintenance_request", mr_id, "approve")
    assert r["status"] == "success", f"MR approve failed: {r.get('message')}"
    assert _state(r) == "approved"

    woa_id = r["data"].get("work_order_activity")
    assert woa_id, f"MR approve must create and link a WOA; got data={r['data']}"

    # Approved → Release  (side-effect: WO created in Requested, linked to WOA)
    r = await _workflow(client, "maintenance_request", mr_id, "submit_for_resolution")
    assert r["status"] == "success", f"submit_for_resolution failed: {r.get('message')}"
    assert _state(r) == "release"

    # Retrieve the WO ID via fetch_from on the WOA
    wo_id = await _fetch_field(client, "work_order_activity", woa_id, "work_order")
    assert wo_id, f"WOA '{woa_id}' must have work_order populated after submit_for_resolution"

    # Add labor to WOA (required for Allocate)
    labor = await _create(client, "work_order_labor", {
        "work_order_activity": woa_id,
        "labor": LABOR_ID,
    })
    labor_id = labor["id"]

    # WO: Requested → Approved
    r = await _workflow(client, "work_order", wo_id, "approve")
    assert r["status"] == "success", f"WO approve failed: {r.get('message')}"
    assert _state(r) == "approved"

    # WOA: Awaiting Resources → Ready  (requires WO in Approved + at least 1 labor)
    r = await _workflow(client, "work_order_activity", woa_id, "allocate")
    assert r["status"] == "success", f"WOA allocate failed: {r.get('message')}"
    assert _state(r) == "ready"

    # WO: Approved → In Progress  (cascades WOA to In Progress)
    r = await _workflow(client, "work_order", wo_id, "start")
    assert r["status"] == "success", f"WO start failed: {r.get('message')}"
    assert _state(r) == "in_progress"

    # WOA: In Progress → Completed  (state was cascaded by WO start)
    r = await _workflow(client, "work_order_activity", woa_id, "complete")
    assert r["status"] == "success", f"WOA complete failed: {r.get('message')}"
    assert _state(r) == "completed"

    # Create Work Order Labor Actual Hours (required for WOA close)
    await _create(client, "work_order_labor_actual_hours", {
        "wo_labor_id": labor_id,
        "date": "2026-04-22",
        "time": "08:00",
        "reason": "Test actual hours",
        "comment": "Test comment",
    })

    # Create Work Order Activity Log (required for WOA close)
    await _create(client, "work_order_activity_logs", {
        "work_order_activity": woa_id,
        "log": "Test log entry for WOA close",
    })

    # WOA: Completed → Closed
    r = await _workflow(client, "work_order_activity", woa_id, "close")
    assert r["status"] == "success", f"WOA close failed: {r.get('message')}"
    assert _state(r) == "closed"

    # WO: In Progress → Closed  (requires all WOAs closed)
    r = await _workflow(client, "work_order", wo_id, "complete")
    assert r["status"] == "success", f"WO complete failed: {r.get('message')}"
    assert _state(r) == "closed"

    # MR: Release → Completed  (requires WOA in completed/closed)
    r = await _workflow(client, "maintenance_request", mr_id, "complete")
    assert r["status"] == "success", f"MR complete failed: {r.get('message')}"
    assert _state(r) == "completed"


# ============================================================================
# 5. Maintenance Request — emergency path
# ============================================================================

@pytest.mark.asyncio
async def test_wf_maintenance_request_emergency_path(superuser_client):
    """
    MR (priority=Emergency): Draft → Release  (submit_for_emergency creates WO + WOA)
    → full WO/WOA execution cycle → MR: Complete → Completed.
    """
    client = superuser_client

    uid = uuid.uuid4().hex[:8]
    mr = await _create(client, "maintenance_request", {
        "description": f"E2E MR emergency path {uid}",
        "request_type": "RAT-0005",
        "asset": ASSET_ID,
        "due_date": "2026-04-30",
        "site": SITE,
        "department": DEPT,
        "priority": "Emergency",
    })
    mr_id = mr["id"]

    # Draft → Release  (emergency; creates WO + WOA simultaneously)
    r = await _workflow(client, "maintenance_request", mr_id, "submit_for_emergency")
    assert r["status"] == "success", f"submit_for_emergency failed: {r.get('message')}"
    assert _state(r) == "release"

    woa_id = r["data"].get("work_order_activity")
    assert woa_id, f"submit_for_emergency must link WOA to MR; got data={r['data']}"

    wo_id = await _fetch_field(client, "work_order_activity", woa_id, "work_order")
    assert wo_id, f"WOA '{woa_id}' must have work_order populated after emergency submission"

    # Add labor to WOA
    labor = await _create(client, "work_order_labor", {
        "work_order_activity": woa_id,
        "labor": LABOR_ID,
    })
    labor_id = labor["id"]

    # WO: Requested → Approved
    r = await _workflow(client, "work_order", wo_id, "approve")
    assert r["status"] == "success", f"WO approve failed: {r.get('message')}"
    assert _state(r) == "approved"

    # WOA: Awaiting Resources → Ready
    r = await _workflow(client, "work_order_activity", woa_id, "allocate")
    assert r["status"] == "success", f"WOA allocate failed: {r.get('message')}"
    assert _state(r) == "ready"

    # WO: Approved → In Progress  (cascades WOA)
    r = await _workflow(client, "work_order", wo_id, "start")
    assert r["status"] == "success", f"WO start failed: {r.get('message')}"
    assert _state(r) == "in_progress"

    # WOA: In Progress → Completed
    r = await _workflow(client, "work_order_activity", woa_id, "complete")
    assert r["status"] == "success", f"WOA complete failed: {r.get('message')}"
    assert _state(r) == "completed"

    # Create Work Order Labor Actual Hours (required for WOA close)
    await _create(client, "work_order_labor_actual_hours", {
        "wo_labor_id": labor_id,
        "date": "2026-04-22",
        "time": "08:00",
        "reason": "Test actual hours",
        "comment": "Test comment",
    })

    # Create Work Order Activity Log (required for WOA close)
    await _create(client, "work_order_activity_logs", {
        "work_order_activity": woa_id,
        "log": "Test log entry for WOA close",
    })

    # WOA: Completed → Closed
    r = await _workflow(client, "work_order_activity", woa_id, "close")
    assert r["status"] == "success", f"WOA close failed: {r.get('message')}"
    assert _state(r) == "closed"

    # WO: In Progress → Closed
    r = await _workflow(client, "work_order", wo_id, "complete")
    assert r["status"] == "success", f"WO complete failed: {r.get('message')}"
    assert _state(r) == "closed"

    # MR: Release → Completed
    r = await _workflow(client, "maintenance_request", mr_id, "complete")
    assert r["status"] == "success", f"MR complete failed: {r.get('message')}"
    assert _state(r) == "completed"


# ============================================================================
# 6. Work Order — standalone full lifecycle (no MR)
# ============================================================================

@pytest.mark.asyncio
async def test_wf_work_order_standalone_lifecycle(superuser_client):
    """
    WO (standalone): Requested → Approved → In Progress → Closed.
    WOA lifecycle: Awaiting Resources → Ready → In Progress → Completed.
    """
    client = superuser_client

    # Create WO
    wo = await _create(client, "work_order", {
        "description": "E2E standalone WO — bearing replacement",
        "work_order_type": "Preventive Maintenance",
        "due_date": "2026-04-30",
        "site": SITE,
        "department": DEPT,
    })
    wo_id = wo["id"]
    assert wo.get("workflow_state", "").lower() in ("requested", ""), (
        f"Expected WO initial state 'requested', got '{wo.get('workflow_state')}'"
    )

    # Create WOA
    woa = await _create(client, "work_order_activity", {
        "description": "Replace main bearings",
        "work_order": wo_id,
    })
    woa_id = woa["id"]
    woa_state = woa.get("workflow_state", "").lower().replace(" ", "_")
    assert woa_state in ("awaiting_resources", ""), (
        f"Expected WOA initial state 'awaiting_resources', got '{woa.get('workflow_state')}'"
    )

    # Add labor (required for Allocate)
    labor = await _create(client, "work_order_labor", {
        "work_order_activity": woa_id,
        "labor": LABOR_ID,
    })
    labor_id = labor["id"]

    # WO: Requested → Approved
    r = await _workflow(client, "work_order", wo_id, "approve")
    assert r["status"] == "success", f"WO approve failed: {r.get('message')}"
    assert _state(r) == "approved"

    # WOA: Awaiting Resources → Ready  (requires WO in Approved)
    r = await _workflow(client, "work_order_activity", woa_id, "allocate")
    assert r["status"] == "success", f"WOA allocate failed: {r.get('message')}"
    assert _state(r) == "ready"

    # WO: Approved → In Progress  (requires all WOAs in Ready; cascades WOAs to In Progress)
    r = await _workflow(client, "work_order", wo_id, "start")
    assert r["status"] == "success", f"WO start failed: {r.get('message')}"
    assert _state(r) == "in_progress"

    # WOA: In Progress → Completed  (state was cascaded by WO start)
    r = await _workflow(client, "work_order_activity", woa_id, "complete")
    assert r["status"] == "success", f"WOA complete failed: {r.get('message')}"
    assert _state(r) == "completed"

    # Create Work Order Labor Actual Hours (required for WOA close)
    await _create(client, "work_order_labor_actual_hours", {
        "wo_labor_id": labor_id,
        "date": "2026-04-22",
        "time": "08:00",
        "reason": "Test actual hours",
        "comment": "Test comment",
    })

    # Create Work Order Activity Log (required for WOA close)
    await _create(client, "work_order_activity_logs", {
        "work_order_activity": woa_id,
        "log": "Test log entry for WOA close",
    })

    # WOA: Completed → Closed
    r = await _workflow(client, "work_order_activity", woa_id, "close")
    assert r["status"] == "success", f"WOA close failed: {r.get('message')}"
    assert _state(r) == "closed"

    # WO: In Progress → Closed  (requires all WOAs closed)
    r = await _workflow(client, "work_order", wo_id, "complete")
    assert r["status"] == "success", f"WO complete failed: {r.get('message')}"
    assert _state(r) == "closed"


# ============================================================================
# 7. Work Order Activity — hold / resume cycle
# ============================================================================

@pytest.mark.asyncio
async def test_wf_work_order_activity_hold_resume(superuser_client):
    """
    WOA: Awaiting Resources → Ready → In Progress → On Hold → In Progress → Completed.
    WO completes afterwards.
    """
    client = superuser_client

    wo = await _create(client, "work_order", {
        "description": "E2E WOA hold/resume test",
        "work_order_type": "Corrective Maintenance",
        "due_date": "2026-04-30",
        "site": SITE,
        "department": DEPT,
    })
    wo_id = wo["id"]

    woa = await _create(client, "work_order_activity", {
        "description": "Inspect gearbox",
        "work_order": wo_id,
    })
    woa_id = woa["id"]

    labor = await _create(client, "work_order_labor", {
        "work_order_activity": woa_id,
        "labor": LABOR_ID,
    })
    labor_id = labor["id"]

    # WO approve
    r = await _workflow(client, "work_order", wo_id, "approve")
    assert r["status"] == "success", f"WO approve failed: {r.get('message')}"
    assert _state(r) == "approved"

    # WOA allocate
    r = await _workflow(client, "work_order_activity", woa_id, "allocate")
    assert r["status"] == "success", f"WOA allocate failed: {r.get('message')}"
    assert _state(r) == "ready"

    # WO start  (cascades WOA → In Progress)
    r = await _workflow(client, "work_order", wo_id, "start")
    assert r["status"] == "success", f"WO start failed: {r.get('message')}"
    assert _state(r) == "in_progress"

    # WOA: In Progress → On Hold
    r = await _workflow(client, "work_order_activity", woa_id, "put_on_hold")
    assert r["status"] == "success", f"WOA put_on_hold failed: {r.get('message')}"
    assert _state(r) == "on_hold", f"Expected 'on_hold', got '{_state(r)}'"

    # WOA: On Hold → In Progress  (Resume)
    r = await _workflow(client, "work_order_activity", woa_id, "resume")
    assert r["status"] == "success", f"WOA resume failed: {r.get('message')}"
    assert _state(r) == "in_progress", f"Expected 'in_progress' after resume, got '{_state(r)}'"

    # WOA: In Progress → Completed
    r = await _workflow(client, "work_order_activity", woa_id, "complete")
    assert r["status"] == "success", f"WOA complete failed: {r.get('message')}"
    assert _state(r) == "completed"

    # Create Work Order Labor Actual Hours (required for WOA close)
    await _create(client, "work_order_labor_actual_hours", {
        "wo_labor_id": labor_id,
        "date": "2026-04-22",
        "time": "08:00",
        "reason": "Test actual hours",
        "comment": "Test comment",
    })

    # Create Work Order Activity Log (required for WOA close)
    await _create(client, "work_order_activity_logs", {
        "work_order_activity": woa_id,
        "log": "Test log entry for WOA close",
    })

    # WOA: Completed → Closed
    r = await _workflow(client, "work_order_activity", woa_id, "close")
    assert r["status"] == "success", f"WOA close failed: {r.get('message')}"
    assert _state(r) == "closed"

    # WO: In Progress → Closed
    r = await _workflow(client, "work_order", wo_id, "complete")
    assert r["status"] == "success", f"WO complete failed: {r.get('message')}"
    assert _state(r) == "closed"


# ============================================================================
# 8. Stock Count — full lifecycle
# ============================================================================

@pytest.mark.asyncio
async def test_wf_stock_count_full_lifecycle(superuser_client):
    """
    SC: Planned → In Progress (start_stock_count) → Approved → Closed (complete).

    A stock_count_line linked to an existing inventory record must exist before
    'start_stock_count' is allowed.
    """
    client = superuser_client

    sc = await _create(client, "stock_count", {
        "site": SITE,
        "store": "STR-00001",
        "method": "Guided",
        "basis": "Full",
    })
    sc_id = sc["id"]
    assert sc.get("workflow_state", "").lower() in ("planned", ""), (
        f"Expected SC initial state 'planned', got '{sc.get('workflow_state')}'"
    )

    # Create at least one line (variance_qty=0 → no inventory adjustment created)
    await _create(client, "stock_count_line", {
        "stock_count": sc_id,
        "inventory": INVENTORY_ID,
        "counted_qty": 0,
        "variance_qty": 0,
    })

    # Planned → In Progress
    r = await _workflow(client, "stock_count", sc_id, "start_stock_count")
    assert r["status"] == "success", f"start_stock_count failed: {r.get('message')}"
    assert _state(r) == "in_progress", f"Expected 'in_progress', got '{_state(r)}'"

    # In Progress → Approved  (validates lines; no adjustment since variance=0)
    r = await _workflow(client, "stock_count", sc_id, "approve")
    assert r["status"] == "success", f"SC approve failed: {r.get('message')}"
    assert _state(r) == "approved", f"Expected 'approved', got '{_state(r)}'"

    # Approved → Closed
    r = await _workflow(client, "stock_count", sc_id, "complete")
    assert r["status"] == "success", f"SC complete failed: {r.get('message')}"
    assert _state(r) == "closed", f"Expected 'closed', got '{_state(r)}'"


# ============================================================================
# 9. Purchase Order — workflow disabled by feature flag
# ============================================================================

@pytest.mark.asyncio
async def test_wf_purchase_order_workflow_disabled(superuser_client):
    """
    PO workflow is disabled (PURCHASE_ORDER_ENABLED=False).

    When PO is disabled, the entity may not be registered in MetaRegistry at all,
    so any attempt to interact with PO workflow must return an error response.
    We use a synthetic ID to probe the workflow endpoint — a success response
    would indicate a misconfiguration.
    """
    client = superuser_client

    # Attempt the workflow transition on a non-existent PO record
    # The response must be an error — either "entity not found" (not registered)
    # or "workflow disabled" (registered but blocked by feature flag).
    resp = await client.post(
        ENTITY_WORKFLOW.format(entity="purchase_order"),
        json={"action": "submit", "id": "PO-DISABLED-TEST"},
    )
    assert resp.status_code == 200, (
        f"HTTP {resp.status_code} on PO workflow probe: {resp.text[:300]}"
    )
    r = resp.json()
    assert r["status"] == "error", (
        f"Expected PO workflow to be blocked (PURCHASE_ORDER_ENABLED=False), "
        f"but got status='{r['status']}': {r.get('message')}"
    )
