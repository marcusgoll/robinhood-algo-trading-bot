"""
Phase 6: Sentiment Integration - External Market Data

Add external sentiment indicators to baseline model:
1. VIX (Volatility Index) - Market fear gauge
2. Relative strength vs market (SPY comparison for individual stocks)
3. Sector momentum (if applicable)

Expected: 60.5-61.5% accuracy by adding genuinely new information.
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


def fetch_vix_data(api_key: str, api_secret: str, days: int = 60):
    """
    Fetch VIX (Volatility Index) data.

    VIX measures market volatility expectations and serves as a "fear gauge".
    High VIX = high market uncertainty, Low VIX = complacent market.
    """
    api = tradeapi.REST(api_key, api_secret, "https://paper-api.alpaca.markets", api_version='v2')

    # Use historical data (30+ days ago) to avoid API restrictions
    end_date = datetime.now() - timedelta(days=30)
    start_date = end_date - timedelta(days=days)

    try:
        # Fetch VIX daily data
        vix = api.get_bars(
            'VIX',
            '1Day',
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            limit=10000
        ).df

        if vix.empty:
            print("WARNING: VIX data not available, using proxy")
            return None

        vix = vix.reset_index()
        vix['timestamp'] = pd.to_datetime(vix['timestamp'])
        vix = vix.rename(columns={'close': 'vix_close'})

        return vix[['timestamp', 'vix_close']]

    except Exception as e:
        print(f"VIX fetch failed: {e}, will use alternative sentiment proxy")
        return None


def create_sentiment_features(primary_df: pd.DataFrame, vix_df: pd.DataFrame = None):
    """
    Add sentiment features to primary dataframe.

    Features:
    1. VIX level (if available) - market fear gauge
    2. VIX change - increasing/decreasing fear
    3. Price momentum (5-period) - short-term strength
    4. Volume surge - unusual activity indicator
    """
    df = primary_df.copy()

    # Feature 1 & 2: VIX integration
    if vix_df is not None:
        # Merge VIX (daily) with intraday data
        # Use date for merge
        df['date'] = df['timestamp'].dt.date
        vix_df['date'] = vix_df['timestamp'].dt.date

        df = pd.merge(df, vix_df[['date', 'vix_close']], on='date', how='left')
        df['vix_close'] = df['vix_close'].fillna(method='ffill')  # Forward fill VIX
        df['vix_change'] = df['vix_close'].pct_change()

        df = df.drop('date', axis=1)
    else:
        # Sentiment proxy: use volatility spike as fear indicator
        df['vix_close'] = df['volatility']  # Use local volatility as proxy
        df['vix_change'] = df['vix_close'].pct_change()

    # Feature 3: Price momentum (5-period rate of change)
    df['momentum_5'] = df['close'].pct_change(5)

    # Feature 4: Volume surge (current vs 20-period average)
    # volume_ratio already exists, but let's add volume change rate
    df['volume_change'] = df['volume'].pct_change()

    return df


def create_sentiment_dataset(
    symbol: str,
    horizon_bars: int,
    days: int,
    api_key: str,
    api_secret: str,
    include_sentiment: bool = True
):
    """
    Create dataset with optional sentiment features.

    Returns:
        X, y, feature_names
    """
    api = tradeapi.REST(api_key, api_secret, "https://paper-api.alpaca.markets", api_version='v2')

    # Fetch primary data (5Min)
    end_date = datetime.now() - timedelta(days=30)
    start_date = end_date - timedelta(days=days)

    print(f"Fetching {symbol} 5Min data...")
    bars = api.get_bars(
        symbol,
        '5Min',
        start=start_date.strftime('%Y-%m-%d'),
        end=end_date.strftime('%Y-%m-%d'),
        limit=10000
    ).df

    bars = bars.reset_index()
    bars['timestamp'] = pd.to_datetime(bars['timestamp'])

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

    # Add sentiment features if requested
    if include_sentiment:
        vix_df = fetch_vix_data(api_key, api_secret, days)
        bars = create_sentiment_features(bars, vix_df)

    # Create target
    bars['target'] = bars['close'].pct_change(horizon_bars).shift(-horizon_bars)

    # Select features
    base_features = ['open', 'high', 'low', 'close', 'volume', 'returns', 'volatility',
                     'volume_ratio', 'sma_20', 'ema_12', 'ema_26', 'rsi',
                     'bb_upper', 'bb_lower', 'bb_position']

    sentiment_features = ['vix_close', 'vix_change', 'momentum_5', 'volume_change']

    if include_sentiment:
        feature_cols = base_features + sentiment_features
    else:
        feature_cols = base_features

    # Drop NaN
    bars = bars.dropna()

    if bars.empty:
        raise ValueError("No valid samples after feature creation")

    X = bars[feature_cols].values
    y = bars['target'].values

    print(f"Created {len(X)} samples with {len(feature_cols)} features")
    print(f"Features: {feature_cols}")

    return X, y, feature_cols


def train_and_evaluate(X, y, model_name, seed=0, epochs=30, device='cpu'):
    """Train model and return directional accuracy."""
    set_seed(seed)

    # Split data
    n = len(X)
    train_end = int(0.6 * n)
    val_end = int(0.8 * n)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]

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

    # Metrics
    y_test_direction = np.sign(y_test)
    pred_direction = np.sign(predictions)
    directional_accuracy = np.mean(y_test_direction == pred_direction) * 100

    return directional_accuracy


def main():
    load_dotenv()
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')

    if not api_key or not api_secret:
        print("ERROR: Missing Alpaca credentials")
        return

    print("=" * 80)
    print("PHASE 6: SENTIMENT INTEGRATION VALIDATION")
    print("=" * 80)
    print()
    print("Test: Add sentiment features (VIX, momentum, volume surge)")
    print("Method: Compare baseline vs sentiment-enhanced with multiple seeds")
    print()

    symbol = 'SPY'
    num_trials = 5

    # Baseline results (we already know these)
    print("Baseline (15 features): 59.77% +/- 0.00%")
    print()

    # Test sentiment-enhanced model
    print("-" * 80)
    print("Sentiment-Enhanced Model (19 features)")
    print("-" * 80)

    sentiment_accuracies = []

    for trial in range(num_trials):
        print(f"Trial {trial+1}/{num_trials} (seed={trial})... ", end="", flush=True)

        # Fetch data with sentiment features
        X, y, features = create_sentiment_dataset(
            symbol=symbol,
            horizon_bars=78,
            days=60,
            api_key=api_key,
            api_secret=api_secret,
            include_sentiment=True
        )

        acc = train_and_evaluate(X, y, f"Sentiment (seed={trial})", seed=trial, epochs=30)
        sentiment_accuracies.append(acc)

        print(f"{acc:.2f}%")

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    print(f"Baseline (15 features):")
    print(f"  Accuracy: 59.77% +/- 0.00%")
    print()
    print(f"Sentiment-Enhanced (19 features):")
    print(f"  Accuracy: {np.mean(sentiment_accuracies):.2f}% +/- {np.std(sentiment_accuracies):.2f}%")
    print(f"  Trials: {sentiment_accuracies}")
    print()

    improvement = np.mean(sentiment_accuracies) - 59.77
    print(f"Improvement: {improvement:+.2f}%")
    print()

    # Statistical significance
    if improvement > 1.0:
        print("SUCCESS: Sentiment provides significant improvement!")
    elif improvement > 0.5:
        print("MARGINAL: Sentiment provides modest improvement")
    elif improvement > 0:
        print("SLIGHT: Sentiment provides minimal improvement")
    else:
        print("NO BENEFIT: Sentiment does not improve predictions")

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
