"""
Performance tests for position plan calculation (T036).

Tests that position plan calculation with pullback analysis completes
within performance requirements:
- Position plan calculation (with pullback analysis) completes <200ms (NFR-001)

From: specs/stop-loss-automation/spec.md NFR-001, tasks.md T036
"""

import time
from decimal import Decimal

import pytest

from src.trading_bot.risk_management.calculator import calculate_position_plan


class TestPositionPlanPerformance:
    """Performance tests for position plan calculation."""

    def test_position_plan_calculation_performance(self):
        """
        Test position plan calculation completes in <200ms (T036, NFR-001).

        GIVEN: Realistic trading parameters (TSLA example from spec)
        WHEN: calculate_position_plan() called 100 times
        THEN: Average execution time is ≤200ms

        Test data:
        - symbol: TSLA
        - entry_price: $250.30
        - stop_price: $248.00 (pullback low, 2.30 point distance)
        - account_balance: $100,000
        - account_risk_pct: 1.0% (max $1,000 risk)
        - target_rr: 2.0 (2:1 risk-reward ratio)

        Expected results:
        - quantity: 434 shares
        - risk_amount: $1,000
        - target_price: $254.90
        - reward_ratio: ~2.0

        Performance target: ≤200ms average over 100 iterations
        """
        # Given: Realistic trading parameters
        symbol = "TSLA"
        entry_price = Decimal("250.30")
        stop_price = Decimal("248.00")
        account_balance = Decimal("100000.00")
        account_risk_pct = 1.0
        target_rr = 2.0

        # When: Run calculation 100 times and measure time
        iterations = 100
        total_time = 0.0

        for _ in range(iterations):
            start_time = time.perf_counter()

            position_plan = calculate_position_plan(
                symbol=symbol,
                entry_price=entry_price,
                stop_price=stop_price,
                target_rr=target_rr,
                account_balance=account_balance,
                risk_pct=account_risk_pct
            )

            end_time = time.perf_counter()
            total_time += (end_time - start_time)

            # Verify calculation is correct (sanity check)
            assert position_plan.symbol == symbol
            assert position_plan.quantity == 434
            assert position_plan.risk_amount == Decimal("1000.00")

        # Calculate average time in milliseconds
        avg_time_ms = (total_time / iterations) * 1000

        # Then: Average execution time is ≤200ms
        assert avg_time_ms <= 200, (
            f"Position plan calculation took {avg_time_ms:.2f}ms average "
            f"(target: ≤200ms, {iterations} iterations)"
        )

    def test_position_plan_with_edge_case_prices_performance(self):
        """
        Test performance with edge case prices (small position size).

        GIVEN: High entry price with tight stop (edge case scenario)
        WHEN: calculate_position_plan() called 100 times
        THEN: Average execution time is ≤200ms even with small position sizes

        Test data:
        - symbol: TSLA
        - entry_price: $1000.00 (high price)
        - stop_price: $993.00 (0.7% stop distance - minimum safe threshold)
        - account_balance: $100,000
        - account_risk_pct: 1.0%
        - target_rr: 2.0

        Performance target: ≤200ms average over 100 iterations
        """
        # Given: Edge case parameters (high price, tight stop)
        symbol = "TSLA"
        entry_price = Decimal("1000.00")
        stop_price = Decimal("993.00")  # 0.7% stop distance
        account_balance = Decimal("100000.00")
        account_risk_pct = 1.0
        target_rr = 2.0

        # When: Run calculation 100 times and measure time
        iterations = 100
        total_time = 0.0

        for _ in range(iterations):
            start_time = time.perf_counter()

            position_plan = calculate_position_plan(
                symbol=symbol,
                entry_price=entry_price,
                stop_price=stop_price,
                target_rr=target_rr,
                account_balance=account_balance,
                risk_pct=account_risk_pct
            )

            end_time = time.perf_counter()
            total_time += (end_time - start_time)

            # Verify calculation is correct (sanity check)
            assert position_plan.symbol == symbol
            assert position_plan.entry_price == entry_price
            assert position_plan.stop_price == stop_price

        # Calculate average time in milliseconds
        avg_time_ms = (total_time / iterations) * 1000

        # Then: Average execution time is ≤200ms
        assert avg_time_ms <= 200, (
            f"Position plan calculation took {avg_time_ms:.2f}ms average "
            f"for edge case prices (target: ≤200ms, {iterations} iterations)"
        )

    def test_position_plan_with_large_account_performance(self):
        """
        Test performance with large account balance.

        GIVEN: Large account balance ($1M) with proportional position sizing
        WHEN: calculate_position_plan() called 100 times
        THEN: Average execution time is ≤200ms even with large numbers

        Test data:
        - symbol: SPY
        - entry_price: $450.00
        - stop_price: $445.50 (1% stop distance)
        - account_balance: $1,000,000
        - account_risk_pct: 1.0%
        - target_rr: 2.0

        Expected:
        - Risk amount: $10,000
        - Position size: ~2,222 shares

        Performance target: ≤200ms average over 100 iterations
        """
        # Given: Large account parameters
        symbol = "SPY"
        entry_price = Decimal("450.00")
        stop_price = Decimal("445.50")  # 1% stop
        account_balance = Decimal("1000000.00")  # $1M account
        account_risk_pct = 1.0
        target_rr = 2.0

        # When: Run calculation 100 times and measure time
        iterations = 100
        total_time = 0.0

        for _ in range(iterations):
            start_time = time.perf_counter()

            position_plan = calculate_position_plan(
                symbol=symbol,
                entry_price=entry_price,
                stop_price=stop_price,
                target_rr=target_rr,
                account_balance=account_balance,
                risk_pct=account_risk_pct
            )

            end_time = time.perf_counter()
            total_time += (end_time - start_time)

            # Verify calculation is correct (sanity check)
            assert position_plan.symbol == symbol
            assert position_plan.risk_amount == Decimal("10000.00")
            assert position_plan.quantity == 2222  # 10000 / 4.50

        # Calculate average time in milliseconds
        avg_time_ms = (total_time / iterations) * 1000

        # Then: Average execution time is ≤200ms
        assert avg_time_ms <= 200, (
            f"Position plan calculation took {avg_time_ms:.2f}ms average "
            f"for large account balance (target: ≤200ms, {iterations} iterations)"
        )
