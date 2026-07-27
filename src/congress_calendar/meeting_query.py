"""Shared meeting lookup — fetch, cache, parse, and filter.

Used by both the iCal feed and the JSON API so the two always agree on which
meetings a given set of filters produces.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from fastapi import Request

from .cache import MeetingCache
from .congress_client import CongressClient
from .models import CommitteeMeeting


@dataclass(frozen=True)
class MeetingWindow:
    """Meetings for a resolved congress + date window."""

    congress: int
    from_date: str
    to_date: str
    meetings: list[CommitteeMeeting]


async def load_meetings(
    request: Request,
    chamber: str | None = None,
    congress: int | None = None,
    days_ahead: int | None = None,
    days_behind: int | None = None,
) -> MeetingWindow:
    """Resolve query defaults, then fetch meetings (from cache when warm)."""
    settings = request.app.state.settings
    cache: MeetingCache = request.app.state.cache

    congress = congress or settings.default_congress
    days_ahead = days_ahead if days_ahead is not None else settings.days_ahead
    days_behind = days_behind if days_behind is not None else settings.days_behind

    today = date.today()
    from_date = (today - timedelta(days=days_behind)).isoformat()
    to_date = (today + timedelta(days=days_ahead)).isoformat()

    raw_meetings = cache.get(congress, chamber, from_date, to_date)

    if raw_meetings is None:
        async with CongressClient(settings) as client:
            raw_meetings = await client.fetch_meetings(congress, chamber, from_date, to_date)
        cache.set(congress, chamber, from_date, to_date, raw_meetings)

    return MeetingWindow(
        congress=congress,
        from_date=from_date,
        to_date=to_date,
        meetings=parse_meetings(raw_meetings, congress),
    )


def parse_meetings(raw: list[dict[str, Any]], congress: int) -> list[CommitteeMeeting]:
    """Parse raw API dicts into CommitteeMeeting models, skipping bad records."""
    meetings: list[CommitteeMeeting] = []
    for item in raw:
        try:
            meetings.append(CommitteeMeeting.from_api_response(item, congress))
        except (KeyError, ValueError):
            continue
    return meetings


def filter_by_committee(
    meetings: list[CommitteeMeeting], committee: str
) -> list[CommitteeMeeting]:
    """Filter meetings by committee code(s).

    Parent committee codes (ending in "00") also match their subcommittees.
    For example, "hssy00" matches "hssy00", "hssy15", "hssy21", etc.
    """
    codes = {c.strip().lower() for c in committee.split(",")}
    prefixes = {code[:-2] for code in codes if code.endswith("00")}
    return [
        m
        for m in meetings
        if any(
            ci.system_code.lower() in codes
            or any(ci.system_code.lower().startswith(p) for p in prefixes)
            for ci in m.committees
        )
    ]
