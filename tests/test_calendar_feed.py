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


def test_invalid_chamber(client):
    resp = client.get("/calendar/meetings.ics", params={"chamber": "invalid"})
    assert resp.status_code == 422
