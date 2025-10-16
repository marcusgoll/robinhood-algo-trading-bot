"""Risk management domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class PositionPlan:
    """Risk-adjusted position parameters for entry and exit."""

    symbol: str
    entry_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    quantity: int
    risk_amount: Decimal
    reward_amount: Decimal
    reward_ratio: float
    pullback_source: str
    pullback_price: Decimal | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class RiskManagementConfig:
    """Configuration parameters for risk management."""

    max_risk_per_trade_pct: float = 1.0
    max_portfolio_risk_pct: float = 6.0
    risk_reward_ratio_min: float = 2.0
    pullback_threshold_pct: float = 5.0
    trailing_stop_activation_pct: float = 10.0
    trailing_stop_distance_pct: float = 5.0


@dataclass(slots=True)
class PullbackData:
    """Pullback detection result for stop-loss calculation."""

    pullback_price: Decimal
    pullback_timestamp: datetime
    confirmation_candles: int
    lookback_window: int
    fallback_used: bool


@dataclass(slots=True)
class ATRStopData:
    """ATR-based stop-loss calculation result with volatility metrics."""

    stop_price: Decimal
    atr_value: Decimal
    atr_multiplier: float
    atr_period: int
    source: str = "atr"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class RiskManagementEnvelope:
    """Audit-friendly record tracking position lifecycle with stop and target orders.

    Similar to OrderEnvelope pattern, tracks entry/stop/target orders and their status.
    Enhanced with correlation_id for full position lifecycle tracing (T033).
    """

    position_plan: PositionPlan
    entry_order_id: str
    stop_order_id: str
    target_order_id: str
    status: str  # "pending" | "active" | "stopped" | "target_hit" | "cancelled"
    correlation_id: str  # UUID4 for tracing position lifecycle across logs
    adjustments: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
