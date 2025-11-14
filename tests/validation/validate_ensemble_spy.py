#!/usr/bin/env python3
"""Validation script for Phase 3 hierarchical stacking ensemble.

Tests the complete ensemble system (LSTM + GRU + Transformer + XGBoost meta-learner)
on SPY historical data using the enhanced 52-feature extraction pipeline.

Usage:
    python validate_ensemble_spy.py [--years 1] [--epochs 20] [--device cpu]
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.config import Config
from trading_bot.market_data.market_data_service import MarketDataService
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


def create_labels(data):
    """Create labels from price data using 2-DAY prediction horizon.

    Labels based on 2-day cumulative return (reduces noise vs next-day):
    - 0 (BUY): 2-day return > 0.5%
    - 1 (HOLD): 2-day return between -0.5% and 0.5%
    - 2 (SELL): 2-day return < -0.5%

    Args:
        data: DataFrame with 'close' column

    Returns:
        Array of labels
    """
    close = data["close"].values

    # Calculate 2-day forward returns instead of next-day
    # This smooths out daily noise and improves signal-to-noise ratio
    returns_2day = np.zeros(len(close))
    for i in range(len(close) - 2):
        returns_2day[i] = (close[i + 2] - close[i]) / close[i]

    # Pad last 2 values
    returns_2day[-2:] = 0

    labels = np.zeros(len(returns_2day), dtype=np.int64)
    labels[returns_2day > 0.005] = 0  # BUY (>0.5% in 2 days)
    labels[(returns_2day >= -0.005) & (returns_2day <= 0.005)] = 1  # HOLD
    labels[returns_2day < -0.005] = 2  # SELL (<-0.5% in 2 days)

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
    """Run validation on SPY data."""
    parser = argparse.ArgumentParser(description="Validate Phase 3 ensemble on SPY")
    parser.add_argument(
        "--years", type=int, default=1, help="Years of historical data (default: 1)"
    )
    parser.add_argument(
        "--epochs", type=int, default=20, help="Training epochs per model (default: 20)"
    )
    parser.add_argument(
        "--device", type=str, default="cpu", help="Device for training (default: cpu)"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("PHASE 3: HIERARCHICAL STACKING ENSEMBLE VALIDATION")
    print("=" * 80)
    print()

    # Initialize
    print("[1/7] Initializing...")
    config = Config.from_env_and_json()
    auth = RobinhoodAuth(config)
    auth.login()
    market_data_service = MarketDataService(auth)
    print("[OK] Authenticated")

    # Fetch data
    print(f"\n[2/7] Fetching {args.years} year(s) of SPY data...")
    span_map = {1: "year", 2: "5year", 3: "5year"}
    span = span_map.get(args.years, "5year")

    data = market_data_service.get_historical_data(
        symbol="SPY", interval="day", span=span
    )

    if args.years > 1:
        # Limit to requested years
        data = data.tail(252 * args.years)

    print(f"[OK] Fetched {len(data)} bars")
    print(f"  Date range: {data['date'].iloc[0]} to {data['date'].iloc[-1]}")

    # Extract features
    print("\n[3/7] Extracting 52-dimensional features (with S/R)...")
    extractor = FeatureExtractor()
    feature_sets = extractor.extract(data, symbol="SPY")
    print(f"[OK] Extracted {len(feature_sets)} feature sets")

    # Prepare data
    print("\n[4/7] Preparing train/val/test splits...")
    X = np.array([fs.to_array() for fs in feature_sets])
    y = create_labels(data)

    # Align X and y (feature extraction starts at different point)
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

    # Create base models (REDUCED SIZE for limited data: 150 samples)
    # Changed: hidden_dim 128→32, num_layers 2→1, dropout 0.3→0.5
    # This reduces params from 400K-600K to ~10K-20K (10-100x samples:params ratio)
    print("\n[5/7] Creating ensemble components...")
    base_models = [
        LSTMModel(input_dim=52, hidden_dim=32, num_layers=1, dropout=0.5),
        GRUModel(input_dim=52, hidden_dim=32, num_layers=1, dropout=0.5),
        TransformerModel(
            input_dim=52, d_model=32, nhead=4, num_layers=1, dropout=0.5
        ),
    ]

    meta_learner = MetaLearner(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
    )

    print(f"[OK] Created {len(base_models)} base models (COMPACT: ~10K params) + meta-learner")

    # Train ensemble
    print(f"\n[6/7] Training ensemble (max {args.epochs} epochs per model)...")
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
        print(f"[OK] Ensemble accuracy {ensemble_acc:.2%} meets target {target_acc:.2%}")

    # Check if ensemble beats all individual models
    all_better = all(
        ensemble_acc > m["accuracy"] for m in individual_metrics
    )
    if all_better:
        print("[OK] Ensemble outperforms all individual base models")
    else:
        print("[WARNING] Ensemble does not beat all base models")
        success = False

    print()
    if success:
        print("Phase 3 validation: SUCCESS")
        return 0
    else:
        print("Phase 3 validation: NEEDS IMPROVEMENT")
        return 1


if __name__ == "__main__":
    sys.exit(main())
