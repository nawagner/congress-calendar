"""FastAPI application factory."""

import json
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from .cache import MeetingCache
from .config import Settings
from .middleware import RequestLoggingMiddleware
from .routes import calendar_feed, health, landing


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
    """Set up structured JSON logging for the access logger."""
    handler = logging.StreamHandler()
    handler.setFormatter(_JSONFormatter())

    access_logger = logging.getLogger("congress-calendar.access")
    access_logger.setLevel(logging.INFO)
    access_logger.addHandler(handler)
    access_logger.propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down application state."""
    _configure_logging()
    settings = Settings()
    app.state.settings = settings
    app.state.cache = MeetingCache(ttl_seconds=settings.cache_ttl_minutes * 60)
    yield


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
    app.include_router(landing.router)
    return app
