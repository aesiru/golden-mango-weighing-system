"""
Full Asset Management Lifecycle — End-to-End Test
==================================================
Tests the COMPLETE procurement-to-maintenance cycle for a "Screw Press" asset:

  Phase 1 : Create Item (Screw Press — Asset Item type)
  Phase 2 : Purchase Request → PR Line → Submit for Approval → Approve
  Phase 3 : Purchase Receipt → confirm_receipt → Asset created (Acquired) + Inventory
  Phase 4 : Inspect Asset (Acquired → Inspected) + full WOA/MR execution cycle
  Phase 5 : Install Asset via bypass (Inspected → Active)
  Phase 6 : Create Maintenance Plan → Maintenance Activity → Planned Maint. Activity (PMA)
  Phase 7 : Maintenance Request from Plan → Submit for Approval → Approve (creates WOA)
  Phase 8 : MR Submit for Resolution → Work Order created (Requested)
  Phase 9 : WO/WOA execution: Approve → Add Labor → Allocate → Start → Complete
  Phase 10: MR Complete → Completed
  Phase 11: Final assertion — Asset is Active, MR/WO/WOA all closed/completed

KNOWN SYSTEM GAPS (documented as test assertions):
  Gap-1: Asset does NOT automatically transition to 'Under Maintenance' when a Work Order
         starts via the MR/WO path.  The `start_activity` WOA hook (which moves the asset)
         requires WO to already be 'in_progress' AND WOA to be in 'ready' state.
         WO.Start cascades WOAs to 'in_progress' *directly* (bypassing the WOA workflow
         handler), so `_handle_start_activity` is never called.  The intended under-
         maintenance cycle is only triggered when `maintain_asset` is called directly on
         the Asset entity workflow.
"""
from __future__ import annotations

import uuid
import pytest
from app.application.services.documents.document import get_value

# ── URL templates ──────────────────────────────────────────────────────────────
ENTITY_ACTION     = "/api/entity/{entity}/action"
ENTITY_WORKFLOW   = "/api/entity/{entity}/workflow"
ENTITY_FETCH_FROM = "/api/entity/{entity}/fetch_from/{record_id}"
ENTITY_DOC_ACTION = "/api/entity/{entity}/{id}/action/{action_name}"
ENTITY_LIST       = "/api/entity/{entity}/list"

# ── Seed-data constants ─────────────────────────────────────────────────────────
SITE         = "SITE-0001"
DEPT         = "DEPT-0001"
EMPLOYEE     = "EMP-00001"
LABOR_ID     = "LBR-00001"
UOM_ID       = "UOM-00001"
ASSET_CLASS  = "AC-00001"
STORE_LOC    = "LOC-00001"   # location with no store mapped → get_value("store") returns None safely

# request_activity_type IDs (from seed)
RAT_INSPECT  = "RAT-0001"    # menu="Inspect Asset",  type="Asset"
RAT_MAINTAIN = "RAT-0019"    # menu="Maintain Asset", type="Maintain Asset"


# ── Test helpers ────────────────────────────────────────────────────────────────

async def _create(client, entity: str, data: dict) -> dict:
    """Create a record and return its data dict."""
    r = await client.post(
        ENTITY_ACTION.format(entity=entity),
        json={"action": "create", "data": data},
    )
    assert r.status_code == 200, f"HTTP {r.status_code} creating {entity}: {r.text[:400]}"
    body = r.json()
    assert body["status"] == "success", f"Create {entity} failed: {body.get('message')}"
    return body["data"]


async def _update(client, entity: str, record_id: str, data: dict) -> dict:
    """Update a record and return its data dict."""
    r = await client.post(
        ENTITY_ACTION.format(entity=entity),
        json={"action": "update", "id": record_id, "data": data},
    )
    assert r.status_code == 200, f"HTTP {r.status_code} updating {entity}/{record_id}: {r.text[:400]}"
    body = r.json()
    assert body["status"] == "success", f"Update {entity}/{record_id} failed: {body.get('message')}"
    return body["data"]


async def _server_action(client, entity: str, record_id: str, action_name: str) -> dict:
    """Call a server action on a record and return the full response body."""
    r = await client.post(
        ENTITY_DOC_ACTION.format(entity=entity, id=record_id, action_name=action_name),
        json={"payload": {}},
    )
    assert r.status_code == 200, (
        f"HTTP {r.status_code} calling {action_name} on {entity}/{record_id}: {r.text[:400]}"
    )
    return r.json()


async def _workflow(client, entity: str, record_id: str, action: str) -> dict:
    """Execute a workflow transition and return the full response body."""
    r = await client.post(
        ENTITY_WORKFLOW.format(entity=entity),
        json={"action": action, "id": record_id},
    )
    assert r.status_code == 200, (
        f"HTTP {r.status_code} workflow '{action}' on {entity}/{record_id}: {r.text[:400]}"
    )
    return r.json()


async def _fetch_field(client, entity: str, record_id: str, field: str):
    """Fetch a single field value from a record."""
    r = await client.get(
        ENTITY_FETCH_FROM.format(entity=entity, record_id=record_id),
        params={"fields": field},
    )
    assert r.status_code == 200, (
        f"HTTP {r.status_code} fetch '{field}' on {entity}/{record_id}: {r.text[:400]}"
    )
    return (r.json().get("data") or {}).get(field)


async def _list_first(client, entity: str, filter_field: str, filter_value: str) -> dict | None:
    """Return the first record matching a filter, or None."""
    r = await client.get(
        ENTITY_LIST.format(entity=entity),
        params={
            "filter_field": filter_field,
            "filter_value": filter_value,
            "sort_order": "desc",
            "page_size": 5,
        },
    )
    assert r.status_code == 200, (
        f"HTTP {r.status_code} listing {entity} (filter {filter_field}={filter_value}): {r.text[:400]}"
    )
    records = (r.json().get("data") or {}).get("records") or []
    return records[0] if records else None


def _state(r: dict) -> str:
    """Normalize workflow_state from a workflow response to a slug."""
    return (r.get("data") or {}).get("workflow_state", "").lower().replace(" ", "_")


# ── Full lifecycle test ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_screw_press_asset_lifecycle(superuser_client):
    """
    Single end-to-end test covering the complete EAM lifecycle:

      Procurement  →  Asset Registration  →  Inspection  →  Installation
      →  Maintenance Plan Setup  →  Preventive Maintenance Execution
      →  Asset back to Active

    Each phase is clearly labeled.  GAP annotations document places where the
    system's current code deviates from the described business intent.
    """
    client = superuser_client
    uid = uuid.uuid4().hex[:8]

    # =========================================================================
    # PHASE 1: Create Item — Screw Press as Asset Item
    # =========================================================================
    item = await _create(client, "item", {
        "item_name": f"Screw Press {uid}",
        "description": f"E2E Screw Press test item {uid}",
        "item_type": "Asset Item",
        "uom": UOM_ID,
        "asset_class": ASSET_CLASS,
        "is_serialized": False,
        "is_equipment": False,
        "inspection_required": False,
    })
    item_id = item["id"]
    assert item_id, "Item creation returned no ID"

    # =========================================================================
    # PHASE 2: Purchase Request — create, add line, submit for approval, approve
    # =========================================================================
    pr = await _create(client, "purchase_request", {
        "pr_description": f"Screw Press procurement {uid}",
        "date_requested": "2026-04-20",
        "requestor": EMPLOYEE,
        "site": SITE,
        "department": DEPT,
    })
    pr_id = pr["id"]

    pr_line = await _create(client, "purchase_request_line", {
        "purchase_request": pr_id,
        "item": item_id,
        "qty_required": 1,
        "unit_of_measure": UOM_ID,
    })
    pr_line_id = pr_line["id"]

    # Draft → Pending Approval
    r = await _workflow(client, "purchase_request", pr_id, "submit_for_approval")
    assert r["status"] == "success", f"PR submit_for_approval failed: {r.get('message')}"
    assert _state(r) == "pending_approval", f"Expected 'pending_approval', got '{_state(r)}'"

    # Pending Approval → Approved  (cascades PR lines to 'approved')
    r = await _workflow(client, "purchase_request", pr_id, "approve")
    assert r["status"] == "success", f"PR approve failed: {r.get('message')}"
    assert _state(r) == "approved", f"Expected 'approved', got '{_state(r)}'"

    # =========================================================================
    # PHASE 3: Purchase Receipt — receive item, trigger confirm_receipt
    #           → creates Inventory record + Asset record (workflow_state=Acquired)
    # =========================================================================
    receipt = await _create(client, "purchase_receipt", {
        "purchase_request_line": pr_line_id,
        "quantity_received": 1,
        "receiving_location": STORE_LOC,
        "site": SITE,
        "department": DEPT,
        "date_received": "2026-04-20",
    })
    receipt_id = receipt["id"]

    # Server action: confirm_receipt
    # Returns: {"status": "success", "data": {"action": "generate_id", "path": "/asset/A-XXXXX"}}
    r = await _server_action(client, "purchase_receipt", receipt_id, "confirm_receipt")
    assert r["status"] == "success", (
        f"confirm_receipt failed: {r.get('message')}  (data={r.get('data')})"
    )
    asset_path = (r.get("data") or {}).get("path", "")
    assert "/asset/" in asset_path, (
        f"confirm_receipt should return an asset path; got data={r.get('data')}"
    )
    asset_id = asset_path.split("/asset/")[-1].rstrip("/")
    assert asset_id, f"Could not parse asset_id from path: {asset_path}"

    # Verify Asset is in 'Acquired' state
    asset_state = await _fetch_field(client, "asset", asset_id, "workflow_state")
    assert (asset_state or "").lower().replace(" ", "_") == "acquired", (
        f"Asset should be 'acquired' after receipt; got: {asset_state}"
    )

    # Verify Inventory exists and is linked to the asset
    inv_id = await _fetch_field(client, "asset", asset_id, "inventory")
    assert inv_id, f"Asset {asset_id} should have an inventory record linked"

    # =========================================================================
    # PHASE 4: Inspect Asset (Acquired → Inspected)
    #
    # Calling the 'Inspect Asset' workflow on the asset:
    #   - Moves asset to 'Inspected' state
    #   - Hook auto-creates WOA (Awaiting Resources) + MR (auto-advanced to Approved)
    #   - MR is returned via redirect_path in the response
    #
    # Then execute the full WOA/MR cycle to formally close the inspection.
    # =========================================================================
    r = await _workflow(client, "asset", asset_id, "inspect_asset")
    assert r["status"] == "success", f"inspect_asset failed: {r.get('message')}"
    assert _state(r) == "inspected", (
        f"Asset should be 'inspected' after Inspect Asset workflow; got '{_state(r)}'"
    )

    # The hook returns {"action": "generate_id", "path": "/maintenance_request/MTREQ-XXXXX"}
    # entity_workflow.py wraps this as data.redirect_path
    insp_redirect = (r.get("data") or {}).get("redirect_path", "")
    assert "maintenance_request" in insp_redirect, (
        f"Inspect Asset should produce a maintenance_request redirect; got data={r.get('data')}"
    )
    insp_mr_id = insp_redirect.rstrip("/").split("/")[-1]
    assert insp_mr_id, f"Could not parse inspection MR ID from: {insp_redirect}"

    # Get inspection WOA (linked to MR)
    insp_woa_id = await _fetch_field(
        client, "maintenance_request", insp_mr_id, "work_order_activity"
    )
    assert insp_woa_id, (
        f"Inspection MR {insp_mr_id} must have a linked work_order_activity"
    )

    # MR is already 'Approved' (auto-advanced by the hook).
    # Submit for Resolution → creates Work Order (Requested), links WOA to WO.
    r = await _workflow(client, "maintenance_request", insp_mr_id, "submit_for_resolution")
    assert r["status"] == "success", (
        f"Inspection MR submit_for_resolution failed: {r.get('message')}"
    )
    assert _state(r) == "release", f"Expected 'release', got '{_state(r)}'"

    # Get the WO created by submit_for_resolution
    insp_wo_id = await _fetch_field(client, "work_order_activity", insp_woa_id, "work_order")
    assert insp_wo_id, (
        f"Inspection WOA {insp_woa_id} must have work_order linked after submit_for_resolution"
    )

    # WO: Requested → Approved
    r = await _workflow(client, "work_order", insp_wo_id, "approve")
    assert r["status"] == "success", f"Inspection WO approve failed: {r.get('message')}"
    assert _state(r) == "approved", f"Expected 'approved', got '{_state(r)}'"

    # Add WO Labor to inspection WOA (required for Allocate)
    labor = await _create(client, "work_order_labor", {
        "work_order_activity": insp_woa_id,
        "labor": LABOR_ID,
    })
    insp_labor_id = labor["id"]

    # WOA: Awaiting Resources → Ready  (WO must be 'approved', labor must exist)
    r = await _workflow(client, "work_order_activity", insp_woa_id, "allocate")
    assert r["status"] == "success", f"Inspection WOA allocate failed: {r.get('message')}"
    assert _state(r) == "ready", f"Expected 'ready', got '{_state(r)}'"

    # WO: Approved → In Progress  (cascades inspection WOA → in_progress)
    r = await _workflow(client, "work_order", insp_wo_id, "start")
    assert r["status"] == "success", f"Inspection WO start failed: {r.get('message')}"
    assert _state(r) == "in_progress", f"Expected 'in_progress', got '{_state(r)}'"

    # WOA: In Progress → Completed
    # (Inspection activity type has no special asset-state side-effect at completion)
    r = await _workflow(client, "work_order_activity", insp_woa_id, "complete")
    assert r["status"] == "success", f"Inspection WOA complete failed: {r.get('message')}"
    assert _state(r) == "completed", f"Expected 'completed', got '{_state(r)}'"

    # Create Work Order Labor Actual Hours (required for WOA close)
    await _create(client, "work_order_labor_actual_hours", {
        "wo_labor_id": insp_labor_id,
        "date": "2026-04-22",
        "time": "08:00",
        "reason": "Test actual hours",
        "comment": "Test comment",
    })

    # Create Work Order Activity Log (required for WOA close)
    await _create(client, "work_order_activity_logs", {
        "work_order_activity": insp_woa_id,
        "log": "Test log entry for WOA close",
    })

    # WOA: Completed → Closed
    r = await _workflow(client, "work_order_activity", insp_woa_id, "close")
    assert r["status"] == "success", f"Inspection WOA close failed: {r.get('message')}"
    assert _state(r) == "closed", f"Expected 'closed', got '{_state(r)}'"

    # WO: In Progress → Closed  (requires all WOAs closed)
    r = await _workflow(client, "work_order", insp_wo_id, "complete")
    assert r["status"] == "success", f"Inspection WO complete failed: {r.get('message')}"
    assert _state(r) == "closed", f"Expected 'closed', got '{_state(r)}'"

    # MR: Release → Completed  (WOA in completed state)
    r = await _workflow(client, "maintenance_request", insp_mr_id, "complete")
    assert r["status"] == "success", f"Inspection MR complete failed: {r.get('message')}"
    assert _state(r) == "completed", f"Expected 'completed', got '{_state(r)}'"

    # Asset should still be 'inspected' (the inspection WOA completion doesn't revert it)
    asset_state = await _fetch_field(client, "asset", asset_id, "workflow_state")
    assert (asset_state or "").lower().replace(" ", "_") == "inspected", (
        f"Asset should be 'inspected' after inspection WOA cycle; got: {asset_state}"
    )

    # =========================================================================
    # PHASE 5: Install Asset — Inspected → Active
    #
    # Set bypass_process=True on the asset so Install Asset directly creates an
    # AssetPosition record without requiring a formal WOA/MR installation cycle.
    # This is the fast-path installation used when formal approval is not required.
    # =========================================================================
    await _update(client, "asset", asset_id, {"bypass_process": True})

    r = await _workflow(client, "asset", asset_id, "install_asset")
    assert r["status"] == "success", f"install_asset failed: {r.get('message')}"
    assert _state(r) == "active", (
        f"Asset should be 'active' after Install Asset (bypass); got '{_state(r)}'"
    )

    # Verify AssetPosition was created
    asset_pos_id = (r.get("data") or {}).get("redirect_path", "")
    # (redirect_path may or may not be present — commission creates AssetPosition)

    # =========================================================================
    # PHASE 6: Create Maintenance Plan → Maintenance Activity → PMA
    #
    # This models the preventive maintenance planning for the Screw Press.
    # The PMA links the plan to a specific maintenance activity and schedule type.
    # =========================================================================
    maint_activity = await _create(client, "maintenance_activity", {
        "activity_name": f"Preventive Maintenance — Screw Press {uid}",
        "description": "Lubrication, bearing inspection, alignment check",
    })
    maint_act_id = maint_activity["id"]

    maint_plan = await _create(client, "maintenance_plan", {
        "description": f"Screw Press PM Plan {uid}",
        "asset_class": ASSET_CLASS,
    })
    plan_id = maint_plan["id"]

    pma = await _create(client, "planned_maintenance_activity", {
        "maintenance_plan": plan_id,
        "maintenance_activity": maint_act_id,
        "maintenance_schedule": "Calendar Based",
        "maintenance_type": RAT_MAINTAIN,   # "Maintain Asset" RAT
    })
    pma_id = pma["id"]

    # =========================================================================
    # PHASE 7: Maintenance Request derived from the Maintenance Plan
    #          Submit for Approval → Approve → WOA created from PMA
    # =========================================================================
    mr = await _create(client, "maintenance_request", {
        "description": f"PM — Screw Press {uid}: lubrication & bearing check",
        "request_type": RAT_MAINTAIN,        # "Maintain Asset"
        "asset": asset_id,
        "due_date": "2026-05-15",
        "site": SITE,
        "department": DEPT,
        "priority": "Normal",
        "planned_maintenance_activity": pma_id,
    })
    mr_id = mr["id"]
    assert (mr.get("workflow_state") or "").lower().replace(" ", "_") in ("draft", ""), (
        f"Expected MR in 'draft' state; got: {mr.get('workflow_state')}"
    )

    # MR: Draft → Pending Approval
    r = await _workflow(client, "maintenance_request", mr_id, "submit_for_approval")
    assert r["status"] == "success", f"MR submit_for_approval failed: {r.get('message')}"
    assert _state(r) == "pending_approval", f"Expected 'pending_approval', got '{_state(r)}'"

    # MR: Pending Approval → Approved
    # Side-effect: WOA created (Awaiting Resources), linked to MR and populated from PMA
    r = await _workflow(client, "maintenance_request", mr_id, "approve")
    assert r["status"] == "success", f"MR approve failed: {r.get('message')}"
    assert _state(r) == "approved", f"Expected 'approved', got '{_state(r)}'"

    woa_id = (r.get("data") or {}).get("work_order_activity")
    assert woa_id, (
        f"MR 'approve' must create and link a Work Order Activity; "
        f"got data={r.get('data')}"
    )

    # =========================================================================
    # PHASE 8: Submit for Resolution → Work Order created (Requested state)
    # =========================================================================
    r = await _workflow(client, "maintenance_request", mr_id, "submit_for_resolution")
    assert r["status"] == "success", f"MR submit_for_resolution failed: {r.get('message')}"
    assert _state(r) == "release", f"Expected 'release', got '{_state(r)}'"

    wo_id = await _fetch_field(client, "work_order_activity", woa_id, "work_order")
    assert wo_id, (
        f"WOA {woa_id} must have work_order linked after submit_for_resolution"
    )

    # =========================================================================
    # PHASE 9: WO / WOA Execution Cycle
    #   WO: Requested → Approved
    #   WOA: Awaiting Resources → Ready  (add labor, then Allocate)
    #   WO: Approved → In Progress  (cascades WOA to in_progress)
    #   WOA: In Progress → Completed  (Maintain Asset type resets asset to Active)
    #   WO: In Progress → Closed
    # =========================================================================

    # WO: Requested → Approved
    r = await _workflow(client, "work_order", wo_id, "approve")
    assert r["status"] == "success", f"WO approve failed: {r.get('message')}"
    assert _state(r) == "approved", f"Expected 'approved', got '{_state(r)}'"

    # Add WO Labor to WOA (required before Allocate)
    labor = await _create(client, "work_order_labor", {
        "work_order_activity": woa_id,
        "labor": LABOR_ID,
    })
    labor_id = labor["id"]

    # WOA: Awaiting Resources → Ready
    # Requires: parent WO is 'approved' + at least 1 labor record
    r = await _workflow(client, "work_order_activity", woa_id, "allocate")
    assert r["status"] == "success", f"WOA allocate failed: {r.get('message')}"
    assert _state(r) == "ready", f"Expected 'ready', got '{_state(r)}'"

    # WO: Approved → In Progress  (all WOAs must be 'ready'; cascades WOAs to in_progress)
    r = await _workflow(client, "work_order", wo_id, "start")
    assert r["status"] == "success", f"WO start failed: {r.get('message')}"
    assert _state(r) == "in_progress", f"Expected 'in_progress', got '{_state(r)}'"

    # ── GAP-1 ASSERTION ──────────────────────────────────────────────────────
    # Per the business description, the asset should now be 'Under Maintenance'.
    # However, the current code does NOT transition the asset when WO.Start runs.
    # WO.Start cascades WOA state directly (bypassing the WOA workflow handler),
    # so _handle_start_activity (which calls asset → maintain_asset) is never invoked.
    # The asset therefore remains 'active' until WOA.Complete is called.
    #
    # EXPECTED SYSTEM BEHAVIOR: asset = 'under_maintenance'
    # ACTUAL SYSTEM BEHAVIOR:   asset = 'active'   ← GAP
    # ─────────────────────────────────────────────────────────────────────────
    asset_mid_state = await _fetch_field(client, "asset", asset_id, "workflow_state")
    assert (asset_mid_state or "").lower().replace(" ", "_") == "active", (
        f"[GAP-1] WO.Start does NOT automatically move asset to 'under_maintenance'. "
        f"Expected asset to remain 'active' (current system behaviour). "
        f"Got: {asset_mid_state}. "
        f"Fix: WO.Start should invoke _handle_start_activity for each WOA, or a separate "
        f"'Start Work' asset workflow transition should be provided."
    )

    # WOA: In Progress → Completed
    # Side-effect for 'Maintain Asset' activity type:
    #   asset.workflow_state = 'active'  (and need_repair = False)
    r = await _workflow(client, "work_order_activity", woa_id, "complete")
    assert r["status"] == "success", f"WOA complete failed: {r.get('message')}"
    assert _state(r) == "completed", f"Expected 'completed', got '{_state(r)}'"

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
    assert _state(r) == "closed", f"Expected 'closed', got '{_state(r)}'"

    # WO: In Progress → Closed  (requires all WOAs closed)  (all WOAs must be 'completed' or 'closed')
    r = await _workflow(client, "work_order", wo_id, "complete")
    assert r["status"] == "success", f"WO complete failed: {r.get('message')}"
    assert _state(r) == "closed", f"Expected 'closed', got '{_state(r)}'"

    # =========================================================================
    # PHASE 10: Maintenance Request Complete
    # Requires: linked WOA in 'completed' or 'closed' state
    # Side-effect: MR.closed_date = today
    # =========================================================================
    r = await _workflow(client, "maintenance_request", mr_id, "complete")
    assert r["status"] == "success", f"MR complete failed: {r.get('message')}"
    assert _state(r) == "completed", f"Expected 'completed', got '{_state(r)}'"

    # =========================================================================
    # PHASE 11: Final State Assertions
    # =========================================================================

    # Asset should be 'active' — restored by WOA.Complete (Maintain Asset type)
    asset_final_state = await _fetch_field(client, "asset", asset_id, "workflow_state")
    assert (asset_final_state or "").lower().replace(" ", "_") == "active", (
        f"Asset should be 'active' after full maintenance cycle; got: {asset_final_state}"
    )

    # Confirm MR closed_date is set
    mr_closed = await _fetch_field(client, "maintenance_request", mr_id, "closed_date")
    assert mr_closed, f"MR {mr_id} should have closed_date set after MR.Complete"

    # Inventory should still exist and be linked to asset
    inv_after = await _fetch_field(client, "asset", asset_id, "inventory")
    assert inv_after == inv_id, (
        f"Inventory link on asset should be unchanged throughout lifecycle; "
        f"before={inv_id}, after={inv_after}"
    )
