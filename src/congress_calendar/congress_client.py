"""Async HTTP client for Congress.gov API with pagination and retry."""

import asyncio
import logging
from typing import Any

import httpx

from .config import Settings

logger = logging.getLogger("congress-calendar.client")

# api.data.gov signals these in the body, not the status line. They affect every
# request in flight, so they must not be mistaken for one bad record.
RETRYABLE_ERROR_CODES = {"OVER_RATE_LIMIT"}


class CongressApiError(RuntimeError):
    """Congress.gov returned an error envelope instead of data."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}" if code else message)


def _error_payload(response: httpx.Response) -> tuple[str, str] | None:
    """Return an ``{"error": ...}`` envelope as (code, message), or None.

    Congress.gov reports rate limits and bad API keys in the response *body*,
    usually under HTTP 200 — so the status code alone can't tell success from
    failure, and an unchecked body silently parses as zero meetings.
    """
    try:
        data = response.json()
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    error = data.get("error")
    if isinstance(error, dict):
        return str(error.get("code", "")), str(error.get("message", ""))
    if isinstance(error, str):
        return "", error
    return None


def _is_rate_limited(response: httpx.Response, error: tuple[str, str] | None) -> bool:
    if response.status_code == 429:
        return True
    return error is not None and error[0] in RETRYABLE_ERROR_CODES


class CongressClient:
    """Async HTTP client for the Congress.gov API.

    Handles authentication, auto-pagination, and retry on rate limits.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "CongressClient":
        self._client = httpx.AsyncClient(
            base_url=self.settings.congress_api_base_url,
            timeout=self.settings.timeout,
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        if self._client:
            await self._client.aclose()

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        limit: int = 250,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Make an authenticated GET request, retrying while rate limited."""
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        params = dict(params) if params else {}
        params["api_key"] = self.settings.congress_api_key
        params["format"] = "json"
        params["limit"] = limit
        params["offset"] = offset

        error: tuple[str, str] | None = None

        for attempt in range(self.settings.max_retries + 1):
            response = await self._client.get(endpoint, params=params)
            error = _error_payload(response)

            if not _is_rate_limited(response, error):
                break

            if attempt >= self.settings.max_retries:
                raise CongressApiError(
                    "OVER_RATE_LIMIT",
                    f"Rate limit exceeded on {endpoint} after {attempt + 1} attempts",
                )

            retry_after = response.headers.get("Retry-After")
            delay = self.settings.retry_base_delay * (2**attempt)
            if retry_after is not None:
                try:
                    delay = float(retry_after)
                except (ValueError, TypeError):
                    pass
            logger.warning(
                "Rate limited on %s (attempt %d/%d), retrying in %.1fs",
                endpoint,
                attempt + 1,
                self.settings.max_retries + 1,
                delay,
            )
            await asyncio.sleep(delay)

        response.raise_for_status()

        if error is not None:
            raise CongressApiError(error[0], f"{error[1]} (endpoint {endpoint})")

        return response.json()

    async def _get_all_list(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Auto-paginate to fetch all committee meeting list items."""
        params = dict(params) if params else {}
        all_items: list[dict[str, Any]] = []
        offset = 0
        batch_size = 250

        while True:
            data = await self.get(endpoint, params=params, limit=batch_size, offset=offset)
            items = data.get("committeeMeetings", [])
            all_items.extend(items)

            pagination = data.get("pagination", {})
            total = pagination.get("count", 0)

            if offset + batch_size >= total or not items:
                break
            offset += batch_size

        logger.info("Listed %d meetings from %s", len(all_items), endpoint)
        return all_items

    async def _fetch_detail(self, url: str) -> dict[str, Any] | None:
        """Fetch a single meeting's detail, returning None on a per-record failure."""
        # The list item `url` is a full URL with api_key — we need the path only
        # Example: https://api.congress.gov/v3/committee-meeting/119/senate/338002?format=json
        # Extract the path after /v3
        try:
            path = url.split("/v3", 1)[1].split("?")[0]
        except (IndexError, AttributeError):
            logger.warning("Unparseable meeting detail URL: %r", url)
            return None
        try:
            data = await self.get(path)
        except CongressApiError:
            # Rate limits and bad keys break every request, not just this one.
            # Surfacing them beats quietly serving a shrunken calendar.
            raise
        except Exception as exc:
            logger.warning("Failed to fetch detail for %s: %s", path, exc)
            return None

        detail = data.get("committeeMeeting")
        if not isinstance(detail, dict):
            logger.warning("No committeeMeeting payload for %s", path)
            return None
        return detail

    async def _enrich_meetings(
        self,
        items: list[dict[str, Any]],
        max_concurrent: int = 25,
    ) -> list[dict[str, Any]]:
        """Fetch details for each meeting concurrently and return enriched dicts."""
        enriched: list[dict[str, Any]] = []
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(items), max_concurrent):
            batch = items[i : i + max_concurrent]
            tasks = [self._fetch_detail(item.get("url", "")) for item in batch]
            results = await asyncio.gather(*tasks)
            for detail in results:
                if detail and isinstance(detail, dict):
                    enriched.append(detail)

        dropped = len(items) - len(enriched)
        if dropped:
            logger.warning(
                "Dropped %d of %d listed meetings that had no usable detail record",
                dropped,
                len(items),
            )
        return enriched

    async def fetch_meetings(
        self,
        congress: int,
        chamber: str | None,
        from_date: str,
        to_date: str,
    ) -> list[dict[str, Any]]:
        """Fetch committee meetings with full details.

        Note: Congress.gov applies `fromDateTime`/`toDateTime` to each record's
        `updateDate`, *not* to the date the meeting is held. Callers wanting a
        real date window must filter the returned meetings themselves.
        """
        params = {
            "fromDateTime": f"{from_date}T00:00:00Z",
            "toDateTime": f"{to_date}T23:59:59Z",
        }

        if chamber:
            items = await self._get_all_list(
                f"/committee-meeting/{congress}/{chamber}",
                params=params,
            )
        else:
            # Fetch both chambers concurrently
            house, senate = await asyncio.gather(
                self._get_all_list(f"/committee-meeting/{congress}/house", params=params),
                self._get_all_list(f"/committee-meeting/{congress}/senate", params=params),
            )
            logger.info("Listed %d house and %d senate meetings", len(house), len(senate))
            items = house + senate

        return await self._enrich_meetings(items)
