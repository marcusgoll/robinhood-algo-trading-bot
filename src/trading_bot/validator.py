"""
Configuration Validator

Enforces Constitution v1.0.0:
- §Security: Validate credentials exist before start
- §Pre_Deploy: Validate all config parameters on boot
- §Safety_First: Test API connection before live trading
"""

from typing import List, Tuple, Optional
from pathlib import Path
import os
import logging

from .config import Config

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigValidator:
    """
    Configuration validator (Constitution v1.0.0).

    Validates:
    1. Credentials exist (§Security)
    2. Config parameters are valid (§Data_Integrity)
    3. API connection works (§Safety_First - before live trading)
    """

    def __init__(self, config: Config):
        """
        Initialize validator with configuration.

        Args:
            config: Configuration instance to validate
        """
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self, test_api: bool = False) -> Tuple[bool, List[str], List[str]]:
        """
        Run all validation checks.

        Args:
            test_api: If True, test API connection (only before live trading)

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        # 1. Validate credentials exist (§Security)
        self._validate_credentials()

        # 2. Validate config parameters (§Data_Integrity)
        self._validate_config_parameters()

        # 3. Validate file paths
        self._validate_file_paths()

        # 4. Test API connection (optional, only before live trading)
        if test_api:
            self._test_api_connection()

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def _validate_credentials(self) -> None:
        """
        Validate that credentials exist in .env file (§Security).

        Required:
        - ROBINHOOD_USERNAME
        - ROBINHOOD_PASSWORD
        """
        # Check .env file exists
        env_file = Path(".env")
        if not env_file.exists():
            self.errors.append(
                "Missing .env file. Copy .env.example to .env and add your credentials."
            )
            return

        # Check required credentials
        if not self.config.robinhood_username:
            self.errors.append(
                "Missing ROBINHOOD_USERNAME in .env file (§Security: required)"
            )

        if not self.config.robinhood_password:
            self.errors.append(
                "Missing ROBINHOOD_PASSWORD in .env file (§Security: required)"
            )

        # Check optional credentials (warnings only)
        if not self.config.robinhood_mfa_secret:
            self.warnings.append(
                "ROBINHOOD_MFA_SECRET not set. MFA will require manual input."
            )

        if not self.config.robinhood_device_token:
            self.warnings.append(
                "ROBINHOOD_DEVICE_TOKEN not set. Authentication may be slower."
            )

        logger.info("Credentials validation completed")

    def _validate_config_parameters(self) -> None:
        """
        Validate all config parameters (§Data_Integrity).

        Uses Config.validate() and adds additional checks.
        """
        try:
            # Run built-in validation
            self.config.validate()
            logger.info("Config parameters validation passed")

        except ValueError as e:
            self.errors.append(f"Invalid configuration: {str(e)}")
            return

        # Additional safety checks
        if self.config.paper_trading is False:
            self.warnings.append(
                "⚠️  LIVE TRADING MODE ENABLED! Real money will be used. "
                "Ensure you have completed paper trading validation (§Safety_First)"
            )

        # Check if config.json exists
        if not self.config.config_file.exists():
            self.warnings.append(
                f"config.json not found at {self.config.config_file}. "
                "Using default parameters. Copy config.example.json to config.json to customize."
            )

        # Validate phase progression
        if self.config.current_phase == "experience" and not self.config.paper_trading:
            self.errors.append(
                "Cannot use live trading in 'experience' phase. "
                "Set mode to 'paper' in config.json (§Safety_First)"
            )

        if self.config.current_phase == "proof" and self.config.max_trades_per_day != 1:
            self.warnings.append(
                "Proof phase should have max_trades_per_day=1 for consistency testing"
            )

    def _validate_file_paths(self) -> None:
        """
        Validate that required directories exist or can be created.
        """
        try:
            self.config.ensure_directories()
            logger.info("Directories validated/created")

        except Exception as e:
            self.errors.append(f"Failed to create directories: {str(e)}")

    def _test_api_connection(self) -> None:
        """
        Test API connection to Robinhood (§Safety_First).

        NOTE: This is a placeholder. Actual implementation requires robin_stocks.
        For now, we just check if credentials are set.
        """
        logger.info("API connection test requested")

        # Placeholder: Will implement with robin_stocks in authentication-module
        # For now, just verify credentials are present
        if not self.config.robinhood_username or not self.config.robinhood_password:
            self.errors.append(
                "Cannot test API connection: Missing credentials"
            )
            return

        self.warnings.append(
            "API connection test skipped (requires authentication-module implementation)"
        )

        # TODO: Implement actual API test when authentication-module is ready
        # try:
        #     import robin_stocks.robinhood as rh
        #     # Test connection without logging in
        #     response = rh.helper.request_get("https://api.robinhood.com/")
        #     if response.status_code == 200:
        #         logger.info("API connection test passed")
        #     else:
        #         self.errors.append(f"API connection failed: {response.status_code}")
        # except Exception as e:
        #     self.errors.append(f"API connection test failed: {str(e)}")

    def print_report(self) -> None:
        """Print validation report to console."""
        print()
        print("=" * 60)
        print("Configuration Validation Report")
        print("=" * 60)
        print()

        if not self.errors and not self.warnings:
            print("✅ All validation checks passed!")
            print()
            return

        if self.errors:
            print("❌ Errors (must fix):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
            print()

        if self.warnings:
            print("⚠️  Warnings (recommended to fix):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
            print()

        if self.errors:
            print("❌ Validation failed. Fix errors above before starting.")
        else:
            print("✅ Validation passed with warnings.")

        print()


def validate_config(config: Config, test_api: bool = False) -> bool:
    """
    Convenience function to validate configuration.

    Args:
        config: Configuration to validate
        test_api: If True, test API connection

    Returns:
        True if valid, False otherwise

    Raises:
        ValidationError: If validation fails
    """
    validator = ConfigValidator(config)
    is_valid, errors, warnings = validator.validate_all(test_api=test_api)

    if not is_valid:
        error_msg = f"Configuration validation failed: {'; '.join(errors)}"
        raise ValidationError(error_msg)

    return True
