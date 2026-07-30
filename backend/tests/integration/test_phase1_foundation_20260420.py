"""
Phase 1 – Setting Up
=====================
Tests that all foundational master-data records defined in
docs/business_logics/user-manual/phase-1-setting-up.md can be
created through the generic entity CRUD API.

These records are prerequisites for every later phase.  Each test
is self-contained and uses the function-scoped database session, so
all inserts are rolled back automatically at the end of each test.
"""

from __future__ import annotations

import pytest

ENTITY_ACTION = "/api/entity/{entity}/action"


async def _create(client, entity: str, data: dict) -> dict:
    """POST entity create and assert success.  Returns the created record dict."""
    response = await client.post(
        ENTITY_ACTION.format(entity=entity),
        json={"action": "create", "data": data},
    )
    assert response.status_code == 200, (
        f"HTTP {response.status_code} creating '{entity}'"
    )
    payload = response.json()
    assert payload["status"] == "success", (
        f"Create '{entity}' failed: {payload.get('message')} | errors={payload.get('errors')}"
    )
    assert payload["data"]["id"], f"Created '{entity}' has no id"
    return payload["data"]


# ---------------------------------------------------------------------------
# 1. Organization & Site structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase1_organization_site_cost_code_and_department(
    superuser_client, record_id_factory
):
    """Assert that the top-level company structure can be created in sequence.

    User-manual reference: Phase 1 §1 – Organization & Financial Foundation.
    """
    rid = record_id_factory

    # Organization (top-level company)
    org = await _create(superuser_client, "organization", {
        "organization_name": rid("METPower"),
        "legal_name": "METPower Industries",
        "organizational_code": rid("METPOWER"),
        "is_active": True,
    })

    # Site linked to organization
    site = await _create(superuser_client, "site", {
        "site_name": rid("Polomolok"),
        "organization": org["id"],
    })

    # Cost Code linked to site
    cost_code = await _create(superuser_client, "cost_code", {
        "code": rid("M003"),
        "description": "Global cost code",
        "site": site["id"],
    })

    # Department linked to site + cost code
    dept = await _create(superuser_client, "department", {
        "department_name": rid("Maintenance"),
        "department_code": rid("MAINT-P"),
        "site": site["id"],
        "default_cost_code": cost_code["id"],
    })

    assert org["id"]
    assert site["id"]
    assert cost_code["id"]
    assert dept["id"]


# ---------------------------------------------------------------------------
# 2. Location hierarchy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase1_location_type_and_location(
    superuser_client, record_id_factory
):
    """Assert that a Location Type and a Location can be created.

    User-manual reference: Phase 1 §1 – Location Type / Location.
    """
    rid = record_id_factory

    site = await _create(superuser_client, "site", {
        "site_name": rid("Polomolok"),
    })

    loc_type = await _create(superuser_client, "location_type", {
        "name": rid("Zone"),
    })

    location = await _create(superuser_client, "location", {
        "name": rid("Waste Water Treatment Area"),
        "description": "Operating area for the screw press conveyor and related equipment",
        "location_type": loc_type["id"],
        "site": site["id"],
    })

    assert loc_type["id"]
    assert location["id"]


# ---------------------------------------------------------------------------
# 3. Asset class & equipment master data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase1_asset_class_manufacturer_and_model(
    superuser_client, record_id_factory
):
    """Assert that Asset Class, Manufacturer, and Model can be created.

    User-manual reference: Phase 1 §1 – Asset Class / Manufacturer / Model.
    """
    rid = record_id_factory

    asset_class = await _create(superuser_client, "asset_class", {
        "name": rid("Rotating Equipment"),
        "description": "Motors, pumps, conveyors, rotating machinery",
        "due_date_lead_time": 7,
    })

    manufacturer = await _create(superuser_client, "manufacturer", {
        "company_name": rid("WAMGROUP"),
    })

    model = await _create(superuser_client, "model", {
        "name": rid("Screw Press Conveyor Model S Series"),
        "manufacturer": manufacturer["id"],
    })

    assert asset_class["id"]
    assert manufacturer["id"]
    assert model["id"]


# ---------------------------------------------------------------------------
# 4. Measurement & property master data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase1_unit_of_measure_property_type_and_property(
    superuser_client, record_id_factory
):
    """Assert that Unit of Measure, Property Type, and Property can be created.

    User-manual reference: Phase 1 §1 – UoM / Property Type / Property.
    """
    rid = record_id_factory

    uom = await _create(superuser_client, "unit_of_measure", {
        "name": rid("Nos"),
        "short_name": rid("nos"),
    })

    prop_type = await _create(superuser_client, "property_type", {
        "name": rid("Numeric"),
    })

    prop = await _create(superuser_client, "property", {
        "name": rid("Capacity"),
        "description": "Maximum throughput for the conveyor assembly",
        "unit_of_measure": uom["id"],
        "property_type": prop_type["id"],
        "system": False,
        "inactive": False,
    })

    assert uom["id"]
    assert prop_type["id"]
    assert prop["id"]


# ---------------------------------------------------------------------------
# 5. Labor & workforce master data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase1_labor_group_and_trade(
    superuser_client, record_id_factory
):
    """Assert that Labor Group and Trade records can be created.

    User-manual reference: Phase 1 §1 – Labor Group / Trade.
    """
    rid = record_id_factory

    labor_group = await _create(superuser_client, "labor_group", {
        "labor_group_name": rid("Maintenance Team"),
    })

    trade = await _create(superuser_client, "trade", {
        "trade_name": rid("Mechanic"),
    })

    assert labor_group["id"]
    assert trade["id"]


# ---------------------------------------------------------------------------
# 6. System hierarchy: System Type → System → Position
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase1_system_type_system_and_position(
    superuser_client, record_id_factory
):
    """Assert that the asset system hierarchy can be created.

    User-manual reference: Phase 1 §1 – System Type / System / Position.
    """
    rid = record_id_factory

    site = await _create(superuser_client, "site", {
        "site_name": rid("Polomolok"),
    })

    loc_type = await _create(superuser_client, "location_type", {
        "name": rid("Zone"),
    })
    location = await _create(superuser_client, "location", {
        "name": rid("Waste Water Treatment Area"),
        "location_type": loc_type["id"],
        "site": site["id"],
    })

    asset_class = await _create(superuser_client, "asset_class", {
        "name": rid("Rotating Equipment"),
    })

    system_type = await _create(superuser_client, "system_type", {
        "name": rid("Waste Water System"),
    })

    system = await _create(superuser_client, "system", {
        "name": rid("Screw Press Line A"),
        "description": "Primary screw press conveyor line at the Polomolok site",
        "system_type": system_type["id"],
        "location": location["id"],
        "site": site["id"],
    })

    position = await _create(superuser_client, "position", {
        "position_tag": rid("CONV-LINE-A"),
        "description": "Screw Press Conveyor Position",
        "asset_class": asset_class["id"],
        "system": system["id"],
        "location": location["id"],
    })

    assert system_type["id"]
    assert system["id"]
    assert position["id"]
