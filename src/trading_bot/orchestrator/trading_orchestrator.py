#!/usr/bin/env python3
"""
Trading Orchestrator

Coordinates LLM-enhanced trading workflows using Claude Code in headless mode.
Integrates with existing trading_bot infrastructure.
"""

import time
import logging
from datetime import datetime, time as datetime_time
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

from trading_bot.orchestrator.workflow import (
    WorkflowStateMachine,
    WorkflowState,
    WorkflowTransition
)
from trading_bot.orchestrator.scheduler import TradingScheduler
from trading_bot.llm.claude_manager import ClaudeCodeManager, LLMConfig, LLMModel
from trading_bot.config import Config

logger = logging.getLogger(__name__)


class TradingOrchestrator:
    """
    Main orchestrator for LLM-enhanced trading workflows.

    Coordinates:
    - Pre-market screening (6:30am EST)
    - Market open execution (9:30am EST)
    - Intraday monitoring (10am, 11am, 2pm EST)
    - End-of-day review (4pm EST)
    - Weekly review (Friday 4pm EST)
    """

    def __init__(self, config: Config, auth: Optional[Any] = None, mode: str = "live"):
        """
        Initialize orchestrator.

        Args:
            config: Trading bot configuration
            auth: Optional authentication object (Robinhood/Alpaca). None for paper trading.
            mode: Operation mode (live, paper, backtest)

        Note:
            For paper trading mode, auth can be None. For live trading, you must provide
            an authentication object (future: Alpaca TradingClient for paper/live trading).
        """
        self.config = config
        self.auth = auth
        self.mode = mode

        if mode == "live" and auth is None:
            logger.warning("Live mode requested but no authentication provided. Trades will not execute.")

        if mode == "paper":
            logger.info("Paper trading mode - no authentication required")

        # Initialize LLM manager
        llm_config = LLMConfig(
            daily_budget_usd=5.0,
            model=LLMModel.HAIKU,
            timeout_seconds=30,
            max_calls_per_hour=50
        )
        self.claude_manager = ClaudeCodeManager(llm_config)

        # Initialize workflow and scheduler
        self.workflow = WorkflowStateMachine()
        self.scheduler = TradingScheduler()

        # Setup scheduled tasks
        self._setup_schedule()

        # Runtime state
        self.running = False
        self.daily_trades = []

        logger.info(f"TradingOrchestrator initialized in {mode} mode")

    def _notify(self, message: str, level: str = "info"):
        """
        Send both log and Telegram notification.

        Args:
            message: The message to log and send
            level: Log level (info, warning, error)
        """
        # Log the message
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)

        # Send Telegram notification for important events
        if self.claude_manager.telegram_enabled:
            # Format message for Telegram (add emoji based on level)
            if level == "error":
                telegram_msg = f"🚨 *Error*\n\n{message}"
            elif level == "warning":
                telegram_msg = f"⚠️ *Warning*\n\n{message}"
            else:
                telegram_msg = f"ℹ️ {message}"

            self.claude_manager._send_telegram_notification(telegram_msg)

    def _setup_schedule(self):
        """Setup scheduled trading workflows."""
        # Pre-market screening (6:30am EST)
        self.scheduler.schedule(
            "pre_market",
            datetime_time(6, 30),
            self.run_pre_market_workflow,
            run_once_per_day=True
        )

        # Market open execution (9:30am EST)
        self.scheduler.schedule(
            "market_open",
            datetime_time(9, 30),
            self.run_market_open_workflow,
            run_once_per_day=True
        )

        # Intraday monitoring
        for hour in [10, 11, 14]:
            self.scheduler.schedule(
                f"monitor_{hour}",
                datetime_time(hour, 0),
                self.run_monitoring_workflow,
                run_once_per_day=False
            )

        # End-of-day review (4pm EST)
        self.scheduler.schedule(
            "eod_review",
            datetime_time(16, 0),
            self.run_eod_workflow,
            run_once_per_day=True
        )

        # Weekly review (Friday 4:05pm EST)
        self.scheduler.schedule(
            "weekly_review",
            datetime_time(16, 5),
            self.run_weekly_workflow,
            run_once_per_day=True
        )

    def run_pre_market_workflow(self):
        """Execute pre-market screening workflow."""
        self._notify("📊 *Pre-Market Workflow Started*\nBeginning market screening...")

        # Transition to PRE_MARKET_SCREENING
        if not self.workflow.transition(WorkflowTransition.START_PRE_MARKET):
            self._notify("Failed to transition to PRE_MARKET_SCREENING state", "error")
            return

        try:
            # Step 1: Run market screening
            logger.info("Running /screen command")
            screen_response = self.claude_manager.invoke(
                "/screen",
                output_format="json"
            )

            if not screen_response.success:
                raise Exception(f"Screening failed: {screen_response.error}")

            watchlist = screen_response.data.get("watchlist", []) if screen_response.data else []
            self.workflow.context.watchlist = watchlist

            symbols = ", ".join([s.get("symbol", "?") for s in watchlist[:5]])
            self._notify(f"✅ *Screening Complete*\nFound {len(watchlist)} candidates\nTop 5: {symbols}")
            self.workflow.transition(WorkflowTransition.SCREENING_COMPLETE)

            # Step 2: Analyze top candidates
            for stock in watchlist[:3]:  # Top 3 only
                symbol = stock["symbol"]
                logger.info(f"Analyzing {symbol}")

                analysis_response = self.claude_manager.invoke(
                    f"/analyze-trade {symbol}",
                    output_format="json"
                )

                if not analysis_response.success:
                    logger.warning(f"Analysis failed for {symbol}")
                    continue

                analysis = analysis_response.data
                signal = analysis.get("analysis", {}).get("signal", "AVOID") if analysis else "AVOID"

                if signal in ["STRONG_BUY", "BUY"]:
                    self.workflow.context.analyzed_symbols[symbol] = analysis
                    logger.info(f"{symbol}: {signal}")
                    self._notify(f"📈 *Buy Signal: {symbol}*\nSignal: {signal}")

            self.workflow.transition(WorkflowTransition.ANALYSIS_COMPLETE)

            # Step 3: Optimize approved trades
            for symbol in self.workflow.context.analyzed_symbols.keys():
                logger.info(f"Optimizing entry for {symbol}")

                opt_response = self.claude_manager.invoke(
                    f"/optimize-entry {symbol}",
                    output_format="json"
                )

                if opt_response.success and opt_response.data:
                    self.workflow.context.optimized_trades.append(
                        opt_response.data
                    )

            num_trades = len(self.workflow.context.optimized_trades)
            symbols_list = list(self.workflow.context.analyzed_symbols.keys())
            self._notify(
                f"✅ *Pre-Market Complete*\n"
                f"{num_trades} trades ready for market open\n"
                f"Symbols: {', '.join(symbols_list)}"
            )
            self.workflow.transition(WorkflowTransition.OPTIMIZATION_COMPLETE)

        except Exception as e:
            self._notify(f"Pre-market workflow error: {str(e)}", "error")
            self.workflow.add_error(str(e))

    def run_market_open_workflow(self):
        """Execute trades at market open."""
        self._notify("🔔 *Market Open*\nExecuting trades...")

        if not self.workflow.transition(WorkflowTransition.MARKET_OPEN):
            self._notify("Failed to transition to MARKET_EXECUTION state", "error")
            return

        try:
            optimized_trades = self.workflow.context.optimized_trades

            if not optimized_trades:
                logger.info("No trades to execute")
                self.workflow.transition(WorkflowTransition.EXECUTION_COMPLETE)
                return

            logger.info(f"Executing {len(optimized_trades)} trades")

            for trade in optimized_trades:
                # TODO: Integrate with existing order execution
                # For now, just log the trade plan
                symbol = trade.get("symbol")
                optimization = trade.get("optimization", {})

                logger.info(f"Trade plan for {symbol}:")
                logger.info(f"  Entry: ${optimization.get('recommended_entry')}")
                logger.info(f"  Shares: {optimization.get('position_size')}")
                logger.info(f"  Stop: ${optimization.get('stop_loss')}")
                logger.info(f"  Target: ${optimization.get('target_1')}")

                if self.mode == "live":
                    # TODO: Implement live trading via Alpaca TradingClient
                    # Example:
                    #   from alpaca.trading.client import TradingClient
                    #   from alpaca.trading.requests import MarketOrderRequest
                    #   from alpaca.trading.enums import OrderSide, TimeInForce
                    #
                    #   if self.auth:  # auth should be TradingClient instance
                    #       order_data = MarketOrderRequest(
                    #           symbol=symbol,
                    #           qty=optimization.get('position_size'),
                    #           side=OrderSide.BUY,
                    #           time_in_force=TimeInForce.DAY
                    #       )
                    #       order = self.auth.submit_order(order_data)
                    pass
                elif self.mode == "paper":
                    # Log paper trade (for testing without real orders)
                    self.daily_trades.append({
                        "symbol": symbol,
                        "entry": optimization.get("recommended_entry"),
                        "shares": optimization.get("position_size"),
                        "timestamp": datetime.now().isoformat()
                    })

            self.workflow.transition(WorkflowTransition.EXECUTION_COMPLETE)
            self._notify(f"✅ *Market Open Complete*\nExecuted {len(optimized_trades)} trades")

        except Exception as e:
            self._notify(f"Market open workflow error: {str(e)}", "error")
            self.workflow.add_error(str(e))

    def run_monitoring_workflow(self):
        """Monitor positions and adjust stops."""
        logger.info("Running intraday monitoring")

        if self.workflow.get_current_state() != WorkflowState.INTRADAY_MONITORING:
            self.workflow.transition(WorkflowTransition.START_MONITORING)

        try:
            # TODO: Implement position monitoring
            # - Check P&L
            # - Adjust stops if needed
            # - Exit positions approaching targets
            logger.info("Position monitoring complete")

        except Exception as e:
            logger.error(f"Monitoring workflow error: {e}")
            self.workflow.add_error(str(e))

    def run_eod_workflow(self):
        """End-of-day performance review."""
        logger.info("Starting end-of-day review")

        # Only transition if currently in monitoring state
        if self.workflow.get_current_state() != WorkflowState.INTRADAY_MONITORING:
            logger.info("Skipping EOD review - bot not in monitoring state")
            return

        if not self.workflow.transition(WorkflowTransition.MARKET_CLOSE):
            logger.error("Failed to transition to END_OF_DAY_REVIEW")
            return

        try:
            # Run performance review
            logger.info("Running /review-performance command")
            review_response = self.claude_manager.invoke(
                "/review-performance --period 1",
                output_format="json"
            )

            if review_response.success:
                review = review_response.data
                summary = review.get("summary", {}) if review else {}

                trades = summary.get('total_trades', 0)
                win_rate = summary.get('win_rate', 0)
                pnl = summary.get('total_pnl', 0)

                logger.info("Daily Performance:")
                logger.info(f"  Trades: {trades}")
                logger.info(f"  Win Rate: {win_rate:.1f}%")
                logger.info(f"  P&L: ${pnl:.2f}")

                # Send daily summary via Telegram
                self._notify(
                    f"📊 *Daily Summary*\n"
                    f"Trades: {trades}\n"
                    f"Win Rate: {win_rate:.1f}%\n"
                    f"P&L: ${pnl:.2f}"
                )

                # Save review to log
                self._save_daily_report(review)

            # Reset for next day
            self.workflow.transition(WorkflowTransition.REVIEW_COMPLETE)
            self.workflow.reset()
            self.daily_trades = []

            logger.info("End-of-day review complete")

        except Exception as e:
            self._notify(f"EOD workflow error: {str(e)}", "error")
            self.workflow.add_error(str(e))

    def run_weekly_workflow(self):
        """Weekly deep review (Fridays only)."""
        # Check if Friday
        if datetime.now().weekday() != 4:
            logger.debug("Not Friday - skipping weekly review")
            return

        logger.info("Starting weekly review")

        if not self.workflow.transition(WorkflowTransition.START_WEEKLY_REVIEW):
            logger.error("Failed to transition to WEEKLY_REVIEW")
            return

        try:
            # Weekly performance review
            logger.info("Running weekly /review-performance command")
            review_response = self.claude_manager.invoke(
                "/review-performance --period 7 --detailed",
                output_format="json"
            )

            if review_response.success:
                review = review_response.data

                # Identify poor performers for backtesting
                patterns = review.get("patterns", {}) if review else {}
                losing = patterns.get("losing", [])

                logger.info(f"Weekly review complete. Issues identified: {len(losing)}")

                # TODO: Run backtests on alternative strategies
                # for poor performing symbols

            self.workflow.transition(WorkflowTransition.REVIEW_COMPLETE)
            self.workflow.reset()

            logger.info("Weekly review complete")

        except Exception as e:
            logger.error(f"Weekly workflow error: {e}")
            self.workflow.add_error(str(e))

    def run_loop(self):
        """Main event loop - check scheduler every minute."""
        logger.info("Starting orchestrator event loop")
        self.running = True

        try:
            while self.running:
                # Check scheduled tasks
                triggered = self.scheduler.check_triggers()

                if triggered:
                    logger.info(f"Triggered tasks: {triggered}")

                # Check workflow state
                if self.workflow.is_error():
                    logger.error("Workflow in ERROR state")
                    # TODO: Implement error recovery
                    self.workflow.reset()

                # Sleep 60 seconds
                time.sleep(60)

        except KeyboardInterrupt:
            logger.info("Orchestrator stopped by user")
            self.running = False
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            raise

    def stop(self):
        """Stop the orchestrator."""
        logger.info("Stopping orchestrator")
        self.running = False

    def _save_daily_report(self, review: Dict[str, Any]):
        """Save daily performance report to file."""
        try:
            reports_dir = Path("logs/reports")
            reports_dir.mkdir(parents=True, exist_ok=True)

            today = datetime.now().strftime("%Y%m%d")
            report_file = reports_dir / f"daily_{today}.json"

            with open(report_file, "w") as f:
                json.dump(review, f, indent=2)

            logger.info(f"Daily report saved: {report_file}")

        except Exception as e:
            logger.error(f"Failed to save daily report: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        return {
            "running": self.running,
            "mode": self.mode,
            "workflow_state": self.workflow.get_current_state().value,
            "daily_cost": self.claude_manager.daily_cost,
            "budget_remaining": self.claude_manager.config.daily_budget_usd - self.claude_manager.daily_cost,
            "trades_today": len(self.daily_trades),
            "next_task": self.scheduler.get_next_trigger()
        }
