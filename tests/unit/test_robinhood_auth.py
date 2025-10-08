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
