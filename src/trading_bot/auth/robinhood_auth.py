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
import time
from typing import Optional, Any, Callable, TypeVar
import dotenv

from ..utils.security import mask_username, mask_password, mask_mfa_secret, mask_device_token

logger = logging.getLogger(__name__)

T = TypeVar('T')

try:
    import robin_stocks.robinhood as rh
    robin_stocks_available = True
except ImportError:
    rh = None
    robin_stocks_available = False

try:
    import pyotp
    pyotp_available = True
except ImportError:
    pyotp = None
    pyotp_available = False


def _retry_with_backoff(
    func: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 1.0
) -> T:
    """
    Retry a function with exponential backoff (T034).

    Args:
        func: Function to retry (takes no args, returns T)
        max_attempts: Maximum number of attempts (default: 3)
        base_delay: Base delay in seconds (default: 1.0)

    Returns:
        Result from successful function call

    Raises:
        Last exception if all attempts fail

    Pattern: 1s, 2s, 4s delays between retries
    """
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_attempts} attempts failed")

    # Re-raise the last exception
    raise last_exception  # type: ignore




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
    def from_config(cls, config: Any) -> "AuthConfig":
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

    def __init__(self, config: Any) -> None:
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

        self._authenticated: bool = False
        self._session: Optional[Any] = None

    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self._authenticated

    def login(self) -> bool:
        """
        Authenticate with Robinhood (T020).

        Returns:
            True if login successful

        Raises:
            AuthenticationError: If authentication fails
        """
        # T021: Session restoration handled by robin_stocks via pickle_name parameter
        # robin_stocks will automatically load cached session if available and valid

        # T022: Credentials-based login with MFA support
        if not rh:
            raise AuthenticationError("robin_stocks library not available")

        # Prepare login parameters
        username = self.auth_config.username
        password = self.auth_config.password

        logger.info(f"Authenticating user {mask_username(username)}")

        # T023: First try without MFA code (for push notification approval)
        # If that fails and MFA secret is configured, retry with TOTP code
        logger.info("Attempting login - if your account uses push notifications, please approve in the Robinhood app")

        # Attempt login with retry logic (T034)
        try:
            # Define login function for retry wrapper
            def _do_login() -> Any:
                # Call rh.login() WITHOUT mfa_code to trigger push notification
                # If user has TOTP-based MFA (not push), they should set MFA_SECRET
                result = rh.login(
                    username=username,
                    password=password,
                    mfa_code=None,  # Let Robinhood send push notification
                    store_session=True,
                    pickle_name=self.auth_config.pickle_path
                )

                if not result:
                    raise AuthenticationError("Invalid credentials or authentication failed")
                return result

            # Use longer delays to give user time to approve push notification
            # 10s, 20s, 40s = 70 seconds total for user to approve
            self._session = _retry_with_backoff(_do_login, max_attempts=3, base_delay=10.0)

            self._authenticated = True
            logger.info(f"Authentication successful for {mask_username(username)}")
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
        if rh:
            rh.logout()

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

    def save_device_token_to_env(self, device_token: str) -> None:
        """
        Save device token to .env file (T018).

        Args:
            device_token: Device token to save

        Constitution v1.0.0:
            §Security: Device tokens persisted to .env for reuse
        """
        dotenv.set_key(".env", "DEVICE_TOKEN", device_token)
        logger.info("Device token saved to .env file")

    def login_with_device_token(self) -> bool:
        """
        Authenticate with device token, fallback to MFA if invalid (T019).

        Returns:
            True if login successful

        Raises:
            AuthenticationError: If authentication fails

        Constitution v1.0.0:
            §Security: Device token tried first, MFA fallback if expired
        """
        if not rh:
            raise AuthenticationError("robin_stocks library not available")

        # Get credentials
        username = self.auth_config.username
        password = self.auth_config.password
        device_token = self.auth_config.device_token

        logger.info(f"Attempting login with device token for {mask_username(username)}")

        # Try login with device token first (single attempt, no retry for invalid token)
        try:
            result = rh.login(username, password, device_token=device_token)
            if not result:
                raise AuthenticationError("Device token authentication failed")

            self._session = result
            self._authenticated = True

            # Save session to pickle
            pickle_path = Path(self.auth_config.pickle_path)
            try:
                with open(pickle_path, 'wb') as f:
                    pickle.dump(self._session, f)
                os.chmod(pickle_path, 0o600)
                logger.info(f"Session saved to cache for {mask_username(username)}")
            except Exception:
                logger.warning(f"Failed to save session cache for {mask_username(username)}")
                pass

            logger.info(f"Device token authentication successful for {mask_username(username)}")
            return True

        except Exception as e:
            # Device token invalid - fallback to MFA
            logger.warning(f"Device token authentication failed: {e}. Falling back to MFA...")

            # Generate MFA code if configured
            if not self.auth_config.mfa_secret or not pyotp:
                raise AuthenticationError("Device token invalid and MFA not configured")

            totp = pyotp.TOTP(self.auth_config.mfa_secret)
            mfa_code = totp.now()

            try:
                result = rh.login(username, password, mfa_code=mfa_code)
                if not result:
                    raise AuthenticationError("MFA authentication failed")

                self._session = result
                self._authenticated = True

                # Save session to pickle
                pickle_path = Path(self.auth_config.pickle_path)
                try:
                    with open(pickle_path, 'wb') as f:
                        pickle.dump(self._session, f)
                    os.chmod(pickle_path, 0o600)
                    logger.info(f"Session saved to cache for {mask_username(username)}")
                except Exception:
                    logger.warning(f"Failed to save session cache for {mask_username(username)}")
                    pass

                # Extract new device token from session if available
                new_device_token = None
                if hasattr(self._session, 'get') and callable(self._session.get):
                    new_device_token = self._session.get('device_token')
                elif isinstance(self._session, dict):
                    new_device_token = self._session.get('device_token')

                # Save new device token to .env
                if new_device_token:
                    self.save_device_token_to_env(new_device_token)
                    logger.info(f"New device token saved after MFA authentication for {mask_username(username)}")

                logger.info(f"MFA authentication successful for {mask_username(username)}")
                return True

            except AuthenticationError:
                raise
            except Exception as e:
                raise AuthenticationError(f"MFA authentication failed: {e}")
