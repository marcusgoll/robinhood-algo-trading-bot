#!/usr/bin/env python3
"""Test all 15 rule-based strategies on SPY data.

This script:
1. Loads SPY historical data
2. Tests each of the 15 rules
3. Reports pass/fail and performance metrics
4. Uses train/validation split (80/20)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
from trading_bot.ml.generators.rule_based import RuleBasedGenerator
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.config import Config


def main():
    print("="*80)
    print("RULE-BASED STRATEGY TEST - ALL 15 RULES")
    print("="*80)

    # Initialize auth
    print("\n1. Authenticating...")
    config = Config.from_env_and_json()
    auth = RobinhoodAuth(config)
    auth.login()
    print("   [OK] Authenticated")

    # Fetch SPY data
    print("\n2. Fetching SPY historical data (1 year)...")
    market_data_service = MarketDataService(auth)

    try:
        data = market_data_service.get_historical_data("SPY", interval="day", span="year")
        print(f"   [OK] Loaded {len(data)} bars")
        print(f"   Date range: {data['date'].iloc[0]} to {data['date'].iloc[-1]}")
    except Exception as e:
        print(f"   [ERROR] Error fetching data: {e}")
        return

    # Split data for validation
    split_idx = int(len(data) * 0.8)
    train_data = data.iloc[:split_idx].copy()
    val_data = data.iloc[split_idx:].copy()

    print(f"\n3. Data split:")
    print(f"   Train: {len(train_data)} bars ({train_data['date'].iloc[0]} to {train_data['date'].iloc[-1]})")
    print(f"   Val:   {len(val_data)} bars ({val_data['date'].iloc[0]} to {val_data['date'].iloc[-1]})")

    # Generate all rules
    print(f"\n4. Testing all 15 rule-based strategies...")
    print("="*80)

    generator = RuleBasedGenerator()

    # Test on FULL data first (to match GP comparison)
    strategies = generator.generate(
        num_strategies=15,
        historical_data=data,
        config={}
    )

    # Display results
    print(f"\n{'='*80}")
    print("RESULTS - FULL DATASET (for comparison with GP)")
    print(f"{'='*80}\n")

    passed_full = 0
    results_full = []

    for i, strategy in enumerate(strategies, 1):
        metrics = strategy.backtest_metrics
        passed = metrics.is_production_ready()
        status = "[PASS]" if passed else "[FAIL]"

        if passed:
            passed_full += 1

        results_full.append({
            'name': strategy.name,
            'sharpe': metrics.sharpe_ratio,
            'max_dd': metrics.max_drawdown,
            'win_rate': metrics.win_rate,
            'trades': metrics.num_trades,
            'return': metrics.total_return,
            'passed': passed
        })

        print(f"{i:2d}. {strategy.name:30s} {status}")
        print(f"    Entry: {strategy.entry_logic[:70]}")
        print(f"    Sharpe: {metrics.sharpe_ratio:6.2f} | DD: {metrics.max_drawdown:6.1%} | "
              f"Win: {metrics.win_rate:5.1%} | Trades: {metrics.num_trades:3d} | "
              f"Return: {metrics.total_return:6.1%}")
        print()

    # Now test with train/val split
    print(f"\n{'='*80}")
    print("RESULTS - TRAIN/VALIDATION SPLIT (80/20)")
    print(f"{'='*80}\n")

    print("Testing on TRAIN data...")
    train_strategies = generator.generate(
        num_strategies=15,
        historical_data=train_data,
        config={}
    )

    print("Testing on VALIDATION data...")
    val_strategies = generator.generate(
        num_strategies=15,
        historical_data=val_data,
        config={}
    )

    print(f"\n{'Rule':<30} | {'Train Sharpe':<12} | {'Val Sharpe':<12} | {'Degradation':<12} | Status")
    print("-"*95)

    passed_val = 0
    for i in range(15):
        train_metrics = train_strategies[i].backtest_metrics
        val_metrics = val_strategies[i].backtest_metrics

        # Calculate degradation
        if train_metrics.sharpe_ratio > 0:
            degradation_pct = ((train_metrics.sharpe_ratio - val_metrics.sharpe_ratio) /
                              train_metrics.sharpe_ratio * 100)
        else:
            degradation_pct = 0.0

        # Check if passes validation (val Sharpe > 1.0, trades >= 20, degradation < 50%)
        passed_validation = (
            val_metrics.sharpe_ratio > 1.0 and
            val_metrics.num_trades >= 20 and
            degradation_pct < 50
        )

        if passed_validation:
            passed_val += 1
            status = "[PASS]"
        else:
            status = "[FAIL]"

        print(f"{train_strategies[i].name:<30} | "
              f"{train_metrics.sharpe_ratio:11.2f} | "
              f"{val_metrics.sharpe_ratio:11.2f} | "
              f"{degradation_pct:11.1f}% | "
              f"{status}")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"\nFull Dataset:")
    print(f"  Strategies Tested: {len(strategies)}")
    print(f"  Production Ready:  {passed_full} ({passed_full/len(strategies)*100:.0f}%)")
    print(f"  Avg Sharpe:        {sum(r['sharpe'] for r in results_full)/len(results_full):.2f}")
    print(f"  Avg Trades:        {sum(r['trades'] for r in results_full)/len(results_full):.0f}")

    print(f"\nTrain/Validation Split:")
    print(f"  Passed Validation: {passed_val}/{len(strategies)} ({passed_val/len(strategies)*100:.0f}%)")
    print(f"  Train Avg Sharpe:  {sum(s.backtest_metrics.sharpe_ratio for s in train_strategies)/len(train_strategies):.2f}")
    print(f"  Val Avg Sharpe:    {sum(s.backtest_metrics.sharpe_ratio for s in val_strategies)/len(val_strategies):.2f}")

    # Comparison with GP
    print(f"\n{'='*80}")
    print("COMPARISON WITH GP RESULTS")
    print(f"{'='*80}")
    print(f"\nGP (with train/val split):")
    print(f"  Strategies:        5")
    print(f"  Production Ready:  0 (0%)")
    print(f"  Train Sharpe:      0.88")
    print(f"  Val Sharpe:        0.01")
    print(f"  Degradation:       99%")

    print(f"\nRule-Based (this test):")
    print(f"  Strategies:        15")
    print(f"  Production Ready:  {passed_full} ({passed_full/15*100:.0f}%) on full data")
    print(f"  Passed Validation: {passed_val} ({passed_val/15*100:.0f}%) on split")
    print(f"  Avg Train Sharpe:  {sum(s.backtest_metrics.sharpe_ratio for s in train_strategies)/15:.2f}")
    print(f"  Avg Val Sharpe:    {sum(s.backtest_metrics.sharpe_ratio for s in val_strategies)/15:.2f}")

    if passed_val > 0:
        print(f"\n[SUCCESS] Rule-based approach WORKS!")
        print(f"  {passed_val} rules generalize to validation data")
        print(f"  vs 0 GP strategies")
    else:
        print(f"\n[WARNING] No rules passed validation")
        print(f"  May need parameter tuning or different market conditions")

    print(f"\n{'='*80}")


if __name__ == "__main__":
    main()
