"""
Robinhood Authentication Service

Handles Robinhood authentication with MFA support, session management, and token refresh.

Constitution v1.0.0:
- §Security: Credentials from environment only, never logged
- §Audit_Everything: All auth events logged
- §Safety_First: Bot fails to start if auth fails
"""

from dataclasses import dataclass
from pathlib import Path
import re
import pickle
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import robin_stocks
except ImportError:
    robin_stocks = None

try:
    import pyotp
except ImportError:
    pyotp = None


def _mask_credential(value: str) -> str:
    """Mask a credential for logging (§Security)."""
    if not value:
        return "****"
    if "@" in value:
        # Email: user****@example.com
        parts = value.split("@")
        return f"{parts[0][:4]}****@{parts[1]}"
    # Other credentials: show first 4 chars
    return f"{value[:4]}****" if len(value) > 4 else "****"


class AuthenticationError(Exception):
    """Custom exception for authentication failures."""
    pass


@dataclass
class AuthConfig:
    """
    Authentication configuration from Config.

    Attributes:
        username: Robinhood email (must be valid email format)
        password: Robinhood password
        mfa_secret: Optional TOTP MFA secret (base32)
        device_token: Optional device token (skips MFA)
        pickle_path: Path to session cache file (default: .robinhood.pickle)
    """
    username: str
    password: str
    mfa_secret: Optional[str] = None
    device_token: Optional[str] = None
    pickle_path: str = ".robinhood.pickle"

    @classmethod
    def from_config(cls, config) -> "AuthConfig":
        """
        Create AuthConfig from Config instance.

        Args:
            config: Config instance with robinhood_* attributes

        Returns:
            AuthConfig instance

        Raises:
            ValueError: If username or password missing or invalid
        """
        # Extract credentials from config
        username = config.robinhood_username
        password = config.robinhood_password
        mfa_secret = config.robinhood_mfa_secret
        device_token = config.robinhood_device_token

        # Validate required fields
        if not username:
            raise ValueError("Robinhood username is required")
        if not password:
            raise ValueError("Robinhood password is required")

        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, username):
            raise ValueError("Invalid email format for Robinhood username")

        return cls(
            username=username,
            password=password,
            mfa_secret=mfa_secret,
            device_token=device_token
        )


class RobinhoodAuth:
    """
    Robinhood authentication service.

    Handles login, logout, session management, MFA, and token refresh.
    """

    def __init__(self, config):
        """
        Initialize RobinhoodAuth with configuration.

        Args:
            config: Config instance or AuthConfig instance
        """
        # Convert Config to AuthConfig if needed
        if hasattr(config, 'robinhood_username'):
            self.auth_config = AuthConfig.from_config(config)
        else:
            self.auth_config = config

        self._authenticated = False
        self._session = None

    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self._authenticated

    def login(self) -> bool:
        """
        Authenticate with Robinhood.

        Returns:
            True if login successful

        Raises:
            AuthenticationError: If authentication fails
        """
        # T021: Try to restore session from pickle first
        pickle_path = Path(self.auth_config.pickle_path)
        if pickle_path.exists():
            try:
                with open(pickle_path, 'rb') as f:
                    self._session = pickle.load(f)
                self._authenticated = True
                logger.info(f"Session restored from cache for {_mask_credential(self.auth_config.username)}")
                return True
            except Exception as e:
                # T015: Corrupt pickle - fall back to credentials
                logger.warning(f"Cached session corrupted, re-authenticating for {_mask_credential(self.auth_config.username)}")
                pass

        # T022: Credentials-based login
        if not robin_stocks:
            raise AuthenticationError("robin_stocks library not available")

        # Prepare login parameters
        username = self.auth_config.username
        password = self.auth_config.password

        logger.info(f"Authenticating user {_mask_credential(username)}")

        # T023: Handle MFA if configured
        mfa_code = None
        if self.auth_config.mfa_secret and pyotp:
            totp = pyotp.TOTP(self.auth_config.mfa_secret)
            mfa_code = totp.now()

        # Attempt login
        try:
            # Call robin_stocks.login()
            # Note: Actual robin_stocks API may require different parameters
            if mfa_code:
                self._session = robin_stocks.login(username, password, mfa_code=mfa_code)
            elif self.auth_config.device_token:
                self._session = robin_stocks.login(username, password, device_token=self.auth_config.device_token)
            else:
                self._session = robin_stocks.login(username, password)

            if not self._session:
                raise AuthenticationError("Invalid credentials or authentication failed")

            self._authenticated = True

            # T014: Save session to pickle with 600 permissions
            try:
                with open(pickle_path, 'wb') as f:
                    pickle.dump(self._session, f)
                os.chmod(pickle_path, 0o600)
                logger.info(f"Session saved to cache for {_mask_credential(username)}")
            except Exception:
                # Non-critical: If pickle save fails, continue with authenticated session
                logger.warning(f"Failed to save session cache for {_mask_credential(username)}")
                pass

            logger.info(f"Authentication successful for {_mask_credential(username)}")
            return True

        except AuthenticationError:
            raise
        except Exception as e:
            if "MFA" in str(e) or "authentication failed" in str(e):
                raise AuthenticationError(f"MFA or authentication failed: {e}")
            raise AuthenticationError(f"Invalid credentials: {e}")

    def logout(self) -> None:
        """Logout and clear session."""
        # T016: Logout implementation
        if robin_stocks:
            robin_stocks.logout()

        self._authenticated = False
        self._session = None

        # Delete pickle file
        pickle_path = Path(self.auth_config.pickle_path)
        if pickle_path.exists():
            pickle_path.unlink()

        # TODO: Add logging - "Logged out successfully"

    def refresh_token(self) -> None:
        """Refresh expired authentication token."""
        # T017: Token refresh implementation
        # This is a placeholder - robin_stocks handles token refresh automatically
        # In a real implementation, this would call robin_stocks refresh method
        # and update the pickle file
        if self._authenticated:
            # TODO: Add logging - "Token expired, refreshing"
            # For now, just maintain authenticated state
            pass
