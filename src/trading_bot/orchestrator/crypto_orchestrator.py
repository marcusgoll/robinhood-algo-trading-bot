#!/usr/bin/env python3
"""
Crypto Trading Orchestrator

24/7 cryptocurrency trading orchestration using interval-based scheduling.
Coordinates screening every 2hrs, position monitoring every 5min.
"""

import time
import logging
import os
import pandas as pd
from datetime import datetime
from typing import Optional, Any, List, Dict

from trading_bot.orchestrator.interval_scheduler import IntervalScheduler

# Alpaca trading client for order placement
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# LLM imports are optional - only needed if MULTI_AGENT_ENABLED=true
try:
    from trading_bot.llm.claude_manager import ClaudeCodeManager
    from trading_bot.llm.examples.multi_agent_consensus_workflow import MultiAgentTradingWorkflow
    HAS_LLM = True
except ImportError:
    # Multi-agent system not available (excluded from Docker or incomplete setup)
    ClaudeCodeManager = None
    MultiAgentTradingWorkflow = None
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

# Technical Analysis framework
try:
    from trading_bot.technical_analysis import TACoordinator
    HAS_TA_FRAMEWORK = True
except ImportError:
    TACoordinator = None
    HAS_TA_FRAMEWORK = False

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

        # Initialize telegram config from environment (for quiet hours checking)
        from trading_bot.config import TelegramConfig
        self.telegram_config = TelegramConfig.default()

        # Initialize crypto data service
        self.crypto_data = CryptoDataService()

        # Initialize Alpaca trading client for order placement
        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")
        is_paper = (mode == "paper")
        self.trading_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=is_paper)

        # Initialize interval scheduler
        self.scheduler = IntervalScheduler()

        # Runtime state
        self.running = False
        self.active_positions = []
        self.watchlist = []

        # Portfolio tracking (for multi-agent position sizing)
        self.portfolio_value = 10000.0  # Default $10k for crypto portfolio
        self.cash_available = 10000.0   # Default $10k cash

        # Notification tracking
        self._startup_notification_sent = False

        # Initialize multi-agent trading workflow if LLM available
        if HAS_LLM and MultiAgentTradingWorkflow is not None:
            self.multi_agent_workflow = MultiAgentTradingWorkflow()
            logger.info("Multi-agent LLM system initialized for crypto trading")
        else:
            self.multi_agent_workflow = None
            logger.info("Multi-agent system not available - using rule-based trading")

        # Initialize Technical Analysis framework (if available)
        if HAS_TA_FRAMEWORK:
            self.ta_coordinator = TACoordinator(account_size=10000.0)
            logger.info("Technical Analysis framework initialized for crypto (20 quantifiable tools)")
        else:
            self.ta_coordinator = None
            logger.info("TA framework not available - skipping TA analysis")

        # Setup scheduled workflows
        self._setup_schedule()

        logger.info(f"CryptoOrchestrator initialized in {mode} mode")
        logger.info(f"Alpaca paper trading: {is_paper}")
        logger.info(f"Symbols: {', '.join(crypto_config.symbols)}")

    def _is_quiet_hours(self, is_critical: bool = False) -> bool:
        """
        Check if currently in quiet hours.

        Args:
            is_critical: If True, check if critical notifications bypass quiet hours

        Returns:
            True if in quiet hours and notification should be suppressed
        """
        from datetime import datetime
        import pytz

        # Critical notifications can bypass quiet hours if configured
        if is_critical and self.telegram_config.critical_bypass_quiet:
            return False

        # Not in quiet hours if disabled (start == end)
        if self.telegram_config.quiet_hours_start == self.telegram_config.quiet_hours_end:
            return False

        # Get current time in configured timezone
        tz = pytz.timezone(self.telegram_config.quiet_hours_timezone)
        now = datetime.now(tz)
        current_time = now.strftime("%H:%M")

        # Check if in quiet hours window
        start = self.telegram_config.quiet_hours_start
        end = self.telegram_config.quiet_hours_end

        # Handle overnight quiet hours (e.g., 22:00 to 06:00)
        if start > end:
            return current_time >= start or current_time < end
        else:
            return start <= current_time < end

    def _notify(self, message: str, level: str = "info", is_critical: bool = False):
        """
        Send log + Telegram notification.

        Args:
            message: Message to send
            level: Log level (info, warning, error)
            is_critical: If True, notification bypasses quiet hours
        """
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)

        if self.claude_manager and self.claude_manager.telegram_enabled:
            # Check quiet hours
            if self._is_quiet_hours(is_critical):
                logger.debug(f"Suppressing crypto notification during quiet hours (critical={is_critical})")
                return

            emoji = {"error": "🚨", "warning": "⚠️"}.get(level, "🪙")
            suppress_minutes = self.telegram_config.duplicate_suppress_minutes
            self.claude_manager._send_telegram_notification(f"{emoji} {message}", suppress_minutes=suppress_minutes)

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
        """Screen crypto symbols using multi-agent AI consensus."""
        logger.info("🔍 Starting AI-powered crypto screening...")

        try:
            # Initial liquidity filtering
            liquid_candidates = []

            for symbol in self.config.symbols:
                try:
                    # Get current crypto quote
                    quote = self.crypto_data.get_latest_quote(symbol)
                    if not quote:
                        logger.debug(f"No quote data for {symbol}")
                        continue

                    price = (quote.bid + quote.ask) / 2.0
                    spread_pct = ((quote.ask - quote.bid) / price) * 100 if price > 0 else 999

                    # Basic liquidity filter (price > $0.10, spread < 2%, has volume)
                    if price > 0.10 and spread_pct < 2.0 and quote.bid_size > 0 and quote.ask_size > 0:
                        liquid_candidates.append({
                            "symbol": symbol,
                            "price": price,
                            "spread_pct": spread_pct,
                            "bid_size": quote.bid_size,
                            "ask_size": quote.ask_size
                        })
                        logger.info(f"Liquid candidate: {symbol} @ ${price:.4f} (spread {spread_pct:.2f}%)")

                except Exception as e:
                    logger.warning(f"Failed to screen {symbol}: {e}")
                    continue

            if not liquid_candidates:
                logger.info("No liquid candidates found")
                return

            # Use multi-agent AI to evaluate each liquid candidate
            ai_approved = []
            previous_watchlist_symbols = set(c["symbol"] for c in self.watchlist)

            if self.multi_agent_workflow:
                logger.info(f"🤖 AI evaluating {len(liquid_candidates)} candidates with multi-agent consensus...")

                for candidate in liquid_candidates:
                    try:
                        symbol = candidate["symbol"]
                        price = candidate["price"]

                        # Build technical indicators for multi-agent evaluation
                        # Fetch real historical data to calculate proper indicators
                        try:
                            historical_df = self.crypto_data.get_historical_bars(
                                symbol=symbol,
                                timeframe="1h",
                                limit=200  # Need enough data for 200 SMA
                            )

                            if historical_df is not None and len(historical_df) >= 50:
                                # Calculate real technical indicators
                                close_prices = historical_df['close']
                                high_prices = historical_df['high']
                                low_prices = historical_df['low']
                                volumes = historical_df['volume']

                                # RSI (14-period)
                                delta = close_prices.diff()
                                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                                rs = gain / loss
                                rsi = 100 - (100 / (1 + rs))

                                # Moving averages
                                sma_20 = close_prices.rolling(window=20).mean()
                                sma_50 = close_prices.rolling(window=50).mean()
                                sma_200 = close_prices.rolling(window=200).mean() if len(close_prices) >= 200 else None

                                # ATR (14-period)
                                high_low = high_prices - low_prices
                                high_close = abs(high_prices - close_prices.shift())
                                low_close = abs(low_prices - close_prices.shift())
                                true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                                atr = true_range.rolling(window=14).mean()

                                # Volume trend (20-period average)
                                volume_sma = volumes.rolling(window=20).mean()

                                technical_indicators = {
                                    "price": price,
                                    "spread_pct": candidate["spread_pct"],
                                    "bid_size": candidate["bid_size"],
                                    "ask_size": candidate["ask_size"],
                                    "liquidity_score": 100 - (candidate["spread_pct"] * 10),
                                    # Real technical indicators
                                    "RSI": float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0,
                                    "SMA_20": float(sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else price,
                                    "SMA_50": float(sma_50.iloc[-1]) if not pd.isna(sma_50.iloc[-1]) else price,
                                    "SMA_200": float(sma_200.iloc[-1]) if sma_200 is not None and not pd.isna(sma_200.iloc[-1]) else None,
                                    "ATR": float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else price * 0.05,
                                    "volume": float(volumes.iloc[-1]),
                                    "volume_sma": float(volume_sma.iloc[-1]) if not pd.isna(volume_sma.iloc[-1]) else float(volumes.iloc[-1]),
                                    "ADX": 25.0  # TODO: Calculate ADX when needed
                                }
                            else:
                                # Fallback to placeholder if insufficient data
                                logger.warning(f"{symbol}: Insufficient historical data, using placeholders")
                                technical_indicators = {
                                    "price": price,
                                    "spread_pct": candidate["spread_pct"],
                                    "bid_size": candidate["bid_size"],
                                    "ask_size": candidate["ask_size"],
                                    "liquidity_score": 100 - (candidate["spread_pct"] * 10),
                                    "RSI": None,
                                    "SMA_20": None,
                                    "ATR": None,
                                    "ADX": None
                                }
                        except Exception as e:
                            logger.warning(f"{symbol}: Failed to calculate indicators: {e}")
                            # Fallback to placeholder if error
                            technical_indicators = {
                                "price": price,
                                "spread_pct": candidate["spread_pct"],
                                "bid_size": candidate["bid_size"],
                                "ask_size": candidate["ask_size"],
                                "liquidity_score": 100 - (candidate["spread_pct"] * 10),
                                "RSI": None,
                                "SMA_20": None,
                                "ATR": None,
                                "ADX": None
                            }

                        # Evaluate with multi-agent consensus
                        logger.info(f"Evaluating {symbol} with AI agents...")
                        result = self.evaluate_trade_with_agents(
                            symbol=symbol,
                            current_price=price,
                            technical_indicators=technical_indicators
                        )

                        # Check if agents recommend BUY
                        if result['decision'] == 'BUY' and result['consensus_reached']:
                            ai_approved.append({
                                **candidate,
                                "ai_decision": result['decision'],
                                "position_size_shares": result['position_size_shares'],
                                "position_size_pct": result['position_size_pct'],
                                "stop_loss_pct": result['stop_loss_pct'],
                                "take_profit_pct": result['take_profit_pct'],
                                "regime": result.get('regime', 'UNKNOWN'),
                                "ai_summary": result['summary']
                            })
                            logger.info(f"✅ AI approved {symbol}: {result['summary']}")
                            # Note: Notification consolidated below with watchlist update
                        else:
                            logger.info(f"❌ AI rejected {symbol}: {result['decision']}")

                    except Exception as e:
                        logger.error(f"AI evaluation failed for {candidate['symbol']}: {e}")
                        continue

                self.watchlist = ai_approved[:3]  # Top 3 AI-approved
            else:
                # Fallback to rule-based if multi-agent not available
                logger.warning("Multi-agent system not available, using rule-based fallback")
                liquid_candidates.sort(key=lambda x: x["spread_pct"])
                self.watchlist = liquid_candidates[:3]

            # Only notify if watchlist changed
            new_watchlist_symbols = set(c["symbol"] for c in self.watchlist)
            watchlist_changed = previous_watchlist_symbols != new_watchlist_symbols

            top_symbols = ", ".join([c["symbol"] for c in self.watchlist])
            logger.info(
                f"✅ Screening complete: "
                f"AI evaluated {len(liquid_candidates)} liquid candidates, "
                f"approved {len(self.watchlist)} for trading. "
                f"Top picks: {top_symbols or 'None'}"
            )

            # Send Telegram notification ONLY if watchlist changed
            if watchlist_changed:
                added_symbols = new_watchlist_symbols - previous_watchlist_symbols
                removed_symbols = previous_watchlist_symbols - new_watchlist_symbols

                change_msg = ""
                if added_symbols:
                    # Build detailed info for added symbols
                    added_details = []
                    for c in self.watchlist:
                        if c["symbol"] in added_symbols:
                            symbol = c["symbol"]
                            price = c.get("price", 0)
                            regime = c.get("regime", "UNKNOWN")
                            position_pct = c.get("position_size_pct", 0)
                            added_details.append(
                                f"   • {symbol} @ ${price:.2f} | {regime} | {position_pct:.1f}%"
                            )

                    change_msg += f"\n➕ *Added:*\n" + "\n".join(added_details)

                if removed_symbols:
                    change_msg += f"\n➖ *Removed:* {', '.join(sorted(removed_symbols))}"

                self._notify(
                    f"📊 *Watchlist Updated*\n"
                    f"Total: {len(self.watchlist)} symbols"
                    f"{change_msg}"
                )

            # Execute trades for AI-approved candidates
            max_positions = int(100 / self.config.max_position_pct)
            if self.watchlist and len(self.active_positions) < max_positions:
                self._execute_entry_orders()

        except Exception as e:
            self._notify(f"Screening error: {str(e)}", "error")
            logger.error(f"Screening workflow error: {e}", exc_info=True)

    def _execute_entry_orders(self):
        """Execute entry orders for AI-approved candidates via Alpaca API."""
        max_positions = int(100 / self.config.max_position_pct)
        slots_available = max_positions - len(self.active_positions)

        for candidate in self.watchlist[:slots_available]:
            try:
                symbol = candidate["symbol"]
                price = candidate["price"]  # Mid-point from quote
                spread_pct = candidate["spread_pct"]

                # Skip if already have position in this symbol
                if any(p["symbol"] == symbol for p in self.active_positions):
                    logger.info(f"Already have position in {symbol}, skipping")
                    continue

                # Use AI-calculated position size if available, otherwise use config default
                if "position_size_shares" in candidate and candidate["position_size_shares"] > 0:
                    # AI-determined position size (in crypto quantity)
                    quantity = candidate["position_size_shares"]
                    position_size_usd = quantity * price
                    logger.info(f"Using AI position size: {quantity:.8f} {symbol} (${position_size_usd:.2f})")
                else:
                    # Fallback to fixed position size from config
                    position_size_usd = self.config.position_size_usd
                    quantity = position_size_usd / price
                    logger.info(f"Using config position size: ${position_size_usd:.2f}")

                # Get fresh quote for limit price (use ask price for buy orders)
                quote = self.crypto_data.get_latest_quote(symbol)
                if not quote:
                    logger.warning(f"No quote available for {symbol}, skipping")
                    continue

                # Use ask price as limit (ensures we can buy at market)
                limit_price = quote.ask

                # Recalculate quantity based on limit price
                quantity = position_size_usd / limit_price

                logger.info(
                    f"Placing AI-optimized Alpaca limit order: {symbol} @ ${limit_price:.4f} x {quantity:.8f} "
                    f"(${position_size_usd:.2f} notional)"
                )

                # Submit LIMIT order instead of market (more reliable for crypto)
                # Using limit at ask price ensures immediate fill at market price
                order_request = LimitOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    limit_price=limit_price,  # Buy at current ask price
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.GTC  # GTC so order stays until filled
                )

                # Execute order via Alpaca
                order_response = self.trading_client.submit_order(order_request)

                # Track position with AI-calculated risk parameters
                # Paper trading limit orders may not fill immediately, but we track
                # the intended quantity since orders are at market price (ask) and will fill
                position = {
                    "symbol": symbol,
                    "entry_price": limit_price,  # Use limit price as entry (actual fill price)
                    "quantity": quantity,  # Use intended quantity (not filled_qty which is 0 initially)
                    "notional": position_size_usd,
                    "entry_time": datetime.now().isoformat(),
                    "alpaca_order_id": str(order_response.id),
                    "alpaca_status": order_response.status,
                    # AI-calculated risk parameters
                    "ai_stop_loss_pct": candidate.get("stop_loss_pct", self.config.stop_loss_pct),
                    "ai_take_profit_pct": candidate.get("take_profit_pct", 10.0),  # Default 10%
                    "ai_regime": candidate.get("regime", "UNKNOWN"),
                    "ai_summary": candidate.get("ai_summary", "Rule-based entry")
                }
                self.active_positions.append(position)

                # Update cash tracking
                self.cash_available -= position_size_usd

                logger.info(f"✅ Order placed: {order_response.id} - Status: {order_response.status}")
                logger.info(f"   Tracking position: {quantity:.8f} {symbol} @ ${limit_price:.4f}")

                # Build notification with AI insights
                ai_info = ""
                if "ai_regime" in candidate:
                    ai_info = (
                        f"AI Regime: {candidate.get('regime', 'N/A')}\n"
                        f"Stop Loss: {candidate.get('stop_loss_pct', 0):.1f}%\n"
                        f"Take Profit: {candidate.get('take_profit_pct', 0):.1f}%\n"
                    )

                self._notify(
                    f"🟢 *AI-Optimized Entry*\n"
                    f"{symbol} @ ${limit_price:.4f}\n"
                    f"Qty: {quantity:.8f} (${position_size_usd:.2f})\n"
                    f"{ai_info}"
                    f"Type: Limit (GTC)\n"
                    f"Status: {order_response.status}\n"
                    f"Order ID: {order_response.id}"
                )

            except Exception as e:
                logger.error(f"Failed to execute entry for {candidate.get('symbol')}: {e}")
                self._notify(f"❌ Order failed for {candidate.get('symbol')}: {str(e)}", "error")

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
                order_id = position.get("alpaca_order_id")

                # Check order status before monitoring
                if order_id:
                    try:
                        order = self.trading_client.get_order_by_id(order_id)
                        position["alpaca_status"] = order.status

                        # Skip monitoring if order not filled yet
                        if order.status in ["new", "pending_new", "accepted", "pending_replace"]:
                            logger.debug(f"Order {order_id} for {symbol} not filled yet (status: {order.status}), skipping monitoring")
                            continue

                        # Remove position if order was cancelled/expired
                        if order.status in ["cancelled", "expired", "rejected"]:
                            logger.warning(f"Order {order_id} for {symbol} was {order.status}, removing from tracking")
                            self.active_positions.remove(position)
                            continue

                        # Update quantity if filled (in case partial fills)
                        if order.status == "filled" and order.filled_qty:
                            position["quantity"] = float(order.filled_qty)
                            logger.debug(f"Order {order_id} filled: {order.filled_qty} {symbol}")

                    except Exception as e:
                        logger.warning(f"Failed to check order status for {order_id}: {e}")
                        # Continue monitoring even if status check fails
                        pass

                # Get current price
                current_price = self.crypto_data.get_current_price(symbol)
                if not current_price:
                    continue

                # Calculate P&L
                pnl_pct = ((current_price - entry_price) / entry_price) * 100

                # Use AI-calculated stop loss if available, otherwise use config default
                stop_loss_pct = position.get("ai_stop_loss_pct", self.config.stop_loss_pct)

                # Check stop loss
                if pnl_pct <= -stop_loss_pct:
                    self._notify(
                        f"🛑 *Stop Loss Hit*\n"
                        f"{symbol}: {pnl_pct:.2f}%\n"
                        f"Entry: ${entry_price:.2f} → Current: ${current_price:.2f}",
                        "warning"
                    )

                    # Execute sell order at stop loss
                    try:
                        # Get fresh quote for limit price (use bid price for sell orders)
                        quote = self.crypto_data.get_latest_quote(symbol)
                        if not quote:
                            logger.error(f"No quote available for stop loss sell on {symbol}")
                            continue

                        # Use bid price as limit for sell (market price)
                        limit_price = quote.bid
                        quantity = position["quantity"]

                        logger.info(
                            f"Executing stop loss sell: {symbol} @ ${limit_price:.4f} x {quantity:.8f}"
                        )

                        # Submit LIMIT sell order with IOC (Immediate or Cancel)
                        order_request = LimitOrderRequest(
                            symbol=symbol,
                            qty=quantity,
                            limit_price=limit_price,
                            side=OrderSide.SELL,
                            time_in_force=TimeInForce.IOC  # Immediate or Cancel for quick exit
                        )

                        # Execute sell order via Alpaca
                        sell_order = self.trading_client.submit_order(order_request)

                        logger.info(
                            f"✅ Stop loss order placed: {sell_order.id} - Status: {sell_order.status}"
                        )

                        # Calculate realized P&L
                        position_value = entry_price * quantity
                        realized_pnl = (current_price - entry_price) * quantity
                        realized_pnl_pct = (realized_pnl / position_value) * 100

                        self._notify(
                            f"🔴 *Stop Loss Executed*\n"
                            f"{symbol} @ ${limit_price:.4f}\n"
                            f"Qty: {quantity:.8f}\n"
                            f"P&L: ${realized_pnl:.2f} ({realized_pnl_pct:.2f}%)\n"
                            f"Order ID: {sell_order.id}"
                        )

                        # Remove position from tracking
                        self.active_positions.remove(position)
                        logger.info(f"Position removed from tracking: {symbol}")

                    except Exception as e:
                        logger.error(f"Failed to execute stop loss sell for {symbol}: {e}")
                        self._notify(
                            f"❌ *Stop Loss Execution Failed*\n{symbol}: {str(e)}",
                            "error"
                        )

            except Exception as e:
                logger.error(f"Error monitoring {position.get('symbol')}: {e}")

    def run_rebalance_workflow(self):
        """
        Daily portfolio rebalancing.

        Rebalances portfolio to maintain equal weights across all positions.
        Triggers when position weights drift more than 20% from target.
        """
        logger.info("Running crypto portfolio rebalance")

        if not self.active_positions:
            logger.info("No active positions to rebalance")
            return

        try:
            # Filter to only filled positions for rebalancing
            filled_positions = []
            for position in self.active_positions:
                order_id = position.get("alpaca_order_id")
                if order_id:
                    try:
                        order = self.trading_client.get_order_by_id(order_id)
                        if order.status == "filled":
                            filled_positions.append(position)
                        else:
                            logger.debug(f"Excluding {position['symbol']} from rebalance (order status: {order.status})")
                    except Exception as e:
                        logger.warning(f"Failed to check order status for {order_id}: {e}")
                        # Include in rebalancing if status check fails (assume filled)
                        filled_positions.append(position)
                else:
                    # No order ID, include it
                    filled_positions.append(position)

            if not filled_positions:
                logger.info("No filled positions to rebalance")
                return

            # Calculate total portfolio value
            total_value = 0.0
            position_values = {}

            for position in filled_positions:
                symbol = position["symbol"]
                try:
                    current_price = self.crypto_data.get_current_price(symbol)
                    if not current_price:
                        continue

                    quantity = position["quantity"]
                    value = current_price * quantity
                    position_values[symbol] = {
                        "value": value,
                        "quantity": quantity,
                        "price": current_price
                    }
                    total_value += value
                except Exception as e:
                    logger.warning(f"Failed to get value for {symbol}: {e}")
                    continue

            if total_value == 0:
                logger.warning("Portfolio total value is 0, skipping rebalance")
                return

            # Calculate current weights and target weights
            num_positions = len(position_values)
            target_weight = 1.0 / num_positions if num_positions > 0 else 0
            rebalance_threshold = 0.20  # 20% drift triggers rebalance

            rebalance_needed = []

            logger.info(f"Portfolio value: ${total_value:.2f}")
            logger.info(f"Target weight per position: {target_weight * 100:.1f}%")

            for symbol, pos_data in position_values.items():
                current_weight = pos_data["value"] / total_value
                weight_diff = abs(current_weight - target_weight)
                weight_diff_pct = weight_diff / target_weight if target_weight > 0 else 0

                logger.info(
                    f"{symbol}: Current {current_weight * 100:.1f}%, "
                    f"Target {target_weight * 100:.1f}%, "
                    f"Drift {weight_diff_pct * 100:.1f}%"
                )

                if weight_diff_pct > rebalance_threshold:
                    target_value = total_value * target_weight
                    value_adjustment = target_value - pos_data["value"]
                    quantity_adjustment = value_adjustment / pos_data["price"]

                    rebalance_needed.append({
                        "symbol": symbol,
                        "current_weight": current_weight,
                        "target_weight": target_weight,
                        "value_adjustment": value_adjustment,
                        "quantity_adjustment": quantity_adjustment,
                        "action": "BUY" if quantity_adjustment > 0 else "SELL"
                    })

            if not rebalance_needed:
                logger.info("Portfolio is balanced, no rebalancing needed")
                self._notify("✅ *Rebalance Check*\nPortfolio is balanced")
                return

            # Execute rebalancing trades
            logger.info(f"Rebalancing {len(rebalance_needed)} positions")
            self._notify(
                f"📊 *Portfolio Rebalance*\n"
                f"Adjusting {len(rebalance_needed)} positions"
            )

            for rebalance in rebalance_needed:
                try:
                    symbol = rebalance["symbol"]
                    action = rebalance["action"]
                    quantity = abs(rebalance["quantity_adjustment"])

                    # Get fresh quote
                    quote = self.crypto_data.get_latest_quote(symbol)
                    if not quote:
                        logger.warning(f"No quote for {symbol}, skipping rebalance")
                        continue

                    # Use appropriate limit price based on action
                    limit_price = quote.ask if action == "BUY" else quote.bid

                    logger.info(
                        f"Rebalancing {symbol}: {action} {quantity:.8f} @ ${limit_price:.4f}"
                    )

                    # Submit rebalance order
                    order_request = LimitOrderRequest(
                        symbol=symbol,
                        qty=quantity,
                        limit_price=limit_price,
                        side=OrderSide.BUY if action == "BUY" else OrderSide.SELL,
                        time_in_force=TimeInForce.GTC
                    )

                    order_response = self.trading_client.submit_order(order_request)
                    logger.info(f"Rebalance order placed: {order_response.id}")

                    # Update position tracking
                    if action == "BUY":
                        # Find and update position
                        for pos in self.active_positions:
                            if pos["symbol"] == symbol:
                                pos["quantity"] += quantity
                                break
                    elif action == "SELL":
                        # Reduce position
                        for pos in self.active_positions:
                            if pos["symbol"] == symbol:
                                pos["quantity"] -= quantity
                                # Remove if fully closed
                                if pos["quantity"] <= 0:
                                    self.active_positions.remove(pos)
                                break

                except Exception as e:
                    logger.error(f"Failed to rebalance {rebalance['symbol']}: {e}")
                    self._notify(
                        f"⚠️ *Rebalance Failed*\n{rebalance['symbol']}: {str(e)}",
                        "warning"
                    )

            self._notify("✅ *Rebalance Complete*\nPortfolio rebalanced")
            logger.info("Rebalance workflow complete")

        except Exception as e:
            self._notify(f"❌ Rebalance error: {str(e)}", "error")
            logger.error(f"Rebalance workflow error: {e}")

    def run_loop(self):
        """Main event loop - check scheduler every 60 seconds."""
        logger.info("Starting crypto orchestrator event loop")
        logger.info(f"Screening: every {self.config.screening_interval_hours}hr")
        logger.info(f"Monitoring: every {self.config.monitoring_interval_minutes}min")

        self.running = True

        # Send startup notification (only once per instance)
        # Startup notification removed - only notify on actual events
        # (watchlist updates, trades, circuit breakers)
        self._startup_notification_sent = True
        logger.debug("Crypto startup logged (no notification sent)")

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

    def evaluate_trade_with_agents(
        self,
        symbol: str,
        current_price: float,
        technical_indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a crypto trade using multi-agent AI consensus.

        Uses 8 specialized agents (RegimeDetector, Research, NewsAnalyst, RiskManager)
        to vote on trade decisions. If 2/3 consensus reached for BUY, RiskManager
        calculates position size with Kelly Criterion.

        Args:
            symbol: Crypto symbol (e.g., 'BTC/USD')
            current_price: Current crypto price
            technical_indicators: Technical data (spread, volume, RSI, etc.)

        Returns:
            {
                'symbol': str,
                'decision': str,                    # BUY/HOLD/SKIP
                'consensus_reached': bool,
                'votes': List[dict],                # Agent votes with reasoning
                'position_size_shares': float,      # If BUY (in crypto quantity)
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
            logger.info(f"Evaluating {symbol} @ ${current_price}")

            # Step 1: TA Framework pre-filtering (if available)
            ta_signal = None
            if self.ta_coordinator:
                try:
                    # Get historical data for TA analysis
                    logger.info(f"Running TA framework analysis on {symbol}...")

                    # Fetch historical bars (100 periods for TA analysis)
                    historical_df = self.crypto_data.get_historical_bars(
                        symbol=symbol,
                        timeframe="1h",
                        limit=100
                    )

                    if historical_df is not None and len(historical_df) >= 50:
                        # Run TA framework analysis
                        ta_signal = self.ta_coordinator.analyze_simple(
                            symbol=symbol,
                            df=historical_df
                        )

                        logger.info(
                            f"TA Signal: {ta_signal.signal} "
                            f"(confidence: {ta_signal.confidence:.1f}%)"
                        )

                        # Early exit if TA says SKIP
                        if ta_signal.signal == 'SKIP':
                            logger.info(f"TA framework rejected {symbol} - skipping LLM evaluation")
                            return {
                                'symbol': symbol,
                                'decision': 'SKIP',
                                'consensus_reached': False,
                                'votes': [],
                                'position_size_shares': 0,
                                'position_size_pct': 0.0,
                                'stop_loss_pct': 0.0,
                                'take_profit_pct': 0.0,
                                'summary': f"TA Framework: {ta_signal.reasoning}",
                                'total_cost_usd': 0.0,
                                'total_tokens': 0,
                                'regime': ta_signal.regime or 'UNKNOWN',
                                'regime_confidence': ta_signal.confidence
                            }

                        # Enhance technical indicators with TA metrics
                        technical_indicators['ta_signal'] = ta_signal.signal
                        technical_indicators['ta_confidence'] = ta_signal.confidence
                        technical_indicators['ta_regime'] = ta_signal.regime
                        if ta_signal.stop_loss:
                            technical_indicators['ta_stop_loss'] = ta_signal.stop_loss
                        if ta_signal.take_profit:
                            technical_indicators['ta_take_profit'] = ta_signal.take_profit

                        logger.info(f"TA approved {symbol} - proceeding to LLM evaluation")
                    else:
                        logger.warning(f"Insufficient historical data for {symbol} TA analysis")

                except Exception as e:
                    logger.warning(f"TA analysis failed for {symbol}: {e} - proceeding without TA")

            # Step 2: Multi-agent LLM consensus
            logger.info(f"Evaluating {symbol} with multi-agent AI consensus")
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

            # Update cash if BUY decision (for next evaluation)
            if result['decision'] == 'BUY' and result['position_size_shares'] > 0:
                trade_cost = current_price * result['position_size_shares']
                # Don't actually deduct yet - that happens in _execute_entry_orders
                logger.info(f"Projected cash after trade: ${self.cash_available - trade_cost:.2f}")

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
        """Get current crypto orchestrator status."""
        next_task = self.scheduler.get_next_trigger()

        return {
            "running": self.running,
            "mode": self.mode,
            "symbols": self.config.symbols,
            "active_positions": len(self.active_positions),
            "watchlist_size": len(self.watchlist),
            "next_task": next_task["task"] if next_task else None,
            "next_run_seconds": next_task["seconds_until"] if next_task else None,
            "portfolio_value": self.portfolio_value,
            "cash_available": self.cash_available
        }
