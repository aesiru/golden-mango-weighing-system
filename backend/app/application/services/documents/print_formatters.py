"""
Application Layer: Print Formatters

Contains display and formatting logic for print document generation.
Provides business-aware formatting functions that convert domain values to display strings.

Clean Architecture Layer: Application
Responsibility: Format domain values for print document display
"""
from typing import Any
from datetime import date, datetime


def format_workflow_state(state: str) -> str:
    """Convert workflow state from slug to Sentence Case."""
    if not state:
        return ""
    return state.replace('_', ' ').title()


def get_priority_description(priority: str) -> str:
    """Get priority description for the given priority level.

    These are business-defined descriptions for each priority level.
    """
    if not priority:
        return ""

    # Normalize: strip whitespace and convert to uppercase
    priority_normalized = priority.strip().upper()

    descriptions = {
        'EMERGENCY': 'P1. Requires immediate action. Can lead to machine failure that may result to plant shutdown or can pose threat to personal health or property. Under repair classification can be either On-The-Run (OTR) or Shutdown.',
        'HIGH': 'P2. Response time within 12 hrs. Considered as important work but may not qualify as emergent. Can cause production losses and can lead to adverse consequences if not attended. May be an OTR job.',
        'MEDIUM': 'P3. Can be done or responded within 10 days. Important in nature but is not urgent nor an emergency. Work needs to be completed but it doesn\'t impose immediate impact on the plant operation and health or safety.',
        'LOW': 'P4. Normally done within 30 days after being queued. Jobs that do not create impact on plant operation (e.g. miscellaneous fabrication work, aesthetics) or may not be done during operation.',
        'SCHEDULED': 'P5. Response will be on the scheduled date. Jobs that are normally done during shutdown period. Can be a large-scale job that requires intensive planning.',
    }

    return descriptions.get(priority_normalized, "")


def format_date(val: Any) -> str:
    """Format a date value to string (Month Day, Year)."""
    if val is None:
        return ""
    if isinstance(val, (date, datetime)):
        return val.strftime("%B %d, %Y")
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val).strftime("%B %d, %Y")
        except (ValueError, TypeError):
            return val
    return str(val)


def format_datetime(val: Any) -> str:
    """Format a datetime value to string (Month Day, Year HH:MM AM/PM)."""
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.strftime("%B %d, %Y %I:%M %p")
    if isinstance(val, date):
        return val.strftime("%B %d, %Y")
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val)
            return dt.strftime("%B %d, %Y %I:%M %p")
        except (ValueError, TypeError):
            return val
    return str(val)
