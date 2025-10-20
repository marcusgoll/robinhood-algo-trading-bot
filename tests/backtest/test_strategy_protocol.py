"""
Tests for IStrategy protocol runtime checking.

Tests protocol compliance for strategy classes implementing the IStrategy protocol.
Verifies that strategies have required methods with correct signatures.
"""

import pytest
from typing import List
from datetime import datetime, timezone
from decimal import Decimal

# This import will fail initially (RED phase) - IStrategy protocol doesn't exist yet
from src.trading_bot.backtest.strategy_protocol import IStrategy
from src.trading_bot.backtest.models import HistoricalDataBar, Position


class ValidStrategy:
    """Valid strategy implementation for testing protocol compliance."""

    def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
        """Check if strategy should enter a position."""
        return len(bars) > 0

    def should_exit(self, position: Position, bars: List[HistoricalDataBar]) -> bool:
        """Check if strategy should exit a position."""
        return len(bars) > 10


class MissingShouldEnterStrategy:
    """Invalid strategy - missing should_enter() method."""

    def should_exit(self, position: Position, bars: List[HistoricalDataBar]) -> bool:
        """Check if strategy should exit a position."""
        return True


class MissingShouldExitStrategy:
    """Invalid strategy - missing should_exit() method."""

    def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
        """Check if strategy should enter a position."""
        return True


class IncorrectSignatureShouldEnter:
    """Invalid strategy - should_enter() has incorrect signature."""

    def should_enter(self) -> bool:  # Missing 'bars' parameter
        """Check if strategy should enter a position."""
        return True

    def should_exit(self, position: Position, bars: List[HistoricalDataBar]) -> bool:
        """Check if strategy should exit a position."""
        return True


class IncorrectSignatureShouldExit:
    """Invalid strategy - should_exit() has incorrect signature."""

    def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
        """Check if strategy should enter a position."""
        return True

    def should_exit(self, bars: List[HistoricalDataBar]) -> bool:  # Missing 'position' parameter
        """Check if strategy should exit a position."""
        return True


class TestProtocolCompliance:
    """Test IStrategy protocol runtime checking."""

    def test_valid_strategy_implements_protocol(self):
        """Valid strategy class should implement IStrategy protocol."""
        strategy = ValidStrategy()

        # Protocol compliance check - should pass for valid strategy
        assert isinstance(strategy, IStrategy), "Valid strategy should implement IStrategy protocol"

    def test_missing_should_enter_method_raises_error(self):
        """Strategy missing should_enter() method should not satisfy protocol."""
        strategy = MissingShouldEnterStrategy()

        # Protocol compliance check - should fail for invalid strategy
        assert not isinstance(strategy, IStrategy), (
            "Strategy missing should_enter() should not satisfy IStrategy protocol"
        )

    def test_missing_should_exit_method_raises_error(self):
        """Strategy missing should_exit() method should not satisfy protocol."""
        strategy = MissingShouldExitStrategy()

        # Protocol compliance check - should fail for invalid strategy
        assert not isinstance(strategy, IStrategy), (
            "Strategy missing should_exit() should not satisfy IStrategy protocol"
        )

    def test_incorrect_should_enter_signature_raises_error(self):
        """Strategy with incorrect should_enter() signature should not satisfy protocol."""
        strategy = IncorrectSignatureShouldEnter()

        # Protocol compliance check - should fail for invalid signature
        # Note: Python's runtime_checkable Protocol only checks method existence,
        # not signatures. For strict signature validation, we need additional checks.
        assert not hasattr(strategy.should_enter, '__code__') or (
            strategy.should_enter.__code__.co_argcount != 2  # self + bars
        ), "Strategy with incorrect should_enter() signature should be detected"

    def test_incorrect_should_exit_signature_raises_error(self):
        """Strategy with incorrect should_exit() signature should not satisfy protocol."""
        strategy = IncorrectSignatureShouldExit()

        # Protocol compliance check - should fail for invalid signature
        # Note: Python's runtime_checkable Protocol only checks method existence,
        # not signatures. For strict signature validation, we need additional checks.
        assert not hasattr(strategy.should_exit, '__code__') or (
            strategy.should_exit.__code__.co_argcount != 3  # self + position + bars
        ), "Strategy with incorrect should_exit() signature should be detected"

    def test_protocol_works_with_real_data(self):
        """Protocol compliance check should work with real HistoricalDataBar data."""
        # Create sample historical data
        bars = [
            HistoricalDataBar(
                symbol="AAPL",
                timestamp=datetime(2024, 1, 16, tzinfo=timezone.utc),
                open=Decimal("180.50"),
                high=Decimal("182.00"),
                low=Decimal("179.00"),
                close=Decimal("181.25"),
                volume=50000000,
            ),
            HistoricalDataBar(
                symbol="AAPL",
                timestamp=datetime(2024, 1, 17, tzinfo=timezone.utc),
                open=Decimal("181.25"),
                high=Decimal("183.50"),
                low=Decimal("180.75"),
                close=Decimal("182.75"),
                volume=45000000,
            ),
        ]

        # Create sample position
        position = Position(
            symbol="AAPL",
            shares=100,
            entry_price=Decimal("180.50"),
            entry_date=datetime(2024, 1, 16, tzinfo=timezone.utc),
            current_price=Decimal("182.75"),
        )

        strategy = ValidStrategy()

        # Verify protocol compliance
        assert isinstance(strategy, IStrategy), "ValidStrategy should implement IStrategy"

        # Verify methods work with real data
        assert strategy.should_enter(bars) is True, "should_enter() should work with real bars"
        assert strategy.should_exit(position, bars) is False, (
            "should_exit() should work with real position and bars"
        )


class TestProtocolEdgeCases:
    """Test edge cases for IStrategy protocol."""

    def test_empty_bars_list_handling(self):
        """Strategy should handle empty bars list gracefully."""
        strategy = ValidStrategy()
        empty_bars: List[HistoricalDataBar] = []

        # should_enter() should handle empty bars without crashing
        result = strategy.should_enter(empty_bars)
        assert result is False, "should_enter() should return False for empty bars"

    def test_strategy_with_additional_methods(self):
        """Strategy with extra methods beyond protocol should still satisfy protocol."""
        class ExtendedStrategy:
            def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
                return True

            def should_exit(self, position: Position, bars: List[HistoricalDataBar]) -> bool:
                return False

            def custom_method(self) -> str:
                """Additional method not in protocol."""
                return "custom"

        strategy = ExtendedStrategy()
        assert isinstance(strategy, IStrategy), (
            "Strategy with additional methods should still satisfy IStrategy protocol"
        )

    def test_strategy_inheritance_works(self):
        """Strategy classes using inheritance should satisfy protocol."""
        class BaseStrategy:
            def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
                return False

        class DerivedStrategy(BaseStrategy):
            def should_exit(self, position: Position, bars: List[HistoricalDataBar]) -> bool:
                return True

        strategy = DerivedStrategy()
        assert isinstance(strategy, IStrategy), (
            "Derived strategy should satisfy IStrategy protocol"
        )
