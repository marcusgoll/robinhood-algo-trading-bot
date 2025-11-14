"""
Utility functions for backtesting operations.

Provides date validation, trading day calculations, and market calendar functions
for the backtesting engine. Handles US market trading days (Mon-Fri, excluding
major holidays).

Constitution v1.0.0:
    §Type Safety: Strict type hints with mypy validation
    §Data Quality: Validate UTC timestamps and chronological ordering
"""

from datetime import datetime, timedelta

# US Market Holidays (major holidays that close markets)
# Source: NYSE holiday calendar
# Note: This is a simplified list for 2024-2025. For production use,
# consider using pandas_market_calendars or a similar library.
US_MARKET_HOLIDAYS: set[str] = {
    # 2024 holidays
    "2024-01-01",  # New Year's Day
    "2024-01-15",  # Martin Luther King Jr. Day
    "2024-02-19",  # Presidents Day
    "2024-03-29",  # Good Friday
    "2024-05-27",  # Memorial Day
    "2024-06-19",  # Juneteenth
    "2024-07-04",  # Independence Day
    "2024-09-02",  # Labor Day
    "2024-11-28",  # Thanksgiving Day
    "2024-12-25",  # Christmas Day
    # 2025 holidays
    "2025-01-01",  # New Year's Day
    "2025-01-20",  # Martin Luther King Jr. Day
    "2025-02-17",  # Presidents Day
    "2025-04-18",  # Good Friday
    "2025-05-26",  # Memorial Day
    "2025-06-19",  # Juneteenth
    "2025-07-04",  # Independence Day
    "2025-09-01",  # Labor Day
    "2025-11-27",  # Thanksgiving Day
    "2025-12-25",  # Christmas Day
}


def is_market_day(date: datetime) -> bool:
    """
    Check if a given date is a US market trading day.

    A trading day is defined as:
    - Monday through Friday (weekday 0-4)
    - Not a major US market holiday

    Args:
        date: Date to check (timezone-aware datetime recommended)

    Returns:
        True if date is a trading day, False otherwise

    Examples:
        >>> from datetime import datetime
        >>> is_market_day(datetime(2024, 1, 15))  # MLK Day (Monday)
        False
        >>> is_market_day(datetime(2024, 1, 16))  # Tuesday after MLK Day
        True
        >>> is_market_day(datetime(2024, 1, 20))  # Saturday
        False

    Constitution v1.0.0:
        §Data Quality: Accurate market calendar for backtest realism
    """
    # Check if weekend (Saturday=5, Sunday=6)
    if date.weekday() >= 5:
        return False

    # Check if market holiday
    date_str = date.strftime("%Y-%m-%d")
    if date_str in US_MARKET_HOLIDAYS:
        return False

    return True


def trading_days_between(start_date: datetime, end_date: datetime) -> int:
    """
    Count trading days between two dates (inclusive).

    Counts Monday-Friday dates that are not US market holidays.
    Includes both start_date and end_date if they are trading days.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        Number of trading days in the range [start_date, end_date]

    Raises:
        ValueError: If start_date > end_date (use validate_date_range first)

    Examples:
        >>> from datetime import datetime
        >>> # Week with MLK Day holiday
        >>> trading_days_between(
        ...     datetime(2024, 1, 15),  # Monday (MLK Day)
        ...     datetime(2024, 1, 19)   # Friday
        ... )
        4
        >>> # Same day (if trading day)
        >>> trading_days_between(
        ...     datetime(2024, 1, 16),
        ...     datetime(2024, 1, 16)
        ... )
        1

    Constitution v1.0.0:
        §Data Quality: Accurate trading day counts for performance metrics
    """
    if start_date > end_date:
        raise ValueError(
            f"start_date ({start_date}) must be <= end_date ({end_date}). "
            "Use validate_date_range() to check inputs."
        )

    # Handle same-day case
    if start_date.date() == end_date.date():
        return 1 if is_market_day(start_date) else 0

    # Count trading days by iterating through date range
    count = 0
    current_date = start_date

    while current_date <= end_date:
        if is_market_day(current_date):
            count += 1
        current_date += timedelta(days=1)

    return count


def validate_date_range(start_date: datetime, end_date: datetime) -> None:
    """
    Validate a date range for backtesting.

    Checks:
    1. Chronological order (start_date < end_date)
    2. UTC timezone awareness (recommended for consistency)

    Args:
        start_date: Start date of backtest period
        end_date: End date of backtest period

    Raises:
        ValueError: If dates are not in chronological order
        ValueError: If dates are not timezone-aware (UTC recommended)

    Examples:
        >>> from datetime import datetime, timezone
        >>> # Valid range
        >>> validate_date_range(
        ...     datetime(2024, 1, 1, tzinfo=timezone.utc),
        ...     datetime(2024, 12, 31, tzinfo=timezone.utc)
        ... )
        >>> # Invalid: end before start
        >>> validate_date_range(
        ...     datetime(2024, 12, 31, tzinfo=timezone.utc),
        ...     datetime(2024, 1, 1, tzinfo=timezone.utc)
        ... )
        Traceback (most recent call last):
        ValueError: start_date (2024-12-31...) must be < end_date (2024-01-01...)

    Constitution v1.0.0:
        §Data Quality: Validate inputs to prevent silent failures
        §Type Safety: Enforce UTC timezone for consistency
    """
    # Check timezone awareness FIRST (before comparison)
    if start_date.tzinfo is None:
        raise ValueError(
            "start_date is timezone-naive. Use UTC-aware datetime: "
            "datetime(..., tzinfo=timezone.utc)"
        )

    if end_date.tzinfo is None:
        raise ValueError(
            "end_date is timezone-naive. Use UTC-aware datetime: "
            "datetime(..., tzinfo=timezone.utc)"
        )

    # Check chronological order (after ensuring both are timezone-aware)
    if start_date >= end_date:
        raise ValueError(
            f"start_date ({start_date.isoformat()}) must be < "
            f"end_date ({end_date.isoformat()}). Dates must be in chronological order."
        )
