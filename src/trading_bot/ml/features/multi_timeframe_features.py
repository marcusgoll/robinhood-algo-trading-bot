"""
Multi-Timeframe Feature Extraction for Phase 4

This module provides utilities to fetch and align multiple timeframes
(1min, 5min, 15min, 1hr, 4hr) and extract features from each timeframe.

The goal is to improve prediction accuracy from 59.65% to 60-61% by
incorporating multi-scale temporal patterns.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import alpaca_trade_api as tradeapi
import warnings
warnings.filterwarnings('ignore')


def fetch_aligned_multi_timeframe(
    symbol: str,
    primary_timeframe: str,
    additional_timeframes: List[str],
    days: int,
    api_key: str,
    api_secret: str,
    base_url: str = "https://paper-api.alpaca.markets"
) -> Dict[str, pd.DataFrame]:
    """
    Fetch multiple timeframes and align them to the primary timeframe.

    Args:
        symbol: Stock ticker
        primary_timeframe: Main timeframe for predictions (e.g., '5Min')
        additional_timeframes: List of additional timeframes (e.g., ['15Min', '1Hour', '4Hour'])
        days: Number of days of historical data
        api_key: Alpaca API key
        api_secret: Alpaca API secret
        base_url: Alpaca API base URL

    Returns:
        Dictionary mapping timeframe names to aligned DataFrames
    """
    api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Fetch all timeframes
    all_data = {}
    timeframes_to_fetch = [primary_timeframe] + additional_timeframes

    print(f"Fetching {len(timeframes_to_fetch)} timeframes for {symbol}...")

    for tf in timeframes_to_fetch:
        print(f"  Fetching {tf}...", end=" ")
        try:
            bars = api.get_bars(
                symbol,
                tf,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                limit=10000
            ).df

            if bars.empty:
                print(f"WARNING: No data for {tf}")
                continue

            # Reset index to make timestamp a column
            bars = bars.reset_index()
            bars['timestamp'] = pd.to_datetime(bars['timestamp'])

            # Calculate returns and volatility
            bars['returns'] = bars['close'].pct_change()
            bars['volatility'] = bars['returns'].rolling(window=20).std()
            bars['volume_ma'] = bars['volume'].rolling(window=20).mean()
            bars['volume_ratio'] = bars['volume'] / bars['volume_ma']

            all_data[tf] = bars
            print(f"OK ({len(bars)} bars)")

        except Exception as e:
            print(f"ERROR: {str(e)}")
            continue

    if primary_timeframe not in all_data:
        raise ValueError(f"Failed to fetch primary timeframe {primary_timeframe}")

    return all_data


def extract_multi_tf_features(
    aligned_data: Dict[str, pd.DataFrame],
    primary_timeframe: str,
    lookback_bars: int = 20
) -> pd.DataFrame:
    """
    Extract features from aligned multi-timeframe data.

    For each timestamp in the primary timeframe, we extract:
    - Price features: close, high, low, returns from each timeframe
    - Volatility features: rolling std from each timeframe
    - Volume features: volume, volume_ratio from each timeframe
    - Trend features: SMA, EMA from each timeframe

    Args:
        aligned_data: Dictionary of DataFrames for each timeframe
        primary_timeframe: The main timeframe for predictions
        lookback_bars: Number of bars to look back for rolling features

    Returns:
        DataFrame with multi-timeframe features aligned to primary timeframe
    """
    primary_df = aligned_data[primary_timeframe].copy()

    # Start with basic features from primary timeframe
    features_df = primary_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()

    # Add returns and volatility from primary
    features_df['returns'] = primary_df['returns']
    features_df['volatility'] = primary_df['volatility']
    features_df['volume_ratio'] = primary_df['volume_ratio']

    # Add technical indicators from primary timeframe
    features_df['sma_20'] = primary_df['close'].rolling(window=20).mean()
    features_df['ema_12'] = primary_df['close'].ewm(span=12).mean()
    features_df['ema_26'] = primary_df['close'].ewm(span=26).mean()
    features_df['rsi'] = calculate_rsi(primary_df['close'], period=14)

    # Add Bollinger Bands
    bb_middle = primary_df['close'].rolling(window=20).mean()
    bb_std = primary_df['close'].rolling(window=20).std()
    features_df['bb_upper'] = bb_middle + (2 * bb_std)
    features_df['bb_lower'] = bb_middle - (2 * bb_std)
    features_df['bb_position'] = (primary_df['close'] - features_df['bb_lower']) / (features_df['bb_upper'] - features_df['bb_lower'])

    # For each additional timeframe, add summary features
    for tf_name, tf_df in aligned_data.items():
        if tf_name == primary_timeframe:
            continue

        print(f"  Extracting features from {tf_name}...")

        # Merge using asof (forward fill to align timestamps)
        merged = pd.merge_asof(
            features_df[['timestamp']].sort_values('timestamp'),
            tf_df[['timestamp', 'close', 'returns', 'volatility', 'volume_ratio']].sort_values('timestamp'),
            on='timestamp',
            direction='backward',
            suffixes=('', f'_{tf_name}')
        )

        # Add features from this timeframe
        tf_prefix = tf_name.replace('Min', 'm').replace('Hour', 'h').replace('Day', 'd')

        features_df[f'{tf_prefix}_close'] = merged['close']
        features_df[f'{tf_prefix}_returns'] = merged['returns']
        features_df[f'{tf_prefix}_volatility'] = merged['volatility']
        features_df[f'{tf_prefix}_volume_ratio'] = merged['volume_ratio']

        # Add trend alignment: is primary trend aligned with this timeframe?
        features_df[f'{tf_prefix}_trend_aligned'] = np.sign(features_df['returns']) == np.sign(merged['returns'])
        features_df[f'{tf_prefix}_trend_aligned'] = features_df[f'{tf_prefix}_trend_aligned'].astype(float)

    # Drop rows with NaN from rolling calculations
    features_df = features_df.dropna()

    return features_df


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def extract_features_and_targets_multi_tf(
    multi_tf_features: pd.DataFrame,
    horizon_bars: int,
    feature_columns: Optional[List[str]] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract feature matrix X and target vector y from multi-timeframe features.

    Args:
        multi_tf_features: DataFrame with multi-timeframe features
        horizon_bars: Number of bars ahead to predict
        feature_columns: Specific columns to use as features (if None, use all numeric)

    Returns:
        X: Feature matrix (n_samples, n_features)
        y: Target vector (n_samples,) - returns at horizon_bars ahead
    """
    df = multi_tf_features.copy()

    # Create target: returns at horizon_bars ahead
    df['target'] = df['close'].pct_change(horizon_bars).shift(-horizon_bars)

    # Drop rows where we can't calculate target
    df = df.dropna(subset=['target'])

    if df.empty:
        raise ValueError("No valid samples after creating targets")

    # Select feature columns
    if feature_columns is None:
        # Use all numeric columns except timestamp and target
        exclude_cols = ['timestamp', 'target']
        feature_columns = [col for col in df.columns if col not in exclude_cols and df[col].dtype in [np.float64, np.int64]]

    # Extract X and y
    X = df[feature_columns].values
    y = df['target'].values

    print(f"Extracted {X.shape[0]} samples with {X.shape[1]} features")
    print(f"Feature columns: {feature_columns}")

    return X, y


def create_multi_tf_dataset(
    symbol: str,
    primary_timeframe: str,
    additional_timeframes: List[str],
    horizon_bars: int,
    days: int,
    api_key: str,
    api_secret: str
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    End-to-end pipeline to create multi-timeframe dataset.

    Args:
        symbol: Stock ticker
        primary_timeframe: Main prediction timeframe
        additional_timeframes: Additional timeframes to incorporate
        horizon_bars: Prediction horizon
        days: Days of historical data
        api_key: Alpaca API key
        api_secret: Alpaca API secret

    Returns:
        X: Feature matrix
        y: Target vector
        feature_names: List of feature column names
    """
    print(f"Creating multi-timeframe dataset for {symbol}")
    print(f"Primary: {primary_timeframe}, Additional: {additional_timeframes}")
    print(f"Horizon: {horizon_bars} bars, History: {days} days")
    print()

    # Step 1: Fetch aligned timeframes
    aligned_data = fetch_aligned_multi_timeframe(
        symbol=symbol,
        primary_timeframe=primary_timeframe,
        additional_timeframes=additional_timeframes,
        days=days,
        api_key=api_key,
        api_secret=api_secret
    )

    print()

    # Step 2: Extract multi-timeframe features
    multi_tf_features = extract_multi_tf_features(
        aligned_data=aligned_data,
        primary_timeframe=primary_timeframe,
        lookback_bars=20
    )

    print()

    # Step 3: Create X, y
    exclude_cols = ['timestamp', 'target']
    feature_columns = [col for col in multi_tf_features.columns
                      if col not in exclude_cols
                      and multi_tf_features[col].dtype in [np.float64, np.int64]]

    X, y = extract_features_and_targets_multi_tf(
        multi_tf_features=multi_tf_features,
        horizon_bars=horizon_bars,
        feature_columns=feature_columns
    )

    return X, y, feature_columns


if __name__ == "__main__":
    """Test multi-timeframe feature extraction."""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')

    if not api_key or not api_secret:
        print("ERROR: Missing Alpaca API credentials")
        exit(1)

    # Test with SPY
    print("=" * 80)
    print("Testing Multi-Timeframe Feature Extraction")
    print("=" * 80)
    print()

    X, y, feature_names = create_multi_tf_dataset(
        symbol='SPY',
        primary_timeframe='5Min',
        additional_timeframes=['15Min', '1Hour', '4Hour'],
        horizon_bars=78,  # Same as Phase 3 winner
        days=60,
        api_key=api_key,
        api_secret=api_secret
    )

    print()
    print("=" * 80)
    print("Dataset Summary")
    print("=" * 80)
    print(f"Total samples: {len(X)}")
    print(f"Total features: {len(feature_names)}")
    print(f"Feature names: {feature_names[:10]}... (showing first 10)")
    print(f"Target range: [{y.min():.4f}, {y.max():.4f}]")
    print(f"Target mean: {y.mean():.4f}")
    print(f"Target std: {y.std():.4f}")
    print()
    print("Feature extraction test PASSED!")
