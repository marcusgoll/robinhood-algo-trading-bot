"""Risk management domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class PositionPlan:
    """Risk-adjusted position parameters for entry and exit."""

    symbol: str
    entry_price: Decimal
    initial_stop_loss: Decimal
    target_price: Decimal
    position_size: int
    risk_amount: Decimal
    risk_reward_ratio: float
    created_at: datetime = field(default_factory=datetime.now)


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
class RiskManagementEnvelope:
    """Audit-friendly record of risk management actions."""

    action_type: str  # "initial_plan", "stop_adjustment", "target_hit", etc.
    symbol: str
    timestamp: datetime
    details: dict[str, Any] = field(default_factory=dict)
    position_plan: PositionPlan | None = None
