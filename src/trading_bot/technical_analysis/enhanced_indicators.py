"""Enhanced Technical Indicators - Tools 5-13 from the TA framework.

Provides all quantifiable indicators:
- Moving Averages (EMA/SMA) - Tool 5
- RSI (Relative Strength Index) - Tool 6
- MACD - Tool 7
- Stochastic / Stoch RSI - Tool 8
- ATR (Average True Range) - Tool 9
- Bollinger Bands - Tool 10
- Volume & Volume Spikes - Tool 11
- OBV (On-Balance Volume) - Tool 12
- Volume Profile / Market Profile - Tool 13

All indicators return structured data with clear interpretation.
No astrology with candles - just math.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class MovingAverageResult:
    """Moving average analysis result."""
    sma_20: float
    sma_50: float
    sma_200: float
    ema_20: float
    ema_50: float
    ema_200: float
    price: float
    above_sma_20: bool
    above_sma_50: bool
    above_sma_200: bool
    ma_alignment: str  # 'bullish', 'bearish', 'mixed'
    golden_cross: bool  # SMA50 > SMA200 and recent cross
    death_cross: bool   # SMA50 < SMA200 and recent cross


@dataclass
class RSIResult:
    """RSI analysis result."""
    rsi: float
    bullish_bias: bool  # RSI > 50
    oversold: bool      # RSI < 30
    overbought: bool    # RSI > 70
    divergence: Optional[str]  # 'bullish', 'bearish', None


@dataclass
class MACDResult:
    """MACD analysis result."""
    macd_line: float
    signal_line: float
    histogram: float
    bullish: bool       # MACD > signal
    cross_up: bool      # Recent bullish cross
    cross_down: bool    # Recent bearish cross
    histogram_expanding: bool


@dataclass
class StochasticResult:
    """Stochastic oscillator result."""
    k: float
    d: float
    oversold: bool      # K < 20
    overbought: bool    # K > 80
    bullish_cross: bool # K crosses above D


@dataclass
class ATRResult:
    """ATR (volatility) result."""
    atr: float
    atr_percent: float  # ATR as % of price
    volatility_regime: str  # 'low', 'normal', 'high', 'extreme'


@dataclass
class BollingerBandsResult:
    """Bollinger Bands result."""
    upper: float
    middle: float
    lower: float
    bandwidth: float    # (upper - lower) / middle
    percent_b: float    # Where price is within bands
    squeeze: bool       # Bandwidth < 20-period average
    expansion: bool     # Bandwidth > 20-period average


@dataclass
class VolumeResult:
    """Volume analysis result."""
    current_volume: float
    avg_volume: float
    volume_ratio: float  # current / average
    spike: bool         # Volume > 2x average
    climax: bool        # Volume > 3x average + price extreme


@dataclass
class OBVResult:
    """On-Balance Volume result."""
    obv: float
    obv_ma: float       # 20-period MA of OBV
    obv_rising: bool
    divergence: Optional[str]  # 'bullish', 'bearish', None


@dataclass
class VolumeProfileResult:
    """Volume Profile / POC (Point of Control) result."""
    poc: float          # Price level with highest volume
    value_area_high: float  # High of value area (70% volume)
    value_area_low: float   # Low of value area
    high_volume_nodes: List[float]  # Price levels with high volume
    low_volume_nodes: List[float]   # Price levels with low volume (gaps)


class EnhancedIndicators:
    """Calculate all technical indicators with proper interpretation.

    No magic, no astrology - just quantifiable signals you can backtest.
    Each method returns structured data with clear buy/sell implications.
    """

    def __init__(self):
        """Initialize indicator calculator."""
        pass

    # Tool 5: Moving Averages
    def calculate_moving_averages(
        self,
        df: pd.DataFrame,
        price_col: str = 'close'
    ) -> MovingAverageResult:
        """Calculate moving averages and alignment.

        Args:
            df: DataFrame with OHLCV data
            price_col: Column name for price (default: 'close')

        Returns:
            MovingAverageResult with all MA data

        Interpretation:
            - Bullish alignment: price > SMA20 > SMA50 > SMA200
            - Golden cross: SMA50 crosses above SMA200 (bullish)
            - Death cross: SMA50 crosses below SMA200 (bearish)
        """
        prices = df[price_col]
        current_price = float(prices.iloc[-1])

        # Calculate SMAs
        sma_20 = float(prices.rolling(window=20).mean().iloc[-1])
        sma_50 = float(prices.rolling(window=50).mean().iloc[-1])
        sma_200 = float(prices.rolling(window=200).mean().iloc[-1])

        # Calculate EMAs
        ema_20 = float(prices.ewm(span=20, adjust=False).mean().iloc[-1])
        ema_50 = float(prices.ewm(span=50, adjust=False).mean().iloc[-1])
        ema_200 = float(prices.ewm(span=200, adjust=False).mean().iloc[-1])

        # Check alignment
        above_sma_20 = current_price > sma_20
        above_sma_50 = current_price > sma_50
        above_sma_200 = current_price > sma_200

        # Determine MA alignment
        if above_sma_20 and sma_20 > sma_50 and sma_50 > sma_200:
            ma_alignment = 'bullish'
        elif not above_sma_20 and sma_20 < sma_50 and sma_50 < sma_200:
            ma_alignment = 'bearish'
        else:
            ma_alignment = 'mixed'

        # Detect crosses (check last 3 periods)
        sma_50_series = prices.rolling(window=50).mean()
        sma_200_series = prices.rolling(window=200).mean()

        golden_cross = False
        death_cross = False

        if len(df) >= 203:  # Need enough data
            # Check if SMA50 crossed above SMA200 in last 3 periods
            for i in range(1, 4):
                if (sma_50_series.iloc[-i-1] <= sma_200_series.iloc[-i-1] and
                    sma_50_series.iloc[-i] > sma_200_series.iloc[-i]):
                    golden_cross = True
                    break
                if (sma_50_series.iloc[-i-1] >= sma_200_series.iloc[-i-1] and
                    sma_50_series.iloc[-i] < sma_200_series.iloc[-i]):
                    death_cross = True
                    break

        return MovingAverageResult(
            sma_20=sma_20,
            sma_50=sma_50,
            sma_200=sma_200,
            ema_20=ema_20,
            ema_50=ema_50,
            ema_200=ema_200,
            price=current_price,
            above_sma_20=above_sma_20,
            above_sma_50=above_sma_50,
            above_sma_200=above_sma_200,
            ma_alignment=ma_alignment,
            golden_cross=golden_cross,
            death_cross=death_cross
        )

    # Tool 6: RSI
    def calculate_rsi(
        self,
        df: pd.DataFrame,
        period: int = 14,
        price_col: str = 'close'
    ) -> RSIResult:
        """Calculate RSI with proper interpretation.

        Args:
            df: DataFrame with price data
            period: RSI period (default: 14)
            price_col: Price column name

        Returns:
            RSIResult with RSI value and signals

        Interpretation:
            - RSI > 50: Bullish bias
            - RSI < 50: Bearish bias
            - RSI < 30: Oversold (but can stay there in downtrend!)
            - RSI > 70: Overbought (but can stay there in uptrend!)
            - Divergence: Price makes new high but RSI doesn't = warning
        """
        prices = df[price_col]

        # Calculate RSI
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = float(rsi.iloc[-1])

        # Detect divergence (compare last 2 significant swings)
        divergence = None
        if len(df) >= period * 3:
            # Find recent price highs/lows
            price_peaks = (prices > prices.shift(1)) & (prices > prices.shift(-1))
            rsi_peaks = (rsi > rsi.shift(1)) & (rsi > rsi.shift(-1))

            recent_price_peaks = prices[price_peaks].tail(2)
            recent_rsi_peaks = rsi[rsi_peaks].tail(2)

            if len(recent_price_peaks) >= 2 and len(recent_rsi_peaks) >= 2:
                # Bearish divergence: price higher high, RSI lower high
                if (recent_price_peaks.iloc[-1] > recent_price_peaks.iloc[-2] and
                    recent_rsi_peaks.iloc[-1] < recent_rsi_peaks.iloc[-2]):
                    divergence = 'bearish'
                # Bullish divergence: price lower low, RSI higher low
                elif (recent_price_peaks.iloc[-1] < recent_price_peaks.iloc[-2] and
                      recent_rsi_peaks.iloc[-1] > recent_rsi_peaks.iloc[-2]):
                    divergence = 'bullish'

        return RSIResult(
            rsi=current_rsi,
            bullish_bias=current_rsi > 50,
            oversold=current_rsi < 30,
            overbought=current_rsi > 70,
            divergence=divergence
        )

    # Tool 7: MACD
    def calculate_macd(
        self,
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        price_col: str = 'close'
    ) -> MACDResult:
        """Calculate MACD with trend + momentum interpretation.

        Args:
            df: DataFrame with price data
            fast: Fast EMA period (default: 12)
            slow: Slow EMA period (default: 26)
            signal: Signal line period (default: 9)
            price_col: Price column name

        Returns:
            MACDResult with MACD values and signals

        Interpretation:
            - MACD > signal line: Bullish
            - MACD crosses above signal: Buy signal (in uptrend!)
            - Histogram expanding: Momentum increasing
            - Use with higher-TF trend filter!
        """
        prices = df[price_col]

        # Calculate MACD
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        current_macd = float(macd_line.iloc[-1])
        current_signal = float(signal_line.iloc[-1])
        current_histogram = float(histogram.iloc[-1])

        # Detect crosses (last 2 periods)
        cross_up = False
        cross_down = False

        if len(df) >= slow + signal:
            if (macd_line.iloc[-2] <= signal_line.iloc[-2] and
                macd_line.iloc[-1] > signal_line.iloc[-1]):
                cross_up = True
            elif (macd_line.iloc[-2] >= signal_line.iloc[-2] and
                  macd_line.iloc[-1] < signal_line.iloc[-1]):
                cross_down = True

        # Check if histogram is expanding
        histogram_expanding = False
        if len(histogram) >= 3:
            histogram_expanding = abs(histogram.iloc[-1]) > abs(histogram.iloc[-2])

        return MACDResult(
            macd_line=current_macd,
            signal_line=current_signal,
            histogram=current_histogram,
            bullish=current_macd > current_signal,
            cross_up=cross_up,
            cross_down=cross_down,
            histogram_expanding=histogram_expanding
        )

    # Tool 8: Stochastic
    def calculate_stochastic(
        self,
        df: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3
    ) -> StochasticResult:
        """Calculate Stochastic Oscillator.

        Args:
            df: DataFrame with OHLC data
            k_period: %K period (default: 14)
            d_period: %D smoothing period (default: 3)

        Returns:
            StochasticResult with stochastic values

        Interpretation:
            - Best in ranging markets
            - Buy oversold (<20) near support
            - Sell overbought (>80) near resistance
            - In strong trends, stays pinned - DON'T FIGHT THE TREND
        """
        high = df['high']
        low = df['low']
        close = df['close']

        # Calculate %K
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k = 100 * ((close - lowest_low) / (highest_high - lowest_low))

        # Calculate %D (smoothed %K)
        d = k.rolling(window=d_period).mean()

        current_k = float(k.iloc[-1])
        current_d = float(d.iloc[-1])

        # Detect bullish cross
        bullish_cross = False
        if len(df) >= k_period + d_period:
            if k.iloc[-2] <= d.iloc[-2] and k.iloc[-1] > d.iloc[-1]:
                bullish_cross = True

        return StochasticResult(
            k=current_k,
            d=current_d,
            oversold=current_k < 20,
            overbought=current_k > 80,
            bullish_cross=bullish_cross
        )

    # Tool 9: ATR (Average True Range)
    def calculate_atr(
        self,
        df: pd.DataFrame,
        period: int = 14
    ) -> ATRResult:
        """Calculate ATR (volatility measure).

        Args:
            df: DataFrame with OHLC data
            period: ATR period (default: 14)

        Returns:
            ATRResult with volatility metrics

        Usage:
            - Position sizing: Smaller size when ATR is high
            - Stop placement: 1.5-3x ATR beyond entry
            - Breakout validation: Higher ATR = more significant move
        """
        high = df['high']
        low = df['low']
        close = df['close']

        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Calculate ATR
        atr = tr.rolling(window=period).mean()
        current_atr = float(atr.iloc[-1])
        current_price = float(close.iloc[-1])

        # ATR as percentage of price
        atr_percent = (current_atr / current_price) * 100

        # Determine volatility regime
        atr_ma = atr.rolling(window=50).mean()
        avg_atr = float(atr_ma.iloc[-1]) if len(atr_ma) >= 50 else current_atr

        if current_atr < avg_atr * 0.7:
            volatility_regime = 'low'
        elif current_atr < avg_atr * 1.3:
            volatility_regime = 'normal'
        elif current_atr < avg_atr * 2.0:
            volatility_regime = 'high'
        else:
            volatility_regime = 'extreme'

        return ATRResult(
            atr=current_atr,
            atr_percent=atr_percent,
            volatility_regime=volatility_regime
        )

    # Tool 10: Bollinger Bands
    def calculate_bollinger_bands(
        self,
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
        price_col: str = 'close'
    ) -> BollingerBandsResult:
        """Calculate Bollinger Bands.

        Args:
            df: DataFrame with price data
            period: BB period (default: 20)
            std_dev: Standard deviations (default: 2.0)
            price_col: Price column name

        Returns:
            BollingerBandsResult with bands and squeeze/expansion

        Interpretation:
            - Squeeze (tight bands): Volatility contraction → expansion coming
            - Price at upper band in uptrend: Strength, not necessarily reversal
            - Price at lower band in downtrend: Weakness, not necessarily bounce
            - Use with trend context!
        """
        prices = df[price_col]

        # Calculate middle band (SMA)
        middle = prices.rolling(window=period).mean()

        # Calculate standard deviation
        std = prices.rolling(window=period).std()

        # Calculate bands
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        current_price = float(prices.iloc[-1])
        current_upper = float(upper.iloc[-1])
        current_middle = float(middle.iloc[-1])
        current_lower = float(lower.iloc[-1])

        # Calculate bandwidth
        bandwidth = (current_upper - current_lower) / current_middle

        # Calculate %B (where price is within bands)
        percent_b = (current_price - current_lower) / (current_upper - current_lower)

        # Detect squeeze/expansion
        bandwidth_series = (upper - lower) / middle
        avg_bandwidth = float(bandwidth_series.rolling(window=period).mean().iloc[-1])

        squeeze = bandwidth < avg_bandwidth * 0.7
        expansion = bandwidth > avg_bandwidth * 1.3

        return BollingerBandsResult(
            upper=current_upper,
            middle=current_middle,
            lower=current_lower,
            bandwidth=bandwidth,
            percent_b=percent_b,
            squeeze=squeeze,
            expansion=expansion
        )

    # Tool 11: Volume Analysis
    def calculate_volume(
        self,
        df: pd.DataFrame,
        period: int = 20
    ) -> VolumeResult:
        """Analyze volume for confirmation.

        Args:
            df: DataFrame with volume data
            period: Average volume period (default: 20)

        Returns:
            VolumeResult with volume metrics

        Interpretation:
            - Breakouts need volume confirmation
            - Volume spike at top/bottom = climax/exhaustion
            - Rising volume in trend = healthy
            - Falling volume in trend = weakening
        """
        volume = df['volume']
        close = df['close']

        current_volume = float(volume.iloc[-1])
        avg_volume = float(volume.rolling(window=period).mean().iloc[-1])

        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Detect spikes
        spike = volume_ratio > 2.0

        # Detect climax (huge volume + price extreme)
        climax = False
        if spike and volume_ratio > 3.0:
            # Check if price is at extreme (near recent high/low)
            recent_high = close.rolling(window=period).max().iloc[-1]
            recent_low = close.rolling(window=period).min().iloc[-1]
            current_price = close.iloc[-1]

            price_range = recent_high - recent_low
            if price_range > 0:
                price_position = (current_price - recent_low) / price_range
                # Climax if at top (>0.9) or bottom (<0.1)
                climax = price_position > 0.9 or price_position < 0.1

        return VolumeResult(
            current_volume=current_volume,
            avg_volume=avg_volume,
            volume_ratio=volume_ratio,
            spike=spike,
            climax=climax
        )

    # Tool 12: OBV (On-Balance Volume)
    def calculate_obv(
        self,
        df: pd.DataFrame,
        ma_period: int = 20
    ) -> OBVResult:
        """Calculate On-Balance Volume.

        Args:
            df: DataFrame with price and volume
            ma_period: OBV moving average period (default: 20)

        Returns:
            OBVResult with OBV metrics

        Interpretation:
            - OBV rising + price flat: Stealth accumulation (bullish)
            - OBV falling + price flat: Distribution (bearish)
            - Divergence between price and OBV warns of reversal
        """
        close = df['close']
        volume = df['volume']

        # Calculate OBV
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()

        current_obv = float(obv.iloc[-1])

        # OBV moving average
        obv_ma = obv.rolling(window=ma_period).mean()
        current_obv_ma = float(obv_ma.iloc[-1])

        # Check if OBV is rising
        obv_rising = current_obv > current_obv_ma

        # Detect divergence (simplified)
        divergence = None
        if len(df) >= ma_period * 2:
            # Compare last 20-period price trend vs OBV trend
            price_change = (close.iloc[-1] - close.iloc[-ma_period]) / close.iloc[-ma_period]
            obv_change = (obv.iloc[-1] - obv.iloc[-ma_period]) / abs(obv.iloc[-ma_period])

            # Bullish divergence: price down, OBV up
            if price_change < -0.05 and obv_change > 0.05:
                divergence = 'bullish'
            # Bearish divergence: price up, OBV down
            elif price_change > 0.05 and obv_change < -0.05:
                divergence = 'bearish'

        return OBVResult(
            obv=current_obv,
            obv_ma=current_obv_ma,
            obv_rising=obv_rising,
            divergence=divergence
        )

    # Tool 13: Volume Profile (simplified POC)
    def calculate_volume_profile(
        self,
        df: pd.DataFrame,
        num_bins: int = 24
    ) -> VolumeProfileResult:
        """Calculate Volume Profile and Point of Control.

        Args:
            df: DataFrame with OHLC and volume
            num_bins: Number of price bins (default: 24)

        Returns:
            VolumeProfileResult with POC and value areas

        Interpretation:
            - POC (Point of Control): Price with most volume = acceptance
            - Value Area: Where 70% of volume traded
            - Low volume nodes: Likely rejection/bounce areas
            - Use for support/resistance and targets
        """
        close = df['close']
        volume = df['volume']

        price_min = close.min()
        price_max = close.max()

        # Create price bins
        bins = np.linspace(price_min, price_max, num_bins)
        bin_indices = np.digitize(close, bins)

        # Sum volume for each bin
        volume_by_bin = {}
        for i in range(len(bin_indices)):
            bin_idx = bin_indices[i]
            if bin_idx in volume_by_bin:
                volume_by_bin[bin_idx] += volume.iloc[i]
            else:
                volume_by_bin[bin_idx] = volume.iloc[i]

        # Find POC (bin with highest volume)
        poc_bin = max(volume_by_bin, key=volume_by_bin.get)
        poc = float((bins[poc_bin-1] + bins[min(poc_bin, len(bins)-1)]) / 2)

        # Find value area (70% of volume)
        total_volume = sum(volume_by_bin.values())
        sorted_bins = sorted(volume_by_bin.items(), key=lambda x: x[1], reverse=True)

        cumulative_volume = 0
        value_area_bins = []
        for bin_idx, vol in sorted_bins:
            cumulative_volume += vol
            value_area_bins.append(bin_idx)
            if cumulative_volume >= total_volume * 0.7:
                break

        value_area_bins = sorted(value_area_bins)
        value_area_low = float(bins[value_area_bins[0]-1])
        value_area_high = float(bins[min(value_area_bins[-1], len(bins)-1)])

        # Find high volume nodes (top 30% of bins)
        threshold_high = sorted([v for v in volume_by_bin.values()], reverse=True)[int(len(volume_by_bin) * 0.3)]
        high_volume_nodes = [
            float((bins[b-1] + bins[min(b, len(bins)-1)]) / 2)
            for b, v in volume_by_bin.items()
            if v >= threshold_high
        ]

        # Find low volume nodes (bottom 20% of bins)
        threshold_low = sorted([v for v in volume_by_bin.values()])[int(len(volume_by_bin) * 0.2)]
        low_volume_nodes = [
            float((bins[b-1] + bins[min(b, len(bins)-1)]) / 2)
            for b, v in volume_by_bin.items()
            if v <= threshold_low
        ]

        return VolumeProfileResult(
            poc=poc,
            value_area_high=value_area_high,
            value_area_low=value_area_low,
            high_volume_nodes=high_volume_nodes,
            low_volume_nodes=low_volume_nodes
        )
