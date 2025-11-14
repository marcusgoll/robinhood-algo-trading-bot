#!/usr/bin/env python3
"""Test rule ensemble across multiple symbols and timeframes.

Tests:
1. Single symbol, single timeframe - baseline
2. Multiple symbols - generalization test
3. Multiple timeframes (daily, weekly) - robustness test
4. Multi-timeframe ensemble - combined signals
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
from trading_bot.ml.generators.rule_based import RuleBasedGenerator
from trading_bot.ml.generators.ensemble import RuleEnsembleGenerator
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.config import Config


def main():
    print("="*80)
    print("RULE ENSEMBLE - MULTI-SYMBOL & MULTI-TIMEFRAME TEST")
    print("="*80)

    # Initialize auth
    print("\n1. Authenticating...")
    config = Config.from_env_and_json()
    auth = RobinhoodAuth(config)
    auth.login()
    print("   [OK] Authenticated")

    # Test configuration
    symbols = ["SPY", "QQQ", "NVDA", "TSLA"]
    timeframes = {
        "daily": ("day", "year"),  # (interval, span)
        "weekly": ("week", "5year")
    }

    market_data_service = MarketDataService(auth)
    rule_generator = RuleBasedGenerator()
    ensemble_generator = RuleEnsembleGenerator()

    # ========================================================================
    # PART 1: Test ensembles on each symbol (daily data)
    # ========================================================================
    print(f"\n{'='*80}")
    print("PART 1: ENSEMBLE PERFORMANCE PER SYMBOL (DAILY)")
    print(f"{'='*80}\n")

    symbol_results = {}

    for symbol in symbols:
        print(f"\nTesting {symbol}...")
        print("-" * 40)

        try:
            # Fetch data
            data = market_data_service.get_historical_data(symbol, interval="day", span="year")
            print(f"   Loaded {len(data)} bars")

            # Generate all rules
            strategies = rule_generator.generate(
                num_strategies=15,
                historical_data=data,
                config={}
            )

            # Count production-ready
            prod_ready = sum(1 for s in strategies if s.backtest_metrics and s.backtest_metrics.is_production_ready())

            # Create ensemble from top 5
            try:
                ensemble = ensemble_generator.create_ensemble(
                    strategies=strategies,
                    weighting="sharpe",
                    top_k=5,
                    min_agreement=0.25  # Low threshold to allow minority votes
                )

                # Backtest ensemble
                ens_metrics = ensemble.backtest(data)

                # Get best individual for comparison
                valid_strats = [s for s in strategies if s.backtest_metrics and s.backtest_metrics.num_trades > 0]
                if valid_strats:
                    best_individual = max(valid_strats, key=lambda s: s.backtest_metrics.sharpe_ratio)
                    best_metrics = best_individual.backtest_metrics
                else:
                    best_individual = None
                    best_metrics = None

                # Display results
                print(f"\n   Individual Rules:")
                print(f"      Tested: 15")
                print(f"      Production Ready: {prod_ready}")
                if best_metrics:
                    print(f"      Best Sharpe: {best_metrics.sharpe_ratio:.2f} ({best_individual.name})")
                    print(f"      Best Return: {best_metrics.total_return:.1%}")
                    print(f"      Best Trades: {best_metrics.num_trades}")

                print(f"\n   Ensemble (Top 5, Sharpe-weighted):")
                print(f"      Sharpe: {ens_metrics.sharpe_ratio:.2f}")
                print(f"      Return: {ens_metrics.total_return:.1%}")
                print(f"      Max DD: {ens_metrics.max_drawdown:.1%}")
                print(f"      Win Rate: {ens_metrics.win_rate:.1%}")
                print(f"      Trades: {ens_metrics.num_trades}")

                # Calculate improvement
                if best_metrics and best_metrics.sharpe_ratio > 0:
                    improvement = ((ens_metrics.sharpe_ratio - best_metrics.sharpe_ratio) /
                                 best_metrics.sharpe_ratio * 100)
                    print(f"\n   Ensemble vs Best Individual:")
                    print(f"      Sharpe Improvement: {improvement:+.1f}%")

                symbol_results[symbol] = {
                    'ensemble': ens_metrics,
                    'best_individual': best_metrics,
                    'prod_ready': prod_ready
                }

            except ValueError as e:
                print(f"   [ERROR] Could not create ensemble: {e}")
                symbol_results[symbol] = None

        except Exception as e:
            print(f"   [ERROR] Failed to test {symbol}: {e}")
            symbol_results[symbol] = None

    # ========================================================================
    # PART 2: Multi-timeframe ensemble (SPY only)
    # ========================================================================
    print(f"\n\n{'='*80}")
    print("PART 2: MULTI-TIMEFRAME ENSEMBLE (SPY)")
    print(f"{'='*80}\n")

    print("Testing SPY across multiple timeframes...")

    strategies_by_tf = {}

    for tf_name, (interval, span) in timeframes.items():
        print(f"\n{tf_name.upper()} ({interval}, {span}):")
        print("-" * 40)

        try:
            # Fetch data
            data = market_data_service.get_historical_data("SPY", interval=interval, span=span)
            print(f"   Loaded {len(data)} bars")

            # Generate rules
            strategies = rule_generator.generate(
                num_strategies=15,
                historical_data=data,
                config={}
            )

            strategies_by_tf[tf_name] = strategies

            # Show top 3
            valid = [s for s in strategies if s.backtest_metrics and s.backtest_metrics.num_trades > 0]
            sorted_strats = sorted(valid, key=lambda s: s.backtest_metrics.sharpe_ratio, reverse=True)

            print(f"\n   Top 3 performers:")
            for i, s in enumerate(sorted_strats[:3], 1):
                m = s.backtest_metrics
                print(f"      {i}. {s.name}: Sharpe={m.sharpe_ratio:.2f}, Return={m.total_return:.1%}, Trades={m.num_trades}")

        except Exception as e:
            print(f"   [ERROR] Failed: {e}")

    # Create multi-timeframe ensemble
    if len(strategies_by_tf) >= 2:
        print(f"\n\nCreating multi-timeframe ensemble...")
        print("-" * 40)

        try:
            mtf_ensemble = ensemble_generator.create_multi_timeframe_ensemble(
                strategies_by_timeframe=strategies_by_tf,
                weighting="sharpe",
                top_k_per_tf=3
            )

            # Backtest on daily data (primary timeframe)
            daily_data = market_data_service.get_historical_data("SPY", interval="day", span="year")
            mtf_metrics = mtf_ensemble.backtest(daily_data)

            print(f"\n   Multi-Timeframe Ensemble:")
            print(f"      Members: {len(mtf_ensemble.members)}")
            print(f"      Sharpe: {mtf_metrics.sharpe_ratio:.2f}")
            print(f"      Return: {mtf_metrics.total_return:.1%}")
            print(f"      Max DD: {mtf_metrics.max_drawdown:.1%}")
            print(f"      Win Rate: {mtf_metrics.win_rate:.1%}")
            print(f"      Trades: {mtf_metrics.num_trades}")

        except Exception as e:
            print(f"   [ERROR] Could not create MTF ensemble: {e}")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    # Symbol comparison
    print("Ensemble Performance by Symbol:")
    print(f"{'Symbol':<10} | {'Sharpe':<8} | {'Return':<8} | {'Trades':<8} | Status")
    print("-" * 60)

    for symbol in symbols:
        result = symbol_results.get(symbol)
        if result and result['ensemble']:
            ens = result['ensemble']
            status = "[PASS]" if ens.is_production_ready() else "[FAIL]"
            print(f"{symbol:<10} | {ens.sharpe_ratio:7.2f} | {ens.total_return:7.1%} | "
                  f"{ens.num_trades:7d} | {status}")
        else:
            print(f"{symbol:<10} | {'N/A':<7} | {'N/A':<7} | {'N/A':<7} | [ERROR]")

    # Overall stats
    valid_results = [r for r in symbol_results.values() if r and r['ensemble']]
    if valid_results:
        avg_sharpe = sum(r['ensemble'].sharpe_ratio for r in valid_results) / len(valid_results)
        avg_return = sum(r['ensemble'].total_return for r in valid_results) / len(valid_results)
        avg_trades = sum(r['ensemble'].num_trades for r in valid_results) / len(valid_results)

        print(f"\nAverages across {len(valid_results)} symbols:")
        print(f"   Sharpe: {avg_sharpe:.2f}")
        print(f"   Return: {avg_return:.1%}")
        print(f"   Trades: {avg_trades:.0f}")

    # Recommendations
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}\n")

    # Find best performing ensemble
    best_symbol = None
    best_sharpe = -999

    for symbol, result in symbol_results.items():
        if result and result['ensemble']:
            if result['ensemble'].sharpe_ratio > best_sharpe:
                best_sharpe = result['ensemble'].sharpe_ratio
                best_symbol = symbol

    if best_symbol:
        print(f"1. Deploy {best_symbol} ensemble to paper trading (Sharpe={best_sharpe:.2f})")
    else:
        print("1. No production-ready ensembles found")

    print("2. Monitor ensemble performance for 2-4 weeks on paper")
    print("3. If paper trading successful, deploy to live with 5% capital allocation")
    print("4. Gradually increase to 20% if performance holds")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
