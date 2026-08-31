"""Configuration management for Congress Calendar service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration loaded from environment variables."""

    congress_api_key: str
    congress_api_base_url: str = "https://api.congress.gov/v3"
    default_congress: int = 119
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

    base_url: str = ""

    model_config = {"env_file": ".env"}
