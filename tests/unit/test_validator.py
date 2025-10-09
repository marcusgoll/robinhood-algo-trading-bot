"""
Unit tests for ConfigValidator

Tests Constitution v1.0.0 requirements:
- §Security: Credentials validation
- §Data_Integrity: Config parameter validation
- §Safety_First: API connection testing
"""

from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from src.trading_bot.config import Config
from src.trading_bot.validator import ConfigValidator, ValidationError, validate_config


class TestConfigValidator:
    """Test ConfigValidator functionality."""

    def test_validator_initialization(self) -> None:
        """Validator should initialize with a config."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass"
        )
        validator = ConfigValidator(config)

        assert validator.config == config
        assert validator.errors == []
        assert validator.warnings == []

    @patch("src.trading_bot.validator.Path.exists")
    def test_validate_credentials_missing_env_file(self, mock_exists: MagicMock) -> None:
        """Should error if .env file missing (§Security)."""
        mock_exists.return_value = False

        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass"
        )
        validator = ConfigValidator(config)
        validator._validate_credentials()

        assert len(validator.errors) > 0
        assert any(".env file" in error for error in validator.errors)

    def test_validate_credentials_missing_username(self) -> None:
        """Should error if username missing (§Security)."""
        config = Config(
            robinhood_username="",
            robinhood_password="test_pass"
        )
        validator = ConfigValidator(config)
        validator._validate_credentials()

        assert any("ROBINHOOD_USERNAME" in error for error in validator.errors)

    def test_validate_credentials_missing_password(self) -> None:
        """Should error if password missing (§Security)."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password=""
        )
        validator = ConfigValidator(config)
        validator._validate_credentials()

        assert any("ROBINHOOD_PASSWORD" in error for error in validator.errors)

    def test_validate_credentials_optional_warnings(self) -> None:
        """Should warn if optional credentials missing."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            robinhood_mfa_secret=None,
            robinhood_device_token=None
        )
        validator = ConfigValidator(config)
        validator._validate_credentials()

        # Should have warnings about MFA and device token
        assert len(validator.warnings) >= 2
        assert any("MFA_SECRET" in warning for warning in validator.warnings)
        assert any("DEVICE_TOKEN" in warning for warning in validator.warnings)

    def test_validate_config_parameters_valid(self) -> None:
        """Should pass validation for valid config (§Data_Integrity)."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            max_position_pct=5.0,
            max_daily_loss_pct=3.0,
            max_consecutive_losses=3
        )
        validator = ConfigValidator(config)
        validator._validate_config_parameters()

        assert len(validator.errors) == 0

    def test_validate_config_parameters_invalid(self) -> None:
        """Should error for invalid config parameters."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            max_position_pct=150.0,  # Invalid: > 100%
        )
        validator = ConfigValidator(config)
        validator._validate_config_parameters()

        assert len(validator.errors) > 0
        assert any("max_position_pct" in error.lower() for error in validator.errors)

    def test_validate_live_trading_warning(self) -> None:
        """Should warn when live trading enabled (§Safety_First)."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=False  # Live trading!
        )
        validator = ConfigValidator(config)
        validator._validate_config_parameters()

        assert any("LIVE TRADING" in warning for warning in validator.warnings)

    def test_validate_experience_phase_live_trading_error(self) -> None:
        """Should error if live trading in experience phase (§Safety_First)."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=False,
            current_phase="experience"
        )
        validator = ConfigValidator(config)
        validator._validate_config_parameters()

        assert any(
            "experience" in error.lower() and "live" in error.lower()
            for error in validator.errors
        )

    def test_validate_all_returns_tuple(self) -> None:
        """validate_all should return (is_valid, errors, warnings) tuple."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass"
        )
        validator = ConfigValidator(config)
        result = validator.validate_all(test_api=False)

        assert isinstance(result, tuple)
        assert len(result) == 3
        is_valid, errors, warnings = result
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
        assert isinstance(warnings, list)

    def test_validate_all_fails_with_errors(self) -> None:
        """validate_all should return False if there are errors."""
        config = Config(
            robinhood_username="",  # Missing!
            robinhood_password="test_pass"
        )
        validator = ConfigValidator(config)
        is_valid, errors, warnings = validator.validate_all(test_api=False)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_all_passes_without_errors(self) -> None:
        """validate_all should return True if no errors."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass"
        )
        validator = ConfigValidator(config)
        is_valid, errors, warnings = validator.validate_all(test_api=False)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_config_function_raises_on_error(self) -> None:
        """validate_config() should raise ValidationError on failure."""
        config = Config(
            robinhood_username="",  # Missing!
            robinhood_password="test_pass"
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_config(config, test_api=False)

        assert "Configuration validation failed" in str(exc_info.value)

    def test_validate_config_function_passes(self) -> None:
        """validate_config() should return True on success."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass"
        )

        result = validate_config(config, test_api=False)
        assert result is True

    def test_api_connection_test_placeholder(self) -> None:
        """API connection test should be a placeholder for now."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass"
        )
        validator = ConfigValidator(config)
        validator._test_api_connection()

        # Should add a warning that API test is not implemented
        assert any(
            "API connection test" in warning or "authentication-module" in warning
            for warning in validator.warnings
        )

    # =========================================================================
    # T008-T010: MFA Secret Validation Tests (RED phase - TDD)
    # FR-008, FR-009: MFA secret format validation
    # =========================================================================

    def test_validate_mfa_secret_format_valid(self) -> None:
        """Should pass validation for valid 16-char base32 MFA secret (T008)."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            robinhood_mfa_secret="ABCDEFGHIJKLMNOP"  # Valid: 16-char base32
        )
        validator = ConfigValidator(config)
        validator._validate_credentials()

        # Should not raise any errors about MFA format
        assert not any("MFA secret must be" in error for error in validator.errors)

    def test_validate_mfa_secret_format_invalid_length(self) -> None:
        """Should error for MFA secret with invalid length (T009)."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            robinhood_mfa_secret="ABCD"  # Invalid: too short
        )
        validator = ConfigValidator(config)
        validator._validate_credentials()

        # Should have error about length
        assert any(
            "MFA secret must be 16 characters" in error
            for error in validator.errors
        )

    def test_validate_mfa_secret_format_invalid_chars(self) -> None:
        """Should error for MFA secret with invalid base32 characters (T010)."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            robinhood_mfa_secret="ABCDEFGH12345678"  # Invalid: contains 8, 9
        )
        validator = ConfigValidator(config)
        validator._validate_credentials()

        # Should have error about invalid base32 characters
        assert any(
            "MFA secret must contain only base32 characters" in error
            for error in validator.errors
        )

    # =========================================================================
    # T011: Device Token Validation Tests (RED phase - TDD)
    # FR-004: Device token is optional, validation should pass if empty
    # =========================================================================

    def test_validate_device_token_optional(self) -> None:
        """Should pass validation for empty device token - token is optional (T011)."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            robinhood_device_token=""  # Empty: optional field
        )
        validator = ConfigValidator(config)
        validator._validate_credentials()

        # Device token is optional - should NOT raise errors
        assert not any("DEVICE_TOKEN" in error for error in validator.errors)
        # May have warning but not error
        assert len(validator.errors) == 0
