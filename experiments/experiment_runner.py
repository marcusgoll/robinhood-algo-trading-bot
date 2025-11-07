#!/usr/bin/env python3
"""Parallel experiment runner for Phase 3 systematic research.

Orchestrates large-scale hyperparameter search across:
- Model architectures
- Feature sets
- Prediction horizons
- Data periods
- Training configurations

Supports multiprocessing for parallel execution and experiment caching.
"""

import argparse
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from trading_bot.ml.features.extractor import FeatureExtractor
from trading_bot.ml.models_v2 import create_model
from experiment_tracker import ExperimentTracker


def fetch_data(symbol: str, timeframe: str, days: int, api_key: str, api_secret: str) -> pd.DataFrame:
    """Fetch data from Alpaca.

    Args:
        symbol: Stock symbol
        timeframe: Timeframe string (e.g., "5Min", "1Hour")
        days: Number of days of history
        api_key: Alpaca API key
        api_secret: Alpaca API secret

    Returns:
        DataFrame with OHLCV data
    """
    client = StockHistoricalDataClient(api_key, api_secret)

    end = datetime.now()
    start = end - timedelta(days=days)

    # Parse timeframe
    timeframe_map = {
        "1Min": TimeFrame(1, TimeFrameUnit.Minute),
        "5Min": TimeFrame(5, TimeFrameUnit.Minute),
        "15Min": TimeFrame(15, TimeFrameUnit.Minute),
        "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
        "4Hour": TimeFrame(4, TimeFrameUnit.Hour),
        "1Day": TimeFrame(1, TimeFrameUnit.Day),
    }

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe_map[timeframe],
        start=start,
        end=end
    )

    bars = client.get_stock_bars(request)
    symbol_bars = bars[symbol]

    # Convert to DataFrame
    data = pd.DataFrame({
        "date": [bar.timestamp for bar in symbol_bars],
        "open": [bar.open for bar in symbol_bars],
        "high": [bar.high for bar in symbol_bars],
        "low": [bar.low for bar in symbol_bars],
        "close": [bar.close for bar in symbol_bars],
        "volume": [bar.volume for bar in symbol_bars],
    })

    return data


def create_labels(data: pd.DataFrame, horizon: int) -> np.ndarray:
    """Create regression labels for given horizon.

    Args:
        data: DataFrame with 'close' column
        horizon: Number of bars ahead to predict

    Returns:
        Array of forward returns
    """
    close = data["close"].values
    labels = np.zeros(len(close), dtype=np.float32)

    for i in range(len(close) - horizon):
        labels[i] = (close[i + horizon] - close[i]) / close[i]

    # Pad last values with 0
    labels[-horizon:] = 0

    return labels


def train_model(
    model: nn.Module,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    learning_rate: float = 0.001,
    batch_size: int = 32,
    max_epochs: int = 30,
    patience: int = 5,
    weight_decay: float = 0.01,
    device: str = "cpu"
) -> Tuple[nn.Module, int]:
    """Train regression model.

    Args:
        model: PyTorch model
        X_train, y_train: Training data
        X_val, y_val: Validation data
        learning_rate: Learning rate
        batch_size: Batch size
        max_epochs: Maximum epochs
        patience: Early stopping patience
        weight_decay: Weight decay for L2 regularization
        device: Device to train on

    Returns:
        Tuple of (trained_model, actual_epochs)
    """
    model = model.to(device)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    criterion = nn.MSELoss()

    # Convert to tensors
    X_train_t = torch.FloatTensor(X_train).to(device)
    y_train_t = torch.FloatTensor(y_train).to(device)
    X_val_t = torch.FloatTensor(X_val).to(device)
    y_val_t = torch.FloatTensor(y_val).to(device)

    best_val_loss = float("inf")
    patience_counter = 0
    actual_epochs = 0

    for epoch in range(max_epochs):
        # Training
        model.train()
        train_loss = 0.0
        num_batches = 0

        for i in range(0, len(X_train_t), batch_size):
            batch_X = X_train_t[i:i + batch_size]
            batch_y = y_train_t[i:i + batch_size]

            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            num_batches += 1

        train_loss /= num_batches

        # Validation
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val_t)
            val_loss = criterion(val_outputs, y_val_t).item()

        actual_epochs = epoch + 1

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                break

    return model, actual_epochs


def evaluate_model(
    model: nn.Module,
    X_test: np.ndarray,
    y_test: np.ndarray,
    device: str = "cpu"
) -> Dict[str, float]:
    """Evaluate regression model.

    Args:
        model: Trained model
        X_test: Test features
        y_test: Test labels
        device: Device for inference

    Returns:
        Dictionary of metrics
    """
    model.eval()
    model = model.to(device)

    X_test_t = torch.FloatTensor(X_test).to(device)

    with torch.no_grad():
        pred = model(X_test_t).cpu().numpy()

    # Regression metrics
    mse = np.mean((pred - y_test) ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(pred - y_test))

    # R² score
    ss_res = np.sum((y_test - pred) ** 2)
    ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # Directional accuracy
    pred_direction = np.sign(pred)
    true_direction = np.sign(y_test)
    direction_acc = np.mean(pred_direction == true_direction)

    return {
        "mse": float(mse),
        "rmse": float(rmse),
        "mae": float(mae),
        "r2": float(r2),
        "directional_accuracy": float(direction_acc)
    }


def run_single_experiment(config: Dict[str, Any], db_path: str = "experiments.db") -> Dict[str, Any]:
    """Run a single experiment.

    Args:
        config: Experiment configuration
        db_path: Path to experiment database

    Returns:
        Results dictionary
    """
    # Create tracker in this process (can't pickle SQLite connections)
    tracker = ExperimentTracker(db_path)

    # Check if experiment already completed
    existing = tracker.get_experiment_by_config(config)
    if existing:
        print(f"  [CACHED] {config['model_name']} @ {config['horizon_name']} ({config['data_period']})")
        tracker.close()
        return existing

    # Start experiment
    exp_id = tracker.start_experiment(config)
    print(f"  [START] {exp_id}: {config['model_name']} @ {config['horizon_name']} ({config['data_period']})")

    try:
        # Get API keys
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_SECRET_KEY")

        if not api_key or not api_secret:
            raise ValueError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set")

        # Fetch data
        data = fetch_data(
            config["symbol"],
            config["timeframe"],
            config["days"],
            api_key,
            api_secret
        )

        # Extract features
        extractor = FeatureExtractor()
        feature_sets = extractor.extract(data, symbol=config["symbol"])
        X = np.array([fs.to_array() for fs in feature_sets])

        # Create labels
        y = create_labels(data, config["horizon_bars"])

        # Align X and y
        min_len = min(len(X), len(y))
        X = X[:min_len]
        y = y[:min_len]

        # Split data
        n = len(X)
        train_end = int(0.6 * n)
        val_end = int(0.8 * n)

        X_train, y_train = X[:train_end], y[:train_end]
        X_val, y_val = X[train_end:val_end], y[train_end:val_end]
        X_test, y_test = X[val_end:], y[val_end:]

        # Update config with actual input dim
        model_params = config["model_params"].copy()
        model_params["input_dim"] = X.shape[1]

        # Create model
        model_config = {
            "type": config["model_type"],
            "params": model_params
        }
        model = create_model(model_config)

        # Train model
        model, actual_epochs = train_model(
            model,
            X_train, y_train,
            X_val, y_val,
            learning_rate=config["learning_rate"],
            batch_size=config["batch_size"],
            max_epochs=config["max_epochs"],
            patience=config.get("patience", 5),
            weight_decay=config["weight_decay"],
            device=config.get("device", "cpu")
        )

        # Evaluate model
        metrics = evaluate_model(model, X_test, y_test, config.get("device", "cpu"))

        # Prepare results
        results = {
            "num_samples": len(X),
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "test_samples": len(X_test),
            "num_features": X.shape[1],
            "actual_epochs": actual_epochs,
            **metrics
        }

        # Complete experiment
        tracker.complete_experiment(exp_id, results, status="completed")

        print(f"  [DONE] {exp_id}: Acc={metrics['directional_accuracy']:.2%}, "
              f"RMSE={metrics['rmse']:.4f}, R²={metrics['r2']:.4f}")

        tracker.close()
        return results

    except Exception as e:
        # Record failure
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        tracker.complete_experiment(
            exp_id,
            {"error_message": error_msg},
            status="failed"
        )
        print(f"  [FAIL] {exp_id}: {str(e)}")
        tracker.close()
        return {"status": "failed", "error": str(e)}


def generate_experiment_configs(yaml_config: Dict) -> List[Dict[str, Any]]:
    """Generate all experiment configurations from YAML.

    Args:
        yaml_config: Loaded YAML configuration

    Returns:
        List of experiment configurations
    """
    configs = []

    # Get all enabled configurations
    symbols = yaml_config["data"]["symbols"]
    periods = [p for p in yaml_config["data"]["periods"] if p.get("priority", 3) <= 2]  # Priority 1 or 2
    timeframes = [tf for tf in yaml_config["data"]["timeframes"] if tf.get("enabled", False)]
    horizons = [h for h in yaml_config["horizons"] if h.get("enabled", False)]
    models = [m for m in yaml_config["models"] if m.get("enabled", False)]

    # Training configs
    batch_sizes = yaml_config["training"]["batch_size"]
    learning_rates = yaml_config["training"]["learning_rate"]
    weight_decays = yaml_config["training"]["weight_decay"]

    # Generate configs (start with baseline: 1yr + 5min + base features)
    for symbol in symbols:
        for period in periods:
            for horizon in horizons:
                for model in models:
                    for batch_size in batch_sizes:
                        for lr in learning_rates:
                            for wd in weight_decays:
                                config = {
                                    # Data
                                    "symbol": symbol,
                                    "data_period": period["name"],
                                    "days": period["days"],
                                    "timeframe": timeframes[0]["alpaca"],  # Start with 5min

                                    # Model
                                    "model_name": model["name"],
                                    "model_type": model["type"],
                                    "model_params": model["params"].copy(),

                                    # Features
                                    "feature_set": "base",  # Start with base features

                                    # Horizon
                                    "horizon_bars": horizon["bars"],
                                    "horizon_name": horizon["name"],

                                    # Training
                                    "batch_size": batch_size,
                                    "learning_rate": lr,
                                    "max_epochs": yaml_config["training"]["max_epochs"],
                                    "patience": yaml_config["training"].get("patience", 5),
                                    "weight_decay": wd,

                                    # Validation
                                    "validation_method": "holdout",

                                    # Execution
                                    "device": yaml_config["execution"]["device"],
                                }
                                configs.append(config)

    return configs


def run_experiments_parallel(
    configs: List[Dict[str, Any]],
    max_workers: int = 4,
    db_path: str = "experiments.db"
) -> List[Dict[str, Any]]:
    """Run experiments in parallel.

    Args:
        configs: List of experiment configurations
        max_workers: Number of parallel workers
        db_path: Path to experiment database

    Returns:
        List of results
    """
    print(f"\n{'=' * 80}")
    print(f"RUNNING {len(configs)} EXPERIMENTS WITH {max_workers} PARALLEL WORKERS")
    print(f"{'=' * 80}\n")

    results = []
    start_time = time.time()

    # Run in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all experiments
        future_to_config = {
            executor.submit(run_single_experiment, config, db_path): config
            for config in configs
        }

        # Process completed experiments
        for i, future in enumerate(as_completed(future_to_config), 1):
            config = future_to_config[future]
            try:
                result = future.result()
                results.append(result)

                # Progress update
                elapsed = time.time() - start_time
                rate = i / elapsed
                eta = (len(configs) - i) / rate if rate > 0 else 0

                print(f"Progress: {i}/{len(configs)} ({i/len(configs)*100:.1f}%) | "
                      f"Rate: {rate:.2f} exp/s | ETA: {eta/60:.1f}min")

            except Exception as e:
                print(f"Experiment failed: {e}")
                results.append({"status": "failed", "error": str(e)})

    total_time = time.time() - start_time
    print(f"\n{'=' * 80}")
    print(f"COMPLETED {len(results)} EXPERIMENTS IN {total_time/60:.1f} MINUTES")
    print(f"{'=' * 80}\n")

    return results


def main():
    """Main experiment runner."""
    parser = argparse.ArgumentParser(description="Run Phase 3 systematic experiments")
    parser.add_argument(
        "--config",
        type=str,
        default="experiment_config.yaml",
        help="Path to experiment configuration YAML"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Number of parallel workers"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="experiments.db",
        help="Path to experiment database"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of experiments (for testing)"
    )
    args = parser.parse_args()

    # Load configuration
    print(f"Loading configuration from {args.config}...")
    with open(args.config, "r") as f:
        yaml_config = yaml.safe_load(f)

    # Generate experiment configurations
    configs = generate_experiment_configs(yaml_config)

    if args.limit:
        configs = configs[:args.limit]

    print(f"Generated {len(configs)} experiment configurations")

    # Initialize tracker
    tracker = ExperimentTracker(args.db)

    # Run experiments
    results = run_experiments_parallel(configs, args.max_workers, args.db)

    # Print summary
    stats = tracker.get_statistics()
    print("\n" + "=" * 80)
    print("EXPERIMENT SUMMARY")
    print("=" * 80)
    print(f"Total experiments: {stats['total_experiments']}")
    print(f"Completed: {stats['completed']}")
    print(f"Failed: {stats['failed']}")
    print(f"Running: {stats['running']}")

    if stats['best_accuracy'] is not None:
        print(f"\nBest directional accuracy: {stats['best_accuracy']:.2%}")
        print(f"Best experiment ID: {stats['best_experiment_id']}")
    if stats['avg_accuracy'] is not None:
        print(f"Average accuracy: {stats['avg_accuracy']:.2%}")

    # Show leaderboard
    print("\n" + "=" * 80)
    print("TOP 10 EXPERIMENTS")
    print("=" * 80)
    leaderboard = tracker.get_leaderboard(limit=10)
    print(leaderboard.to_string())

    # Export results
    tracker.export_to_csv("experiment_results.csv")
    print(f"\nResults exported to experiment_results.csv")

    tracker.close()


if __name__ == "__main__":
    main()
