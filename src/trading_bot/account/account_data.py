"""
Account Data Service

Fetches and caches account data from Robinhood API.

Constitution v1.0.0:
- §Security: Never log account numbers, mask sensitive values
- §Audit_Everything: All API calls and cache events logged
- §Risk_Management: Day trade count enforcement
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


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
        self._cache: Dict[str, CacheEntry] = {}
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

    def invalidate_cache(self, cache_type: Optional[str] = None) -> None:
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
        Fetch buying power from robin-stocks API.

        T022: API integration for buying power.

        Returns:
            Buying power as float

        Raises:
            AccountDataError: If API response is invalid
        """
        import robin_stocks.robinhood as rh

        profile = rh.account.load_account_profile()

        # Validate response
        if not profile or 'buying_power' not in profile:
            raise AccountDataError("Invalid API response: missing buying_power")

        try:
            return float(profile['buying_power'])
        except (ValueError, TypeError) as e:
            raise AccountDataError(f"Invalid buying_power value: {e}")
