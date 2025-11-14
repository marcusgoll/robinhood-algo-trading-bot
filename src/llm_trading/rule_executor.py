"""
Rule-Based Trade Executor

Fast, deterministic execution engine for intraday trading. Runs during market
hours (9:30am-4pm) and executes trades based on LLM-generated watchlist setups.

NO LLM CALLS during execution (for speed). Purely rule-based using criteria
from morning screener.

Architecture:
- Monitors watchlist symbols every minute
- Checks entry conditions (price, RSI, volume, etc.)
- Executes orders when criteria met
- Manages open positions (stop loss, take profit, time exits)
- Tracks performance for evening optimizer
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import alpaca_trade_api as tradeapi
import pandas as pd


class RuleExecutor:
    """Fast rule-based trade execution engine"""

    def __init__(self,
                 api_key: str,
                 api_secret: str,
                 paper: bool = True,
                 check_interval: int = 60):
        """
        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            paper: Use paper trading (True) or live (False)
            check_interval: Seconds between watchlist checks (default 60)
        """
        base_url = "https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"
        self.api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')

        self.check_interval = check_interval
        self.paper = paper

        # Load current strategy parameters (set by optimizer)
        self.params = self._load_strategy_params()

        # Active positions
        self.positions = {}  # symbol -> position data

        # Performance tracking
        self.trades_today = []
        self.daily_pnl = 0.0

        # Circuit breaker state
        self.circuit_breaker_active = False

    def run_trading_session(self, watchlist_file: str = 'watchlists/watchlist_latest.json'):
        """
        Main trading loop - runs from market open to close.

        Args:
            watchlist_file: Path to today's watchlist JSON
        """
        print(f"\n{'='*80}")
        print(f"RULE EXECUTOR - TRADING SESSION")
        print(f"Mode: {'PAPER' if self.paper else 'LIVE'}")
        print(f"{'='*80}\n")

        # Load watchlist
        watchlist = self._load_watchlist(watchlist_file)
        if not watchlist:
            print("ERROR: No watchlist loaded. Run screener first.")
            return

        print(f"Loaded {len(watchlist)} symbols from watchlist\n")

        # Check if market is open
        clock = self.api.get_clock()
        if not clock.is_open:
            print(f"Market is CLOSED. Next open: {clock.next_open}")
            return

        print(f"Market is OPEN. Trading until {clock.next_close}\n")

        # Main trading loop
        try:
            while True:
                now = datetime.now()

                # Check if market closed
                clock = self.api.get_clock()
                if not clock.is_open:
                    print(f"\n[{now.strftime('%H:%M:%S')}] Market closed. Session complete.")
                    break

                # Check circuit breaker
                if self.circuit_breaker_active:
                    print(f"\n[{now.strftime('%H:%M:%S')}] CIRCUIT BREAKER ACTIVE - Trading halted")
                    break

                print(f"\n[{now.strftime('%H:%M:%S')}] Checking watchlist...")

                # Monitor existing positions
                self._manage_positions()

                # Check for new entries
                self._check_entry_opportunities(watchlist)

                # Status update
                print(f"  Open positions: {len(self.positions)}")
                print(f"  Trades today: {len(self.trades_today)}")
                print(f"  Daily P&L: ${self.daily_pnl:+.2f}")

                # Wait for next check
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print("\n\nSession interrupted by user")

        finally:
            # Close all positions at end of day
            if self.positions:
                print(f"\nClosing {len(self.positions)} open positions...")
                self._close_all_positions()

            # Save performance data
            self._save_performance()

            print(f"\n{'='*80}")
            print(f"SESSION COMPLETE")
            print(f"{'='*80}")
            print(f"Total trades: {len(self.trades_today)}")
            print(f"Final P&L: ${self.daily_pnl:+.2f}")
            print(f"Performance saved to: llm_trading/performance/performance_latest.json")
            print()

    def _check_entry_opportunities(self, watchlist: List[Dict]):
        """Check watchlist for new entry opportunities"""

        # Respect max trades limit
        max_trades = self.params.get('max_trades_per_day', 15)
        if len(self.trades_today) >= max_trades:
            return

        # Check each symbol on watchlist
        for setup in watchlist:
            symbol = setup['symbol']

            # Skip if already in position
            if symbol in self.positions:
                continue

            # Check if still in entry time window
            if not self._in_time_window(setup['entry'].get('time_window', '9:30am - 4:00pm')):
                continue

            # Check entry condition
            if self._check_entry_condition(symbol, setup):
                print(f"  ✓ ENTRY SIGNAL: {symbol} ({setup['setup_type']})")
                self._execute_entry(symbol, setup)

    def _check_entry_condition(self, symbol: str, setup: Dict) -> bool:
        """Check if entry criteria are met"""

        try:
            # Fetch recent data
            bars = self.api.get_bars(symbol, '1Min', limit=100).df
            if bars.empty:
                return False

            bars = bars.reset_index()
            current_price = bars['close'].iloc[-1]

            entry = setup['entry']
            condition = entry.get('condition', '').lower()

            # Parse entry condition (simplified rule checking)
            # Real implementation would be more robust

            # Example: "price breaks above 145.50 with volume"
            if 'breaks above' in condition or 'above' in condition:
                # Extract target price from condition or setup
                target_price = self._extract_price(condition)
                if target_price and current_price > target_price:
                    # Check volume confirmation
                    if 'volume' in condition:
                        volume_ratio = bars['volume'].iloc[-1] / bars['volume'].rolling(20).mean().iloc[-1]
                        if volume_ratio < 1.2:  # Not enough volume
                            return False

                    # Check confirmation signal
                    confirmation = entry.get('confirmation', '').lower()
                    if 'rsi' in confirmation:
                        rsi = self._calculate_rsi(bars, period=14)
                        if 'above' in confirmation:
                            threshold = self._extract_number(confirmation)
                            if threshold and rsi < threshold:
                                return False

                    return True

            # Example: "price at or below 142.00 (oversold bounce)"
            elif 'below' in condition or 'at or below' in condition:
                target_price = self._extract_price(condition)
                if target_price and current_price <= target_price:
                    # Check RSI for oversold
                    rsi = self._calculate_rsi(bars, period=14)
                    if rsi < self.params.get('rsi_oversold', 30):
                        return True

            # Generic condition: Check current price vs setup parameters
            # If no specific condition, use default thresholds
            else:
                # Check RSI
                rsi = self._calculate_rsi(bars, period=14)

                setup_type = setup.get('setup_type', '').lower()

                if 'oversold' in setup_type or 'bounce' in setup_type:
                    if rsi < self.params.get('rsi_oversold', 30):
                        return True

                elif 'breakout' in setup_type:
                    # Check if price breaking out
                    sma_20 = bars['close'].rolling(20).mean().iloc[-1]
                    if current_price > sma_20 * 1.02:  # 2% above SMA
                        volume_ratio = bars['volume'].iloc[-1] / bars['volume'].rolling(20).mean().iloc[-1]
                        if volume_ratio > 1.5:  # High volume
                            return True

            return False

        except Exception as e:
            print(f"    Error checking {symbol}: {e}")
            return False

    def _execute_entry(self, symbol: str, setup: Dict):
        """Execute entry order"""

        try:
            # Get account info
            account = self.api.get_account()
            buying_power = float(account.buying_power)
            account_value = float(account.equity)

            # Calculate position size based on risk (handle missing 'risk' key)
            risk_info = setup.get('risk', {})
            risk_pct = risk_info.get('account_risk_pct', self.params.get('position_size_pct', 0.015))

            # Handle nested exit structures
            exit_info = setup.get('exit', {})
            if 'stop_loss_pct' in exit_info:
                stop_loss_pct = abs(exit_info['stop_loss_pct'])
            elif isinstance(exit_info.get('stop_loss'), dict):
                stop_loss_pct = abs(exit_info['stop_loss'].get('pct', -1.0))
            else:
                stop_loss_pct = 1.0  # Default 1%

            # Position size = (Account * Risk%) / Stop%
            # E.g., $100k * 1.5% / 1.0% = $1,500 / 0.01 = $150,000 notional
            # But limited by buying power
            position_value = (account_value * risk_pct) / (stop_loss_pct / 100.0)
            position_value = min(position_value, buying_power * 0.9)  # Max 90% of buying power

            # Get current price
            quote = self.api.get_latest_trade(symbol)
            current_price = quote.price

            # Calculate shares
            shares = int(position_value / current_price)

            if shares == 0:
                print(f"    Insufficient buying power for {symbol}")
                return

            # Place order
            print(f"    Placing order: BUY {shares} shares of {symbol} @ ${current_price:.2f}")

            order = self.api.submit_order(
                symbol=symbol,
                qty=shares,
                side='buy',
                type='market',
                time_in_force='day'
            )

            # Track position
            self.positions[symbol] = {
                'symbol': symbol,
                'shares': shares,
                'entry_price': current_price,
                'entry_time': datetime.now().isoformat(),
                'setup': setup,
                'order_id': order.id
            }

            print(f"    ✓ Order placed: {order.id}")

        except Exception as e:
            print(f"    ERROR placing order for {symbol}: {e}")

    def _manage_positions(self):
        """Manage open positions (check exits)"""

        symbols_to_close = []

        for symbol, position in self.positions.items():
            try:
                # Get current price
                quote = self.api.get_latest_trade(symbol)
                current_price = quote.price

                entry_price = position['entry_price']
                pnl_pct = (current_price - entry_price) / entry_price * 100

                setup = position['setup']
                exit_criteria = setup['exit']

                # Check take profit
                take_profit_pct = exit_criteria.get('take_profit_pct', 2.0)
                if pnl_pct >= take_profit_pct:
                    print(f"  ✓ TAKE PROFIT: {symbol} (+{pnl_pct:.1f}%)")
                    self._close_position(symbol, 'take_profit')
                    symbols_to_close.append(symbol)
                    continue

                # Check stop loss
                stop_loss_pct = exit_criteria.get('stop_loss_pct', -1.0)
                if pnl_pct <= stop_loss_pct:
                    print(f"  ✗ STOP LOSS: {symbol} ({pnl_pct:.1f}%)")
                    self._close_position(symbol, 'stop_loss')
                    symbols_to_close.append(symbol)
                    continue

                # Check time-based exit
                entry_time = datetime.fromisoformat(position['entry_time'])
                elapsed_minutes = (datetime.now() - entry_time).seconds / 60
                max_hold_minutes = exit_criteria.get('max_hold_minutes', 120)

                if elapsed_minutes >= max_hold_minutes:
                    print(f"  ⏰ TIME EXIT: {symbol} ({pnl_pct:+.1f}%)")
                    self._close_position(symbol, 'time_exit')
                    symbols_to_close.append(symbol)
                    continue

            except Exception as e:
                print(f"    Error managing {symbol}: {e}")

        # Remove closed positions
        for symbol in symbols_to_close:
            del self.positions[symbol]

    def _close_position(self, symbol: str, reason: str):
        """Close position and record trade"""

        try:
            position = self.positions[symbol]
            shares = position['shares']

            # Get current price
            quote = self.api.get_latest_trade(symbol)
            current_price = quote.price

            # Place sell order
            order = self.api.submit_order(
                symbol=symbol,
                qty=shares,
                side='sell',
                type='market',
                time_in_force='day'
            )

            # Calculate P&L
            entry_price = position['entry_price']
            pnl = (current_price - entry_price) * shares
            pnl_pct = (current_price - entry_price) / entry_price * 100

            # Record trade
            trade = {
                'symbol': symbol,
                'setup_type': position['setup'].get('setup_type'),
                'entry_price': entry_price,
                'exit_price': current_price,
                'shares': shares,
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2),
                'entry_time': position['entry_time'],
                'exit_time': datetime.now().isoformat(),
                'exit_reason': reason,
                'hold_time_minutes': (datetime.now() - datetime.fromisoformat(position['entry_time'])).seconds / 60
            }

            self.trades_today.append(trade)
            self.daily_pnl += pnl

            # Check circuit breaker
            self._check_circuit_breaker()

            print(f"    Trade closed: {symbol} | P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)")

        except Exception as e:
            print(f"    ERROR closing {symbol}: {e}")

    def _close_all_positions(self):
        """Close all positions at end of day"""

        for symbol in list(self.positions.keys()):
            print(f"  Closing {symbol}...")
            self._close_position(symbol, 'end_of_day')

    def _check_circuit_breaker(self):
        """Check if circuit breaker should trigger"""

        # Get account value
        account = self.api.get_account()
        account_value = float(account.equity)

        # Calculate daily loss percentage
        loss_pct = (self.daily_pnl / account_value) * 100

        # Trigger at -10% daily loss
        if loss_pct <= -10.0:
            self.circuit_breaker_active = True
            print(f"\n{'='*80}")
            print(f"CIRCUIT BREAKER TRIGGERED")
            print(f"Daily loss: {loss_pct:.1f}%")
            print(f"Trading HALTED for safety")
            print(f"{'='*80}\n")

            # Close all positions
            self._close_all_positions()

    # Helper methods

    def _load_watchlist(self, filename: str) -> List[Dict]:
        """Load watchlist from JSON file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                return data.get('watchlist', [])
        except Exception as e:
            print(f"Error loading watchlist: {e}")
            return []

    def _load_strategy_params(self) -> Dict:
        """Load current strategy parameters"""
        try:
            with open('llm_trading/strategy_params.json', 'r') as f:
                return json.load(f)
        except:
            # Default params if file doesn't exist
            return {
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'stop_loss_pct': -1.0,
                'take_profit_pct': 2.0,
                'position_size_pct': 0.015,
                'max_trades_per_day': 15,
                'max_hold_minutes': 120,
                'confidence_threshold': 70
            }

    def _save_performance(self):
        """Save today's performance data"""
        os.makedirs('llm_trading/performance', exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        performance = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat(),
            'trades': self.trades_today,
            'daily_pnl': round(self.daily_pnl, 2),
            'num_trades': len(self.trades_today),
            'circuit_breaker_triggered': self.circuit_breaker_active
        }

        # Save timestamped version
        with open(f'llm_trading/performance/performance_{timestamp}.json', 'w') as f:
            json.dump(performance, f, indent=2)

        # Save as latest
        with open('llm_trading/performance/performance_latest.json', 'w') as f:
            json.dump(performance, f, indent=2)

    def _in_time_window(self, window: str) -> bool:
        """Check if current time is within entry window"""
        try:
            # Parse window like "9:30am - 11:30am"
            parts = window.split('-')
            if len(parts) != 2:
                return True  # Invalid format, allow anytime

            start_str = parts[0].strip()
            end_str = parts[1].strip()

            # Convert to datetime
            now = datetime.now()
            start = datetime.strptime(start_str, '%I:%M%p').replace(
                year=now.year, month=now.month, day=now.day
            )
            end = datetime.strptime(end_str, '%I:%M%p').replace(
                year=now.year, month=now.month, day=now.day
            )

            return start <= now <= end

        except:
            return True  # Error parsing, allow anytime

    def _calculate_rsi(self, bars: pd.DataFrame, period: int = 14) -> float:
        """Calculate RSI indicator"""
        delta = bars['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    def _extract_price(self, text: str) -> Optional[float]:
        """Extract price from text like 'above 145.50'"""
        import re
        match = re.search(r'\d+\.\d+', text)
        if match:
            return float(match.group())
        return None

    def _extract_number(self, text: str) -> Optional[float]:
        """Extract first number from text"""
        import re
        match = re.search(r'\d+\.?\d*', text)
        if match:
            return float(match.group())
        return None


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    executor = RuleExecutor(
        api_key=os.getenv('ALPACA_API_KEY'),
        api_secret=os.getenv('ALPACA_SECRET_KEY'),
        paper=True,  # ALWAYS use paper trading for testing
        check_interval=60  # Check every minute
    )

    # Run trading session
    executor.run_trading_session()
