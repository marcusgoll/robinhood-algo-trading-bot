"""
Claude Code Headless Manager

Manages subprocess invocation of Claude Code CLI for LLM-powered trading operations.
Uses Claude Haiku 4.5 for fast, cost-effective analysis.

Features:
- Subprocess-based CLI invocation with JSON responses
- Daily budget tracking and circuit breaker
- Comprehensive error handling with fallback logic
- JSONL logging of all LLM calls
- Cost monitoring and reporting
- Latency tracking

Usage:
    from trading_bot.llm import ClaudeCodeManager, LLMConfig

    config = LLMConfig(daily_budget_usd=5.0, model="haiku")
    manager = ClaudeCodeManager(config)

    result = manager.invoke("/screen momentum stocks")

    if result.success:
        symbols = result.data["symbols"]
        # Process symbols...

Constitution v1.0.0 - §Security: API keys from environment only, subprocess sandboxing
"""

import json
import subprocess
import logging
import os
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class LLMModel(str, Enum):
    """Available Claude models"""
    HAIKU = "haiku"  # Claude Haiku 4.5 - Fast + cheap
    SONNET = "sonnet"  # Claude Sonnet 4.5 - Balanced
    OPUS = "opus"  # Claude Opus 4.1 - Most capable


@dataclass
class LLMConfig:
    """Configuration for Claude Code manager"""
    daily_budget_usd: float = 5.0  # Max spend per day
    model: LLMModel = LLMModel.HAIKU
    timeout_seconds: int = 30  # Per-call timeout
    max_calls_per_hour: int = 50
    fallback_on_error: bool = True
    log_dir: str = "logs"
    enable_cost_tracking: bool = True


@dataclass
class LLMResponse:
    """Response from Claude Code CLI invocation"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cost_usd: float = 0.0
    latency_seconds: float = 0.0
    model: str = "haiku"
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class BudgetExceededError(Exception):
    """Raised when daily budget is exceeded"""
    pass


class ClaudeCodeManager:
    """
    Manages Claude Code headless CLI invocations for trading operations.

    Handles subprocess execution, JSON parsing, cost tracking, and error recovery.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize Claude Code manager.

        Args:
            config: Configuration object (uses defaults if None)
        """
        self.config = config or LLMConfig()
        self.log_dir = Path(self.config.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Cost tracking
        self.daily_cost = self._load_daily_cost()
        self.call_count = 0
        self.hour_start = datetime.now().replace(minute=0, second=0, microsecond=0)
        self.hourly_calls = 0

        # Logging setup
        self._setup_logging()

        # Telegram notification setup
        self._setup_telegram()

        logger.info(f"Claude Code Manager initialized: model={self.config.model.value}, "
                   f"budget=${self.config.daily_budget_usd}/day")

    def _setup_logging(self):
        """Setup JSONL logging for all LLM calls"""
        self.calls_log = self.log_dir / "llm-calls.jsonl"
        self.costs_log = self.log_dir / "llm-costs.jsonl"
        self.errors_log = self.log_dir / "llm-errors.jsonl"

    def _setup_telegram(self):
        """Setup Telegram notifications for LLM triggers"""
        self.telegram_enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.telegram_client = None

        if self.telegram_enabled and self.telegram_bot_token and self.telegram_chat_id:
            try:
                from trading_bot.notifications.telegram_client import TelegramClient
                self.telegram_client = TelegramClient(
                    bot_token=self.telegram_bot_token,
                    timeout=5.0
                )
                logger.info("Telegram notifications enabled for LLM triggers")
            except Exception as e:
                logger.warning(f"Failed to initialize Telegram client: {e}")
                self.telegram_enabled = False
        else:
            logger.debug("Telegram notifications disabled for LLM triggers")

    def _send_telegram_notification(self, message: str):
        """Send async Telegram notification (non-blocking)"""
        if not self.telegram_enabled or not self.telegram_client:
            return

        try:
            # Run async notification in a new event loop (non-blocking)
            asyncio.run(
                self.telegram_client.send_message(
                    chat_id=self.telegram_chat_id,
                    text=message,
                    parse_mode="Markdown"
                )
            )
        except Exception as e:
            # Never let Telegram failures block LLM operations
            logger.debug(f"Telegram notification failed (non-blocking): {e}")

    def _load_daily_cost(self) -> float:
        """Load today's accumulated cost from logs"""
        today = date.today().isoformat()
        costs_file = self.log_dir / "llm-costs.jsonl"

        if not costs_file.exists():
            return 0.0

        total_cost = 0.0
        with open(costs_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get('date') == today:
                        total_cost += entry.get('cost_usd', 0.0)
                except json.JSONDecodeError:
                    continue

        return total_cost

    def _check_budget(self):
        """
        Check if daily budget is exceeded.

        Raises:
            BudgetExceededError: If daily budget exceeded
        """
        if self.config.enable_cost_tracking and self.daily_cost >= self.config.daily_budget_usd:
            raise BudgetExceededError(
                f"Daily budget exceeded: ${self.daily_cost:.2f} >= ${self.config.daily_budget_usd}"
            )

    def _check_rate_limit(self):
        """Check hourly rate limit"""
        now = datetime.now()
        current_hour = now.replace(minute=0, second=0, microsecond=0)

        if current_hour != self.hour_start:
            # New hour, reset counter
            self.hour_start = current_hour
            self.hourly_calls = 0

        if self.hourly_calls >= self.config.max_calls_per_hour:
            raise Exception(f"Hourly rate limit exceeded: {self.hourly_calls} calls this hour")

        self.hourly_calls += 1

    def _log_call(self, prompt: str, response: LLMResponse):
        """Log LLM call to JSONL"""
        log_entry = {
            "timestamp": response.timestamp,
            "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,  # Truncate for readability
            "success": response.success,
            "cost_usd": response.cost_usd,
            "latency_seconds": response.latency_seconds,
            "model": response.model,
            "error": response.error
        }

        with open(self.calls_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def _log_cost(self, cost_usd: float):
        """Log cost to daily tracker"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "date": date.today().isoformat(),
            "cost_usd": cost_usd,
            "daily_total": self.daily_cost
        }

        with open(self.costs_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def _log_error(self, prompt: str, error: str):
        """Log error to errors log"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
            "error": error
        }

        with open(self.errors_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def invoke(self, prompt: str, output_format: str = "json") -> LLMResponse:
        """
        Invoke Claude Code CLI in headless mode.

        Args:
            prompt: The prompt to send (can include slash commands like /screen)
            output_format: Response format ("json" or "stream-json")

        Returns:
            LLMResponse with parsed JSON data and metadata

        Raises:
            BudgetExceededError: If daily budget exceeded
            subprocess.TimeoutExpired: If command times out
        """
        start_time = datetime.now()

        # Pre-flight checks
        try:
            self._check_budget()
            self._check_rate_limit()
        except (BudgetExceededError, Exception) as e:
            logger.error(f"Pre-flight check failed: {e}")
            self._log_error(prompt, str(e))
            return LLMResponse(
                success=False,
                error=str(e),
                timestamp=start_time.isoformat()
            )

        # Build command
        cmd = [
            "claude",
            "-p", prompt,
            "--model", self.config.model.value,
            "--output-format", output_format
        ]

        logger.debug(f"Invoking Claude Code: {' '.join(cmd[:4])}...")  # Don't log full prompt

        # Send Telegram notification: LLM triggered
        emoji = "🤖" if os.getenv("TELEGRAM_INCLUDE_EMOJIS", "true").lower() == "true" else ""
        truncated_prompt = prompt[:100] + "..." if len(prompt) > 100 else prompt
        self._send_telegram_notification(
            f"{emoji} *LLM Triggered*\n"
            f"Model: `{self.config.model.value}`\n"
            f"Prompt: `{truncated_prompt}`\n"
            f"Budget: ${self.daily_cost:.2f}/${self.config.daily_budget_usd}"
        )

        try:
            # Run subprocess
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds
            )

            end_time = datetime.now()
            latency = (end_time - start_time).total_seconds()

            # Check return code
            if result.returncode != 0:
                error_msg = f"Claude Code failed with code {result.returncode}: {result.stderr}"
                logger.error(error_msg)
                self._log_error(prompt, error_msg)

                return LLMResponse(
                    success=False,
                    error=error_msg,
                    latency_seconds=latency,
                    timestamp=start_time.isoformat()
                )

            # Parse JSON response
            try:
                response_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                error_msg = f"JSON parse error: {e}\nOutput: {result.stdout[:500]}"
                logger.error(error_msg)
                self._log_error(prompt, error_msg)

                return LLMResponse(
                    success=False,
                    error=error_msg,
                    latency_seconds=latency,
                    timestamp=start_time.isoformat()
                )

            # Extract cost if available
            cost = response_data.get('total_cost_usd', 0.0)
            self.daily_cost += cost
            self.call_count += 1

            # Create response
            response = LLMResponse(
                success=True,
                data=response_data,
                cost_usd=cost,
                latency_seconds=latency,
                model=self.config.model.value,
                timestamp=start_time.isoformat()
            )

            # Logging
            self._log_call(prompt, response)
            if cost > 0:
                self._log_cost(cost)

            logger.info(f"Claude Code success: latency={latency:.2f}s, cost=${cost:.4f}")

            # Send Telegram notification: LLM completed
            success_emoji = "✅" if os.getenv("TELEGRAM_INCLUDE_EMOJIS", "true").lower() == "true" else ""
            self._send_telegram_notification(
                f"{success_emoji} *LLM Completed*\n"
                f"Latency: `{latency:.2f}s`\n"
                f"Cost: `${cost:.4f}`\n"
                f"Total Today: `${self.daily_cost:.2f}/${self.config.daily_budget_usd}`"
            )

            return response

        except subprocess.TimeoutExpired:
            error_msg = f"Claude Code timeout after {self.config.timeout_seconds}s"
            logger.error(error_msg)
            self._log_error(prompt, error_msg)

            # Send Telegram notification: LLM error
            error_emoji = "❌" if os.getenv("TELEGRAM_INCLUDE_EMOJIS", "true").lower() == "true" else ""
            self._send_telegram_notification(
                f"{error_emoji} *LLM Timeout*\n"
                f"Error: `{error_msg}`\n"
                f"Prompt: `{truncated_prompt}`"
            )

            return LLMResponse(
                success=False,
                error=error_msg,
                latency_seconds=self.config.timeout_seconds,
                timestamp=start_time.isoformat()
            )

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.exception(error_msg)
            self._log_error(prompt, error_msg)

            # Send Telegram notification: LLM error
            error_emoji = "❌" if os.getenv("TELEGRAM_INCLUDE_EMOJIS", "true").lower() == "true" else ""
            self._send_telegram_notification(
                f"{error_emoji} *LLM Error*\n"
                f"Error: `{str(e)[:200]}`\n"
                f"Prompt: `{truncated_prompt}`"
            )

            return LLMResponse(
                success=False,
                error=error_msg,
                timestamp=start_time.isoformat()
            )

    def get_daily_stats(self) -> Dict[str, Any]:
        """
        Get statistics for today's LLM usage.

        Returns:
            Dictionary with cost, call count, and budget info
        """
        return {
            "date": date.today().isoformat(),
            "total_cost_usd": self.daily_cost,
            "total_calls": self.call_count,
            "budget_usd": self.config.daily_budget_usd,
            "budget_remaining_usd": max(0, self.config.daily_budget_usd - self.daily_cost),
            "budget_used_pct": (self.daily_cost / self.config.daily_budget_usd * 100)
                if self.config.daily_budget_usd > 0 else 0,
            "hourly_calls": self.hourly_calls,
            "hourly_limit": self.config.max_calls_per_hour
        }

    def reset_daily_cost(self):
        """Reset daily cost counter (called at midnight)"""
        logger.info(f"Resetting daily cost: ${self.daily_cost:.2f}")
        self.daily_cost = 0.0
        self.call_count = 0

    # Convenience methods for trading operations

    def screen_stocks(self, criteria: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """
        Screen stocks using /screen command.

        Args:
            criteria: Screening criteria (volume, price, momentum, etc.)

        Returns:
            LLMResponse with screened symbols and scores
        """
        if criteria:
            criteria_str = json.dumps(criteria)
            prompt = f"/screen {criteria_str}"
        else:
            prompt = "/screen momentum stocks"

        return self.invoke(prompt)

    def analyze_trade(self, symbol: str, **kwargs) -> LLMResponse:
        """
        Analyze trade setup using /analyze-trade command.

        Args:
            symbol: Stock symbol to analyze
            **kwargs: Additional parameters (entry_price, etc.)

        Returns:
            LLMResponse with entry signal and parameters
        """
        params = " ".join([f"--{k.replace('_', '-')} {v}" for k, v in kwargs.items()])
        prompt = f"/analyze-trade {symbol} {params}".strip()

        return self.invoke(prompt)

    def optimize_entry(self, symbol: str, entry_price: float) -> LLMResponse:
        """
        Optimize position parameters using /optimize-entry command.

        Args:
            symbol: Stock symbol
            entry_price: Proposed entry price

        Returns:
            LLMResponse with optimized position size, stop, target
        """
        prompt = f"/optimize-entry {symbol} --entry {entry_price}"
        return self.invoke(prompt)

    def review_performance(self) -> LLMResponse:
        """
        Review today's performance using /review-performance command.

        Returns:
            LLMResponse with performance analysis and suggestions
        """
        return self.invoke("/review-performance")

    def backtest_strategy(self, strategy_params: Dict[str, Any]) -> LLMResponse:
        """
        Backtest strategy using /backtest-strategy command.

        Args:
            strategy_params: Strategy parameters to backtest

        Returns:
            LLMResponse with backtest results and metrics
        """
        params_str = json.dumps(strategy_params)
        prompt = f"/backtest-strategy {params_str}"
        return self.invoke(prompt)
