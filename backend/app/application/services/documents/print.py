"""
Print Service
==============
Renders entity records to HTML via Jinja2 and generates PDFs using Playwright.

Supports two rendering paths:
1. Assembler-based: entity-specific assemblers gather rich data for custom templates
2. Generic: flat field list rendering via default.html template
"""
import asyncio
from pathlib import Path
from typing import Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.print.registry import get_assembler
from app.infrastructure.print.assemblers.loader import load_print_assemblers

TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent / "templates" / "print"


def _get_jinja_env() -> Environment:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def render_entity_html(
    entity_name: str,
    entity_label: str,
    record: dict,
    fields: list[dict],
    link_titles: Optional[dict] = None,
    children: Optional[list[dict]] = None,
    branding: Optional[dict] = None,
) -> str:
    """Render an entity record to printable HTML using Jinja2.
    
    Args:
        children: list of dicts with keys: label, columns (list of {name, label}), rows (list of dicts)
    """
    env = _get_jinja_env()

    # Use custom template if exists, otherwise fall back to default
    template_name = f"{entity_name}.html"
    try:
        template = env.get_template(template_name)
    except Exception:
        template = env.get_template("default.html")

    # Format field values for display
    display_fields = []
    for field in fields:
        name = field.get("name", "")
        if name in ("id", "created_at", "updated_at"):
            continue
        value = record.get(name)
        if value is None:
            value = ""
        elif isinstance(value, (datetime, date)):
            value = value.isoformat()

        # Resolve link titles
        if link_titles and field.get("link_entity"):
            key = f"{field['link_entity']}::{value}"
            value = link_titles.get(key, value)

        display_fields.append({
            "name": name,
            "label": field.get("label", name),
            "value": value,
            "field_type": field.get("field_type", "string"),
        })

    return template.render(
        entity_name=entity_name,
        entity_label=entity_label,
        record=record,
        fields=display_fields,
        children=children or [],
        record_id=record.get("id", ""),
        now=datetime.now().strftime("%Y-%m-%d %H:%M"),
        branding=branding or {"organization_name": "Organization", "description": "", "logo_url": None},
    )


async def render_with_assembler(
    entity_name: str,
    record: dict,
    db: AsyncSession,
    branding: Optional[dict] = None,
) -> Optional[str]:
    """
    Render using an entity-specific assembler if one is registered.
    Returns rendered HTML string, or None if no assembler exists.
    """
    load_print_assemblers()
    assembler = get_assembler(entity_name)
    if not assembler:
        return None

    env = _get_jinja_env()
    template_name = assembler.get_template_name()
    template = env.get_template(template_name)
    context = await assembler.assemble(record, db)
    context.setdefault("branding", branding or {"organization_name": "Organization", "description": "", "logo_url": None})
    context.setdefault("now", datetime.now().strftime("%Y-%m-%d %H:%M"))
    context.setdefault("record_id", record.get("id", "") if isinstance(record, dict) else "")
    context.setdefault("record", record if isinstance(record, dict) else {})
    return template.render(**context)


async def html_to_pdf(html_content: str) -> bytes:
    """Convert HTML string to PDF bytes using Playwright."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html_content, wait_until="networkidle")
        pdf_bytes = await page.pdf(
            format="Letter",
            margin={"top": "0.5in", "bottom": "0.5in", "left": "0.5in", "right": "0.5in"},
            print_background=True,
            display_header_footer=True,
            header_template="<span></span>",
            footer_template=(
                '<div style="width:100%;font-size:9px;color:#888;'
                'display:flex;justify-content:space-between;padding:0 0.5in;">'
                '<span class="title"></span>'
                '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span>'
                "</div>"
            ),
        )
        await browser.close()
    return pdf_bytes
