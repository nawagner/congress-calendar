"""Calendar feed endpoint — serves iCal .ics files."""

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Query, Request, Response

from ..cache import MeetingCache
from ..congress_client import CongressClient
from ..ical_builder import build_calendar, calendar_to_bytes
from ..models import CommitteeMeeting

router = APIRouter(prefix="/calendar")


@router.get("/meetings.ics")
async def meetings_ics(
    request: Request,
    chamber: str | None = Query(None, pattern="^(house|senate)$"),
    committee: str | None = Query(None, description="Comma-separated committee systemCodes"),
    congress: int | None = Query(None, ge=1, le=200),
    days_ahead: int | None = Query(None, ge=0, le=365),
    days_behind: int | None = Query(None, ge=0, le=365),
) -> Response:
    """Serve an iCal calendar feed of Congress committee meetings."""
    settings = request.app.state.settings
    cache: MeetingCache = request.app.state.cache

    congress = congress or settings.default_congress
    days_ahead = days_ahead if days_ahead is not None else settings.days_ahead
    days_behind = days_behind if days_behind is not None else settings.days_behind

    today = date.today()
    from_date = (today - timedelta(days=days_behind)).isoformat()
    to_date = (today + timedelta(days=days_ahead)).isoformat()

    # Check cache
    raw_meetings = cache.get(congress, chamber, from_date, to_date)

    if raw_meetings is None:
        async with CongressClient(settings) as client:
            raw_meetings = await client.fetch_meetings(congress, chamber, from_date, to_date)
        cache.set(congress, chamber, from_date, to_date, raw_meetings)

    # Parse into models
    meetings = _parse_meetings(raw_meetings, congress)

    # Filter by committee if requested
    if committee:
        codes = {c.strip().lower() for c in committee.split(",")}
        # Parent committee codes end in "00" — also match their subcommittees
        # e.g. "hssy00" matches "hssy15", "hssy21", etc.
        prefixes = {code[:-2] for code in codes if code.endswith("00")}
        meetings = [
            m
            for m in meetings
            if any(
                ci.system_code.lower() in codes
                or any(ci.system_code.lower().startswith(p) for p in prefixes)
                for ci in m.committees
            )
        ]

    cal = build_calendar(meetings)
    return Response(
        content=calendar_to_bytes(cal),
        media_type="text/calendar",
        headers={"Content-Disposition": "inline; filename=meetings.ics"},
    )


def _parse_meetings(raw: list[dict[str, Any]], congress: int) -> list[CommitteeMeeting]:
    """Parse raw API dicts into CommitteeMeeting models, skipping bad records."""
    meetings: list[CommitteeMeeting] = []
    for item in raw:
        try:
            meetings.append(CommitteeMeeting.from_api_response(item, congress))
        except (KeyError, ValueError):
            continue
    return meetings
