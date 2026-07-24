"""
Sends booking confirmation emails over iCloud Mail SMTP, reusing the same
Apple ID + app-specific password already used for CalDAV auth.

Best-effort only: a failed send is logged and swallowed, never raised, so
it can never fail or roll back the calendar operation it follows.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("email_service")


def _send(subject: str, body: str) -> None:
    if not settings.booking_notification_email:
        return
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.apple_id
        msg["To"] = settings.booking_notification_email
        msg.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.apple_id, settings.apple_app_specific_password)
            server.send_message(msg)
    except Exception:
        logger.exception("Failed to send email: %s", subject)


def send_booking_confirmation(summary: str, start_iso: str, end_iso: str, location: str = "") -> None:
    body = (
        f"Your appointment has been booked.\n\n"
        f"Summary: {summary}\n"
        f"Start: {start_iso}\n"
        f"End: {end_iso}\n"
        f"Location: {location or '-'}\n"
    )
    _send("Booking Confirmation", body)


def send_update_confirmation(uid: str, summary: str | None, start_iso: str | None, end_iso: str | None, location: str | None = None) -> None:
    body = (
        f"Your appointment has been updated.\n\n"
        f"UID: {uid}\n"
        f"Summary: {summary or '-'}\n"
        f"Start: {start_iso or '-'}\n"
        f"End: {end_iso or '-'}\n"
        f"Location: {location or '-'}\n"
    )
    _send("Booking Update Confirmation", body)


def send_cancellation_confirmation(uid: str) -> None:
    body = f"Your appointment has been cancelled.\n\nUID: {uid}\n"
    _send("Booking Cancellation Confirmation", body)
