"""
Time utilities for trading hours validation.

Provides timezone-aware trading hours checking with DST support.

Constitution v1.0.0 - §Code_Quality: Type hints required
"""

from typing import Optional
from datetime import datetime

import pytz


def is_trading_hours(timezone: str, current_time: Optional[datetime] = None) -> bool:
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
