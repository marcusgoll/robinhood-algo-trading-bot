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

# Alpaca trading client for order execution
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# LLM imports are optional - only needed if MULTI_AGENT_ENABLED=true
try:
    from trading_bot.llm.claude_manager import ClaudeCodeManager, LLMConfig, LLMModel
    from trading_bot.llm.examples.multi_agent_consensus_workflow import MultiAgentTradingWorkflow
    HAS_LLM = True
except ImportError:
    # Multi-agent system not available (excluded from Docker or incomplete setup)
    ClaudeCodeManager = None
    LLMConfig = None
    LLMModel = None
    MultiAgentTradingWorkflow = None
    HAS_LLM = False

# Technical Analysis framework
try:
    from trading_bot.technical_analysis import TACoordinator
    HAS_TA_FRAMEWORK = True
except ImportError:
    TACoordinator = None
    HAS_TA_FRAMEWORK = False

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

        # Initialize LLM manager (if available)
        if HAS_LLM:
            llm_config = LLMConfig(
                daily_budget_usd=5.0,
                model=LLMModel.HAIKU,
                timeout_seconds=30,
                max_calls_per_hour=50
            )
            self.claude_manager = ClaudeCodeManager(llm_config)

            # Initialize multi-agent trading workflow
            self.multi_agent_workflow = MultiAgentTradingWorkflow()
            logger.info("Multi-agent trading system initialized with 8 specialized agents")
        else:
            self.claude_manager = None
            self.multi_agent_workflow = None
            logger.info("Multi-agent system not available - running in basic mode")

        # Initialize Technical Analysis framework (if available)
        if HAS_TA_FRAMEWORK:
            self.ta_coordinator = TACoordinator(account_size=100000.0)
            logger.info("Technical Analysis framework initialized (20 quantifiable tools)")
        else:
            self.ta_coordinator = None
            logger.info("TA framework not available - skipping TA analysis")

        # Initialize workflow and scheduler
        self.workflow = WorkflowStateMachine()
        self.scheduler = TradingScheduler()

        # Setup scheduled tasks
        self._setup_schedule()

        # Runtime state
        self.running = False
        self.daily_trades = []

        # Portfolio tracking (for multi-agent position sizing)
        self.portfolio_value = 100000.0  # Default $100k portfolio
        self.cash_available = 100000.0   # Default $100k cash

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

        # Intraday scanning - Every 30 minutes during market hours (10am-3:30pm)
        scan_times = [
            (10, 0), (10, 30),
            (11, 0), (11, 30),
            (12, 0), (12, 30),
            (13, 0), (13, 30),
            (14, 0), (14, 30),
            (15, 0), (15, 30)
        ]
        for hour, minute in scan_times:
            self.scheduler.schedule(
                f"intraday_scan_{hour:02d}{minute:02d}",
                datetime_time(hour, minute),
                self.run_intraday_scan_workflow,
                run_once_per_day=False
            )

        # After-hours screening - Every 2 hours
        for hour in [18, 20, 22]:
            self.scheduler.schedule(
                f"afterhours_scan_{hour}",
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
                symbol = trade.get("symbol")
                optimization = trade.get("optimization", {})
                recommended_entry = optimization.get('recommended_entry')
                position_size = optimization.get('position_size')
                stop_loss = optimization.get('stop_loss')
                target = optimization.get('target_1')

                logger.info(f"Trade plan for {symbol}:")
                logger.info(f"  Entry: ${recommended_entry}")
                logger.info(f"  Shares: {position_size}")
                logger.info(f"  Stop: ${stop_loss}")
                logger.info(f"  Target: ${target}")

                if self.mode == "live":
                    # Execute live trading via Alpaca TradingClient
                    if not self.auth:
                        logger.error(f"Cannot execute live trade for {symbol}: No TradingClient configured")
                        self._notify(
                            f"❌ *Live Trade Failed*\n{symbol}: No authentication configured",
                            "error"
                        )
                        continue

                    if not isinstance(self.auth, TradingClient):
                        logger.error(f"Auth object is not a TradingClient instance: {type(self.auth)}")
                        self._notify(
                            f"❌ *Live Trade Failed*\n{symbol}: Invalid auth object",
                            "error"
                        )
                        continue

                    try:
                        # Submit market order for live execution
                        order_request = MarketOrderRequest(
                            symbol=symbol,
                            qty=position_size,
                            side=OrderSide.BUY,
                            time_in_force=TimeInForce.DAY
                        )

                        logger.info(f"Submitting live order: {symbol} x {position_size} shares")
                        order_response = self.auth.submit_order(order_request)

                        # Log successful order
                        logger.info(f"✅ Live order placed: {order_response.id} - Status: {order_response.status}")

                        # Track the trade
                        trade_record = {
                            "symbol": symbol,
                            "entry": recommended_entry,
                            "shares": position_size,
                            "stop_loss": stop_loss,
                            "target": target,
                            "timestamp": datetime.now().isoformat(),
                            "order_id": str(order_response.id),
                            "status": order_response.status
                        }
                        self.daily_trades.append(trade_record)

                        # Send notification
                        self._notify(
                            f"🟢 *Live Trade Executed*\n"
                            f"{symbol} x {position_size} shares\n"
                            f"Entry: ${recommended_entry:.2f}\n"
                            f"Stop: ${stop_loss:.2f}\n"
                            f"Target: ${target:.2f}\n"
                            f"Order ID: {order_response.id}"
                        )

                    except Exception as e:
                        logger.error(f"Failed to execute live order for {symbol}: {e}")
                        self._notify(
                            f"❌ *Live Trade Failed*\n{symbol}: {str(e)}",
                            "error"
                        )

                elif self.mode == "paper":
                    # Log paper trade (for testing without real orders)
                    trade_record = {
                        "symbol": symbol,
                        "entry": recommended_entry,
                        "shares": position_size,
                        "stop_loss": stop_loss,
                        "target": target,
                        "timestamp": datetime.now().isoformat()
                    }
                    self.daily_trades.append(trade_record)

                    logger.info(f"📝 Paper trade logged: {symbol} x {position_size} shares")

            self.workflow.transition(WorkflowTransition.EXECUTION_COMPLETE)
            self._notify(f"✅ *Market Open Complete*\nExecuted {len(optimized_trades)} trades")

        except Exception as e:
            self._notify(f"Market open workflow error: {str(e)}", "error")
            self.workflow.add_error(str(e))

    def run_intraday_scan_workflow(self):
        """Quick intraday scan for new opportunities + monitor existing positions."""
        logger.info("Running intraday scan workflow")

        try:
            # First, monitor existing positions
            self.run_monitoring_workflow()

            # Then scan for new opportunities (lighter than pre-market)
            logger.info("Scanning for intraday breakouts/momentum plays")

            # Use LLM for quick momentum screening
            scan_response = self.claude_manager.invoke(
                "/screen-momentum --intraday --limit 5",
                output_format="json"
            )

            if not scan_response.success or not scan_response.data:
                logger.info("No new intraday opportunities found")
                return

            candidates = scan_response.data.get("candidates", [])
            if not candidates:
                logger.info("Screening returned no candidates")
                return

            logger.info(f"Found {len(candidates)} intraday candidates")
            symbols = [c.get("symbol") for c in candidates[:3]]
            self._notify(f"📊 *Intraday Scan*\nFound {len(candidates)} opportunities\nTop: {', '.join(symbols)}")

            # Analyze top 2 candidates only (faster than pre-market)
            trades_executed = 0
            for stock in candidates[:2]:
                symbol = stock.get("symbol")
                logger.info(f"Analyzing intraday setup for {symbol}")

                analysis_response = self.claude_manager.invoke(
                    f"/analyze-trade {symbol} --quick",
                    output_format="json"
                )

                if not analysis_response.success:
                    logger.warning(f"Analysis failed for {symbol}")
                    continue

                analysis = analysis_response.data
                signal = analysis.get("analysis", {}).get("signal", "AVOID") if analysis else "AVOID"

                if signal in ["STRONG_BUY", "BUY"]:
                    # Get quick optimization
                    opt_response = self.claude_manager.invoke(
                        f"/optimize-entry {symbol} --quick",
                        output_format="json"
                    )

                    if opt_response.success and opt_response.data:
                        trade = opt_response.data
                        optimization = trade.get("optimization", {})
                        recommended_entry = optimization.get('recommended_entry')
                        position_size = optimization.get('position_size')
                        stop_loss = optimization.get('stop_loss')
                        target = optimization.get('target_1')

                        logger.info(f"Intraday trade setup for {symbol}:")
                        logger.info(f"  Entry: ${recommended_entry}, Size: {position_size}, Stop: ${stop_loss}, Target: ${target}")

                        if self.mode == "live" and self.auth and isinstance(self.auth, TradingClient):
                            try:
                                order_request = MarketOrderRequest(
                                    symbol=symbol,
                                    qty=position_size,
                                    side=OrderSide.BUY,
                                    time_in_force=TimeInForce.DAY
                                )

                                order_response = self.auth.submit_order(order_request)
                                logger.info(f"✅ Intraday order placed: {order_response.id}")

                                trade_record = {
                                    "symbol": symbol,
                                    "entry": recommended_entry,
                                    "shares": position_size,
                                    "stop_loss": stop_loss,
                                    "target": target,
                                    "timestamp": datetime.now().isoformat(),
                                    "order_id": str(order_response.id),
                                    "type": "intraday"
                                }
                                self.daily_trades.append(trade_record)
                                trades_executed += 1

                                self._notify(
                                    f"🟢 *Intraday Trade*\n"
                                    f"{symbol} x {position_size} shares\n"
                                    f"Entry: ${recommended_entry:.2f}\n"
                                    f"Stop: ${stop_loss:.2f}\n"
                                    f"Target: ${target:.2f}"
                                )

                            except Exception as e:
                                logger.error(f"Failed to execute intraday order for {symbol}: {e}")
                                self._notify(f"❌ *Intraday Trade Failed*\n{symbol}: {str(e)}", "error")

                        elif self.mode == "paper":
                            trade_record = {
                                "symbol": symbol,
                                "entry": recommended_entry,
                                "shares": position_size,
                                "stop_loss": stop_loss,
                                "target": target,
                                "timestamp": datetime.now().isoformat(),
                                "type": "intraday"
                            }
                            self.daily_trades.append(trade_record)
                            trades_executed += 1
                            logger.info(f"📝 Intraday paper trade logged: {symbol}")

            if trades_executed > 0:
                self._notify(f"✅ *Intraday Scan Complete*\nExecuted {trades_executed} new trades")

        except Exception as e:
            logger.error(f"Intraday scan error: {e}")
            self._notify(f"Intraday scan error: {str(e)}", "error")

    def run_monitoring_workflow(self):
        """Monitor positions and adjust stops."""
        logger.info("Running intraday monitoring")

        if self.workflow.get_current_state() != WorkflowState.INTRADAY_MONITORING:
            self.workflow.transition(WorkflowTransition.START_MONITORING)

        try:
            # Get all open positions
            if self.mode == "live" and self.auth and isinstance(self.auth, TradingClient):
                try:
                    # Get positions from Alpaca
                    positions = self.auth.get_all_positions()
                    logger.info(f"Monitoring {len(positions)} open positions")

                    if not positions:
                        logger.info("No open positions to monitor")
                        return

                    # Match positions with daily trades to get stop/target info
                    for position in positions:
                        symbol = position.symbol
                        current_price = float(position.current_price)
                        avg_entry = float(position.avg_entry_price)
                        qty = float(position.qty)

                        # Calculate P&L
                        unrealized_pl = float(position.unrealized_pl)
                        unrealized_plpc = float(position.unrealized_plpc) * 100  # Convert to percentage

                        logger.info(
                            f"{symbol}: Entry ${avg_entry:.2f} → Current ${current_price:.2f} "
                            f"| P&L: ${unrealized_pl:.2f} ({unrealized_plpc:.2f}%)"
                        )

                        # Find trade record to get stop/target levels
                        trade_record = next(
                            (t for t in self.daily_trades if t["symbol"] == symbol),
                            None
                        )

                        if not trade_record:
                            logger.warning(f"No trade record found for {symbol}")
                            continue

                        stop_loss = trade_record.get("stop_loss")
                        target = trade_record.get("target")

                        # Check stop loss (exit if price <= stop)
                        if stop_loss and current_price <= stop_loss:
                            logger.warning(f"Stop loss hit for {symbol}: ${current_price:.2f} <= ${stop_loss:.2f}")
                            self._execute_exit_order(
                                symbol, qty, current_price, "Stop Loss",
                                unrealized_pl, unrealized_plpc
                            )
                            continue

                        # Check target (exit if price >= target)
                        if target and current_price >= target:
                            logger.info(f"Target reached for {symbol}: ${current_price:.2f} >= ${target:.2f}")
                            self._execute_exit_order(
                                symbol, qty, current_price, "Target",
                                unrealized_pl, unrealized_plpc
                            )
                            continue

                        # Optional: Implement trailing stop adjustment
                        # For now, we just log and monitor

                    logger.info("Position monitoring complete")

                except Exception as e:
                    logger.error(f"Failed to get positions from Alpaca: {e}")
                    self._notify(f"⚠️ Position monitoring error: {str(e)}", "warning")

            elif self.mode == "paper":
                # For paper trading, we don't have real positions
                # Just log that monitoring is running
                logger.info(f"Paper mode: {len(self.daily_trades)} trades logged today")
                logger.info("Position monitoring complete (paper mode)")

            else:
                logger.debug("No auth configured or not live mode - skipping position monitoring")

        except Exception as e:
            logger.error(f"Monitoring workflow error: {e}")
            self.workflow.add_error(str(e))

    def _execute_exit_order(
        self,
        symbol: str,
        qty: float,
        current_price: float,
        reason: str,
        realized_pl: float,
        realized_plpc: float
    ):
        """Execute exit order for a position."""
        try:
            # Submit SELL order
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )

            logger.info(f"Executing {reason} exit for {symbol}: {qty} shares @ ${current_price:.2f}")
            order_response = self.auth.submit_order(order_request)

            logger.info(f"✅ Exit order placed: {order_response.id} - Status: {order_response.status}")

            # Send notification
            self._notify(
                f"🔴 *{reason} Exit*\n"
                f"{symbol} x {qty} shares @ ${current_price:.2f}\n"
                f"P&L: ${realized_pl:.2f} ({realized_plpc:.2f}%)\n"
                f"Order ID: {order_response.id}"
            )

            # Remove from daily trades tracking
            self.daily_trades = [t for t in self.daily_trades if t["symbol"] != symbol]

        except Exception as e:
            logger.error(f"Failed to execute {reason} exit for {symbol}: {e}")
            self._notify(f"❌ *Exit Order Failed*\n{symbol}: {str(e)}", "error")

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

        # Send startup notification
        startup_msg = (
            f"🤖 *Trading Bot Started*\n\n"
            f"Mode: `{self.mode}`\n"
            f"Crypto: `{'enabled' if hasattr(self, 'crypto_enabled') else 'disabled'}`\n"
            f"Multi-Agent: `{'enabled' if self.multi_agent_workflow else 'disabled'}`\n"
            f"Daily Budget: `$5.00`\n\n"
            f"_Monitoring markets..._"
        )
        self._notify(startup_msg, level="info")

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

    def evaluate_trade_with_agents(
        self,
        symbol: str,
        current_price: float,
        technical_indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a trade opportunity using multi-agent consensus.

        Uses 3 specialized agents (RegimeDetector, Research, NewsAnalyst) to vote
        on trade decisions. If 2/3 consensus reached for BUY, RiskManager calculates
        position size with Kelly Criterion.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            current_price: Current stock price
            technical_indicators: Technical data (RSI, SMA, ATR, ADX, etc.)

        Returns:
            {
                'symbol': str,
                'decision': str,                    # BUY/HOLD/SKIP
                'consensus_reached': bool,
                'votes': List[dict],                # Agent votes with reasoning
                'position_size_shares': int,        # If BUY
                'position_size_pct': float,         # If BUY (% of portfolio)
                'stop_loss_pct': float,            # If BUY
                'take_profit_pct': float,          # If BUY
                'summary': str,
                'total_cost_usd': float,           # LLM API cost
                'total_tokens': int,               # Tokens used
                'regime': str,                      # Market regime
                'regime_confidence': float         # Regime confidence %
            }
        """
        try:
            logger.info(f"Evaluating {symbol} @ ${current_price} using multi-agent consensus")

            # Call multi-agent trading workflow
            result = self.multi_agent_workflow.evaluate_trade_opportunity(
                symbol=symbol,
                current_price=current_price,
                portfolio_value=self.portfolio_value,
                cash_available=self.cash_available,
                technical_indicators=technical_indicators
            )

            # Log cost tracking
            logger.info(f"Multi-agent evaluation cost: ${result['total_cost_usd']:.4f} ({result['total_tokens']:,} tokens)")
            logger.info(f"Decision: {result['decision']} (consensus: {result['consensus_reached']})")

            # Update cash if BUY decision
            if result['decision'] == 'BUY' and result['position_size_shares'] > 0:
                trade_cost = current_price * result['position_size_shares']
                self.cash_available -= trade_cost
                logger.info(f"Cash after trade: ${self.cash_available:.2f}")

            return result

        except Exception as e:
            logger.error(f"Multi-agent evaluation failed for {symbol}: {e}")
            return {
                'symbol': symbol,
                'decision': 'SKIP',
                'consensus_reached': False,
                'votes': [],
                'position_size_shares': 0,
                'position_size_pct': 0.0,
                'stop_loss_pct': 0.0,
                'take_profit_pct': 0.0,
                'summary': f"Error: {str(e)}",
                'total_cost_usd': 0.0,
                'total_tokens': 0,
                'regime': 'UNKNOWN',
                'regime_confidence': 0.0
            }

    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        return {
            "running": self.running,
            "mode": self.mode,
            "workflow_state": self.workflow.get_current_state().value,
            "daily_cost": self.claude_manager.daily_cost,
            "budget_remaining": self.claude_manager.config.daily_budget_usd - self.claude_manager.daily_cost,
            "trades_today": len(self.daily_trades),
            "next_task": self.scheduler.get_next_trigger(),
            "portfolio_value": self.portfolio_value,
            "cash_available": self.cash_available
        }
