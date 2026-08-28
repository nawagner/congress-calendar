"""Caches for Congress.gov API responses."""

import threading
from typing import Any

from cachetools import LRUCache, TTLCache


class MeetingCache:
    """Thread-safe TTL cache for a Congress's full enriched meeting set.

    Keyed by congress alone. Chamber, date window, and committee filters are
    all applied post-cache, so every combination of them shares one fetch —
    and changing a filter never costs a round trip to Congress.gov.
    """

    def __init__(self, ttl_seconds: int = 1800, maxsize: int = 8) -> None:
        self._cache: TTLCache[int, list[dict[str, Any]]] = TTLCache(
            maxsize=maxsize, ttl=ttl_seconds
        )
        self._lock = threading.Lock()

    def get(self, congress: int) -> list[dict[str, Any]] | None:
        with self._lock:
            return self._cache.get(congress)

    def set(self, congress: int, meetings: list[dict[str, Any]]) -> None:
        with self._lock:
            self._cache[congress] = meetings


class DetailCache:
    """Thread-safe cache of individual meeting detail records.

    Keyed by (eventId, updateDate). A detail record can't change without
    Congress.gov bumping its `updateDate`, so a hit is always current and
    entries never need to expire — which is what makes refetching the whole
    Congress every half hour affordable: only records whose `updateDate`
    moved are actually requested.
    """

    def __init__(self, maxsize: int = 20000) -> None:
        self._cache: LRUCache[tuple[str, str], dict[str, Any]] = LRUCache(maxsize=maxsize)
        self._lock = threading.Lock()

    def get(self, event_id: str, update_date: str) -> dict[str, Any] | None:
        with self._lock:
            return self._cache.get((event_id, update_date))

    def set(self, event_id: str, update_date: str, detail: dict[str, Any]) -> None:
        if not event_id:
            return
        with self._lock:
            self._cache[(event_id, update_date)] = detail

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)
