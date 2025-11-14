#!/usr/bin/env python3
"""Diagnostic script to investigate why ensemble models collapse to HOLD predictions.

Analyzes:
- Label distribution and class imbalance
- Training loss curves
- Prediction distributions over time
- Model gradients and learning dynamics
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.config import Config
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.ml.ensemble import LSTMModel
from trading_bot.ml.features.extractor import FeatureExtractor


def create_labels_with_threshold(data, buy_threshold=0.005, sell_threshold=-0.005):
    """Create labels with configurable thresholds."""
    close = data["close"].values
    returns = np.diff(close) / close[:-1]
    returns = np.append(returns, 0)

    labels = np.zeros(len(returns), dtype=np.int64)
    labels[returns > buy_threshold] = 0  # BUY
    labels[(returns >= sell_threshold) & (returns <= buy_threshold)] = 1  # HOLD
    labels[returns < sell_threshold] = 2  # SELL

    return labels, returns


def analyze_label_distribution(y, returns, name="Dataset"):
    """Analyze and visualize label distribution."""
    print(f"\n{name} Label Distribution:")
    print("-" * 80)

    class_names = ["BUY", "HOLD", "SELL"]
    for i, name in enumerate(class_names):
        count = np.sum(y == i)
        pct = count / len(y) * 100
        print(f"  {name:8s}: {count:4d} samples ({pct:5.2f}%)")

    # Return statistics
    print(f"\nReturn Statistics:")
    print(f"  Mean:   {np.mean(returns):.4f}")
    print(f"  Std:    {np.std(returns):.4f}")
    print(f"  Min:    {np.min(returns):.4f}")
    print(f"  Max:    {np.max(returns):.4f}")
    print(f"  Median: {np.median(returns):.4f}")


def train_with_diagnostics(model, X_train, y_train, X_val, y_val, epochs=30):
    """Train model with detailed diagnostics."""
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()

    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.LongTensor(y_train)
    X_val_t = torch.FloatTensor(X_val)
    y_val_t = torch.LongTensor(y_val)

    history = {
        "train_loss": [],
        "val_loss": [],
        "train_acc": [],
        "val_acc": [],
        "train_pred_dist": [],
        "val_pred_dist": [],
    }

    print("\nTraining with diagnostics...")
    print("-" * 80)

    for epoch in range(epochs):
        # Training
        model.train()
        logits = model(X_train_t)
        loss = criterion(logits, y_train_t)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        train_loss = loss.item()
        train_preds = torch.argmax(logits, dim=1)
        train_acc = (train_preds == y_train_t).float().mean().item()

        # Prediction distribution
        train_pred_dist = [
            (train_preds == 0).float().mean().item(),
            (train_preds == 1).float().mean().item(),
            (train_preds == 2).float().mean().item(),
        ]

        # Validation
        model.eval()
        with torch.no_grad():
            val_logits = model(X_val_t)
            val_loss = criterion(val_logits, y_val_t).item()
            val_preds = torch.argmax(val_logits, dim=1)
            val_acc = (val_preds == y_val_t).float().mean().item()

            val_pred_dist = [
                (val_preds == 0).float().mean().item(),
                (val_preds == 1).float().mean().item(),
                (val_preds == 2).float().mean().item(),
            ]

        # Store history
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["train_acc"].append(train_acc)
        history["val_acc"].append(val_acc)
        history["train_pred_dist"].append(train_pred_dist)
        history["val_pred_dist"].append(val_pred_dist)

        # Print every 5 epochs
        if (epoch + 1) % 5 == 0:
            print(f"Epoch {epoch+1:2d}: "
                  f"Loss={train_loss:.4f}/{val_loss:.4f} "
                  f"Acc={train_acc:.2%}/{val_acc:.2%} "
                  f"Pred=[{train_pred_dist[0]:.2f},{train_pred_dist[1]:.2f},{train_pred_dist[2]:.2f}]")

    return history


def plot_diagnostics(history, save_path="diagnostics.png"):
    """Plot training diagnostics."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Loss curves
    ax = axes[0, 0]
    ax.plot(history["train_loss"], label="Train")
    ax.plot(history["val_loss"], label="Val")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title("Training and Validation Loss")
    ax.legend()
    ax.grid(True)

    # Accuracy curves
    ax = axes[0, 1]
    ax.plot(history["train_acc"], label="Train")
    ax.plot(history["val_acc"], label="Val")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Accuracy")
    ax.set_title("Training and Validation Accuracy")
    ax.legend()
    ax.grid(True)

    # Training prediction distribution over time
    ax = axes[1, 0]
    train_dists = np.array(history["train_pred_dist"])
    ax.plot(train_dists[:, 0], label="BUY", color="green")
    ax.plot(train_dists[:, 1], label="HOLD", color="gray")
    ax.plot(train_dists[:, 2], label="SELL", color="red")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Prediction Fraction")
    ax.set_title("Training Prediction Distribution Over Time")
    ax.legend()
    ax.grid(True)

    # Validation prediction distribution over time
    ax = axes[1, 1]
    val_dists = np.array(history["val_pred_dist"])
    ax.plot(val_dists[:, 0], label="BUY", color="green")
    ax.plot(val_dists[:, 1], label="HOLD", color="gray")
    ax.plot(val_dists[:, 2], label="SELL", color="red")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Prediction Fraction")
    ax.set_title("Validation Prediction Distribution Over Time")
    ax.legend()
    ax.grid(True)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    print(f"\nDiagnostic plots saved to: {save_path}")


def main():
    """Run diagnostic analysis."""
    print("=" * 80)
    print("ENSEMBLE DIAGNOSTIC ANALYSIS")
    print("=" * 80)

    # Initialize
    print("\n[1/6] Initializing...")
    config = Config.from_env_and_json()
    auth = RobinhoodAuth(config)
    auth.login()
    market_data_service = MarketDataService(auth)
    print("[OK] Authenticated")

    # Fetch data
    print("\n[2/6] Fetching 2 years of SPY data...")
    data = market_data_service.get_historical_data(
        symbol="SPY", interval="day", span="5year"
    )
    data = data.tail(504)  # 2 years
    print(f"[OK] Fetched {len(data)} bars")

    # Extract features
    print("\n[3/6] Extracting features...")
    extractor = FeatureExtractor()
    feature_sets = extractor.extract(data, symbol="SPY")
    X = np.array([fs.to_array() for fs in feature_sets])
    print(f"[OK] Extracted {len(X)} feature sets")

    # Create labels with different thresholds
    print("\n[4/6] Testing different label thresholds...")

    thresholds_to_test = [
        (0.005, "±0.5%"),
        (0.003, "±0.3%"),
        (0.002, "±0.2%"),
        (0.001, "±0.1%"),
    ]

    for threshold, name in thresholds_to_test:
        y, returns = create_labels_with_threshold(data, threshold, -threshold)

        # Align X and y
        min_len = min(len(X), len(y))
        X_aligned = X[:min_len]
        y_aligned = y[:min_len]

        analyze_label_distribution(y_aligned, returns[:min_len], f"{name} threshold")

    # Use best threshold (±0.2%)
    print("\n[5/6] Training with ±0.2% threshold...")
    y, returns = create_labels_with_threshold(data, 0.002, -0.002)

    # Align and split
    min_len = min(len(X), len(y))
    X = X[:min_len]
    y = y[:min_len]

    n = len(X)
    train_end = int(0.6 * n)
    val_end = int(0.8 * n)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]

    print(f"\nSplits: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")

    # Train model with diagnostics
    print("\n[6/6] Training LSTM with full diagnostics...")
    model = LSTMModel(input_dim=52, hidden_dim=128, num_layers=2, dropout=0.3)
    history = train_with_diagnostics(model, X_train, y_train, X_val, y_val, epochs=30)

    # Plot diagnostics
    plot_diagnostics(history, "phase3_diagnostics.png")

    # Final evaluation
    print("\n" + "=" * 80)
    print("FINAL EVALUATION")
    print("=" * 80)

    model.eval()
    with torch.no_grad():
        test_logits = model(torch.FloatTensor(X_test))
        test_preds = torch.argmax(test_logits, dim=1).numpy()

    test_acc = np.mean(test_preds == y_test)
    print(f"\nTest Accuracy: {test_acc:.2%}")

    class_names = ["BUY", "HOLD", "SELL"]
    print("\nPer-Class Test Accuracy:")
    for i, name in enumerate(class_names):
        mask = y_test == i
        if mask.sum() > 0:
            class_acc = np.mean(test_preds[mask] == y_test[mask])
            print(f"  {name:8s}: {class_acc:.2%} ({mask.sum()} samples)")

    print("\nPrediction Distribution:")
    for i, name in enumerate(class_names):
        count = np.sum(test_preds == i)
        pct = count / len(test_preds) * 100
        print(f"  {name:8s}: {pct:5.2f}%")

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print(f"Review 'phase3_diagnostics.png' for visualizations")

    return 0


if __name__ == "__main__":
    sys.exit(main())
