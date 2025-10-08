"""
Unit tests for RobinhoodAuth authentication service.

Tests the complete authentication flow including:
- Credential validation
- Login flows (pickle, credentials, MFA, device token)
- Session persistence
- Token refresh
- Security (credentials never logged)

Constitution v1.0.0 - §Testing_Requirements: TDD approach
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import os


class TestCredentialValidation:
    """Test suite for credential validation."""

    def test_valid_credentials_loaded_from_config(self):
        """
        Test valid credentials are loaded from Config.

        GIVEN: Config with ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD set
        WHEN: AuthConfig created from Config
        THEN: username and password populated, optional fields None if not set
        """
        # Given: Config with valid credentials
        from unittest.mock import Mock
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When: AuthConfig created from Config
        from src.trading_bot.auth.robinhood_auth import AuthConfig
        auth_config = AuthConfig.from_config(config)

        # Then: Credentials populated correctly
        assert auth_config.username == "user@example.com"
        assert auth_config.password == "secure_password"
        assert auth_config.mfa_secret is None
        assert auth_config.device_token is None
        assert auth_config.pickle_path == ".robinhood.pickle"

    def test_missing_username_raises_error(self):
        """
        Test missing username raises ValueError.

        GIVEN: Config with empty/None ROBINHOOD_USERNAME
        WHEN: AuthConfig validation called
        THEN: ValueError raised with clear message
        """
        # Given: Config with missing username
        from unittest.mock import Mock
        config = Mock()
        config.robinhood_username = None
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When/Then: AuthConfig creation raises ValueError
        from src.trading_bot.auth.robinhood_auth import AuthConfig
        with pytest.raises(ValueError, match="username"):
            AuthConfig.from_config(config)

    def test_missing_password_raises_error(self):
        """
        Test missing password raises ValueError.

        GIVEN: Config with empty/None ROBINHOOD_PASSWORD
        WHEN: AuthConfig validation called
        THEN: ValueError raised with clear message
        """
        # Given: Config with missing password
        from unittest.mock import Mock
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = None
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When/Then: AuthConfig creation raises ValueError
        from src.trading_bot.auth.robinhood_auth import AuthConfig
        with pytest.raises(ValueError, match="password"):
            AuthConfig.from_config(config)

    def test_invalid_email_format_raises_error(self):
        """
        Test invalid email format raises ValueError.

        GIVEN: ROBINHOOD_USERNAME is not a valid email (e.g., "notanemail")
        WHEN: AuthConfig validation called
        THEN: ValueError raised with "Invalid email format" message
        """
        # Given: Config with invalid email format
        from unittest.mock import Mock
        config = Mock()
        config.robinhood_username = "notanemail"  # Not a valid email
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When/Then: AuthConfig creation raises ValueError
        from src.trading_bot.auth.robinhood_auth import AuthConfig
        with pytest.raises(ValueError, match="Invalid email format"):
            AuthConfig.from_config(config)
