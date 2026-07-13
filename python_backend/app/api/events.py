"""REST endpoint for the UI event bridge (FAZA 11).

GET /events?since=<timestamp> — polled by the renderer every few seconds
to receive backend-originated events (artifact.created, tool.*,
backend.ready) in order. Events are stored in SQLite via EventBus.
"""
from fastapi import APIRouter, Query, Request

from app.core.errors import AppError
from app.services.event_bus import EventBus

router = APIRouter(tags=["events"])


def _service(request: Request) -> EventBus:
    service = getattr(request.app.state, "event_bus", None)
    if service is None:
        raise AppError("EVENTS_UNAVAILABLE", "Event bus is not initialized.", status_code=500)
    return service


@router.get("/events")
def list_events(
    request: Request,
    since: str | None = Query(default=None, description="ISO timestamp cursor"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    service = _service(request)
    if since:
        events = service.since(since, limit=limit)
    else:
        events = service.recent(limit=limit)
    # Return oldest-first for cursor-based polling; `recent` returns newest-first,
    # so reverse it to keep a consistent ordering for the UI.
    if not since:
        events = list(reversed(events))
    return {
        "events": events,
        # The timestamp of the last event (oldest when since given, newest otherwise)
        # so the UI can use it as the next `since` cursor.
        "next_cursor": events[-1]["timestamp"] if events else None,
    }
