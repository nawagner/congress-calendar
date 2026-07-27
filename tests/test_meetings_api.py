"""Tests for the JSON meetings API — stubbed client, no network."""

from datetime import UTC, datetime

from congress_calendar.models import CommitteeMeeting


def test_returns_window_and_meetings(stub_client):
    resp = stub_client.get("/api/meetings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["congress"] == 119
    assert body["from_date"] < body["to_date"]
    assert body["count"] == 2
    assert len(body["meetings"]) == 2


def test_meeting_shape(stub_client):
    meeting = stub_client.get("/api/meetings").json()["meetings"][0]
    assert meeting["event_id"] == "118001"
    assert meeting["chamber"] == "senate"
    assert meeting["status"] == "Scheduled"
    assert meeting["location"] == "Room 216, Hart Senate Office Building"
    assert meeting["committees"] == [
        {"name": "Judiciary Committee", "system_code": "ssju00"}
    ]
    assert meeting["url"] == (
        "https://www.congress.gov/event/119th-congress/senate-event/118001"
    )


def test_dates_are_timezone_aware(stub_client):
    for meeting in stub_client.get("/api/meetings").json()["meetings"]:
        assert datetime.fromisoformat(meeting["date"]).tzinfo is not None


def test_sorted_earliest_first(stub_client):
    dates = [m["date"] for m in stub_client.get("/api/meetings").json()["meetings"]]
    assert dates == sorted(dates)


def test_committee_filter_matches_subcommittees(stub_client):
    body = stub_client.get("/api/meetings", params={"committee": "hssy00"}).json()
    assert body["count"] == 1
    assert body["meetings"][0]["committees"][0]["system_code"] == "hssy16"


def test_chamber_is_validated(stub_client):
    assert stub_client.get("/api/meetings", params={"chamber": "moon"}).status_code == 422


def test_days_are_bounded(stub_client):
    assert stub_client.get("/api/meetings", params={"days_ahead": 400}).status_code == 422


def test_browser_cache_header(stub_client):
    resp = stub_client.get("/api/meetings")
    assert "max-age" in resp.headers["cache-control"]


def test_public_url_falls_back_to_none_for_unknown_chamber():
    meeting = CommitteeMeeting(
        event_id="1",
        date=datetime(2026, 3, 5, 15, 0, tzinfo=UTC),
        title="Joint Session",
        chamber="nodetermined",
        meeting_status="Scheduled",
        building="",
        room="",
        committees=[],
        congress=119,
    )
    assert meeting.public_url is None
    assert meeting.to_summary_dict()["location"] == ""
