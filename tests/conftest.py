"""
Root-level test configuration.

Disables the module-level rate limiter for all tests so normal tests are never
blocked by accumulated counts in the in-memory storage.
Tests that specifically want to assert 429 can re-enable the limiter locally.
"""
import os

_TEST_ENV = {
    "ENV": "test",
    "FASTAPI_ENV": "test",
    "DEBUG": "false",
    "FASTAPI_TITLE": "FastAPI Demo",
    "SERVER_IP": "localhost",
    "DATABASE_URL": "sqlite+pysqlite:///:memory:",
    "JWT_KEY": "test-jwt-secret-key-for-pytest-minimum-32chars",
    "SESSIONMIDDLEWARE_SECRET_KEY": "test-session-secret-key-minimum-32chars",
    "BROKER_URL": "memory://",
    "CELERY_RESULT_BACKEND": "cache+memory://",
    "CACHE_SERVER_HOST": "localhost",
    "CACHE_SERVER_PORT": "6379",
}

for key, value in _TEST_ENV.items():
    os.environ[key] = value

import pytest
from app.limiter import limiter


@pytest.fixture(autouse=True)
def disable_rate_limiting(monkeypatch):
    """Patch the module-level limiter to disabled for every test."""
    monkeypatch.setattr(limiter, "enabled", False)
