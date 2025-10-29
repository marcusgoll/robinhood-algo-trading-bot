"""Pydantic schemas for backtest API responses."""

from datetime import datetime
from pydantic import BaseModel, Field


class BacktestSummary(BaseModel):
    """Summary metadata for backtest list view."""

    id: str = Field(..., description="Backtest identifier (filename without extension)")
    strategy: str = Field(..., description="Strategy class name")
    symbols: list[str] = Field(..., description="List of symbols backtested")
    start_date: str = Field(..., description="Start date (ISO format)")
    end_date: str = Field(..., description="End date (ISO format)")
    total_return: float = Field(..., description="Total return percentage")
    win_rate: float = Field(..., description="Win rate (0-1)")
    total_trades: int = Field(..., description="Number of completed trades")
    created_at: str = Field(..., description="Backtest completion timestamp (ISO format)")


class BacktestListResponse(BaseModel):
    """Response for GET /api/v1/backtests."""

    data: list[BacktestSummary]
    total: int = Field(..., description="Total number of backtests")


class TradeDetail(BaseModel):
    """Individual trade details."""

    symbol: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    duration_days: int
    exit_reason: str
    commission: float
    slippage: float


class PerformanceMetrics(BaseModel):
    """Aggregated performance metrics."""

    total_return: float
    annualized_return: float
    cagr: float
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    max_drawdown: float
    max_drawdown_duration_days: int
    sharpe_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int


class EquityCurvePoint(BaseModel):
    """Single point on equity curve."""

    timestamp: str
    equity: float


class BacktestConfig(BaseModel):
    """Backtest configuration."""

    strategy: str
    symbols: list[str]
    start_date: str
    end_date: str
    initial_capital: float
    commission: float
    slippage_pct: float


class BacktestDetailResponse(BaseModel):
    """Complete backtest result for detail view."""

    config: BacktestConfig
    metrics: PerformanceMetrics
    trades: list[TradeDetail]
    equity_curve: list[EquityCurvePoint]
    data_warnings: list[str]
