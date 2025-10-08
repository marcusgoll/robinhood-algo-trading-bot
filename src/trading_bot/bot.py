"""
Main Trading Bot Implementation

Enforces Constitution v1.0.0 principles:
- §Safety_First: Circuit breakers, paper trading mode
- §Risk_Management: Position limits, stop losses
- §Code_Quality: Type hints, clear logic
"""

from typing import Dict, List, Optional
from decimal import Decimal
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker to halt trading on excessive losses (§Safety_First)."""

    def __init__(self, max_daily_loss_pct: float, max_consecutive_losses: int):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.daily_pnl: Decimal = Decimal("0")
        self.consecutive_losses: int = 0
        self.is_tripped: bool = False

    def check_and_trip(self, trade_pnl: Decimal, portfolio_value: Decimal) -> bool:
        """
        Check if circuit breaker should trip.

        Args:
            trade_pnl: Profit/loss from latest trade
            portfolio_value: Current portfolio value

        Returns:
            True if circuit breaker tripped, False otherwise
        """
        self.daily_pnl += trade_pnl

        # Check consecutive losses
        if trade_pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Trip if daily loss exceeds threshold
        daily_loss_pct = abs(float(self.daily_pnl / portfolio_value)) * 100
        if daily_loss_pct > self.max_daily_loss_pct:
            self.is_tripped = True
            logger.critical(
                f"CIRCUIT BREAKER TRIPPED: Daily loss {daily_loss_pct:.2f}% "
                f"exceeds limit {self.max_daily_loss_pct}%"
            )
            return True

        # Trip if consecutive losses exceed threshold
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.is_tripped = True
            logger.critical(
                f"CIRCUIT BREAKER TRIPPED: {self.consecutive_losses} "
                f"consecutive losses (limit: {self.max_consecutive_losses})"
            )
            return True

        return False

    def reset_daily(self) -> None:
        """Reset daily counters (call at market open)."""
        self.daily_pnl = Decimal("0")
        self.is_tripped = False
        logger.info("Circuit breaker reset for new trading day")


class TradingBot:
    """
    Main trading bot with safety features per Constitution v1.0.0.

    Enforces:
    - Circuit breakers (§Safety_First)
    - Position limits (§Risk_Management)
    - Paper trading mode (§Safety_First)
    - Comprehensive logging (§Audit_Everything)
    """

    def __init__(
        self,
        *,
        paper_trading: bool = True,
        max_position_pct: float = 5.0,
        max_daily_loss_pct: float = 3.0,
        max_consecutive_losses: int = 3,
    ):
        """
        Initialize trading bot with safety parameters.

        Args:
            paper_trading: If True, simulate trades without real money (§Safety_First)
            max_position_pct: Maximum % of portfolio per position (§Risk_Management)
            max_daily_loss_pct: Circuit breaker: max daily loss % (§Safety_First)
            max_consecutive_losses: Circuit breaker: max consecutive losses (§Safety_First)
        """
        self.paper_trading = paper_trading
        self.max_position_pct = max_position_pct

        self.circuit_breaker = CircuitBreaker(
            max_daily_loss_pct=max_daily_loss_pct,
            max_consecutive_losses=max_consecutive_losses,
        )

        self.positions: Dict[str, Dict] = {}
        self.is_running: bool = False

        logger.info(
            f"TradingBot initialized | "
            f"Paper Trading: {paper_trading} | "
            f"Max Position: {max_position_pct}% | "
            f"Max Daily Loss: {max_daily_loss_pct}% | "
            f"Max Consecutive Losses: {max_consecutive_losses}"
        )

    def start(self) -> None:
        """Start the trading bot (§Safety_First: manual start required)."""
        if self.circuit_breaker.is_tripped:
            logger.error("Cannot start: Circuit breaker is tripped")
            raise RuntimeError("Circuit breaker is tripped - manual reset required")

        self.is_running = True
        logger.info("Trading bot started")

    def stop(self) -> None:
        """Emergency stop (§Safety_First: kill switch)."""
        self.is_running = False
        logger.warning("Trading bot stopped (manual kill switch)")

    def calculate_position_size(
        self,
        symbol: str,
        portfolio_value: Decimal,
        current_price: Decimal,
    ) -> int:
        """
        Calculate position size within risk limits (§Risk_Management).

        Args:
            symbol: Stock symbol
            portfolio_value: Current portfolio value
            current_price: Current stock price

        Returns:
            Number of shares to buy (0 if limits exceeded)
        """
        max_position_value = portfolio_value * Decimal(self.max_position_pct / 100)
        shares = int(max_position_value / current_price)

        logger.info(
            f"Position sizing for {symbol}: "
            f"Portfolio=${portfolio_value} | "
            f"Max Position=${max_position_value} | "
            f"Price=${current_price} | "
            f"Shares={shares}"
        )

        return shares

    def execute_trade(
        self,
        symbol: str,
        action: str,
        shares: int,
        price: Decimal,
        reason: str,
    ) -> None:
        """
        Execute trade with logging (§Audit_Everything).

        Args:
            symbol: Stock symbol
            action: 'buy' or 'sell'
            shares: Number of shares
            price: Execution price
            reason: Trading decision reason (for audit trail)
        """
        if not self.is_running:
            logger.warning(f"Trade rejected: Bot not running | {symbol} {action} {shares}")
            return

        if self.circuit_breaker.is_tripped:
            logger.error(f"Trade rejected: Circuit breaker tripped | {symbol} {action} {shares}")
            return

        # Log trade decision with reasoning (§Audit_Everything)
        logger.info(
            f"TRADE EXECUTED | "
            f"Symbol={symbol} | "
            f"Action={action} | "
            f"Shares={shares} | "
            f"Price=${price} | "
            f"Paper={self.paper_trading} | "
            f"Reason={reason} | "
            f"Timestamp={datetime.utcnow().isoformat()}"
        )

        if self.paper_trading:
            logger.info(f"PAPER TRADE: {symbol} {action} {shares} @ ${price}")
        else:
            # TODO: Implement real Robinhood API call
            # Must implement with proper error handling (§Error_Handling)
            logger.warning("Real trading not yet implemented")

    def update_position(
        self,
        symbol: str,
        shares: int,
        entry_price: Decimal,
        stop_loss_price: Decimal,
    ) -> None:
        """
        Update position tracking with stop loss (§Risk_Management).

        Args:
            symbol: Stock symbol
            shares: Position size
            entry_price: Entry price
            stop_loss_price: Stop loss price (§Risk_Management: required)
        """
        self.positions[symbol] = {
            "shares": shares,
            "entry_price": entry_price,
            "stop_loss": stop_loss_price,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(
            f"Position updated: {symbol} | "
            f"Shares={shares} | "
            f"Entry=${entry_price} | "
            f"Stop Loss=${stop_loss_price}"
        )

    def check_stop_loss(self, symbol: str, current_price: Decimal) -> bool:
        """
        Check if stop loss triggered (§Risk_Management).

        Args:
            symbol: Stock symbol
            current_price: Current market price

        Returns:
            True if stop loss hit, False otherwise
        """
        if symbol not in self.positions:
            return False

        position = self.positions[symbol]
        stop_loss = Decimal(str(position["stop_loss"]))

        if current_price <= stop_loss:
            logger.warning(
                f"STOP LOSS TRIGGERED: {symbol} | "
                f"Current=${current_price} | "
                f"Stop=${stop_loss} | "
                f"Entry=${position['entry_price']}"
            )
            return True

        return False
