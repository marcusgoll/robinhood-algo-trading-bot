"""State aggregator service for bot monitoring.

Combines dashboard snapshot, performance metrics, and health data into a unified
state response for LLM consumption.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from decimal import Decimal
import os

from api.app.schemas.state import (
    BotStateResponse,
    BotSummaryResponse,
    HealthStatus,
    PositionResponse,
    AccountStatusResponse,
    PerformanceMetricsResponse,
)


class StateAggregator:
    """
    Aggregates bot state from multiple sources.

    This service combines data from:
    - Dashboard snapshot (positions, account)
    - Performance tracker (metrics, P&L)
    - Health monitor (circuit breaker, API status)
    - Configuration (risk limits, paper trading mode)
    """

    def __init__(self):
        """Initialize state aggregator with default cache TTL."""
        self.cache_ttl = int(os.getenv("BOT_STATE_CACHE_TTL", "60"))
        self._cached_state: Optional[BotStateResponse] = None
        self._cache_timestamp: Optional[datetime] = None

    async def get_bot_state(self, use_cache: bool = True) -> BotStateResponse:
        """
        Get complete bot state.

        Args:
            use_cache: Whether to use cached state (default: True)

        Returns:
            BotStateResponse with all state data

        Example:
            >>> aggregator = StateAggregator()
            >>> state = await aggregator.get_bot_state()
            >>> print(f"Positions: {len(state.positions)}")
            Positions: 2
        """
        # Check cache
        if use_cache and self._is_cache_valid():
            return self._cached_state  # type: ignore

        # Aggregate fresh state
        state = await self._aggregate_state()

        # Update cache
        self._cached_state = state
        self._cache_timestamp = datetime.now(timezone.utc)

        return state

    async def get_health_status(self) -> HealthStatus:
        """
        Get bot health status.

        Returns:
            HealthStatus with circuit breaker, API connection, error count

        Example:
            >>> aggregator = StateAggregator()
            >>> health = await aggregator.get_health_status()
            >>> health.status
            'healthy'
        """
        # TODO: Integrate with actual health monitor
        # For now, return mock data
        now = datetime.now(timezone.utc)
        return HealthStatus(
            status="healthy",
            circuit_breaker_active=False,
            api_connected=True,
            last_trade_timestamp=now,
            last_heartbeat=now,
            error_count_last_hour=0,
        )

    async def get_summary(self) -> BotSummaryResponse:
        """
        Get compressed bot summary (<10KB target).

        Returns:
            BotSummaryResponse with critical state only

        Example:
            >>> aggregator = StateAggregator()
            >>> summary = await aggregator.get_summary()
            >>> summary.position_count
            2
        """
        # Get full state (will use cache if valid)
        state = await self.get_bot_state(use_cache=True)

        # Calculate daily P&L (simplified)
        daily_pnl = state.performance.total_unrealized_pl

        # Get recent errors (max 3)
        recent_errors: List[Dict[str, Any]] = []
        # TODO: Integrate with error log
        # For now, return empty list

        return BotSummaryResponse(
            health_status=state.health.status,
            position_count=len(state.positions),
            open_orders_count=len(state.orders),
            daily_pnl=daily_pnl,
            circuit_breaker_status=(
                "active" if state.health.circuit_breaker_active else "inactive"
            ),
            recent_errors=recent_errors[:3],  # Max 3 errors
            timestamp=datetime.now(timezone.utc),
        )

    def invalidate_cache(self) -> None:
        """Invalidate cached state to force refresh on next request."""
        self._cached_state = None
        self._cache_timestamp = None

    def _is_cache_valid(self) -> bool:
        """Check if cached state is still valid.

        Returns:
            bool: True if cache exists and is within TTL
        """
        if not self._cached_state or not self._cache_timestamp:
            return False

        age = (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds()
        return age < self.cache_ttl

    async def _aggregate_state(self) -> BotStateResponse:
        """
        Aggregate state from all sources.

        Returns:
            BotStateResponse with fresh data from all sources

        Note:
            This is a simplified MVP implementation. In production, this would:
            1. Query dashboard data provider for positions/account
            2. Query performance tracker for metrics
            3. Query health monitor for status
            4. Load configuration from environment or config file
        """
        # TODO: Replace with actual data sources
        # For MVP, return mock data structure

        # Mock positions
        positions = [
            PositionResponse(
                symbol="AAPL",
                quantity=100,
                entry_price=Decimal("150.00"),
                current_price=Decimal("155.50"),
                unrealized_pl=Decimal("550.00"),
                unrealized_pl_pct=Decimal("3.67"),
                last_updated=datetime.now(timezone.utc),
            )
        ]

        # Mock account
        account = AccountStatusResponse(
            buying_power=Decimal("50000.00"),
            account_balance=Decimal("100000.00"),
            cash_balance=Decimal("75000.00"),
            day_trade_count=2,
            last_updated=datetime.now(timezone.utc),
        )

        # Mock performance
        performance = PerformanceMetricsResponse(
            win_rate=0.65,
            avg_risk_reward=2.5,
            total_realized_pl=Decimal("5000.00"),
            total_unrealized_pl=Decimal("550.00"),
            total_pl=Decimal("5550.00"),
            current_streak=3,
            streak_type="WIN",
            trades_today=5,
            session_count=15,
            max_drawdown=Decimal("-800.00"),
        )

        # Get health status
        health = await self.get_health_status()

        # Load config summary from environment
        config_summary = {
            "max_position_pct": float(os.getenv("MAX_POSITION_PCT", "5.0")),
            "max_daily_loss_pct": float(os.getenv("MAX_DAILY_LOSS_PCT", "3.0")),
            "paper_trading": os.getenv("PAPER_TRADING", "true").lower() == "true",
        }

        now = datetime.now(timezone.utc)
        data_collection_time = (
            self._cache_timestamp if self._is_cache_valid() else now
        )
        data_age = (now - data_collection_time).total_seconds() if data_collection_time else 0.0

        return BotStateResponse(
            positions=positions,
            orders=[],  # TODO: Integrate with order repository
            account=account,
            health=health,
            performance=performance,
            config_summary=config_summary,
            market_status="OPEN",  # TODO: Integrate with market data
            timestamp=now,
            data_age_seconds=data_age,
            warnings=[],  # TODO: Integrate with alert system
        )
