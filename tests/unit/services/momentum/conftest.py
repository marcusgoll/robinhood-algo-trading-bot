"""
Shared pytest fixtures for momentum detection unit tests.

Provides mocks and test data for:
- Catalyst detection (news API responses)
- Pre-market scanning (market data)
- Bull flag pattern detection (OHLCV data)
- Signal ranking and scoring
"""

import pytest
from datetime import datetime, timezone
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock


# Fixtures will be added as needed during test implementation
# Following TDD approach: write minimal failing tests first
