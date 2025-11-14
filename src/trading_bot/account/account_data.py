"""
Account Data Service

Fetches and caches account data from the Alpaca Trading API.

Constitution v1.0.0:
- §Security: Never log account numbers, mask sensitive values
- §Audit_Everything: All API calls and cache events logged
- §Risk_Management: Day trade count enforcement
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, TYPE_CHECKING, TypeVar

from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from trading_bot.auth.alpaca_auth import AlpacaAuth

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _safe_decimal(value: Any, *, default: str = "0") -> Decimal:
    """Convert Alpaca string/float values into Decimal."""
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Failed to convert %s to Decimal (%s), using default", value, exc)
        return Decimal(default)


@dataclass(slots=True)
class Position:
    """
    Equity position with P&L calculation.

    T011: Data model for stock positions with automatic P&L computation.
    """

    symbol: str
    quantity: int
    average_buy_price: Decimal
    current_price: Decimal
    last_updated: datetime

    @property
    def cost_basis(self) -> Decimal:
        """Calculate cost basis (quantity × average_buy_price)."""
        return Decimal(self.quantity) * self.average_buy_price

    @property
    def current_value(self) -> Decimal:
        """Calculate current value (quantity × current_price)."""
        return Decimal(self.quantity) * self.current_price

    @property
    def profit_loss(self) -> Decimal:
        """Calculate profit/loss (current_value - cost_basis)."""
        return self.current_value - self.cost_basis

    @property
    def profit_loss_pct(self) -> Decimal:
        """Calculate profit/loss percentage ((P&L / cost_basis) × 100)."""
        if self.cost_basis == 0:
            return Decimal("0")
        return (self.profit_loss / self.cost_basis) * 100


@dataclass(slots=True)
class AccountBalance:
    """
    Account balance breakdown.

    T012: Data model for account balance information.
    """

    cash: Decimal
    equity: Decimal
    buying_power: Decimal
    last_updated: datetime


@dataclass(slots=True)
class CacheEntry:
    """
    Cache entry with TTL.

    T013: Data model for TTL-based cache storage.
    """

    value: Any
    cached_at: datetime
    ttl_seconds: int


class AccountDataError(Exception):
    """Custom exception for account data errors."""


class AccountData:
    """Account data service with TTL-based caching (Alpaca-backed)."""

    def __init__(self, auth: Any | None = None):
        """
        Initialize AccountData service.

        Args:
            auth: AlpacaAuth instance (optional). If omitted, AccountData will
                  create its own AlpacaAuth based on environment variables.
        """
        self.auth = auth
        self._owned_auth: AlpacaAuth | None = None
        self._trading_client: TradingClient | None = None
        self._cache: dict[str, CacheEntry] = {}
        logger.info("AccountData service initialized (provider=Alpaca)")

    # ------------------------------------------------------------------ #
    # Cache helpers
    # ------------------------------------------------------------------ #
    def _is_cache_valid(self, key: str) -> bool:
        """Return True when cache entry exists and is not expired."""
        entry = self._cache.get(key)
        if not entry:
            return False

        age_seconds = (datetime.now(UTC) - entry.cached_at).total_seconds()
        if age_seconds < entry.ttl_seconds:
            logger.debug("Cache hit: %s (age=%.1fs, TTL=%ss)", key, age_seconds, entry.ttl_seconds)
            return True

        logger.debug("Cache stale: %s (age=%.1fs > TTL=%ss)", key, age_seconds, entry.ttl_seconds)
        return False

    def _update_cache(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Store cache entry."""
        self._cache[key] = CacheEntry(value=value, cached_at=datetime.now(UTC), ttl_seconds=ttl_seconds)

    def invalidate_cache(self, cache_type: str | None = None) -> None:
        """Invalidate cache (all or specific type)."""
        if cache_type is None:
            self._cache.clear()
            logger.info("All account data caches invalidated")
            return

        if cache_type in self._cache:
            del self._cache[cache_type]
            logger.info("Cache invalidated: %s", cache_type)

    # ------------------------------------------------------------------ #
    # Public APIs
    # ------------------------------------------------------------------ #
    def get_buying_power(self, use_cache: bool = True) -> float:
        """Return current buying power."""
        cache_key = "buying_power"
        if use_cache and self._is_cache_valid(cache_key):
            return float(self._cache[cache_key].value)

        value = self._fetch_buying_power()
        self._update_cache(cache_key, value, ttl_seconds=30)
        return value

    def get_positions(self, use_cache: bool = True) -> list[Position]:
        """Return open positions."""
        cache_key = "positions"
        if use_cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key].value

        value = self._fetch_positions()
        self._update_cache(cache_key, value, ttl_seconds=30)
        return value

    def get_account_balance(self, use_cache: bool = True) -> AccountBalance:
        """Return account balance summary."""
        cache_key = "account_balance"
        if use_cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key].value

        value = self._fetch_account_balance()
        self._update_cache(cache_key, value, ttl_seconds=30)
        return value

    def get_day_trade_count(self, use_cache: bool = True) -> int:
        """Return pattern day trade count."""
        cache_key = "day_trade_count"
        if use_cache and self._is_cache_valid(cache_key):
            return int(self._cache[cache_key].value)

        value = self._fetch_day_trade_count()
        self._update_cache(cache_key, value, ttl_seconds=300)
        return value

    # ------------------------------------------------------------------ #
    # Fetch implementations
    # ------------------------------------------------------------------ #
    def _ensure_trading_client(self) -> TradingClient:
        """Ensure a TradingClient is available."""
        if self._trading_client:
            return self._trading_client

        if self.auth and hasattr(self.auth, "get_trading_client"):
            self._trading_client = self.auth.get_trading_client()
            return self._trading_client

        from trading_bot.auth import AlpacaAuth  # Local import to avoid cycles

        self._owned_auth = AlpacaAuth(None)
        self._owned_auth.login()
        self._trading_client = self._owned_auth.get_trading_client()
        return self._trading_client

    def _fetch_buying_power(self) -> float:
        """Fetch buying power via Alpaca account endpoint."""

        def _fetch() -> float:
            client = self._ensure_trading_client()
            account = client.get_account()
            buying_power = getattr(account, "buying_power", None)
            if buying_power is None:
                raise AccountDataError("Alpaca response missing buying_power")
            return float(buying_power)

        return self._retry_with_backoff(_fetch)

    def _fetch_positions(self) -> list[Position]:
        """Fetch open positions via Alpaca trading API."""

        def _fetch() -> list[Position]:
            client = self._ensure_trading_client()
            alpaca_positions = client.get_all_positions()
            now = datetime.now(UTC)
            positions: list[Position] = []

            for raw_position in alpaca_positions:
                try:
                    quantity_decimal = _safe_decimal(getattr(raw_position, "qty", "0"))
                    avg_price = _safe_decimal(getattr(raw_position, "avg_entry_price", "0"))
                    current_price = _safe_decimal(
                        getattr(raw_position, "current_price", None)
                        or getattr(raw_position, "lastday_price", None)
                        or "0"
                    )

                    position = Position(
                        symbol=getattr(raw_position, "symbol", "N/A"),
                        quantity=int(quantity_decimal),
                        average_buy_price=avg_price,
                        current_price=current_price,
                        last_updated=now,
                    )
                    positions.append(position)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("Skipping invalid Alpaca position %s: %s", raw_position, exc)
                    continue

            return positions

        return self._retry_with_backoff(_fetch)

    def _fetch_account_balance(self) -> AccountBalance:
        """Fetch account summary from Alpaca account endpoint."""

        def _fetch() -> AccountBalance:
            client = self._ensure_trading_client()
            account = client.get_account()
            return AccountBalance(
                cash=_safe_decimal(getattr(account, "cash", "0")),
                equity=_safe_decimal(getattr(account, "equity", "0")),
                buying_power=_safe_decimal(getattr(account, "buying_power", "0")),
                last_updated=datetime.now(UTC),
            )

        return self._retry_with_backoff(_fetch)

    def _fetch_day_trade_count(self) -> int:
        """Fetch PDT day trade count."""

        def _fetch() -> int:
            client = self._ensure_trading_client()
            account = client.get_account()
            count = getattr(account, "daytrade_count", None)
            if count is None:
                logger.debug("daytrade_count missing from Alpaca account payload, defaulting to 0")
                return 0
            return int(count)

        return self._retry_with_backoff(_fetch)

    # ------------------------------------------------------------------ #
    # Retry helper
    # ------------------------------------------------------------------ #
    def _retry_with_backoff(
        self,
        func: Callable[[], T],
        max_attempts: int = 3,
        base_delay: float = 1.0,
    ) -> T:
        """
        Retry a function with exponential backoff.

        Pattern: 1s, 2s, 4s delays between retries.
        """
        last_exception: Exception | None = None

        for attempt in range(max_attempts):
            try:
                return func()
            except (APIError, AccountDataError) as exc:
                last_exception = exc
                if attempt < max_attempts - 1:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        "Attempt %s/%s failed (%s). Retrying in %.1fs...",
                        attempt + 1,
                        max_attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error("All %s attempts failed: %s", max_attempts, exc)
            except Exception as exc:  # pragma: no cover - defensive
                last_exception = exc
                logger.exception("Unexpected error fetching account data")
                break

        if last_exception:
            raise last_exception
        raise RuntimeError("Retry helper failed without exception")  # pragma: no cover
