"""The Congress number follows the calendar, including across January 3.

Before this, the 119th was hard-coded: from 2027-01-03, when the 120th
convenes, the app would have kept enumerating the 119th and shown no new
meetings at all.
"""

import time
from collections import Counter
from datetime import date

import pytest
from fastapi.testclient import TestClient

from congress_calendar.app import create_app
from congress_calendar.config import congress_on
from congress_calendar.congress_client import CongressApiError

# One meeting held late in the 119th, one early in the 120th.
MEETINGS = {
    119: {"eventId": "338900", "date": "2026-12-17T15:00:00Z", "chamber": "Senate"},
    120: {"eventId": "120001", "date": "2027-01-08T15:00:00Z", "chamber": "House"},
}


@pytest.mark.parametrize(
    ("day", "congress"),
    [
        (date(2025, 1, 3), 119),
        (date(2026, 10, 26), 119),
        (date(2026, 12, 31), 119),
        (date(2027, 1, 2), 119),
        (date(2027, 1, 3), 120),
        (date(2028, 12, 31), 120),
        (date(2029, 1, 3), 121),
    ],
)
def test_congress_number_follows_the_date(day, congress):
    assert congress_on(day) == congress


@pytest.fixture
def at(monkeypatch):
    """Start an app whose 'today' is the given date; return (client, fetches)."""
    clients = []

    def start(today: date, fail: frozenset[int] = frozenset(), **env):
        fetched: Counter[int] = Counter()

        async def fake_fetch(self, congress):
            fetched[congress] += 1
            if congress in fail:
                raise CongressApiError("OVER_RATE_LIMIT", "budget spent")
            m = MEETINGS.get(congress)
            return [{**m, "title": "Hearing", "committees": []}] if m else []

        monkeypatch.setattr(
            "congress_calendar.congress_client.CongressClient.fetch_meetings", fake_fetch
        )
        monkeypatch.setattr("congress_calendar.meeting_query.today_in_et", lambda: today)
        monkeypatch.setattr("congress_calendar.app.today_in_et", lambda: today)
        monkeypatch.setenv("CONGRESS_API_KEY", "test-key")
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        client = TestClient(create_app())
        client.__enter__()
        clients.append(client)
        return client, fetched

    yield start
    for client in clients:
        client.__exit__(None, None, None)


def test_the_month_after_january_3_shows_both_congresses(at):
    client, fetched = at(date(2027, 1, 10))
    body = client.get("/api/meetings").json()
    assert body["congress"] == 120
    assert [m["event_id"] for m in body["meetings"]] == ["338900", "120001"]
    assert set(fetched) == {119, 120}
    # Each meeting keeps its own Congress, so its UID and link stay correct.
    assert "338900.119@congress-calendar" in client.get("/calendar/meetings.ics").text
    assert body["meetings"][1]["url"].endswith("/120th-congress/house-event/120001")


def test_a_window_inside_one_congress_fetches_only_that_one(at):
    client, fetched = at(date(2027, 1, 10))
    body = client.get("/api/meetings", params={"days_behind": 0}).json()
    assert [m["event_id"] for m in body["meetings"]] == []
    assert set(fetched) == {120}


def test_a_wide_window_keeps_the_outgoing_congress_after_the_first_month(at):
    """The request's own start decides, not the server's default lookback."""
    client, fetched = at(date(2027, 2, 10))
    body = client.get("/api/meetings", params={"days_behind": 60}).json()
    assert [m["event_id"] for m in body["meetings"]] == ["338900", "120001"]

    client, fetched = at(date(2027, 2, 10))
    body = client.get("/api/meetings").json()
    assert [m["event_id"] for m in body["meetings"]] == []
    assert set(fetched) == {120}, "a 30-day window no longer reaches the 119th"


def test_only_the_current_and_previous_congress_can_be_named(at):
    client, _ = at(date(2027, 3, 1))
    assert client.get("/api/meetings", params={"congress": 120}).status_code == 200
    assert client.get("/api/meetings", params={"congress": 119}).status_code == 200
    assert client.get("/api/meetings", params={"congress": 118}).status_code == 422


def test_supported_congresses_adds_to_the_automatic_set(at):
    client, fetched = at(date(2027, 1, 10), SUPPORTED_CONGRESSES="[118]")
    body = client.get("/api/meetings").json()
    assert [m["event_id"] for m in body["meetings"]] == ["338900", "120001"]
    assert set(fetched) == {119, 120}
    assert client.get("/api/meetings", params={"congress": 118}).status_code == 200


def test_a_failing_outgoing_congress_does_not_fail_the_calendar(at):
    client, _ = at(date(2027, 1, 10), fail=frozenset({119}))
    resp = client.get("/api/meetings")
    assert resp.status_code == 200
    assert [m["event_id"] for m in resp.json()["meetings"]] == ["120001"]
    assert client.get("/calendar/meetings.ics").status_code == 200


def test_a_failing_current_congress_still_fails_loudly(at):
    client, _ = at(date(2027, 1, 10), fail=frozenset({120}))
    with pytest.raises(CongressApiError):
        client.get("/api/meetings")


def test_a_pinned_default_congress_is_still_honoured(at):
    client, fetched = at(date(2027, 1, 10), DEFAULT_CONGRESS="119")
    body = client.get("/api/meetings", params={"days_behind": 60}).json()
    assert body["congress"] == 119
    assert [m["event_id"] for m in body["meetings"]] == ["338900"]
    assert set(fetched) == {119}


def test_warm_up_loads_both_congresses_in_the_transition_month(at):
    client, fetched = at(date(2027, 1, 10), WARM_CACHE_ON_STARTUP="true")
    # Checked before any request, so only the warm-up can have fetched.
    deadline = time.monotonic() + 5
    while fetched != Counter({119: 1, 120: 1}) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert fetched == Counter({119: 1, 120: 1})
    client.get("/api/meetings")
    assert fetched == Counter({119: 1, 120: 1}), "the request reuses the warm cache"


def test_warm_up_still_warms_the_current_congress_if_the_outgoing_one_fails(at):
    _, fetched = at(date(2027, 1, 10), fail=frozenset({119}), WARM_CACHE_ON_STARTUP="true")
    deadline = time.monotonic() + 5
    while set(fetched) != {119, 120} and time.monotonic() < deadline:
        time.sleep(0.01)
    assert set(fetched) == {119, 120}
