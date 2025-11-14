"""
Phase 4 Robust Validation - Multiple Runs with Fixed Seeds

Address the variance issue by running multiple trials with different
random seeds and reporting mean +/- std statistics.

This is the CORRECT way to evaluate ML model architectures.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import torch

# Import Phase 4 components
from multi_timeframe_features import create_multi_tf_dataset
from validate_phase4 import AttentionLSTM, train_and_evaluate


def set_seed(seed: int):
    """Set random seeds for reproducibility."""
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def validate_with_multiple_seeds(
    symbol: str,
    use_multi_tf: bool,
    api_key: str,
    api_secret: str,
    num_runs: int = 5
) -> dict:
    """
    Run validation multiple times with different seeds.

    Returns:
        Dictionary with mean, std, min, max for directional accuracy
    """
    config_name = "Multi-TF" if use_multi_tf else "Baseline"
    print(f"\n[{symbol} {config_name}] Running {num_runs} trials...")

    accuracies = []
    rmses = []

    # Fetch data once (outside seed loop)
    if use_multi_tf:
        X, y, features = create_multi_tf_dataset(
            symbol=symbol,
            primary_timeframe='5Min',
            additional_timeframes=['15Min', '1Hour', '4Hour'],
            horizon_bars=78,
            days=60,
            api_key=api_key,
            api_secret=api_secret
        )
    else:
        X, y, features = create_multi_tf_dataset(
            symbol=symbol,
            primary_timeframe='5Min',
            additional_timeframes=[],
            horizon_bars=78,
            days=60,
            api_key=api_key,
            api_secret=api_secret
        )

    # Run multiple trials with different seeds
    for seed in range(num_runs):
        set_seed(seed)

        print(f"  Trial {seed+1}/{num_runs}... ", end="", flush=True)

        acc, rmse, r2 = train_and_evaluate(
            X, y, f"{symbol} {config_name} (seed={seed})", epochs=30
        )

        accuracies.append(acc)
        rmses.append(rmse)

        print(f"{acc:.2f}%")

    return {
        'symbol': symbol,
        'config': config_name,
        'num_features': len(features),
        'mean_acc': np.mean(accuracies),
        'std_acc': np.std(accuracies),
        'min_acc': np.min(accuracies),
        'max_acc': np.max(accuracies),
        'mean_rmse': np.mean(rmses),
        'std_rmse': np.std(rmses),
        'all_accs': accuracies
    }


def main():
    load_dotenv()
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')

    if not api_key or not api_secret:
        print("ERROR: Missing Alpaca credentials")
        return

    print("=" * 80)
    print("PHASE 4 ROBUST VALIDATION: Statistical Significance Testing")
    print("=" * 80)
    print()
    print("Method: Run each configuration 5x with different random seeds")
    print("Report: Mean +/- Std directional accuracy")
    print("Goal: Determine if multi-TF improvement is statistically significant")
    print()

    # Test on SPY only (to save time, can expand later)
    symbols = ['SPY']
    num_runs = 5

    results = []

    for symbol in symbols:
        print(f"\n{'=' * 80}")
        print(f"SYMBOL: {symbol}")
        print(f"{'=' * 80}")

        # Baseline
        baseline_result = validate_with_multiple_seeds(
            symbol=symbol,
            use_multi_tf=False,
            api_key=api_key,
            api_secret=api_secret,
            num_runs=num_runs
        )
        results.append(baseline_result)

        # Multi-TF
        multi_tf_result = validate_with_multiple_seeds(
            symbol=symbol,
            use_multi_tf=True,
            api_key=api_key,
            api_secret=api_secret,
            num_runs=num_runs
        )
        results.append(multi_tf_result)

        # Statistical comparison
        print(f"\n{'-' * 80}")
        print(f"STATISTICAL SUMMARY: {symbol}")
        print(f"{'-' * 80}")
        print()
        print(f"Baseline ({baseline_result['num_features']} features):")
        print(f"  Mean accuracy: {baseline_result['mean_acc']:.2f}% +/- {baseline_result['std_acc']:.2f}%")
        print(f"  Range: [{baseline_result['min_acc']:.2f}%, {baseline_result['max_acc']:.2f}%]")
        print(f"  Trials: {baseline_result['all_accs']}")
        print()
        print(f"Multi-TF ({multi_tf_result['num_features']} features):")
        print(f"  Mean accuracy: {multi_tf_result['mean_acc']:.2f}% +/- {multi_tf_result['std_acc']:.2f}%")
        print(f"  Range: [{multi_tf_result['min_acc']:.2f}%, {multi_tf_result['max_acc']:.2f}%]")
        print(f"  Trials: {multi_tf_result['all_accs']}")
        print()

        # Calculate improvement
        mean_improvement = multi_tf_result['mean_acc'] - baseline_result['mean_acc']
        pooled_std = np.sqrt((baseline_result['std_acc']**2 + multi_tf_result['std_acc']**2) / 2)

        print(f"Improvement:")
        print(f"  Mean: {mean_improvement:+.2f}%")
        print(f"  Pooled Std: {pooled_std:.2f}%")
        print()

        # Simple significance test (is improvement > 2*pooled_std?)
        if abs(mean_improvement) > 2 * pooled_std:
            if mean_improvement > 0:
                print(f"✓ SIGNIFICANT IMPROVEMENT (>2 std deviations)")
            else:
                print(f"✗ SIGNIFICANT DEGRADATION (>2 std deviations)")
        else:
            print(f"⚠ NOT STATISTICALLY SIGNIFICANT (within 2 std deviations)")
            print(f"  Likely due to random initialization variance")

    # Save results
    df = pd.DataFrame(results)
    output_file = 'phase4_robust_validation.csv'
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
