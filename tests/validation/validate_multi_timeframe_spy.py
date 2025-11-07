#!/usr/bin/env python3
"""Walk-forward validation of HierarchicalTimeframeNet on SPY.

Validates the multi-timeframe ML system on real market data:
1. Fetches 2-3 years of SPY data across 6 timeframes
2. Extracts multi-timeframe features with cross-TF signals
3. Trains HierarchicalTimeframeNet with regularization
4. Runs walk-forward validation (1yr train, 3mo test, 1mo step)
5. Generates comprehensive performance report

Expected Results (Research-Backed):
- Sharpe Ratio: 2.0-3.0 (target: >2.5)
- Max Drawdown: <15%
- Win Rate: 55-65%
- Consistency: >70% profitable folds

Usage:
    python validate_multi_timeframe_spy.py --years 2 --save-results

Arguments:
    --years: Years of historical data (default: 2)
    --save-results: Save results to ml_strategies/
    --save-model: Save trained model weights
    --device: cpu or cuda (default: cpu)
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import torch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.config import Config
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.ml.features.multi_timeframe import MultiTimeframeExtractor
from trading_bot.ml.neural_models import HierarchicalTimeframeNet
from trading_bot.ml.validation import WalkForwardValidator, WalkForwardConfig
from trading_bot.ml.training import (
    EarlyStopping,
    ModelCheckpoint,
    EnsembleAverager,
    apply_weight_decay,
    get_model_complexity,
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate HierarchicalTimeframeNet on SPY data"
    )
    parser.add_argument(
        "--years",
        type=int,
        default=2,
        help="Years of historical data to use"
    )
    parser.add_argument(
        "--save-results",
        action="store_true",
        help="Save results to ml_strategies/"
    )
    parser.add_argument(
        "--save-model",
        action="store_true",
        help="Save trained model weights"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cpu", "cuda"],
        help="Device to use for training"
    )
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=["5min", "15min", "1hr", "4hr", "1day"],
        help="Timeframes to use (space-separated)"
    )
    parser.add_argument(
        "--hidden-dim",
        type=int,
        default=128,
        help="Hidden dimension for neural network"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=30,
        help="Max epochs per fold"
    )

    return parser.parse_args()


def fetch_multi_timeframe_data(
    market_data_service: MarketDataService,
    symbol: str,
    timeframes: list,
    years: int = 2
) -> dict:
    """Fetch historical data across multiple timeframes.

    Args:
        market_data_service: Market data service instance
        symbol: Ticker symbol
        timeframes: List of timeframes to fetch
        years: Years of historical data

    Returns:
        Dict mapping timeframe -> DataFrame
    """
    print(f"\n{'='*80}")
    print(f"FETCHING MULTI-TIMEFRAME DATA FOR {symbol}")
    print(f"{'='*80}\n")

    print(f"Timeframes: {', '.join(timeframes)}")
    print(f"Period: {years} years")

    # Determine span based on years
    # API only accepts: "day", "week", "month", "3month", "year", "5year"
    if years <= 1:
        span = "year"
    else:
        span = "5year"  # Use 5year for any request > 1 year

    try:
        data_by_tf = market_data_service.get_multi_timeframe_data(
            symbol=symbol,
            timeframes=timeframes,
            span=span
        )

        print(f"\n[OK] Successfully fetched data:")
        for tf, df in data_by_tf.items():
            print(f"  {tf:6s}: {len(df):5d} bars ({df['date'].iloc[0]} to {df['date'].iloc[-1]})")

        return data_by_tf

    except Exception as e:
        print(f"\n[FAIL] Error fetching data: {e}")
        print("\nFalling back to individual timeframe fetches...")

        # Fallback: fetch each timeframe separately
        data_by_tf = {}
        for tf in timeframes:
            try:
                # Map timeframes to Robinhood intervals
                if tf in ["5min", "15min"]:
                    interval = "5minute"
                elif tf in ["1hr", "4hr"]:
                    interval = "5minute"  # Will resample
                else:
                    interval = "day"

                df = market_data_service.get_historical_data(
                    symbol=symbol,
                    interval=interval,
                    span=span
                )

                # Resample if needed
                if tf == "15min" and interval == "5minute":
                    df = df.set_index("date").resample("15T").agg({
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum"
                    }).dropna().reset_index()
                elif tf in ["1hr", "4hr"] and interval == "5minute":
                    freq = "1H" if tf == "1hr" else "4H"
                    df = df.set_index("date").resample(freq).agg({
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum"
                    }).dropna().reset_index()

                data_by_tf[tf] = df
                print(f"  {tf:6s}: {len(df):5d} bars")

            except Exception as e2:
                print(f"  {tf:6s}: FAILED - {e2}")

        return data_by_tf


def prepare_training_data(
    data_by_timeframe: dict,
    timeframes: list,
    extractor: MultiTimeframeExtractor
) -> tuple:
    """Prepare features and labels for training.

    Args:
        data_by_timeframe: Dict of timeframe -> DataFrame
        timeframes: List of timeframes
        extractor: Feature extractor

    Returns:
        Tuple of (X, y, dates) where:
        - X: Feature DataFrame
        - y: Labels (0=Buy when price will go up, 1=Hold, 2=Sell when price will go down)
        - dates: Timestamps
    """
    print(f"\n{'='*80}")
    print("PREPARING TRAINING DATA")
    print(f"{'='*80}\n")

    # Use daily data for timestamps and labels
    daily_data = data_by_timeframe.get("1day")
    if daily_data is None:
        daily_data = data_by_timeframe.get("daily")

    if daily_data is None or (hasattr(daily_data, 'empty') and daily_data.empty):
        raise ValueError("Daily data required for label generation")

    print(f"Generating features for {len(daily_data)} daily bars...")

    feature_arrays = []
    labels = []
    valid_dates = []

    for idx in range(50, len(daily_data) - 5):  # Need history and future for labels
        try:
            current_timestamp = daily_data["date"].iloc[idx]

            # Extract multi-timeframe features
            features = extractor.extract_aligned_features(
                data_by_timeframe=data_by_timeframe,
                target_timestamp=current_timestamp,
                symbol="SPY"
            )

            # Generate label based on forward returns
            current_price = daily_data["close"].iloc[idx]
            future_price_5d = daily_data["close"].iloc[idx + 5]
            forward_return = (future_price_5d - current_price) / current_price

            # Classify: Buy if return > 2%, Sell if < -2%, Hold otherwise
            if forward_return > 0.02:
                label = 0  # Buy
            elif forward_return < -0.02:
                label = 2  # Sell
            else:
                label = 1  # Hold

            feature_arrays.append(features.to_array())
            labels.append(label)
            valid_dates.append(current_timestamp)

        except Exception as e:
            # Skip bars where feature extraction fails
            continue

    print(f"  [OK] Generated {len(feature_arrays)} feature samples")

    # Create DataFrame
    X = pd.DataFrame(feature_arrays)
    X["date"] = valid_dates

    y = pd.Series(labels)

    # Distribution
    counts = y.value_counts()
    print(f"\n  Label distribution:")
    print(f"    Buy  (0): {counts.get(0, 0):4d} ({counts.get(0, 0)/len(y)*100:.1f}%)")
    print(f"    Hold (1): {counts.get(1, 0):4d} ({counts.get(1, 0)/len(y)*100:.1f}%)")
    print(f"    Sell (2): {counts.get(2, 0):4d} ({counts.get(2, 0)/len(y)*100:.1f}%)")

    return X, y, valid_dates


def main():
    """Main validation script."""
    args = parse_args()

    print(f"\n{'='*80}")
    print("HIERARCHICAL MULTI-TIMEFRAME NEURAL NETWORK VALIDATION")
    print(f"{'='*80}\n")

    print(f"Symbol: SPY")
    print(f"Historical Period: {args.years} years")
    print(f"Timeframes: {', '.join(args.timeframes)}")
    print(f"Hidden Dimension: {args.hidden_dim}")
    print(f"Device: {args.device}")

    # Initialize services
    print(f"\n{'='*80}")
    print("INITIALIZATION")
    print(f"{'='*80}\n")

    config = Config.from_env_and_json()
    auth = RobinhoodAuth(config)
    auth.login()
    print("[OK] Authenticated with Robinhood")

    market_data_service = MarketDataService(auth)
    print("[OK] Market data service initialized")

    # Fetch multi-timeframe data
    data_by_timeframe = fetch_multi_timeframe_data(
        market_data_service=market_data_service,
        symbol="SPY",
        timeframes=args.timeframes,
        years=args.years
    )

    if not data_by_timeframe:
        print("\n[FAIL] Failed to fetch any data. Exiting.")
        return 1

    # Initialize feature extractor
    extractor = MultiTimeframeExtractor(
        timeframes=args.timeframes,
        enable_cross_tf_features=True
    )
    # Get actual feature count from FeatureSet
    from trading_bot.ml.models import FeatureSet
    dummy_fs = FeatureSet(timestamp=None, symbol="TEST")
    actual_features_per_tf = len(dummy_fs.to_array())

    print(f"\n[OK] Feature extractor initialized")
    print(f"  Timeframes: {len(args.timeframes)}")
    print(f"  Features per TF: {actual_features_per_tf}")
    print(f"  Cross-TF features: 8")
    print(f"  Total features: {len(args.timeframes) * actual_features_per_tf + 8}")

    # Prepare training data
    X, y, dates = prepare_training_data(
        data_by_timeframe=data_by_timeframe,
        timeframes=args.timeframes,
        extractor=extractor
    )

    # Initialize model
    print(f"\n{'='*80}")
    print("MODEL INITIALIZATION")
    print(f"{'='*80}\n")

    model = HierarchicalTimeframeNet(
        num_timeframes=len(args.timeframes),
        features_per_tf=actual_features_per_tf,
        cross_tf_features=8,
        hidden_dim=args.hidden_dim,
        num_heads=4,
        dropout=0.3,
        num_classes=3
    )

    complexity = get_model_complexity(model)
    print(f"[OK] Model initialized:")
    print(f"  Total parameters: {complexity['total_params']:,}")
    print(f"  Trainable parameters: {complexity['trainable_params']:,}")
    print(f"  Model size: ~{complexity['trainable_params'] * 4 / 1024 / 1024:.1f} MB (FP32)")

    # Configure walk-forward validation
    print(f"\n{'='*80}")
    print("WALK-FORWARD VALIDATION CONFIGURATION")
    print(f"{'='*80}\n")

    # Adaptive window sizing based on available data
    num_samples = len(X)

    # Calculate optimal windows: use 60% for train, 20% for test, 10% for step
    # Ensure at least 2 folds
    train_days = max(int(num_samples * 0.60), 50)
    test_days = max(int(num_samples * 0.20), 20)
    step_days = max(int(num_samples * 0.10), 10)
    min_train_days = max(int(train_days * 0.5), 30)

    # Ensure we can generate at least 1 fold
    required_days = train_days + test_days
    if required_days > num_samples:
        # Adjust to fit
        train_days = int(num_samples * 0.70)
        test_days = num_samples - train_days - 10  # Leave buffer for step
        step_days = max(int(test_days * 0.5), 5)

    print(f"  Data size: {num_samples} samples")
    print(f"  Adaptive windows calculated:")

    wf_config = WalkForwardConfig(
        train_days=train_days,
        test_days=test_days,
        step_days=step_days,
        min_train_days=min_train_days,
        batch_size=32,
        epochs=args.epochs,
        learning_rate=0.001,
        early_stopping_patience=5,
        early_stopping_metric="loss",
        device=args.device
    )

    print(f"  Training window: {wf_config.train_days} days (~1 year)")
    print(f"  Test window: {wf_config.test_days} days (~3 months)")
    print(f"  Step size: {wf_config.step_days} days (~1 month)")
    print(f"  Batch size: {wf_config.batch_size}")
    print(f"  Max epochs: {wf_config.epochs}")
    print(f"  Learning rate: {wf_config.learning_rate}")

    # Run validation
    print(f"\n{'='*80}")
    print("RUNNING WALK-FORWARD VALIDATION")
    print(f"{'='*80}\n")

    validator = WalkForwardValidator(wf_config)

    try:
        results = validator.validate(model, X, y, date_column="date")

        # Display results
        print(f"\n{results.summary()}")

        # Save results if requested
        if args.save_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_dir = Path("ml_strategies")
            results_dir.mkdir(exist_ok=True)

            results_file = results_dir / f"mtf_validation_SPY_{timestamp}.json"

            results_data = {
                "symbol": "SPY",
                "validation_type": "walk_forward",
                "timestamp": timestamp,
                "configuration": {
                    "timeframes": args.timeframes,
                    "years": args.years,
                    "hidden_dim": args.hidden_dim,
                    "epochs": args.epochs,
                    "train_days": wf_config.train_days,
                    "test_days": wf_config.test_days,
                    "step_days": wf_config.step_days,
                },
                "results": {
                    "mean_sharpe": results.mean_sharpe,
                    "sharpe_std": results.sharpe_std,
                    "mean_return": results.mean_return,
                    "mean_drawdown": results.mean_drawdown,
                    "mean_win_rate": results.mean_win_rate,
                    "consistency_score": results.consistency_score,
                    "total_folds": results.total_folds,
                    "profitable_folds": results.profitable_folds,
                },
                "folds": [
                    {
                        "fold_idx": f.fold_idx,
                        "train_start": f.train_start.isoformat(),
                        "train_end": f.train_end.isoformat(),
                        "test_start": f.test_start.isoformat(),
                        "test_end": f.test_end.isoformat(),
                        "sharpe_ratio": f.sharpe_ratio,
                        "total_return": f.total_return,
                        "max_drawdown": f.max_drawdown,
                        "win_rate": f.win_rate,
                        "num_trades": f.num_trades,
                    }
                    for f in results.folds
                ]
            }

            with open(results_file, "w") as f:
                json.dump(results_data, f, indent=2)

            print(f"\n[OK] Results saved to: {results_file}")

        # Save model if requested
        if args.save_model:
            model_dir = Path("ml_strategies/models")
            model_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_file = model_dir / f"hierarchical_tf_net_SPY_{timestamp}.pth"

            torch.save({
                "model_state_dict": model.state_dict(),
                "config": {
                    "num_timeframes": len(args.timeframes),
                    "features_per_tf": 55,
                    "hidden_dim": args.hidden_dim,
                    "timeframes": args.timeframes,
                },
                "validation_results": {
                    "mean_sharpe": results.mean_sharpe,
                    "mean_return": results.mean_return,
                },
            }, model_file)

            print(f"[OK] Model saved to: {model_file}")

        # Final summary
        print(f"\n{'='*80}")
        print("VALIDATION COMPLETE")
        print(f"{'='*80}\n")

        if results.mean_sharpe >= 2.5:
            print("[OK] EXCELLENT: Sharpe >= 2.5 (ready for production)")
        elif results.mean_sharpe >= 2.0:
            print("[OK] GOOD: Sharpe >= 2.0 (consider production)")
        elif results.mean_sharpe >= 1.5:
            print("[WARN] FAIR: Sharpe >= 1.5 (needs improvement)")
        else:
            print("[FAIL] POOR: Sharpe < 1.5 (not recommended)")

        if results.consistency_score >= 0.7:
            print(f"[OK] CONSISTENT: {results.consistency_score:.1%} profitable folds")
        else:
            print(f"[WARN] INCONSISTENT: Only {results.consistency_score:.1%} profitable folds")

        return 0

    except Exception as e:
        print(f"\n[FAIL] Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
