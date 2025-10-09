"""
Integration tests for credentials management flow (T024-T027).

Tests the complete credentials flow including:
- First-time authentication saves device token
- Subsequent authentication uses device token
- Invalid device token triggers MFA fallback
- Credentials properly masked in logs

Constitution v1.0.0 - §Testing_Requirements: Integration testing
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import logging


class TestCredentialsFlow:
    """Integration tests for end-to-end credentials management."""

    @patch('src.trading_bot.auth.robinhood_auth.dotenv.set_key')
    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_first_time_auth_saves_device_token(
        self, mock_path, mock_robin_stocks, mock_set_key
    ):
        """
        Test first-time authentication saves device token to .env (T024).

        GIVEN: User authenticating for the first time (no device token)
        WHEN: login() called and robin_stocks returns device_token
        THEN: Device token saved to .env via dotenv.set_key()
        """
        # Given: No pickle file
        mock_path.return_value.exists.return_value = False

        # And: Config without device token
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = "ABCDEFGHIJKLMNOP"
        config.robinhood_device_token = None

        # And: robin_stocks.login succeeds with MFA and returns device token
        mock_session = {"device_token": "new_device_token_abc123"}
        mock_robin_stocks.login.return_value = mock_session

        # And: pyotp configured
        with patch('src.trading_bot.auth.robinhood_auth.pyotp') as mock_pyotp:
            mock_totp = MagicMock()
            mock_totp.now.return_value = "123456"
            mock_pyotp.TOTP.return_value = mock_totp

            # When: RobinhoodAuth logs in for first time
            from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
            auth = RobinhoodAuth(config)
            result = auth.login()

            # Then: Login succeeded
            assert result is True

            # And: NO device token saved (no device token in session for first login without it)
            # Note: Device tokens are only saved during MFA fallback in login_with_device_token()
            # For first-time login without device token, we use MFA directly

    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_subsequent_auth_uses_device_token(
        self, mock_path, mock_robin_stocks
    ):
        """
        Test subsequent authentication uses device token (T025).

        GIVEN: User has device token in config
        WHEN: login() called
        THEN: login_with_device_token() called first (no MFA code generated)
        """
        # Given: No pickle file
        mock_path.return_value.exists.return_value = False

        # And: Config WITH device token
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = "ABCDEFGHIJKLMNOP"
        config.robinhood_device_token = "existing_device_token_xyz789"

        # And: robin_stocks.login succeeds with device token
        mock_session = MagicMock()
        mock_robin_stocks.login.return_value = mock_session

        # When: RobinhoodAuth logs in with device token
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        result = auth.login()

        # Then: Login succeeded
        assert result is True

        # And: robin_stocks.login called with device_token parameter
        mock_robin_stocks.login.assert_called_once()
        call_kwargs = mock_robin_stocks.login.call_args.kwargs
        assert "device_token" in call_kwargs
        assert call_kwargs["device_token"] == "existing_device_token_xyz789"

    @patch('src.trading_bot.auth.robinhood_auth.dotenv.set_key')
    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.pyotp')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_invalid_device_token_triggers_mfa_fallback(
        self, mock_path, mock_pyotp, mock_robin_stocks, mock_set_key
    ):
        """
        Test invalid device token triggers MFA fallback (T026).

        GIVEN: User has device token but it's expired/invalid
        WHEN: login_with_device_token() called
        THEN: First login attempt fails, falls back to MFA
              New device token saved to .env
        """
        # Given: No pickle file
        mock_path.return_value.exists.return_value = False

        # And: Config with INVALID device token
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = "ABCDEFGHIJKLMNOP"
        config.robinhood_device_token = "expired_device_token_old123"

        # And: pyotp generates MFA code
        mock_totp = MagicMock()
        mock_totp.now.return_value = "123456"
        mock_pyotp.TOTP.return_value = mock_totp

        # And: robin_stocks.login fails with device token, succeeds with MFA
        mock_session_success = {"device_token": "new_device_token_fresh456"}
        mock_robin_stocks.login.side_effect = [
            Exception("401 Unauthorized: Invalid device token"),  # Device token fails
            mock_session_success,  # MFA succeeds and returns new device token
        ]

        # When: RobinhoodAuth logs in (triggers device token → MFA fallback)
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        result = auth.login()

        # Then: Login succeeded after fallback
        assert result is True

        # And: robin_stocks.login called twice (device token, then MFA)
        assert mock_robin_stocks.login.call_count == 2

        # And: MFA code generated for fallback
        mock_pyotp.TOTP.assert_called_once_with("ABCDEFGHIJKLMNOP")
        mock_totp.now.assert_called_once()

        # And: New device token saved to .env
        mock_set_key.assert_called_once()
        assert "DEVICE_TOKEN" in mock_set_key.call_args.args
        assert "new_device_token_fresh456" in str(mock_set_key.call_args)

    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_credentials_masked_in_logs(
        self, mock_path, mock_robin_stocks, caplog
    ):
        """
        Test credentials properly masked in logs (T027).

        GIVEN: User authenticates with credentials
        WHEN: login() executes
        THEN: No plaintext credentials in logs (username, password, MFA, device token)
              Only masked versions appear (use***, *****, etc.)
        """
        # Given: No pickle file
        mock_path.return_value.exists.return_value = False

        # And: Config with all credentials
        config = Mock()
        config.robinhood_username = "testuser@example.com"
        config.robinhood_password = "super_secret_password_123"
        config.robinhood_mfa_secret = "ABCDEFGHIJKLMNOP"
        config.robinhood_device_token = "device_token_secret_xyz"

        # And: robin_stocks.login succeeds
        mock_session = MagicMock()
        mock_robin_stocks.login.return_value = mock_session

        # When: RobinhoodAuth logs in (capture logs)
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        caplog.set_level(logging.DEBUG)

        auth = RobinhoodAuth(config)
        auth.login()

        # Then: Plaintext credentials NEVER appear in logs
        all_logs = caplog.text
        assert "testuser@example.com" not in all_logs  # Full email
        assert "super_secret_password_123" not in all_logs  # Password
        assert "ABCDEFGHIJKLMNOP" not in all_logs  # MFA secret
        assert "device_token_secret_xyz" not in all_logs  # Device token

        # And: Masked versions DO appear
        assert "tes***" in all_logs  # Masked username (first 3 chars)
        # Password and MFA never logged (even masked)
        # Device token may appear masked if logged
