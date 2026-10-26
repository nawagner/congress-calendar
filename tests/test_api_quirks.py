"""Regression tests for Congress.gov data quirks found auditing the 119th Congress."""

import httpx
import pytest

from congress_calendar.config import Settings
from congress_calendar.congress_client import CongressApiError, CongressClient
from congress_calendar.ical_builder import build_calendar
from congress_calendar.models import CommitteeMeeting


def _meeting(committees):
    return CommitteeMeeting.from_api_response(
        {
            "eventId": "118679",
            "date": "2025-11-19T15:00:00Z",
            "title": "Hearing",
            "chamber": "House",
            "committees": committees,
        },
        119,
    )


def test_committee_without_a_name_is_named_from_its_code():
    """Congress.gov sent event 118679 with only {"systemCode": "hsha00"}."""
    meeting = _meeting([{"systemCode": "hsha00"}])
    assert meeting.committees[0].name == "House Administration"
    ical = build_calendar([meeting]).to_ical().decode()
    assert "Unknown Committee" not in ical


def test_nameless_subcommittee_is_named_after_its_parent():
    meeting = _meeting([{"systemCode": "hspw07"}])
    assert meeting.committees[0].name == "House Transportation and Infrastructure Subcommittee"


def test_names_from_the_api_are_kept():
    meeting = _meeting([{"name": "House Education and Workforce", "systemCode": "hsed00"}])
    assert meeting.committees[0].name == "House Education and Workforce"


def test_unrecognised_code_without_a_name_stays_unknown():
    meeting = _meeting([{"systemCode": "zzzz00"}])
    assert meeting.committees[0].name == "Unknown Committee"


def test_null_committee_fields_do_not_drop_the_meeting():
    """A JSON null used to fail validation and skip the whole meeting."""
    meeting = _meeting([{"name": None, "systemCode": "hsha00"}])
    assert meeting.committees[0].name == "House Administration"
    meeting = _meeting([{"name": "Judiciary", "systemCode": None}])
    assert meeting.committees[0].system_code == ""


def _client(handler, **kwargs):
    settings = Settings(congress_api_key="test-key", retry_base_delay=0, **kwargs)
    client = CongressClient(settings)
    client._client = httpx.AsyncClient(
        base_url=settings.congress_api_base_url,
        transport=httpx.MockTransport(handler),
    )
    return client


def _is_list_call(request):
    return request.url.path.rstrip("/").count("/") == 4


@pytest.mark.asyncio
async def test_a_meeting_listed_twice_is_fetched_and_served_once():
    """The Senate list returned event 337761 twice, with identical entries."""
    entry = {
        "eventId": "337761",
        "updateDate": "2025-12-08T23:53:20Z",
        "url": "https://api.congress.gov/v3/committee-meeting/119/senate/337761?format=json",
    }
    details = {"n": 0}

    def handler(request):
        if _is_list_call(request):
            items = [entry, dict(entry)] if "/senate" in request.url.path else []
            return httpx.Response(
                200, json={"committeeMeetings": items, "pagination": {"count": len(items)}}
            )
        details["n"] += 1
        return httpx.Response(
            200,
            json={
                "committeeMeeting": {
                    "eventId": "337761",
                    "date": "2025-12-09T19:00:00Z",
                    "title": "Hearing",
                    "chamber": "Senate",
                    "committees": [],
                }
            },
        )

    client = _client(handler)
    meetings = await client.fetch_meetings(119)
    assert len(meetings) == 1
    assert details["n"] == 1
    await client._client.aclose()


@pytest.mark.asyncio
async def test_a_long_retry_after_fails_fast_instead_of_sleeping(monkeypatch):
    """A spent hourly budget came back with Retry-After: 1765.

    Honouring it held the cache lock for ~30 minutes per attempt, so every
    request hung instead of falling back to the last good calendar.
    """

    async def no_sleeping(delay):
        raise AssertionError(f"slept {delay}s instead of failing fast")

    monkeypatch.setattr("congress_calendar.congress_client.asyncio.sleep", no_sleeping)
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(429, headers={"Retry-After": "1765"})

    client = _client(handler, max_retries=3)
    with pytest.raises(CongressApiError) as exc:
        await client.get("/committee-meeting/119/senate")
    assert exc.value.code == "OVER_RATE_LIMIT"
    assert calls["n"] == 1
    await client._client.aclose()


@pytest.mark.asyncio
async def test_a_short_retry_after_is_still_honoured():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"committeeMeetings": []})

    client = _client(handler, max_retries=3)
    await client.get("/committee-meeting/119/senate")
    assert calls["n"] == 2
    await client._client.aclose()


@pytest.mark.asyncio
async def test_long_own_backoff_without_retry_after_is_not_cut_short(monkeypatch):
    """The cap is for upstream's Retry-After, not the client's own backoff."""
    slept = []

    async def record(delay):
        slept.append(delay)

    monkeypatch.setattr("congress_calendar.congress_client.asyncio.sleep", record)
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429)
        return httpx.Response(200, json={"committeeMeetings": []})

    client = CongressClient(
        Settings(congress_api_key="test-key", retry_base_delay=60, max_retries=1)
    )
    client._client = httpx.AsyncClient(
        base_url=client.settings.congress_api_base_url,
        transport=httpx.MockTransport(handler),
    )
    await client.get("/committee-meeting/119/senate")
    assert slept == [60]
    await client._client.aclose()
