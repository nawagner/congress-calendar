"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from congress_calendar.app import create_app


@pytest.fixture
def client():
    """FastAPI test client for integration tests."""
    app = create_app()
    with TestClient(app) as c:
        yield c
