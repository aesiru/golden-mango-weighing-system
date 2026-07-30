"""
Email Service Protocol
=======================
Abstract interface for sending emails.
No framework or SMTP dependencies — pure domain contract.
"""
from typing import Optional, Protocol, runtime_checkable
from dataclasses import dataclass


@dataclass
class EmailMessage:
    """Value object representing an email to be sent."""
    to: list[str]
    subject: str
    html_body: str
    plain_body: Optional[str] = None
    cc: Optional[list[str]] = None
    bcc: Optional[list[str]] = None


@dataclass
class EmailResult:
    """Value object representing the outcome of sending an email."""
    success: bool
    message: str
    recipient_count: int = 0


@runtime_checkable
class EmailServiceProtocol(Protocol):
    """Interface for sending emails."""

    async def send(self, message: EmailMessage) -> EmailResult:
        """Send a single email message."""
        ...

    async def send_bulk(self, messages: list[EmailMessage]) -> list[EmailResult]:
        """Send multiple email messages."""
        ...


@runtime_checkable
class EmailTemplateRendererProtocol(Protocol):
    """Interface for rendering email templates."""

    def render(
        self,
        template_name: str,
        context: dict,
    ) -> str:
        """Render an HTML email template with the given context."""
        ...
