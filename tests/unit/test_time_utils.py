"""
Unit tests for time utilities module.

Tests trading hours validation with timezone awareness,
including DST transitions.

Constitution v1.0.0 - §Testing_Requirements: TDD with RED-GREEN-REFACTOR
"""

import pytest
from datetime import datetime
from unittest.mock import patch
import pytz


class TestTradingHoursValidation:
    """Test suite for trading hours validation with timezone support."""

    @patch('src.trading_bot.utils.time_utils.datetime')
    def test_is_trading_hours_within_hours_est(self, mock_datetime):
        """
        Test that trading hours check returns True during valid hours.

        GIVEN: Current time is 8:00 AM EST (within 7am-10am trading window)
        WHEN: is_trading_hours("America/New_York") is called
        THEN: Returns True

        From: spec.md FR-002 (Trading Hours Enforcement)
        Task: T004 [RED]
        """
        # Mock current time to 8:00 AM EST on a weekday
        est = pytz.timezone("America/New_York")
        mock_time = est.localize(datetime(2025, 10, 8, 8, 0, 0))  # Wednesday 8am
        mock_datetime.now.return_value = mock_time

        # Import after patching
        from src.trading_bot.utils.time_utils import is_trading_hours

        # Should return True (within 7am-10am)
        result = is_trading_hours("America/New_York")
        assert result is True, "8:00 AM EST should be within trading hours"

    @patch('src.trading_bot.utils.time_utils.datetime')
    def test_is_trading_hours_outside_hours_est(self, mock_datetime):
        """
        Test that trading hours check returns False outside valid hours.

        GIVEN: Current time is 6:59 AM EST (before 7am)
        WHEN: is_trading_hours("America/New_York") is called
        THEN: Returns False

        From: spec.md FR-002, Scenario 2
        Task: T005 [RED]
        """
        # Mock current time to 6:59 AM EST on a weekday
        est = pytz.timezone("America/New_York")
        mock_time = est.localize(datetime(2025, 10, 8, 6, 59, 0))  # Wednesday 6:59am
        mock_datetime.now.return_value = mock_time

        from src.trading_bot.utils.time_utils import is_trading_hours

        # Should return False (before 7am)
        result = is_trading_hours("America/New_York")
        assert result is False, "6:59 AM EST should be outside trading hours"

    @patch('src.trading_bot.utils.time_utils.datetime')
    def test_is_trading_hours_handles_dst_transition(self, mock_datetime):
        """
        Test that trading hours check correctly handles DST transitions.

        GIVEN: Mock time during DST transition (spring forward)
        WHEN: is_trading_hours("America/New_York") is called
        THEN: Returns correct result accounting for DST offset

        From: plan.md [RISK MITIGATION] DST edge cases
        Task: T006 [RED]
        """
        # Test during DST (spring - EDT, UTC-4)
        est = pytz.timezone("America/New_York")
        mock_time = est.localize(datetime(2025, 6, 15, 8, 0, 0))  # June (DST active)
        mock_datetime.now.return_value = mock_time

        from src.trading_bot.utils.time_utils import is_trading_hours

        # Should return True regardless of DST
        result = is_trading_hours("America/New_York")
        assert result is True, "8:00 AM EDT should be within trading hours during DST"

        # Test during standard time (winter - EST, UTC-5)
        mock_time = est.localize(datetime(2025, 12, 15, 8, 0, 0))  # December (no DST)
        mock_datetime.now.return_value = mock_time

        result = is_trading_hours("America/New_York")
        assert result is True, "8:00 AM EST should be within trading hours during standard time"
