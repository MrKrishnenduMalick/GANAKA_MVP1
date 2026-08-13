"""Transactional email delivery.

Every message is persisted to the `outbound_email` collection first (delivery
ledger, so an operator can always prove what was sent to whom), then handed to
SMTP when SMTP credentials are configured. Secrets and tokens are never logged;
only the rendered body stored in the ledger contains the link.
"""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core import db as database
from app.core.config import settings
from app.core.models import new_id, utc_now

logger = logging.getLogger("ganaka.email")

TEMPLATES = {
    "VERIFY_EMAIL": (
        "Verify your Ganaka account",
        "Welcome to Ganaka.\n\nConfirm your email address to activate your account:\n{link}\n\n"
        "This link expires in {ttl_hours} hours and can be used once.",
    ),
    "REGISTER_COLLISION": (
        "Someone tried to register with your email",
        "Someone attempted to create a Ganaka account using your email address.\n\n"
        "If this was not you, no action is needed — your existing account is unchanged.\n"
        "If you have forgotten your password, reset it here:\n{link}",
    ),
    "PASSWORD_RESET": (
        "Reset your Ganaka password",
        "A password reset was requested for your Ganaka account.\n\n{link}\n\n"
        "This link expires in {ttl_minutes} minutes. All active sessions are signed out once the"
        " password is changed.",
    ),
    "PASSWORD_CHANGED": (
        "Your Ganaka password was changed",
        "Your Ganaka password was just changed and all active sessions were signed out.\n\n"
        "If this was not you, reset your password immediately.",
    ),
    "ACCOUNT_LOCKED": (
        "Your Ganaka account was temporarily locked",
        "We locked your Ganaka account for {lock_minutes} minutes after {attempts} failed sign-in"
        " attempts.\n\nIf this was not you, reset your password once the lock expires.",
    ),
    "GOOGLE_LINKING_REQUIRED": (
        "A Google sign-in was attempted on your Ganaka account",
        "Someone tried to sign in to Ganaka with Google using your email address.\n\n"
        "For your security we did not sign them in. To use Google sign-in, log in with your"
        " password once and link Google from Account Settings. If you no longer have your"
        " password, reset it here:\n{link}",
    ),
    "WORKSPACE_INVITATION": (
        "You have been invited to a Ganaka workspace",
        "{inviter} invited you to join the workspace \"{workspace_name}\" on Ganaka as {role}.\n\n"
        "Accept the invitation:\n{link}\n\nThis invitation expires in {ttl_days} days.",
    ),
    # ARCH-AUDIT-003 fix: generic operational-notification template used by
    # app.modules.shopify.service.send_notification (integration failures,
    # OAuth expiry, critical reconciliation exceptions, etc).
    "WORKSPACE_NOTIFICATION": (
        "Ganaka alert: {notification_title}",
        "{message}\n\nWorkspace: {workspace_name}\nEvent: {notification_type}",
    ),
}


def _send_smtp(to_email: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as smtp:
        smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)


async def send(template: str, to_email: str, **context) -> dict:
    subject, body_template = TEMPLATES[template]
    body = body_template.format(**context)

    status = "SENT" if settings.email_transport_configured else "PENDING_NO_TRANSPORT"
    error = None
    if settings.email_transport_configured:
        try:
            await asyncio.to_thread(_send_smtp, to_email, subject, body)
        except Exception as exc:  # noqa: BLE001 - delivery failures must not break the request
            status, error = "FAILED", type(exc).__name__
            logger.error("email_delivery_failed template=%s status=%s", template, status)

    await database.db[database.OUTBOUND_EMAIL].insert_one(
        {
            "_id": new_id(),
            "template": template,
            "to_email": to_email,
            "subject": subject,
            "body": body,
            "status": status,
            "error": error,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
    )
    logger.info("email_recorded template=%s status=%s", template, status)
    # ARCH-AUDIT-003 fix: callers that need to know whether delivery actually
    # succeeded (rather than just being logged) can inspect this. Existing
    # callers all use `await email_service.send(...)` without capturing a
    # return value, so this is additive and does not change their behavior.
    return {"status": status, "error": error}
