from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


DASHBOARD_ENDPOINT = "/api/operations/dashboard/widgets/{dashboard_key}"
START_DATE = date(2026, 3, 23)
END_DATE = date(2026, 4, 22)
END_DATE_EXCLUSIVE = END_DATE + timedelta(days=1)
LIST_PREVIEW_LIMIT = 10


async def _fetch_dashboard(client, dashboard_key: str) -> dict[str, Any]:
    response = await client.get(
        DASHBOARD_ENDPOINT.format(dashboard_key=dashboard_key),
        params={
            "start_date": START_DATE.isoformat(),
            "end_date": END_DATE.isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _widget_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {widget["type"]: widget["data"] for widget in payload["widgets"]}


def _resolve_field(source_data: dict[str, Any], field_path: str) -> Any:
    value: Any = source_data
    for part in field_path.split("."):
        if part == "length":
            value = len(value) if value is not None else 0
        elif isinstance(value, dict):
            value = value.get(part)
        else:
            value = None
    return 0 if value is None else value


def _assert_widget_payloads_have_no_errors(payload: dict[str, Any]) -> None:
    for widget in payload["widgets"]:
        assert "error" not in widget["data"], (
            f"Widget {widget['type']} returned an error payload: {widget['data']}"
        )


def _assert_stats_are_resolvable(payload: dict[str, Any]) -> None:
    widgets = _widget_map(payload)
    for stat in payload["stats"]:
        assert stat["source"] in widgets, f"Missing stat source widget {stat['source']}"
        value = _resolve_field(widgets[stat["source"]], stat["field"])
        assert isinstance(value, int | float), (
            f"Stat field {stat['field']} did not resolve to a number: {value!r}"
        )


def _assert_charts_are_consistent(payload: dict[str, Any]) -> None:
    widgets = _widget_map(payload)
    for chart in payload["charts"]:
        assert chart["source"] in widgets, f"Missing chart source widget {chart['source']}"
        source = widgets[chart["source"]]
        total_value = int(source.get(chart["total_field"], 0) or 0)

        if chart.get("custom_data"):
            if chart["source"] == "inventory_summary":
                assert 0 <= int(source.get("low_stock_count", 0) or 0) <= total_value
            else:
                series = source.get(chart["data_field"], {}) or {}
                assert sum(int(value) for value in series.values()) == total_value
            continue

        series = source.get(chart["data_field"], {}) or {}
        assert sum(int(value) for value in series.values()) == total_value
        preferred_order = set(chart.get("preferred_order") or [])
        assert set(series).issubset(preferred_order), (
            f"Chart {chart['title']} is missing categories from preferred_order: "
            f"{sorted(set(series) - preferred_order)}"
        )


async def _workflow_state_labels(db_session: AsyncSession) -> dict[str, str]:
    result = await db_session.execute(text("SELECT slug, label FROM core_workflow_states"))
    return {row.slug: row.label for row in result.fetchall()}


def _merge_state_counts(rows: list[Any], state_labels: dict[str, str]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for row in rows:
        raw_state = row.workflow_state or "Unassigned"
        label = state_labels.get(raw_state, raw_state)
        merged[label] = merged.get(label, 0) + int(row.count)
    return merged


@pytest.mark.asyncio
async def test_work_management_dashboard_counts_are_consistent(
    superuser_client,
    db_session: AsyncSession,
):
    payload = await _fetch_dashboard(superuser_client, "work-management")
    widgets = _widget_map(payload)
    state_labels = await _workflow_state_labels(db_session)

    total_result = await db_session.execute(
        text(
            """
            SELECT COUNT(*) AS count
            FROM work_order
            WHERE created_at >= :start_date
              AND created_at < :end_date_exclusive
            """
        ),
        {"start_date": START_DATE, "end_date_exclusive": END_DATE_EXCLUSIVE},
    )
    expected_total = int(total_result.scalar_one() or 0)

    status_result = await db_session.execute(
        text(
            """
            SELECT COALESCE(workflow_state, 'Unassigned') AS workflow_state, COUNT(*) AS count
            FROM work_order
            WHERE created_at >= :start_date
              AND created_at < :end_date_exclusive
            GROUP BY COALESCE(workflow_state, 'Unassigned')
            """
        ),
        {"start_date": START_DATE, "end_date_exclusive": END_DATE_EXCLUSIVE},
    )
    expected_by_status = _merge_state_counts(status_result.fetchall(), state_labels)

    overdue_result = await db_session.execute(
        text(
            """
            SELECT COUNT(*) AS count
            FROM work_order
            WHERE due_date < CURRENT_DATE
              AND LOWER(COALESCE(workflow_state, '')) != 'closed'
              AND created_at >= :start_date
              AND created_at < :end_date_exclusive
            """
        ),
        {"start_date": START_DATE, "end_date_exclusive": END_DATE_EXCLUSIVE},
    )
    expected_overdue = int(overdue_result.scalar_one() or 0)

    type_result = await db_session.execute(
        text(
            """
            SELECT COALESCE(work_order_type, 'Unassigned') AS work_order_type, COUNT(*) AS count
            FROM work_order
            WHERE created_at >= :start_date
              AND created_at < :end_date_exclusive
            GROUP BY COALESCE(work_order_type, 'Unassigned')
            """
        ),
        {"start_date": START_DATE, "end_date_exclusive": END_DATE_EXCLUSIVE},
    )
    expected_by_type = {
        row.work_order_type: int(row.count)
        for row in type_result.fetchall()
    }

    attention_total_result = await db_session.execute(
        text(
            """
            SELECT COUNT(*) AS count
            FROM work_order
            WHERE LOWER(COALESCE(workflow_state, '')) != 'closed'
            """
        )
    )
    expected_attention_total = int(attention_total_result.scalar_one() or 0)

    assert payload["date_filter"] == {
        "start_date": START_DATE.isoformat(),
        "end_date": END_DATE.isoformat(),
    }
    assert widgets["work_order_summary"] == {
        "total": expected_total,
        "by_status": expected_by_status,
        "overdue_count": expected_overdue,
    }
    assert widgets["work_order_type_distribution"] == {
        "total": expected_total,
        "by_type": expected_by_type,
    }
    assert widgets["work_order_attention_list"]["total"] == expected_attention_total
    assert len(widgets["work_order_attention_list"]["items"]) == min(
        LIST_PREVIEW_LIMIT, expected_attention_total
    )
    assert widgets["my_work_order_list"] == {"total": 0, "items": []}

    _assert_widget_payloads_have_no_errors(payload)
    _assert_stats_are_resolvable(payload)
    _assert_charts_are_consistent(payload)


@pytest.mark.asyncio
async def test_procurement_dashboard_counts_are_consistent(
    superuser_client,
    db_session: AsyncSession,
):
    payload = await _fetch_dashboard(superuser_client, "procurement")
    widgets = _widget_map(payload)
    state_labels = await _workflow_state_labels(db_session)

    status_result = await db_session.execute(
        text(
            """
            SELECT workflow_state, COUNT(*) AS count
            FROM purchase_request
            WHERE date_requested >= :start_date
              AND date_requested <= :end_date
            GROUP BY workflow_state
            """
        ),
        {"start_date": START_DATE, "end_date": END_DATE},
    )
    expected_by_status = _merge_state_counts(status_result.fetchall(), state_labels)

    pending_result = await db_session.execute(
        text(
            """
            SELECT COUNT(*) AS count
            FROM purchase_request
            WHERE workflow_state = 'Pending Approval'
            """
        )
    )
    expected_pending_total = int(pending_result.scalar_one() or 0)

    assert widgets["pr_status_summary"] == {
        "total": sum(expected_by_status.values()),
        "by_status": expected_by_status,
        "period": "filtered",
    }
    assert widgets["pr_attention_list"]["total"] == expected_pending_total
    assert len(widgets["pr_attention_list"]["items"]) == min(
        LIST_PREVIEW_LIMIT, expected_pending_total
    )

    _assert_widget_payloads_have_no_errors(payload)
    _assert_stats_are_resolvable(payload)
    _assert_charts_are_consistent(payload)


@pytest.mark.asyncio
async def test_inventory_dashboard_counts_are_consistent(
    superuser_client,
    db_session: AsyncSession,
):
    payload = await _fetch_dashboard(superuser_client, "inventory")
    widgets = _widget_map(payload)

    inventory_result = await db_session.execute(
        text(
            """
            SELECT
                COUNT(DISTINCT item) AS total_items,
                COUNT(DISTINCT location) AS location_count,
                SUM(CASE WHEN actual_inv < 10 THEN 1 ELSE 0 END) AS low_stock_count
            FROM inventory
            WHERE actual_inv IS NOT NULL
            """
        )
    )
    inventory_row = inventory_result.fetchone()
    expected_inventory_summary = {
        "total_items": int(inventory_row.total_items or 0),
        "location_count": int(inventory_row.location_count or 0),
        "low_stock_count": int(inventory_row.low_stock_count or 0),
    }

    low_stock_total_result = await db_session.execute(
        text(
            """
            SELECT COUNT(*) AS count
            FROM inventory
            WHERE actual_inv IS NOT NULL AND actual_inv < 10
            """
        )
    )
    expected_low_stock_total = int(low_stock_total_result.scalar_one() or 0)

    stock_count_result = await db_session.execute(
        text(
            """
            SELECT sc.workflow_state, COUNT(*) AS count
            FROM stock_count_task sct
            JOIN stock_count sc ON sc.id = sct.stock_count
            WHERE sc.workflow_state IN ('Planned', 'In Progress')
            GROUP BY sc.workflow_state
            """
        )
    )
    stock_count_rows = {row.workflow_state: int(row.count) for row in stock_count_result.fetchall()}
    expected_stock_count_summary = {
        "pending_count": stock_count_rows.get("Planned", 0),
        "in_progress_count": stock_count_rows.get("In Progress", 0),
        "total_active": stock_count_rows.get("Planned", 0) + stock_count_rows.get("In Progress", 0),
        "by_status": {
            "Pending": stock_count_rows.get("Planned", 0),
            "In Progress": stock_count_rows.get("In Progress", 0),
        },
    }

    assert widgets["inventory_summary"] == expected_inventory_summary
    assert widgets["inventory_low_stock"]["total"] == expected_low_stock_total
    assert len(widgets["inventory_low_stock"]["items"]) == min(
        LIST_PREVIEW_LIMIT, expected_low_stock_total
    )
    assert widgets["inventory_low_stock"]["threshold"] == 10
    assert widgets["stock_count_summary"] == expected_stock_count_summary

    _assert_widget_payloads_have_no_errors(payload)
    _assert_stats_are_resolvable(payload)
    _assert_charts_are_consistent(payload)