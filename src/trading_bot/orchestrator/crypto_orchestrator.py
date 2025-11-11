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

# Crypto config imports are optional - only needed for crypto trading mode
try:
    from trading_bot.crypto_config import CryptoConfig
    from trading_bot.market_data.crypto_service import CryptoDataService
    HAS_CRYPTO = True
except ImportError:
    # Crypto trading not available (config classes not implemented)
    CryptoConfig = None
    CryptoDataService = None
    HAS_CRYPTO = False

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
            # Direct technical screening (bypass broken MCP /screen command)
            candidates = []

            for symbol in self.config.symbols:
                try:
                    # Get current crypto data
                    price = self.crypto_data.get_current_price(symbol)
                    if not price:
                        continue

                    # Get 24h volume and price change
                    volume_24h = self.crypto_data.get_24h_volume(symbol)
                    price_change_24h = self.crypto_data.get_price_change_pct(symbol, hours=24)

                    if not volume_24h or not price_change_24h:
                        continue

                    # Simple momentum screening:
                    # - Price moved 2-8% in 24h (not too flat, not too volatile)
                    # - Volume above average (indicates interest)
                    abs_change = abs(price_change_24h)
                    if 2.0 <= abs_change <= 8.0 and volume_24h > 0:
                        candidates.append({
                            "symbol": symbol,
                            "price": price,
                            "change_24h": price_change_24h,
                            "volume_24h": volume_24h,
                            "momentum": "bullish" if price_change_24h > 0 else "bearish"
                        })
                        logger.info(f"Candidate: {symbol} @ ${price} ({price_change_24h:+.2f}% 24h)")

                except Exception as e:
                    logger.warning(f"Failed to screen {symbol}: {e}")
                    continue

            # Sort by absolute momentum (highest movers first)
            candidates.sort(key=lambda x: abs(x["change_24h"]), reverse=True)
            self.watchlist = candidates[:5]  # Top 5 candidates

            top_symbols = ", ".join([c["symbol"] for c in self.watchlist])
            self._notify(
                f"✅ *Screening Complete*\n"
                f"Found {len(candidates)} total, tracking top {len(self.watchlist)}\n"
                f"Top candidates: {top_symbols or 'None'}"
            )

            # Execute trades for top candidates (if not at max positions)
            # Max positions = 100% / max_position_pct (e.g., 3% each = max 33 positions)
            max_positions = int(100 / self.config.max_position_pct)
            if self.watchlist and len(self.active_positions) < max_positions:
                self._execute_entry_orders()

        except Exception as e:
            self._notify(f"Screening error: {str(e)}", "error")

    def _execute_entry_orders(self):
        """Execute entry orders for watchlist candidates."""
        max_positions = int(100 / self.config.max_position_pct)
        slots_available = max_positions - len(self.active_positions)

        for candidate in self.watchlist[:slots_available]:
            try:
                symbol = candidate["symbol"]
                price = candidate["price"]
                momentum = candidate["momentum"]

                # Skip if already have position in this symbol
                if any(p["symbol"] == symbol for p in self.active_positions):
                    logger.info(f"Already have position in {symbol}, skipping")
                    continue

                # Use fixed position size from config
                position_size_usd = self.config.position_size_usd
                quantity = position_size_usd / price

                logger.info(
                    f"PAPER TRADE ENTRY: {symbol} @ ${price:.2f} x {quantity:.4f} "
                    f"(~${position_size_usd:.2f}) - {momentum} momentum"
                )

                # In paper trading mode, just track the position
                if self.mode == "paper":
                    position = {
                        "symbol": symbol,
                        "entry_price": price,
                        "quantity": quantity,
                        "entry_time": datetime.now().isoformat(),
                        "momentum": momentum
                    }
                    self.active_positions.append(position)

                    self._notify(
                        f"🟢 *Paper Trade Entry*\n"
                        f"{symbol} @ ${price:.2f}\n"
                        f"Qty: {quantity:.4f} (~${position_size_usd:.2f})\n"
                        f"Momentum: {momentum}"
                    )
                else:
                    # TODO: Implement live trading via Alpaca
                    logger.warning(f"Live trading not implemented yet for {symbol}")

            except Exception as e:
                logger.error(f"Failed to execute entry for {candidate.get('symbol')}: {e}")

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
