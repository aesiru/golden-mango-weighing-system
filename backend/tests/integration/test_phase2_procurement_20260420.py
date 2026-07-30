"""
Phase 2 – Item Acquisition and Procurement
============================================
Tests that the Item Catalog and Purchase Request workflow work end-to-end
as described in docs/business_logics/user-manual/phase-2-item-acquisition-procurement.md.

Covers:
  • Item Class creation
  • Item creation (Fixed Asset type)
  • Purchase Request creation (starts in Draft)
  • Full PR workflow: Draft → Pending Review → Pending Approval → Approved
"""

from __future__ import annotations

import pytest

ENTITY_ACTION = "/api/entity/{entity}/action"
ENTITY_WORKFLOW = "/api/entity/{entity}/workflow"


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


async def _workflow(client, entity: str, record_id: str, action: str) -> dict:
    """Execute a workflow transition and return the response payload."""
    response = await client.post(
        ENTITY_WORKFLOW.format(entity=entity),
        json={"action": action, "id": record_id},
    )
    assert response.status_code == 200, (
        f"HTTP {response.status_code} on workflow action '{action}' for '{entity}'"
    )
    return response.json()


# ---------------------------------------------------------------------------
# 1. Item Catalog
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase2_item_class_and_fixed_asset_item_can_be_created(
    superuser_client, record_id_factory
):
    """Assert that an Item Class and a Fixed Asset Item can be created.

    User-manual reference: Phase 2 §1 – Item Catalog Setup.
    """
    rid = record_id_factory

    uom = await _create(superuser_client, "unit_of_measure", {
        "name": rid("Nos"),
        "short_name": rid("nos"),
    })

    asset_class = await _create(superuser_client, "asset_class", {
        "name": rid("Rotating Equipment"),
    })

    item_class = await _create(superuser_client, "item_class", {
        "item_class_name": rid("Equipment"),
        "description": "Equipment and spare parts",
        "item_class_type": "Fixed Asset Item",
        "asset_class": asset_class["id"],
        "default_uom": uom["id"],
        "valuation_method": "FIFO",
        "inventory_tracking": True,
        "is_serialized": True,
        "is_active": True,
    })

    item = await _create(superuser_client, "item", {
        "item_name": rid("Screw Press Conveyor Assembly"),
        "description": "Complete screw press conveyor assembly for the Polomolok waste water line",
        "item_class": item_class["id"],
        "item_type": "Fixed Asset Item",
        "uom": uom["id"],
        "is_serialized": True,
        "inspection_required": True,
        "is_equipment": True,
    })

    assert item_class["id"]
    assert item["id"]


@pytest.mark.asyncio
async def test_phase2_inventory_item_can_be_created(
    superuser_client, record_id_factory
):
    """Assert that a non-serialized Inventory Item (spare part) can be created.

    User-manual reference: Phase 2 §1 – Spare Parts Items.
    """
    rid = record_id_factory

    uom = await _create(superuser_client, "unit_of_measure", {
        "name": rid("Set"),
        "short_name": rid("set"),
    })

    item_class = await _create(superuser_client, "item_class", {
        "item_class_name": rid("Spare Parts"),
        "description": "Non-serialized spare parts",
        "item_class_type": "Inventory Item",
        "default_uom": uom["id"],
        "is_serialized": False,
        "is_active": True,
    })

    item = await _create(superuser_client, "item", {
        "item_name": rid("Bearings Set"),
        "description": "High-speed bearings for conveyor motor",
        "item_class": item_class["id"],
        "item_type": "Inventory Item",
        "uom": uom["id"],
        "is_serialized": False,
        "is_equipment": True,
    })

    assert item["id"]


# ---------------------------------------------------------------------------
# 2. Purchase Request workflow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase2_purchase_request_can_be_created_in_draft(
    superuser_client, record_id_factory
):
    """Assert that a Purchase Request is created with workflow_state=Draft.

    User-manual reference: Phase 2 §2 – Purchase Request Process.
    """
    rid = record_id_factory

    pr = await _create(superuser_client, "purchase_request", {
        "pr_description": rid("PR for Screw Press Conveyor"),
        "date_requested": "2026-04-20",
        "requestor": "EMP-00001",
        "site": "SITE-0001",
        "department": "DEPT-0001",
    })

    # The PR must start in Draft state (initial state in entity metadata)
    state = (pr.get("workflow_state") or "").lower()
    assert state in ("draft", ""), (
        f"Expected PR to start in Draft state, got '{state}'"
    )
    assert pr["id"]


@pytest.mark.asyncio
async def test_phase2_purchase_request_workflow_draft_to_approved(
    superuser_client, record_id_factory
):
    """Assert that a PR can move through Draft → Pending Review → Pending Approval → Approved.

    User-manual reference: Phase 2 §2 – Purchase Request Workflow.
    """
    rid = record_id_factory

    pr = await _create(superuser_client, "purchase_request", {
        "pr_description": rid("PR workflow test"),
        "date_requested": "2026-04-20",
        "requestor": "EMP-00001",
        "site": "SITE-0001",
        "department": "DEPT-0001",
    })
    pr_id = pr["id"]

    # Add a purchase request line (required for submit_for_review)
    await _create(superuser_client, "purchase_request_line", {
        "purchase_request": pr_id,
        "item": "ITM-00001",
        "qty_required": 1,
        "unit_of_measure": "UOM-00001",
    })

    # Step 1: Draft → Pending Review
    step1 = await _workflow(superuser_client, "purchase_request", pr_id, "submit_for_review")
    assert step1["status"] == "success", f"submit_for_review failed: {step1.get('message')}"
    assert (step1.get("data") or {}).get("workflow_state", "").lower().replace(" ", "_") == "pending_review"

    # Step 2: Pending Review → Pending Approval
    step2 = await _workflow(superuser_client, "purchase_request", pr_id, "submit_for_approval")
    assert step2["status"] == "success", f"submit_for_approval failed: {step2.get('message')}"
    assert (step2.get("data") or {}).get("workflow_state", "").lower().replace(" ", "_") == "pending_approval"

    # Step 3: Pending Approval → Approved
    step3 = await _workflow(superuser_client, "purchase_request", pr_id, "approve")
    assert step3["status"] == "success", f"approve failed: {step3.get('message')}"
    assert (step3.get("data") or {}).get("workflow_state", "").lower().replace(" ", "_") == "approved"
