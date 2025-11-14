"""Unit tests for Telegram middleware (auth and rate limiting)."""

import time
from unittest.mock import patch

import pytest

from trading_bot.telegram.middleware import CommandAuthMiddleware, CommandRateLimiter


# CommandAuthMiddleware Tests


def test_auth_middleware_initialization_with_users():
    """Test auth middleware initializes with provided user IDs."""
    # Arrange
    authorized_users = {123456, 789012}

    # Act
    middleware = CommandAuthMiddleware(authorized_user_ids=authorized_users)

    # Assert
    assert middleware.authorized_user_ids == authorized_users


def test_auth_middleware_initialization_from_env():
    """Test auth middleware loads user IDs from environment."""
    # Arrange
    with patch.dict("os.environ", {"TELEGRAM_AUTHORIZED_USER_IDS": "111,222,333"}):
        # Act
        middleware = CommandAuthMiddleware()

    # Assert
    assert middleware.authorized_user_ids == {111, 222, 333}


def test_auth_middleware_initialization_empty_env():
    """Test auth middleware handles empty environment variable."""
    # Arrange
    with patch.dict("os.environ", {"TELEGRAM_AUTHORIZED_USER_IDS": ""}):
        # Act
        middleware = CommandAuthMiddleware()

    # Assert
    assert middleware.authorized_user_ids == set()


def test_auth_middleware_is_authorized_valid_user():
    """Test is_authorized returns True for authorized user."""
    # Arrange
    middleware = CommandAuthMiddleware(authorized_user_ids={123456})

    # Act
    result = middleware.is_authorized(123456)

    # Assert
    assert result is True


def test_auth_middleware_is_authorized_invalid_user():
    """Test is_authorized returns False for unauthorized user."""
    # Arrange
    middleware = CommandAuthMiddleware(authorized_user_ids={123456})

    # Act
    result = middleware.is_authorized(999999)

    # Assert
    assert result is False


def test_auth_middleware_add_authorized_user():
    """Test adding user to authorized list."""
    # Arrange
    middleware = CommandAuthMiddleware(authorized_user_ids={123456})

    # Act
    middleware.add_authorized_user(789012)

    # Assert
    assert middleware.is_authorized(789012) is True
    assert middleware.is_authorized(123456) is True


def test_auth_middleware_remove_authorized_user():
    """Test removing user from authorized list."""
    # Arrange
    middleware = CommandAuthMiddleware(authorized_user_ids={123456, 789012})

    # Act
    middleware.remove_authorized_user(789012)

    # Assert
    assert middleware.is_authorized(789012) is False
    assert middleware.is_authorized(123456) is True


def test_auth_middleware_remove_nonexistent_user():
    """Test removing non-existent user doesn't raise error."""
    # Arrange
    middleware = CommandAuthMiddleware(authorized_user_ids={123456})

    # Act & Assert - should not raise
    middleware.remove_authorized_user(999999)


# CommandRateLimiter Tests


def test_rate_limiter_initialization_with_cooldown():
    """Test rate limiter initializes with provided cooldown."""
    # Arrange & Act
    limiter = CommandRateLimiter(cooldown_seconds=10.0)

    # Assert
    assert limiter.cooldown_seconds == 10.0


def test_rate_limiter_initialization_from_env():
    """Test rate limiter loads cooldown from environment."""
    # Arrange
    with patch.dict("os.environ", {"TELEGRAM_COMMAND_COOLDOWN_SECONDS": "15.0"}):
        # Act
        limiter = CommandRateLimiter()

    # Assert
    assert limiter.cooldown_seconds == 15.0


def test_rate_limiter_initialization_default():
    """Test rate limiter uses default cooldown when env not set."""
    # Arrange
    with patch.dict("os.environ", {}, clear=True):
        # Act
        limiter = CommandRateLimiter()

    # Assert
    assert limiter.cooldown_seconds == 5.0


def test_rate_limiter_is_allowed_first_command():
    """Test first command is always allowed."""
    # Arrange
    limiter = CommandRateLimiter(cooldown_seconds=5.0)

    # Act
    result = limiter.is_allowed(123456)

    # Assert
    assert result is True


def test_rate_limiter_is_allowed_within_cooldown():
    """Test command is blocked within cooldown period."""
    # Arrange
    limiter = CommandRateLimiter(cooldown_seconds=5.0)
    limiter.record_command(123456)

    # Act - immediately try again
    result = limiter.is_allowed(123456)

    # Assert
    assert result is False


def test_rate_limiter_is_allowed_after_cooldown():
    """Test command is allowed after cooldown expires."""
    # Arrange
    limiter = CommandRateLimiter(cooldown_seconds=0.1)  # 100ms cooldown
    limiter.record_command(123456)

    # Act - wait for cooldown
    time.sleep(0.15)
    result = limiter.is_allowed(123456)

    # Assert
    assert result is True


def test_rate_limiter_different_users_independent():
    """Test rate limits are independent per user."""
    # Arrange
    limiter = CommandRateLimiter(cooldown_seconds=5.0)
    limiter.record_command(123456)

    # Act - different user should be allowed
    result = limiter.is_allowed(789012)

    # Assert
    assert result is True


def test_rate_limiter_get_remaining_cooldown_active():
    """Test get_remaining_cooldown returns correct value during cooldown."""
    # Arrange
    limiter = CommandRateLimiter(cooldown_seconds=5.0)
    limiter.record_command(123456)

    # Act
    remaining = limiter.get_remaining_cooldown(123456)

    # Assert
    assert 4.5 < remaining <= 5.0  # Should be close to 5.0 seconds


def test_rate_limiter_get_remaining_cooldown_expired():
    """Test get_remaining_cooldown returns 0 after cooldown."""
    # Arrange
    limiter = CommandRateLimiter(cooldown_seconds=0.1)
    limiter.record_command(123456)

    # Act - wait for expiry
    time.sleep(0.15)
    remaining = limiter.get_remaining_cooldown(123456)

    # Assert
    assert remaining == 0.0


def test_rate_limiter_get_remaining_cooldown_no_history():
    """Test get_remaining_cooldown returns 0 for user with no history."""
    # Arrange
    limiter = CommandRateLimiter(cooldown_seconds=5.0)

    # Act
    remaining = limiter.get_remaining_cooldown(123456)

    # Assert
    assert remaining == 0.0


def test_rate_limiter_record_command():
    """Test record_command updates last command time."""
    # Arrange
    limiter = CommandRateLimiter(cooldown_seconds=5.0)

    # Act
    limiter.record_command(123456)

    # Assert
    assert 123456 in limiter._last_command_time
    assert limiter.is_allowed(123456) is False  # Should be in cooldown


def test_rate_limiter_reset_user():
    """Test reset_user clears cooldown for specific user."""
    # Arrange
    limiter = CommandRateLimiter(cooldown_seconds=5.0)
    limiter.record_command(123456)
    limiter.record_command(789012)

    # Act
    limiter.reset_user(123456)

    # Assert
    assert limiter.is_allowed(123456) is True  # Cooldown cleared
    assert limiter.is_allowed(789012) is False  # Other user still limited


def test_rate_limiter_reset_all():
    """Test reset_all clears cooldowns for all users."""
    # Arrange
    limiter = CommandRateLimiter(cooldown_seconds=5.0)
    limiter.record_command(123456)
    limiter.record_command(789012)

    # Act
    limiter.reset_all()

    # Assert
    assert limiter.is_allowed(123456) is True
    assert limiter.is_allowed(789012) is True
    assert len(limiter._last_command_time) == 0


def test_rate_limiter_multiple_commands_sequence():
    """Test rate limiter handles sequence of commands correctly."""
    # Arrange
    limiter = CommandRateLimiter(cooldown_seconds=0.1)

    # Act & Assert
    # First command - allowed
    assert limiter.is_allowed(123456) is True
    limiter.record_command(123456)

    # Second command immediately - blocked
    assert limiter.is_allowed(123456) is False

    # Wait and try again - allowed
    time.sleep(0.15)
    assert limiter.is_allowed(123456) is True
    limiter.record_command(123456)

    # Third command immediately - blocked
    assert limiter.is_allowed(123456) is False


def test_rate_limiter_concurrent_users():
    """Test rate limiter handles multiple users concurrently."""
    # Arrange
    limiter = CommandRateLimiter(cooldown_seconds=0.1)

    # Act - User 1 sends command
    assert limiter.is_allowed(111) is True
    limiter.record_command(111)

    # User 2 sends command (should be allowed)
    assert limiter.is_allowed(222) is True
    limiter.record_command(222)

    # User 3 sends command (should be allowed)
    assert limiter.is_allowed(333) is True
    limiter.record_command(333)

    # All users blocked immediately after
    assert limiter.is_allowed(111) is False
    assert limiter.is_allowed(222) is False
    assert limiter.is_allowed(333) is False

    # Wait for cooldown
    time.sleep(0.15)

    # All users allowed again
    assert limiter.is_allowed(111) is True
    assert limiter.is_allowed(222) is True
    assert limiter.is_allowed(333) is True
