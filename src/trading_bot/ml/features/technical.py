"""Technical indicator feature calculations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from numpy.typing import NDArray

if TYPE_CHECKING:
    from pandas import DataFrame, Series


class TechnicalFeatureCalculator:
    """Calculate technical indicator features from OHLCV data.

    Computes 15 technical indicators:
    - RSI (14)
    - MACD (12, 26, 9)
    - Stochastic Oscillator (14, 3)
    - ATR (14)
    - ADX (14)
    - CCI (20)
    - Williams %R (14)
    - ROC (10)
    - Momentum (20)
    - Bollinger Bands (20, 2)
    - Keltner Channel (20, 2)
    - Donchian Channel (20)

    All outputs normalized to [-1, 1] or [0, 1] ranges.
    """

    def __init__(self) -> None:
        """Initialize calculator."""
        pass

    def calculate_rsi(
        self, prices: Series, period: int = 14
    ) -> NDArray[np.float64]:
        """Calculate RSI (Relative Strength Index).

        Args:
            prices: Close prices
            period: RSI period (default: 14)

        Returns:
            RSI values (0-100), normalized to [0, 1]
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # Normalize to [0, 1]
        return (rsi / 100.0).fillna(0.5).values

    def calculate_macd(
        self,
        prices: Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
        """Calculate MACD (Moving Average Convergence Divergence).

        Args:
            prices: Close prices
            fast: Fast EMA period (default: 12)
            slow: Slow EMA period (default: 26)
            signal: Signal line period (default: 9)

        Returns:
            Tuple of (macd_line, signal_line, histogram) normalized
        """
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        # Normalize by price
        price_std = prices.rolling(window=50).std()
        macd_norm = (macd_line / price_std).fillna(0.0).clip(-3, 3) / 3.0
        signal_norm = (signal_line / price_std).fillna(0.0).clip(-3, 3) / 3.0
        hist_norm = (histogram / price_std).fillna(0.0).clip(-3, 3) / 3.0

        return macd_norm.values, signal_norm.values, hist_norm.values

    def calculate_stochastic(
        self, high: Series, low: Series, close: Series, k_period: int = 14, d_period: int = 3
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Calculate Stochastic Oscillator.

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            k_period: %K period (default: 14)
            d_period: %D period (default: 3)

        Returns:
            Tuple of (%K, %D) normalized to [0, 1]
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()

        # Normalize to [0, 1]
        k_norm = (k / 100.0).fillna(0.5)
        d_norm = (d / 100.0).fillna(0.5)

        return k_norm.values, d_norm.values

    def calculate_atr(
        self, high: Series, low: Series, close: Series, period: int = 14
    ) -> NDArray[np.float64]:
        """Calculate ATR (Average True Range).

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period (default: 14)

        Returns:
            ATR values normalized by price
        """
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        # Normalize by price (ATR as % of price)
        atr_pct = (atr / close).fillna(0.0).clip(0, 0.2) / 0.2

        return atr_pct.values

    def calculate_adx(
        self, high: Series, low: Series, close: Series, period: int = 14
    ) -> NDArray[np.float64]:
        """Calculate ADX (Average Directional Index).

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ADX period (default: 14)

        Returns:
            ADX values (0-100), normalized to [0, 1]
        """
        # Calculate +DM and -DM
        up_move = high.diff()
        down_move = -low.diff()

        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)

        # Calculate ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Smooth with Wilder's method
        atr = true_range.ewm(alpha=1 / period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)

        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(alpha=1 / period, adjust=False).mean()

        # Normalize to [0, 1]
        adx_norm = (adx / 100.0).fillna(0.0).clip(0, 1)

        return adx_norm.values

    def calculate_cci(
        self, high: Series, low: Series, close: Series, period: int = 20
    ) -> NDArray[np.float64]:
        """Calculate CCI (Commodity Channel Index).

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: CCI period (default: 20)

        Returns:
            CCI values normalized to [-1, 1]
        """
        typical_price = (high + low + close) / 3
        sma = typical_price.rolling(window=period).mean()
        mean_deviation = (
            (typical_price - sma).abs().rolling(window=period).mean()
        )

        cci = (typical_price - sma) / (0.015 * mean_deviation)

        # Normalize to [-1, 1] (clipping extreme values)
        cci_norm = cci.fillna(0.0).clip(-200, 200) / 200.0

        return cci_norm.values

    def calculate_williams_r(
        self, high: Series, low: Series, close: Series, period: int = 14
    ) -> NDArray[np.float64]:
        """Calculate Williams %R.

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: Period (default: 14)

        Returns:
            Williams %R values (-100 to 0), normalized to [-1, 0]
        """
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()

        williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)

        # Normalize to [-1, 0]
        williams_norm = (williams_r / 100.0).fillna(-0.5)

        return williams_norm.values

    def calculate_roc(self, prices: Series, period: int = 10) -> NDArray[np.float64]:
        """Calculate ROC (Rate of Change).

        Args:
            prices: Close prices
            period: ROC period (default: 10)

        Returns:
            ROC values (%) normalized to [-1, 1]
        """
        roc = 100 * (prices - prices.shift(period)) / prices.shift(period)

        # Normalize to [-1, 1] (assuming ±20% max ROC)
        roc_norm = roc.fillna(0.0).clip(-20, 20) / 20.0

        return roc_norm.values

    def calculate_momentum(
        self, prices: Series, period: int = 20
    ) -> NDArray[np.float64]:
        """Calculate Momentum.

        Args:
            prices: Close prices
            period: Momentum period (default: 20)

        Returns:
            Momentum values normalized to [-1, 1]
        """
        momentum = prices - prices.shift(period)

        # Normalize by rolling std
        rolling_std = prices.rolling(window=period).std()
        momentum_norm = (momentum / rolling_std).fillna(0.0).clip(-3, 3) / 3.0

        return momentum_norm.values

    def calculate_bollinger_bands(
        self, prices: Series, period: int = 20, num_std: float = 2.0
    ) -> NDArray[np.float64]:
        """Calculate Bollinger Bands position.

        Args:
            prices: Close prices
            period: SMA period (default: 20)
            num_std: Number of standard deviations (default: 2.0)

        Returns:
            Position within bands (0-1): 0=lower, 0.5=middle, 1=upper
        """
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()

        upper_band = sma + (num_std * std)
        lower_band = sma - (num_std * std)

        # Calculate position (0-1)
        bb_position = (prices - lower_band) / (upper_band - lower_band)
        bb_position = bb_position.fillna(0.5).clip(0, 1)

        return bb_position.values

    def calculate_keltner_channel(
        self,
        high: Series,
        low: Series,
        close: Series,
        ema_period: int = 20,
        atr_period: int = 14,
        multiplier: float = 2.0,
    ) -> NDArray[np.float64]:
        """Calculate Keltner Channel position.

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            ema_period: EMA period (default: 20)
            atr_period: ATR period (default: 14)
            multiplier: ATR multiplier (default: 2.0)

        Returns:
            Position within channel (0-1)
        """
        ema = close.ewm(span=ema_period, adjust=False).mean()

        # Calculate ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=atr_period).mean()

        upper_channel = ema + (multiplier * atr)
        lower_channel = ema - (multiplier * atr)

        # Calculate position (0-1)
        kc_position = (close - lower_channel) / (upper_channel - lower_channel)
        kc_position = kc_position.fillna(0.5).clip(0, 1)

        return kc_position.values

    def calculate_donchian_channel(
        self, high: Series, low: Series, close: Series, period: int = 20
    ) -> NDArray[np.float64]:
        """Calculate Donchian Channel position.

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: Channel period (default: 20)

        Returns:
            Position within channel (0-1)
        """
        upper_channel = high.rolling(window=period).max()
        lower_channel = low.rolling(window=period).min()

        # Calculate position (0-1)
        dc_position = (close - lower_channel) / (upper_channel - lower_channel)
        dc_position = dc_position.fillna(0.5).clip(0, 1)

        return dc_position.values

    def calculate_all(
        self, df: DataFrame
    ) -> dict[str, NDArray[np.float64]]:
        """Calculate all technical indicators.

        Args:
            df: OHLCV DataFrame with columns: open, high, low, close, volume

        Returns:
            Dictionary of technical indicator arrays
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # Calculate all indicators
        rsi = self.calculate_rsi(close)
        macd, macd_signal, macd_hist = self.calculate_macd(close)
        stoch_k, stoch_d = self.calculate_stochastic(high, low, close)
        atr = self.calculate_atr(high, low, close)
        adx = self.calculate_adx(high, low, close)
        cci = self.calculate_cci(high, low, close)
        williams_r = self.calculate_williams_r(high, low, close)
        roc = self.calculate_roc(close)
        momentum = self.calculate_momentum(close)
        bb_pct = self.calculate_bollinger_bands(close)
        kc_pct = self.calculate_keltner_channel(high, low, close)
        dc_pct = self.calculate_donchian_channel(high, low, close)

        return {
            "rsi_14": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
            "macd_histogram": macd_hist,
            "stoch_k": stoch_k,
            "stoch_d": stoch_d,
            "atr_14": atr,
            "adx_14": adx,
            "cci_20": cci,
            "williams_r": williams_r,
            "roc_10": roc,
            "momentum_20": momentum,
            "bollinger_pct": bb_pct,
            "keltner_pct": kc_pct,
            "donchian_pct": dc_pct,
        }
