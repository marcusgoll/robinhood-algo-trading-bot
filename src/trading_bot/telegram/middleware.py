"""Middleware for Telegram command handlers.

Provides authentication and rate limiting for command execution.

Constitution v1.0.0:
- §Security: User ID authentication required for all commands
- §Non_Blocking: All checks are non-blocking
"""

import logging
import os
import time
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


class CommandAuthMiddleware:
    """
    Authentication middleware for Telegram commands.

    Validates user IDs against authorized list from environment.
    Pattern: Fail-safe (reject unknown users, log all attempts)
    """

    def __init__(self, authorized_user_ids: Optional[Set[int]] = None) -> None:
        """
        Initialize auth middleware.

        Args:
            authorized_user_ids: Set of authorized Telegram user IDs
                                 (default: from TELEGRAM_AUTHORIZED_USER_IDS env)
        """
        if authorized_user_ids is not None:
            self.authorized_user_ids = authorized_user_ids
        else:
            # Load from environment
            user_ids_str = os.getenv("TELEGRAM_AUTHORIZED_USER_IDS", "")
            if user_ids_str:
                self.authorized_user_ids = set(
                    int(uid.strip()) for uid in user_ids_str.split(",") if uid.strip()
                )
            else:
                self.authorized_user_ids = set()

        logger.info(
            f"CommandAuthMiddleware initialized with {len(self.authorized_user_ids)} authorized users"
        )

    def is_authorized(self, user_id: int) -> bool:
        """
        Check if user is authorized.

        Args:
            user_id: Telegram user ID

        Returns:
            bool: True if authorized, False otherwise
        """
        authorized = user_id in self.authorized_user_ids

        if not authorized:
            logger.warning(
                f"Unauthorized command attempt from user {user_id}",
                extra={"user_id": user_id, "result": "rejected"},
            )
        else:
            logger.debug(
                f"Authorized command from user {user_id}",
                extra={"user_id": user_id, "result": "accepted"},
            )

        return authorized

    def add_authorized_user(self, user_id: int) -> None:
        """
        Add user to authorized list (runtime only, not persisted).

        Args:
            user_id: Telegram user ID to authorize
        """
        self.authorized_user_ids.add(user_id)
        logger.info(f"Added user {user_id} to authorized list")

    def remove_authorized_user(self, user_id: int) -> None:
        """
        Remove user from authorized list (runtime only, not persisted).

        Args:
            user_id: Telegram user ID to deauthorize
        """
        self.authorized_user_ids.discard(user_id)
        logger.info(f"Removed user {user_id} from authorized list")


class CommandRateLimiter:
    """
    Rate limiter for Telegram commands.

    Enforces per-user cooldown period between commands.
    Pattern: In-memory state (dict of user_id -> last_command_time)
    """

    def __init__(self, cooldown_seconds: Optional[float] = None) -> None:
        """
        Initialize rate limiter.

        Args:
            cooldown_seconds: Cooldown period in seconds (default: from env or 5.0)
        """
        if cooldown_seconds is not None:
            self.cooldown_seconds = cooldown_seconds
        else:
            self.cooldown_seconds = float(
                os.getenv("TELEGRAM_COMMAND_COOLDOWN_SECONDS", "5.0")
            )

        self._last_command_time: Dict[int, float] = {}

        logger.info(
            f"CommandRateLimiter initialized with {self.cooldown_seconds}s cooldown"
        )

    def is_allowed(self, user_id: int) -> bool:
        """
        Check if user is allowed to execute command (not in cooldown).

        Args:
            user_id: Telegram user ID

        Returns:
            bool: True if allowed, False if still in cooldown
        """
        current_time = time.time()
        last_time = self._last_command_time.get(user_id, 0.0)

        time_since_last = current_time - last_time

        if time_since_last >= self.cooldown_seconds:
            return True
        else:
            remaining = self.cooldown_seconds - time_since_last
            logger.debug(
                f"Rate limit hit for user {user_id}. {remaining:.1f}s remaining",
                extra={"user_id": user_id, "remaining_seconds": remaining},
            )
            return False

    def get_remaining_cooldown(self, user_id: int) -> float:
        """
        Get remaining cooldown time for user.

        Args:
            user_id: Telegram user ID

        Returns:
            float: Remaining seconds in cooldown (0.0 if no cooldown)
        """
        current_time = time.time()
        last_time = self._last_command_time.get(user_id, 0.0)
        time_since_last = current_time - last_time

        if time_since_last >= self.cooldown_seconds:
            return 0.0
        else:
            return self.cooldown_seconds - time_since_last

    def record_command(self, user_id: int) -> None:
        """
        Record command execution for rate limiting.

        Args:
            user_id: Telegram user ID
        """
        self._last_command_time[user_id] = time.time()
        logger.debug(f"Recorded command execution for user {user_id}")

    def reset_user(self, user_id: int) -> None:
        """
        Reset cooldown for specific user.

        Args:
            user_id: Telegram user ID
        """
        self._last_command_time.pop(user_id, None)
        logger.debug(f"Reset rate limit for user {user_id}")

    def reset_all(self) -> None:
        """Reset cooldown for all users."""
        self._last_command_time.clear()
        logger.info("Reset rate limits for all users")
