#!/usr/bin/env python3

import asyncio
import os
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.framework.models.workflow import (
    Workflow,
    WorkflowAction,
    WorkflowState,
    WorkflowStateLink,
    WorkflowTransition,
    generate_slug,
)


def normalize_entity_name(label: str) -> str:
    s = (label or "").strip().lower()
    s = re.sub(r"[^a-z0-9\s_]", "", s)
    s = re.sub(r"\s+", "_", s)
    return s


REPO_MASTERFILES_DIR = Path(__file__).resolve().parent.parent / "masterfiles"
DOWNLOADS_MASTERFILES_DIR = Path.home() / "Downloads" / "eam2.1" / "masterfiles"


def first_existing_dir(*candidates: Path) -> Path:
    for c in candidates:
        if c and c.exists() and c.is_dir():
            return c
    return candidates[0]


MASTERFILES_DIR = first_existing_dir(
    Path(os.getenv("EAM_MASTERFILES_DIR")) if os.getenv("EAM_MASTERFILES_DIR") else None,
    DOWNLOADS_MASTERFILES_DIR,
    REPO_MASTERFILES_DIR,
)

WORKFLOW_XLSX = Path(os.getenv("EAM_WORKFLOW_XLSX", str(MASTERFILES_DIR / "Workflow.xlsx")))


TARGET_DOCUMENT_TYPES = {
    # HIGH PRIO
    "Asset",
    "Purchase Request",
    "Purchase Request Line",
    "Purchase Order",
    "Purchase Order Line",
    "Maintenance Request",
    "Work Order",
    "Work Order Activity",
    # LESS PRIO
    "Stock Count",
    "Inventory Adjustment",
    "Item Issue",
    "Item Return",
}


async def get_state_by_label(db, label: str) -> WorkflowState | None:
    slug = generate_slug(label)
    res = await db.execute(select(WorkflowState).where(WorkflowState.slug == slug))
    return res.scalar_one_or_none()


async def get_action_by_label(db, label: str) -> WorkflowAction | None:
    slug = generate_slug(label)
    res = await db.execute(select(WorkflowAction).where(WorkflowAction.slug == slug))
    return res.scalar_one_or_none()


async def upsert_workflow(db, *, name: str, target_entity: str, is_active: bool) -> Workflow:
    res = await db.execute(select(Workflow).where(Workflow.target_entity == target_entity))
    wf = res.scalar_one_or_none()
    if wf:
        wf.name = name
        wf.is_active = is_active
        await db.flush()
        return wf

    wf = Workflow(name=name, target_entity=target_entity, is_active=is_active)
    db.add(wf)
    await db.flush()
    return wf


async def clear_workflow_config(db, workflow_id: str) -> None:
    res = await db.execute(select(WorkflowTransition).where(WorkflowTransition.workflow_id == workflow_id))
    for t in res.scalars().all():
        await db.delete(t)

    res = await db.execute(select(WorkflowStateLink).where(WorkflowStateLink.workflow_id == workflow_id))
    for sl in res.scalars().all():
        await db.delete(sl)

    await db.flush()


async def seed_workflows() -> None:
    if not WORKFLOW_XLSX.exists():
        raise FileNotFoundError(f"Missing workflow workbook: {WORKFLOW_XLSX}. Set EAM_WORKFLOW_XLSX or EAM_MASTERFILES_DIR.")

    df = pd.read_excel(WORKFLOW_XLSX, sheet_name="Workflow")

    # Workflow.xlsx is typically exported with merged cells; pandas will read subsequent
    # rows as NaN. Forward-fill the workflow header columns so every row is attributable.
    for col in ["Workflow Name", "Document Type", "Workflow State Field", "Is Active"]:
        if col in df.columns:
            df[col] = df[col].ffill()

    df["Workflow Name"] = df["Workflow Name"].astype(str).str.strip()
    df["Document Type"] = df["Document Type"].astype(str).str.strip()

    # Filter down to the doctypes we care about
    df = df[df["Document Type"].isin(TARGET_DOCUMENT_TYPES)].copy()

    async with async_session_maker() as db:
        created = 0
        updated = 0
        state_links = 0
        transitions = 0

        for (wf_name, doc_type), g in df.groupby(["Workflow Name", "Document Type"], dropna=False):
            wf_name = str(wf_name).strip()
            doc_type = str(doc_type).strip()
            if not wf_name or not doc_type:
                continue

            target_entity = normalize_entity_name(doc_type)
            wf = await upsert_workflow(db, name=wf_name, target_entity=target_entity, is_active=bool(g["Is Active"].fillna(0).iloc[0]))

            # Re-seed links/transitions deterministically
            await clear_workflow_config(db, wf.id)

            # State links (from Document States)
            doc_states = (
                g[["State (Document States)", "Doc Status (Document States)"]]
                .dropna(subset=["State (Document States)"])
                .drop_duplicates()
            )

            states_in_order: list[str] = [str(s).strip() for s in doc_states["State (Document States)"].tolist() if str(s).strip()]
            initial_slug = None
            if any(generate_slug(s) == "draft" for s in states_in_order):
                initial_slug = "draft"
            elif states_in_order:
                initial_slug = generate_slug(states_in_order[0])

            for i, state_label in enumerate(states_in_order):
                st = await get_state_by_label(db, state_label)
                if not st:
                    # States are expected to already exist (seeded separately)
                    continue
                sl = WorkflowStateLink(
                    workflow_id=wf.id,
                    state_id=st.id,
                    is_initial=(st.slug == initial_slug),
                    sort_order=i,
                )
                db.add(sl)
                state_links += 1

            await db.flush()

            # Transitions
            trans = g[["State (Transitions)", "Action (Transitions)", "Next State (Transitions)"]].dropna(how="all")
            trans_rows = []
            for _, r in trans.iterrows():
                from_state = str(r.get("State (Transitions)") or "").strip()
                action = str(r.get("Action (Transitions)") or "").strip()
                to_state = str(r.get("Next State (Transitions)") or "").strip()
                if not from_state or not action or not to_state:
                    continue
                trans_rows.append((from_state, action, to_state))

            seen = set()
            sort = 0
            for from_label, action_label, to_label in trans_rows:
                key = (from_label, action_label, to_label)
                if key in seen:
                    continue
                seen.add(key)

                from_st = await get_state_by_label(db, from_label)
                to_st = await get_state_by_label(db, to_label)
                act = await get_action_by_label(db, action_label)
                if not from_st or not to_st or not act:
                    continue

                db.add(
                    WorkflowTransition(
                        workflow_id=wf.id,
                        from_state_id=from_st.id,
                        action_id=act.id,
                        to_state_id=to_st.id,
                        sort_order=sort,
                    )
                )
                sort += 1
                transitions += 1

            if wf.id:
                # treat as updated if existed before
                res = await db.execute(select(Workflow).where(Workflow.id == wf.id))
                if res.scalar_one_or_none():
                    updated += 1
                else:
                    created += 1

        await db.commit()

    print("✅ Workflow seeding complete")


async def main() -> None:
    await seed_workflows()


if __name__ == "__main__":
    asyncio.run(main())
