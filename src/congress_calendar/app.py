"""FastAPI application factory."""

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from .cache import CongressLocks, DetailCache, MeetingCache
from .config import Settings
from .meeting_query import fetch_into_cache
from .middleware import RequestLoggingMiddleware
from .routes import calendar_feed, health, landing, meetings_api

logger = logging.getLogger("congress-calendar.app")


class _JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "client_ip_hash", "method", "path", "query",
            "user_agent", "referer", "status_code", "duration_ms",
        ):
            if hasattr(record, key):
                entry[key] = getattr(record, key)
        return json.dumps(entry)


def _configure_logging() -> None:
    """Set up structured JSON logging for the whole congress-calendar tree."""
    handler = logging.StreamHandler()
    handler.setFormatter(_JSONFormatter())

    # The client and query loggers report dropped records, rate limits, and
    # cache stats. Without a handler here those only reach stderr at WARNING,
    # so the counts that make a shrinking calendar visible would be lost.
    base_logger = logging.getLogger("congress-calendar")
    base_logger.handlers.clear()
    base_logger.setLevel(logging.INFO)
    base_logger.addHandler(handler)
    base_logger.propagate = False

    access_logger = logging.getLogger("congress-calendar.access")
    access_logger.handlers.clear()
    access_logger.setLevel(logging.INFO)
    access_logger.addHandler(handler)
    access_logger.propagate = False


async def _warm_cache(app: FastAPI) -> None:
    """Fill the meeting cache on boot so no visitor pays for the cold fetch."""
    settings: Settings = app.state.settings
    started = time.perf_counter()
    try:
        meetings = await fetch_into_cache(
            settings,
            app.state.cache,
            app.state.details,
            app.state.locks,
            settings.default_congress,
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        # A failed warm-up costs latency, not correctness — the first request
        # will fetch for itself. Never take the app down over it.
        logger.exception("Cache warm-up failed; the first request will fetch instead")
        return
    logger.info(
        "Warmed cache with %d meetings in %.1fs",
        len(meetings),
        time.perf_counter() - started,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down application state."""
    _configure_logging()
    settings = Settings()
    app.state.settings = settings
    app.state.cache = MeetingCache(ttl_seconds=settings.cache_ttl_minutes * 60)
    # Outlives the TTL cache on purpose: detail records are immutable for a
    # given updateDate, so each half-hourly refresh only fetches what changed.
    app.state.details = DetailCache()
    # Guards the cold fetch so a request arriving mid-warm-up waits for it
    # rather than starting a second one — per congress, so one cold load
    # can't stall requests for another.
    app.state.locks = CongressLocks()

    warm_task: asyncio.Task[None] | None = None
    if settings.warm_cache_on_startup:
        warm_task = asyncio.create_task(_warm_cache(app))

    try:
        yield
    finally:
        if warm_task is not None and not warm_task.done():
            warm_task.cancel()
            with suppress(asyncio.CancelledError):
                await warm_task


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Congress Calendar",
        description="Subscribable iCal feed for Congress committee meetings",
        lifespan=lifespan,
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(health.router)
    app.include_router(calendar_feed.router)
    app.include_router(meetings_api.router)
    app.include_router(landing.router)
    return app
