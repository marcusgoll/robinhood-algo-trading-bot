#!/usr/bin/env python3
"""
Crypto Trading Orchestrator

24/7 cryptocurrency trading orchestration using interval-based scheduling.
Coordinates screening every 2hrs, position monitoring every 5min.
"""

import time
import logging
from datetime import datetime
from typing import Optional, Any, List, Dict

from trading_bot.orchestrator.interval_scheduler import IntervalScheduler

# LLM imports are optional - only needed if MULTI_AGENT_ENABLED=true
try:
    from trading_bot.llm.claude_manager import ClaudeCodeManager
    HAS_LLM = True
except ImportError:
    # Multi-agent system not available (excluded from Docker or incomplete setup)
    ClaudeCodeManager = None
    HAS_LLM = False

from trading_bot.config.crypto_config import CryptoConfig
from trading_bot.market_data.crypto_service import CryptoDataService

logger = logging.getLogger(__name__)


class CryptoOrchestrator:
    """
    24/7 Crypto trading orchestrator.

    Workflows:
    - Screening: Every 2 hours (scan BTC, ETH, alts for momentum)
    - Monitoring: Every 5 minutes (check positions, adjust stops)
    - Rebalancing: Daily (portfolio rebalance)
    """

    def __init__(
        self,
        crypto_config: CryptoConfig,
        claude_manager: ClaudeCodeManager,
        mode: str = "paper"
    ):
        """
        Initialize crypto orchestrator.

        Args:
            crypto_config: Crypto configuration
            claude_manager: Shared LLM manager (budget tracking)
            mode: Operation mode (paper/live)
        """
        self.config = crypto_config
        self.claude_manager = claude_manager
        self.mode = mode

        # Initialize crypto data service
        self.crypto_data = CryptoDataService()

        # Initialize interval scheduler
        self.scheduler = IntervalScheduler()

        # Runtime state
        self.running = False
        self.active_positions = []
        self.watchlist = []

        # Setup scheduled workflows
        self._setup_schedule()

        logger.info(f"CryptoOrchestrator initialized in {mode} mode")
        logger.info(f"Symbols: {', '.join(crypto_config.symbols)}")

    def _notify(self, message: str, level: str = "info"):
        """Send log + Telegram notification."""
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)

        if self.claude_manager.telegram_enabled:
            emoji = {"error": "🚨", "warning": "⚠️"}.get(level, "🪙")
            self.claude_manager._send_telegram_notification(f"{emoji} {message}")

    def _setup_schedule(self):
        """Setup interval-based workflows."""
        # Screening every 2 hours
        self.scheduler.schedule_hourly(
            "crypto_screening",
            hours=self.config.screening_interval_hours,
            callback=self.run_screening_workflow,
            run_immediately=True  # Run on startup
        )

        # Position monitoring every 5 minutes
        self.scheduler.schedule_interval(
            "crypto_monitoring",
            interval_minutes=self.config.monitoring_interval_minutes,
            callback=self.run_monitoring_workflow,
            run_immediately=False  # Wait for first interval
        )

        # Daily rebalancing
        self.scheduler.schedule_hourly(
            "crypto_rebalance",
            hours=self.config.rebalance_interval_hours,
            callback=self.run_rebalance_workflow,
            run_immediately=False
        )

    def run_screening_workflow(self):
        """Screen crypto symbols for trading opportunities."""
        self._notify("🔍 *Crypto Screening Started*")

        try:
            # Build symbol list for screening
            symbols = " ".join(self.config.symbols)

            # Invoke LLM screening command
            response = self.claude_manager.invoke(
                f"/screen --asset-type crypto --symbols {symbols}",
                output_format="json"
            )

            if not response.success:
                raise Exception(f"Screening failed: {response.error}")

            data = response.data or {}
            candidates = data.get("watchlist", [])
            self.watchlist = candidates

            top_symbols = ", ".join([c.get("symbol", "?") for c in candidates[:3]])
            self._notify(
                f"✅ *Screening Complete*\n"
                f"Found {len(candidates)} candidates\n"
                f"Top 3: {top_symbols}"
            )

        except Exception as e:
            self._notify(f"Screening error: {str(e)}", "error")

    def run_monitoring_workflow(self):
        """Monitor active crypto positions."""
        if not self.active_positions:
            logger.debug("No active crypto positions to monitor")
            return

        logger.info(f"Monitoring {len(self.active_positions)} crypto positions")

        for position in self.active_positions:
            try:
                symbol = position["symbol"]
                entry_price = position["entry_price"]

                # Get current price
                current_price = self.crypto_data.get_current_price(symbol)
                if not current_price:
                    continue

                # Calculate P&L
                pnl_pct = ((current_price - entry_price) / entry_price) * 100

                # Check stop loss
                if pnl_pct <= -self.config.stop_loss_pct:
                    self._notify(
                        f"🛑 *Stop Loss Hit*\n"
                        f"{symbol}: {pnl_pct:.2f}%\n"
                        f"Entry: ${entry_price:.2f} → Current: ${current_price:.2f}",
                        "warning"
                    )
                    # TODO: Execute sell order

            except Exception as e:
                logger.error(f"Error monitoring {position.get('symbol')}: {e}")

    def run_rebalance_workflow(self):
        """Daily portfolio rebalancing."""
        logger.info("Running crypto portfolio rebalance")
        # TODO: Implement rebalancing logic

    def run_loop(self):
        """Main event loop - check scheduler every 60 seconds."""
        logger.info("Starting crypto orchestrator event loop")
        logger.info(f"Screening: every {self.config.screening_interval_hours}hr")
        logger.info(f"Monitoring: every {self.config.monitoring_interval_minutes}min")

        self.running = True

        try:
            while self.running:
                # Check scheduled tasks
                triggered = self.scheduler.check_triggers()

                if triggered:
                    logger.info(f"Triggered crypto tasks: {triggered}")

                # Sleep 60 seconds
                time.sleep(60)

        except KeyboardInterrupt:
            logger.info("Crypto orchestrator stopped by user")
            self.running = False
        except Exception as e:
            logger.error(f"Crypto orchestrator error: {e}")
            raise

    def stop(self):
        """Stop the crypto orchestrator."""
        logger.info("Stopping crypto orchestrator")
        self.running = False

    def get_status(self) -> Dict[str, Any]:
        """Get current crypto orchestrator status."""
        next_task = self.scheduler.get_next_trigger()

        return {
            "running": self.running,
            "mode": self.mode,
            "symbols": self.config.symbols,
            "active_positions": len(self.active_positions),
            "watchlist_size": len(self.watchlist),
            "next_task": next_task["task"] if next_task else None,
            "next_run_seconds": next_task["seconds_until"] if next_task else None
        }
