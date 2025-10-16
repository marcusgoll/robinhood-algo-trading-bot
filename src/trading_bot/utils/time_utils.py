"""
Time utilities for trading hours validation.

Provides timezone-aware trading hours checking with DST support.

Constitution v1.0.0 - §Code_Quality: Type hints required
"""

from datetime import datetime
from typing import Optional

import pytz


def is_trading_hours(timezone: str, current_time: datetime | None = None) -> bool:
    """
    Check if current time is within trading hours (7am-10am) for given timezone.

    Args:
        timezone: Timezone string (e.g., "America/New_York")
        current_time: Optional datetime to check (defaults to now if not provided)

    Returns:
        True if within trading hours, False otherwise

    From: spec.md FR-002 (Trading Hours Enforcement)
    Pattern: Simple timezone conversion with bounds checking
    Task: T018 [GREEN→T004,T005,T006]
    Task: T045-T051 [Added current_time parameter for testability]
    """
    tz = pytz.timezone(timezone)
    current = current_time if current_time is not None else datetime.now(tz)

    # Ensure current has timezone info
    if current.tzinfo is None:
        current = tz.localize(current)
    else:
        current = current.astimezone(tz)

    # Trading hours: 7:00 AM - 10:00 AM
    start = current.replace(hour=7, minute=0, second=0, microsecond=0)
    end = current.replace(hour=10, minute=0, second=0, microsecond=0)

    return start <= current < end


def get_current_time_in_tz(timezone: str) -> datetime:
    """
    Get current time in specified timezone.

    Args:
        timezone: Timezone string (e.g., "America/New_York")

    Returns:
        Current datetime in specified timezone

    Task: T018 [GREEN→T004,T005,T006]
    """
    tz = pytz.timezone(timezone)
    return datetime.now(tz)


def is_market_open(check_time: datetime | None = None) -> bool:
    """
    Check if US stock market is open at the given time.

    Market hours: Monday-Friday, 9:30 AM - 4:00 PM Eastern Time (ET).
    Handles Daylight Saving Time (DST) transitions automatically using pytz.

    Args:
        check_time: Optional datetime to check (defaults to current time if not provided)

    Returns:
        True if market is open, False otherwise (weekends, outside trading hours)

    Pattern: Timezone-aware checking with DST support via pytz
    Task: T017 [status-dashboard]
    """
    et_tz = pytz.timezone("America/New_York")
    current = check_time if check_time is not None else datetime.now(et_tz)

    # Ensure current has timezone info
    if current.tzinfo is None:
        current = et_tz.localize(current)
    else:
        current = current.astimezone(et_tz)

    # Check if weekday (0=Monday, 4=Friday)
    if current.weekday() > 4:  # 5=Saturday, 6=Sunday
        return False

    # Market hours: 9:30 AM - 4:00 PM ET
    market_open = current.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = current.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open <= current < market_close
