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
