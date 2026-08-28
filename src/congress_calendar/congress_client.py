"""Async HTTP client for Congress.gov API with pagination and retry."""

import asyncio
import logging
from typing import Any

import httpx

from .cache import DetailCache
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

    def __init__(self, settings: Settings, details: DetailCache | None = None) -> None:
        self.settings = settings
        self.details = details if details is not None else DetailCache()
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

    async def _fetch_detail(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """Return a meeting's detail record, from cache when it hasn't changed."""
        event_id = str(item.get("eventId", ""))
        update_date = str(item.get("updateDate", ""))

        cached = self.details.get(event_id, update_date)
        if cached is not None:
            return cached

        # The list item `url` is a full URL with api_key — we need the path only
        # Example: https://api.congress.gov/v3/committee-meeting/119/senate/338002?format=json
        # Extract the path after /v3
        url = item.get("url", "")
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

        self.details.set(event_id, update_date, detail)
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
            tasks = [self._fetch_detail(item) for item in batch]
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

    async def fetch_meetings(self, congress: int) -> list[dict[str, Any]]:
        """Fetch every committee meeting in a Congress, with full details.

        Deliberately unfiltered. Congress.gov applies `fromDateTime`/
        `toDateTime` to each record's `updateDate` — when the record was last
        edited — and offers no way to filter or sort by the date a meeting is
        actually held. Passing a date window there drops meetings that sit
        inside it but haven't been touched recently, and admits ones held
        months outside it. So enumerate the Congress and let callers apply a
        real date window to the parsed results.

        The listing is cheap (a few hundred records per page) and the detail
        cache means only meetings whose `updateDate` moved since the last
        refresh are actually fetched.
        """
        house, senate = await asyncio.gather(
            self._get_all_list(f"/committee-meeting/{congress}/house"),
            self._get_all_list(f"/committee-meeting/{congress}/senate"),
        )
        logger.info("Listed %d house and %d senate meetings", len(house), len(senate))

        cached_before = len(self.details)
        enriched = await self._enrich_meetings(house + senate)
        logger.info(
            "Enriched %d meetings (%d fetched, %d served from detail cache)",
            len(enriched),
            len(self.details) - cached_before,
            len(enriched) - (len(self.details) - cached_before),
        )
        return enriched
