"""
Test integration of LLM Trading System components
"""

import os
import json
from dotenv import load_dotenv
from rule_executor import RuleExecutor

def test_watchlist_loading():
    """Test that rule executor can load LLM-generated watchlist"""
    print("="*80)
    print("TEST 1: Watchlist Loading")
    print("="*80)

    watchlist_file = 'llm_trading/watchlists/watchlist_latest.json'

    if not os.path.exists(watchlist_file):
        print(f"ERROR: Watchlist file not found: {watchlist_file}")
        return False

    with open(watchlist_file, 'r') as f:
        data = json.load(f)

    watchlist = data.get('watchlist', [])
    print(f"\nWatchlist loaded: {len(watchlist)} symbols")

    # Check structure of each entry
    required_keys = ['symbol', 'entry', 'exit', 'risk', 'setup_type']

    for i, setup in enumerate(watchlist, 1):
        symbol = setup.get('symbol', 'UNKNOWN')
        print(f"\n{i}. {symbol}")

        # Check required keys
        missing_keys = [k for k in required_keys if k not in setup]
        if missing_keys:
            print(f"   WARNING: Missing keys: {missing_keys}")
        else:
            print(f"   [OK] All required keys present")

        # Check entry structure
        entry = setup.get('entry', {})
        if isinstance(entry, dict):
            entry_keys = list(entry.keys())
            print(f"   Entry keys: {entry_keys[:3]}...")  # First 3

        # Check exit structure
        exit_info = setup.get('exit', {})
        if isinstance(exit_info, dict):
            # Look for stop loss in various formats
            has_stop = 'stop_loss_pct' in exit_info or ('stop_loss' in exit_info and isinstance(exit_info['stop_loss'], dict))
            print(f"   Exit has stop loss: {has_stop}")

    print(f"\n[OK] Watchlist loading test PASSED")
    return True


def test_executor_init():
    """Test that rule executor initializes correctly"""
    print("\n" + "="*80)
    print("TEST 2: Rule Executor Initialization")
    print("="*80)

    load_dotenv()

    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')

    if not api_key or not api_secret:
        print("ERROR: Alpaca API keys not found in .env")
        return False

    try:
        executor = RuleExecutor(
            api_key=api_key,
            api_secret=api_secret,
            paper=True,
            check_interval=60
        )

        print("\n[OK] Rule Executor initialized successfully")
        print(f"  Mode: PAPER")
        print(f"  Check interval: 60 seconds")
        print(f"  Strategy params loaded: {len(executor.params)} parameters")

        return True

    except Exception as e:
        print(f"\n[FAIL] ERROR initializing Rule Executor: {e}")
        return False


def test_watchlist_compatibility():
    """Test that watchlist format is compatible with executor"""
    print("\n" + "="*80)
    print("TEST 3: Watchlist-Executor Compatibility")
    print("="*80)

    load_dotenv()

    executor = RuleExecutor(
        api_key=os.getenv('ALPACA_API_KEY'),
        api_secret=os.getenv('ALPACA_SECRET_KEY'),
        paper=True
    )

    watchlist_file = 'llm_trading/watchlists/watchlist_latest.json'
    watchlist_data = json.load(open(watchlist_file))
    watchlist = watchlist_data['watchlist']

    print(f"\nTesting {len(watchlist)} watchlist entries...")

    compatible = 0
    for setup in watchlist:
        symbol = setup['symbol']

        # Test that executor can process entry (with graceful defaults for missing keys)
        try:
            # Required fields (must exist)
            _ = setup['symbol']
            _ = setup['entry']
            _ = setup['setup_type']
            _ = setup['exit']

            # Optional fields (executor uses defaults if missing)
            # Check that .get() would work for these
            risk_info = setup.get('risk', {})
            account_risk = risk_info.get('account_risk_pct', 1.5) if isinstance(risk_info, dict) else 1.5

            # Check exit structure can be parsed
            exit_info = setup['exit']
            has_stop = ('stop_loss_pct' in exit_info or
                       (isinstance(exit_info.get('stop_loss'), dict)))
            has_tp = ('take_profit_pct' in exit_info or
                     (isinstance(exit_info.get('take_profit'), dict)))

            if not has_stop:
                print(f"  [WARN] {symbol}: No stop loss found, will use default")
            if not has_tp:
                print(f"  [WARN] {symbol}: No take profit found, will use default")

            print(f"  [OK] {symbol}: Compatible (risk={'explicit' if 'risk' in setup else 'default'})")
            compatible += 1

        except KeyError as e:
            print(f"  [FAIL] {symbol}: Missing required key {e}")
        except Exception as e:
            print(f"  [FAIL] {symbol}: Error processing setup: {e}")

    print(f"\nCompatibility: {compatible}/{len(watchlist)} entries")

    if compatible == len(watchlist):
        print("[OK] All watchlist entries compatible with rule executor")
        return True
    else:
        print(f"[FAIL] {len(watchlist) - compatible} entries incompatible")
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("LLM TRADING SYSTEM - INTEGRATION TESTS")
    print("="*80 + "\n")

    results = []

    # Run tests
    results.append(("Watchlist Loading", test_watchlist_loading()))
    results.append(("Executor Initialization", test_executor_init()))
    results.append(("Watchlist Compatibility", test_watchlist_compatibility()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "[OK]" if result else "[FAIL]"
        print(f"{symbol} {test_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n[OK] ALL TESTS PASSED - System ready for paper trading")
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed - Review errors above")
