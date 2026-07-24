"""
Endpoints for the demo frontend: reads/writes events on the user's Apple
calendar. Writes (create/update/delete) auto-mirror to the provider's
calendar inside caldav_service, same as the ElevenLabs tool webhooks do —
the frontend demo shows both iCloud accounts being kept in sync live.
"""
import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app import caldav_service

logger = logging.getLogger("calendar_view")

router = APIRouter(prefix="/calendar", tags=["calendar-view"])


class CreateEventBody(BaseModel):
    summary: str = Field(...)
    start_iso: str = Field(...)
    end_iso: str = Field(...)
    description: str = ""
    location: str = ""


class UpdateEventBody(BaseModel):
    summary: str | None = None
    start_iso: str | None = None
    end_iso: str | None = None
    description: str | None = None
    location: str | None = None


@router.get("/events")
def get_events(
    account: str = Query(..., pattern="^(user|provider)$"),
    start_iso: str = Query(...),
    end_iso: str = Query(...),
):
    try:
        events = caldav_service.list_events(start_iso, end_iso, account=account)
        return {"account": account, "events": events, "count": len(events)}
    except Exception as e:
        logger.exception("get_events failed for account=%s", account)
        raise HTTPException(status_code=400, detail=f"{type(e).__name__}: {e}")


@router.post("/events")
def create_event(payload: CreateEventBody):
    try:
        return caldav_service.create_event(
            summary=payload.summary,
            start_iso=payload.start_iso,
            end_iso=payload.end_iso,
            description=payload.description,
            location=payload.location,
        )
    except Exception as e:
        logger.exception("create_event failed")
        raise HTTPException(status_code=400, detail=f"{type(e).__name__}: {e}")


@router.patch("/events/{uid}")
def update_event(uid: str, payload: UpdateEventBody):
    try:
        return caldav_service.update_event(
            uid=uid,
            summary=payload.summary,
            start_iso=payload.start_iso,
            end_iso=payload.end_iso,
            description=payload.description,
            location=payload.location,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("update_event failed")
        raise HTTPException(status_code=400, detail=f"{type(e).__name__}: {e}")


@router.delete("/events/{uid}")
def delete_event(uid: str):
    try:
        return caldav_service.delete_event(uid=uid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("delete_event failed")
        raise HTTPException(status_code=400, detail=f"{type(e).__name__}: {e}")
