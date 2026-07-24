"""
Google Calendar service layer: same interface as caldav_service.py
(list_events / create_event / update_event / delete_event), backed by
the Google Calendar API v3 instead of CalDAV.

Auth note: uses OAuth2 with a long-lived refresh token. Get one by running
scripts/google_oauth_setup.py once and pasting the printed values into .env
(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN).
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings

_service = None


def _get_service():
    global _service
    if _service is None:
        creds = Credentials(
            token=None,
            refresh_token=settings.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        _service = build("calendar", "v3", credentials=creds)
    return _service


def _parse_dt(value: str) -> datetime:
    """Parses an ISO 8601 datetime string, assuming default_timezone if none given."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(settings.default_timezone))
    return dt


def list_events(start_iso: str, end_iso: str) -> list[dict]:
    """Lists events between start and end, used to check availability/conflicts."""
    service = _get_service()
    start = _parse_dt(start_iso)
    end = _parse_dt(end_iso)

    result = (
        service.events()
        .list(
            calendarId=settings.google_calendar_id,
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = []
    for item in result.get("items", []):
        events.append(
            {
                "uid": item["id"],
                "summary": item.get("summary", ""),
                "start": item["start"].get("dateTime", item["start"].get("date")),
                "end": item["end"].get("dateTime", item["end"].get("date")),
                "location": item.get("location", ""),
                "description": item.get("description", ""),
            }
        )
    return events


def create_event(
    summary: str,
    start_iso: str,
    end_iso: str,
    description: str = "",
    location: str = "",
) -> dict:
    """Creates a new event on the calendar."""
    service = _get_service()
    start = _parse_dt(start_iso)
    end = _parse_dt(end_iso)

    body = {
        "summary": summary,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location

    created = service.events().insert(calendarId=settings.google_calendar_id, body=body).execute()

    return {"uid": created["id"], "summary": summary, "start": start_iso, "end": end_iso}


def update_event(
    uid: str,
    summary: str | None = None,
    start_iso: str | None = None,
    end_iso: str | None = None,
    description: str | None = None,
    location: str | None = None,
) -> dict:
    """Updates fields on an existing event, identified by its uid (Google event id)."""
    service = _get_service()

    try:
        event = service.events().get(calendarId=settings.google_calendar_id, eventId=uid).execute()
    except Exception as e:
        raise ValueError(f"No event found with uid '{uid}'") from e

    if summary is not None:
        event["summary"] = summary
    if start_iso is not None:
        event["start"] = {"dateTime": _parse_dt(start_iso).isoformat()}
    if end_iso is not None:
        event["end"] = {"dateTime": _parse_dt(end_iso).isoformat()}
    if description is not None:
        event["description"] = description
    if location is not None:
        event["location"] = location

    service.events().update(calendarId=settings.google_calendar_id, eventId=uid, body=event).execute()

    return {"uid": uid, "status": "updated"}


def delete_event(uid: str) -> dict:
    """Deletes an event by uid (Google event id)."""
    service = _get_service()
    try:
        service.events().delete(calendarId=settings.google_calendar_id, eventId=uid).execute()
    except Exception as e:
        raise ValueError(f"No event found with uid '{uid}'") from e

    return {"uid": uid, "status": "deleted"}
