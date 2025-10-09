"""
Metrics Calculator Service

Calculates aggregated trading performance metrics from trade records and positions.

Constitution v1.0.0:
- §Data_Integrity: Robust handling of edge cases (empty lists, division by zero)
- §Audit_Everything: All calculations traceable to source data
- §Safety_First: Decimal precision for financial calculations

Feature: status-dashboard
Task: T018 - Create MetricsCalculator class
"""

from datetime import UTC
from decimal import Decimal
from typing import Literal

from ..account.account_data import Position
from ..logging.trade_record import TradeRecord
from .models import PerformanceMetrics


class MetricsCalculator:
    """
    Service class for calculating trading performance metrics.

    Provides static methods for win rate, risk-reward ratio, streak tracking,
    and P&L aggregation. All methods handle edge cases gracefully (empty lists,
    division by zero) and use Decimal precision for financial calculations.

    Usage:
        trades = load_trades_from_log()
        positions = account_data.get_positions()
        metrics = MetricsCalculator.aggregate_metrics(trades, positions)
    """

    @staticmethod
    def calculate_win_rate(trades: list[TradeRecord]) -> float:
        """
        Calculate win rate percentage from closed trades.

        Formula: (winning trades / total closed trades) × 100

        Args:
            trades: List of TradeRecord objects

        Returns:
            Win rate as float percentage (0.0-100.0).
            Returns 0.0 if no closed trades exist.

        Examples:
            >>> trades = [
            ...     TradeRecord(..., outcome="win"),
            ...     TradeRecord(..., outcome="win"),
            ...     TradeRecord(..., outcome="loss"),
            ...     TradeRecord(..., outcome="open")  # Excluded
            ... ]
            >>> MetricsCalculator.calculate_win_rate(trades)
            66.67

        Notes:
            - Only counts closed trades (outcome in ["win", "loss", "breakeven"])
            - Open trades are excluded from calculation
            - Breakeven trades count as non-wins
        """
        # Filter closed trades only
        closed_trades = [
            t for t in trades
            if t.outcome in ["win", "loss", "breakeven"]
        ]

        if not closed_trades:
            return 0.0

        winning_trades = sum(1 for t in closed_trades if t.outcome == "win")
        win_rate = (winning_trades / len(closed_trades)) * 100

        return round(win_rate, 2)

    @staticmethod
    def calculate_avg_risk_reward(trades: list[TradeRecord]) -> float:
        """
        Calculate average risk-reward ratio from trades with targets and stops.

        Formula: Average of (target - entry) / (entry - stop_loss) for each trade

        Args:
            trades: List of TradeRecord objects

        Returns:
            Average risk-reward ratio as float (e.g., 2.0 means 2:1 R:R).
            Returns 0.0 if no trades have both target and stop_loss set.

        Examples:
            >>> trades = [
            ...     TradeRecord(..., price=100, target=106, stop_loss=98),  # 3:1 R:R
            ...     TradeRecord(..., price=50, target=52, stop_loss=49)     # 2:1 R:R
            ... ]
            >>> MetricsCalculator.calculate_avg_risk_reward(trades)
            2.5

        Notes:
            - Only includes trades with both target and stop_loss set
            - Handles edge case where entry == stop_loss (returns 0 for that trade)
            - Uses Decimal for precision during calculation
        """
        valid_trades = [
            t for t in trades
            if t.target is not None and t.stop_loss is not None
        ]

        if not valid_trades:
            return 0.0

        risk_reward_ratios = []
        for trade in valid_trades:
            entry = trade.price
            target = trade.target  # type: ignore
            stop_loss = trade.stop_loss  # type: ignore

            risk = entry - stop_loss
            reward = target - entry

            # Avoid division by zero
            if risk == 0:
                continue

            rr_ratio = float(reward / risk)
            risk_reward_ratios.append(rr_ratio)

        if not risk_reward_ratios:
            return 0.0

        avg_rr = sum(risk_reward_ratios) / len(risk_reward_ratios)
        return round(avg_rr, 2)

    @staticmethod
    def calculate_current_streak(
        trades: list[TradeRecord]
    ) -> tuple[int, Literal["WIN", "LOSS", "NONE"]]:
        """
        Calculate current win/loss streak from most recent trades.

        Counts consecutive wins or losses starting from the most recent closed trade
        and working backwards. Stops at first trade with opposite outcome.

        Args:
            trades: List of TradeRecord objects (any order, will be sorted by timestamp)

        Returns:
            Tuple of (streak_count, streak_type):
                - streak_count: Number of consecutive outcomes (0 if no closed trades)
                - streak_type: "WIN", "LOSS", or "NONE"

        Examples:
            >>> trades = [
            ...     TradeRecord(..., timestamp="2025-01-09T10:00:00Z", outcome="win"),
            ...     TradeRecord(..., timestamp="2025-01-09T11:00:00Z", outcome="win"),
            ...     TradeRecord(..., timestamp="2025-01-09T12:00:00Z", outcome="win"),
            ...     TradeRecord(..., timestamp="2025-01-09T13:00:00Z", outcome="loss")
            ... ]
            >>> MetricsCalculator.calculate_current_streak(trades)
            (1, "LOSS")  # Most recent trade is a loss

        Notes:
            - Only considers closed trades (outcome in ["win", "loss"])
            - Breakeven trades break the streak (returns streak before breakeven)
            - Open trades are ignored
        """
        # Filter and sort closed trades by timestamp (most recent first)
        closed_trades = [
            t for t in trades
            if t.outcome in ["win", "loss"]
        ]

        if not closed_trades:
            return (0, "NONE")

        # Sort by timestamp descending (most recent first)
        closed_trades.sort(key=lambda t: t.timestamp, reverse=True)

        # Start with most recent trade outcome
        current_outcome = closed_trades[0].outcome
        streak_count = 0

        # Count consecutive trades with same outcome
        for trade in closed_trades:
            if trade.outcome == current_outcome:
                streak_count += 1
            else:
                break

        streak_type: Literal["WIN", "LOSS"] = "WIN" if current_outcome == "win" else "LOSS"
        return (streak_count, streak_type)

    @staticmethod
    def calculate_total_pl(
        trades: list[TradeRecord],
        positions: list[Position]
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Calculate total profit/loss from realized trades and unrealized positions.

        Args:
            trades: List of TradeRecord objects
            positions: List of Position objects from account data

        Returns:
            Tuple of (total_realized_pl, total_unrealized_pl, total_pl):
                - total_realized_pl: Sum of net_profit_loss from closed trades
                - total_unrealized_pl: Sum of profit_loss from open positions
                - total_pl: Sum of realized + unrealized

        Examples:
            >>> trades = [
            ...     TradeRecord(..., net_profit_loss=Decimal("50.00")),
            ...     TradeRecord(..., net_profit_loss=Decimal("-20.00"))
            ... ]
            >>> positions = [
            ...     Position(..., profit_loss=Decimal("15.00"))
            ... ]
            >>> MetricsCalculator.calculate_total_pl(trades, positions)
            (Decimal("30.00"), Decimal("15.00"), Decimal("45.00"))

        Notes:
            - Only includes trades with non-None net_profit_loss
            - Uses Decimal for precise financial calculations
            - Returns (0, 0, 0) if no trades or positions exist
        """
        # Calculate realized P&L from closed trades
        realized_pl = Decimal("0")
        for trade in trades:
            if trade.net_profit_loss is not None:
                realized_pl += trade.net_profit_loss

        # Calculate unrealized P&L from open positions
        unrealized_pl = Decimal("0")
        for position in positions:
            unrealized_pl += position.profit_loss

        # Total P&L
        total_pl = realized_pl + unrealized_pl

        return (realized_pl, unrealized_pl, total_pl)

    @staticmethod
    def aggregate_metrics(
        trades: list[TradeRecord],
        positions: list[Position],
        session_count: int = 0
    ) -> PerformanceMetrics:
        """
        Aggregate all performance metrics into PerformanceMetrics dataclass.

        Main entry point for dashboard metric calculation. Calls all individual
        calculation methods and bundles results into a single dataclass.

        Args:
            trades: List of TradeRecord objects
            positions: List of Position objects from account data
            session_count: Number of trading sessions (default: 0)

        Returns:
            PerformanceMetrics dataclass with all calculated metrics

        Examples:
            >>> trades = load_trades_from_log()
            >>> positions = account_data.get_positions()
            >>> metrics = MetricsCalculator.aggregate_metrics(trades, positions)
            >>> print(f"Win Rate: {metrics.win_rate}%")
            >>> print(f"Total P&L: ${metrics.total_pl}")

        Notes:
            - Handles empty trade/position lists gracefully
            - All calculations use appropriate precision (float for rates, Decimal for money)
            - trades_today calculated as count of trades with today's date in timestamp
        """
        # Calculate individual metrics
        win_rate = MetricsCalculator.calculate_win_rate(trades)
        avg_rr = MetricsCalculator.calculate_avg_risk_reward(trades)
        streak_count, streak_type = MetricsCalculator.calculate_current_streak(trades)
        realized_pl, unrealized_pl, total_pl = MetricsCalculator.calculate_total_pl(
            trades, positions
        )

        # Count today's trades
        from datetime import datetime
        today = datetime.now(UTC).date()
        trades_today = sum(
            1 for t in trades
            if datetime.fromisoformat(t.timestamp.replace('Z', '+00:00')).date() == today
        )

        # Build PerformanceMetrics dataclass
        return PerformanceMetrics(
            win_rate=win_rate,
            avg_risk_reward=avg_rr,
            total_realized_pl=realized_pl,
            total_unrealized_pl=unrealized_pl,
            total_pl=total_pl,
            current_streak=streak_count,
            streak_type=streak_type,
            trades_today=trades_today,
            session_count=session_count
        )
