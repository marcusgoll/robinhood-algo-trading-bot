"""
Authentication Module

Robinhood authentication with MFA support, session management, and token refresh.

Enforces Constitution v1.0.0:
- §Security: Credentials from environment only, never logged
- §Audit_Everything: All auth events logged
- §Safety_First: Bot fails to start if auth fails
"""

from trading_bot.auth.robinhood_auth import AuthenticationError, RobinhoodAuth

__all__ = ["RobinhoodAuth", "AuthenticationError"]
