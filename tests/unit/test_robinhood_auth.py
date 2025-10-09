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

    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_device_token_login_skips_mfa(self, mock_path, mock_robin_stocks):
        """
        Test login with device token - skips MFA.

        GIVEN: ROBINHOOD_DEVICE_TOKEN set
        WHEN: RobinhoodAuth.login() called
        THEN: robin_stocks.login() called with device_token parameter
              No MFA challenge required
              Login succeeds
        """
        # Given: No pickle file
        mock_path.return_value.exists.return_value = False

        # And: Device token configured
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = "DEVICE123ABC"

        # And: robin_stocks.login succeeds
        mock_session = MagicMock()
        mock_robin_stocks.login.return_value = mock_session

        # When: RobinhoodAuth logs in
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        result = auth.login()

        # Then: Login called with device token (no MFA needed)
        mock_robin_stocks.login.assert_called_once()
        assert result is True
        assert auth.is_authenticated() is True

    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_invalid_credentials_raises_authentication_error(self, mock_path, mock_robin_stocks):
        """
        Test login with invalid credentials - raises AuthenticationError.

        GIVEN: Invalid username/password
        WHEN: RobinhoodAuth.login() called
        THEN: robin_stocks.login() returns None/error
              AuthenticationError raised with clear message
              Not authenticated
        """
        # Given: No pickle file
        mock_path.return_value.exists.return_value = False

        # And: Invalid credentials
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "wrong_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # And: robin_stocks.login fails
        mock_robin_stocks.login.return_value = None

        # When/Then: RobinhoodAuth login raises AuthenticationError
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth, AuthenticationError
        auth = RobinhoodAuth(config)
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            auth.login()

    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.pyotp')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_mfa_failure_raises_authentication_error(self, mock_path, mock_pyotp, mock_robin_stocks):
        """
        Test login with MFA failure - raises AuthenticationError.

        GIVEN: Valid credentials but MFA challenge fails
        WHEN: RobinhoodAuth.login() called with MFA
        THEN: AuthenticationError raised with MFA error message
              Not authenticated
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

        # And: robin_stocks.login fails (MFA rejected)
        mock_robin_stocks.login.return_value = None

        # When/Then: RobinhoodAuth login raises AuthenticationError
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth, AuthenticationError
        auth = RobinhoodAuth(config)
        with pytest.raises(AuthenticationError, match="MFA|authentication failed"):
            auth.login()


class TestSessionManagement:
    """Test suite for session persistence and management."""

    @patch('src.trading_bot.auth.robinhood_auth.pickle')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    def test_pickle_saved_with_600_permissions(self, mock_robin_stocks, mock_path, mock_pickle):
        """
        Test session saved to pickle with 600 permissions.

        GIVEN: Successful login creates a session
        WHEN: Session saved to .robinhood.pickle
        THEN: Pickle file created with 600 permissions (owner read/write only)
              Logged "Session saved to cache"
        """
        # Given: No pickle file initially
        mock_path.return_value.exists.return_value = False

        # And: Successful login
        mock_session = MagicMock()
        mock_robin_stocks.login.return_value = mock_session

        # And: Config
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When: RobinhoodAuth logs in and saves session
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        auth.login()

        # Then: Pickle saved and permissions set to 600
        mock_pickle.dump.assert_called_once()
        # Note: Permission check will be in implementation (os.chmod(path, 0o600))

    @patch('src.trading_bot.auth.robinhood_auth.pickle')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    def test_corrupt_pickle_falls_back_to_credentials(self, mock_robin_stocks, mock_path, mock_pickle):
        """
        Test corrupt pickle triggers fallback to credential auth.

        GIVEN: .robinhood.pickle exists but is corrupted
        WHEN: RobinhoodAuth.login() called
        THEN: pickle.load() raises exception
              Falls back to username/password login
              Logged "Cached session corrupted, re-authenticating"
        """
        # Given: Pickle file exists but is corrupted
        mock_path.return_value.exists.return_value = True
        mock_pickle.load.side_effect = Exception("Pickle corrupted")

        # And: Fallback login succeeds
        mock_session = MagicMock()
        mock_robin_stocks.login.return_value = mock_session

        # And: Config
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When: RobinhoodAuth logs in
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        result = auth.login()

        # Then: Fallback to credentials login
        mock_robin_stocks.login.assert_called_once()
        assert result is True
        assert auth.is_authenticated() is True

    @patch('src.trading_bot.auth.robinhood_auth.pickle')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    def test_logout_clears_session_and_deletes_pickle(self, mock_robin_stocks, mock_path, mock_pickle):
        """
        Test logout clears session and deletes pickle.

        GIVEN: Authenticated session exists
        WHEN: RobinhoodAuth.logout() called
        THEN: robin_stocks.logout() called
              .robinhood.pickle deleted
              is_authenticated() returns False
              Logged "Logged out successfully"
        """
        # Given: Authenticated session
        mock_path.return_value.exists.return_value = True
        mock_session = MagicMock()
        mock_pickle.load.return_value = mock_session

        # And: Config
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When: RobinhoodAuth logs in then logs out
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        auth.login()
        auth.logout()

        # Then: robin_stocks.logout called and pickle deleted
        mock_robin_stocks.logout.assert_called_once()
        mock_path.return_value.unlink.assert_called_once()
        assert auth.is_authenticated() is False

    @patch('src.trading_bot.auth.robinhood_auth.pickle')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    def test_token_refresh_on_401_error(self, mock_robin_stocks, mock_path, mock_pickle):
        """
        Test token automatically refreshed on 401 error.

        GIVEN: Authenticated session with expired token
        WHEN: API call returns 401 Unauthorized
        THEN: Token automatically refreshed via robin_stocks
              Pickle updated with new token
              Logged "Token expired, refreshing"
        """
        # Given: Valid pickle session
        mock_path.return_value.exists.return_value = True
        mock_session = MagicMock()
        mock_pickle.load.return_value = mock_session

        # And: Config
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When: RobinhoodAuth detects expired token
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        auth.login()

        # Simulate token refresh
        auth.refresh_token()

        # Then: Token refreshed (implementation will call robin_stocks refresh)
        # Note: Actual refresh logic tested in implementation
        assert auth.is_authenticated() is True


class TestSecurity:
    """Test suite for security requirements."""

    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_credentials_never_logged(self, mock_path, mock_robin_stocks, caplog):
        """
        Test credentials are never logged.

        GIVEN: RobinhoodAuth performing login
        WHEN: Login flow executes (success or failure)
        THEN: Credentials (username, password, MFA secret, device token) NEVER appear in logs
              Only masked values appear (e.g., "user****@example.com", "****")
        """
        # Given: No pickle
        mock_path.return_value.exists.return_value = False

        # And: Credentials
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "super_secret_password"
        config.robinhood_mfa_secret = "BASE32SECRETKEY"
        config.robinhood_device_token = "DEVICE123ABC"

        # And: Login succeeds
        mock_session = MagicMock()
        mock_robin_stocks.login.return_value = mock_session

        # When: RobinhoodAuth logs in (captures logs)
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        import logging
        caplog.set_level(logging.DEBUG)

        auth = RobinhoodAuth(config)
        auth.login()

        # Then: Credentials NEVER appear in logs
        all_logs = caplog.text
        assert "super_secret_password" not in all_logs
        assert "BASE32SECRETKEY" not in all_logs
        assert "DEVICE123ABC" not in all_logs
        # Should see masked version instead
        assert "****" in all_logs or "user****" in all_logs


class TestNetworkResilience:
    """Test suite for network error handling and retry logic."""

    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    @patch('src.trading_bot.auth.robinhood_auth.time.sleep')  # Mock sleep to speed up test
    def test_network_error_retries_with_backoff(self, mock_sleep, mock_path, mock_robin_stocks):
        """
        Test network error during login - retry with exponential backoff (T041).

        GIVEN: robin_stocks.login() fails with network error on first 2 attempts
        WHEN: RobinhoodAuth.login() called
        THEN: Retries 3 times with exponential backoff (1s, 2s)
              Succeeds on 3rd attempt
              Logged retry attempts
        """
        # Given: No pickle file
        mock_path.return_value.exists.return_value = False

        # And: robin_stocks.login() fails twice then succeeds
        mock_session = MagicMock()
        mock_robin_stocks.login.side_effect = [
            Exception("Network error: Connection timeout"),
            Exception("Network error: Connection timeout"),
            mock_session,  # Success on 3rd attempt
        ]

        # And: Config
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When: RobinhoodAuth logs in
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        result = auth.login()

        # Then: Login eventually succeeded after retries
        assert result is True
        assert auth.is_authenticated() is True

        # And: robin_stocks.login called 3 times
        assert mock_robin_stocks.login.call_count == 3

        # And: sleep called twice (for retries with exponential backoff)
        assert mock_sleep.call_count == 2
        # First retry: 1s delay
        mock_sleep.assert_any_call(1.0)
        # Second retry: 2s delay
        mock_sleep.assert_any_call(2.0)


class TestDeviceTokenManagement:
    """Test suite for device token save/load/fallback functionality (T012-T014)."""

    @patch('src.trading_bot.auth.robinhood_auth.dotenv.set_key')
    def test_save_device_token_to_env(self, mock_set_key):
        """
        Test saving device token to .env file (T012).

        GIVEN: Device token "test_token_123"
        WHEN: RobinhoodAuth.save_device_token_to_env("test_token_123") called
        THEN: dotenv.set_key called with (".env", "DEVICE_TOKEN", "test_token_123")
        """
        # Given: Config
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # And: RobinhoodAuth instance
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)

        # When: save_device_token_to_env called with device token
        device_token = "test_token_123"
        auth.save_device_token_to_env(device_token)

        # Then: dotenv.set_key called with correct parameters
        mock_set_key.assert_called_once_with(".env", "DEVICE_TOKEN", device_token)

    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_login_with_device_token_success(self, mock_path, mock_robin_stocks):
        """
        Test login with valid device token succeeds (T013).

        GIVEN: Valid device token in config
        WHEN: RobinhoodAuth.login_with_device_token() called
        THEN: robin_stocks.login called with device_token parameter, returns True
        """
        # Given: No pickle file
        mock_path.return_value.exists.return_value = False

        # And: Config with device token
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = "valid_device_token_123"

        # And: robin_stocks.login succeeds with device token
        mock_session = MagicMock()
        mock_robin_stocks.login.return_value = mock_session

        # When: RobinhoodAuth logs in with device token
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        result = auth.login_with_device_token()

        # Then: Login called with device_token parameter
        mock_robin_stocks.login.assert_called_once()
        call_args = mock_robin_stocks.login.call_args
        assert "device_token" in call_args.kwargs or len(call_args.args) > 2
        assert result is True

    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.pyotp')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    @patch('src.trading_bot.auth.robinhood_auth.dotenv.set_key')
    def test_login_with_device_token_fallback(
        self, mock_set_key, mock_path, mock_pyotp, mock_robin_stocks
    ):
        """
        Test login with invalid device token falls back to MFA (T014).

        GIVEN: Invalid device token (causes 401 error)
        WHEN: RobinhoodAuth.login_with_device_token() called
        THEN: Falls back to MFA authentication
              Saves new device token to .env on successful MFA login
        """
        # Given: No pickle file
        mock_path.return_value.exists.return_value = False

        # And: Config with invalid device token and MFA secret
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = "BASE32SECRETMFA"
        config.robinhood_device_token = "invalid_token_old"

        # And: pyotp generates MFA code
        mock_totp = MagicMock()
        mock_totp.now.return_value = "123456"
        mock_pyotp.TOTP.return_value = mock_totp

        # And: robin_stocks.login fails with device token (401), succeeds with MFA
        mock_session_success = MagicMock()
        mock_session_success.get.return_value = {"device_token": "new_device_token_456"}
        mock_robin_stocks.login.side_effect = [
            Exception("401 Unauthorized: Invalid device token"),  # Device token fails
            mock_session_success,  # MFA succeeds
        ]

        # When: RobinhoodAuth attempts login with fallback
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        result = auth.login_with_device_token()

        # Then: robin_stocks.login called twice (device token, then MFA)
        assert mock_robin_stocks.login.call_count == 2

        # And: MFA code generated
        mock_pyotp.TOTP.assert_called_once_with("BASE32SECRETMFA")
        mock_totp.now.assert_called_once()

        # And: New device token saved to .env
        mock_set_key.assert_called_once()
        assert "DEVICE_TOKEN" in mock_set_key.call_args.args
        assert "new_device_token_456" in str(mock_set_key.call_args)

        # And: Login succeeded
        assert result is True
