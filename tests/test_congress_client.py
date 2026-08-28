"""Client-level regression tests for silently-dropped meetings.

Congress.gov reports rate limits and bad keys in the response *body* under
HTTP 200. Before these tests, such a body parsed as "zero meetings" — so a
throttled Senate list call produced a House-only calendar with no error.
"""

import httpx
import pytest

from congress_calendar.config import Settings
from congress_calendar.congress_client import CongressApiError, CongressClient
from congress_calendar.meeting_query import parse_meetings

RATE_LIMIT_BODY = {
    "error": {"code": "OVER_RATE_LIMIT", "message": "You have exceeded your rate limit."}
}
BAD_KEY_BODY = {"error": {"code": "API_KEY_INVALID", "message": "Invalid API key."}}


def _settings(**kwargs):
    return Settings(congress_api_key="test-key", retry_base_delay=0, **kwargs)


def _client(handler, **kwargs):
    settings = _settings(**kwargs)
    client = CongressClient(settings)
    client._client = httpx.AsyncClient(
        base_url=settings.congress_api_base_url,
        transport=httpx.MockTransport(handler),
    )
    return client


def _list_body(chamber, count):
    return {
        "committeeMeetings": [
            {"url": f"https://api.congress.gov/v3/committee-meeting/119/{chamber}/{i}?format=json"}
            for i in range(count)
        ],
        "pagination": {"count": count},
    }


def _detail_body(event_id, chamber):
    return {
        "committeeMeeting": {
            "eventId": str(event_id),
            "date": "2026-09-01T14:00:00Z",
            "title": "Hearing",
            "chamber": chamber.title(),
            "committees": [],
        }
    }


def _is_list_call(request):
    # /v3/committee-meeting/{congress}/{chamber} — details carry an extra segment
    return request.url.path.rstrip("/").count("/") == 4


@pytest.mark.asyncio
async def test_rate_limited_list_call_raises_instead_of_emptying_a_chamber():
    """A throttled Senate list must not silently yield a House-only calendar."""

    def handler(request):
        if "/senate" in request.url.path:
            return httpx.Response(200, json=RATE_LIMIT_BODY)
        if _is_list_call(request):
            return httpx.Response(200, json=_list_body("house", 1))
        return httpx.Response(200, json=_detail_body(1, "house"))

    client = _client(handler, max_retries=1)
    with pytest.raises(CongressApiError) as exc:
        await client.fetch_meetings(119, None, "2026-07-29", "2026-09-27")
    assert exc.value.code == "OVER_RATE_LIMIT"
    await client._client.aclose()


@pytest.mark.asyncio
async def test_rate_limited_detail_call_raises_instead_of_dropping_meetings():
    """Throttled detail lookups must not quietly shrink the calendar."""

    def handler(request):
        if _is_list_call(request):
            return httpx.Response(200, json=_list_body("senate", 3))
        return httpx.Response(200, json=RATE_LIMIT_BODY)

    client = _client(handler, max_retries=1)
    with pytest.raises(CongressApiError):
        await client.fetch_meetings(119, "senate", "2026-07-29", "2026-09-27")
    await client._client.aclose()


@pytest.mark.asyncio
async def test_error_body_under_http_200_is_not_treated_as_data():
    """A non-retryable error envelope must raise, not parse as zero meetings."""

    def handler(request):
        return httpx.Response(200, json=BAD_KEY_BODY)

    client = _client(handler)
    with pytest.raises(CongressApiError) as exc:
        await client.fetch_meetings(119, "senate", "2026-07-29", "2026-09-27")
    assert exc.value.code == "API_KEY_INVALID"
    await client._client.aclose()


@pytest.mark.asyncio
async def test_rate_limit_is_retried_then_succeeds():
    """The backoff path must fire for body-reported limits, not just HTTP 429."""
    calls = {"n": 0}

    def handler(request):
        if _is_list_call(request):
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(200, json=RATE_LIMIT_BODY)
            return httpx.Response(200, json=_list_body("senate", 1))
        return httpx.Response(200, json=_detail_body(0, "senate"))

    client = _client(handler, max_retries=2)
    meetings = await client.fetch_meetings(119, "senate", "2026-07-29", "2026-09-27")
    assert calls["n"] == 2
    assert len(meetings) == 1
    await client._client.aclose()


@pytest.mark.asyncio
async def test_missing_detail_payload_drops_only_that_meeting():
    """A single unusable record is skipped; the rest of the calendar survives."""

    def handler(request):
        if _is_list_call(request):
            return httpx.Response(200, json=_list_body("senate", 3))
        if request.url.path.endswith("/1"):
            return httpx.Response(200, json={})
        event_id = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, json=_detail_body(event_id, "senate"))

    client = _client(handler)
    meetings = await client.fetch_meetings(119, "senate", "2026-07-29", "2026-09-27")
    assert len(meetings) == 2
    await client._client.aclose()


def test_parse_meetings_survives_a_null_date():
    """A null `date` used to raise TypeError and 500 the whole request."""
    raw = [
        {"eventId": "1", "date": None, "chamber": "Senate"},
        {
            "eventId": "2",
            "date": "2026-09-01T14:00:00Z",
            "title": "Hearing",
            "chamber": "Senate",
            "committees": [],
        },
    ]
    meetings = parse_meetings(raw, 119)
    assert [m.event_id for m in meetings] == ["2"]
