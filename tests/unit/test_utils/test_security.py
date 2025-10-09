"""
Unit tests for credential masking utilities.

Tests Constitution v1.0.0 requirements:
- §Security: Credentials never logged in plaintext
- FR-007: Credential masking in all log output

TDD Tasks T004-T007: RED phase tests for security.py masking functions
"""

import pytest

from src.trading_bot.utils.security import (
    mask_username,
    mask_password,
    mask_mfa_secret,
    mask_device_token
)


class TestMaskUsername:
    """Test mask_username() function."""

    def test_mask_username_standard_format(self) -> None:
        """
        T004 [RED]: Username should mask local part, preserve domain.

        Pattern: "john@example.com" -> "joh***@example.com"
        Shows first 3 chars + *** + full domain for debugging.

        Constitution v1.0.0: §Security
        """
        # AAA Pattern: Arrange
        username = "john@example.com"

        # Act
        masked = mask_username(username)

        # Assert
        assert masked == "joh***@example.com", (
            f"Expected 'joh***@example.com', got '{masked}'"
        )
        assert "@example.com" in masked, "Domain should be preserved for debugging"
        assert "john" not in masked, "Full local part should not appear in mask"

    def test_mask_username_short_email(self) -> None:
        """Username shorter than 3 chars should still mask safely."""
        username = "ab@example.com"

        masked = mask_username(username)

        assert masked == "ab***@example.com"
        assert "@example.com" in masked

    def test_mask_username_non_email(self) -> None:
        """Non-email username should show first 3 chars + ***."""
        username = "johndoe"

        masked = mask_username(username)

        assert masked == "joh***"
        assert "johndoe" not in masked

    def test_mask_username_empty(self) -> None:
        """Empty username should return generic mask."""
        username = ""

        masked = mask_username(username)

        assert masked == "****"


class TestMaskPassword:
    """Test mask_password() function."""

    def test_mask_password(self) -> None:
        """
        T005 [RED]: Password should always return *****.

        Pattern: Any password -> "*****"
        Never reveals any password characteristics (length, content).

        Constitution v1.0.0: §Security - Passwords never logged in any form
        """
        # AAA Pattern: Arrange
        password = "any_password_123!@#"

        # Act
        masked = mask_password(password)

        # Assert
        assert masked == "*****", f"Expected '*****', got '{masked}'"
        assert password not in masked, "Password should never appear in mask"

    def test_mask_password_empty(self) -> None:
        """Empty password should still return *****."""
        password = ""

        masked = mask_password(password)

        assert masked == "*****"

    def test_mask_password_short(self) -> None:
        """Short password should return ***** (no length leakage)."""
        password = "abc"

        masked = mask_password(password)

        assert masked == "*****"

    def test_mask_password_long(self) -> None:
        """Long password should return ***** (no length leakage)."""
        password = "a" * 100

        masked = mask_password(password)

        assert masked == "*****"


class TestMaskMfaSecret:
    """Test mask_mfa_secret() function."""

    def test_mask_mfa_secret(self) -> None:
        """
        T006 [RED]: MFA secret should always return ****.

        Pattern: "ABCDEFGHIJKLMNOP" -> "****"
        Never reveals any MFA secret characteristics.

        Constitution v1.0.0: §Security - MFA secrets never logged in any form
        """
        # AAA Pattern: Arrange
        mfa_secret = "ABCDEFGHIJKLMNOP"

        # Act
        masked = mask_mfa_secret(mfa_secret)

        # Assert
        assert masked == "****", f"Expected '****', got '{masked}'"
        assert mfa_secret not in masked, "MFA secret should never appear in mask"

    def test_mask_mfa_secret_empty(self) -> None:
        """Empty MFA secret should return ****."""
        mfa_secret = ""

        masked = mask_mfa_secret(mfa_secret)

        assert masked == "****"

    def test_mask_mfa_secret_invalid_format(self) -> None:
        """Invalid MFA format should still mask safely."""
        mfa_secret = "invalid_secret_format"

        masked = mask_mfa_secret(mfa_secret)

        assert masked == "****"
        assert "invalid" not in masked


class TestMaskDeviceToken:
    """Test mask_device_token() function."""

    def test_mask_device_token(self) -> None:
        """
        T007 [RED]: Device token should show first 8 chars + ***.

        Pattern: "1a2b3c4d5e6f7g8h" -> "1a2b3c4d***"
        Shows prefix for debugging token patterns while masking rest.

        Constitution v1.0.0: §Security - Device tokens partially masked for debugging
        """
        # AAA Pattern: Arrange
        device_token = "1a2b3c4d5e6f7g8h"

        # Act
        masked = mask_device_token(device_token)

        # Assert
        assert masked == "1a2b3c4d***", f"Expected '1a2b3c4d***', got '{masked}'"
        assert masked.startswith("1a2b3c4d"), "First 8 chars should be preserved"
        assert "5e6f7g8h" not in masked, "Remaining token should be masked"

    def test_mask_device_token_short(self) -> None:
        """Short device token should append *** to entire token."""
        device_token = "short"

        masked = mask_device_token(device_token)

        assert masked == "short***"

    def test_mask_device_token_empty(self) -> None:
        """Empty device token should return generic mask."""
        device_token = ""

        masked = mask_device_token(device_token)

        assert masked == "****"

    def test_mask_device_token_exactly_8_chars(self) -> None:
        """Device token exactly 8 chars should show all + ***."""
        device_token = "12345678"

        masked = mask_device_token(device_token)

        assert masked == "12345678***"
