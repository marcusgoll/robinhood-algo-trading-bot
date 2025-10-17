"""
Shared test fixtures for momentum detection unit tests.

Provides mock objects, sample data, and reusable fixtures for testing
momentum detection components in isolation.
"""

import pytest


@pytest.fixture
def sample_symbols():
    """Return list of sample stock symbols for testing."""
    return ["AAPL", "GOOGL", "TSLA"]
