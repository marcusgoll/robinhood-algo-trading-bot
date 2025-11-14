"""
Tests to verify conftest.py fixtures load correctly.

Validates that sample_strategies and sample_weights fixtures are available
and work properly for orchestrator testing.
"""

import pytest
from src.trading_bot.backtest.strategy_protocol import IStrategy


def test_sample_strategies_fixture_exists(sample_strategies):
    """Verify sample_strategies fixture provides 3 strategies."""
    assert len(sample_strategies) == 3, "Should provide exactly 3 test strategies"


def test_sample_strategies_implement_protocol(sample_strategies):
    """Verify all sample strategies implement IStrategy protocol."""
    for strategy in sample_strategies:
        assert isinstance(strategy, IStrategy), (
            f"Strategy {strategy.__class__.__name__} should implement IStrategy protocol"
        )


def test_sample_strategies_have_required_methods(sample_strategies):
    """Verify all sample strategies have should_enter and should_exit methods."""
    for strategy in sample_strategies:
        assert hasattr(strategy, 'should_enter'), (
            f"Strategy {strategy.__class__.__name__} should have should_enter method"
        )
        assert hasattr(strategy, 'should_exit'), (
            f"Strategy {strategy.__class__.__name__} should have should_exit method"
        )


def test_sample_weights_fixture_exists(sample_weights):
    """Verify sample_weights fixture provides allocation weights."""
    assert isinstance(sample_weights, dict), "sample_weights should be a dictionary"
    assert len(sample_weights) == 3, "Should provide exactly 3 weight allocations"


def test_sample_weights_sum_to_one(sample_weights):
    """Verify sample_weights allocations sum to 1.0 (100%)."""
    total = sum(sample_weights.values())
    assert abs(total - 1.0) < 1e-9, f"Weights should sum to 1.0, got {total}"


def test_sample_weights_all_positive(sample_weights):
    """Verify all sample_weights are positive values."""
    for strategy_id, weight in sample_weights.items():
        assert weight > 0, f"Weight for {strategy_id} should be positive, got {weight}"
        assert weight <= 1.0, f"Weight for {strategy_id} should be <= 1.0, got {weight}"


def test_sample_weights_keys_match_expected_format(sample_weights):
    """Verify sample_weights keys follow expected naming convention."""
    expected_keys = {"strategy1", "strategy2", "strategy3"}
    assert set(sample_weights.keys()) == expected_keys, (
        f"Expected keys {expected_keys}, got {set(sample_weights.keys())}"
    )
