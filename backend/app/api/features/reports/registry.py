"""Reports Registry
================
Minimal legacy report stub for the core framework.
"""
from typing import Any

REPORTS: dict[str, dict[str, Any]] = {}


def get_report_data(report_key: str, params: dict[str, Any]) -> dict[str, Any]:
    return {"error": "Legacy reporting is disabled"}


def render_report_html(report_key: str, params: dict[str, Any]) -> str:
    return "<p>Legacy reporting is disabled.</p>"
