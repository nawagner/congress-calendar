"""Tests for the landing page — the browse view is rendered client-side."""


def test_page_renders(stub_client):
    resp = stub_client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


def test_placeholders_are_substituted(stub_client):
    body = stub_client.get("/").text
    assert "%%BASE_URL%%" not in body
    assert "%%COMMITTEES_JSON%%" not in body
    assert "/calendar/meetings.ics" in body


def test_page_loads_the_json_feed(stub_client):
    body = stub_client.get("/").text
    assert "/api/meetings?days_ahead=" in body


def test_page_ships_committee_data(stub_client):
    body = stub_client.get("/").text
    assert '"system_code": "ssju00"' in body
    assert '"chamber": "house"' in body


def test_page_has_browse_controls(stub_client):
    body = stub_client.get("/").text
    for marker in ('id="agenda"', 'id="tab-upcoming"', 'id="tab-past"', 'id="committee-list"'):
        assert marker in body
