"""
Shared test fixtures for momentum detection integration tests.

Provides integration test fixtures with mocked external APIs
(Alpaca, news providers) for end-to-end testing of momentum engine.
"""

import pytest


@pytest.fixture
def mock_market_data():
    """Mock MarketDataService for integration testing."""
    pass  # To be implemented with actual tests
