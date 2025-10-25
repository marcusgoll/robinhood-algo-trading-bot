"""State API schemas for bot status and monitoring.

Pydantic schemas for state, health, and summary endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


class PositionResponse(BaseModel):
    """Position display for API responses."""

    symbol: str = Field(..., description="Stock ticker symbol")
    quantity: int = Field(..., description="Number of shares")
    entry_price: Decimal = Field(..., description="Average entry price")
    current_price: Decimal = Field(..., description="Current market price")
    unrealized_pl: Decimal = Field(..., description="Unrealized profit/loss in dollars")
    unrealized_pl_pct: Decimal = Field(..., description="Unrealized profit/loss percentage")
    last_updated: datetime = Field(..., description="Last price update timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "AAPL",
                "quantity": 100,
                "entry_price": "150.00",
                "current_price": "155.50",
                "unrealized_pl": "550.00",
                "unrealized_pl_pct": "3.67",
                "last_updated": "2025-10-24T10:30:00Z",
            }
        }
    )


class AccountStatusResponse(BaseModel):
    """Account status for API responses."""

    buying_power: Decimal = Field(..., description="Available buying power")
    account_balance: Decimal = Field(..., description="Total account balance")
    cash_balance: Decimal = Field(..., description="Cash balance")
    day_trade_count: int = Field(..., description="Day trades in last 5 business days")
    last_updated: datetime = Field(..., description="Last account data update")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "buying_power": "50000.00",
                "account_balance": "100000.00",
                "cash_balance": "75000.00",
                "day_trade_count": 2,
                "last_updated": "2025-10-24T10:30:00Z",
            }
        }
    )


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics for API responses."""

    win_rate: float = Field(..., description="Win rate (0.0-1.0)")
    avg_risk_reward: float = Field(..., description="Average risk/reward ratio")
    total_realized_pl: Decimal = Field(..., description="Total realized profit/loss")
    total_unrealized_pl: Decimal = Field(..., description="Total unrealized profit/loss")
    total_pl: Decimal = Field(..., description="Combined total profit/loss")
    current_streak: int = Field(..., description="Current win/loss streak count")
    streak_type: Literal["WIN", "LOSS", "NONE"] = Field(..., description="Streak type")
    trades_today: int = Field(..., description="Number of trades today")
    session_count: int = Field(..., description="Total trading sessions")
    max_drawdown: Decimal = Field(..., description="Maximum drawdown")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "win_rate": 0.65,
                "avg_risk_reward": 2.5,
                "total_realized_pl": "5000.00",
                "total_unrealized_pl": "550.00",
                "total_pl": "5550.00",
                "current_streak": 3,
                "streak_type": "WIN",
                "trades_today": 5,
                "session_count": 15,
                "max_drawdown": "-800.00",
            }
        }
    )


class HealthStatus(BaseModel):
    """Health status of the trading bot."""

    status: Literal["healthy", "degraded", "offline"] = Field(
        ..., description="Overall health status"
    )
    circuit_breaker_active: bool = Field(..., description="Circuit breaker status")
    api_connected: bool = Field(..., description="Robinhood API connection status")
    last_trade_timestamp: Optional[datetime] = Field(
        None, description="Timestamp of last trade execution"
    )
    last_heartbeat: datetime = Field(
        ..., description="Timestamp of last health check heartbeat"
    )
    error_count_last_hour: int = Field(
        0, description="Number of errors in the last hour"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "circuit_breaker_active": False,
                "api_connected": True,
                "last_trade_timestamp": "2025-10-24T10:25:00Z",
                "last_heartbeat": "2025-10-24T10:30:00Z",
                "error_count_last_hour": 0,
            }
        }
    )


class BotStateResponse(BaseModel):
    """Complete bot state response for GET /api/v1/state."""

    positions: List[PositionResponse] = Field(..., description="Current open positions")
    orders: List[Dict[str, Any]] = Field(..., description="Recent orders summary")
    account: AccountStatusResponse = Field(..., description="Account status")
    health: HealthStatus = Field(..., description="Bot health status")
    performance: PerformanceMetricsResponse = Field(..., description="Performance metrics")
    config_summary: Dict[str, Any] = Field(
        ..., description="Current configuration summary"
    )
    market_status: Literal["OPEN", "CLOSED"] = Field(..., description="Market status")
    timestamp: datetime = Field(..., description="Response generation timestamp")
    data_age_seconds: float = Field(
        ..., description="Age of data in seconds since collection (for staleness detection)"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Active warnings or alerts"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "positions": [
                    {
                        "symbol": "AAPL",
                        "quantity": 100,
                        "entry_price": "150.00",
                        "current_price": "155.50",
                        "unrealized_pl": "550.00",
                        "unrealized_pl_pct": "3.67",
                        "last_updated": "2025-10-24T10:30:00Z",
                    }
                ],
                "orders": [],
                "account": {
                    "buying_power": "50000.00",
                    "account_balance": "100000.00",
                    "cash_balance": "75000.00",
                    "day_trade_count": 2,
                    "last_updated": "2025-10-24T10:30:00Z",
                },
                "health": {
                    "status": "healthy",
                    "circuit_breaker_active": False,
                    "api_connected": True,
                    "last_trade_timestamp": "2025-10-24T10:25:00Z",
                    "error_count_last_hour": 0,
                },
                "performance": {
                    "win_rate": 0.65,
                    "avg_risk_reward": 2.5,
                    "total_realized_pl": "5000.00",
                    "total_unrealized_pl": "550.00",
                    "total_pl": "5550.00",
                    "current_streak": 3,
                    "streak_type": "WIN",
                    "trades_today": 5,
                    "session_count": 15,
                    "max_drawdown": "-800.00",
                },
                "config_summary": {
                    "max_position_pct": 5.0,
                    "max_daily_loss_pct": 3.0,
                    "paper_trading": True,
                },
                "market_status": "OPEN",
                "timestamp": "2025-10-24T10:30:00Z",
            }
        }
    )


class BotSummaryResponse(BaseModel):
    """Compressed bot summary for GET /api/v1/summary (<10KB target)."""

    health_status: Literal["healthy", "degraded", "offline"] = Field(
        ..., description="Overall health status"
    )
    position_count: int = Field(..., description="Number of open positions")
    open_orders_count: int = Field(..., description="Number of open orders")
    daily_pnl: Decimal = Field(..., description="Today's profit/loss")
    circuit_breaker_status: str = Field(..., description="Circuit breaker status")
    recent_errors: List[Dict[str, Any]] = Field(
        ..., max_length=3, description="Last 3 errors (truncated)"
    )
    timestamp: datetime = Field(..., description="Response generation timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "health_status": "healthy",
                "positions_count": 1,
                "open_orders_count": 0,
                "daily_pnl": "550.00",
                "circuit_breaker_status": "inactive",
                "recent_errors": [],
                "timestamp": "2025-10-24T10:30:00Z",
            }
        }
    )
