"""
Multi-Period Robustness Validation

Test baseline model across different time periods to determine if instability
is fundamental to the model or data-dependent.

Time Periods:
- 2020: COVID crash recovery (high volatility, regime change)
- 2021: Bull market (low volatility, trending up)
- 2022: Bear market (high volatility, trending down)
- 2023: Recovery (moderate volatility, trending up)
- 2024: Current conditions (recent market behavior)

Expected: If model is robust, should show consistent accuracy/stability
         If data-dependent, will show varying stability across regimes
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from validate_multi_symbol_baseline import set_seed, create_baseline_dataset, train_and_evaluate


def validate_period(
    symbol: str,
    start_date: str,
    end_date: str,
    period_name: str,
    api_key: str,
    api_secret: str,
    num_trials: int = 5
):
    """
    Validate baseline model on a specific time period.

    Args:
        symbol: Stock symbol (e.g., 'SPY')
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        period_name: Descriptive name for the period
        api_key: Alpaca API key
        api_secret: Alpaca API secret
        num_trials: Number of trials with different seeds

    Returns:
        Dictionary with statistics
    """
    print(f"\n{'=' * 80}")
    print(f"PERIOD: {period_name}")
    print(f"DATE RANGE: {start_date} to {end_date}")
    print(f"{'=' * 80}")

    try:
        # Import here to avoid circular dependency
        import alpaca_trade_api as tradeapi
        import torch
        from validate_phase4 import AttentionLSTM

        api = tradeapi.REST(api_key, api_secret, "https://paper-api.alpaca.markets", api_version='v2')

        # Fetch data for this period
        print(f"  Fetching {symbol} 5Min data...", end=" ", flush=True)
        bars = api.get_bars(
            symbol,
            '5Min',
            start=start_date,
            end=end_date,
            limit=10000
        ).df

        if bars.empty:
            raise ValueError(f"No data for {symbol} in period {period_name}")

        bars = bars.reset_index()
        bars['timestamp'] = pd.to_datetime(bars['timestamp'])

        print(f"OK ({len(bars)} bars)")

        # Calculate features (same as baseline)
        bars['returns'] = bars['close'].pct_change()
        bars['volatility'] = bars['returns'].rolling(window=20).std()
        bars['volume_ma'] = bars['volume'].rolling(window=20).mean()
        bars['volume_ratio'] = bars['volume'] / bars['volume_ma']

        # Technical indicators
        bars['sma_20'] = bars['close'].rolling(window=20).mean()
        bars['ema_12'] = bars['close'].ewm(span=12).mean()
        bars['ema_26'] = bars['close'].ewm(span=26).mean()

        # RSI
        delta = bars['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        bars['rsi'] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        bb_middle = bars['close'].rolling(window=20).mean()
        bb_std = bars['close'].rolling(window=20).std()
        bars['bb_upper'] = bb_middle + (2 * bb_std)
        bars['bb_lower'] = bb_middle - (2 * bb_std)
        bars['bb_position'] = (bars['close'] - bars['bb_lower']) / (bars['bb_upper'] - bars['bb_lower'])

        # Create target (78-bar horizon)
        horizon_bars = 78
        bars['target'] = bars['close'].pct_change(horizon_bars).shift(-horizon_bars)

        # Select features (baseline 15)
        feature_cols = ['open', 'high', 'low', 'close', 'volume', 'returns', 'volatility',
                        'volume_ratio', 'sma_20', 'ema_12', 'ema_26', 'rsi',
                        'bb_upper', 'bb_lower', 'bb_position']

        # Drop NaN
        bars = bars.dropna()

        if bars.empty or len(bars) < 200:
            raise ValueError(f"Insufficient data for {symbol} in period {period_name} (need 200+ samples, got {len(bars)})")

        X = bars[feature_cols].values
        y = bars['target'].values

        print(f"  Created {len(X)} samples with {len(feature_cols)} features")

        # Run multiple trials
        accuracies = []
        print(f"\n  Running {num_trials} trials:")

        for seed in range(num_trials):
            print(f"    Trial {seed+1}/{num_trials} (seed={seed})... ", end="", flush=True)
            acc = train_and_evaluate(X, y, f"{symbol} {period_name}", seed=seed, epochs=30)
            accuracies.append(acc)
            print(f"{acc:.2f}%")

        # Statistics
        mean_acc = np.mean(accuracies)
        std_acc = np.std(accuracies)
        min_acc = np.min(accuracies)
        max_acc = np.max(accuracies)

        # Calculate market statistics for context
        period_returns = (bars['close'].iloc[-1] - bars['close'].iloc[0]) / bars['close'].iloc[0] * 100
        avg_volatility = bars['volatility'].mean() * 100

        print(f"\n  Period Statistics:")
        print(f"    Total return: {period_returns:+.2f}%")
        print(f"    Avg volatility: {avg_volatility:.2f}%")
        print(f"    Samples: {len(X)}")

        print(f"\n  Model Performance:")
        print(f"    Mean: {mean_acc:.2f}% ± {std_acc:.2f}%")
        print(f"    Range: [{min_acc:.2f}%, {max_acc:.2f}%]")

        # Stability assessment
        if std_acc < 2.0:
            stability = 'EXCELLENT'
        elif std_acc < 5.0:
            stability = 'GOOD'
        elif std_acc < 8.0:
            stability = 'MARGINAL'
        else:
            stability = 'POOR'

        print(f"    Stability: {stability}")

        return {
            'period': period_name,
            'start_date': start_date,
            'end_date': end_date,
            'mean_acc': mean_acc,
            'std_acc': std_acc,
            'min_acc': min_acc,
            'max_acc': max_acc,
            'trials': accuracies,
            'num_samples': len(X),
            'period_return': period_returns,
            'avg_volatility': avg_volatility,
            'stability': stability,
            'status': 'success'
        }

    except Exception as e:
        print(f"\n  ERROR: {str(e)}")
        return {
            'period': period_name,
            'start_date': start_date,
            'end_date': end_date,
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
    print("MULTI-PERIOD ROBUSTNESS VALIDATION")
    print("=" * 80)
    print()
    print("Testing baseline model across different market regimes")
    print("Goal: Determine if instability is fundamental or data-dependent")
    print()

    symbol = 'SPY'
    num_trials = 5

    # Define test periods (each ~60 trading days)
    # Note: Using dates that are >30 days in past to avoid API restrictions
    periods = [
        {
            'name': '2020 COVID Recovery',
            'start': '2020-04-01',
            'end': '2020-06-30',
            'description': 'Post-crash recovery, extreme volatility, V-shaped bounce'
        },
        {
            'name': '2021 Bull Market',
            'start': '2021-03-01',
            'end': '2021-05-31',
            'description': 'Strong uptrend, low volatility, stimulus-driven'
        },
        {
            'name': '2022 Bear Market',
            'start': '2022-06-01',
            'end': '2022-08-31',
            'description': 'Downtrend, high volatility, rate hike fears'
        },
        {
            'name': '2023 Recovery',
            'start': '2023-03-01',
            'end': '2023-05-31',
            'description': 'Post-bear recovery, AI hype, banking crisis'
        },
        {
            'name': '2024 Current',
            'start': '2024-03-01',
            'end': '2024-05-31',
            'description': 'Recent conditions, ATH runs, rate uncertainty'
        }
    ]

    results = []

    for period in periods:
        print(f"\nTesting: {period['name']}")
        print(f"Context: {period['description']}")

        result = validate_period(
            symbol=symbol,
            start_date=period['start'],
            end_date=period['end'],
            period_name=period['name'],
            api_key=api_key,
            api_secret=api_secret,
            num_trials=num_trials
        )
        results.append(result)

    # Summary Analysis
    print("\n" + "=" * 80)
    print("CROSS-PERIOD ANALYSIS")
    print("=" * 80)
    print()

    df = pd.DataFrame(results)
    successful = df[df['status'] == 'success']

    if len(successful) > 0:
        print("Period Performance Summary:")
        print()
        print(f"{'Period':<22} {'Return':<10} {'Volatility':<12} {'Mean Acc':<12} {'Std':<8} {'Stability':<12}")
        print("-" * 85)

        for _, row in successful.iterrows():
            period_name = row['period'][:20]
            return_str = f"{row['period_return']:+.1f}%"
            vol_str = f"{row['avg_volatility']:.2f}%"

            print(f"{period_name:<22} {return_str:<10} {vol_str:<12} {row['mean_acc']:>10.2f}%  "
                  f"{row['std_acc']:>6.2f}%  {row['stability']:<12}")

        print()
        print("Cross-Period Statistics:")
        print(f"  Periods tested: {len(successful)}")
        print(f"  Average accuracy: {successful['mean_acc'].mean():.2f}%")
        print(f"  Accuracy range: [{successful['mean_acc'].min():.2f}%, {successful['mean_acc'].max():.2f}%]")
        print(f"  Average stability (std): {successful['std_acc'].mean():.2f}%")
        print(f"  Stability range: [{successful['std_acc'].min():.2f}%, {successful['std_acc'].max():.2f}%]")
        print()

        # Correlations
        if len(successful) >= 3:
            print("Regime Dependency Analysis:")

            # Correlation between period return and accuracy
            corr_return_acc = successful['period_return'].corr(successful['mean_acc'])
            print(f"  Period return vs accuracy: {corr_return_acc:.3f}")

            # Correlation between volatility and stability
            corr_vol_stability = successful['avg_volatility'].corr(successful['std_acc'])
            print(f"  Volatility vs instability: {corr_vol_stability:.3f}")
            print()

        # Verdict
        print("=" * 80)
        print("FINAL VERDICT")
        print("=" * 80)
        print()

        avg_acc = successful['mean_acc'].mean()
        avg_std = successful['std_acc'].mean()
        min_acc = successful['mean_acc'].min()
        max_std = successful['std_acc'].max()

        # Count how many periods are stable
        stable_periods = len(successful[successful['std_acc'] < 5.0])
        total_periods = len(successful)

        print(f"Consistency: {stable_periods}/{total_periods} periods stable (std < 5%)")
        print()

        if avg_acc >= 55.0 and avg_std < 5.0 and min_acc >= 52.0:
            print("VERDICT: MODEL IS ROBUST")
            print()
            print("  - Consistent accuracy across all market regimes")
            print("  - Low variance in most/all periods")
            print("  - Safe for production deployment")
            print()
            print("RECOMMENDATION: Proceed to Phase 7B (Screener Development)")
            print(f"  Expected win rate: {avg_acc:.1f}%")
            print(f"  Expected stability: ±{avg_std:.1f}%")

        elif avg_acc >= 55.0 and stable_periods >= (total_periods * 0.6):
            print("VERDICT: MODEL IS CONDITIONALLY ROBUST")
            print()
            print("  - Good accuracy on average")
            print(f"  - Stable in {stable_periods}/{total_periods} periods")
            print("  - Some regime dependency exists")
            print()
            print("RECOMMENDATION: Proceed with regime detection")
            print("  - Deploy only when market conditions match stable regimes")
            print("  - Monitor real-time stability metrics")
            print("  - Use ensemble or high-confidence filtering")

        elif avg_acc >= 52.0:
            print("VERDICT: MODEL IS DATA-DEPENDENT")
            print()
            print("  - Marginal accuracy")
            print(f"  - Inconsistent stability (avg std: {avg_std:.1f}%)")
            print("  - Strong regime dependency")
            print()
            print("RECOMMENDATION: Hybrid approach (Option C)")
            print("  - Use ML only for very high confidence signals (>75%)")
            print("  - Fall back to rule-based strategies")
            print("  - OR pursue Option A (fix instability with better architecture)")

        else:
            print("VERDICT: MODEL IS FUNDAMENTALLY UNSTABLE")
            print()
            print("  - Poor accuracy across all periods")
            print("  - High variance regardless of regime")
            print("  - Not suitable for production")
            print()
            print("RECOMMENDATION: Abandon ML approach (Option B)")
            print("  - Pivot to pure rule-based strategies")
            print("  - OR completely redesign architecture (Transformer, different features)")
            print("  - Current model architecture has hit quality ceiling")

        print()

        # Best/worst periods for context
        best_period = successful.loc[successful['mean_acc'].idxmax()]
        worst_period = successful.loc[successful['mean_acc'].idxmin()]

        print("Performance Context:")
        print(f"  Best period: {best_period['period']} ({best_period['mean_acc']:.2f}% ± {best_period['std_acc']:.2f}%)")
        print(f"  Worst period: {worst_period['period']} ({worst_period['mean_acc']:.2f}% ± {worst_period['std_acc']:.2f}%)")
        print(f"  Performance spread: {best_period['mean_acc'] - worst_period['mean_acc']:.2f}%")

    # Failed periods
    failed = df[df['status'] == 'failed']
    if len(failed) > 0:
        print()
        print("Failed Periods:")
        for _, row in failed.iterrows():
            print(f"  {row['period']}: {row.get('error', 'Unknown error')}")

    # Save results
    output_file = 'multi_period_robustness_results.csv'
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
