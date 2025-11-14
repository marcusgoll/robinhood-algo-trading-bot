"""Tests for TradeLimiter (daily trade limit enforcement).

Tasks: T070-T071 (RED phase)
Tests verify:
- Phase-specific limits (PoC: 1/day, others: unlimited)
- Daily counter state management
- TradeLimitExceeded exception with countdown
- Daily reset at market open
"""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest

from trading_bot.config import Config
from trading_bot.phase.models import Phase
from trading_bot.phase.trade_limiter import TradeLimiter, TradeLimitExceeded


@pytest.fixture
def config():
    """Create test configuration."""
    return Config(
        robinhood_username="test",
        robinhood_password="test",
        current_phase="experience"
    )


@pytest.fixture
def limiter(config):
    """Create TradeLimiter instance."""
    return TradeLimiter(config)


class TestTradeLimitChecks:
    """Test check_limit() for phase-specific limits."""

    def test_poc_first_trade_allowed(self, limiter):
        """PoC phase: First trade of the day should pass."""
        trade_date = date(2025, 1, 15)

        # Should not raise exception
        limiter.check_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        # Counter should be incremented
        assert limiter._trade_counts[trade_date] == 1

    def test_poc_second_trade_blocked(self, limiter):
        """PoC phase: Second trade of the day should raise TradeLimitExceeded."""
        trade_date = date(2025, 1, 15)

        # First trade passes
        limiter.check_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        # Second trade should fail
        with pytest.raises(TradeLimitExceeded) as exc_info:
            limiter.check_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        # Verify exception details
        exc = exc_info.value
        assert exc.phase == Phase.PROOF_OF_CONCEPT
        assert exc.limit == 1
        assert exc.next_allowed.date() == trade_date + timedelta(days=1)
        assert exc.next_allowed.time() == time(7, 0)  # 7:00 AM market open

    def test_experience_phase_unlimited(self, limiter):
        """Experience phase: No trade limit enforced."""
        trade_date = date(2025, 1, 15)

        # Execute 5 trades - all should pass
        for _ in range(5):
            limiter.check_limit(Phase.EXPERIENCE, trade_date)

        # No counter should be tracked for unlimited phases
        assert trade_date not in limiter._trade_counts

    def test_trial_phase_unlimited(self, limiter):
        """Real Money Trial phase: No trade limit enforced."""
        trade_date = date(2025, 1, 15)

        # Execute 5 trades - all should pass
        for _ in range(5):
            limiter.check_limit(Phase.REAL_MONEY_TRIAL, trade_date)

        # No counter should be tracked for unlimited phases
        assert trade_date not in limiter._trade_counts

    def test_scaling_phase_unlimited(self, limiter):
        """Scaling phase: No trade limit enforced."""
        trade_date = date(2025, 1, 15)

        # Execute 5 trades - all should pass
        for _ in range(5):
            limiter.check_limit(Phase.SCALING, trade_date)

        # No counter should be tracked for unlimited phases
        assert trade_date not in limiter._trade_counts

    def test_multiple_days_independent(self, limiter):
        """PoC phase: Each day has independent counter."""
        day1 = date(2025, 1, 15)
        day2 = date(2025, 1, 16)

        # Day 1: First trade passes
        limiter.check_limit(Phase.PROOF_OF_CONCEPT, day1)
        assert limiter._trade_counts[day1] == 1

        # Day 2: First trade passes (independent counter)
        limiter.check_limit(Phase.PROOF_OF_CONCEPT, day2)
        assert limiter._trade_counts[day2] == 1

        # Day 1: Second trade blocked
        with pytest.raises(TradeLimitExceeded):
            limiter.check_limit(Phase.PROOF_OF_CONCEPT, day1)

        # Day 2: Second trade blocked
        with pytest.raises(TradeLimitExceeded):
            limiter.check_limit(Phase.PROOF_OF_CONCEPT, day2)


class TestDailyReset:
    """Test reset_daily_counter() for memory management."""

    def test_reset_clears_old_dates(self, limiter):
        """Old date counters should be removed."""
        day1 = date(2025, 1, 10)
        day2 = date(2025, 1, 11)
        current = date(2025, 1, 15)

        # Simulate trades on old dates
        limiter.check_limit(Phase.PROOF_OF_CONCEPT, day1)
        limiter.check_limit(Phase.PROOF_OF_CONCEPT, day2)
        assert len(limiter._trade_counts) == 2

        # Reset to current date
        limiter.reset_daily_counter(current)

        # Old dates should be removed
        assert day1 not in limiter._trade_counts
        assert day2 not in limiter._trade_counts
        assert len(limiter._trade_counts) == 0

    def test_reset_keeps_current_date(self, limiter):
        """Current date counter should be preserved."""
        current = date(2025, 1, 15)

        # Trade on current date
        limiter.check_limit(Phase.PROOF_OF_CONCEPT, current)

        # Reset should keep current date
        limiter.reset_daily_counter(current)

        assert current in limiter._trade_counts
        assert limiter._trade_counts[current] == 1

    def test_reset_keeps_future_dates(self, limiter):
        """Future date counters should be preserved."""
        current = date(2025, 1, 15)
        future = date(2025, 1, 16)

        # Trade on future date (edge case)
        limiter.check_limit(Phase.PROOF_OF_CONCEPT, future)

        # Reset should keep future date
        limiter.reset_daily_counter(current)

        assert future in limiter._trade_counts
        assert limiter._trade_counts[future] == 1

    def test_reset_empty_state(self, limiter):
        """Reset on empty state should not error."""
        current = date(2025, 1, 15)

        # Reset with no trades
        limiter.reset_daily_counter(current)

        # Should be no-op
        assert len(limiter._trade_counts) == 0


class TestTradeLimitExceededException:
    """Test TradeLimitExceeded exception details."""

    def test_exception_message_format(self, limiter):
        """Exception message should include phase, limit, and next allowed time."""
        trade_date = date(2025, 1, 15)

        # Trigger limit
        limiter.check_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        with pytest.raises(TradeLimitExceeded) as exc_info:
            limiter.check_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        error_msg = str(exc_info.value)
        assert "Trade limit exceeded" in error_msg
        assert "1 trade(s) allowed" in error_msg
        assert "proof phase" in error_msg
        assert "Next trade at:" in error_msg

    def test_exception_next_allowed_calculation(self, limiter):
        """Next allowed time should be 7:00 AM UTC next day."""
        trade_date = date(2025, 1, 15)

        # Trigger limit
        limiter.check_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        with pytest.raises(TradeLimitExceeded) as exc_info:
            limiter.check_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        next_allowed = exc_info.value.next_allowed
        expected = datetime(2025, 1, 16, 7, 0, 0, tzinfo=timezone.utc)

        assert next_allowed == expected

    def test_exception_attributes(self, limiter):
        """Exception should have phase, limit, and next_allowed attributes."""
        trade_date = date(2025, 1, 15)

        # Trigger limit
        limiter.check_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        with pytest.raises(TradeLimitExceeded) as exc_info:
            limiter.check_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        exc = exc_info.value
        assert hasattr(exc, 'phase')
        assert hasattr(exc, 'limit')
        assert hasattr(exc, 'next_allowed')
        assert exc.phase == Phase.PROOF_OF_CONCEPT
        assert exc.limit == 1
        assert isinstance(exc.next_allowed, datetime)


class TestGetNextAllowedTrade:
    """Test get_next_allowed_trade() countdown logic."""

    def test_no_limit_returns_none(self, limiter):
        """Unlimited phases should return None (no countdown needed)."""
        trade_date = date(2025, 1, 15)

        # Experience phase (unlimited)
        next_allowed = limiter.get_next_allowed_trade(Phase.EXPERIENCE, trade_date)
        assert next_allowed is None

    def test_poc_under_limit_returns_none(self, limiter):
        """PoC phase under limit should return None."""
        trade_date = date(2025, 1, 15)

        # No trades yet
        next_allowed = limiter.get_next_allowed_trade(Phase.PROOF_OF_CONCEPT, trade_date)
        assert next_allowed is None

    def test_poc_at_limit_returns_next_day(self, limiter):
        """PoC phase at limit should return next day 7:00 AM."""
        trade_date = date(2025, 1, 15)

        # Execute one trade (hit limit)
        limiter.check_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        # Should return next day countdown
        next_allowed = limiter.get_next_allowed_trade(Phase.PROOF_OF_CONCEPT, trade_date)
        expected = datetime(2025, 1, 16, 7, 0, 0, tzinfo=timezone.utc)

        assert next_allowed == expected
