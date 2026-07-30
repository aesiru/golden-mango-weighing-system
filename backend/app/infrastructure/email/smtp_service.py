"""
SMTP Email Service
===================
Concrete implementation of EmailServiceProtocol using aiosmtplib.
"""
import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.domain.protocols.email_service import EmailMessage, EmailResult

logger = logging.getLogger(__name__)


class SmtpEmailService:
    """Sends emails via SMTP (async). Implements EmailServiceProtocol."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool | None = None,
        from_address: str | None = None,
        from_name: str | None = None,
    ):
        self._host = host or settings.SMTP_HOST
        self._port = port or settings.SMTP_PORT
        self._username = username or settings.SMTP_USERNAME
        self._password = password or settings.SMTP_PASSWORD
        self._use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self._from_address = from_address or settings.EMAIL_FROM_ADDRESS or self._username
        self._from_name = from_name or settings.EMAIL_FROM_NAME

    def _build_mime(self, message: EmailMessage) -> MIMEMultipart:
        """Build a MIME message from an EmailMessage value object."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = f"{self._from_name} <{self._from_address}>"
        msg["To"] = ", ".join(message.to)

        if message.cc:
            msg["Cc"] = ", ".join(message.cc)

        if message.plain_body:
            msg.attach(MIMEText(message.plain_body, "plain"))
        msg.attach(MIMEText(message.html_body, "html"))

        return msg

    def _all_recipients(self, message: EmailMessage) -> list[str]:
        """Collect all recipients (to + cc + bcc)."""
        recipients = list(message.to)
        if message.cc:
            recipients.extend(message.cc)
        if message.bcc:
            recipients.extend(message.bcc)
        return recipients

    async def send(self, message: EmailMessage) -> EmailResult:
        """Send a single email via SMTP."""
        if not settings.EMAIL_ENABLED:
            return EmailResult(success=False, message="Email sending is disabled")

        if not self._username or not self._password:
            return EmailResult(success=False, message="SMTP credentials not configured")

        mime = self._build_mime(message)
        recipients = self._all_recipients(message)

        try:
            await aiosmtplib.send(
                mime,
                hostname=self._host,
                port=self._port,
                start_tls=self._use_tls,
                username=self._username,
                password=self._password,
                recipients=recipients,
            )
            logger.info("Email sent to %s: %s", recipients, message.subject)
            return EmailResult(
                success=True,
                message=f"Email sent to {len(recipients)} recipient(s)",
                recipient_count=len(recipients),
            )
        except Exception as e:
            logger.error("Failed to send email to %s: %s", recipients, str(e))
            return EmailResult(success=False, message=f"SMTP error: {str(e)}")

    async def send_bulk(self, messages: list[EmailMessage]) -> list[EmailResult]:
        """Send multiple emails. Each is sent independently."""
        results = []
        for msg in messages:
            result = await self.send(msg)
            results.append(result)
        return results
