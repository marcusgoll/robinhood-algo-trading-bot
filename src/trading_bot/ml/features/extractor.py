"""Main feature extraction orchestrator."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from trading_bot.ml.features.support_resistance import SupportResistanceDetector
from trading_bot.ml.features.technical import TechnicalFeatureCalculator
from trading_bot.ml.models import FeatureSet

if TYPE_CHECKING:
    from pandas import DataFrame


class FeatureExtractor:
    """Extracts 52-dimensional feature vectors from market data.

    Orchestrates feature calculation from multiple sources:
    - Price features (10)
    - Technical indicators (15)
    - Market microstructure (5)
    - Sentiment (3)
    - Time features (4)
    - Support/Resistance features (9)
    - Pattern features (6)

    All features normalized to [-1, 1] or [0, 1] ranges.

    Usage:
        ```python
        extractor = FeatureExtractor()
        features = extractor.extract(ohlcv_df, symbol="AAPL")
        ```
    """

    def __init__(self) -> None:
        """Initialize feature extractor."""
        self.technical_calc = TechnicalFeatureCalculator()
        self.sr_detector = SupportResistanceDetector()

    def calculate_price_features(
        self, df: DataFrame
    ) -> dict[str, NDArray[np.float64]]:
        """Calculate price-based features (10 features).

        Args:
            df: OHLCV DataFrame

        Returns:
            Dictionary of price feature arrays
        """
        # Convert string columns to float (Robinhood API returns strings)
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        # Returns
        returns_1d = close.pct_change(1).fillna(0.0).clip(-0.2, 0.2) / 0.2
        returns_5d = close.pct_change(5).fillna(0.0).clip(-0.5, 0.5) / 0.5
        returns_20d = close.pct_change(20).fillna(0.0).clip(-1.0, 1.0)

        # Volatility (20-day realized vol)
        volatility_20d = (
            close.pct_change()
            .rolling(window=20)
            .std()
            .fillna(0.0)
            .clip(0, 0.1)
            / 0.1
        )

        # Volume ratio (vs 20-day average)
        vol_avg = volume.rolling(window=20).mean()
        volume_ratio = (volume / vol_avg).fillna(1.0).clip(0, 5) / 5.0

        # Intraday range
        high_low_range = ((high - low) / close).fillna(0.0).clip(0, 0.1) / 0.1

        # Close position within range
        close_to_high = ((close - low) / (high - low + 1e-9)).fillna(0.5).clip(0, 1)

        # Price to moving averages
        sma20 = close.rolling(window=20).mean()
        sma50 = close.rolling(window=50).mean()

        price_to_sma20 = (close / sma20).fillna(1.0).clip(0.8, 1.2)
        price_to_sma20 = (price_to_sma20 - 1.0) / 0.2  # Center at 0

        price_to_sma50 = (close / sma50).fillna(1.0).clip(0.8, 1.2)
        price_to_sma50 = (price_to_sma50 - 1.0) / 0.2  # Center at 0

        # VWAP (intraday - use cumulative for daily data)
        cumulative_tpv = (close * volume).cumsum()
        cumulative_vol = volume.cumsum()
        vwap = cumulative_tpv / (cumulative_vol + 1e-9)
        price_to_vwap = (close / vwap).fillna(1.0).clip(0.95, 1.05)
        price_to_vwap = (price_to_vwap - 1.0) / 0.05  # Center at 0

        return {
            "returns_1d": returns_1d.values,
            "returns_5d": returns_5d.values,
            "returns_20d": returns_20d.values,
            "volatility_20d": volatility_20d.values,
            "volume_ratio": volume_ratio.values,
            "high_low_range": high_low_range.values,
            "close_to_high": close_to_high.values,
            "price_to_sma20": price_to_sma20.values,
            "price_to_sma50": price_to_sma50.values,
            "price_to_vwap": price_to_vwap.values,
        }

    def calculate_microstructure_features(
        self, df: DataFrame
    ) -> dict[str, NDArray[np.float64]]:
        """Calculate market microstructure features (5 features).

        Note: Some features require Level 2 data which may not be available.
        Placeholder values used when data unavailable.

        Args:
            df: OHLCV DataFrame

        Returns:
            Dictionary of microstructure feature arrays
        """
        n = len(df)

        # Placeholder features (require real-time Level 2 data)
        bid_ask_spread = np.zeros(n)
        order_imbalance = np.zeros(n)
        tick_direction = np.zeros(n)

        # VWAP distance (can calculate from OHLCV)
        close = df["close"]
        volume = df["volume"]
        cumulative_tpv = (close * volume).cumsum()
        cumulative_vol = volume.cumsum()
        vwap = cumulative_tpv / (cumulative_vol + 1e-9)
        vwap_distance = ((close - vwap) / vwap).fillna(0.0).clip(-0.05, 0.05) / 0.05

        # Volume profile rank (percentile of today's volume)
        volume_profile_rank = (
            volume.rolling(window=20, min_periods=1).rank(pct=True).fillna(0.5)
        )

        return {
            "bid_ask_spread": bid_ask_spread,
            "order_imbalance": order_imbalance,
            "tick_direction": tick_direction,
            "vwap_distance": vwap_distance.values,
            "volume_profile_rank": volume_profile_rank.values,
        }

    def calculate_sentiment_features(
        self, symbol: str, timestamp: datetime
    ) -> dict[str, float]:
        """Calculate sentiment features (3 features).

        Integrates with existing sentiment module.
        Placeholder values when data unavailable.

        Args:
            symbol: Ticker symbol
            timestamp: Current timestamp

        Returns:
            Dictionary of sentiment features
        """
        # TODO: Integrate with existing sentiment analysis module
        # For now, return neutral placeholders
        return {
            "news_sentiment": 0.0,
            "social_sentiment": 0.0,
            "options_sentiment": 0.0,
        }

    def calculate_time_features(self, timestamp: datetime) -> dict[str, float]:
        """Calculate time-based features (4 features).

        Args:
            timestamp: Current timestamp

        Returns:
            Dictionary of time features
        """
        # Hour of day (normalized to [0, 1])
        hour_of_day = timestamp.hour / 23.0

        # Day of week (0=Monday, 4=Friday, normalized to [0, 1])
        day_of_week = timestamp.weekday() / 4.0 if timestamp.weekday() < 5 else 1.0

        # Earnings proximity (placeholder - requires earnings calendar)
        days_to_earnings = 1.0  # Max value (far from earnings)
        days_from_earnings = 1.0  # Max value (far from earnings)

        return {
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "days_to_earnings": days_to_earnings,
            "days_from_earnings": days_from_earnings,
        }

    def calculate_pattern_features(
        self, df: DataFrame
    ) -> dict[str, NDArray[np.float64]]:
        """Calculate pattern-based features (6 features) and S/R features (9 features).

        Args:
            df: OHLCV DataFrame

        Returns:
            Dictionary of S/R and pattern feature arrays
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]
        n = len(df)

        # Support/Resistance features using enhanced detector
        sr_features_arrays = {
            "distance_to_nearest_support": np.full(n, -0.05),
            "distance_to_nearest_resistance": np.full(n, 0.05),
            "support_strength": np.zeros(n),
            "resistance_strength": np.zeros(n),
            "between_levels": np.zeros(n),
            "num_supports_below": np.zeros(n),
            "num_resistances_above": np.zeros(n),
            "avg_support_distance": np.full(n, -0.05),
            "avg_resistance_distance": np.full(n, 0.05),
        }

        # Calculate S/R for each bar (rolling window approach)
        for i in range(min(100, n), n):  # Start after minimum window
            lookback_df = df.iloc[:i+1]
            current_price = float(close.iloc[i])

            # Get S/R features for current price
            sr_features = self.sr_detector.get_features(lookback_df, current_price, lookback=100)

            # Store in arrays
            for key, value in sr_features.items():
                sr_features_arrays[key][i] = value

        # Trend detection (using SMA slopes)
        sma50 = close.rolling(window=50).mean()
        sma50_slope = sma50.diff(5) / sma50.shift(5)  # 5-day slope

        in_uptrend = (sma50_slope > 0.01).astype(float).fillna(0.0)
        in_downtrend = (sma50_slope < -0.01).astype(float).fillna(0.0)

        # Pattern scores (placeholder - requires pattern detection)
        bull_flag_score = np.zeros(n)
        bear_flag_score = np.zeros(n)

        # Breakout/reversal signals (simple version)
        # Breakout: Close above 20-day high with volume confirmation
        high_20 = high.rolling(window=20).max()
        volume = df["volume"]
        volume_avg = volume.rolling(window=20).mean()

        breakout_price = (close > high_20.shift(1)).astype(float)
        breakout_volume = (volume > volume_avg * 1.3).astype(float)
        breakout_signal = (breakout_price * breakout_volume).fillna(0.0).values

        # Reversal: Mean reversion from extremes
        returns_5d = close.pct_change(5)
        reversal_signal = (
            -returns_5d.fillna(0.0).clip(-0.2, 0.2) / 0.2
        ).values  # Contrarian

        return {
            # S/R features (9)
            "distance_to_nearest_support": sr_features_arrays["distance_to_nearest_support"],
            "distance_to_nearest_resistance": sr_features_arrays["distance_to_nearest_resistance"],
            "support_strength": sr_features_arrays["support_strength"],
            "resistance_strength": sr_features_arrays["resistance_strength"],
            "between_levels": sr_features_arrays["between_levels"],
            "num_supports_below": sr_features_arrays["num_supports_below"],
            "num_resistances_above": sr_features_arrays["num_resistances_above"],
            "avg_support_distance": sr_features_arrays["avg_support_distance"],
            "avg_resistance_distance": sr_features_arrays["avg_resistance_distance"],
            # Pattern features (6)
            "in_uptrend": in_uptrend.values,
            "in_downtrend": in_downtrend.values,
            "bull_flag_score": bull_flag_score,
            "bear_flag_score": bear_flag_score,
            "breakout_signal": breakout_signal,
            "reversal_signal": reversal_signal,
        }

    def extract(
        self,
        df: DataFrame,
        symbol: str,
        timestamp: datetime | None = None,
    ) -> list[FeatureSet]:
        """Extract feature sets for each bar in DataFrame.

        Args:
            df: OHLCV DataFrame with columns: open, high, low, close, volume
            symbol: Ticker symbol
            timestamp: Optional override timestamp (uses index if None)

        Returns:
            List of FeatureSet objects (one per bar)
        """
        # Calculate all feature categories
        price_features = self.calculate_price_features(df)
        technical_features = self.technical_calc.calculate_all(df)
        microstructure_features = self.calculate_microstructure_features(df)
        pattern_features = self.calculate_pattern_features(df)

        # Build feature sets for each bar
        feature_sets = []
        for i in range(len(df)):
            # Use index timestamp or provided timestamp
            if timestamp is None:
                if isinstance(df.index, pd.DatetimeIndex):
                    bar_timestamp = df.index[i].to_pydatetime()
                else:
                    bar_timestamp = datetime.utcnow()
            else:
                bar_timestamp = timestamp

            # Get sentiment and time features (constant per bar)
            sentiment_features = self.calculate_sentiment_features(
                symbol, bar_timestamp
            )
            time_features = self.calculate_time_features(bar_timestamp)

            # Build FeatureSet
            features = FeatureSet(
                timestamp=bar_timestamp,
                symbol=symbol,
                # Price features
                returns_1d=float(price_features["returns_1d"][i]),
                returns_5d=float(price_features["returns_5d"][i]),
                returns_20d=float(price_features["returns_20d"][i]),
                volatility_20d=float(price_features["volatility_20d"][i]),
                volume_ratio=float(price_features["volume_ratio"][i]),
                high_low_range=float(price_features["high_low_range"][i]),
                close_to_high=float(price_features["close_to_high"][i]),
                price_to_sma20=float(price_features["price_to_sma20"][i]),
                price_to_sma50=float(price_features["price_to_sma50"][i]),
                price_to_vwap=float(price_features["price_to_vwap"][i]),
                # Technical indicators
                rsi_14=float(technical_features["rsi_14"][i]),
                macd=float(technical_features["macd"][i]),
                macd_signal=float(technical_features["macd_signal"][i]),
                macd_histogram=float(technical_features["macd_histogram"][i]),
                stoch_k=float(technical_features["stoch_k"][i]),
                stoch_d=float(technical_features["stoch_d"][i]),
                atr_14=float(technical_features["atr_14"][i]),
                adx_14=float(technical_features["adx_14"][i]),
                cci_20=float(technical_features["cci_20"][i]),
                williams_r=float(technical_features["williams_r"][i]),
                roc_10=float(technical_features["roc_10"][i]),
                momentum_20=float(technical_features["momentum_20"][i]),
                bollinger_pct=float(technical_features["bollinger_pct"][i]),
                keltner_pct=float(technical_features["keltner_pct"][i]),
                donchian_pct=float(technical_features["donchian_pct"][i]),
                # Microstructure
                bid_ask_spread=float(microstructure_features["bid_ask_spread"][i]),
                order_imbalance=float(microstructure_features["order_imbalance"][i]),
                tick_direction=float(microstructure_features["tick_direction"][i]),
                vwap_distance=float(microstructure_features["vwap_distance"][i]),
                volume_profile_rank=float(
                    microstructure_features["volume_profile_rank"][i]
                ),
                # Sentiment
                news_sentiment=sentiment_features["news_sentiment"],
                social_sentiment=sentiment_features["social_sentiment"],
                options_sentiment=sentiment_features["options_sentiment"],
                # Time features
                hour_of_day=time_features["hour_of_day"],
                day_of_week=time_features["day_of_week"],
                days_to_earnings=time_features["days_to_earnings"],
                days_from_earnings=time_features["days_from_earnings"],
                # Support/Resistance features
                distance_to_nearest_support=float(pattern_features["distance_to_nearest_support"][i]),
                distance_to_nearest_resistance=float(pattern_features["distance_to_nearest_resistance"][i]),
                support_strength=float(pattern_features["support_strength"][i]),
                resistance_strength=float(pattern_features["resistance_strength"][i]),
                between_levels=float(pattern_features["between_levels"][i]),
                num_supports_below=float(pattern_features["num_supports_below"][i]),
                num_resistances_above=float(pattern_features["num_resistances_above"][i]),
                avg_support_distance=float(pattern_features["avg_support_distance"][i]),
                avg_resistance_distance=float(pattern_features["avg_resistance_distance"][i]),
                # Pattern features
                in_uptrend=float(pattern_features["in_uptrend"][i]),
                in_downtrend=float(pattern_features["in_downtrend"][i]),
                bull_flag_score=float(pattern_features["bull_flag_score"][i]),
                bear_flag_score=float(pattern_features["bear_flag_score"][i]),
                breakout_signal=float(pattern_features["breakout_signal"][i]),
                reversal_signal=float(pattern_features["reversal_signal"][i]),
            )

            feature_sets.append(features)

        return feature_sets

    def extract_latest(
        self,
        df: DataFrame,
        symbol: str,
        timestamp: datetime | None = None,
    ) -> FeatureSet:
        """Extract features for the latest bar only.

        More efficient than extract() when you only need the most recent features.

        Args:
            df: OHLCV DataFrame
            symbol: Ticker symbol
            timestamp: Optional override timestamp

        Returns:
            FeatureSet for latest bar
        """
        feature_sets = self.extract(df, symbol, timestamp)
        return feature_sets[-1]
