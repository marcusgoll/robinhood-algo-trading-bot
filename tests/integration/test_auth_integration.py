"""
Integration tests for authentication module.

Tests the complete authentication flow with bot integration.

Constitution v1.0.0 - §Testing_Requirements: Integration testing
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestBotAuthenticationIntegration:
    """Integration tests for bot startup with authentication."""

    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_bot_starts_with_valid_credentials(self, mock_path, mock_robin_stocks):
        """
        Test bot starts successfully with valid authentication (T035).

        GIVEN: Valid credentials configured
        WHEN: Bot initialized and auth triggered
        THEN: RobinhoodAuth.login() succeeds
              Bot session authenticated
              Bot ready to trade
        """
        # Given: No existing pickle
        mock_path.return_value.exists.return_value = False

        # And: robin_stocks login succeeds
        mock_session = MagicMock()
        mock_robin_stocks.login.return_value = mock_session

        # And: Valid config
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When: RobinhoodAuth initialized and logs in
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        result = auth.login()

        # Then: Authentication successful
        assert result is True
        assert auth.is_authenticated() is True
        mock_robin_stocks.login.assert_called()

    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    def test_bot_fails_to_start_with_invalid_credentials(self, mock_path, mock_robin_stocks):
        """
        Test bot fails to start with invalid credentials (T036).

        GIVEN: Invalid credentials configured
        WHEN: Bot initialization attempted
        THEN: RobinhoodAuth.login() raises AuthenticationError
              Bot does not start (§Safety_First)
              Clear error message provided
        """
        # Given: No pickle
        mock_path.return_value.exists.return_value = False

        # And: robin_stocks login fails
        mock_robin_stocks.login.return_value = None

        # And: Invalid config
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "wrong_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When/Then: RobinhoodAuth login raises AuthenticationError
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth, AuthenticationError
        auth = RobinhoodAuth(config)

        with pytest.raises(AuthenticationError):
            auth.login()

        # And: Bot not authenticated
        assert auth.is_authenticated() is False

    @patch('src.trading_bot.auth.robinhood_auth.pickle')
    @patch('src.trading_bot.auth.robinhood_auth.Path')
    @patch('src.trading_bot.auth.robinhood_auth.robin_stocks')
    def test_session_restored_on_bot_restart(self, mock_robin_stocks, mock_path, mock_pickle):
        """
        Test session restored when bot restarts (T037).

        GIVEN: Valid pickle file exists from previous session
        WHEN: Bot restarts
        THEN: Session restored from pickle
              robin_stocks.login() NOT called (cached session used)
              Bot starts quickly (<2s - NFR-004)
        """
        # Given: Valid pickle exists
        mock_path.return_value.exists.return_value = True
        mock_session = MagicMock()
        mock_pickle.load.return_value = mock_session

        # And: Config
        config = Mock()
        config.robinhood_username = "user@example.com"
        config.robinhood_password = "secure_password"
        config.robinhood_mfa_secret = None
        config.robinhood_device_token = None

        # When: RobinhoodAuth initialized and logs in
        from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
        auth = RobinhoodAuth(config)
        result = auth.login()

        # Then: Session restored from pickle
        assert result is True
        assert auth.is_authenticated() is True
        # Should NOT call robin_stocks.login (used pickle)
        mock_robin_stocks.login.assert_not_called()
        mock_pickle.load.assert_called_once()
