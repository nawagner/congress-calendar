"""Caches and locks for Congress.gov API responses."""

import asyncio
import threading
from typing import Any

from cachetools import LRUCache, TTLCache


class MeetingCache:
    """Thread-safe TTL cache for a Congress's full enriched meeting set.

    Keyed by congress alone. Chamber, date window, and committee filters are
    all applied post-cache, so every combination of them shares one fetch —
    and changing a filter never costs a round trip to Congress.gov.

    Alongside the expiring entry it keeps a last-good copy that never expires.
    A refresh that fails or comes back visibly incomplete can then fall back to
    the previous answer instead of serving an error or a short calendar; the
    data it holds is at most one TTL stale, which beats both alternatives.
    """

    def __init__(
        self, ttl_seconds: int = 1800, maxsize: int = 8, retry_seconds: int = 300
    ) -> None:
        self._cache: TTLCache[int, list[dict[str, Any]]] = TTLCache(
            maxsize=maxsize, ttl=ttl_seconds
        )
        self._last_good: dict[int, list[dict[str, Any]]] = {}
        # Marks a congress whose refresh just failed, so we serve the last good
        # copy for a while instead of retrying an upstream that is still down.
        self._failed: TTLCache[int, bool] = TTLCache(maxsize=maxsize, ttl=retry_seconds)
        self._lock = threading.Lock()

    def get(self, congress: int) -> list[dict[str, Any]] | None:
        with self._lock:
            return self._cache.get(congress)

    def set(self, congress: int, meetings: list[dict[str, Any]]) -> None:
        with self._lock:
            self._cache[congress] = meetings
            self._last_good[congress] = meetings
            self._failed.pop(congress, None)

    def last_good(self, congress: int) -> list[dict[str, Any]] | None:
        """The most recent successful fetch, however old."""
        with self._lock:
            return self._last_good.get(congress)

    def mark_failed(self, congress: int) -> None:
        with self._lock:
            self._failed[congress] = True

    def in_retry_backoff(self, congress: int) -> bool:
        with self._lock:
            return congress in self._failed


class DetailCache:
    """Thread-safe cache of individual meeting detail records.

    Keyed by (eventId, updateDate). A detail record can't change without
    Congress.gov bumping its `updateDate`, so a hit is always current and
    entries never need to expire — which is what makes refetching the whole
    Congress every half hour affordable: only records whose `updateDate`
    moved are actually requested.

    That guarantee rests entirely on both parts of the key being present. A
    record with no `updateDate` would otherwise cache under a fixed key and
    never refresh again, so those are refused here and refetched every time.
    """

    def __init__(self, maxsize: int = 20000) -> None:
        self._cache: LRUCache[tuple[str, str], dict[str, Any]] = LRUCache(maxsize=maxsize)
        self._lock = threading.Lock()

    def get(self, event_id: str, update_date: str) -> dict[str, Any] | None:
        if not (event_id and update_date):
            return None
        with self._lock:
            return self._cache.get((event_id, update_date))

    def set(self, event_id: str, update_date: str, detail: dict[str, Any]) -> None:
        if not (event_id and update_date):
            return
        with self._lock:
            self._cache[(event_id, update_date)] = detail

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


class CongressLocks:
    """One fetch lock per congress.

    A cold fetch enumerates a whole Congress, so two at once would double an
    expensive job and can breach the hourly API budget — but a single shared
    lock would also let a fetch for one congress stall requests for every
    other. The registry is only ever keyed by congresses the app accepts, so
    it stays small.
    """

    def __init__(self) -> None:
        self._locks: dict[int, asyncio.Lock] = {}

    def get(self, congress: int) -> asyncio.Lock:
        # setdefault has no await in it, so it is atomic on the event loop.
        return self._locks.setdefault(congress, asyncio.Lock())
