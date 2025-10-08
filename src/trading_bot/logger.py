"""
Structured Logging System

Enforces Constitution v1.0.0:
- §Audit_Everything: Separate logs for trades, errors, and info
- §Data_Integrity: All timestamps in UTC
- §Safety_First: Comprehensive audit trail for compliance

Log Files:
- logs/trading_bot.log: General application logs
- logs/trades.log: Trade execution logs (§Audit_Everything)
- logs/errors.log: Error and exception logs
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
import sys
from datetime import datetime, timezone


class UTCFormatter(logging.Formatter):
    """
    Custom formatter that uses UTC timestamps.

    Enforces §Data_Integrity: All timestamps must be UTC.
    """

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        """
        Format time in UTC.

        Args:
            record: Log record
            datefmt: Date format string (optional)

        Returns:
            Formatted UTC timestamp
        """
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat()


class TradingLogger:
    """
    Centralized logging configuration for trading bot.

    Provides separate loggers for:
    - General application logs (info, debug, warning)
    - Trade execution logs (§Audit_Everything)
    - Error logs (exceptions, critical issues)
    """

    # Log file paths
    LOGS_DIR = Path("logs")
    MAIN_LOG = LOGS_DIR / "trading_bot.log"
    TRADES_LOG = LOGS_DIR / "trades.log"
    ERRORS_LOG = LOGS_DIR / "errors.log"

    # Log rotation settings
    MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    BACKUP_COUNT = 5  # Keep 5 backup files

    # Log format (ISO 8601 UTC timestamps)
    LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S UTC"

    _initialized = False

    @classmethod
    def setup(cls, logs_dir: Optional[Path] = None) -> None:
        """
        Initialize logging system.

        Creates log directory and configures all loggers.
        Should be called once at application startup.

        Args:
            logs_dir: Optional custom logs directory (default: ./logs)
        """
        if cls._initialized:
            return

        # Set custom logs directory if provided
        if logs_dir:
            cls.LOGS_DIR = logs_dir
            cls.MAIN_LOG = logs_dir / "trading_bot.log"
            cls.TRADES_LOG = logs_dir / "trades.log"
            cls.ERRORS_LOG = logs_dir / "errors.log"

        # Create logs directory
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # Configure root logger
        cls._configure_root_logger()

        # Configure specialized loggers
        cls._configure_trades_logger()
        cls._configure_errors_logger()

        cls._initialized = True

        # Log initialization
        logger = logging.getLogger(__name__)
        logger.info("Logging system initialized (Constitution v1.0.0)")
        logger.info(f"Logs directory: {cls.LOGS_DIR.absolute()}")
        logger.info(f"UTC timestamps enabled (§Data_Integrity)")

    @classmethod
    def _configure_root_logger(cls) -> None:
        """Configure root logger for general application logs."""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        # Clear any existing handlers
        root_logger.handlers.clear()

        # Console handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = UTCFormatter(cls.LOG_FORMAT, cls.DATE_FORMAT)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            cls.MAIN_LOG,
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = UTCFormatter(cls.LOG_FORMAT, cls.DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    @classmethod
    def _configure_trades_logger(cls) -> None:
        """
        Configure trades logger (§Audit_Everything).

        Logs all trade executions for compliance and analysis.
        """
        trades_logger = logging.getLogger("trading_bot.trades")
        trades_logger.setLevel(logging.INFO)
        trades_logger.propagate = False  # Don't propagate to root logger

        # Trades file handler with rotation
        trades_handler = RotatingFileHandler(
            cls.TRADES_LOG,
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT
        )
        trades_handler.setLevel(logging.INFO)
        trades_formatter = UTCFormatter(cls.LOG_FORMAT, cls.DATE_FORMAT)
        trades_handler.setFormatter(trades_formatter)
        trades_logger.addHandler(trades_handler)

        # Also log to console for visibility
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = UTCFormatter(cls.LOG_FORMAT, cls.DATE_FORMAT)
        console_handler.setFormatter(console_formatter)
        trades_logger.addHandler(console_handler)

    @classmethod
    def _configure_errors_logger(cls) -> None:
        """
        Configure errors logger.

        Logs all errors and exceptions for debugging.
        """
        errors_logger = logging.getLogger("trading_bot.errors")
        errors_logger.setLevel(logging.WARNING)
        errors_logger.propagate = True  # Also log to root logger

        # Errors file handler with rotation
        errors_handler = RotatingFileHandler(
            cls.ERRORS_LOG,
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT
        )
        errors_handler.setLevel(logging.WARNING)
        errors_formatter = UTCFormatter(cls.LOG_FORMAT, cls.DATE_FORMAT)
        errors_handler.setFormatter(errors_formatter)
        errors_logger.addHandler(errors_handler)

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance.

        Args:
            name: Logger name (use __name__ in modules)

        Returns:
            Configured logger instance
        """
        if not cls._initialized:
            cls.setup()

        return logging.getLogger(name)

    @classmethod
    def get_trades_logger(cls) -> logging.Logger:
        """
        Get the trades logger (§Audit_Everything).

        Use this for logging all trade executions.

        Returns:
            Trades logger instance
        """
        if not cls._initialized:
            cls.setup()

        return logging.getLogger("trading_bot.trades")

    @classmethod
    def get_errors_logger(cls) -> logging.Logger:
        """
        Get the errors logger.

        Use this for logging errors and exceptions.

        Returns:
            Errors logger instance
        """
        if not cls._initialized:
            cls.setup()

        return logging.getLogger("trading_bot.errors")


def setup_logging(logs_dir: Optional[Path] = None) -> None:
    """
    Convenience function to initialize logging system.

    Args:
        logs_dir: Optional custom logs directory (default: ./logs)
    """
    TradingLogger.setup(logs_dir)


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger.

    Args:
        name: Logger name (use __name__ in modules)

    Returns:
        Configured logger instance
    """
    return TradingLogger.get_logger(name)


def log_trade(
    action: str,
    symbol: str,
    quantity: int,
    price: float,
    mode: str,
    **kwargs
) -> None:
    """
    Log a trade execution (§Audit_Everything).

    Args:
        action: Trade action (BUY, SELL)
        symbol: Stock symbol
        quantity: Number of shares
        price: Execution price
        mode: Trading mode (PAPER or LIVE)
        **kwargs: Additional trade details
    """
    logger = TradingLogger.get_trades_logger()

    trade_details = f"{action} {quantity} shares of {symbol} @ ${price:.2f} [{mode}]"

    if kwargs:
        extra_info = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        trade_details += f" | {extra_info}"

    logger.info(trade_details)


def log_error(error: Exception, context: str = "") -> None:
    """
    Log an error with context.

    Args:
        error: Exception instance
        context: Additional context about the error
    """
    logger = TradingLogger.get_errors_logger()

    if context:
        logger.error(f"{context}: {type(error).__name__}: {str(error)}", exc_info=True)
    else:
        logger.error(f"{type(error).__name__}: {str(error)}", exc_info=True)
