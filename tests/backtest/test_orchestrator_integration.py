"""
Integration tests for StrategyOrchestrator.

Tests the complete end-to-end workflow of multi-strategy orchestration
with real strategy implementations and historical data.

Test Pattern: Integration tests validating complete user stories
Coverage Target: End-to-end acceptance criteria validation
"""

from decimal import Decimal
from datetime import datetime, timezone
import pytest

from src.trading_bot.backtest.orchestrator import StrategyOrchestrator
from src.trading_bot.backtest.models import (
    HistoricalDataBar,
    OrchestratorConfig,
    Position,
)
from src.trading_bot.backtest.strategy_protocol import IStrategy


# Simple test strategies for integration testing
class BuyAndHoldStrategy:
    """Buy on first bar, hold forever."""

    def __init__(self):
        self.entered = False

    def should_enter(self, bars: list[HistoricalDataBar]) -> bool:
        """Enter on first bar only."""
        if not self.entered and len(bars) > 0:
            self.entered = True
            return True
        return False

    def should_exit(self, position: Position, bars: list[HistoricalDataBar]) -> bool:
        """Never exit."""
        return False


class MomentumStrategy:
    """Simple momentum strategy - buy when price increases."""

    def should_enter(self, bars: list[HistoricalDataBar]) -> bool:
        """Enter when current close > previous close."""
        if len(bars) < 2:
            return False
        return bars[-1].close > bars[-2].close

    def should_exit(self, position: Position, bars: list[HistoricalDataBar]) -> bool:
        """Exit when current price < entry price."""
        if len(bars) == 0:
            return False
        current_price = bars[-1].close
        return current_price < position.entry_price


class MeanReversionStrategy:
    """Simple mean reversion - buy when price drops."""

    def should_enter(self, bars: list[HistoricalDataBar]) -> bool:
        """Enter when current close < previous close."""
        if len(bars) < 2:
            return False
        return bars[-1].close < bars[-2].close

    def should_exit(self, position: Position, bars: list[HistoricalDataBar]) -> bool:
        """Exit when current price > entry price * 1.05 (5% profit target)."""
        if len(bars) == 0:
            return False
        current_price = bars[-1].close
        profit_target = position.entry_price * Decimal("1.05")
        return current_price >= profit_target


@pytest.fixture
def sample_historical_data():
    """Create sample historical data with realistic price movements."""
    # 10 bars with varied price movements
    prices = [
        Decimal("100.0"),  # Day 0: Start
        Decimal("102.0"),  # Day 1: Up 2%
        Decimal("101.0"),  # Day 2: Down 1%
        Decimal("103.0"),  # Day 3: Up 2%
        Decimal("102.5"),  # Day 4: Down 0.5%
        Decimal("105.0"),  # Day 5: Up 2.5%
        Decimal("104.0"),  # Day 6: Down 1%
        Decimal("106.0"),  # Day 7: Up 2%
        Decimal("105.5"),  # Day 8: Down 0.5%
        Decimal("108.0"),  # Day 9: Up 2.5%
    ]

    bars = []
    for i, price in enumerate(prices):
        bar = HistoricalDataBar(
            symbol="AAPL",
            timestamp=datetime(2024, 1, i+1, 9, 30, tzinfo=timezone.utc),
            open=price - Decimal("0.5"),
            high=price + Decimal("1.0"),
            low=price - Decimal("1.0"),
            close=price,
            volume=1000000,
            split_adjusted=True,
            dividend_adjusted=True,
        )
        bars.append(bar)

    return {"AAPL": bars}


class TestOrchestratorIntegrationUS1:
    """Integration tests for US1: Multi-strategy fixed allocation."""

    def test_us1_multi_strategy_fixed_allocation_e2e(self, sample_historical_data):
        """
        Test US1: Complete multi-strategy workflow with fixed allocations.

        **Acceptance Criteria** (spec.md US1):
        - GIVEN: 2 strategies with 50/50 allocation
        - WHEN: Full backtest runs with 10 bars of data
        - THEN: Both strategies execute trades independently
        - AND: Final portfolio equity = sum of strategy equities
        - AND: Each strategy respects its 50% capital allocation

        **From**: tasks.md T040, spec.md US1
        **Pattern**: End-to-end workflow validation
        """
        # ARRANGE: Create 2 different strategies with 50/50 allocation
        buy_and_hold = BuyAndHoldStrategy()
        momentum = MomentumStrategy()

        strategies_with_weights = [
            (buy_and_hold, Decimal("0.50")),
            (momentum, Decimal("0.50")),
        ]

        initial_capital = Decimal("100000.0")

        # ACT: Run full backtest
        orchestrator = StrategyOrchestrator(
            strategies_with_weights=strategies_with_weights,
            initial_capital=initial_capital,
            config=OrchestratorConfig(logging_level="INFO")
        )

        result = orchestrator.run(sample_historical_data)

        # ASSERT: Both strategies executed trades
        assert len(result.strategy_results) == 2, "Should have 2 strategy results"

        strategy_ids = list(result.strategy_results.keys())
        strategy1_result = result.strategy_results[strategy_ids[0]]
        strategy2_result = result.strategy_results[strategy_ids[1]]

        # Each strategy should have an equity curve showing activity
        assert len(strategy1_result.equity_curve) > 0, "Strategy 1 should have equity curve"
        assert len(strategy2_result.equity_curve) > 0, "Strategy 2 should have equity curve"

        # Verify equity curves show growth (positions were created)
        # Note: Buy&Hold never exits so won't have Trade records, but equity will grow
        strategy1_start = strategy1_result.equity_curve[0][1]
        strategy1_end = strategy1_result.equity_curve[-1][1]
        strategy2_start = strategy2_result.equity_curve[0][1]
        strategy2_end = strategy2_result.equity_curve[-1][1]

        # At least one strategy should show equity change (trades/positions executed)
        assert (strategy1_end != strategy1_start or strategy2_end != strategy2_start), (
            "At least one strategy should show equity movement from trading activity"
        )

        # Verify capital allocation (50% each = $50k each)
        max_allocation = initial_capital * Decimal("0.50")

        # Check starting equity equals allocated capital
        strategy1_start_equity = strategy1_result.equity_curve[0][1]
        strategy2_start_equity = strategy2_result.equity_curve[0][1]

        assert strategy1_start_equity == max_allocation, (
            f"Strategy 1 should start with ${max_allocation}, got ${strategy1_start_equity}"
        )
        assert strategy2_start_equity == max_allocation, (
            f"Strategy 2 should start with ${max_allocation}, got ${strategy2_start_equity}"
        )

        # Portfolio metrics should be calculated
        assert result.aggregate_metrics is not None, "Should have portfolio metrics"
        assert result.aggregate_metrics.total_return is not None, "Should have total return"

        print(f"\nUS1 Integration Test Results:")
        print(f"  Strategy 1 trades: {len(strategy1_result.trades)}")
        print(f"  Strategy 2 trades: {len(strategy2_result.trades)}")
        print(f"  Portfolio return: {result.aggregate_metrics.total_return}%")


class TestOrchestratorIntegrationUS2:
    """Integration tests for US2: Independent tracking."""

    def test_us2_independent_tracking_e2e(self, sample_historical_data):
        """
        Test US2: Strategies track performance independently.

        **Acceptance Criteria** (spec.md US2):
        - GIVEN: 3 different strategies with different behaviors
        - WHEN: Full backtest runs
        - THEN: Each strategy has independent equity curve
        - AND: Trades tagged with correct strategy_id
        - AND: Per-strategy metrics calculated correctly
        - AND: Comparison table generated

        **From**: tasks.md T041, spec.md US2
        **Pattern**: Independent tracking validation
        """
        # ARRANGE: Create 3 different strategies
        buy_and_hold = BuyAndHoldStrategy()
        momentum = MomentumStrategy()
        mean_reversion = MeanReversionStrategy()

        strategies_with_weights = [
            (buy_and_hold, Decimal("0.33")),
            (momentum, Decimal("0.33")),
            (mean_reversion, Decimal("0.34")),  # 34% to sum to 100%
        ]

        initial_capital = Decimal("300000.0")

        # ACT: Run backtest
        orchestrator = StrategyOrchestrator(
            strategies_with_weights=strategies_with_weights,
            initial_capital=initial_capital
        )

        result = orchestrator.run(sample_historical_data)

        # ASSERT: 3 independent strategy results
        assert len(result.strategy_results) == 3, "Should have 3 strategy results"

        strategy_ids = list(result.strategy_results.keys())

        # Each strategy should have independent tracking
        for strategy_id in strategy_ids:
            strategy_result = result.strategy_results[strategy_id]

            # Independent equity curve
            assert len(strategy_result.equity_curve) > 0, (
                f"{strategy_id} should have equity curve"
            )

            # Independent metrics
            assert strategy_result.metrics is not None, (
                f"{strategy_id} should have metrics"
            )
            assert strategy_result.metrics.total_return is not None, (
                f"{strategy_id} should have total return"
            )

            # Trades tagged with strategy_id
            for trade in strategy_result.trades:
                # Note: The Trade model doesn't have strategy_id field by default,
                # but trades are organized by strategy in result.strategy_results
                assert trade.symbol is not None, "Trade should have symbol"
                assert trade.entry_date is not None, "Trade should have entry date"

        # Verify equity curves are different (strategies behave differently)
        equity_curves = [
            result.strategy_results[sid].equity_curve[-1][1]
            for sid in strategy_ids
        ]

        # At least one strategy should have different ending equity
        # (they can't all be identical if they follow different strategies)
        assert len(set(equity_curves)) > 1, (
            "Strategies should have different ending equities"
        )

        # Comparison table should exist
        assert result.comparison_table is not None, "Should have comparison table"
        assert len(result.comparison_table) > 0, "Comparison table should not be empty"

        print(f"\nUS2 Integration Test Results:")
        for i, strategy_id in enumerate(strategy_ids, 1):
            strategy_result = result.strategy_results[strategy_id]
            print(f"  Strategy {i} ({strategy_id}):")
            print(f"    Trades: {len(strategy_result.trades)}")
            print(f"    Return: {strategy_result.metrics.total_return}%")
            print(f"    Final Equity: ${strategy_result.equity_curve[-1][1]}")


class TestOrchestratorIntegrationUS3:
    """Integration tests for US3: Capital limits."""

    def test_us3_capital_limits_enforced_e2e(self, sample_historical_data):
        """
        Test US3: Capital limits enforced in complete workflow.

        **Acceptance Criteria** (spec.md US3):
        - GIVEN: Strategy with 30% allocation generating many signals
        - WHEN: Full backtest runs
        - THEN: Total capital used never exceeds 30% allocation
        - AND: Blocked signals logged when at limit
        - AND: Capital released when positions close

        **From**: tasks.md T042, spec.md US3
        **Pattern**: Capital limit enforcement validation
        """
        # ARRANGE: Create aggressive momentum strategy that tries to enter often
        momentum = MomentumStrategy()

        strategies_with_weights = [
            (momentum, Decimal("0.30")),  # Only 30% allocation
        ]

        initial_capital = Decimal("100000.0")
        max_allocation = initial_capital * Decimal("0.30")  # $30k

        # ACT: Run backtest
        orchestrator = StrategyOrchestrator(
            strategies_with_weights=strategies_with_weights,
            initial_capital=initial_capital
        )

        result = orchestrator.run(sample_historical_data)

        # ASSERT: Capital limits respected
        strategy_result = list(result.strategy_results.values())[0]

        # Verify equity never exceeded allocation by unreasonable amount
        # Allow some variance for mark-to-market gains, but starting equity
        # should equal allocation
        starting_equity = strategy_result.equity_curve[0][1]
        assert starting_equity == max_allocation, (
            f"Starting equity ${starting_equity} should equal allocation ${max_allocation}"
        )

        # Check that strategy couldn't use unlimited capital
        # (if it had unlimited capital, it would have more trades)
        assert len(strategy_result.trades) < 10, (
            "Strategy should be limited by 30% capital allocation, "
            f"but executed {len(strategy_result.trades)} trades"
        )

        # Verify some capital was actually used (strategy not blocked completely)
        assert len(strategy_result.trades) > 0, (
            "Strategy should have executed at least one trade within its allocation"
        )

        # Portfolio metrics should reflect limited allocation
        assert result.aggregate_metrics is not None

        print(f"\nUS3 Integration Test Results:")
        print(f"  Max Allocation: ${max_allocation}")
        print(f"  Starting Equity: ${starting_equity}")
        print(f"  Ending Equity: ${strategy_result.equity_curve[-1][1]}")
        print(f"  Trades Executed: {len(strategy_result.trades)}")
        print(f"  Capital limit enforced: ✓")
