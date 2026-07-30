"""Purchase Receipt — Non-Inventory Item confirm_receipt behavior.

Ensures that `confirm_receipt` allows completion for Non-Inventory Items but
creates NO inventory records.

Regression target: purchasing_stores/apis/purchase_receipt.py
"""

from __future__ import annotations

import pytest


ENTITY_ACTION = "/api/entity/{entity}/action"
ENTITY_DOC_ACTION = "/api/entity/{entity}/{id}/action/{action_name}"
ENTITY_FETCH_FROM = "/api/entity/{entity}/fetch_from/{record_id}"


async def _create(client, entity: str, data: dict) -> dict:
    r = await client.post(
        ENTITY_ACTION.format(entity=entity),
        json={"action": "create", "data": data},
    )
    assert r.status_code == 200, f"HTTP {r.status_code} creating {entity}: {r.text[:400]}"
    body = r.json()
    assert body["status"] == "success", f"Create {entity} failed: {body.get('message')}"
    return body["data"]


async def _server_action(client, entity: str, record_id: str, action_name: str) -> dict:
    r = await client.post(
        ENTITY_DOC_ACTION.format(entity=entity, id=record_id, action_name=action_name),
        json={"payload": {}},
    )
    assert r.status_code == 200, (
        f"HTTP {r.status_code} calling {action_name} on {entity}/{record_id}: {r.text[:400]}"
    )
    return r.json()


async def _fetch_fields(client, entity: str, record_id: str, fields: str) -> dict:
    r = await client.get(
        ENTITY_FETCH_FROM.format(entity=entity, record_id=record_id),
        params={"fields": fields},
    )
    assert r.status_code == 200, (
        f"HTTP {r.status_code} fetch '{fields}' on {entity}/{record_id}: {r.text[:400]}"
    )
    return r.json().get("data") or {}


@pytest.mark.asyncio
async def test_confirm_receipt_allows_non_inventory_item_without_inventory_records(
    superuser_client, record_id_factory
):
    rid = record_id_factory

    uom = await _create(superuser_client, "unit_of_measure", {
        "name": rid("Box"),
        "short_name": rid("box"),
    })

    item_class = await _create(superuser_client, "item_class", {
        "item_class_name": rid("Consumables"),
        "description": "Non-stock consumables",
        "item_class_type": "Non Inventory Item",
        "default_uom": uom["id"],
        "is_serialized": False,
        "is_active": True,
    })

    item = await _create(superuser_client, "item", {
        "item_name": rid("Cleaning Chemicals"),
        "description": "Non-stock cleaning chemicals",
        "item_class": item_class["id"],
        "item_type": "Non Inventory Item",
        "uom": uom["id"],
        "is_serialized": False,
        "is_equipment": False,
    })

    pr = await _create(superuser_client, "purchase_request", {
        "pr_description": rid("PR non-inventory"),
        "date_requested": "2026-05-11",
        "requestor": "EMP-00001",
        "site": "SITE-0001",
        "department": "DEPT-0001",
    })

    pr_line = await _create(superuser_client, "purchase_request_line", {
        "purchase_request": pr["id"],
        "item": item["id"],
        "qty_required": 2,
        "unit_of_measure": uom["id"],
        "site": "SITE-0001",
        "department": "DEPT-0001",
    })

    receipt = await _create(superuser_client, "purchase_receipt", {
        "purchase_request_line": pr_line["id"],
        "item": item["id"],
        "quantity_received": 2,
        "receiving_location": "LOC-00001",
        "site": "SITE-0001",
        "department": "DEPT-0001",
        "date_received": "2026-05-11",
    })

    r = await _server_action(superuser_client, "purchase_receipt", receipt["id"], "confirm_receipt")
    assert r["status"] == "success", f"confirm_receipt should succeed for non-inventory: {r}"

    receipt_after = await _fetch_fields(
        superuser_client,
        "purchase_receipt",
        receipt["id"],
        "generated_inventory,is_received",
    )
    assert receipt_after.get("generated_inventory") in (True, 1), receipt_after
    assert receipt_after.get("is_received") in (True, 1), receipt_after

    inv_list = await superuser_client.get(
        "/api/entity/inventory/list",
        params={"filters": f'{{"item": "{item["id"]}", "transaction_type": "Add"}}'},
    )
    assert inv_list.status_code == 200, inv_list.text[:400]
    inv_body = inv_list.json()
    assert inv_body["status"] == "success", inv_body
    
    # Filter out any existing inventory records and check no new ones were created
    existing_inv = [inv for inv in (inv_body.get("data") or []) if inv.get("item") == item["id"]]
    assert existing_inv == [], (
        f"Expected no inventory records for Non Inventory Item {item['id']}; got: {existing_inv}"
    )
