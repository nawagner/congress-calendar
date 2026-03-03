"""FastAPI application factory."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from .cache import MeetingCache
from .config import Settings
from .routes import calendar_feed, health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down application state."""
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
    app.include_router(health.router)
    app.include_router(calendar_feed.router)
    return app
