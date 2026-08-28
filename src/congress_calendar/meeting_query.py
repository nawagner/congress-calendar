"""Shared meeting lookup — fetch, cache, parse, and filter.

Used by both the iCal feed and the JSON API so the two always agree on which
meetings a given set of filters produces.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import Request

from .cache import MeetingCache
from .congress_client import CongressClient
from .models import CommitteeMeeting

logger = logging.getLogger("congress-calendar.query")

# Congress sits on Eastern time, and the UI renders every meeting in ET, so the
# date window has to be judged in ET too — otherwise a 7pm ET hearing on the
# last day of the window reads as the next day in UTC and falls out of it.
ET = ZoneInfo("America/New_York")


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

    today = datetime.now(ET).date()
    from_date = (today - timedelta(days=days_behind)).isoformat()
    to_date = (today + timedelta(days=days_ahead)).isoformat()

    raw_meetings = cache.get(congress)

    if raw_meetings is None:
        async with CongressClient(settings, details=request.app.state.details) as client:
            raw_meetings = await client.fetch_meetings(congress)
        cache.set(congress, raw_meetings)

    meetings = parse_meetings(raw_meetings, congress)
    meetings = filter_by_date(meetings, from_date, to_date)
    if chamber:
        meetings = [m for m in meetings if m.chamber == chamber]

    return MeetingWindow(
        congress=congress,
        from_date=from_date,
        to_date=to_date,
        meetings=meetings,
    )


def filter_by_date(
    meetings: list[CommitteeMeeting], from_date: str, to_date: str
) -> list[CommitteeMeeting]:
    """Keep meetings held within [from_date, to_date] inclusive, judged in ET.

    This is the real date window. Congress.gov can't apply one server-side —
    its date params filter each record's `updateDate` instead — so the window
    the caller asked for is enforced here, against the date each meeting is
    actually held.
    """
    kept = []
    for m in meetings:
        when = m.date if m.date.tzinfo else m.date.replace(tzinfo=UTC)
        held_on = when.astimezone(ET).date().isoformat()
        if from_date <= held_on <= to_date:
            kept.append(m)
    return kept


def parse_meetings(raw: list[dict[str, Any]], congress: int) -> list[CommitteeMeeting]:
    """Parse raw API dicts into CommitteeMeeting models, skipping bad records.

    A record missing `date` raises KeyError, a null one TypeError, and an
    unparseable one ValueError — all mean the same thing here: no usable
    meeting. Skipping is right, but silence is not, so the losses are logged.
    """
    meetings: list[CommitteeMeeting] = []
    skipped = 0
    for item in raw:
        try:
            meetings.append(CommitteeMeeting.from_api_response(item, congress))
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
    if skipped:
        logger.warning("Skipped %d of %d meeting records that failed to parse", skipped, len(raw))
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
