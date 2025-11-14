"""
Unit tests for is_market_open() in time_utils module (TDD RED Phase).

Tests market hours detection with timezone awareness, DST transitions, and weekends.

Constitution v1.0.0 - §Testing_Requirements: TDD with RED-GREEN-REFACTOR
Feature: status-dashboard
Task: T004 [RED] - Write failing test for is_market_open()

Expected to FAIL: is_market_open() implementation already exists and passes
"""

import pytest
from datetime import datetime
from unittest.mock import patch
import pytz

from src.trading_bot.utils.time_utils import is_market_open


class TestMarketHoursDetection:
    """Test suite for is_market_open() market hours detection."""

    def test_market_open_during_trading_hours(self) -> None:
        """
        Test that market is detected as OPEN during trading hours.

        GIVEN: Current time is 10:00 AM ET on Wednesday (market hours: 9:30-16:00 ET)
        WHEN: is_market_open() is called
        THEN: Returns True

        From: tasks.md T004 - Market open (Mon-Fri 9:30 AM - 4:00 PM ET)
        Pattern: tests/unit/test_time_utils.py
        """
        # GIVEN: Wednesday 10:00 AM ET (market hours)
        et_tz = pytz.timezone("America/New_York")
        check_time = et_tz.localize(datetime(2025, 10, 8, 10, 0, 0))  # Wednesday 10am

        # WHEN: Check if market is open
        result = is_market_open(check_time)

        # THEN: Market should be open
        assert result is True, "10:00 AM ET on Wednesday should be market open"

    def test_market_open_at_exact_open_time(self) -> None:
        """
        Test that market is OPEN at exact market open time (9:30 AM).

        GIVEN: Current time is 9:30:00 AM ET on Friday (exact market open)
        WHEN: is_market_open() is called
        THEN: Returns True (inclusive boundary)

        From: tasks.md T004 - Market open at 9:30 AM ET
        """
        # GIVEN: Friday 9:30:00 AM ET (exact market open)
        et_tz = pytz.timezone("America/New_York")
        check_time = et_tz.localize(datetime(2025, 10, 10, 9, 30, 0))  # Friday 9:30am

        # WHEN: Check if market is open
        result = is_market_open(check_time)

        # THEN: Market should be open (inclusive boundary)
        assert result is True, "9:30 AM ET should be market open (inclusive)"

    def test_market_closed_before_open(self) -> None:
        """
        Test that market is CLOSED before 9:30 AM.

        GIVEN: Current time is 9:29 AM ET on Monday (before market open)
        WHEN: is_market_open() is called
        THEN: Returns False

        From: tasks.md T004 - Market closed (before 9:30 AM)
        """
        # GIVEN: Monday 9:29 AM ET (before market open)
        et_tz = pytz.timezone("America/New_York")
        check_time = et_tz.localize(datetime(2025, 10, 6, 9, 29, 0))  # Monday 9:29am

        # WHEN: Check if market is open
        result = is_market_open(check_time)

        # THEN: Market should be closed
        assert result is False, "9:29 AM ET should be before market open"

    def test_market_closed_after_hours(self) -> None:
        """
        Test that market is CLOSED after 4:00 PM.

        GIVEN: Current time is 4:00 PM ET on Tuesday (at/after market close)
        WHEN: is_market_open() is called
        THEN: Returns False

        From: tasks.md T004 - Market closed (after 4:00 PM)
        """
        # GIVEN: Tuesday 4:00 PM ET (market close time - exclusive)
        et_tz = pytz.timezone("America/New_York")
        check_time = et_tz.localize(datetime(2025, 10, 7, 16, 0, 0))  # Tuesday 4:00pm

        # WHEN: Check if market is open
        result = is_market_open(check_time)

        # THEN: Market should be closed (exclusive boundary)
        assert result is False, "4:00 PM ET should be market close (exclusive)"

    def test_market_closed_on_saturday(self) -> None:
        """
        Test that market is CLOSED on Saturday.

        GIVEN: Current time is 10:00 AM ET on Saturday
        WHEN: is_market_open() is called
        THEN: Returns False

        From: tasks.md T004 - Market closed (weekends)
        """
        # GIVEN: Saturday 10:00 AM ET (weekend)
        et_tz = pytz.timezone("America/New_York")
        check_time = et_tz.localize(datetime(2025, 10, 11, 10, 0, 0))  # Saturday 10am

        # WHEN: Check if market is open
        result = is_market_open(check_time)

        # THEN: Market should be closed (weekend)
        assert result is False, "Saturday should be market closed"

    def test_market_closed_on_sunday(self) -> None:
        """
        Test that market is CLOSED on Sunday.

        GIVEN: Current time is 14:00 (2:00 PM) ET on Sunday
        WHEN: is_market_open() is called
        THEN: Returns False

        From: tasks.md T004 - Market closed (weekends)
        """
        # GIVEN: Sunday 2:00 PM ET (weekend)
        et_tz = pytz.timezone("America/New_York")
        check_time = et_tz.localize(datetime(2025, 10, 12, 14, 0, 0))  # Sunday 2pm

        # WHEN: Check if market is open
        result = is_market_open(check_time)

        # THEN: Market should be closed (weekend)
        assert result is False, "Sunday should be market closed"

    def test_market_hours_during_dst_spring(self) -> None:
        """
        Test that market hours detection handles DST spring forward correctly.

        GIVEN: Current time is 10:00 AM EDT in June (DST active - UTC-4)
        WHEN: is_market_open() is called
        THEN: Returns True (market hours same local time regardless of DST)

        From: tasks.md T004 - DST transitions
        Pattern: tests/unit/test_time_utils.py DST handling
        """
        # GIVEN: June 15, 2025 at 10:00 AM EDT (DST active)
        et_tz = pytz.timezone("America/New_York")
        check_time = et_tz.localize(datetime(2025, 6, 15, 10, 0, 0))  # June 10am EDT

        # WHEN: Check if market is open
        result = is_market_open(check_time)

        # THEN: Market should be open (10am EDT is within 9:30-16:00)
        assert result is True, "10:00 AM EDT (DST) should be market open"

    def test_market_hours_during_standard_time(self) -> None:
        """
        Test that market hours detection handles standard time (non-DST) correctly.

        GIVEN: Current time is 10:00 AM EST in December (DST inactive - UTC-5)
        WHEN: is_market_open() is called
        THEN: Returns True (market hours same local time regardless of DST)

        From: tasks.md T004 - DST transitions
        """
        # GIVEN: December 15, 2025 at 10:00 AM EST (no DST)
        et_tz = pytz.timezone("America/New_York")
        check_time = et_tz.localize(datetime(2025, 12, 15, 10, 0, 0))  # December 10am EST

        # WHEN: Check if market is open
        result = is_market_open(check_time)

        # THEN: Market should be open (10am EST is within 9:30-16:00)
        assert result is True, "10:00 AM EST (standard time) should be market open"

    def test_market_closed_just_before_open_different_timezones(self) -> None:
        """
        Test market closed detection works with UTC timezone input.

        GIVEN: Current time is 9:29 AM ET (14:29 UTC) on Thursday
        WHEN: is_market_open() called with UTC datetime
        THEN: Returns False (before market open after timezone conversion)

        From: tasks.md T004 - Timezone handling
        """
        # GIVEN: 9:29 AM ET = 14:29 UTC (assuming EST, UTC-5)
        utc_tz = pytz.timezone("UTC")
        # December 11, 2025 (standard time, UTC-5)
        check_time = utc_tz.localize(datetime(2025, 12, 11, 14, 29, 0))  # 9:29 AM ET

        # WHEN: Check if market is open
        result = is_market_open(check_time)

        # THEN: Market should be closed (before 9:30 AM ET)
        assert result is False, "9:29 AM ET (14:29 UTC) should be before market open"

    def test_market_open_uses_current_time_if_none_provided(self) -> None:
        """
        Test that is_market_open() uses current time when check_time is None.

        GIVEN: No check_time parameter provided
        WHEN: is_market_open() is called
        THEN: Function executes without error (uses datetime.now())

        From: tasks.md T004 - Default behavior
        Note: This test verifies the function can be called without parameters
        """
        # GIVEN: No check_time parameter

        # WHEN: Call is_market_open() with no arguments
        try:
            result = is_market_open()

            # THEN: Function should execute and return a boolean
            assert isinstance(result, bool), "is_market_open() should return a boolean"
        except Exception as e:
            pytest.fail(f"is_market_open() should accept no arguments and use current time: {e}")
