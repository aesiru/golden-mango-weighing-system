#!/usr/bin/env python3
"""Seed masterfiles from the masterfiles workbook directory.

Authoritative source: masterfiles Excel workbooks.

Design goals:
- Seed masterfiles FIRST.
- Skip note/sample rows and ignore unnamed note columns.
- Be idempotent (skip if ID exists).
- Use correct DB column names (based on observed schema).

This script only handles masterfiles + close-to-master entities found in the masterfiles workbooks.
Transactional seeding should happen after this script.
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from app.core.database import async_session_maker


def _first_existing_dir(*candidates: Path) -> Path:
    for c in candidates:
        if c and c.exists() and c.is_dir():
            return c
    return candidates[0]


REPO_MASTERFILES_DIR = Path(__file__).resolve().parent.parent / "masterfiles"
DOWNLOADS_MASTERFILES_DIR = Path.home() / "Downloads" / "eam2.1" / "masterfiles"

MASTERFILES_DIR = _first_existing_dir(
    Path(os.getenv("EAM_MASTERFILES_DIR")) if os.getenv("EAM_MASTERFILES_DIR") else None,
    DOWNLOADS_MASTERFILES_DIR,
    REPO_MASTERFILES_DIR,
)

ASSET_MASTERFILES = Path(os.getenv("EAM_ASSET_MASTERFILES", str(MASTERFILES_DIR / "Asset Masterfiles.xlsx")))
CORE_MASTERFILES = Path(os.getenv("EAM_CORE_MASTERFILES", str(MASTERFILES_DIR / "Core Masterfiles.xlsx")))
MAINTENANCE_MASTERFILES = Path(os.getenv("EAM_MAINTENANCE_MASTERFILES", str(MASTERFILES_DIR / "Maintenance Masterfiles.xlsx")))


def _assert_workbook_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing workbook: {path}. Set EAM_MASTERFILES_DIR or EAM_ASSET_MASTERFILES/EAM_CORE_MASTERFILES/EAM_MAINTENANCE_MASTERFILES."
        )


def clean_value(value):
    if pd.isna(value) or value == "" or value == "nan":
        return None
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return None
        return v
    return value


def to_bool(value):
    """Convert common Excel encodings (0/1, yes/no, true/false) to bool/None."""
    v = clean_value(value)
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        if v == 1:
            return True
        if v == 0:
            return False
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"1", "true", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "no", "n", "off"}:
            return False
    return None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for c in list(df.columns):
        if c.startswith("Unnamed") or c in {"Note:", "Note"}:
            df.drop(columns=[c], inplace=True)
    return df


def iter_rows(df: pd.DataFrame):
    df = normalize_columns(df)
    for _, row in df.iterrows():
        rid = clean_value(row.get("ID"))
        if not rid:
            continue
        yield row


async def exists(db, table: str, rid: str) -> bool:
    res = await db.execute(text(f"SELECT 1 FROM {table} WHERE id = :id LIMIT 1"), {"id": rid})
    return res.scalar_one_or_none() is not None


async def next_series_id(db, table: str, prefix: str, width: int = 5) -> str:
    res = await db.execute(
        text(
            "SELECT id FROM "
            + table
            + " WHERE id LIKE :p ORDER BY id DESC LIMIT 1"
        ),
        {"p": f"{prefix}%"},
    )
    last_id = res.scalar_one_or_none()
    if last_id and isinstance(last_id, str) and last_id.startswith(prefix):
        tail = last_id[len(prefix) :]
        try:
            n = int(tail)
        except Exception:
            n = 0
    else:
        n = 0
    return f"{prefix}{str(n + 1).zfill(width)}"


async def resolve_id(db, table: str, value: str, *, id_prefixes: tuple[str, ...] = (), name_columns: tuple[str, ...] = ("name",)):
    """Resolve a reference that may be either an ID or a human-readable name.

    - If `value` matches an existing id, return it.
    - If `id_prefixes` provided, treat values starting with those prefixes as IDs.
    - Otherwise try lookup by any of `name_columns`.
    """
    value = clean_value(value)
    if not value:
        return None

    if id_prefixes and any(value.startswith(p) for p in id_prefixes):
        res = await db.execute(text(f"SELECT id FROM {table} WHERE id = :v LIMIT 1"), {"v": value})
        return res.scalar_one_or_none()

    # try by id
    res = await db.execute(text(f"SELECT id FROM {table} WHERE id = :v LIMIT 1"), {"v": value})
    found = res.scalar_one_or_none()
    if found:
        return found

    for col in name_columns:
        res = await db.execute(text(f"SELECT id FROM {table} WHERE {col} = :v LIMIT 1"), {"v": value})
        found = res.scalar_one_or_none()
        if found:
            return found
    return None


async def upsert_by_id(db, table: str, rid: str, values: dict):
    """Generic update-if-exists else insert for tables with `id` PK."""
    rid = clean_value(rid)
    if not rid:
        return False

    # remove None-only keys is NOT done; we want masterfiles to be authoritative, including clearing.
    cols = list(values.keys())
    if await exists(db, table, rid):
        set_clause = ", ".join([f"{c} = :{c}" for c in cols] + ["updated_at = :updated_at"])
        params = {"id": rid, **values, "updated_at": datetime.now()}
        await db.execute(text(f"UPDATE {table} SET {set_clause} WHERE id = :id"), params)
        return False

    insert_cols = ", ".join(["id"] + cols + ["created_at", "updated_at"])
    insert_vals = ", ".join([":id"] + [f":{c}" for c in cols] + [":created_at", ":updated_at"])
    params = {"id": rid, **values, "created_at": datetime.now(), "updated_at": datetime.now()}
    await db.execute(text(f"INSERT INTO {table} ({insert_cols}) VALUES ({insert_vals})"), params)
    return True


async def seed_simple_name_table(db, *, xlsx: Path, sheet: str, table: str, name_col: str):
    df = pd.read_excel(xlsx, sheet_name=sheet)
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        if await exists(db, table, rid):
            continue
        name = clean_value(row.get(name_col))
        await db.execute(
            text(f"INSERT INTO {table} (id, name, created_at, updated_at) VALUES (:id, :name, :c, :u)"),
            {"id": rid, "name": name, "c": datetime.now(), "u": datetime.now()},
        )
        inserted += 1
    return inserted


async def seed_location_types(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Location Type")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        name = clean_value(row.get("Location Type"))
        if await upsert_by_id(db, "location_type", rid, {"name": name}):
            inserted += 1
    return inserted


async def seed_system_types(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="System Type")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        name = clean_value(row.get("System Type"))
        if await upsert_by_id(db, "system_type", rid, {"name": name}):
            inserted += 1
    return inserted


async def seed_locations(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Location")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        name = clean_value(row.get("Name"))
        desc = clean_value(row.get("Description"))
        lt_ref = clean_value(row.get("Location Type"))
        parent_ref = clean_value(row.get("Parent Location"))
        site_ref = clean_value(row.get("Site"))

        lt_id = await resolve_id(db, "location_type", lt_ref, id_prefixes=("LT-",), name_columns=("name",))
        parent_id = await resolve_id(db, "location", parent_ref, id_prefixes=("LOC-",), name_columns=("name", "location_name"))
        site_id = await resolve_id(db, "site", site_ref, id_prefixes=("SITE-",), name_columns=("site_name", "site_code"))

        lt_name = None
        if lt_id:
            res = await db.execute(text("SELECT name FROM location_type WHERE id=:id"), {"id": lt_id})
            lt_name = res.scalar_one_or_none()

        values = {
            "name": name,
            "description": desc,
            "location_type": lt_id,
            "location_type_name": lt_name,
            "parent_location": parent_id,
            "site": site_id,
            "latitude": clean_value(row.get("Latitude")),
            "longitude": clean_value(row.get("Longitude")),
            "address": clean_value(row.get("Address")),
            "location_name": name,
        }
        if await upsert_by_id(db, "location", rid, values):
            inserted += 1
    return inserted


async def seed_systems(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="System")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        name = clean_value(row.get("Name"))
        desc = clean_value(row.get("Description"))
        st_ref = clean_value(row.get("System Type"))
        parent_ref = clean_value(row.get("Parent System"))
        loc_ref = clean_value(row.get("Location"))
        site_ref = clean_value(row.get("Site"))

        st_id = await resolve_id(db, "system_type", st_ref, id_prefixes=("ST-",), name_columns=("name",))
        parent_id = await resolve_id(db, "system", parent_ref, id_prefixes=("SYS-",), name_columns=("name", "system_name"))
        loc_id = await resolve_id(db, "location", loc_ref, id_prefixes=("LOC-",), name_columns=("name", "location_name"))
        site_id = await resolve_id(db, "site", site_ref, id_prefixes=("SITE-",), name_columns=("site_name", "site_code"))

        st_name = None
        if st_id:
            res = await db.execute(text("SELECT name FROM system_type WHERE id=:id"), {"id": st_id})
            st_name = res.scalar_one_or_none()

        parent_name = None
        if parent_id:
            res = await db.execute(text("SELECT COALESCE(system_name, name) FROM system WHERE id=:id"), {"id": parent_id})
            parent_name = res.scalar_one_or_none()

        loc_name = None
        if loc_id:
            res = await db.execute(text("SELECT COALESCE(location_name, name) FROM location WHERE id=:id"), {"id": loc_id})
            loc_name = res.scalar_one_or_none()

        site_name = None
        if site_id:
            res = await db.execute(text("SELECT site_name FROM site WHERE id=:id"), {"id": site_id})
            site_name = res.scalar_one_or_none()

        values = {
            "name": name,
            "description": desc,
            "system_type": st_id,
            "system_type_name": st_name,
            "parent_system": parent_id,
            "location": loc_id,
            "site": site_id,
            "system_name": name,
            "parent_system_name": parent_name,
            "location_name": loc_name,
            "site_name": site_name,
        }
        if await upsert_by_id(db, "system", rid, values):
            inserted += 1
    return inserted


async def seed_units_of_measure(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Unit Of Measure")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        values = {"name": clean_value(row.get("Name")), "short_name": clean_value(row.get("Short Name"))}
        if await upsert_by_id(db, "unit_of_measure", rid, values):
            inserted += 1
    return inserted


async def seed_property_types(db):
    """Seed property_type from the Property worksheet references."""
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Property")
    inserted = 0
    for row in iter_rows(df):
        pt_id = clean_value(row.get("Property Type"))
        pt_name = clean_value(row.get("Property Type Name"))
        if not pt_id or not pt_name:
            continue
        if await upsert_by_id(db, "property_type", pt_id, {"name": pt_name}):
            inserted += 1
    return inserted


async def seed_properties(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Property")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        pname = clean_value(row.get("Property Name"))
        desc = clean_value(row.get("Description"))
        uom_ref = clean_value(row.get("Unit of Measure"))
        system_ref = clean_value(row.get("System"))

        uom_id = await resolve_id(db, "unit_of_measure", uom_ref, id_prefixes=("UOM-",), name_columns=("name", "short_name"))
        uom_name = None
        if uom_id:
            res = await db.execute(text("SELECT name FROM unit_of_measure WHERE id=:id"), {"id": uom_id})
            uom_name = res.scalar_one_or_none()

        system_id = await resolve_id(db, "system", system_ref, id_prefixes=("SYS-",), name_columns=("name", "system_name"))

        pt_ref = clean_value(row.get("Property Type"))
        pt_name = clean_value(row.get("Property Type Name"))
        pt_id = await resolve_id(db, "property_type", pt_ref, id_prefixes=("PT-",), name_columns=("name",))
        if pt_ref and not pt_id and pt_ref.startswith("PT-"):
            # Create missing property_type on-the-fly to satisfy FK
            await upsert_by_id(db, "property_type", pt_ref, {"name": pt_name})
            pt_id = pt_ref
        values = {
            "name": pname,
            "description": desc,
            "unit_of_measure": uom_id,
            "unit_of_measure_name": uom_name,
            "property_type": pt_id,
            "property_type_name": pt_name,
            "system": system_id,
            "inactive": to_bool(row.get("Inactive")),
        }
        if await upsert_by_id(db, "property", rid, values):
            inserted += 1
    return inserted


async def seed_organizations(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Organization")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        name = clean_value(row.get("Name"))
        code = clean_value(row.get("Code"))
        legal_name = clean_value(row.get("Legal Name"))
        if name is None:
            name = rid
        if legal_name is None:
            legal_name = name
        is_active = clean_value(row.get("Is Active"))
        if await exists(db, "organization", rid):
            await db.execute(
                text(
                    "UPDATE organization SET organization_name=:n, legal_name=:legal, organizational_code=:code, is_active=:active, updated_at=:u "
                    "WHERE id=:id"
                ),
                {
                    "id": rid,
                    "n": name,
                    "legal": legal_name,
                    "code": code,
                    "active": bool(is_active) if is_active is not None else None,
                    "u": datetime.now(),
                },
            )
        else:
            await db.execute(
                text(
                    "INSERT INTO organization (id, organization_name, legal_name, organizational_code, is_active, created_at, updated_at) "
                    "VALUES (:id, :n, :legal, :code, :active, :c, :u)"
                ),
                {
                    "id": rid,
                    "n": name,
                    "legal": legal_name,
                    "code": code,
                    "active": bool(is_active) if is_active is not None else None,
                    "c": datetime.now(),
                    "u": datetime.now(),
                },
            )
            inserted += 1
    return inserted


async def seed_sites(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Site")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        # Sheet columns are 'Site Name' and 'Site Code'
        site_name = clean_value(row.get("Site Name"))
        site_code = clean_value(row.get("Site Code"))
        org = clean_value(row.get("Organization"))
        org_name = clean_value(row.get("Organization Name"))
        default_cost_code = clean_value(row.get("Default Cost Code"))
        if await exists(db, "site", rid):
            await db.execute(
                text(
                    "UPDATE site SET site_name=:n, site_code=:code, organization=:org, organization_name=:org_name, default_cost_code=:dcc, updated_at=:u "
                    "WHERE id=:id"
                ),
                {
                    "id": rid,
                    "n": site_name,
                    "code": site_code,
                    "org": org,
                    "org_name": org_name,
                    "dcc": default_cost_code,
                    "u": datetime.now(),
                },
            )
        else:
            await db.execute(
                text(
                    "INSERT INTO site (id, site_name, site_code, organization, organization_name, default_cost_code, created_at, updated_at) "
                    "VALUES (:id, :n, :code, :org, :org_name, :dcc, :c, :u)"
                ),
                {
                    "id": rid,
                    "n": site_name,
                    "code": site_code,
                    "org": org,
                    "org_name": org_name,
                    "dcc": default_cost_code,
                    "c": datetime.now(),
                    "u": datetime.now(),
                },
            )
            inserted += 1
    return inserted


async def seed_departments(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Department")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        dept_name = clean_value(row.get("Department Name"))
        dept_code = clean_value(row.get("Department Code")) or rid
        site = clean_value(row.get("Site"))
        default_cost_code = clean_value(row.get("Default Cost Code"))

        resolved_site_name = None
        if site:
            res = await db.execute(text("SELECT site_name FROM site WHERE id = :id"), {"id": site})
            resolved_site_name = res.scalar_one_or_none()

        if await exists(db, "department", rid):
            await db.execute(
                text(
                    "UPDATE department SET department_name=:n, department_code=:code, site=:site, site_name=:site_name, default_cost_code=:dcc, updated_at=:u "
                    "WHERE id=:id"
                ),
                {
                    "id": rid,
                    "n": dept_name,
                    "code": dept_code,
                    "site": site,
                    "site_name": resolved_site_name,
                    "dcc": default_cost_code,
                    "u": datetime.now(),
                },
            )
        else:
            await db.execute(
                text(
                    "INSERT INTO department (id, department_name, department_code, site, site_name, default_cost_code, created_at, updated_at) "
                    "VALUES (:id, :n, :code, :site, :site_name, :dcc, :c, :u)"
                ),
                {
                    "id": rid,
                    "n": dept_name,
                    "code": dept_code,
                    "site": site,
                    "site_name": resolved_site_name,
                    "dcc": default_cost_code,
                    "c": datetime.now(),
                    "u": datetime.now(),
                },
            )
            inserted += 1
    return inserted


async def seed_vendors(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Vendor")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        if await exists(db, "vendor", rid):
            continue
        name = clean_value(row.get("Vendor Name"))
        site = clean_value(row.get("Site"))
        await db.execute(
            text("INSERT INTO vendor (id, vendor_name, site, created_at, updated_at) VALUES (:id, :n, :site, :c, :u)"),
            {"id": rid, "n": name, "site": site, "c": datetime.now(), "u": datetime.now()},
        )
        inserted += 1
    return inserted


async def seed_manufacturers(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Manufacturer")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        if await exists(db, "manufacturer", rid):
            continue
        company_name = clean_value(row.get("Company Name"))
        email = clean_value(row.get("Email"))
        await db.execute(
            text("INSERT INTO manufacturer (id, company_name, email, created_at, updated_at) VALUES (:id, :n, :e, :c, :u)"),
            {"id": rid, "n": company_name, "e": email, "c": datetime.now(), "u": datetime.now()},
        )
        inserted += 1
    return inserted


async def seed_models(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Model")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        if await exists(db, "model", rid):
            continue
        model_name = clean_value(row.get("Name"))
        manufacturer = clean_value(row.get("Manufacturer"))
        manufacturer_name = None
        if manufacturer:
            res = await db.execute(text("SELECT company_name FROM manufacturer WHERE id = :id"), {"id": manufacturer})
            manufacturer_name = res.scalar_one_or_none()
        await db.execute(
            text(
                "INSERT INTO model (id, name, manufacturer, manufacturer_name, created_at, updated_at) "
                "VALUES (:id, :n, :m, :mn, :c, :u)"
            ),
            {"id": rid, "n": model_name, "m": manufacturer, "mn": manufacturer_name, "c": datetime.now(), "u": datetime.now()},
        )
        inserted += 1
    return inserted


async def seed_asset_classes(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Asset Class")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        name = clean_value(row.get("Class Name"))
        desc = clean_value(row.get("Description"))
        parent_ref = clean_value(row.get("Parent Asset Class"))
        parent = await resolve_id(db, "asset_class", parent_ref, id_prefixes=("AC-",), name_columns=("name",))
        due = clean_value(row.get("Due Date Lead Time"))
        if await upsert_by_id(
            db,
            "asset_class",
            rid,
            {"name": name, "description": desc, "parent_asset_class": parent, "due_date_lead_time": due},
        ):
            inserted += 1
    return inserted


async def seed_asset_class_properties(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Asset Class Property")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        ac_ref = clean_value(row.get("Asset Class"))
        prop_ref = clean_value(row.get("Property"))
        uom_ref = clean_value(row.get("Unit of Measure"))

        ac_id = await resolve_id(db, "asset_class", ac_ref, id_prefixes=("AC-",), name_columns=("name",))
        prop_id = await resolve_id(db, "property", prop_ref, id_prefixes=("PRP-", "PROP-"), name_columns=("name",))
        uom_id = await resolve_id(db, "unit_of_measure", uom_ref, id_prefixes=("UOM-",), name_columns=("name", "short_name"))

        ac_name = None
        if ac_id:
            res = await db.execute(text("SELECT name FROM asset_class WHERE id=:id"), {"id": ac_id})
            ac_name = res.scalar_one_or_none()
        prop_name = None
        if prop_id:
            res = await db.execute(text("SELECT name FROM property WHERE id=:id"), {"id": prop_id})
            prop_name = res.scalar_one_or_none()
        uom_short = None
        if uom_id:
            res = await db.execute(text("SELECT short_name FROM unit_of_measure WHERE id=:id"), {"id": uom_id})
            uom_short = res.scalar_one_or_none()

        values = {
            "asset_class": ac_id,
            "asset_class_name": clean_value(row.get("Asset Class Name")) or ac_name,
            "property": prop_id,
            "property_name": clean_value(row.get("Property Name")) or prop_name,
            "unit_of_measure": uom_id,
            "uom_short_name": uom_short,
            "default_value": clean_value(row.get("Default Value")),
        }
        if await upsert_by_id(db, "asset_class_property", rid, values):
            inserted += 1
    return inserted


async def seed_items(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Item")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        item_name = clean_value(row.get("Item Name"))
        desc = clean_value(row.get("Description"))
        item_class = clean_value(row.get("Item Class"))
        primary_vendor_ref = clean_value(row.get("Primary Vendor"))
        asset_class_ref = clean_value(row.get("Asset Class"))
        uom_ref = clean_value(row.get("Unit of Measure"))

        item_class_id = await resolve_id(db, "item_class", item_class, id_prefixes=("IC-", "ITC-", "ITEMC-"), name_columns=("name",))
        vendor_id = await resolve_id(db, "vendor", primary_vendor_ref, id_prefixes=("VND-",), name_columns=("vendor_name",))
        asset_class_id = await resolve_id(db, "asset_class", asset_class_ref, id_prefixes=("AC-",), name_columns=("name",))
        uom_id = await resolve_id(db, "unit_of_measure", uom_ref, id_prefixes=("UOM-",), name_columns=("name", "short_name"))

        values = {
            "item_name": item_name,
            "name": item_name,
            "description": desc,
            "item_class": item_class_id,
            "item_type": clean_value(row.get("Item Type")),
            "abc_code": clean_value(row.get("ABC's Code")),
            "inventory_adjustment_account": clean_value(row.get("Inventory Adjustment Account")),
            "expense_account": clean_value(row.get("EPV Account")),
            "primary_vendor": vendor_id,
            "asset_class": asset_class_id,
            "uom": uom_id,
            "actual_qty_on_hand": clean_value(row.get("Actual Quantity on Hand")),
            "available_capacity": clean_value(row.get("Available Capacity")),
            "unit_cost": clean_value(row.get("Unit Cost")),
            "is_serialized": to_bool(row.get("Is Serialized")),
            "inspection_required": to_bool(row.get("Inspection Required")),
            "is_equipment": to_bool(row.get("Is Equipment/Tool")),
        }

        if await upsert_by_id(db, "item", rid, values):
            inserted += 1
    return inserted


async def seed_positions(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Position")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        tag = clean_value(row.get("Position Tag"))
        desc = clean_value(row.get("Description"))
        ac_ref = clean_value(row.get("Asset Class"))
        sys_ref = clean_value(row.get("System"))
        loc_ref = clean_value(row.get("Location"))
        site_ref = clean_value(row.get("Site"))

        ac_id = await resolve_id(db, "asset_class", ac_ref, id_prefixes=("AC-",), name_columns=("name",))
        sys_id = await resolve_id(db, "system", sys_ref, id_prefixes=("SYS-",), name_columns=("name", "system_name"))
        loc_id = await resolve_id(db, "location", loc_ref, id_prefixes=("LOC-",), name_columns=("name", "location_name"))
        site_id = await resolve_id(db, "site", site_ref, id_prefixes=("SITE-",), name_columns=("site_name", "site_code"))

        ac_name = None
        if ac_id:
            res = await db.execute(text("SELECT name FROM asset_class WHERE id=:id"), {"id": ac_id})
            ac_name = res.scalar_one_or_none()
        sys_name = None
        if sys_id:
            res = await db.execute(text("SELECT COALESCE(system_name, name) FROM system WHERE id=:id"), {"id": sys_id})
            sys_name = res.scalar_one_or_none()
        loc_name = None
        if loc_id:
            res = await db.execute(text("SELECT COALESCE(location_name, name) FROM location WHERE id=:id"), {"id": loc_id})
            loc_name = res.scalar_one_or_none()

        values = {
            "position_tag": tag,
            "description": desc,
            "asset_class": ac_id,
            "asset_class_name": ac_name,
            "system": sys_id,
            "system_name": sys_name,
            "location": loc_id,
            "location_name": loc_name,
            "site": site_id,
        }
        if await upsert_by_id(db, "position", rid, values):
            inserted += 1
    return inserted


async def seed_position_relations(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Position Relation")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        pos_a_ref = clean_value(row.get("Position A"))
        rel_type = clean_value(row.get("Position Relation Type"))
        pos_b_ref = clean_value(row.get("Position B"))

        pos_a = await resolve_id(db, "position", pos_a_ref, id_prefixes=("POS-",), name_columns=("position_tag",))
        pos_b = await resolve_id(db, "position", pos_b_ref, id_prefixes=("POS-",), name_columns=("position_tag",))

        pos_a_desc = None
        if pos_a:
            res = await db.execute(text("SELECT COALESCE(description, position_tag) FROM position WHERE id=:id"), {"id": pos_a})
            pos_a_desc = res.scalar_one_or_none()
        pos_b_desc = None
        if pos_b:
            res = await db.execute(text("SELECT COALESCE(description, position_tag) FROM position WHERE id=:id"), {"id": pos_b})
            pos_b_desc = res.scalar_one_or_none()

        values = {
            "position_a": pos_a,
            "position_relation_type": rel_type,
            "position_b": pos_b,
            "position_a_description": pos_a_desc,
            "position_b_description": pos_b_desc,
        }
        if await upsert_by_id(db, "position_relation", rid, values):
            inserted += 1
    return inserted


async def seed_assets(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Asset")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        asset_tag = clean_value(row.get("Asset Tag"))
        desc = clean_value(row.get("Description"))
        ac_ref = clean_value(row.get("Asset Class"))
        mfg_ref = clean_value(row.get("Manufacturer"))
        model_ref = clean_value(row.get("Model"))
        loc_ref = clean_value(row.get("Location"))
        site_ref = clean_value(row.get("Site"))
        dept_ref = clean_value(row.get("Department"))
        assigned_ref = clean_value(row.get("Assigned To"))
        sys_ref = clean_value(row.get("System"))

        ac_id = await resolve_id(db, "asset_class", ac_ref, id_prefixes=("AC-",), name_columns=("name",))
        ac_name = None
        if ac_id:
            res = await db.execute(text("SELECT name FROM asset_class WHERE id=:id"), {"id": ac_id})
            ac_name = res.scalar_one_or_none()

        mfg_id = await resolve_id(db, "manufacturer", mfg_ref, id_prefixes=("MFG-",), name_columns=("company_name",))
        mfg_name = None
        if mfg_id:
            res = await db.execute(text("SELECT company_name FROM manufacturer WHERE id=:id"), {"id": mfg_id})
            mfg_name = res.scalar_one_or_none()

        model_id = await resolve_id(db, "model", model_ref, id_prefixes=("MDL-",), name_columns=("name",))
        model_name = None
        if model_id:
            res = await db.execute(text("SELECT name FROM model WHERE id=:id"), {"id": model_id})
            model_name = res.scalar_one_or_none()

        loc_id = await resolve_id(db, "location", loc_ref, id_prefixes=("LOC-",), name_columns=("name", "location_name"))
        loc_name = None
        if loc_id:
            res = await db.execute(text("SELECT COALESCE(location_name, name) FROM location WHERE id=:id"), {"id": loc_id})
            loc_name = res.scalar_one_or_none()

        site_id = await resolve_id(db, "site", site_ref, id_prefixes=("SITE-",), name_columns=("site_name", "site_code"))
        site_name = None
        if site_id:
            res = await db.execute(text("SELECT site_name FROM site WHERE id=:id"), {"id": site_id})
            site_name = res.scalar_one_or_none()

        dept_id = await resolve_id(db, "department", dept_ref, id_prefixes=("DEPT-",), name_columns=("department_name",))
        dept_name = None
        if dept_id:
            res = await db.execute(text("SELECT department_name FROM department WHERE id=:id"), {"id": dept_id})
            dept_name = res.scalar_one_or_none()

        sys_id = await resolve_id(db, "system", sys_ref, id_prefixes=("SYS-",), name_columns=("name", "system_name"))
        sys_name = None
        if sys_id:
            res = await db.execute(text("SELECT COALESCE(system_name, name) FROM system WHERE id=:id"), {"id": sys_id})
            sys_name = res.scalar_one_or_none()

        values = {
            "asset_tag": asset_tag,
            "asset_class": ac_id,
            "description": desc,
            "series": clean_value(row.get("Series")),
            "manufacturer": mfg_id,
            "model": model_id,
            "serial_number": clean_value(row.get("Serial Number")),
            "date_purchased": clean_value(row.get("Date Purchased")),
            "cost": clean_value(row.get("Cost")),
            "block_number": clean_value(row.get("Block Number")),
            "number_of_repairs": clean_value(row.get("Number of Repairs")),
            "location": loc_id,
            "site": site_id,
            "department": dept_id,
            "assigned_to": assigned_ref,
            "system": sys_id,
            "asset_name": desc,
            "asset_class_name": ac_name,
            "location_name": loc_name,
            "site_name": site_name,
            "department_name": dept_name,
            "assigned_to_name": assigned_ref,
            "system_name": sys_name,
            "purchase_date": clean_value(row.get("Date Purchased")),
            "purchase_cost": clean_value(row.get("Cost")),
        }
        # If excel provides manufacturer/model as names, preserve them in the text fields too
        if mfg_name and not values.get("manufacturer"):
            values["manufacturer"] = mfg_id
        if model_name and not values.get("model"):
            values["model"] = model_id

        if await upsert_by_id(db, "asset", rid, values):
            inserted += 1
    return inserted


async def seed_asset_properties(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Asset Property")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        asset_ref = clean_value(row.get("Asset"))
        prop_ref = clean_value(row.get("Property"))
        uom_ref = clean_value(row.get("Unit of Measure"))

        asset_id = await resolve_id(db, "asset", asset_ref, id_prefixes=("AST-",), name_columns=("asset_tag", "description"))
        prop_id = await resolve_id(db, "property", prop_ref, id_prefixes=("PRP-", "PROP-"), name_columns=("name",))
        uom_id = await resolve_id(db, "unit_of_measure", uom_ref, id_prefixes=("UOM-",), name_columns=("name", "short_name"))

        asset_name = None
        if asset_id:
            res = await db.execute(text("SELECT COALESCE(asset_name, description) FROM asset WHERE id=:id"), {"id": asset_id})
            asset_name = res.scalar_one_or_none()
        prop_name = None
        if prop_id:
            res = await db.execute(text("SELECT name FROM property WHERE id=:id"), {"id": prop_id})
            prop_name = res.scalar_one_or_none()
        uom_short = None
        if uom_id:
            res = await db.execute(text("SELECT short_name FROM unit_of_measure WHERE id=:id"), {"id": uom_id})
            uom_short = res.scalar_one_or_none()

        values = {
            "asset": asset_id,
            "asset_name": clean_value(row.get("Asset Desc")) or asset_name,
            "property": prop_id,
            "property_name": clean_value(row.get("Property Name")) or prop_name,
            "property_value": clean_value(row.get("Property Value")),
            "unit_of_measure": uom_id,
            "uom_short_name": uom_short,
            "property_type": None,
        }
        if await upsert_by_id(db, "asset_property", rid, values):
            inserted += 1
    return inserted


async def seed_asset_positions(db):
    df = pd.read_excel(ASSET_MASTERFILES, sheet_name="Asset Position")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        pos_ref = clean_value(row.get("Position"))
        asset_ref = clean_value(row.get("Asset"))

        pos_id = await resolve_id(db, "position", pos_ref, id_prefixes=("POS-",), name_columns=("position_tag",))
        asset_id = await resolve_id(db, "asset", asset_ref, id_prefixes=("AST-",), name_columns=("asset_tag", "description"))

        pos_name = None
        if pos_id:
            res = await db.execute(text("SELECT position_tag FROM position WHERE id=:id"), {"id": pos_id})
            pos_name = res.scalar_one_or_none()
        asset_name = None
        if asset_id:
            res = await db.execute(text("SELECT COALESCE(asset_name, description) FROM asset WHERE id=:id"), {"id": asset_id})
            asset_name = res.scalar_one_or_none()

        values = {
            "position": pos_id,
            "position_name": pos_name,
            "asset": asset_id,
            "asset_name": asset_name,
            "date_installed": clean_value(row.get("Date Installed")),
            "date_removed": clean_value(row.get("Date Removed")),
        }
        if await upsert_by_id(db, "asset_position", rid, values):
            inserted += 1
    return inserted


async def seed_item_classes(db):
    # Item Class lives in the main excel folder; not present in these masterfiles workbooks.
    # Keep this a no-op here to avoid failing. It should be seeded from the main Excel directory.
    return 0


async def seed_labor_groups(db):
    # Labor Group not present in these masterfiles workbooks (labor is in Core Masterfiles.xlsx)
    return 0


async def seed_trades(db):
    # Trade not present in these masterfiles workbooks; seed from main Excel directory.
    return 0


async def seed_category_of_failure(db):
    df = pd.read_excel(MAINTENANCE_MASTERFILES, sheet_name="Category Of Failure")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        values = {
            "failure_name": clean_value(row.get("Name")),
            "description": clean_value(row.get("Description")),
            "site": await resolve_id(db, "site", clean_value(row.get("Site")), id_prefixes=("SITE-",), name_columns=("site_name",)),
            "active": to_bool(row.get("Active")),
        }
        if await upsert_by_id(db, "category_of_failure", rid, values):
            inserted += 1
    return inserted


async def seed_checklists(db):
    df = pd.read_excel(MAINTENANCE_MASTERFILES, sheet_name="Checklist")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        values = {
            "checklist_name": clean_value(row.get("Checklist Name")),
            "checklist_type": clean_value(row.get("Checklist Type")),
        }
        if await upsert_by_id(db, "checklist", rid, values):
            inserted += 1
    return inserted


async def seed_checklist_details(db):
    df = pd.read_excel(MAINTENANCE_MASTERFILES, sheet_name="Checklist Detail")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        checklist_ref = clean_value(row.get("Checklist"))
        checklist_id = await resolve_id(db, "checklist", checklist_ref, id_prefixes=("CL-",), name_columns=("checklist_name",))
        values = {
            "checklist": checklist_id,
            "item_name": clean_value(row.get("Item Name")),
            "is_mandatory": to_bool(row.get("Is Mandatory")),
        }
        if await upsert_by_id(db, "checklist_details", rid, values):
            inserted += 1
    return inserted


async def seed_maintenance_activities(db):
    df = pd.read_excel(MAINTENANCE_MASTERFILES, sheet_name="Maintenance Activity")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        values = {
            "activity_name": clean_value(row.get("Activity Name")),
            "description": clean_value(row.get("Description")),
        }
        if await upsert_by_id(db, "maintenance_activity", rid, values):
            inserted += 1
    return inserted


async def seed_maintenance_parts(db):
    df = pd.read_excel(MAINTENANCE_MASTERFILES, sheet_name="Maintenance Part")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        ma_ref = clean_value(row.get("Maintenance Activity"))
        item_ref = clean_value(row.get("Part"))
        ma_id = await resolve_id(db, "maintenance_activity", ma_ref, id_prefixes=("MA-",), name_columns=("activity_name",))
        item_id = await resolve_id(db, "item", item_ref, id_prefixes=("ITEM-", "ITM-"), name_columns=("item_name", "name"))
        values = {
            "maintenance_activity": ma_id,
            "item": item_id,
            "quantity": clean_value(row.get("Required Quantity")),
        }
        if await upsert_by_id(db, "maintenance_parts", rid, values):
            inserted += 1
    return inserted


async def seed_maintenance_equipment(db):
    df = pd.read_excel(MAINTENANCE_MASTERFILES, sheet_name="Maintenance Equipment")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        ma_ref = clean_value(row.get("Maintenance Activity"))
        equipment_ref = clean_value(row.get("Equipment"))
        ma_id = await resolve_id(db, "maintenance_activity", ma_ref, id_prefixes=("MA-",), name_columns=("activity_name",))
        equipment_id = await resolve_id(db, "equipment", equipment_ref, id_prefixes=("EQ-", "EQUIP-"), name_columns=("description",))
        values = {
            "maintenance_activity": ma_id,
            "equipment": equipment_id,
            "required_qty": clean_value(row.get("Required Quantity")),
            "required_hours": clean_value(row.get("Required Hours")),
        }
        if await upsert_by_id(db, "maintenance_equipment", rid, values):
            inserted += 1
    return inserted


async def seed_maintenance_trades(db):
    df = pd.read_excel(MAINTENANCE_MASTERFILES, sheet_name="Maintenance Trade")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        ma_ref = clean_value(row.get("Maintenance Activity"))
        trade_ref = clean_value(row.get("Trade"))
        ma_id = await resolve_id(db, "maintenance_activity", ma_ref, id_prefixes=("MA-",), name_columns=("activity_name",))
        trade_id = await resolve_id(db, "trade", trade_ref, id_prefixes=("TRD-", "TRADE-"), name_columns=("trade_name",))
        values = {
            "maintenance_activity": ma_id,
            "trade": trade_id,
            "required_qty": clean_value(row.get("Required Quantity")),
            "required_hours": clean_value(row.get("Required Hours")),
        }
        if await upsert_by_id(db, "maintenance_trade", rid, values):
            inserted += 1
    return inserted


async def seed_maintenance_plans(db):
    df = pd.read_excel(MAINTENANCE_MASTERFILES, sheet_name="Planned Maintenance Activity")
    inserted = 0
    for row in iter_rows(df):
        desc = clean_value(row.get("Maintenance Plan"))
        if not desc:
            continue
        # De-duplicate by description + asset/manufacturer/model
        asset_class_ref = clean_value(row.get("Asset Class"))
        manufacturer_ref = clean_value(row.get("Manufacturer"))
        model_ref = clean_value(row.get("Model"))

        asset_class_id = await resolve_id(db, "asset_class", asset_class_ref, id_prefixes=("AC-", "ACLASS-", "ASCLS-"), name_columns=("name",))
        manufacturer_id = await resolve_id(db, "manufacturer", manufacturer_ref, id_prefixes=("MFR-", "MAN-"), name_columns=("company_name",))
        model_id = await resolve_id(db, "model", model_ref, id_prefixes=("MDL-", "MODEL-"), name_columns=("name",))

        res = await db.execute(
            text(
                "SELECT id FROM maintenance_plan WHERE description=:d "
                "AND COALESCE(asset_class,'')=COALESCE(:ac,'') "
                "AND COALESCE(manufacturer,'')=COALESCE(:mfr,'') "
                "AND COALESCE(model,'')=COALESCE(:mdl,'') LIMIT 1"
            ),
            {"d": desc, "ac": asset_class_id, "mfr": manufacturer_id, "mdl": model_id},
        )
        rid = res.scalar_one_or_none()
        if not rid:
            rid = await next_series_id(db, "maintenance_plan", "MP-", width=5)

        values = {
            "description": desc,
            "asset_class": asset_class_id,
            "asset_class_name": asset_class_ref,
            "manufacturer": manufacturer_id,
            "manufacturer_name": manufacturer_ref,
            "model": model_id,
        }
        if await upsert_by_id(db, "maintenance_plan", rid, values):
            inserted += 1
    return inserted


async def seed_planned_maintenance_activities(db):
    df = pd.read_excel(MAINTENANCE_MASTERFILES, sheet_name="Planned Maintenance Activity")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))

        desc = clean_value(row.get("Maintenance Plan"))
        asset_class_ref = clean_value(row.get("Asset Class"))
        manufacturer_ref = clean_value(row.get("Manufacturer"))
        model_ref = clean_value(row.get("Model"))

        asset_class_id = await resolve_id(db, "asset_class", asset_class_ref, id_prefixes=("AC-", "ACLASS-", "ASCLS-"), name_columns=("name",))
        manufacturer_id = await resolve_id(db, "manufacturer", manufacturer_ref, id_prefixes=("MFR-", "MAN-"), name_columns=("company_name",))
        model_id = await resolve_id(db, "model", model_ref, id_prefixes=("MDL-", "MODEL-"), name_columns=("name",))

        res = await db.execute(
            text(
                "SELECT id FROM maintenance_plan WHERE description=:d "
                "AND COALESCE(asset_class,'')=COALESCE(:ac,'') "
                "AND COALESCE(manufacturer,'')=COALESCE(:mfr,'') "
                "AND COALESCE(model,'')=COALESCE(:mdl,'') LIMIT 1"
            ),
            {"d": desc, "ac": asset_class_id, "mfr": manufacturer_id, "mdl": model_id},
        )
        plan_id = res.scalar_one_or_none()
        if not plan_id and desc:
            # Ensure plan exists
            plan_id = await next_series_id(db, "maintenance_plan", "MP-", width=5)
            await upsert_by_id(
                db,
                "maintenance_plan",
                plan_id,
                {
                    "description": desc,
                    "asset_class": asset_class_id,
                    "asset_class_name": asset_class_ref,
                    "manufacturer": manufacturer_id,
                    "manufacturer_name": manufacturer_ref,
                    "model": model_id,
                },
            )

        ma_ref = clean_value(row.get("Maintenance Activity"))
        ma_id = await resolve_id(db, "maintenance_activity", ma_ref, id_prefixes=("MA-",), name_columns=("activity_name",))

        checklist_ref = clean_value(row.get("Checklist"))
        checklist_id = await resolve_id(db, "checklist", checklist_ref, id_prefixes=("CL-",), name_columns=("checklist_name",))

        schedule = clean_value(row.get("Maintenance Schedule"))
        maintenance_type_id = await resolve_id(
            db,
            "request_activity_type",
            schedule,
            id_prefixes=("RAT-",),
            name_columns=("type", "menu"),
        )
        values = {
            "maintenance_plan": plan_id,
            "maintenance_plan_name": desc,
            "maintenance_activity": ma_id,
            "maintenance_activity_name": ma_ref,
            "checklist": checklist_id,
            "checklist_name": checklist_ref,
            "maintenance_schedule": schedule,
            # maintenance_type is an FK to request_activity_type.id; only set if resolvable.
            "maintenance_type": maintenance_type_id,
        }
        if await upsert_by_id(db, "planned_maintenance_activity", rid, values):
            inserted += 1
    return inserted


async def seed_maintenance_calendars(db):
    df = pd.read_excel(MAINTENANCE_MASTERFILES, sheet_name="Maintenance Calendar")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        pma_ref = clean_value(row.get("Planned Maintenance Activity"))
        pma_id = await resolve_id(db, "planned_maintenance_activity", pma_ref, id_prefixes=("PMA-",), name_columns=())

        plan_id = None
        ma_id = None
        if pma_id:
            res = await db.execute(
                text(
                    "SELECT maintenance_plan, maintenance_activity FROM planned_maintenance_activity WHERE id=:id"
                ),
                {"id": pma_id},
            )
            row2 = res.first()
            if row2:
                plan_id, ma_id = row2

        last_prop_ref = clean_value(row.get("Last Maintenance Date Property"))
        last_prop_id = await resolve_id(db, "property", last_prop_ref, id_prefixes=("PROP-",), name_columns=("name",))

        values = {
            "planned_maintenance_activity": pma_id,
            "maintenance_plan": plan_id,
            "maintenance_activity": ma_id,
            "frequency": clean_value(row.get("Frequency")),
            "lead_calendar_days": clean_value(row.get("Lead Calendar Days")),
            "last_maintenance_date_property": last_prop_id,
        }
        if await upsert_by_id(db, "maintenance_calendar", rid, values):
            inserted += 1
    return inserted


async def seed_maintenance_intervals(db):
    df = pd.read_excel(MAINTENANCE_MASTERFILES, sheet_name="Maintenance Interval")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        pma_ref = clean_value(row.get("Planned Maintenance Activity"))
        pma_id = await resolve_id(db, "planned_maintenance_activity", pma_ref, id_prefixes=("PMA-",), name_columns=())

        plan_id = None
        ma_id = None
        if pma_id:
            res = await db.execute(
                text(
                    "SELECT maintenance_plan, maintenance_activity FROM planned_maintenance_activity WHERE id=:id"
                ),
                {"id": pma_id},
            )
            row2 = res.first()
            if row2:
                plan_id, ma_id = row2

        uom_ref = clean_value(row.get("Interval Unit of Measure"))
        uom_id = await resolve_id(db, "unit_of_measure", uom_ref, id_prefixes=("UOM-",), name_columns=("name", "short_name"))

        running_ref = clean_value(row.get("Running Interval Property"))
        last_ref = clean_value(row.get("Last Interval Property"))
        running_id = await resolve_id(db, "property", running_ref, id_prefixes=("PROP-",), name_columns=("name",))
        last_id = await resolve_id(db, "property", last_ref, id_prefixes=("PROP-",), name_columns=("name",))

        values = {
            "planned_maintenance_activity": pma_id,
            "maintenance_plan": plan_id,
            "maintenance_activity": ma_id,
            "lead_interval": clean_value(row.get("Lead Interval")),
            "interval": clean_value(row.get("Interval")),
            "interval_unit_of_measure": uom_id,
            "running_interval_property": running_id,
            "last_interval_property": last_id,
        }
        if await upsert_by_id(db, "maintenance_interval", rid, values):
            inserted += 1
    return inserted


async def seed_cost_codes(db):
    df = pd.read_excel(CORE_MASTERFILES, sheet_name="Cost Code")
    inserted = 0
    for row in iter_rows(df):
        rid = clean_value(row.get("ID"))
        if await exists(db, "cost_code", rid):
            continue
        code = clean_value(row.get("Code")) or clean_value(row.get("Name"))
        desc = clean_value(row.get("Description"))
        scope = clean_value(row.get("Scope"))
        site = clean_value(row.get("Site"))
        site_name = clean_value(row.get("Site Name"))

        # Some masterfiles use site NAME instead of site ID.
        # cost_code.site is an FK to site.id, so resolve names to IDs.
        if site and not site.startswith("SITE-"):
            res = await db.execute(
                text(
                    "SELECT id, site_name FROM site WHERE site_name = :v OR site_code = :v LIMIT 1"
                ),
                {"v": site},
            )
            row_site = res.first()
            if row_site:
                site = row_site[0]
                site_name = site_name or row_site[1]
            else:
                # If we cannot resolve, avoid FK violation by leaving NULL.
                site = None
                site_name = None

        # Drop obvious note/sample rows
        if not code and not desc:
            continue
        await db.execute(
            text(
                "INSERT INTO cost_code (id, code, description, scope, site, site_name, created_at, updated_at) "
                "VALUES (:id, :code, :d, :scope, :site, :site_name, :c, :u)"
            ),
            {"id": rid, "code": code, "d": desc, "scope": scope, "site": site, "site_name": site_name, "c": datetime.now(), "u": datetime.now()},
        )
        inserted += 1
    return inserted


async def main():
    print("=" * 60)
    print("SEED MASTERFILES WORKBOOKS")
    print("=" * 60)

    _assert_workbook_exists(ASSET_MASTERFILES)
    _assert_workbook_exists(CORE_MASTERFILES)
    _assert_workbook_exists(MAINTENANCE_MASTERFILES)

    async with async_session_maker() as db:
        # Order: core foundations first
        counts = {}
        # Asset Masterfiles.xlsx (requested order)
        counts["organization"] = await seed_organizations(db)
        counts["site"] = await seed_sites(db)
        counts["department"] = await seed_departments(db)
        counts["location_type"] = await seed_location_types(db)
        counts["location"] = await seed_locations(db)
        counts["system_type"] = await seed_system_types(db)
        counts["system"] = await seed_systems(db)
        counts["unit_of_measure"] = await seed_units_of_measure(db)
        counts["property_type"] = await seed_property_types(db)
        counts["property"] = await seed_properties(db)
        counts["manufacturer"] = await seed_manufacturers(db)
        counts["model"] = await seed_models(db)
        counts["vendor"] = await seed_vendors(db)
        counts["asset_class"] = await seed_asset_classes(db)
        counts["asset_class_property"] = await seed_asset_class_properties(db)
        counts["item"] = await seed_items(db)
        counts["position"] = await seed_positions(db)
        counts["position_relation"] = await seed_position_relations(db)
        counts["asset"] = await seed_assets(db)
        counts["asset_property"] = await seed_asset_properties(db)
        counts["asset_position"] = await seed_asset_positions(db)

        # Core Masterfiles.xlsx
        counts["cost_code"] = await seed_cost_codes(db)

        # Maintenance Masterfiles.xlsx (workbook order)
        counts["category_of_failure"] = await seed_category_of_failure(db)
        counts["checklist"] = await seed_checklists(db)
        counts["checklist_details"] = await seed_checklist_details(db)
        counts["maintenance_activity"] = await seed_maintenance_activities(db)
        counts["maintenance_parts"] = await seed_maintenance_parts(db)
        counts["maintenance_equipment"] = await seed_maintenance_equipment(db)
        counts["maintenance_trade"] = await seed_maintenance_trades(db)
        counts["maintenance_plan"] = await seed_maintenance_plans(db)
        counts["planned_maintenance_activity"] = await seed_planned_maintenance_activities(db)
        counts["maintenance_calendar"] = await seed_maintenance_calendars(db)
        counts["maintenance_interval"] = await seed_maintenance_intervals(db)

        await db.commit()

    print("\nInserted rows:")
    for k, v in counts.items():
        print(f"  - {k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
