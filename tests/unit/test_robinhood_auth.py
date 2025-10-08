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


class TestLoginFlows:
    """Test suite for authentication login flows."""

    @patch('src.trading_bot.auth.robinhood_auth.pickle')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_login_with_valid_pickle_restores_session(self, mock_path, mock_pickle):
        """
        Test login with pickle - valid session restored.

        GIVEN: .robinhood.pickle exists with valid session data
        WHEN: RobinhoodAuth.login() called
        THEN: Session restored without calling robin_stocks.login()
              Logged "Session restored from cache"
        """
        # Given: Valid pickle file exists
        mock_path.return_value.exists.return_value = True
        mock_session = MagicMock()
        mock_pickle.load.return_value = mock_session

        # And: Config with credentials
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When: RobinhoodAuth logs in
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)

        with patch('src.trading_bot.auth.robinhood_auth.robin_stocks') as mock_rh:
            result = auth.login()

            # Then: Session restored from pickle
            assert result is True
            assert auth.is_authenticated() is True
            # robin_stocks.login should NOT be called (pickle used instead)
            mock_rh.login.assert_not_called()

    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_first_time_login_with_credentials(self, mock_path, mock_robin_stocks):
        """
        Test login without pickle - username/password auth.

        GIVEN: No .robinhood.pickle exists
        WHEN: RobinhoodAuth.login() called
        THEN: robin_stocks.login() called with username/password
              Session saved to pickle
              Logged "Authentication successful"
        """
        # Given: No pickle file exists
        mock_path.return_value.exists.return_value = False

        # And: robin_stocks.login succeeds
        mock_session = MagicMock()
        mock_robin_stocks.login.return_value = mock_session

        # And: Config with credentials
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When: RobinhoodAuth logs in
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        result = auth.login()

        # Then: robin_stocks.login called with credentials
        mock_robin_stocks.login.assert_called_once()
        assert result is True
        assert auth.is_authenticated() is True

    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.pyotp')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_mfa_challenge_handled_with_pyotp(self, mock_path, mock_pyotp, mock_robin_stocks):
        """
        Test login with MFA - pyotp handles challenge.

        GIVEN: ROBINHOOD_MFA_SECRET set
              robin_stocks.login() triggers MFA challenge
        WHEN: RobinhoodAuth.login() called
        THEN: pyotp.TOTP(secret).now() called
              MFA code submitted
              Login succeeds
        """
        # Given: No pickle file
        mock_path.return_value.exists.return_value = False

        # And: MFA secret configured
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = "BASE32SECRET"
        config.robinhood_device_token = None

        # And: pyotp generates MFA code
        mock_totp = MagicMock()
        mock_totp.now.return_value = "123456"
        mock_pyotp.TOTP.return_value = mock_totp

        # And: robin_stocks.login succeeds with MFA
        mock_session = MagicMock()
        mock_robin_stocks.login.return_value = mock_session

        # When: RobinhoodAuth logs in
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        result = auth.login()

        # Then: pyotp generated MFA code
        mock_pyotp.TOTP.assert_called_once_with("BASE32SECRET")
        mock_totp.now.assert_called_once()
        assert result is True
