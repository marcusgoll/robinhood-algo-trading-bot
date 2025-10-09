"""
Account Data Service

Fetches and caches account data from Robinhood API.

Constitution v1.0.0:
- §Security: Never log account numbers, mask sensitive values
- §Audit_Everything: All API calls and cache events logged
- §Risk_Management: Day trade count enforcement
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
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


@dataclass
class AccountBalance:
    """
    Account balance breakdown.

    T012: Data model for account balance information.
    """
    cash: Decimal
    equity: Decimal
    buying_power: Decimal
    last_updated: datetime


@dataclass
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
    pass


class AccountData:
    """Account data service with TTL-based caching."""

    def __init__(self, auth: Any):
        """
        Initialize AccountData service.

        Args:
            auth: RobinhoodAuth instance for authenticated API calls
        """
        self.auth = auth
        self._cache: dict[str, CacheEntry] = {}
        logger.info("AccountData service initialized")

    def _is_cache_valid(self, key: str) -> bool:
        """
        Check if cache entry is valid (not expired).

        T021: Cache validation with TTL check.

        Args:
            key: Cache key to check

        Returns:
            True if cache entry exists and is not expired, False otherwise
        """
        if key not in self._cache:
            return False

        entry = self._cache[key]
        age_seconds = (datetime.utcnow() - entry.cached_at).total_seconds()
        is_valid = age_seconds < entry.ttl_seconds

        if is_valid:
            logger.debug(f"Cache hit: {key} (age: {age_seconds:.1f}s, TTL: {entry.ttl_seconds}s)")
        else:
            logger.debug(f"Cache stale: {key} (age: {age_seconds:.1f}s, TTL: {entry.ttl_seconds}s)")

        return is_valid

    def _update_cache(self, key: str, value: Any, ttl_seconds: int) -> None:
        """
        Update cache with new value and timestamp.

        T021: Cache update with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds
        """
        self._cache[key] = CacheEntry(
            value=value,
            cached_at=datetime.utcnow(),
            ttl_seconds=ttl_seconds
        )
        logger.debug(f"Cache updated: {key} (TTL: {ttl_seconds}s)")

    def invalidate_cache(self, cache_type: str | None = None) -> None:
        """
        Invalidate cache (all or specific type).

        T021: Manual cache invalidation.

        Args:
            cache_type: Specific cache key to invalidate, or None to clear all
        """
        if cache_type is None:
            self._cache.clear()
            logger.info("All caches invalidated")
        elif cache_type in self._cache:
            del self._cache[cache_type]
            logger.info(f"Cache invalidated: {cache_type}")

    def get_buying_power(self, use_cache: bool = True) -> float:
        """
        Fetch current buying power with optional caching.

        T022: Public API for buying power with cache support.

        Args:
            use_cache: If True, use cached value if valid. If False, always fetch fresh.

        Returns:
            Current buying power as float
        """
        cache_key = 'buying_power'

        # Check cache if enabled
        if use_cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key].value

        # Cache miss - fetch from API
        logger.info(f"Fetching {cache_key} from API")
        buying_power = self._fetch_buying_power()

        # Update cache (60s TTL for volatile data)
        self._update_cache(cache_key, buying_power, ttl_seconds=60)

        return buying_power

    def _fetch_buying_power(self) -> float:
        """
        Fetch buying power from robin-stocks API with retry.

        T022/T036: API integration for buying power with exponential backoff.

        Returns:
            Buying power as float

        Raises:
            AccountDataError: If API response is invalid
        """
        def _fetch() -> float:
            import robin_stocks.robinhood as rh

            profile = rh.account.load_account_profile()

            # Validate response
            if not profile or 'buying_power' not in profile:
                raise AccountDataError("Invalid API response: missing buying_power")

            try:
                return float(profile['buying_power'])
            except (ValueError, TypeError) as e:
                raise AccountDataError(f"Invalid buying_power value: {e}") from e

        # Apply retry with exponential backoff (1s, 2s, 4s)
        return self._retry_with_backoff(_fetch, max_attempts=3, base_delay=1.0)

    def get_positions(self, use_cache: bool = True) -> list[Position]:
        """
        Fetch all positions with P&L calculations.

        T033: Public API for positions with cache support.

        Args:
            use_cache: If True, use cached value if valid. If False, always fetch fresh.

        Returns:
            List of Position objects with P&L
        """
        cache_key = 'positions'

        if use_cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key].value

        logger.info(f"Fetching {cache_key} from API")
        positions = self._fetch_positions()

        # Update cache (60s TTL for volatile data)
        self._update_cache(cache_key, positions, ttl_seconds=60)

        return positions

    def _fetch_positions(self) -> list[Position]:
        """
        Fetch positions from robin-stocks API with retry.

        T033/T036: API integration for positions with exponential backoff.

        Returns:
            List of Position objects

        Raises:
            AccountDataError: If API response is invalid
        """
        def _fetch() -> list[Position]:
            import robin_stocks.robinhood as rh

            holdings = rh.account.build_holdings()

            positions = []
            for symbol, data in holdings.items():
                try:
                    position = Position(
                        symbol=symbol,
                        quantity=int(float(data['quantity'])),
                        average_buy_price=Decimal(data['average_buy_price']),
                        current_price=Decimal(data['price']),
                        last_updated=datetime.utcnow()
                    )
                    positions.append(position)
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(f"Skipping invalid position {symbol}: {e}")
                    continue

            return positions

        return self._retry_with_backoff(_fetch, max_attempts=3, base_delay=1.0)

    def get_account_balance(self, use_cache: bool = True) -> AccountBalance:
        """
        Fetch account balance breakdown.

        T034: Public API for account balance with cache support.

        Args:
            use_cache: If True, use cached value if valid. If False, always fetch fresh.

        Returns:
            AccountBalance object
        """
        cache_key = 'account_balance'

        if use_cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key].value

        logger.info(f"Fetching {cache_key} from API")
        balance = self._fetch_account_balance()

        # Update cache (60s TTL for volatile data)
        self._update_cache(cache_key, balance, ttl_seconds=60)

        return balance

    def _fetch_account_balance(self) -> AccountBalance:
        """
        Fetch account balance from robin-stocks API with retry.

        T034/T036: API integration for balance with exponential backoff.

        Returns:
            AccountBalance object

        Raises:
            AccountDataError: If API response is invalid
        """
        def _fetch() -> AccountBalance:
            import robin_stocks.robinhood as rh

            profile = rh.account.load_account_profile()

            # Validate response
            if not profile:
                raise AccountDataError("Invalid API response: empty profile")

            required_fields = ['cash', 'equity', 'buying_power']
            for field in required_fields:
                if field not in profile:
                    raise AccountDataError(f"Invalid API response: missing {field}")

            try:
                return AccountBalance(
                    cash=Decimal(profile['cash']),
                    equity=Decimal(profile['equity']),
                    buying_power=Decimal(profile['buying_power']),
                    last_updated=datetime.utcnow()
                )
            except (ValueError, TypeError) as e:
                raise AccountDataError(f"Invalid balance values: {e}") from e

        return self._retry_with_backoff(_fetch, max_attempts=3, base_delay=1.0)

    def get_day_trade_count(self, use_cache: bool = True) -> int:
        """
        Fetch day trade count (PDT tracking).

        T035: Public API for day trade count with cache support.

        Args:
            use_cache: If True, use cached value if valid. If False, always fetch fresh.

        Returns:
            Day trade count as int (0-3)
        """
        cache_key = 'day_trade_count'

        if use_cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key].value

        logger.info(f"Fetching {cache_key} from API")
        count = self._fetch_day_trade_count()

        # Update cache (300s TTL = 5 minutes - stable data)
        self._update_cache(cache_key, count, ttl_seconds=300)

        return count

    def _fetch_day_trade_count(self) -> int:
        """
        Fetch day trade count from robin-stocks API with retry.

        T035/T036: API integration for day trade count with exponential backoff.

        Returns:
            Day trade count as int

        Raises:
            AccountDataError: If API response is invalid
        """
        def _fetch() -> int:
            import robin_stocks.robinhood as rh

            profile = rh.account.load_account_profile()

            # Validate response
            if not profile or 'day_trade_count' not in profile:
                raise AccountDataError("Invalid API response: missing day_trade_count")

            try:
                return int(profile['day_trade_count'])
            except (ValueError, TypeError) as e:
                raise AccountDataError(f"Invalid day_trade_count value: {e}") from e

        return self._retry_with_backoff(_fetch, max_attempts=3, base_delay=1.0)

    def _retry_with_backoff(
        self,
        func: Callable[[], T],
        max_attempts: int = 3,
        base_delay: float = 1.0
    ) -> T:
        """
        Retry a function with exponential backoff.

        T036: Reusable retry logic for network resilience.

        Args:
            func: Function to retry (takes no args, returns T)
            max_attempts: Maximum number of attempts (default: 3)
            base_delay: Base delay in seconds (default: 1.0)

        Returns:
            Result from successful function call

        Raises:
            Last exception if all attempts fail

        Pattern: 1s, 2s, 4s delays between retries
        """
        last_exception = None

        for attempt in range(max_attempts):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_attempts} attempts failed")

        # Re-raise the last exception
        raise last_exception  # type: ignore
