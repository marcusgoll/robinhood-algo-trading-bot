"""
Multi-Symbol Baseline Validation

Test baseline model (15 features) across multiple symbols to confirm
generalization beyond SPY.

Symbols to test:
- SPY: S&P 500 ETF (already validated)
- QQQ: Nasdaq 100 ETF (tech-heavy)
- NVDA: Individual tech stock (high volatility)
- TSLA: Individual stock (very high volatility)

Expected: 55%+ accuracy across all symbols
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import alpaca_trade_api as tradeapi

from validate_phase4 import AttentionLSTM


def set_seed(seed: int):
    """Set random seeds for reproducibility."""
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def create_baseline_dataset(
    symbol: str,
    horizon_bars: int,
    days: int,
    api_key: str,
    api_secret: str
):
    """
    Create baseline dataset (15 features) for any symbol.

    Returns:
        X, y, feature_names
    """
    api = tradeapi.REST(api_key, api_secret, "https://paper-api.alpaca.markets", api_version='v2')

    # Fetch data (30+ days in past to avoid API restrictions)
    end_date = datetime.now() - timedelta(days=30)
    start_date = end_date - timedelta(days=days)

    print(f"  Fetching {symbol} 5Min data...", end=" ", flush=True)
    bars = api.get_bars(
        symbol,
        '5Min',
        start=start_date.strftime('%Y-%m-%d'),
        end=end_date.strftime('%Y-%m-%d'),
        limit=10000
    ).df

    if bars.empty:
        raise ValueError(f"No data for {symbol}")

    bars = bars.reset_index()
    bars['timestamp'] = pd.to_datetime(bars['timestamp'])

    print(f"OK ({len(bars)} bars)")

    # Calculate base features
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

    # Create target
    bars['target'] = bars['close'].pct_change(horizon_bars).shift(-horizon_bars)

    # Select features (baseline 15)
    feature_cols = ['open', 'high', 'low', 'close', 'volume', 'returns', 'volatility',
                    'volume_ratio', 'sma_20', 'ema_12', 'ema_26', 'rsi',
                    'bb_upper', 'bb_lower', 'bb_position']

    # Drop NaN
    bars = bars.dropna()

    if bars.empty:
        raise ValueError(f"No valid samples for {symbol} after feature creation")

    X = bars[feature_cols].values
    y = bars['target'].values

    print(f"  Created {len(X)} samples with {len(feature_cols)} features")

    return X, y, feature_cols


def train_and_evaluate(X, y, symbol, seed=0, epochs=30, device='cpu'):
    """Train baseline model and return directional accuracy."""
    set_seed(seed)

    # Split data
    n = len(X)
    train_end = int(0.6 * n)
    val_end = int(0.8 * n)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]

    # Create model
    model = AttentionLSTM(input_dim=15, hidden_dim=64, num_layers=2, dropout=0.3).to(device)
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
                break

    # Evaluate on test set
    model.eval()
    with torch.no_grad():
        X_tensor = torch.FloatTensor(X_test).to(device)
        predictions = model(X_tensor).cpu().numpy().flatten()

    # Directional accuracy
    y_test_direction = np.sign(y_test)
    pred_direction = np.sign(predictions)
    directional_accuracy = np.mean(y_test_direction == pred_direction) * 100

    return directional_accuracy


def validate_symbol(symbol: str, api_key: str, api_secret: str, num_trials: int = 5):
    """
    Validate baseline model on a symbol with multiple seeds.

    Returns:
        Dictionary with statistics
    """
    print(f"\n{'=' * 80}")
    print(f"SYMBOL: {symbol}")
    print(f"{'=' * 80}")

    try:
        # Fetch data once
        X, y, features = create_baseline_dataset(
            symbol=symbol,
            horizon_bars=78,
            days=60,
            api_key=api_key,
            api_secret=api_secret
        )

        # Run multiple trials
        accuracies = []
        print(f"\n  Running {num_trials} trials:")

        for seed in range(num_trials):
            print(f"    Trial {seed+1}/{num_trials} (seed={seed})... ", end="", flush=True)
            acc = train_and_evaluate(X, y, symbol, seed=seed, epochs=30)
            accuracies.append(acc)
            print(f"{acc:.2f}%")

        # Statistics
        mean_acc = np.mean(accuracies)
        std_acc = np.std(accuracies)
        min_acc = np.min(accuracies)
        max_acc = np.max(accuracies)

        print(f"\n  Summary:")
        print(f"    Mean: {mean_acc:.2f}% ± {std_acc:.2f}%")
        print(f"    Range: [{min_acc:.2f}%, {max_acc:.2f}%]")

        return {
            'symbol': symbol,
            'mean_acc': mean_acc,
            'std_acc': std_acc,
            'min_acc': min_acc,
            'max_acc': max_acc,
            'trials': accuracies,
            'num_samples': len(X),
            'status': 'success'
        }

    except Exception as e:
        print(f"\n  ERROR: {str(e)}")
        return {
            'symbol': symbol,
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
    print("MULTI-SYMBOL BASELINE VALIDATION")
    print("=" * 80)
    print()
    print("Testing baseline model (15 features) across multiple symbols")
    print("Goal: Confirm 55%+ accuracy generalizes beyond SPY")
    print()

    # Test symbols
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA']
    num_trials = 5

    results = []

    for symbol in symbols:
        result = validate_symbol(symbol, api_key, api_secret, num_trials)
        results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print()

    df = pd.DataFrame(results)

    # Successful validations
    successful = df[df['status'] == 'success']

    if len(successful) > 0:
        print("Symbol Performance:")
        print()
        print(f"{'Symbol':<8} {'Mean Acc':<12} {'Std':<8} {'Range':<20} {'Samples':<10}")
        print("-" * 60)

        for _, row in successful.iterrows():
            range_str = f"[{row['min_acc']:.2f}%, {row['max_acc']:.2f}%]"
            print(f"{row['symbol']:<8} {row['mean_acc']:>10.2f}%  {row['std_acc']:>6.2f}%  {range_str:<20} {row['num_samples']:>8}")

        print()
        print("Overall Statistics:")
        print(f"  Average across symbols: {successful['mean_acc'].mean():.2f}%")
        print(f"  Best symbol: {successful.loc[successful['mean_acc'].idxmax(), 'symbol']} ({successful['mean_acc'].max():.2f}%)")
        print(f"  Worst symbol: {successful.loc[successful['mean_acc'].idxmin(), 'symbol']} ({successful['mean_acc'].min():.2f}%)")
        print(f"  Stability (avg std): {successful['std_acc'].mean():.2f}%")
        print()

        # Verdict
        min_symbol_acc = successful['mean_acc'].min()
        avg_acc = successful['mean_acc'].mean()

        if min_symbol_acc >= 55.0 and avg_acc >= 57.0:
            print("SUCCESS: Baseline generalizes well across all symbols (55%+ minimum)")
        elif avg_acc >= 55.0:
            print("PARTIAL SUCCESS: Average above 55%, but some symbols underperform")
        elif avg_acc >= 52.0:
            print("MARGINAL: Weak generalization, needs further investigation")
        else:
            print("FAILURE: Model does not generalize beyond SPY")

    # Failed validations
    failed = df[df['status'] == 'failed']
    if len(failed) > 0:
        print()
        print("Failed Symbols:")
        for _, row in failed.iterrows():
            print(f"  {row['symbol']}: {row.get('error', 'Unknown error')}")

    # Save results
    output_file = 'baseline_multi_symbol_results.csv'
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
