"""
Jinja Email Template Renderer
===============================
Renders HTML email templates using Jinja2.
Implements EmailTemplateRendererProtocol.
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "email"


class JinjaEmailTemplateRenderer:
    """Renders email templates from the templates/email directory."""

    def __init__(self, template_dir: Path | None = None):
        self._template_dir = template_dir or TEMPLATE_DIR
        self._template_dir.mkdir(parents=True, exist_ok=True)
        self._env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            autoescape=select_autoescape(["html"]),
        )

    def render(self, template_name: str, context: dict) -> str:
        """Render a Jinja2 email template with the given context."""
        template = self._env.get_template(template_name)
        return template.render(**context)
