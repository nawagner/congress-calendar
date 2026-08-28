"""Integration tests — hits the live Congress.gov API."""


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_meetings_ics_senate(client):
    resp = client.get("/calendar/meetings.ics", params={"chamber": "senate"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/calendar; charset=utf-8"
    body = resp.text
    assert "BEGIN:VCALENDAR" in body
    assert "END:VCALENDAR" in body


def test_senate_feed_is_not_empty(client):
    """A well-formed but empty calendar used to pass every test here.

    Over a year-wide window the Senate always has meetings on record, so an
    empty feed means we dropped them, not that Congress was idle.
    """
    resp = client.get(
        "/calendar/meetings.ics",
        params={"chamber": "senate", "days_behind": 365, "days_ahead": 90},
    )
    assert resp.status_code == 200
    assert resp.text.count("BEGIN:VEVENT") > 50


def test_senate_and_house_are_both_well_represented(client):
    """Guards against one chamber silently collapsing to zero."""
    params = {"days_behind": 365, "days_ahead": 90}
    senate = client.get(
        "/calendar/meetings.ics", params={**params, "chamber": "senate"}
    ).text.count("BEGIN:VEVENT")
    house = client.get(
        "/calendar/meetings.ics", params={**params, "chamber": "house"}
    ).text.count("BEGIN:VEVENT")
    assert senate > 50 and house > 50


def test_feed_excludes_meetings_held_outside_the_window(client):
    """The window must bound meeting dates, not each record's updateDate."""
    from datetime import UTC, datetime, timedelta

    resp = client.get("/calendar/meetings.ics", params={"days_behind": 7, "days_ahead": 7})
    assert resp.status_code == 200

    starts = [
        line.split(":", 1)[1].strip()
        for line in resp.text.splitlines()
        if line.startswith("DTSTART")
    ]
    today = datetime.now(UTC).date()
    for raw in starts:
        held = datetime.strptime(raw.rstrip("Z")[:8], "%Y%m%d").date()
        assert today - timedelta(days=8) <= held <= today + timedelta(days=8), raw


def test_meetings_ics_house(client):
    resp = client.get("/calendar/meetings.ics", params={"chamber": "house"})
    assert resp.status_code == 200
    assert "BEGIN:VCALENDAR" in resp.text


def test_meetings_ics_with_committee_filter(client):
    resp = client.get(
        "/calendar/meetings.ics",
        params={"chamber": "senate", "committee": "ssju00"},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "BEGIN:VCALENDAR" in body


def test_parent_committee_includes_subcommittee_meetings(client):
    """Filtering by a parent code like hssy00 should also return subcommittee meetings."""
    resp = client.get(
        "/calendar/meetings.ics",
        params={"chamber": "house", "committee": "hssy00", "days_behind": 365},
    )
    assert resp.status_code == 200
    body = resp.text

    # The feed should contain at least one subcommittee meeting.
    # Subcommittee events include "Subcommittee" in their SUMMARY line.
    assert "Subcommittee" in body, (
        "Expected at least one subcommittee meeting when filtering by parent code hssy00"
    )


def test_invalid_chamber(client):
    resp = client.get("/calendar/meetings.ics", params={"chamber": "invalid"})
    assert resp.status_code == 422
