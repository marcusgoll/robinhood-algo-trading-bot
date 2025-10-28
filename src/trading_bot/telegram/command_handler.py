"""Main Telegram command handler orchestrator.

Integrates auth, rate limiting, formatting, and API calls.

Constitution v1.0.0:
- §Non_Blocking: All operations async
- §Security: Authentication required for all commands
- §Error_Handling: Graceful degradation on API failures
"""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .api_client import InternalAPIClient
from .middleware import CommandAuthMiddleware, CommandRateLimiter
from .response_formatter import ResponseFormatter

logger = logging.getLogger(__name__)


class TelegramCommandHandler:
    """
    Main command handler for Telegram bot.

    Orchestrates:
    - Command routing (registers /start, /status, /pause, etc.)
    - Authentication (via CommandAuthMiddleware)
    - Rate limiting (via CommandRateLimiter)
    - API calls (via InternalAPIClient)
    - Response formatting (via ResponseFormatter)

    Pattern: Facade (simplifies complex subsystem interactions)
    Architecture: Dependency injection (receives middleware, formatter)
    """

    def __init__(
        self,
        application: Application,
        auth_middleware: Optional[CommandAuthMiddleware] = None,
        rate_limiter: Optional[CommandRateLimiter] = None,
        formatter: Optional[ResponseFormatter] = None,
        api_client_factory=None,
    ) -> None:
        """
        Initialize command handler.

        Args:
            application: python-telegram-bot Application instance
            auth_middleware: Authentication middleware (default: create new)
            rate_limiter: Rate limiter (default: create new)
            formatter: Response formatter (default: create new)
            api_client_factory: Factory function for creating API client (for testing)
        """
        self.application = application
        self.auth_middleware = auth_middleware or CommandAuthMiddleware()
        self.rate_limiter = rate_limiter or CommandRateLimiter()
        self.formatter = formatter or ResponseFormatter()
        self._api_client_factory = api_client_factory or InternalAPIClient

        logger.info("TelegramCommandHandler initialized")

    def register_commands(self) -> None:
        """
        Register all command handlers with the application.

        Registers:
        - /start - Welcome message
        - /help - Command list
        - /status - Bot status
        - /pause - Pause trading
        - /resume - Resume trading
        - /positions - Open positions
        - /performance - Performance metrics
        """
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        self.application.add_handler(CommandHandler("status", self._handle_status))
        self.application.add_handler(CommandHandler("pause", self._handle_pause))
        self.application.add_handler(CommandHandler("resume", self._handle_resume))
        self.application.add_handler(
            CommandHandler("positions", self._handle_positions)
        )
        self.application.add_handler(
            CommandHandler("performance", self._handle_performance)
        )

        logger.info("Registered 7 command handlers")

    async def _handle_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command."""
        user_id = update.effective_user.id
        authorized = self.auth_middleware.is_authorized(user_id)

        message = self.formatter.format_welcome(authorized=authorized)
        await update.message.reply_text(message, parse_mode="Markdown")

        logger.info(f"/start command from user {user_id} (authorized={authorized})")

    async def _handle_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command."""
        user_id = update.effective_user.id

        # Auth check
        if not self.auth_middleware.is_authorized(user_id):
            await self._send_unauthorized_error(update)
            return

        # Rate limit check
        if not await self._check_rate_limit(update, user_id):
            return

        message = self.formatter.format_help()
        await update.message.reply_text(message, parse_mode="Markdown")

        self.rate_limiter.record_command(user_id)
        logger.info(f"/help command from user {user_id}")

    async def _handle_status(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /status command."""
        user_id = update.effective_user.id

        # Auth check
        if not self.auth_middleware.is_authorized(user_id):
            await self._send_unauthorized_error(update)
            return

        # Rate limit check
        if not await self._check_rate_limit(update, user_id):
            return

        # Call API
        try:
            async with self._api_client_factory() as client:
                state = await client.get_bot_state()

            message = self.formatter.format_status(state)
            await update.message.reply_text(message, parse_mode="Markdown")

            self.rate_limiter.record_command(user_id)
            logger.info(f"/status command from user {user_id}")

        except Exception as e:
            logger.error(f"API error in /status: {e}")
            error_message = self.formatter.format_error("api_error", str(e))
            await update.message.reply_text(error_message, parse_mode="Markdown")

    async def _handle_pause(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /pause command."""
        user_id = update.effective_user.id

        # Auth check
        if not self.auth_middleware.is_authorized(user_id):
            await self._send_unauthorized_error(update)
            return

        # Rate limit check
        if not await self._check_rate_limit(update, user_id):
            return

        # Call API
        try:
            async with self._api_client_factory() as client:
                response = await client.pause_bot(reason="Manual pause via Telegram")

            # Format success response
            message = f"✅ **Bot Paused**\n\n{response.get('message', 'Trading paused successfully.')}"
            await update.message.reply_text(message, parse_mode="Markdown")

            self.rate_limiter.record_command(user_id)
            logger.info(f"/pause command from user {user_id}")

        except Exception as e:
            logger.error(f"API error in /pause: {e}")
            error_message = self.formatter.format_error("api_error", str(e))
            await update.message.reply_text(error_message, parse_mode="Markdown")

    async def _handle_resume(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /resume command."""
        user_id = update.effective_user.id

        # Auth check
        if not self.auth_middleware.is_authorized(user_id):
            await self._send_unauthorized_error(update)
            return

        # Rate limit check
        if not await self._check_rate_limit(update, user_id):
            return

        # Call API
        try:
            async with self._api_client_factory() as client:
                response = await client.resume_bot()

            # Format success response
            message = f"▶️ **Bot Resumed**\n\n{response.get('message', 'Trading resumed successfully.')}"
            await update.message.reply_text(message, parse_mode="Markdown")

            self.rate_limiter.record_command(user_id)
            logger.info(f"/resume command from user {user_id}")

        except Exception as e:
            logger.error(f"API error in /resume: {e}")
            error_message = self.formatter.format_error("api_error", str(e))
            await update.message.reply_text(error_message, parse_mode="Markdown")

    async def _handle_positions(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /positions command."""
        user_id = update.effective_user.id

        # Auth check
        if not self.auth_middleware.is_authorized(user_id):
            await self._send_unauthorized_error(update)
            return

        # Rate limit check
        if not await self._check_rate_limit(update, user_id):
            return

        # Call API
        try:
            async with self._api_client_factory() as client:
                positions = await client.get_positions()

            message = self.formatter.format_positions(positions)
            await update.message.reply_text(message, parse_mode="Markdown")

            self.rate_limiter.record_command(user_id)
            logger.info(f"/positions command from user {user_id}")

        except Exception as e:
            logger.error(f"API error in /positions: {e}")
            error_message = self.formatter.format_error("api_error", str(e))
            await update.message.reply_text(error_message, parse_mode="Markdown")

    async def _handle_performance(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /performance command."""
        user_id = update.effective_user.id

        # Auth check
        if not self.auth_middleware.is_authorized(user_id):
            await self._send_unauthorized_error(update)
            return

        # Rate limit check
        if not await self._check_rate_limit(update, user_id):
            return

        # Call API
        try:
            async with self._api_client_factory() as client:
                metrics = await client.get_performance_metrics()

            message = self.formatter.format_performance(metrics)
            await update.message.reply_text(message, parse_mode="Markdown")

            self.rate_limiter.record_command(user_id)
            logger.info(f"/performance command from user {user_id}")

        except Exception as e:
            logger.error(f"API error in /performance: {e}")
            error_message = self.formatter.format_error("api_error", str(e))
            await update.message.reply_text(error_message, parse_mode="Markdown")

    async def _check_rate_limit(self, update: Update, user_id: int) -> bool:
        """
        Check rate limit for user.

        Returns:
            bool: True if allowed, False if rate limited (error sent to user)
        """
        if not self.rate_limiter.is_allowed(user_id):
            remaining = self.rate_limiter.get_remaining_cooldown(user_id)
            error_message = self.formatter.format_error(
                "rate_limit", f"{remaining:.0f} seconds"
            )
            await update.message.reply_text(error_message, parse_mode="Markdown")
            return False
        return True

    async def _send_unauthorized_error(self, update: Update) -> None:
        """Send unauthorized error message."""
        error_message = self.formatter.format_error("unauthorized")
        await update.message.reply_text(error_message, parse_mode="Markdown")

    @classmethod
    def from_env(cls) -> 'TelegramCommandHandler':
        """
        Create TelegramCommandHandler from environment variables.

        Reads TELEGRAM_BOT_TOKEN from environment and creates Application instance.

        Returns:
            TelegramCommandHandler instance configured from environment

        Raises:
            ValueError: If TELEGRAM_BOT_TOKEN not set
        """
        import os

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

        # Create Application instance
        application = Application.builder().token(token).build()

        # Create handler with default middleware
        handler = cls(
            application=application,
            auth_middleware=CommandAuthMiddleware(),
            rate_limiter=CommandRateLimiter(),
            formatter=ResponseFormatter(),
            api_client_factory=InternalAPIClient
        )

        logger.info("TelegramCommandHandler created from environment")
        return handler

    def start(self) -> None:
        """
        Start the Telegram bot command handler.

        Starts polling for updates in a background thread.
        Non-blocking - returns immediately while bot runs in background.
        """
        import threading

        def run_bot():
            """Run bot polling in separate thread with its own event loop."""
            logger.info("Starting Telegram bot polling...")
            self.application.run_polling(drop_pending_updates=True, stop_signals=None)

        # Start polling in background thread (daemon so it exits with main process)
        bot_thread = threading.Thread(target=run_bot, daemon=True, name="TelegramBotThread")
        bot_thread.start()

        logger.info("Telegram command handler started (polling in background thread)")

    async def stop(self) -> None:
        """
        Stop the Telegram bot command handler.

        Gracefully shuts down the Application and stops polling.
        """
        await self.application.stop()
        logger.info("Telegram command handler stopped")
