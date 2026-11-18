"""Fixtures of the UI tests with Playwright: the address that each page opens relative to."""

import os

import pytest


@pytest.fixture(scope="session")
def base_url():
    """The service under test, read from `BASE_URL` as the API tests read it, instead of the
    `--base-url` option of pytest-playwright."""
    return os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
