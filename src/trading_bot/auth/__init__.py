"""
Authentication Module

Alpaca authentication wrapper that provides shared Trading/Data clients.

Enforces Constitution v1.0.0:
- §Security: Credentials from environment only, never logged
- §Audit_Everything: All auth events logged
- §Safety_First: Bot fails to start if auth fails
"""

from trading_bot.auth.alpaca_auth import AlpacaAuth, AuthenticationError

# Backwards compatibility: legacy RobinhoodAuth imports now resolve to AlpacaAuth
RobinhoodAuth = AlpacaAuth

__all__ = ["AlpacaAuth", "AuthenticationError", "RobinhoodAuth"]
