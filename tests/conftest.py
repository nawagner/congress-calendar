"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from congress_calendar.app import create_app

RAW_MEETINGS = [
    {
        "eventId": "118001",
        "date": "2026-03-05T15:00:00Z",
        "title": "Executive Business Meeting",
        "chamber": "Senate",
        "meetingStatus": "Scheduled",
        "location": {"building": "Hart Senate Office Building", "room": "216"},
        "committees": [{"name": "Judiciary Committee", "systemCode": "ssju00"}],
    },
    {
        "eventId": "118002",
        "date": "2026-03-06T14:30:00Z",
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
]


@pytest.fixture
def client():
    """FastAPI test client for integration tests."""
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def stub_client(monkeypatch):
    """Test client whose Congress.gov calls return fixed data — no network."""

    async def fake_fetch(self, congress, chamber, from_date, to_date):
        return RAW_MEETINGS

    monkeypatch.setattr(
        "congress_calendar.congress_client.CongressClient.fetch_meetings", fake_fetch
    )
    monkeypatch.setenv("CONGRESS_API_KEY", "test-key")

    with TestClient(create_app()) as c:
        yield c
