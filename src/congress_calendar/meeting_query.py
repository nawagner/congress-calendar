"""Shared meeting lookup — fetch, cache, parse, and filter.

Used by both the iCal feed and the JSON API so the two always agree on which
meetings a given set of filters produces.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request

from .cache import CongressLocks, DetailCache, MeetingCache
from .config import Settings
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
    if congress not in settings.supported_congresses | {settings.default_congress}:
        raise HTTPException(
            status_code=422,
            detail=f"Congress {congress} is not available; supported: "
            + ", ".join(str(c) for c in sorted(settings.supported_congresses)),
        )
    days_ahead = days_ahead if days_ahead is not None else settings.days_ahead
    days_behind = days_behind if days_behind is not None else settings.days_behind

    today = datetime.now(ET).date()
    from_date = (today - timedelta(days=days_behind)).isoformat()
    to_date = (today + timedelta(days=days_ahead)).isoformat()

    raw_meetings = await fetch_into_cache(
        settings,
        cache,
        request.app.state.details,
        request.app.state.locks,
        congress,
    )

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


async def fetch_into_cache(
    settings: Settings,
    cache: MeetingCache,
    details: DetailCache,
    locks: CongressLocks,
    congress: int,
) -> list[dict[str, Any]]:
    """Return the Congress's meetings, fetching them once if the cache is cold.

    A cold fetch enriches every meeting in the Congress, so two of them at once
    would double an already expensive job and can breach the hourly API budget.
    The per-congress lock makes concurrent callers — a request landing
    mid-warm-up, say — wait for the one fetch in flight and share its result.

    When a refresh fails or comes back visibly incomplete, the last good answer
    is served instead. The cached entry has expired by the time we get here, so
    the alternative is a 500 or a short calendar for every subscriber until the
    upstream recovers — both worse than data that is one TTL old.
    """
    cached = cache.get(congress)
    if cached is not None:
        return cached

    async with locks.get(congress):
        # Re-check: whoever held the lock has likely just filled the cache.
        cached = cache.get(congress)
        if cached is not None:
            return cached

        stale = cache.last_good(congress)
        if stale is not None and cache.in_retry_backoff(congress):
            # A refresh failed recently. Keep serving the last good copy rather
            # than hammering an upstream that is probably still failing.
            return stale

        try:
            async with CongressClient(settings, details=details) as client:
                raw = await client.fetch_meetings(congress)
        except Exception:
            if stale is None:
                raise
            cache.mark_failed(congress)
            logger.exception(
                "Refresh for congress %d failed; serving %d meetings from the "
                "last good fetch",
                congress,
                len(stale),
            )
            return stale

        cache.set(congress, raw)
        return raw


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
