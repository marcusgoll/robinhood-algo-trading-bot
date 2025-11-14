"""
Deprecated Robinhood auth shim.

This module now simply re-exports the Alpaca authentication service so that
legacy imports (`from trading_bot.auth.robinhood_auth import RobinhoodAuth`)
continue to function while the codebase migrates to Alpaca-first naming.
"""

from __future__ import annotations

import warnings

from trading_bot.auth.alpaca_auth import AlpacaAuth, AuthenticationError

warnings.warn(
    "trading_bot.auth.robinhood_auth is deprecated. "
    "Import trading_bot.auth.AlpacaAuth instead.",
    DeprecationWarning,
    stacklevel=2,
)


class RobinhoodAuth(AlpacaAuth):
    """Backward-compatible alias for AlpacaAuth."""


__all__ = ["RobinhoodAuth", "AuthenticationError"]
