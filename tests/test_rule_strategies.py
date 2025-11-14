#!/usr/bin/env python3
"""Quick test script for rule-based strategies."""

import pandas as pd
from trading_bot.ml.generators.rule_based import RuleBasedGenerator
from trading_bot.data import PolygonDataFetcher

# Fetch SPY data
print("Fetching SPY data...")
fetcher = PolygonDataFetcher()
data = fetcher.fetch("SPY", span="year")

print(f"Loaded {len(data)} bars of SPY data")
print(f"Date range: {data.index[0]} to {data.index[-1]}")

# Generate rule-based strategies
print("\nGenerating rule-based strategies...")
generator = RuleBasedGenerator()
strategies = generator.generate(
    num_strategies=5,
    historical_data=data,
    config={}
)

# Display results
print(f"\n{'='*80}")
print("RULE-BASED STRATEGY TEST RESULTS")
print(f"{'='*80}")

for i, strategy in enumerate(strategies, 1):
    metrics = strategy.backtest_metrics
    status = "✓ PASS" if metrics.is_production_ready() else "✗ FAIL"

    print(f"\n{i}. {strategy.name} {status}")
    print(f"   Entry: {strategy.entry_logic}")
    print(f"   Sharpe: {metrics.sharpe_ratio:.2f}")
    print(f"   Max DD: {metrics.max_drawdown:.1%}")
    print(f"   Win Rate: {metrics.win_rate:.1%}")
    print(f"   Trades: {metrics.num_trades}")
    print(f"   Return: {metrics.total_return:.1%}")

passed = sum(1 for s in strategies if s.backtest_metrics.is_production_ready())
print(f"\n{'='*80}")
print(f"Summary: {passed}/{len(strategies)} strategies passed ({passed/len(strategies)*100:.0f}%)")
print(f"{'='*80}")
