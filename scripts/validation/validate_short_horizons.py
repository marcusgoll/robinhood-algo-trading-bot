"""
Phase 7A: Short Horizon Validation

Test if baseline model works for day trading timeframes:
- 10 bars (50 minutes) - Very short-term
- 20 bars (1.7 hours) - Short-term
- 30 bars (2.5 hours) - Medium short-term
- 78 bars (6.5 hours) - Baseline for comparison

Goal: Find optimal horizon for high-frequency day trading (10-20 trades/day)
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import torch
from validate_multi_symbol_baseline import set_seed, create_baseline_dataset, train_and_evaluate


def validate_horizon(symbol: str, horizon_bars: int, api_key: str, api_secret: str, num_trials: int = 3):
    """
    Test a single prediction horizon with multiple seeds.

    Returns:
        Dictionary with statistics
    """
    print(f"\nHorizon: {horizon_bars} bars ({horizon_bars * 5:.0f} minutes)")
    print("-" * 60)

    try:
        # Fetch data
        X, y, features = create_baseline_dataset(
            symbol=symbol,
            horizon_bars=horizon_bars,
            days=60,
            api_key=api_key,
            api_secret=api_secret
        )

        print(f"Dataset: {len(X)} samples")

        # Run multiple trials
        accuracies = []
        for seed in range(num_trials):
            print(f"  Trial {seed+1}/{num_trials} (seed={seed})... ", end="", flush=True)
            acc = train_and_evaluate(X, y, f"{symbol} {horizon_bars}bar", seed=seed, epochs=30)
            accuracies.append(acc)
            print(f"{acc:.2f}%")

        mean_acc = np.mean(accuracies)
        std_acc = np.std(accuracies)
        min_acc = np.min(accuracies)
        max_acc = np.max(accuracies)

        print(f"\n  Summary:")
        print(f"    Mean: {mean_acc:.2f}% ± {std_acc:.2f}%")
        print(f"    Range: [{min_acc:.2f}%, {max_acc:.2f}%]")
        print(f"    Stability: {'STABLE' if std_acc < 2.0 else 'UNSTABLE'}")

        # Calculate trades per day potential
        hours_per_bar = (horizon_bars * 5) / 60
        market_hours = 6.5  # 9:30am-4:00pm
        max_trades_per_day = int(market_hours / hours_per_bar)

        print(f"    Trading frequency: Up to {max_trades_per_day} trades/day/symbol")

        return {
            'horizon_bars': horizon_bars,
            'horizon_hours': hours_per_bar,
            'mean_acc': mean_acc,
            'std_acc': std_acc,
            'min_acc': min_acc,
            'max_acc': max_acc,
            'num_samples': len(X),
            'trades_per_day': max_trades_per_day,
            'trials': accuracies,
            'status': 'success'
        }

    except Exception as e:
        print(f"\n  ERROR: {str(e)}")
        return {
            'horizon_bars': horizon_bars,
            'status': 'failed',
            'error': str(e)
        }


def main():
    load_dotenv()
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')

    if not api_key or not api_secret:
        print("ERROR: Missing Alpaca credentials")
        return

    print("=" * 80)
    print("PHASE 7A: SHORT HORIZON VALIDATION")
    print("=" * 80)
    print()
    print("Testing if baseline model works for day trading timeframes")
    print("Goal: Find optimal horizon for 10-20 trades/day")
    print()

    symbol = 'SPY'
    horizons = [10, 20, 30, 78]  # bars (50min, 1.7hr, 2.5hr, 6.5hr)
    num_trials = 3  # Faster than 5 for initial validation

    results = []

    for horizon in horizons:
        result = validate_horizon(symbol, horizon, api_key, api_secret, num_trials)
        results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print()

    df = pd.DataFrame(results)
    successful = df[df['status'] == 'success']

    if len(successful) > 0:
        print("Horizon Performance:")
        print()
        print(f"{'Horizon':<12} {'Time':<12} {'Mean Acc':<12} {'Std':<8} {'Trades/Day':<12} {'Verdict':<15}")
        print("-" * 75)

        for _, row in successful.iterrows():
            horizon_str = f"{row['horizon_bars']} bars"
            time_str = f"{row['horizon_hours']:.1f}h"
            verdict = 'EXCELLENT' if row['mean_acc'] >= 58 and row['std_acc'] < 2 else \
                     'GOOD' if row['mean_acc'] >= 55 and row['std_acc'] < 5 else \
                     'MARGINAL' if row['mean_acc'] >= 52 else 'POOR'

            print(f"{horizon_str:<12} {time_str:<12} {row['mean_acc']:>10.2f}%  {row['std_acc']:>6.2f}%  {row['trades_per_day']:>10}  {verdict:<15}")

        print()
        print("Analysis:")
        print()

        # Find best horizon
        best = successful.loc[successful['mean_acc'].idxmax()]
        print(f"Best Performance: {best['horizon_bars']} bars ({best['horizon_hours']:.1f}h)")
        print(f"  Accuracy: {best['mean_acc']:.2f}% ± {best['std_acc']:.2f}%")
        print(f"  Potential: {best['trades_per_day']} trades/day per symbol")
        print()

        # Find best for day trading (balance accuracy + frequency)
        # Score = accuracy * log(trades_per_day) to favor both
        successful['day_trading_score'] = successful['mean_acc'] * np.log(successful['trades_per_day'] + 1)
        best_daytrading = successful.loc[successful['day_trading_score'].idxmax()]

        print(f"Best for Day Trading: {best_daytrading['horizon_bars']} bars ({best_daytrading['horizon_hours']:.1f}h)")
        print(f"  Accuracy: {best_daytrading['mean_acc']:.2f}% ± {best_daytrading['std_acc']:.2f}%")
        print(f"  Frequency: {best_daytrading['trades_per_day']} trades/day")
        print(f"  Score: {best_daytrading['day_trading_score']:.2f}")
        print()

        # Recommendation
        if best['mean_acc'] >= 55 and best['std_acc'] < 5:
            print("RECOMMENDATION: Proceed to Phase 7B (Screener Development)")
            print(f"  Use {best['horizon_bars']}-bar horizon for ML predictions")
            print(f"  Expected win rate: {best['mean_acc']:.1f}%")
            print(f"  Trading frequency: {best['trades_per_day']} trades/day/symbol")
            print(f"  With 10 symbols: {best['trades_per_day'] * 10} total trades/day")
        elif successful['mean_acc'].max() >= 52:
            print("RECOMMENDATION: Proceed with caution")
            print(f"  Accuracy marginal ({successful['mean_acc'].max():.1f}%) but may work with strict filtering")
            print(f"  Consider: Only trade highest confidence signals (>75%)")
        else:
            print("RECOMMENDATION: Return to research")
            print(f"  All horizons show weak performance (<52%)")
            print(f"  Consider: Different architectures (Transformer), more features, or longer timeframes")

    # Failed horizons
    failed = df[df['status'] == 'failed']
    if len(failed) > 0:
        print()
        print("Failed Horizons:")
        for _, row in failed.iterrows():
            print(f"  {row['horizon_bars']} bars: {row.get('error', 'Unknown error')}")

    # Save results
    output_file = 'short_horizon_validation_results.csv'
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
