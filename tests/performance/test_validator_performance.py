"""
Performance tests for ConfigValidator (T029).

Tests that validation completes within performance requirements:
- All credential validation checks complete <500ms

Constitution v1.0.0 - §Performance: Validation latency targets
"""

import pytest
import time
from unittest.mock import Mock
from pathlib import Path


class TestValidatorPerformance:
    """Performance tests for configuration validation."""

    def test_validation_completes_under_500ms(self):
        """
        Test validation completes in <500ms (T029).

        GIVEN: Config with all credentials set
        WHEN: ConfigValidator.validate_all() called
        THEN: Execution completes in <500ms
        """
        # Given: Config with all fields
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = "ABCDEFGHIJKLMNOP"
        config.robinhood_device_token = "device_token_123"
        config.current_phase = "experience"
        config.paper_trading = True
        config.max_trades_per_day = 1
        config.config_file = Path("config.json")

        # Mock validate() method
        config.validate = Mock()

        # Mock ensure_directories() method
        config.ensure_directories = Mock()

        # When: Validation runs (measure time)
        from src.trading_bot.validator import ConfigValidator

        start_time = time.perf_counter()
        validator = ConfigValidator(config)
        is_valid, errors, warnings = validator.validate_all(test_api=False)
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        # Then: Validation completed in <500ms
        assert elapsed_ms < 500, f"Validation took {elapsed_ms:.2f}ms (target: <500ms)"

        # And: Validation succeeded
        assert is_valid is True
        assert len(errors) == 0

    def test_validation_with_invalid_credentials_still_fast(self):
        """
        Test validation still fast even with validation errors.

        GIVEN: Config with invalid MFA secret format
        WHEN: ConfigValidator.validate_all() called
        THEN: Execution completes in <500ms even with errors
        """
        # Given: Config with invalid MFA secret (wrong length)
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = "INVALID"  # Too short
        config.robinhood_device_token = None
        config.current_phase = "experience"
        config.paper_trading = True
        config.max_trades_per_day = 1
        config.config_file = Path("config.json")

        # Mock validate() method
        config.validate = Mock()

        # Mock ensure_directories() method
        config.ensure_directories = Mock()

        # When: Validation runs (measure time)
        from src.trading_bot.validator import ConfigValidator

        start_time = time.perf_counter()
        validator = ConfigValidator(config)
        is_valid, errors, warnings = validator.validate_all(test_api=False)
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        # Then: Validation completed in <500ms (even with errors)
        assert elapsed_ms < 500, f"Validation took {elapsed_ms:.2f}ms (target: <500ms)"

        # And: Validation found errors
        assert is_valid is False
        assert len(errors) > 0
