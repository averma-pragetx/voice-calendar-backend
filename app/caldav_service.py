"""
CalDAV service layer: talks to Apple's iCloud CalDAV server to
create / list / update / delete events.

Auth note: Apple requires an APP-SPECIFIC PASSWORD for CalDAV access,
not the user's real Apple ID password (2FA blocks that). Generate one at:
https://appleid.apple.com -> Sign-In and Security -> App-Specific Passwords
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import caldav
from icalendar import Calendar as ICalendar
from icalendar import Event as IEvent

from app.config import settings

logger = logging.getLogger("caldav_service")

# Two iCloud accounts get mirrored writes: "user" (caller's own calendar) and
# "provider" (the business/provider's calendar). Clients/calendars cached per account.
_ACCOUNTS = {
    "user": (settings.apple_id, settings.apple_app_specific_password),
    "provider": (settings.apple_provider_id, settings.apple_app_specific_provider_password),
}

_clients: dict[str, caldav.DAVClient] = {}
_calendars: dict[str, caldav.Calendar] = {}


def _get_client(account: str = "user") -> caldav.DAVClient:
    if account not in _clients:
        username, password = _ACCOUNTS[account]
        _clients[account] = caldav.DAVClient(
            url=settings.apple_caldav_url,
            username=username,
            password=password,
        )
    return _clients[account]


def _get_calendar(account: str = "user") -> caldav.Calendar:
    """Finds and caches the target calendar on the given iCloud account."""
    if account in _calendars:
        return _calendars[account]

    client = _get_client(account)
    principal = client.principal()
    calendars = principal.calendars()

    if not calendars:
        raise RuntimeError(f"No calendars found on the '{account}' iCloud account.")

    calendar = None
    if settings.calendar_name:
        for cal in calendars:
            if cal.name == settings.calendar_name:
                calendar = cal
                break
        if calendar is None:
            raise RuntimeError(
                f"Calendar named '{settings.calendar_name}' not found on '{account}' account. "
                f"Available: {[c.name for c in calendars]}"
            )
    else:
        calendar = calendars[0]

    _calendars[account] = calendar
    return calendar


def _mirror_to_provider(action: str, fn, *args) -> None:
    """Best-effort: apply same op on provider account. Log, don't break caller's flow."""
    if not settings.apple_provider_id:
        return
    try:
        fn(_get_calendar("provider"), *args)
    except Exception as e:
        logger.error("Provider-calendar mirror failed (%s): %s", action, e)


def _parse_dt(value: str) -> datetime:
    """
    Parses an ISO 8601 datetime string (e.g. '2026-07-25T14:00:00').
    If no timezone info is present, assumes the default configured timezone.
    """
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(settings.default_timezone))
    return dt


def list_events(start_iso: str, end_iso: str, account: str = "user") -> list[dict]:
    """Lists events between start and end (inclusive), used to check availability/conflicts."""
    calendar = _get_calendar(account)
    start = _parse_dt(start_iso)
    end = _parse_dt(end_iso)

    results = calendar.date_search(start=start, end=end, expand=False)

    events = []
    for result in results:
        try:
            ical = ICalendar.from_ical(result.data)
            for component in ical.walk("VEVENT"):
                events.append(
                    {
                        "uid": str(component.get("UID")),
                        "summary": str(component.get("SUMMARY", "")),
                        "start": component.get("DTSTART").dt.isoformat(),
                        "end": component.get("DTEND").dt.isoformat(),
                        "location": str(component.get("LOCATION", "")),
                        "description": str(component.get("DESCRIPTION", "")),
                    }
                )
        except Exception as e:
            logger.warning("Skipping malformed VEVENT: %s", e)
    return events


def _find_event_by_uid(calendar: caldav.Calendar, uid: str):
    """
    iCloud's CalDAV server returns 412 Precondition Failed for UID-only
    queries with no time-range, so we can't use calendar.event_by_uid().
    Instead, date_search over a wide window (same approach as list_events)
    and match the VEVENT UID manually.
    """
    now = datetime.now(ZoneInfo(settings.default_timezone))
    start = now - timedelta(days=365)
    end = now + timedelta(days=730)

    results = calendar.date_search(start=start, end=end, expand=False)

    for result in results:
        try:
            ical = ICalendar.from_ical(result.data)
            for component in ical.walk("VEVENT"):
                if str(component.get("UID")) == uid:
                    return result
        except Exception as e:
            logger.warning("Skipping malformed VEVENT while searching for uid '%s': %s", uid, e)

    return None


def create_event(
    summary: str,
    start_iso: str,
    end_iso: str,
    description: str = "",
    location: str = "",
) -> dict:
    """Creates a new event (e.g. a plumbing appointment) on the calendar."""
    calendar = _get_calendar()
    start = _parse_dt(start_iso)
    end = _parse_dt(end_iso)
    uid = str(uuid.uuid4())

    ical = ICalendar()
    ical.add("prodid", "-//Voice Calendar Agent//EN")
    ical.add("version", "2.0")

    vevent = IEvent()
    vevent.add("uid", uid)
    vevent.add("summary", summary)
    vevent.add("dtstart", start)
    vevent.add("dtend", end)
    vevent.add("dtstamp", datetime.now(ZoneInfo("UTC")))
    if description:
        vevent.add("description", description)
    if location:
        vevent.add("location", location)

    ical.add_component(vevent)
    ical_str = ical.to_ical().decode("utf-8")
    calendar.save_event(ical_str)

    # Mirror same event (same uid) to provider's calendar so both sides stay in sync.
    _mirror_to_provider("create", lambda cal: cal.save_event(ical_str))

    return {"uid": uid, "summary": summary, "start": start_iso, "end": end_iso}


def update_event(
    uid: str,
    summary: str | None = None,
    start_iso: str | None = None,
    end_iso: str | None = None,
    description: str | None = None,
    location: str | None = None,
) -> dict:
    """Updates fields on an existing event, identified by its uid."""
    if not uid:
        raise ValueError("uid is required")

    calendar = _get_calendar()
    event = _find_event_by_uid(calendar, uid)
    if event is None:
        raise ValueError(f"No event found with uid '{uid}'")

    ical = ICalendar.from_ical(event.data)
    vevent = ical.walk("VEVENT")[0]

    if summary is not None:
        vevent["SUMMARY"] = summary
    if start_iso is not None:
        vevent["DTSTART"].dt = _parse_dt(start_iso)
    if end_iso is not None:
        vevent["DTEND"].dt = _parse_dt(end_iso)
    if description is not None:
        vevent["DESCRIPTION"] = description
    if location is not None:
        vevent["LOCATION"] = location

    event.data = ical.to_ical().decode("utf-8")
    event.save()

    def _update_provider(cal):
        p_event = _find_event_by_uid(cal, uid)
        if p_event is None:
            raise ValueError(f"No event found with uid '{uid}' on provider calendar")
        p_ical = ICalendar.from_ical(p_event.data)
        p_vevent = p_ical.walk("VEVENT")[0]
        if summary is not None:
            p_vevent["SUMMARY"] = summary
        if start_iso is not None:
            p_vevent["DTSTART"].dt = _parse_dt(start_iso)
        if end_iso is not None:
            p_vevent["DTEND"].dt = _parse_dt(end_iso)
        if description is not None:
            p_vevent["DESCRIPTION"] = description
        if location is not None:
            p_vevent["LOCATION"] = location
        p_event.data = p_ical.to_ical().decode("utf-8")
        p_event.save()

    _mirror_to_provider("update", _update_provider)

    return {"uid": uid, "status": "updated"}


def delete_event(uid: str) -> dict:
    """Deletes an event by uid."""
    if not uid:
        raise ValueError("uid is required")

    calendar = _get_calendar()
    event = _find_event_by_uid(calendar, uid)
    if event is None:
        raise ValueError(f"No event found with uid '{uid}'")

    event.delete()

    def _delete_provider(cal):
        p_event = _find_event_by_uid(cal, uid)
        if p_event is None:
            raise ValueError(f"No event found with uid '{uid}' on provider calendar")
        p_event.delete()

    _mirror_to_provider("delete", _delete_provider)

    return {"uid": uid, "status": "deleted"}
