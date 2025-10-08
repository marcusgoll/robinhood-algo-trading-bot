"""Tests for retry policy configuration"""

import pytest


def test_retry_policy_dataclass_with_defaults():
    """RetryPolicy should have sensible defaults for retry behavior."""
    from trading_bot.error_handling import RetryPolicy, RetriableError

    # Given: A RetryPolicy with default values
    policy = RetryPolicy()

    # Then: Default values should be set
    assert policy.max_attempts == 3
    assert policy.base_delay == 1.0
    assert policy.backoff_multiplier == 2.0
    assert policy.jitter is True
    assert policy.retriable_exceptions == (RetriableError,)


def test_retry_policy_validates_max_attempts_positive():
    """RetryPolicy should validate that max_attempts is > 0."""
    from trading_bot.error_handling import RetryPolicy

    # Given/When: Attempting to create policy with invalid max_attempts
    # Then: Should raise ValueError
    with pytest.raises(ValueError, match="max_attempts must be greater than 0"):
        RetryPolicy(max_attempts=0)

    with pytest.raises(ValueError, match="max_attempts must be greater than 0"):
        RetryPolicy(max_attempts=-1)


def test_predefined_policies_exist():
    """Framework should provide predefined retry policies."""
    from trading_bot.error_handling import (
        DEFAULT_POLICY,
        AGGRESSIVE_POLICY,
        CONSERVATIVE_POLICY,
        RetryPolicy,
    )

    # Then: Predefined policies should exist and be configured correctly
    assert isinstance(DEFAULT_POLICY, RetryPolicy)
    assert DEFAULT_POLICY.max_attempts == 3
    assert DEFAULT_POLICY.base_delay == 1.0
    assert DEFAULT_POLICY.backoff_multiplier == 2.0
    assert DEFAULT_POLICY.jitter is True

    assert isinstance(AGGRESSIVE_POLICY, RetryPolicy)
    assert AGGRESSIVE_POLICY.max_attempts == 5

    assert isinstance(CONSERVATIVE_POLICY, RetryPolicy)
    assert CONSERVATIVE_POLICY.max_attempts == 1
    assert CONSERVATIVE_POLICY.jitter is False
