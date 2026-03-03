"""TTL cache for Congress.gov API responses."""

import threading
from typing import Any

from cachetools import TTLCache


class MeetingCache:
    """Thread-safe TTL cache for committee meeting data.

    Caches raw meeting dicts keyed by (congress, chamber, from_date, to_date).
    Committee filtering is applied post-cache.
    """

    def __init__(self, ttl_seconds: int = 1800, maxsize: int = 64) -> None:
        self._cache: TTLCache[tuple[int, str | None, str, str], list[dict[str, Any]]] = TTLCache(
            maxsize=maxsize, ttl=ttl_seconds
        )
        self._lock = threading.Lock()

    def get(
        self, congress: int, chamber: str | None, from_date: str, to_date: str
    ) -> list[dict[str, Any]] | None:
        key = (congress, chamber, from_date, to_date)
        with self._lock:
            return self._cache.get(key)

    def set(
        self,
        congress: int,
        chamber: str | None,
        from_date: str,
        to_date: str,
        meetings: list[dict[str, Any]],
    ) -> None:
        key = (congress, chamber, from_date, to_date)
        with self._lock:
            self._cache[key] = meetings
