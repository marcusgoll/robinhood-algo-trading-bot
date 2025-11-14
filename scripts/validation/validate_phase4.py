"""
Phase 4 Simple Validation - Multi-Timeframe vs Baseline

Compare baseline (5Min only) vs multi-timeframe (5Min+15Min+1Hr+4Hr) to validate
that multi-timeframe features improve prediction accuracy.

Target: Improve from 59.65% (Phase 3 winner) to 60-61%
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Import our Phase 4 feature extraction
from multi_timeframe_features import create_multi_tf_dataset, fetch_aligned_multi_timeframe, extract_multi_tf_features, extract_features_and_targets_multi_tf

# PyTorch for models
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


class AttentionLSTM(nn.Module):
    """LSTM with self-attention - Phase 3 winner architecture."""
    def __init__(self, input_dim: int = 57, hidden_dim: int = 64, num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=dropout)
        self.attention = nn.MultiheadAttention(hidden_dim, num_heads=4, dropout=dropout)
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        if x.dim() == 2:
            x = x.unsqueeze(1)
        lstm_out, _ = self.lstm(x)
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        prediction = self.fc(attn_out[:, -1, :])
        return prediction


def train_and_evaluate(X, y, model_name, epochs=30, device='cpu'):
    """Train model and return directional accuracy."""
    # Split data
    n = len(X)
    train_end = int(0.6 * n)
    val_end = int(0.8 * n)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]

    print(f"\n{model_name}")
    print(f"  Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    print(f"  Features: {X.shape[1]}")

    # Create model
    model = AttentionLSTM(input_dim=X.shape[1], hidden_dim=64, num_layers=2, dropout=0.3).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.0001)

    # Data loaders
    train_loader = DataLoader(
        TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train)),
        batch_size=32, shuffle=True
    )
    val_loader = DataLoader(
        TensorDataset(torch.FloatTensor(X_val), torch.FloatTensor(y_val)),
        batch_size=32, shuffle=False
    )

    # Training loop with early stopping
    best_val_loss = float('inf')
    patience = 5
    patience_counter = 0

    print(f"  Training... ", end="", flush=True)
    for epoch in range(epochs):
        # Train
        model.train()
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device).unsqueeze(1)
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()

        # Validate
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device).unsqueeze(1)
                outputs = model(X_batch)
                val_loss += criterion(outputs, y_batch).item()

        val_loss /= len(val_loader)

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Stopped at epoch {epoch+1}")
                break
    else:
        print(f"Completed {epochs} epochs")

    # Evaluate on test set
    model.eval()
    with torch.no_grad():
        X_tensor = torch.FloatTensor(X_test).to(device)
        predictions = model(X_tensor).cpu().numpy().flatten()

    # Metrics
    mse = mean_squared_error(y_test, predictions)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    # Directional accuracy
    y_test_direction = np.sign(y_test)
    pred_direction = np.sign(predictions)
    directional_accuracy = np.mean(y_test_direction == pred_direction) * 100

    print(f"  Directional Accuracy: {directional_accuracy:.2f}%")
    print(f"  RMSE: {rmse:.6f}, MAE: {mae:.6f}, R2: {r2:.4f}")

    return directional_accuracy, rmse, r2


def main():
    load_dotenv()
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')

    if not api_key or not api_secret:
        print("ERROR: Missing Alpaca credentials")
        return

    print("=" * 80)
    print("PHASE 4 VALIDATION: Multi-Timeframe Features")
    print("=" * 80)
    print()
    print("Goal: Improve from 59.65% (Phase 3 baseline) to 60-61%")
    print("Method: Add multi-timeframe context (5Min + 15Min + 1Hr + 4Hr)")
    print()

    # Experiment 1: Baseline (5Min only) - equivalent to Phase 3
    print("-" * 80)
    print("Experiment 1: Baseline (5Min only)")
    print("-" * 80)

    X_baseline, y_baseline, features_baseline = create_multi_tf_dataset(
        symbol='SPY',
        primary_timeframe='5Min',
        additional_timeframes=[],  # No additional timeframes
        horizon_bars=78,  # Phase 3 winner: 6.5 hours
        days=60,
        api_key=api_key,
        api_secret=api_secret
    )

    acc_baseline, rmse_baseline, r2_baseline = train_and_evaluate(
        X_baseline, y_baseline, "Baseline (5Min only)", epochs=30
    )

    # Experiment 2: Multi-Timeframe (5Min + 15Min + 1Hr + 4Hr)
    print()
    print("-" * 80)
    print("Experiment 2: Multi-Timeframe (5Min + 15Min + 1Hr + 4Hr)")
    print("-" * 80)

    X_multi, y_multi, features_multi = create_multi_tf_dataset(
        symbol='SPY',
        primary_timeframe='5Min',
        additional_timeframes=['15Min', '1Hour', '4Hour'],
        horizon_bars=78,
        days=60,
        api_key=api_key,
        api_secret=api_secret
    )

    acc_multi, rmse_multi, r2_multi = train_and_evaluate(
        X_multi, y_multi, "Multi-Timeframe (5Min+15Min+1Hr+4Hr)", epochs=30
    )

    # Summary
    print()
    print("=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print()
    print(f"Baseline (5Min only):")
    print(f"  Accuracy: {acc_baseline:.2f}%")
    print(f"  RMSE: {rmse_baseline:.6f}")
    print(f"  R2: {r2_baseline:.4f}")
    print(f"  Features: {len(features_baseline)}")
    print()
    print(f"Multi-Timeframe (5Min+15Min+1Hr+4Hr):")
    print(f"  Accuracy: {acc_multi:.2f}%")
    print(f"  RMSE: {rmse_multi:.6f}")
    print(f"  R2: {r2_multi:.4f}")
    print(f"  Features: {len(features_multi)}")
    print()
    print(f"Improvement:")
    print(f"  Accuracy: {acc_multi - acc_baseline:+.2f}%")
    print(f"  RMSE: {rmse_multi - rmse_baseline:.6f}")
    print(f"  Additional Features: +{len(features_multi) - len(features_baseline)}")
    print()

    # Verdict
    target = 60.50
    if acc_multi >= target:
        print(f"SUCCESS: Phase 4 target achieved ({target}%+)!")
    elif acc_multi >= 60.00:
        print(f"PROGRESS: Close to target ({target}%), may need Phase 4B (sentiment)")
    else:
        print(f"No significant improvement - multi-timeframe alone insufficient")

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
