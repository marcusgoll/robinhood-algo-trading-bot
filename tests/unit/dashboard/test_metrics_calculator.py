"""
Unit tests for MetricsCalculator (TDD RED Phase).

Tests performance metric calculations including win rate, current streak, and total P&L.

Constitution v1.0.0 - §Testing_Requirements: TDD with RED-GREEN-REFACTOR
Feature: status-dashboard
Tasks: T005-T007 [RED] - Write failing tests for MetricsCalculator

Expected to FAIL: MetricsCalculator methods not fully implemented yet
"""

import pytest
from datetime import datetime, timezone, UTC
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, Mock
import tempfile
import shutil

# This import may FAIL if MetricsCalculator doesn't have required methods yet (RED phase)
from trading_bot.dashboard.metrics_calculator import MetricsCalculator
from trading_bot.logging.trade_record import TradeRecord
from trading_bot.account.account_data import Position


def _create_trade(
    symbol: str = "AAPL",
    action: str = "BUY",
    quantity: int = 100,
    price: Decimal = Decimal("150.00"),
    outcome: str = "open",
    profit_loss: Decimal | None = None,
) -> TradeRecord:
    """Helper to create a TradeRecord for testing.

    Args:
        symbol: Stock ticker symbol
        action: "BUY" or "SELL"
        quantity: Number of shares
        price: Execution price
        outcome: "win", "loss", "breakeven", or "open"
        profit_loss: P&L amount (required if outcome is not "open")

    Returns:
        TradeRecord instance with test data
    """
    now_iso = datetime.now(UTC).isoformat()

    return TradeRecord(
        timestamp=now_iso,
        symbol=symbol,
        action=action,
        quantity=quantity,
        price=price,
        total_value=Decimal(quantity) * price,
        order_id=f"order-{symbol}-{action}",
        execution_mode="PAPER",
        account_id=None,
        strategy_name="test-strategy",
        entry_type="breakout",
        stop_loss=price * Decimal("0.95"),
        target=price * Decimal("1.10"),
        decision_reasoning="Test trade",
        indicators_used=["VWAP", "EMA-9"],
        risk_reward_ratio=2.0,
        outcome=outcome,
        profit_loss=profit_loss,
        hold_duration_seconds=300 if outcome != "open" else None,
        exit_timestamp=now_iso if outcome != "open" else None,
        exit_reasoning=f"Test {outcome}" if outcome != "open" else None,
        slippage=Decimal("0"),
        commission=Decimal("0"),
        net_profit_loss=profit_loss if profit_loss else None,
        session_id="test-session",
        bot_version="1.0.0",
        config_hash="test-hash",
    )


class TestMetricsCalculatorWinRate:
    """T005 [RED]: Test win rate computation from trade logs."""

    @pytest.fixture
    def metrics_calculator(self) -> MetricsCalculator:
        """Create a MetricsCalculator instance for testing."""
        return MetricsCalculator()

    def test_win_rate_all_wins(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test win rate calculation with all winning trades (100%).

        GIVEN: Trade log with 5 winning trades (all closed with outcome="win")
        WHEN: calculate_win_rate() is called
        THEN: Returns 100.0 (100% win rate)

        From: tasks.md T005 - Win rate with all wins (100%)
        Pattern: tests/unit/test_query_helper.py calculate_win_rate
        """
        # GIVEN: 5 winning trades
        trades = [
            _create_trade(symbol="AAPL", outcome="win", profit_loss=Decimal("50.00")),
            _create_trade(symbol="MSFT", outcome="win", profit_loss=Decimal("75.00")),
            _create_trade(symbol="TSLA", outcome="win", profit_loss=Decimal("100.00")),
            _create_trade(symbol="GOOGL", outcome="win", profit_loss=Decimal("25.00")),
            _create_trade(symbol="AMZN", outcome="win", profit_loss=Decimal("60.00")),
        ]

        # WHEN: Calculate win rate
        win_rate = metrics_calculator.calculate_win_rate(trades)

        # THEN: Win rate should be 100%
        assert win_rate == 100.0, f"Expected 100% win rate with all wins, got {win_rate}%"

    def test_win_rate_all_losses(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test win rate calculation with all losing trades (0%).

        GIVEN: Trade log with 3 losing trades (all closed with outcome="loss")
        WHEN: calculate_win_rate() is called
        THEN: Returns 0.0 (0% win rate)

        From: tasks.md T005 - Win rate with all losses (0%)
        """
        # GIVEN: 3 losing trades
        trades = [
            _create_trade(symbol="AAPL", outcome="loss", profit_loss=Decimal("-30.00")),
            _create_trade(symbol="MSFT", outcome="loss", profit_loss=Decimal("-45.00")),
            _create_trade(symbol="TSLA", outcome="loss", profit_loss=Decimal("-20.00")),
        ]

        # WHEN: Calculate win rate
        win_rate = metrics_calculator.calculate_win_rate(trades)

        # THEN: Win rate should be 0%
        assert win_rate == 0.0, f"Expected 0% win rate with all losses, got {win_rate}%"

    def test_win_rate_mixed_outcomes(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test win rate calculation with realistic mixed outcomes.

        GIVEN: Trade log with 6 wins, 4 losses, 2 breakevens, 3 open trades
        WHEN: calculate_win_rate() is called
        THEN: Returns 50.0 (6 wins / 12 closed trades = 50%)

        From: tasks.md T005 - Win rate with mixed outcomes (realistic)
        Note: Breakevens count as closed trades but not wins
        """
        # GIVEN: Mixed trade outcomes
        trades = [
            # 6 winning trades
            _create_trade(symbol="AAPL", outcome="win", profit_loss=Decimal("50.00")),
            _create_trade(symbol="MSFT", outcome="win", profit_loss=Decimal("40.00")),
            _create_trade(symbol="TSLA", outcome="win", profit_loss=Decimal("60.00")),
            _create_trade(symbol="GOOGL", outcome="win", profit_loss=Decimal("30.00")),
            _create_trade(symbol="AMZN", outcome="win", profit_loss=Decimal("70.00")),
            _create_trade(symbol="NVDA", outcome="win", profit_loss=Decimal("45.00")),
            # 4 losing trades
            _create_trade(symbol="AAPL", outcome="loss", profit_loss=Decimal("-25.00")),
            _create_trade(symbol="MSFT", outcome="loss", profit_loss=Decimal("-35.00")),
            _create_trade(symbol="TSLA", outcome="loss", profit_loss=Decimal("-30.00")),
            _create_trade(symbol="GOOGL", outcome="loss", profit_loss=Decimal("-20.00")),
            # 2 breakeven trades
            _create_trade(symbol="AMZN", outcome="breakeven", profit_loss=Decimal("0.00")),
            _create_trade(symbol="NVDA", outcome="breakeven", profit_loss=Decimal("0.00")),
            # 3 open trades (should be excluded from win rate)
            _create_trade(symbol="META", outcome="open", profit_loss=None),
            _create_trade(symbol="NFLX", outcome="open", profit_loss=None),
            _create_trade(symbol="DIS", outcome="open", profit_loss=None),
        ]

        # WHEN: Calculate win rate
        win_rate = metrics_calculator.calculate_win_rate(trades)

        # THEN: Win rate = 6 wins / (6 wins + 4 losses + 2 breakevens) = 6/12 = 50%
        expected_win_rate = 50.0
        assert abs(win_rate - expected_win_rate) < 0.01, \
            f"Expected {expected_win_rate}% win rate, got {win_rate}%"

    def test_win_rate_empty_log(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test win rate calculation with empty trade log.

        GIVEN: Empty trade log (no trades)
        WHEN: calculate_win_rate() is called
        THEN: Returns 0.0 (no closed trades = 0% by convention)

        From: tasks.md T005 - Empty log (0%)
        Pattern: TradeQueryHelper.calculate_win_rate() edge case handling
        """
        # GIVEN: Empty trade list
        trades: list[TradeRecord] = []

        # WHEN: Calculate win rate
        win_rate = metrics_calculator.calculate_win_rate(trades)

        # THEN: Win rate should be 0.0 (edge case: no trades)
        assert win_rate == 0.0, f"Expected 0% win rate with empty log, got {win_rate}%"

    def test_win_rate_only_open_trades(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test win rate calculation with only open trades (no closed trades).

        GIVEN: Trade log with 5 open trades (all outcome="open")
        WHEN: calculate_win_rate() is called
        THEN: Returns 0.0 (no closed trades = 0% by convention)

        From: tasks.md T005 - Edge case: all open trades
        """
        # GIVEN: 5 open trades
        trades = [
            _create_trade(symbol="AAPL", outcome="open", profit_loss=None),
            _create_trade(symbol="MSFT", outcome="open", profit_loss=None),
            _create_trade(symbol="TSLA", outcome="open", profit_loss=None),
            _create_trade(symbol="GOOGL", outcome="open", profit_loss=None),
            _create_trade(symbol="AMZN", outcome="open", profit_loss=None),
        ]

        # WHEN: Calculate win rate
        win_rate = metrics_calculator.calculate_win_rate(trades)

        # THEN: Win rate should be 0.0 (no closed trades)
        assert win_rate == 0.0, f"Expected 0% win rate with only open trades, got {win_rate}%"


class TestMetricsCalculatorStreak:
    """T006 [RED]: Test current streak computation."""

    @pytest.fixture
    def metrics_calculator(self) -> MetricsCalculator:
        """Create a MetricsCalculator instance for testing."""
        return MetricsCalculator()

    def test_current_streak_win_streak(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test current streak with 3 consecutive wins.

        GIVEN: Trade log ending with 3 consecutive wins
        WHEN: calculate_current_streak() is called
        THEN: Returns (3, "WIN")

        From: tasks.md T006 - Win streak (3)
        """
        # GIVEN: Trade log with 3 consecutive wins at the end
        trades = [
            _create_trade(symbol="AAPL", outcome="loss", profit_loss=Decimal("-20.00")),
            _create_trade(symbol="MSFT", outcome="win", profit_loss=Decimal("50.00")),
            _create_trade(symbol="TSLA", outcome="win", profit_loss=Decimal("60.00")),
            _create_trade(symbol="GOOGL", outcome="win", profit_loss=Decimal("40.00")),
        ]

        # WHEN: Calculate current streak
        streak_count, streak_type = metrics_calculator.calculate_current_streak(trades)

        # THEN: Should return 3 win streak
        assert streak_count == 3, f"Expected streak count of 3, got {streak_count}"
        assert streak_type == "WIN", f"Expected streak type 'WIN', got '{streak_type}'"

    def test_current_streak_loss_streak(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test current streak with 2 consecutive losses.

        GIVEN: Trade log ending with 2 consecutive losses
        WHEN: calculate_current_streak() is called
        THEN: Returns (2, "LOSS")

        From: tasks.md T006 - Loss streak (2)
        """
        # GIVEN: Trade log with 2 consecutive losses at the end
        trades = [
            _create_trade(symbol="AAPL", outcome="win", profit_loss=Decimal("50.00")),
            _create_trade(symbol="MSFT", outcome="win", profit_loss=Decimal("40.00")),
            _create_trade(symbol="TSLA", outcome="loss", profit_loss=Decimal("-30.00")),
            _create_trade(symbol="GOOGL", outcome="loss", profit_loss=Decimal("-25.00")),
        ]

        # WHEN: Calculate current streak
        streak_count, streak_type = metrics_calculator.calculate_current_streak(trades)

        # THEN: Should return 2 loss streak
        assert streak_count == 2, f"Expected streak count of 2, got {streak_count}"
        assert streak_type == "LOSS", f"Expected streak type 'LOSS', got '{streak_type}'"

    def test_current_streak_no_trades(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test current streak with no trades (empty log).

        GIVEN: Empty trade log
        WHEN: calculate_current_streak() is called
        THEN: Returns (0, "NONE")

        From: tasks.md T006 - No trades (0)
        """
        # GIVEN: Empty trade list
        trades: list[TradeRecord] = []

        # WHEN: Calculate current streak
        streak_count, streak_type = metrics_calculator.calculate_current_streak(trades)

        # THEN: Should return 0 streak with type NONE
        assert streak_count == 0, f"Expected streak count of 0, got {streak_count}"
        assert streak_type == "NONE", f"Expected streak type 'NONE', got '{streak_type}'"

    def test_current_streak_single_trade_win(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test current streak with single winning trade.

        GIVEN: Trade log with single win
        WHEN: calculate_current_streak() is called
        THEN: Returns (1, "WIN")

        From: tasks.md T006 - Single trade (1)
        """
        # GIVEN: Single winning trade
        trades = [
            _create_trade(symbol="AAPL", outcome="win", profit_loss=Decimal("50.00")),
        ]

        # WHEN: Calculate current streak
        streak_count, streak_type = metrics_calculator.calculate_current_streak(trades)

        # THEN: Should return 1 win streak
        assert streak_count == 1, f"Expected streak count of 1, got {streak_count}"
        assert streak_type == "WIN", f"Expected streak type 'WIN', got '{streak_type}'"

    def test_current_streak_single_trade_loss(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test current streak with single losing trade.

        GIVEN: Trade log with single loss
        WHEN: calculate_current_streak() is called
        THEN: Returns (1, "LOSS")

        From: tasks.md T006 - Single trade (1) - loss variant
        """
        # GIVEN: Single losing trade
        trades = [
            _create_trade(symbol="AAPL", outcome="loss", profit_loss=Decimal("-30.00")),
        ]

        # WHEN: Calculate current streak
        streak_count, streak_type = metrics_calculator.calculate_current_streak(trades)

        # THEN: Should return 1 loss streak
        assert streak_count == 1, f"Expected streak count of 1, got {streak_count}"
        assert streak_type == "LOSS", f"Expected streak type 'LOSS', got '{streak_type}'"

    def test_current_streak_ignores_open_trades(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test that current streak ignores open trades at the end.

        GIVEN: Trade log with 2 wins, then 3 open trades
        WHEN: calculate_current_streak() is called
        THEN: Returns (2, "WIN") - open trades don't affect streak

        From: tasks.md T006 - Verify streak calculation logic
        """
        # GIVEN: 2 wins followed by 3 open trades
        trades = [
            _create_trade(symbol="AAPL", outcome="loss", profit_loss=Decimal("-20.00")),
            _create_trade(symbol="MSFT", outcome="win", profit_loss=Decimal("50.00")),
            _create_trade(symbol="TSLA", outcome="win", profit_loss=Decimal("60.00")),
            _create_trade(symbol="GOOGL", outcome="open", profit_loss=None),
            _create_trade(symbol="AMZN", outcome="open", profit_loss=None),
            _create_trade(symbol="NVDA", outcome="open", profit_loss=None),
        ]

        # WHEN: Calculate current streak
        streak_count, streak_type = metrics_calculator.calculate_current_streak(trades)

        # THEN: Should return 2 win streak (open trades ignored)
        assert streak_count == 2, f"Expected streak count of 2, got {streak_count}"
        assert streak_type == "WIN", f"Expected streak type 'WIN', got '{streak_type}'"


class TestMetricsCalculatorTotalPL:
    """T007 [RED]: Test total P&L aggregation."""

    @pytest.fixture
    def metrics_calculator(self) -> MetricsCalculator:
        """Create a MetricsCalculator instance for testing."""
        return MetricsCalculator()

    def test_total_pl_realized_only(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test total P&L with realized P&L only (no open positions).

        GIVEN: Trade log with 3 closed trades (realized P&L) and no open positions
        WHEN: calculate_total_pl() is called
        THEN: Returns realized_pl, unrealized_pl=0, total_pl=realized_pl

        From: tasks.md T007 - Realized P&L only (no positions)
        Pattern: Decimal comparison with quantize
        """
        # GIVEN: 3 closed trades with realized P&L
        trades = [
            _create_trade(symbol="AAPL", outcome="win", profit_loss=Decimal("50.00")),
            _create_trade(symbol="MSFT", outcome="loss", profit_loss=Decimal("-30.00")),
            _create_trade(symbol="TSLA", outcome="win", profit_loss=Decimal("70.00")),
        ]

        # No open positions
        positions: list[Position] = []

        # WHEN: Calculate total P&L
        realized_pl, unrealized_pl, total_pl = metrics_calculator.calculate_total_pl(
            trades=trades,
            positions=positions
        )

        # THEN: Should return realized P&L = 90.00, unrealized = 0, total = 90.00
        assert realized_pl == Decimal("90.00"), \
            f"Expected realized P&L of 90.00, got {realized_pl}"
        assert unrealized_pl == Decimal("0.00"), \
            f"Expected unrealized P&L of 0.00, got {unrealized_pl}"
        assert total_pl == Decimal("90.00"), \
            f"Expected total P&L of 90.00, got {total_pl}"

    def test_total_pl_unrealized_only(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test total P&L with unrealized P&L only (open positions, no closed trades).

        GIVEN: No closed trades and 2 open positions with unrealized P&L
        WHEN: calculate_total_pl() is called
        THEN: Returns realized_pl=0, unrealized_pl, total_pl=unrealized_pl

        From: tasks.md T007 - Unrealized P&L only (open positions, no closed trades)
        Mock: AccountData.get_positions() returns positions with P&L
        """
        # GIVEN: No closed trades
        trades: list[TradeRecord] = []

        # 2 open positions with unrealized P&L
        position1 = Position(
            symbol="AAPL",
            quantity=100,
            average_buy_price=Decimal("150.00"),
            current_price=Decimal("155.00"),
            last_updated=datetime.now(UTC)
        )
        # Unrealized P&L for position1 = (155 - 150) * 100 = 500

        position2 = Position(
            symbol="MSFT",
            quantity=50,
            average_buy_price=Decimal("300.00"),
            current_price=Decimal("295.00"),
            last_updated=datetime.now(UTC)
        )
        # Unrealized P&L for position2 = (295 - 300) * 50 = -250

        positions = [position1, position2]

        # WHEN: Calculate total P&L
        realized_pl, unrealized_pl, total_pl = metrics_calculator.calculate_total_pl(
            trades=trades,
            positions=positions
        )

        # THEN: Should return realized = 0, unrealized = 250.00, total = 250.00
        assert realized_pl == Decimal("0.00"), \
            f"Expected realized P&L of 0.00, got {realized_pl}"
        assert unrealized_pl == Decimal("250.00"), \
            f"Expected unrealized P&L of 250.00, got {unrealized_pl}"
        assert total_pl == Decimal("250.00"), \
            f"Expected total P&L of 250.00, got {total_pl}"

    def test_total_pl_combined(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test total P&L with both realized and unrealized P&L.

        GIVEN: Closed trades with realized P&L AND open positions with unrealized P&L
        WHEN: calculate_total_pl() is called
        THEN: Returns realized_pl, unrealized_pl, total_pl = realized + unrealized

        From: tasks.md T007 - Combined realized + unrealized
        """
        # GIVEN: Closed trades with realized P&L
        trades = [
            _create_trade(symbol="AAPL", outcome="win", profit_loss=Decimal("100.00")),
            _create_trade(symbol="MSFT", outcome="loss", profit_loss=Decimal("-50.00")),
        ]
        # Total realized = 50.00

        # Open positions with unrealized P&L
        position = Position(
            symbol="TSLA",
            quantity=25,
            average_buy_price=Decimal("200.00"),
            current_price=Decimal("210.00"),
            last_updated=datetime.now(UTC)
        )
        # Unrealized P&L = (210 - 200) * 25 = 250.00

        positions = [position]

        # WHEN: Calculate total P&L
        realized_pl, unrealized_pl, total_pl = metrics_calculator.calculate_total_pl(
            trades=trades,
            positions=positions
        )

        # THEN: Should return realized = 50.00, unrealized = 250.00, total = 300.00
        assert realized_pl == Decimal("50.00"), \
            f"Expected realized P&L of 50.00, got {realized_pl}"
        assert unrealized_pl == Decimal("250.00"), \
            f"Expected unrealized P&L of 250.00, got {unrealized_pl}"
        assert total_pl == Decimal("300.00"), \
            f"Expected total P&L of 300.00, got {total_pl}"

    def test_total_pl_decimal_precision_preserved(self, metrics_calculator: MetricsCalculator) -> None:
        """
        Test that total P&L calculation preserves decimal precision.

        GIVEN: Trades with precise decimal amounts (cents)
        WHEN: calculate_total_pl() is called
        THEN: Returns P&L values with exact decimal precision (no floating point errors)

        From: tasks.md T007 - Decimal precision preserved
        Pattern: Decimal comparison with quantize
        """
        # GIVEN: Trades with precise decimal amounts
        trades = [
            _create_trade(symbol="AAPL", outcome="win", profit_loss=Decimal("123.45")),
            _create_trade(symbol="MSFT", outcome="win", profit_loss=Decimal("67.89")),
            _create_trade(symbol="TSLA", outcome="loss", profit_loss=Decimal("-34.56")),
        ]
        # Total realized = 123.45 + 67.89 - 34.56 = 156.78

        positions: list[Position] = []

        # WHEN: Calculate total P&L
        realized_pl, unrealized_pl, total_pl = metrics_calculator.calculate_total_pl(
            trades=trades,
            positions=positions
        )

        # THEN: Should preserve exact decimal precision
        expected_realized = Decimal("156.78")
        assert realized_pl == expected_realized, \
            f"Expected realized P&L of {expected_realized}, got {realized_pl}"

        # Verify no floating point errors (e.g., 156.77999999)
        assert str(realized_pl) == "156.78", \
            f"Decimal precision not preserved: {str(realized_pl)}"
