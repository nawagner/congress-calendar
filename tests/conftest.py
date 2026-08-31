"""Shared test fixtures."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from congress_calendar.app import create_app

ET = ZoneInfo("America/New_York")


def _iso(days_from_today: int, hour: int) -> str:
    """A UTC timestamp that lands `days_from_today` away in Eastern time."""
    when = datetime.now(ET).replace(
        hour=hour, minute=0, second=0, microsecond=0
    ) + timedelta(days=days_from_today)
    return when.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


RAW_MEETINGS = [
    {
        "eventId": "118001",
        "date": _iso(2, 10),
        "title": "Executive Business Meeting",
        "chamber": "Senate",
        "meetingStatus": "Scheduled",
        "location": {"building": "Hart Senate Office Building", "room": "216"},
        "committees": [{"name": "Judiciary Committee", "systemCode": "ssju00"}],
    },
    {
        "eventId": "118002",
        "date": _iso(3, 14),
        "title": "Hearing on Space Policy",
        "chamber": "House",
        "meetingStatus": "Cancelled",
        "location": {"building": "Rayburn House Office Building", "room": "2318"},
        "committees": [
            {"name": "Space and Aeronautics Subcommittee", "systemCode": "hssy16"}
        ],
    },
    {
        # Missing date — must be skipped rather than blowing up the response.
        "eventId": "118003",
        "title": "Malformed",
        "chamber": "House",
    },
    {
        # Null date — same, and it used to raise TypeError out of the handler.
        "eventId": "118004",
        "date": None,
        "title": "Null date",
        "chamber": "Senate",
    },
    {
        # Held far outside any default window. Congress.gov happily returns
        # records like this — its date params filter `updateDate`, not the date
        # the meeting is held — so the date window has to exclude it locally.
        "eventId": "118005",
        "date": _iso(-200, 15),
        "title": "Long-past hearing with a recent update",
        "chamber": "Senate",
        "meetingStatus": "Scheduled",
        "location": {"building": "Dirksen Senate Office Building", "room": "419"},
        "committees": [{"name": "Intelligence Committee", "systemCode": "slin00"}],
    },
]


@pytest.fixture(autouse=True)
def no_startup_warm(monkeypatch):
    """Keep the boot-time warm-up out of the tests.

    It would fire a detail request for every meeting in the Congress the moment
    any TestClient starts. Tests that exercise warm-up turn it back on.
    """
    monkeypatch.setenv("WARM_CACHE_ON_STARTUP", "false")


@pytest.fixture
def client():
    """FastAPI test client for integration tests."""
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def stub_client(monkeypatch):
    """Test client whose Congress.gov calls return fixed data — no network."""

    async def fake_fetch(self, congress):
        return RAW_MEETINGS

    monkeypatch.setattr(
        "congress_calendar.congress_client.CongressClient.fetch_meetings", fake_fetch
    )
    monkeypatch.setenv("CONGRESS_API_KEY", "test-key")

    with TestClient(create_app()) as c:
        yield c
