"""Tests for the real meeting-date window and the per-event detail cache.

Congress.gov applies `fromDateTime`/`toDateTime` to each record's `updateDate`,
not to the date the meeting is held, and offers no way to filter or sort by the
latter. The window therefore has to be enforced locally, against the parsed
meeting dates.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import httpx

from congress_calendar.cache import DetailCache
from congress_calendar.config import Settings
from congress_calendar.congress_client import CongressClient
from congress_calendar.meeting_query import filter_by_date
from congress_calendar.models import CommitteeMeeting

ET = ZoneInfo("America/New_York")


def _meeting(when: datetime, chamber: str = "senate") -> CommitteeMeeting:
    return CommitteeMeeting(
        event_id="1",
        date=when,
        title="Hearing",
        chamber=chamber,
        meeting_status="Scheduled",
        building="",
        room="",
        committees=[],
        congress=119,
    )


def test_window_keeps_meetings_held_inside_it():
    kept = filter_by_date(
        [_meeting(datetime(2026, 9, 15, 14, 0, tzinfo=UTC))],
        "2026-08-28",
        "2026-09-27",
    )
    assert len(kept) == 1


def test_window_drops_a_meeting_held_outside_it():
    """The Feb hearing that a July-September query used to return."""
    kept = filter_by_date(
        [_meeting(datetime(2026, 2, 4, 20, 0, tzinfo=UTC))],
        "2026-07-29",
        "2026-09-27",
    )
    assert kept == []


def test_window_boundaries_are_inclusive():
    inside = [
        _meeting(datetime(2026, 7, 29, 13, 30, tzinfo=UTC)),
        _meeting(datetime(2026, 9, 27, 15, 0, tzinfo=UTC)),
    ]
    assert len(filter_by_date(inside, "2026-07-29", "2026-09-27")) == 2


def test_window_is_judged_in_eastern_time():
    """7pm ET on the last day is the next day in UTC — it must still count."""
    late = _meeting(datetime(2026, 9, 27, 23, 30, tzinfo=UTC))  # 7:30pm ET Sep 27
    assert len(filter_by_date([late], "2026-08-28", "2026-09-27")) == 1


def test_naive_datetimes_are_treated_as_utc():
    kept = filter_by_date(
        [_meeting(datetime(2026, 9, 15, 14, 0))], "2026-08-28", "2026-09-27"
    )
    assert len(kept) == 1


def _handler_factory(detail_calls):
    def handler(request):
        path = request.url.path
        if path.rstrip("/").count("/") == 4:  # list call
            chamber = "senate" if "/senate" in path else "house"
            count = 3 if chamber == "senate" else 0
            return httpx.Response(
                200,
                json={
                    "committeeMeetings": [
                        {
                            "eventId": str(i),
                            "updateDate": "2026-08-01T00:00:00Z",
                            "url": (
                                "https://api.congress.gov/v3/committee-meeting/"
                                f"119/senate/{i}?format=json"
                            ),
                        }
                        for i in range(count)
                    ],
                    "pagination": {"count": count},
                },
            )
        detail_calls.append(path)
        event_id = path.rsplit("/", 1)[-1]
        return httpx.Response(
            200,
            json={
                "committeeMeeting": {
                    "eventId": event_id,
                    "date": "2026-09-01T14:00:00Z",
                    "title": "Hearing",
                    "chamber": "Senate",
                    "committees": [],
                }
            },
        )

    return handler


async def test_unchanged_meetings_are_not_refetched():
    """A refresh must only pay for records whose updateDate moved."""
    detail_calls: list[str] = []
    settings = Settings(congress_api_key="test-key")
    details = DetailCache()

    for _ in range(2):
        client = CongressClient(settings, details=details)
        client._client = httpx.AsyncClient(
            base_url=settings.congress_api_base_url,
            transport=httpx.MockTransport(_handler_factory(detail_calls)),
        )
        meetings = await client.fetch_meetings(119)
        assert len(meetings) == 3
        await client._client.aclose()

    # Three details on the cold pass, zero on the warm one.
    assert len(detail_calls) == 3


async def test_a_changed_update_date_invalidates_the_cached_detail():
    details = DetailCache()
    details.set("7", "2026-08-01T00:00:00Z", {"eventId": "7"})
    assert details.get("7", "2026-08-01T00:00:00Z") is not None
    assert details.get("7", "2026-08-20T00:00:00Z") is None


def test_out_of_window_meeting_is_excluded_from_the_api(stub_client):
    """Fixture 118005 is held 200 days ago; the default window must drop it."""
    body = stub_client.get("/api/meetings").json()
    assert "118005" not in [m["event_id"] for m in body["meetings"]]
    assert body["count"] == 2


def test_widening_the_window_lets_the_old_meeting_back_in(stub_client):
    body = stub_client.get("/api/meetings", params={"days_behind": 365}).json()
    assert "118005" in [m["event_id"] for m in body["meetings"]]


def test_days_ahead_actually_bounds_the_result(stub_client):
    """Fixture 118001/118002 sit 2 and 3 days out; days_ahead=1 excludes both."""
    body = stub_client.get(
        "/api/meetings", params={"days_ahead": 1, "days_behind": 0}
    ).json()
    assert body["count"] == 0


def test_chamber_filter_applies_after_the_shared_fetch(stub_client):
    body = stub_client.get("/api/meetings", params={"chamber": "senate"}).json()
    assert [m["event_id"] for m in body["meetings"]] == ["118001"]


async def test_concurrent_cold_fetches_only_hit_the_api_once():
    """Two callers racing a cold cache must share one fetch, not double it.

    A cold fetch enriches the whole Congress, so a duplicate would both double
    the work and risk breaching the hourly API budget.
    """
    import asyncio

    from congress_calendar.cache import MeetingCache
    from congress_calendar.meeting_query import fetch_into_cache

    detail_calls: list[str] = []
    settings = Settings(congress_api_key="test-key")
    cache = MeetingCache()
    details = DetailCache()
    lock = asyncio.Lock()

    real_fetch = CongressClient.fetch_meetings
    fetches = 0

    async def counting_fetch(self, congress):
        nonlocal fetches
        fetches += 1
        self._client = httpx.AsyncClient(
            base_url=settings.congress_api_base_url,
            transport=httpx.MockTransport(_handler_factory(detail_calls)),
        )
        try:
            return await real_fetch(self, congress)
        finally:
            await self._client.aclose()

    CongressClient.fetch_meetings = counting_fetch
    try:
        results = await asyncio.gather(
            *[fetch_into_cache(settings, cache, details, lock, 119) for _ in range(4)]
        )
    finally:
        CongressClient.fetch_meetings = real_fetch

    assert fetches == 1
    assert all(len(r) == 3 for r in results)


def test_warm_up_failure_does_not_break_the_app(monkeypatch):
    """A failed warm-up costs latency, not availability."""
    from fastapi.testclient import TestClient

    from congress_calendar.app import create_app

    monkeypatch.setenv("WARM_CACHE_ON_STARTUP", "true")
    monkeypatch.setenv("CONGRESS_API_KEY", "test-key")

    async def boom(self, congress):
        raise RuntimeError("Congress.gov is down")

    monkeypatch.setattr(
        "congress_calendar.congress_client.CongressClient.fetch_meetings", boom
    )
    with TestClient(create_app()) as c:
        assert c.get("/health").status_code == 200


def test_startup_warm_up_spares_the_first_request(monkeypatch):
    """Boot fetches once; the first visitor reuses it rather than refetching.

    Whether the request lands before or after the warm-up finishes, the lock in
    fetch_into_cache means exactly one fetch happens either way.
    """
    from fastapi.testclient import TestClient

    from congress_calendar.app import create_app

    monkeypatch.setenv("WARM_CACHE_ON_STARTUP", "true")
    monkeypatch.setenv("CONGRESS_API_KEY", "test-key")

    calls = {"n": 0}

    async def counting_fetch(self, congress):
        calls["n"] += 1
        return [
            {
                "eventId": "1",
                "date": "2026-09-01T14:00:00Z",
                "title": "Hearing",
                "chamber": "Senate",
                "committees": [],
            }
        ]

    monkeypatch.setattr(
        "congress_calendar.congress_client.CongressClient.fetch_meetings", counting_fetch
    )
    with TestClient(create_app()) as c:
        assert c.get("/api/meetings").status_code == 200
        assert c.get("/api/meetings").status_code == 200

    assert calls["n"] == 1
