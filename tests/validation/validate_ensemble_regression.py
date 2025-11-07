#!/usr/bin/env python3
"""Phase 3 ensemble with REGRESSION + longer horizon + cumulative returns + microstructure.

Key improvements:
1. Regression task: Predict 60-minute cumulative return magnitude (continuous)
2. Longer prediction horizon: 60 minutes (12 bars) instead of next bar
3. Cumulative returns: Reduces noise vs single-bar movements
4. Microstructure features: Volume profile, intrabar volatility, momentum

Usage:
    python validate_ensemble_regression.py [--months 12] [--epochs 20] [--device cpu]
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from trading_bot.ml.features.extractor import FeatureExtractor

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def add_microstructure_features(data):
    """Add microstructure features to intraday bar data.

    Features added:
    - intrabar_volatility: (high - low) / close
    - volume_imbalance: Volume deviation from recent average
    - price_momentum: Recent price change momentum
    - volume_weighted_price: (high + low + close) / 3 weighted by volume

    Args:
        data: DataFrame with OHLCV columns

    Returns:
        DataFrame with additional microstructure columns
    """
    df = data.copy()

    # Intrabar volatility (range / close)
    df['intrabar_volatility'] = (df['high'] - df['low']) / df['close']

    # Volume imbalance (vs 20-bar moving average)
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    df['volume_imbalance'] = (df['volume'] - df['volume_ma20']) / (df['volume_ma20'] + 1e-8)

    # Price momentum (5-bar and 10-bar)
    df['momentum_5'] = df['close'].pct_change(5)
    df['momentum_10'] = df['close'].pct_change(10)

    # Volume-weighted typical price
    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
    df['vwap_20'] = (df['typical_price'] * df['volume']).rolling(20).sum() / df['volume'].rolling(20).sum()
    df['price_vs_vwap'] = (df['close'] - df['vwap_20']) / (df['vwap_20'] + 1e-8)

    # Fill NaN with 0
    df = df.fillna(0)

    return df


def create_regression_labels(data, horizon=12):
    """Create regression labels: predict N-bar cumulative return.

    Args:
        data: DataFrame with 'close' column
        horizon: Number of bars to look ahead (default: 12 = 60 minutes)

    Returns:
        Array of cumulative returns (continuous values, not classes)
    """
    close = data["close"].values

    # Calculate N-bar forward cumulative returns
    labels = np.zeros(len(close), dtype=np.float32)
    for i in range(len(close) - horizon):
        labels[i] = (close[i + horizon] - close[i]) / close[i]

    # Pad last values with 0
    labels[-horizon:] = 0

    return labels


class RegressionLSTM(nn.Module):
    """LSTM for regression (predicts continuous return)."""

    def __init__(self, input_dim=58, hidden_dim=64, num_layers=2, dropout=0.3):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers,
                           batch_first=True, dropout=dropout if num_layers > 1 else 0)
        self.fc = nn.Linear(hidden_dim, 1)  # Output: single continuous value

    def forward(self, x):
        # x shape: (batch, input_dim) -> add sequence dim
        x = x.unsqueeze(1)  # (batch, 1, input_dim)
        lstm_out, _ = self.lstm(x)
        out = self.fc(lstm_out[:, -1, :])  # (batch, 1)
        return out.squeeze(-1)  # (batch,)


class RegressionGRU(nn.Module):
    """GRU for regression."""

    def __init__(self, input_dim=58, hidden_dim=64, num_layers=2, dropout=0.3):
        super().__init__()
        self.gru = nn.GRU(input_dim, hidden_dim, num_layers,
                         batch_first=True, dropout=dropout if num_layers > 1 else 0)
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        x = x.unsqueeze(1)
        gru_out, _ = self.gru(x)
        out = self.fc(gru_out[:, -1, :])
        return out.squeeze(-1)


class RegressionTransformer(nn.Module):
    """Transformer for regression."""

    def __init__(self, input_dim=58, d_model=64, nhead=4, num_layers=2, dropout=0.3):
        super().__init__()
        self.embedding = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model, nhead, dim_feedforward=d_model*2,
                                                   dropout=dropout, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        self.fc = nn.Linear(d_model, 1)

    def forward(self, x):
        x = x.unsqueeze(1)
        x = self.embedding(x)
        x = self.transformer(x)
        out = self.fc(x[:, -1, :])
        return out.squeeze(-1)


def train_regression_model(model, X_train, y_train, X_val, y_val,
                          learning_rate=0.001, batch_size=64, max_epochs=20,
                          patience=5, device='cpu'):
    """Train regression model with MSE loss and early stopping."""
    model = model.to(device)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=0.01)
    criterion = nn.MSELoss()

    # Convert to tensors
    X_train_t = torch.FloatTensor(X_train).to(device)
    y_train_t = torch.FloatTensor(y_train).to(device)
    X_val_t = torch.FloatTensor(X_val).to(device)
    y_val_t = torch.FloatTensor(y_val).to(device)

    best_val_loss = float('inf')
    patience_counter = 0

    for epoch in range(max_epochs):
        # Training
        model.train()
        indices = torch.randperm(len(X_train_t))
        train_loss = 0
        num_batches = 0

        for i in range(0, len(indices), batch_size):
            batch_idx = indices[i:i+batch_size]
            X_batch = X_train_t[batch_idx]
            y_batch = y_train_t[batch_idx]

            optimizer.zero_grad()
            pred = model(X_batch)
            loss = criterion(pred, y_batch)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            num_batches += 1

        train_loss /= num_batches

        # Validation
        model.eval()
        with torch.no_grad():
            val_pred = model(X_val_t)
            val_loss = criterion(val_pred, y_val_t).item()

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"    Early stopping at epoch {epoch+1}")
                break

    logger.info(f"    Final - Train MSE: {train_loss:.6f}, Val MSE: {val_loss:.6f}")
    return model


def evaluate_regression(model, X_test, y_test, device='cpu'):
    """Evaluate regression model performance."""
    model.eval()
    X_test_t = torch.FloatTensor(X_test).to(device)

    with torch.no_grad():
        pred = model(X_test_t).cpu().numpy()

    # Calculate metrics
    mse = np.mean((pred - y_test) ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(pred - y_test))

    # R² score
    ss_res = np.sum((y_test - pred) ** 2)
    ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # Directional accuracy (did we predict the right sign?)
    pred_direction = np.sign(pred)
    true_direction = np.sign(y_test)
    direction_acc = np.mean(pred_direction == true_direction)

    return {
        'mse': mse,
        'rmse': rmse,
        'mae': mae,
        'r2': r2,
        'direction_accuracy': direction_acc,
        'predictions': pred
    }


def main():
    parser = argparse.ArgumentParser(
        description="Phase 3 ensemble with regression + longer horizon + microstructure"
    )
    parser.add_argument("--months", type=int, default=12, help="Months of intraday data")
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu/cuda)")
    parser.add_argument("--horizon", type=int, default=12, help="Prediction horizon in bars (default: 12 = 60min)")
    args = parser.parse_args()

    print("=" * 80)
    print("PHASE 3: REGRESSION ENSEMBLE WITH LONG HORIZON + MICROSTRUCTURE")
    print("=" * 80)
    print()

    # Initialize
    print("[1/8] Initializing Alpaca client...")
    API_KEY = os.getenv("ALPACA_API_KEY")
    API_SECRET = os.getenv("ALPACA_SECRET_KEY")

    if not API_KEY or not API_SECRET:
        print("ERROR: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set")
        return 1

    client = StockHistoricalDataClient(API_KEY, API_SECRET)
    print("[OK] Connected")

    # Fetch data
    print(f"\n[2/8] Fetching {args.months} months of SPY 5-minute data...")
    end = datetime.now()
    start = end - timedelta(days=args.months * 30)

    request = StockBarsRequest(
        symbol_or_symbols="SPY",
        timeframe=TimeFrame(5, TimeFrameUnit.Minute),
        start=start,
        end=end
    )

    bars = client.get_stock_bars(request)
    spy_bars = bars["SPY"]

    data = pd.DataFrame({
        "date": [bar.timestamp for bar in spy_bars],
        "open": [bar.open for bar in spy_bars],
        "high": [bar.high for bar in spy_bars],
        "low": [bar.low for bar in spy_bars],
        "close": [bar.close for bar in spy_bars],
        "volume": [bar.volume for bar in spy_bars],
    })

    print(f"[OK] Fetched {len(data)} bars")

    # Add microstructure features
    print(f"\n[3/8] Adding microstructure features...")
    data = add_microstructure_features(data)
    print("[OK] Added 6 microstructure features")

    # Extract base 52 features
    print("\n[4/8] Extracting 52-dimensional technical features...")
    extractor = FeatureExtractor()
    feature_sets = extractor.extract(data, symbol="SPY")
    X_base = np.array([fs.to_array() for fs in feature_sets])

    # Add microstructure features to feature array
    microstructure_cols = ['intrabar_volatility', 'volume_imbalance', 'momentum_5',
                           'momentum_10', 'price_vs_vwap']
    X_micro = data[microstructure_cols].values[:len(X_base)]
    X = np.concatenate([X_base, X_micro], axis=1)

    print(f"[OK] Total features: {X.shape[1]} (52 technical + {X_micro.shape[1]} microstructure)")

    # Create regression labels
    print(f"\n[5/8] Creating {args.horizon}-bar ({args.horizon*5}min) cumulative return labels...")
    y = create_regression_labels(data, horizon=args.horizon)

    # Align X and y
    min_len = min(len(X), len(y))
    X = X[:min_len]
    y = y[:min_len]

    print(f"[OK] Label statistics:")
    print(f"  Mean return: {np.mean(y)*100:.4f}%")
    print(f"  Std return: {np.std(y)*100:.4f}%")
    print(f"  Min return: {np.min(y)*100:.4f}%")
    print(f"  Max return: {np.max(y)*100:.4f}%")

    # Split data
    print("\n[6/8] Preparing train/val/test splits...")
    n = len(X)
    train_end = int(0.6 * n)
    val_end = int(0.8 * n)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]

    print(f"[OK] Splits: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")

    # Create and train models
    print(f"\n[7/8] Training regression ensemble ({args.epochs} epochs)...")
    input_dim = X.shape[1]

    models = [
        ('LSTM', RegressionLSTM(input_dim=input_dim, hidden_dim=64, num_layers=2, dropout=0.3)),
        ('GRU', RegressionGRU(input_dim=input_dim, hidden_dim=64, num_layers=2, dropout=0.3)),
        ('Transformer', RegressionTransformer(input_dim=input_dim, d_model=64, nhead=4, num_layers=2, dropout=0.3))
    ]

    trained_models = []
    for name, model in models:
        print(f"  Training {name}...")
        trained_model = train_regression_model(
            model, X_train, y_train, X_val, y_val,
            learning_rate=0.001, batch_size=64, max_epochs=args.epochs,
            patience=5, device=args.device
        )
        trained_models.append((name, trained_model))

    print("[OK] Training complete")

    # Evaluate
    print("\n[8/8] Evaluating performance...")
    print("=" * 80)

    results = {}
    for name, model in trained_models:
        metrics = evaluate_regression(model, X_test, y_test, device=args.device)
        results[name] = metrics

        print(f"\n{name} Performance:")
        print("-" * 80)
        print(f"  RMSE: {metrics['rmse']*100:.4f}% (lower is better)")
        print(f"  MAE:  {metrics['mae']*100:.4f}%")
        print(f"  R²:   {metrics['r2']:.4f} (higher is better, max 1.0)")
        print(f"  Directional Accuracy: {metrics['direction_accuracy']*100:.2f}%")

    # Ensemble prediction (simple average)
    print("\n" + "=" * 80)
    print("ENSEMBLE PERFORMANCE (Average of all models)")
    print("=" * 80)

    all_preds = np.array([results[name]['predictions'] for name, _ in trained_models])
    ensemble_pred = np.mean(all_preds, axis=0)

    mse = np.mean((ensemble_pred - y_test) ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(ensemble_pred - y_test))

    ss_res = np.sum((y_test - ensemble_pred) ** 2)
    ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    direction_acc = np.mean(np.sign(ensemble_pred) == np.sign(y_test))

    print(f"  RMSE: {rmse*100:.4f}%")
    print(f"  MAE:  {mae*100:.4f}%")
    print(f"  R²:   {r2:.4f}")
    print(f"  Directional Accuracy: {direction_acc*100:.2f}%")

    # Success criteria for regression
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)

    # For regression, good performance:
    # - R² > 0.05 (explains 5%+ of variance - difficult for financial data!)
    # - Directional accuracy > 55% (better than random)

    success = r2 > 0.05 and direction_acc > 0.55

    if success:
        print(f"[OK] R² = {r2:.4f} > 0.05 (explains {r2*100:.2f}% of variance)")
        print(f"[OK] Directional accuracy = {direction_acc*100:.2f}% > 55%")
        print("\nPhase 3 validation: SUCCESS")
        print(f"Regression ensemble achieves {direction_acc*100:.1f}% directional accuracy!")
        return 0
    else:
        print(f"[WARNING] R² = {r2:.4f} < 0.05 (explains only {r2*100:.2f}% of variance)")
        if direction_acc <= 0.55:
            print(f"[WARNING] Directional accuracy = {direction_acc*100:.2f}% <= 55%")
        print("\nPhase 3 validation: NEEDS IMPROVEMENT")
        return 1


if __name__ == "__main__":
    sys.exit(main())
