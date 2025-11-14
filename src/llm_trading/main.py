"""
LLM Trading System - Main Orchestrator

Coordinates the daily trading cycle:
- Morning (9:00am): Generate watchlist
- Intraday (9:30am-4pm): Execute trades
- Evening (5:00pm): Optimize strategy

This is the main entry point for the autonomous trading system.
"""

import os
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv

from .llm_screener import LLMScreener
from .rule_executor import RuleExecutor
from .llm_optimizer import LLMOptimizer
from .market_context import MarketContextBuilder


class TradingSystem:
    """Main orchestrator for LLM-powered trading system"""

    def __init__(self,
                 alpaca_api_key: str,
                 alpaca_secret_key: str,
                 anthropic_api_key: str,
                 autonomy_level: int = 1,
                 paper: bool = True):
        """
        Args:
            alpaca_api_key: Alpaca API key
            alpaca_secret_key: Alpaca secret key
            anthropic_api_key: Anthropic API key
            autonomy_level: 1=supervised, 2=bounded, 3=fully autonomous
            paper: Use paper trading (True) or live (False)
        """
        self.alpaca_key = alpaca_api_key
        self.alpaca_secret = alpaca_secret_key
        self.anthropic_key = anthropic_api_key
        self.autonomy_level = autonomy_level
        self.paper = paper

        # Components
        self.screener = None
        self.executor = None
        self.optimizer = None

        print(f"\n{'='*80}")
        print(f"LLM TRADING SYSTEM")
        print(f"{'='*80}")
        print(f"Mode: {'PAPER' if paper else 'LIVE'}")
        print(f"Autonomy Level: {autonomy_level}")
        print(f"{'='*80}\n")

    def run_morning_screener(self):
        """Morning routine: Generate watchlist (9:00am)"""
        print(f"\n{'='*80}")
        print(f"MORNING SCREENER - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*80}\n")

        if self.screener is None:
            self.screener = LLMScreener(
                api_key_alpaca=self.alpaca_key,
                api_secret_alpaca=self.alpaca_secret,
                api_key_anthropic=self.anthropic_key
            )

        # Get candidate symbols (top volume stocks)
        # For now, using common high-volume stocks
        # In production, would fetch dynamically from market data
        candidates = [
            'SPY', 'QQQ', 'IWM',  # ETFs
            'NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',  # Big tech
            'AMD', 'NFLX', 'DIS', 'BABA', 'BA',  # Others
            'JPM', 'GS', 'BAC',  # Financials
            'XOM', 'CVX'  # Energy
        ]

        # Generate watchlist
        watchlist = self.screener.generate_watchlist(candidates, max_picks=15)

        print(f"\nWatchlist generation complete!")
        print(f"Ready for trading at market open (9:30am)\n")

        return watchlist

    def run_trading_session(self):
        """Intraday routine: Execute trades (9:30am-4pm)"""
        print(f"\n{'='*80}")
        print(f"TRADING SESSION STARTING - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*80}\n")

        if self.executor is None:
            self.executor = RuleExecutor(
                api_key=self.alpaca_key,
                api_secret=self.alpaca_secret,
                paper=self.paper,
                check_interval=60  # Check every minute
            )

        # Run trading session (blocks until market close)
        self.executor.run_trading_session()

        print(f"\nTrading session complete!\n")

    def run_evening_optimizer(self):
        """Evening routine: Analyze and optimize (5:00pm)"""
        print(f"\n{'='*80}")
        print(f"EVENING OPTIMIZER - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*80}\n")

        if self.optimizer is None:
            self.optimizer = LLMOptimizer(
                api_key_anthropic=self.anthropic_key,
                autonomy_level=self.autonomy_level
            )

        # Load today's performance
        try:
            import json
            with open('llm_trading/performance/performance_latest.json', 'r') as f:
                performance = json.load(f)
        except:
            print("No performance data found. Skipping optimization.")
            return

        # Load watchlist
        try:
            with open('watchlists/watchlist_latest.json', 'r') as f:
                watchlist = json.load(f)
        except:
            watchlist = {}

        # Get market conditions
        context_builder = MarketContextBuilder(self.alpaca_key, self.alpaca_secret)
        market_context = context_builder.build_full_context('SPY')['market_context']

        # Run optimization
        report = self.optimizer.optimize_strategy(
            performance_data=performance,
            watchlist_data=watchlist,
            market_conditions=market_context
        )

        print(f"\nOptimization complete!\n")

        return report

    def run_daily_cycle(self):
        """Run full daily trading cycle (for manual execution)"""
        print(f"\n{'='*80}")
        print(f"STARTING DAILY CYCLE")
        print(f"{'='*80}\n")

        # Morning: Generate watchlist
        print("\n[1/3] Running morning screener...")
        self.run_morning_screener()

        # Intraday: Trade (only if market is open)
        import alpaca_trade_api as tradeapi
        api = tradeapi.REST(self.alpaca_key, self.alpaca_secret,
                           "https://paper-api.alpaca.markets", api_version='v2')
        clock = api.get_clock()

        if clock.is_open:
            print("\n[2/3] Starting trading session...")
            self.run_trading_session()
        else:
            print(f"\n[2/3] Market is closed. Skipping trading.")
            print(f"Next open: {clock.next_open}")

        # Evening: Optimize
        print("\n[3/3] Running evening optimizer...")
        self.run_evening_optimizer()

        print(f"\n{'='*80}")
        print(f"DAILY CYCLE COMPLETE")
        print(f"{'='*80}\n")

    def schedule_daily_cycle(self):
        """Schedule automated daily trading cycle"""
        print(f"\n{'='*80}")
        print(f"SCHEDULING AUTOMATED DAILY CYCLE")
        print(f"{'='*80}\n")

        # Schedule morning screener (9:00am)
        schedule.every().day.at("09:00").do(self.run_morning_screener)
        print("✓ Morning screener scheduled for 9:00am")

        # Schedule trading session (9:30am)
        schedule.every().day.at("09:30").do(self.run_trading_session)
        print("✓ Trading session scheduled for 9:30am")

        # Schedule evening optimizer (5:00pm)
        schedule.every().day.at("17:00").do(self.run_evening_optimizer)
        print("✓ Evening optimizer scheduled for 5:00pm")

        print("\n Scheduler active. Press Ctrl+C to stop.\n")

        # Run scheduler
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            print("\n\nScheduler stopped by user\n")


def main():
    """Main entry point"""
    load_dotenv()

    # Load credentials
    alpaca_key = os.getenv('ALPACA_API_KEY')
    alpaca_secret = os.getenv('ALPACA_SECRET_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')

    if not all([alpaca_key, alpaca_secret, anthropic_key]):
        print("ERROR: Missing API credentials in .env file")
        print("Required: ALPACA_API_KEY, ALPACA_SECRET_KEY, ANTHROPIC_API_KEY")
        return

    # Create system
    system = TradingSystem(
        alpaca_api_key=alpaca_key,
        alpaca_secret_key=alpaca_secret,
        anthropic_api_key=anthropic_key,
        autonomy_level=1,  # Start with supervised mode
        paper=True  # ALWAYS use paper trading initially
    )

    # Choose mode
    print("Select mode:")
    print("1. Run daily cycle once (manual)")
    print("2. Schedule automated daily cycle")
    print("3. Run morning screener only")
    print("4. Run trading session only (requires watchlist)")
    print("5. Run evening optimizer only (requires performance data)")

    choice = input("\nEnter choice (1-5): ").strip()

    if choice == '1':
        system.run_daily_cycle()
    elif choice == '2':
        system.schedule_daily_cycle()
    elif choice == '3':
        system.run_morning_screener()
    elif choice == '4':
        system.run_trading_session()
    elif choice == '5':
        system.run_evening_optimizer()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
