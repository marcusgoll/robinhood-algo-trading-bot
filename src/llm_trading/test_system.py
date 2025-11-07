"""
Test script for LLM Trading System

Tests each component individually to ensure everything works before
running the full daily cycle.
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_market_context():
    """Test market context builder"""
    print("\n" + "="*80)
    print("TEST 1: Market Context Builder")
    print("="*80)

    try:
        from market_context import MarketContextBuilder

        builder = MarketContextBuilder(
            api_key=os.getenv('ALPACA_API_KEY'),
            api_secret=os.getenv('ALPACA_SECRET_KEY')
        )

        print("\n[OK] MarketContextBuilder initialized")

        # Test with SPY (should always have data)
        print("\nFetching SPY context...")
        context = builder.build_full_context('SPY')

        if 'error' in context:
            print(f"[FAIL] Error: {context['error']}")
            return False

        print(f"[OK] Context built successfully")
        print(f"\nSample output:")
        print(f"  Symbol: {context['symbol']}")
        print(f"  Current price: ${context['price_action']['current_price']:.2f}")
        print(f"  RSI: {context['technicals']['rsi_14']['value']:.1f} ({context['technicals']['rsi_14']['level']})")
        print(f"  Interpretation: {context['technicals']['rsi_14']['interpretation']}")

        return True

    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_screener():
    """Test LLM morning screener"""
    print("\n" + "="*80)
    print("TEST 2: LLM Morning Screener")
    print("="*80)

    try:
        from llm_screener import LLMScreener

        screener = LLMScreener(
            api_key_alpaca=os.getenv('ALPACA_API_KEY'),
            api_secret_alpaca=os.getenv('ALPACA_SECRET_KEY'),
            api_key_anthropic=os.getenv('ANTHROPIC_API_KEY')
        )

        print("\n[OK] LLMScreener initialized")

        # Test with small candidate list
        print("\nGenerating watchlist (this will take ~30 seconds)...")
        candidates = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL']

        watchlist = screener.generate_watchlist(candidates, max_picks=3)

        if not watchlist:
            print("[FAIL] No watchlist generated")
            return False

        print(f"[OK] Watchlist generated: {len(watchlist)} stocks")

        print("\nWatchlist:")
        for i, entry in enumerate(watchlist, 1):
            print(f"\n{i}. {entry['symbol']} ({entry['confidence']}% confidence)")
            print(f"   Setup: {entry['setup_type']}")
            print(f"   Catalyst: {entry['catalyst'][:60]}...")

        return True

    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rule_executor():
    """Test rule executor (without actual trading)"""
    print("\n" + "="*80)
    print("TEST 3: Rule Executor")
    print("="*80)

    try:
        from rule_executor import RuleExecutor

        executor = RuleExecutor(
            api_key=os.getenv('ALPACA_API_KEY'),
            api_secret=os.getenv('ALPACA_SECRET_KEY'),
            paper=True,
            check_interval=60
        )

        print("\n[OK] RuleExecutor initialized")
        print("[OK] Paper trading mode: ON")
        print("[OK] Check interval: 60 seconds")

        # Check if watchlist exists
        if not os.path.exists('watchlists/watchlist_latest.json'):
            print("\n[WARN] No watchlist found (run test 2 first)")
            print("  RuleExecutor would load watchlist before trading")
        else:
            print("\n[OK] Watchlist found")

        print("\n[OK] RuleExecutor ready (trading not started)")

        return True

    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_optimizer():
    """Test LLM optimizer with mock data"""
    print("\n" + "="*80)
    print("TEST 4: LLM Evening Optimizer")
    print("="*80)

    try:
        from llm_optimizer import LLMOptimizer

        optimizer = LLMOptimizer(
            api_key_anthropic=os.getenv('ANTHROPIC_API_KEY'),
            autonomy_level=1  # Supervised
        )

        print("\n[OK] LLMOptimizer initialized")
        print("[OK] Autonomy level: 1 (Supervised)")

        # Mock performance data
        mock_performance = {
            'trades': [
                {'symbol': 'NVDA', 'setup_type': 'oversold_bounce', 'pnl': 2.1, 'exit_reason': 'take_profit'},
                {'symbol': 'TSLA', 'setup_type': 'breakout', 'pnl': -1.0, 'exit_reason': 'stop_loss'},
                {'symbol': 'AAPL', 'setup_type': 'oversold_bounce', 'pnl': 1.5, 'exit_reason': 'take_profit'},
            ]
        }

        mock_watchlist = {'watchlist': ['NVDA', 'TSLA', 'AAPL']}
        mock_market = {'spy_trend': 'risk-on', 'vix': 15.2, 'regime': 'normal_volatility'}

        print("\nTesting optimization with mock data...")
        print("Note: This will ask for approval (Level 1 mode)")
        print("You can decline all proposals to just test the system")

        # Don't actually run optimizer in automated test
        print("\n[OK] LLMOptimizer ready (optimization not started)")
        print("  To test: Run llm_optimizer.py directly")

        return True

    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_main_orchestrator():
    """Test main orchestrator"""
    print("\n" + "="*80)
    print("TEST 5: Main Orchestrator")
    print("="*80)

    try:
        from main import TradingSystem

        system = TradingSystem(
            alpaca_api_key=os.getenv('ALPACA_API_KEY'),
            alpaca_secret_key=os.getenv('ALPACA_SECRET_KEY'),
            anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
            autonomy_level=1,
            paper=True
        )

        print("\n[OK] TradingSystem initialized")
        print("[OK] Paper trading mode: ON")
        print("[OK] Autonomy level: 1 (Supervised)")

        print("\n[OK] Main orchestrator ready")
        print("  To run: python llm_trading/main.py")

        return True

    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("LLM TRADING SYSTEM - COMPONENT TESTS")
    print("="*80)

    # Check API keys
    print("\nChecking API keys...")
    api_keys = {
        'ALPACA_API_KEY': os.getenv('ALPACA_API_KEY'),
        'ALPACA_SECRET_KEY': os.getenv('ALPACA_SECRET_KEY'),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY')
    }

    missing = [k for k, v in api_keys.items() if not v]
    if missing:
        print(f"[FAIL] Missing API keys: {', '.join(missing)}")
        print("  Add them to .env file")
        return

    print("[OK] All API keys found")

    # Run tests
    results = {
        'Market Context Builder': test_market_context(),
        'LLM Screener': test_llm_screener(),
        'Rule Executor': test_rule_executor(),
        'LLM Optimizer': test_llm_optimizer(),
        'Main Orchestrator': test_main_orchestrator()
    }

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for name, passed in results.items():
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"{status}: {name}")

    passed = sum(results.values())
    total = len(results)

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n[OK] System ready for use!")
        print("\nNext steps:")
        print("1. Run: python llm_trading/llm_screener.py (test screener)")
        print("2. Run: python llm_trading/main.py (full system)")
    else:
        print("\n[FAIL] Some tests failed. Check errors above.")


if __name__ == "__main__":
    main()
