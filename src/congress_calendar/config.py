"""Configuration management for Congress Calendar service."""

from datetime import date

from pydantic_settings import BaseSettings


def congress_on(day: date) -> int:
    """The Congress sitting on `day`.

    Since the 20th Amendment each Congress convenes on January 3 of an odd year
    (the 119th on 2025-01-03, the 120th on 2027-01-03), so the number follows
    from the date and never needs bumping by hand.
    """
    year = day.year
    if year % 2 == 1 and (day.month, day.day) < (1, 3):
        year -= 1
    return (year - 1789) // 2 + 1


class Settings(BaseSettings):
    """Service configuration loaded from environment variables."""

    congress_api_key: str
    congress_api_base_url: str = "https://api.congress.gov/v3"
    # Unset, the default follows the calendar (see `congress_on`); set, it pins
    # the default view to one Congress.
    default_congress: int | None = None
    # Each distinct congress costs a full enumeration, so only a few may be
    # requested. Without this, `congress` is a public query param that can be
    # walked to force ~200 cold loads. The current and previous Congress are
    # always allowed; these are extra (see `meeting_query.supported_congresses`).
    supported_congresses: set[int] | None = None
    cache_ttl_minutes: int = 30
    days_ahead: int = 30
    days_behind: int = 30
    timeout: float = 30.0
    # Cold start enriches every meeting in the Congress; 25 took ~98s in
    # production. Congress.gov caps on requests per hour, not concurrency.
    detail_concurrency: int = 75
    # Fill the cache on boot so the first visitor doesn't pay for it.
    warm_cache_on_startup: bool = True
    max_retries: int = 3
    retry_base_delay: float = 1.0
    # A Retry-After longer than this means the hourly budget is gone; fail fast
    # so callers fall back to cached data rather than hanging for half an hour.
    max_retry_delay: float = 30.0

    base_url: str = ""

    model_config = {"env_file": ".env"}
