"""
Alpaca Authentication Service

Provides authenticated clients for the Alpaca Trading and Data APIs.

Enforces Constitution v1.0.0:
- §Security: Credentials loaded from environment/config, never logged
- §Audit_Everything: Explicit logging around auth lifecycle
- §Safety_First: Validates credentials against Alpaca before allowing trading
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient

try:  # Optional dependency – some deployments only need trading client
    from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
except ImportError:  # pragma: no cover - handled gracefully when data client unavailable
    CryptoHistoricalDataClient = None  # type: ignore[assignment]
    StockHistoricalDataClient = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when Alpaca authentication fails."""


@dataclass(slots=True)
class AlpacaAuthConfig:
    """
    Strongly typed Alpaca credential container.

    Attributes:
        api_key: Alpaca API key ID
        secret_key: Alpaca API secret key
        paper: Whether to use paper trading environment
        base_url: Trading API base URL
        data_base_url: Market data API base URL
    """

    api_key: str
    secret_key: str
    paper: bool = True
    base_url: str = "https://paper-api.alpaca.markets"
    data_base_url: str = "https://data.alpaca.markets"

    @classmethod
    def from_config(cls, config: Any | None = None) -> "AlpacaAuthConfig":
        """
        Create configuration from Config object or environment variables.

        Environment fallbacks:
            - ALPACA_API_KEY / ALPACA_SECRET_KEY
            - ALPACA_BASE_URL
            - ALPACA_DATA_URL
            - ALPACA_PAPER ("true"/"false")
        """
        api_key = getattr(config, "alpaca_api_key", None) or os.getenv("ALPACA_API_KEY")
        secret_key = getattr(config, "alpaca_secret_key", None) or os.getenv("ALPACA_SECRET_KEY")

        if not api_key or not secret_key:
            raise AuthenticationError(
                "Alpaca credentials missing. Set ALPACA_API_KEY and ALPACA_SECRET_KEY "
                "environment variables or provide them via Config."
            )

        if hasattr(config, "paper_trading"):
            paper_default = bool(getattr(config, "paper_trading"))
        else:
            paper_default = True

        paper_env = os.getenv("ALPACA_PAPER")
        if paper_env is not None:
            paper = paper_env.lower() not in {"0", "false", "no"}
        else:
            paper = paper_default

        base_url = (
            getattr(config, "alpaca_base_url", None)
            or os.getenv("ALPACA_BASE_URL")
            or ("https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets")
        )
        data_base_url = (
            getattr(config, "alpaca_data_url", None)
            or os.getenv("ALPACA_DATA_URL")
            or "https://data.alpaca.markets"
        )

        return cls(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper,
            base_url=base_url,
            data_base_url=data_base_url,
        )


class AlpacaAuth:
    """
    Authentication facade for Alpaca APIs.

    Responsibilities:
    - Validate credentials (via lightweight account probe)
    - Provide shared TradingClient and data clients
    - Manage authenticated state for dependent services
    """

    def __init__(self, config: Any | None = None) -> None:
        self.auth_config = (
            config if isinstance(config, AlpacaAuthConfig) else AlpacaAuthConfig.from_config(config)
        )
        self._trading_client: TradingClient | None = None
        self._stock_data_client: StockHistoricalDataClient | None = None
        self._crypto_data_client: CryptoHistoricalDataClient | None = None
        self._account_id: Optional[str] = None
        self._authenticated = False

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def is_authenticated(self) -> bool:
        """Return True if login() succeeded."""
        return self._authenticated

    def login(self) -> bool:
        """
        Initialize trading client and validate credentials by fetching account data.
        """
        logger.info("Authenticating with Alpaca (paper=%s)", self.auth_config.paper)
        try:
            self._trading_client = TradingClient(
                api_key=self.auth_config.api_key,
                secret_key=self.auth_config.secret_key,
                paper=self.auth_config.paper,
                url_override=self.auth_config.base_url,
            )
            account = self._trading_client.get_account()
            self._account_id = getattr(account, "id", None) or getattr(account, "account_number", None)
            self._authenticated = True
            logger.info("Alpaca authentication successful (account_id=%s)", self._account_id)
            return True
        except APIError as exc:
            logger.error("Alpaca API rejected credentials: %s", exc)
            raise AuthenticationError(f"Alpaca authentication failed: {exc}") from exc
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Unexpected Alpaca authentication failure")
            raise AuthenticationError(f"Unexpected Alpaca auth error: {exc}") from exc

    def logout(self) -> None:
        """Release clients (Alpaca uses key-based auth so nothing to revoke)."""
        self._trading_client = None
        self._stock_data_client = None
        self._crypto_data_client = None
        self._authenticated = False
        logger.info("Alpaca clients released")

    def refresh_token(self) -> None:
        """No-op for key-based auth (kept for interface parity)."""
        logger.debug("refresh_token() called - Alpaca uses permanent API keys")

    def get_account_id(self) -> Optional[str]:
        """Return cached account identifier if available."""
        return self._account_id

    def get_trading_client(self) -> TradingClient:
        """Return authenticated TradingClient, logging in if necessary."""
        if not self._trading_client:
            self.login()
        assert self._trading_client is not None  # for type checkers
        return self._trading_client

    def get_stock_data_client(self) -> StockHistoricalDataClient:
        """Return shared StockHistoricalDataClient (lazy init)."""
        if StockHistoricalDataClient is None:
            raise AuthenticationError(
                "alpaca-py data client not installed. Install alpaca-py>=0.43.2 to fetch market data."
            )
        if not self._stock_data_client:
            self._stock_data_client = StockHistoricalDataClient(
                api_key=self.auth_config.api_key,
                secret_key=self.auth_config.secret_key,
                url_override=self.auth_config.data_base_url,
            )
        return self._stock_data_client

    def get_crypto_data_client(self) -> CryptoHistoricalDataClient:
        """Return shared CryptoHistoricalDataClient (lazy init)."""
        if CryptoHistoricalDataClient is None:
            raise AuthenticationError(
                "alpaca-py data client not installed. Install alpaca-py>=0.43.2 to fetch crypto data."
            )
        if not self._crypto_data_client:
            self._crypto_data_client = CryptoHistoricalDataClient(
                api_key=self.auth_config.api_key,
                secret_key=self.auth_config.secret_key,
                url_override=self.auth_config.data_base_url,
            )
        return self._crypto_data_client
