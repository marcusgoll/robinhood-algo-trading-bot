"""
Telegram notification system for trading bot alerts.

Provides real-time mobile notifications for:
- Position entries and exits
- Risk alerts and circuit breakers
- System errors
- Performance summaries

Constitution alignment:
- §Non_Blocking: Notification failures never prevent trade execution
- §Graceful_Degradation: Missing credentials disable notifications, not trading
- §Security: Credentials via environment variables only
"""

from typing import Optional


class ConfigurationError(Exception):
    """Raised when Telegram configuration is invalid."""
    pass


# Lazy imports to avoid circular dependencies
def get_notification_service():
    """Factory function for NotificationService (lazy import)."""
    from .notification_service import NotificationService
    return NotificationService()


__all__ = [
    'ConfigurationError',
    'get_notification_service',
]
