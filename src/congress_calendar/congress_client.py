"""Async HTTP client for Congress.gov API with pagination and retry."""

import asyncio
import logging
from typing import Any

import httpx

from .config import Settings

logger = logging.getLogger("congress-calendar.client")


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
        """Make an authenticated GET request with retry on 429."""
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        params = dict(params) if params else {}
        params["api_key"] = self.settings.congress_api_key
        params["format"] = "json"
        params["limit"] = limit
        params["offset"] = offset

        for attempt in range(self.settings.max_retries + 1):
            response = await self._client.get(endpoint, params=params)

            if response.status_code != 429:
                break

            if attempt < self.settings.max_retries:
                retry_after = response.headers.get("Retry-After")
                if retry_after is not None:
                    try:
                        delay = float(retry_after)
                    except (ValueError, TypeError):
                        delay = self.settings.retry_base_delay * (2**attempt)
                else:
                    delay = self.settings.retry_base_delay * (2**attempt)
                logger.warning(
                    "Rate limited on %s (attempt %d/%d), retrying in %.1fs",
                    endpoint,
                    attempt + 1,
                    self.settings.max_retries + 1,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                raise RuntimeError(f"Rate limit exceeded on {endpoint} after {attempt + 1} attempts")

        response.raise_for_status()
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

        return all_items

    async def _fetch_detail(self, url: str) -> dict[str, Any] | None:
        """Fetch a single meeting's detail, returning None on failure."""
        # The list item `url` is a full URL with api_key — we need the path only
        # Example: https://api.congress.gov/v3/committee-meeting/119/senate/338002?format=json
        # Extract the path after /v3
        try:
            path = url.split("/v3", 1)[1].split("?")[0]
        except (IndexError, AttributeError):
            return None
        try:
            data = await self.get(path)
            return data.get("committeeMeeting")
        except Exception:
            logger.warning("Failed to fetch detail for %s", path)
            return None

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
        return enriched

    async def fetch_meetings(
        self,
        congress: int,
        chamber: str | None,
        from_date: str,
        to_date: str,
    ) -> list[dict[str, Any]]:
        """Fetch committee meetings with full details."""
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
            items = house + senate

        return await self._enrich_meetings(items)
