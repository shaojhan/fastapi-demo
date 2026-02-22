"""
Root-level test configuration.

Disables the module-level rate limiter for all tests so normal tests are never
blocked by accumulated counts in the in-memory storage.
Tests that specifically want to assert 429 can re-enable the limiter locally.
"""
import pytest
from app.limiter import limiter


@pytest.fixture(autouse=True)
def disable_rate_limiting(monkeypatch):
    """Patch the module-level limiter to disabled for every test."""
    monkeypatch.setattr(limiter, "enabled", False)
