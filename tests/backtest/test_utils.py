"""
Tests for backtest utility functions.

Tests date validation, trading day calculations, and market calendar functions.
"""

import pytest
from datetime import datetime, timezone, timedelta

from src.trading_bot.backtest.utils import (
    is_market_day,
    trading_days_between,
    validate_date_range,
)


class TestIsMarketDay:
    """Test is_market_day() function."""

    def test_weekday_is_trading_day(self):
        """Regular weekdays should be trading days."""
        # Tuesday, Jan 16, 2024 (no holiday)
        date = datetime(2024, 1, 16)
        assert is_market_day(date) is True

    def test_saturday_is_not_trading_day(self):
        """Saturdays should not be trading days."""
        # Saturday, Jan 20, 2024
        date = datetime(2024, 1, 20)
        assert is_market_day(date) is False

    def test_sunday_is_not_trading_day(self):
        """Sundays should not be trading days."""
        # Sunday, Jan 21, 2024
        date = datetime(2024, 1, 21)
        assert is_market_day(date) is False

    def test_mlk_day_is_not_trading_day(self):
        """MLK Day (Monday) should not be a trading day."""
        # Monday, Jan 15, 2024 (MLK Day)
        date = datetime(2024, 1, 15)
        assert is_market_day(date) is False

    def test_independence_day_is_not_trading_day(self):
        """Independence Day should not be a trading day."""
        # Thursday, July 4, 2024
        date = datetime(2024, 7, 4)
        assert is_market_day(date) is False

    def test_christmas_is_not_trading_day(self):
        """Christmas should not be a trading day."""
        # Wednesday, Dec 25, 2024
        date = datetime(2024, 12, 25)
        assert is_market_day(date) is False

    def test_day_after_holiday_is_trading_day(self):
        """Day after holiday should be a trading day (if weekday)."""
        # Tuesday, Jan 16, 2024 (day after MLK Day)
        date = datetime(2024, 1, 16)
        assert is_market_day(date) is True

    def test_timezone_aware_datetime(self):
        """Should handle timezone-aware datetimes."""
        date = datetime(2024, 1, 16, tzinfo=timezone.utc)
        assert is_market_day(date) is True

    def test_2025_holidays(self):
        """Should recognize 2025 holidays."""
        # Monday, Jan 20, 2025 (MLK Day)
        date = datetime(2025, 1, 20)
        assert is_market_day(date) is False


class TestTradingDaysBetween:
    """Test trading_days_between() function."""

    def test_same_day_trading_day(self):
        """Same day range should return 1 if trading day."""
        date = datetime(2024, 1, 16)  # Tuesday
        assert trading_days_between(date, date) == 1

    def test_same_day_weekend(self):
        """Same day range should return 0 if weekend."""
        date = datetime(2024, 1, 20)  # Saturday
        assert trading_days_between(date, date) == 0

    def test_same_day_holiday(self):
        """Same day range should return 0 if holiday."""
        date = datetime(2024, 1, 15)  # MLK Day
        assert trading_days_between(date, date) == 0

    def test_full_week_no_holidays(self):
        """Full week (Mon-Fri) should return 5 trading days."""
        # Week of Jan 22-26, 2024 (no holidays)
        start = datetime(2024, 1, 22)  # Monday
        end = datetime(2024, 1, 26)    # Friday
        assert trading_days_between(start, end) == 5

    def test_week_with_holiday(self):
        """Week with MLK Day should return 4 trading days."""
        # Week of Jan 15-19, 2024 (MLK Day on Monday)
        start = datetime(2024, 1, 15)  # Monday (holiday)
        end = datetime(2024, 1, 19)    # Friday
        assert trading_days_between(start, end) == 4

    def test_includes_weekend(self):
        """Range including weekend should only count weekdays."""
        # Monday to Sunday
        start = datetime(2024, 1, 22)  # Monday
        end = datetime(2024, 1, 28)    # Sunday
        assert trading_days_between(start, end) == 5  # Mon-Fri only

    def test_two_weeks(self):
        """Two full weeks should return 10 trading days."""
        # Two weeks: Jan 22 - Feb 2, 2024 (no holidays)
        start = datetime(2024, 1, 22)  # Monday
        end = datetime(2024, 2, 2)     # Friday
        assert trading_days_between(start, end) == 10

    def test_month_with_holidays(self):
        """Full month with holidays should count correctly."""
        # July 2024 has July 4th (Thursday)
        # 23 total days (July 1-31), expect ~21-22 trading days
        start = datetime(2024, 7, 1)   # Monday
        end = datetime(2024, 7, 31)    # Wednesday
        count = trading_days_between(start, end)
        # July 2024: 4 weekends (8 days) + 1 holiday (July 4) = 9 non-trading days
        # 31 - 9 = 22 trading days
        assert count == 22

    def test_start_after_end_raises_error(self):
        """Start date after end date should raise ValueError."""
        start = datetime(2024, 1, 20)
        end = datetime(2024, 1, 10)
        with pytest.raises(ValueError, match="start_date.*must be <= end_date"):
            trading_days_between(start, end)

    def test_timezone_aware_dates(self):
        """Should handle timezone-aware datetimes."""
        start = datetime(2024, 1, 22, tzinfo=timezone.utc)
        end = datetime(2024, 1, 26, tzinfo=timezone.utc)
        assert trading_days_between(start, end) == 5


class TestValidateDateRange:
    """Test validate_date_range() function."""

    def test_valid_utc_range(self):
        """Valid UTC date range should not raise error."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 12, 31, tzinfo=timezone.utc)
        # Should not raise
        validate_date_range(start, end)

    def test_start_equals_end_raises_error(self):
        """Start date equal to end date should raise ValueError."""
        date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="must be <"):
            validate_date_range(date, date)

    def test_start_after_end_raises_error(self):
        """Start date after end date should raise ValueError."""
        start = datetime(2024, 12, 31, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="chronological order"):
            validate_date_range(start, end)

    def test_naive_start_date_raises_error(self):
        """Timezone-naive start date should raise ValueError."""
        start = datetime(2024, 1, 1)  # No timezone
        end = datetime(2024, 12, 31, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="timezone-naive"):
            validate_date_range(start, end)

    def test_naive_end_date_raises_error(self):
        """Timezone-naive end date should raise ValueError."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 12, 31)  # No timezone
        with pytest.raises(ValueError, match="timezone-naive"):
            validate_date_range(start, end)

    def test_both_naive_raises_error(self):
        """Both naive dates should raise ValueError."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        with pytest.raises(ValueError, match="timezone-naive"):
            validate_date_range(start, end)

    def test_one_day_range(self):
        """One day range should be valid."""
        start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 23, 59, 59, tzinfo=timezone.utc)
        # Should not raise
        validate_date_range(start, end)

    def test_different_timezones(self):
        """Different timezones should work (both timezone-aware)."""
        # UTC and EST (UTC-5)
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 12, 31, tzinfo=timezone(timedelta(hours=-5)))
        # Should not raise (both are timezone-aware)
        validate_date_range(start, end)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_leap_year_february_29(self):
        """Leap year Feb 29 should be handled correctly."""
        # Feb 29, 2024 (Thursday, leap year)
        date = datetime(2024, 2, 29)
        assert is_market_day(date) is True

    def test_year_boundary(self):
        """Year boundary should count correctly."""
        # Dec 26, 2024 (Thursday) to Jan 3, 2025 (Friday)
        # Excludes Dec 25 (Christmas), Jan 1 (New Year)
        start = datetime(2024, 12, 26)
        end = datetime(2025, 1, 3)
        # Dec: 26, 27, 30, 31 (4 days)
        # Jan: 2, 3 (2 days)
        # Total: 6 trading days
        count = trading_days_between(start, end)
        assert count == 6

    def test_all_holidays_in_range(self):
        """Range with multiple holidays should exclude all."""
        # Week of Nov 25-29, 2024 (Thanksgiving week)
        # Nov 28 is Thanksgiving (Thursday)
        start = datetime(2024, 11, 25)  # Monday
        end = datetime(2024, 11, 29)    # Friday
        count = trading_days_between(start, end)
        # Mon, Tue, Wed, Fri (4 days) - excludes Thanksgiving Thursday
        assert count == 4

    def test_very_short_range(self):
        """One-hour range should work."""
        start = datetime(2024, 1, 16, 9, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 16, 10, 0, tzinfo=timezone.utc)
        validate_date_range(start, end)
        assert trading_days_between(start, end) == 1

    def test_microsecond_difference(self):
        """Microsecond difference should be valid range."""
        start = datetime(2024, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 0, 0, 0, 1, tzinfo=timezone.utc)
        validate_date_range(start, end)
