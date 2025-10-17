"""
Shared pytest fixtures for momentum detection integration tests.

Provides integration-level mocks and test infrastructure:
- Mock Alpaca API client
- Test database fixtures
- Integration test configuration
- End-to-end test data
"""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import List, Dict, Any


# Fixtures will be added as needed during integration testing
# Following TDD approach: implement after unit tests pass
