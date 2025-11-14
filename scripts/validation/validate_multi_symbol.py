"""
Multi-Symbol Validation - Confirm Phase 4 Generalizability

Test multi-timeframe approach on QQQ, NVDA, TSLA to ensure the
improvement isn't specific to SPY.

Expected: Similar improvement pattern across symbols
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Import Phase 4 components
from multi_timeframe_features import create_multi_tf_dataset
from validate_phase4 import AttentionLSTM, train_and_evaluate


def validate_symbol(symbol: str, api_key: str, api_secret: str) -> dict:
    """
    Validate both baseline and multi-TF on a single symbol.

    Returns:
        Dictionary with symbol, baseline_acc, multi_tf_acc, improvement
    """
    print(f"\n{'=' * 80}")
    print(f"SYMBOL: {symbol}")
    print(f"{'=' * 80}")

    results = {'symbol': symbol}

    try:
        # Baseline (5Min only)
        print(f"\n[{symbol}] Baseline (5Min only)...")
        X_baseline, y_baseline, features_baseline = create_multi_tf_dataset(
            symbol=symbol,
            primary_timeframe='5Min',
            additional_timeframes=[],
            horizon_bars=78,
            days=60,
            api_key=api_key,
            api_secret=api_secret
        )

        acc_baseline, rmse_baseline, r2_baseline = train_and_evaluate(
            X_baseline, y_baseline, f"{symbol} Baseline", epochs=30
        )

        results['baseline_acc'] = acc_baseline
        results['baseline_rmse'] = rmse_baseline
        results['baseline_features'] = len(features_baseline)

        # Multi-Timeframe
        print(f"\n[{symbol}] Multi-Timeframe (5Min+15Min+1Hr+4Hr)...")
        X_multi, y_multi, features_multi = create_multi_tf_dataset(
            symbol=symbol,
            primary_timeframe='5Min',
            additional_timeframes=['15Min', '1Hour', '4Hour'],
            horizon_bars=78,
            days=60,
            api_key=api_key,
            api_secret=api_secret
        )

        acc_multi, rmse_multi, r2_multi = train_and_evaluate(
            X_multi, y_multi, f"{symbol} Multi-TF", epochs=30
        )

        results['multi_tf_acc'] = acc_multi
        results['multi_tf_rmse'] = rmse_multi
        results['multi_tf_features'] = len(features_multi)
        results['improvement'] = acc_multi - acc_baseline
        results['status'] = 'success'

        print(f"\n[{symbol}] Summary:")
        print(f"  Baseline: {acc_baseline:.2f}%")
        print(f"  Multi-TF: {acc_multi:.2f}%")
        print(f"  Improvement: {acc_multi - acc_baseline:+.2f}%")

    except Exception as e:
        print(f"\n[{symbol}] ERROR: {str(e)}")
        results['status'] = 'failed'
        results['error'] = str(e)

    return results


def main():
    load_dotenv()
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')

    if not api_key or not api_secret:
        print("ERROR: Missing Alpaca credentials")
        return

    print("=" * 80)
    print("MULTI-SYMBOL VALIDATION: Phase 4 Generalizability")
    print("=" * 80)
    print()
    print("Testing multi-timeframe approach on: SPY, QQQ, NVDA, TSLA")
    print("Goal: Confirm improvement generalizes across different market instruments")
    print()

    # Test symbols
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA']
    all_results = []

    for symbol in symbols:
        result = validate_symbol(symbol, api_key, api_secret)
        all_results.append(result)

    # Summary table
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print()

    df = pd.DataFrame(all_results)

    # Filter successful runs
    successful = df[df['status'] == 'success']

    if len(successful) > 0:
        print("Successful Validations:")
        print()
        print(f"{'Symbol':<8} {'Baseline':<12} {'Multi-TF':<12} {'Improvement':<12}")
        print("-" * 44)

        for _, row in successful.iterrows():
            print(f"{row['symbol']:<8} {row['baseline_acc']:>10.2f}%  {row['multi_tf_acc']:>10.2f}%  {row['improvement']:>+10.2f}%")

        print()
        print("Statistics:")
        print(f"  Average baseline: {successful['baseline_acc'].mean():.2f}%")
        print(f"  Average multi-TF: {successful['multi_tf_acc'].mean():.2f}%")
        print(f"  Average improvement: {successful['improvement'].mean():+.2f}%")
        print(f"  Min improvement: {successful['improvement'].min():+.2f}%")
        print(f"  Max improvement: {successful['improvement'].max():+.2f}%")
        print()

        # Verdict
        if successful['improvement'].min() > 5.0:
            print("✅ STRONG GENERALIZATION: Multi-TF improves >5% across all symbols")
        elif successful['improvement'].mean() > 5.0:
            print("✅ GOOD GENERALIZATION: Average improvement >5%")
        elif successful['improvement'].mean() > 0:
            print("⚠️  WEAK GENERALIZATION: Positive but inconsistent improvement")
        else:
            print("❌ NO GENERALIZATION: Multi-TF approach doesn't generalize")

    # Failed runs
    failed = df[df['status'] == 'failed']
    if len(failed) > 0:
        print()
        print("Failed Validations:")
        for _, row in failed.iterrows():
            print(f"  {row['symbol']}: {row.get('error', 'Unknown error')}")

    # Save results
    output_file = 'multi_symbol_validation.csv'
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
