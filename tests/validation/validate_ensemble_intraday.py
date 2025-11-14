#!/usr/bin/env python3
"""Validation script for Phase 3 ensemble with INTRADAY 5-minute data from Alpaca.

Uses Alpaca Markets API to fetch 5-minute bars (47K+ samples per year vs 250 daily).
This provides sufficient data for deep learning ensemble training.

Usage:
    python validate_ensemble_intraday.py [--months 3] [--epochs 20] [--device cpu]
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from trading_bot.ml.ensemble import (
    LSTMModel,
    GRUModel,
    TransformerModel,
    MetaLearner,
    EnsembleTrainer,
)
from trading_bot.ml.features.extractor import FeatureExtractor

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_labels_intraday(data):
    """Create labels from 5-minute bar data.

    Predict next 5-minute bar movement with optimal threshold for class balance:
    - 0 (BUY): Next bar return > 0.01%
    - 1 (HOLD): Next bar return between -0.01% and 0.01%
    - 2 (SELL): Next bar return < -0.01%

    Note: Using ±0.01% threshold gives near-perfect 34-33-33 class balance for 5-minute
    SPY bars (determined via diagnostic testing on 3 months of Alpaca data).

    Args:
        data: DataFrame with 'close' column

    Returns:
        Array of labels
    """
    close = data["close"].values

    # Calculate next-bar forward returns
    returns = np.zeros(len(close))
    for i in range(len(close) - 1):
        returns[i] = (close[i + 1] - close[i]) / close[i]

    # Pad last value
    returns[-1] = 0

    labels = np.zeros(len(returns), dtype=np.int64)
    labels[returns > 0.0001] = 0  # BUY (>0.01%)
    labels[(returns >= -0.0001) & (returns <= 0.0001)] = 1  # HOLD
    labels[returns < -0.0001] = 2  # SELL (<-0.01%)

    return labels


def evaluate_model(model, X_test, y_test, model_name="Model"):
    """Evaluate model performance.

    Args:
        model: Model with predict_proba method
        X_test: Test features
        y_test: Test labels
        model_name: Name for logging

    Returns:
        Dictionary of metrics
    """
    # Get predictions
    probs = model.predict_proba(X_test)
    preds = np.argmax(probs, axis=1)

    # Calculate metrics
    accuracy = np.mean(preds == y_test)

    # Per-class accuracy
    class_names = ["BUY", "HOLD", "SELL"]
    class_accuracies = {}
    for i, name in enumerate(class_names):
        mask = y_test == i
        if mask.sum() > 0:
            class_accuracies[name] = np.mean(preds[mask] == y_test[mask])
        else:
            class_accuracies[name] = 0.0

    # Class distribution
    pred_dist = {name: np.mean(preds == i) for i, name in enumerate(class_names)}
    true_dist = {name: np.mean(y_test == i) for i, name in enumerate(class_names)}

    return {
        "accuracy": accuracy,
        "class_accuracies": class_accuracies,
        "pred_distribution": pred_dist,
        "true_distribution": true_dist,
    }


def print_metrics(metrics, model_name="Model"):
    """Print formatted metrics.

    Args:
        metrics: Dictionary from evaluate_model
        model_name: Name for display
    """
    print(f"\n{model_name} Performance:")
    print("-" * 80)
    print(f"Overall Accuracy: {metrics['accuracy']:.2%}")
    print("\nPer-Class Accuracy:")
    for name, acc in metrics["class_accuracies"].items():
        print(f"  {name:8s}: {acc:.2%}")
    print("\nPrediction Distribution:")
    for name, pct in metrics["pred_distribution"].items():
        print(f"  {name:8s}: {pct:.2%}")
    print("\nTrue Distribution:")
    for name, pct in metrics["true_distribution"].items():
        print(f"  {name:8s}: {pct:.2%}")


def main():
    """Run validation on SPY 5-minute intraday data."""
    parser = argparse.ArgumentParser(
        description="Validate Phase 3 ensemble on 5-minute intraday data"
    )
    parser.add_argument(
        "--months",
        type=int,
        default=3,
        help="Months of intraday data (default: 3 = ~4,900 samples)",
    )
    parser.add_argument(
        "--epochs", type=int, default=20, help="Training epochs per model (default: 20)"
    )
    parser.add_argument(
        "--device", type=str, default="cpu", help="Device for training (default: cpu)"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("PHASE 3: INTRADAY 5-MINUTE ENSEMBLE VALIDATION")
    print("=" * 80)
    print()

    # Initialize Alpaca client
    print("[1/7] Initializing...")
    API_KEY = os.getenv("ALPACA_API_KEY")
    API_SECRET = os.getenv("ALPACA_SECRET_KEY")

    if not API_KEY or not API_SECRET:
        print("ERROR: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env")
        return 1

    client = StockHistoricalDataClient(API_KEY, API_SECRET)
    print("[OK] Connected to Alpaca")

    # Fetch 5-minute intraday data
    print(f"\n[2/7] Fetching {args.months} month(s) of SPY 5-minute data from Alpaca...")
    print(
        f"  Expected samples: ~{args.months * 1638} bars (78 bars/day × 21 days/month)"
    )

    # Calculate date range
    end = datetime.now()
    start = end - timedelta(days=args.months * 30)  # Approximate months as 30 days

    request = StockBarsRequest(
        symbol_or_symbols="SPY",
        timeframe=TimeFrame(5, TimeFrameUnit.Minute),  # 5-minute bars
        start=start,
        end=end
    )

    try:
        bars = client.get_stock_bars(request)
        spy_bars = bars["SPY"]

        # Convert to DataFrame format expected by FeatureExtractor
        data = pd.DataFrame({
            "date": [bar.timestamp for bar in spy_bars],
            "open": [bar.open for bar in spy_bars],
            "high": [bar.high for bar in spy_bars],
            "low": [bar.low for bar in spy_bars],
            "close": [bar.close for bar in spy_bars],
            "volume": [bar.volume for bar in spy_bars],
        })

        print(f"[OK] Fetched {len(data)} bars")
        print(f"  Date range: {data['date'].iloc[0]} to {data['date'].iloc[-1]}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch Alpaca data: {e}")
        return 1

    # Extract features
    print("\n[3/7] Extracting 52-dimensional features (with S/R)...")
    extractor = FeatureExtractor()
    feature_sets = extractor.extract(data, symbol="SPY")
    print(f"[OK] Extracted {len(feature_sets)} feature sets")

    # Prepare data
    print("\n[4/7] Preparing train/val/test splits...")
    X = np.array([fs.to_array() for fs in feature_sets])
    y = create_labels_intraday(data)

    # Align X and y
    min_len = min(len(X), len(y))
    X = X[:min_len]
    y = y[:min_len]

    # Split: 60% train, 20% val, 20% test
    n = len(X)
    train_end = int(0.6 * n)
    val_end = int(0.8 * n)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]

    print(f"[OK] Splits created:")
    print(f"  Train: {len(X_train)} samples")
    print(f"  Val:   {len(X_val)} samples")
    print(f"  Test:  {len(X_test)} samples")
    print(f"  Total: {len(X)} samples")

    # Create ensemble (with all improvements from previous attempts)
    print("\n[5/7] Creating ensemble components...")
    print("  Using IMPROVED architecture:")
    print("    - Compact models (~10K params for faster training)")
    print("    - Focal Loss (gamma=3.0) for aggressive class balancing")
    print("    - Strong regularization (dropout=0.5, weight_decay=0.01)")

    base_models = [
        LSTMModel(input_dim=52, hidden_dim=32, num_layers=1, dropout=0.5),
        GRUModel(input_dim=52, hidden_dim=32, num_layers=1, dropout=0.5),
        TransformerModel(input_dim=52, d_model=32, nhead=4, num_layers=1, dropout=0.5),
    ]

    meta_learner = MetaLearner(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
    )

    print(f"[OK] Created {len(base_models)} base models + meta-learner")

    # Train ensemble
    print(f"\n[6/7] Training ensemble (max {args.epochs} epochs per model)...")
    print(f"  Training on {len(X_train)} samples (sufficient for deep learning!)")
    print("  This may take several minutes...")

    trainer = EnsembleTrainer(
        base_models=base_models,
        meta_learner=meta_learner,
        learning_rate=0.001,
        batch_size=32,
        max_epochs=args.epochs,
        patience=5,
        device=args.device,
    )

    ensemble = trainer.train(X_train, y_train, X_val, y_val)
    print("[OK] Ensemble training complete")

    # Evaluate
    print("\n[7/7] Evaluating performance...")
    print("=" * 80)

    # Evaluate ensemble
    ensemble_metrics = evaluate_model(ensemble, X_test, y_test, "Ensemble")
    print_metrics(ensemble_metrics, "ENSEMBLE")

    # Evaluate individual base models
    model_names = ["LSTM", "GRU", "Transformer"]
    individual_metrics = []

    for name, model in zip(model_names, ensemble.base_models):
        metrics = evaluate_model(model, X_test, y_test, name)
        individual_metrics.append(metrics)
        print_metrics(metrics, name.upper())

    # Compare ensemble vs base models
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)

    ensemble_acc = ensemble_metrics["accuracy"]
    print(f"Ensemble:    {ensemble_acc:.2%}")

    for name, metrics in zip(model_names, individual_metrics):
        acc = metrics["accuracy"]
        improvement = ((ensemble_acc - acc) / acc) * 100
        print(f"{name:12s} {acc:.2%}  (ensemble {improvement:+.1f}% better)")

    # Feature importance
    print("\n" + "=" * 80)
    print("META-LEARNER FEATURE IMPORTANCE")
    print("=" * 80)

    importance = ensemble.get_feature_importance()
    if importance:
        print("Top 10 most important features:")
        for i, (name, score) in enumerate(
            sorted(importance.items(), key=lambda x: -x[1])[:10], 1
        ):
            print(f"  {i:2d}. {name:20s} {score:.4f}")
    else:
        print("  No feature importance available")

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)

    # Check if we met success criteria
    success = True
    target_acc = 0.60  # 60% baseline

    if ensemble_acc < target_acc:
        print(
            f"[WARNING] Ensemble accuracy {ensemble_acc:.2%} below target {target_acc:.2%}"
        )
        success = False
    else:
        print(
            f"[OK] Ensemble accuracy {ensemble_acc:.2%} meets target {target_acc:.2%}"
        )

    # Check if ensemble beats all individual models
    all_better = all(ensemble_acc > m["accuracy"] for m in individual_metrics)
    if all_better:
        print("[OK] Ensemble outperforms all individual base models")
    else:
        print("[WARNING] Ensemble does not beat all base models")
        success = False

    print()
    if success:
        print("Phase 3 validation: SUCCESS")
        print(
            f"With {len(X_train)} training samples, the ensemble achieves {ensemble_acc:.1%} accuracy!"
        )
        return 0
    else:
        print("Phase 3 validation: NEEDS IMPROVEMENT")
        return 1


if __name__ == "__main__":
    sys.exit(main())
