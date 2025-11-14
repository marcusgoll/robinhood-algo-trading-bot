"""Regime Detector - Tool 4 from TA framework.

Two different market regimes require different strategies:
- Breakout Regime: Price keeps running after ranges
- Mean Reversion Regime: Price snaps back toward average

Don't run a pure mean-reversion system in a strong trendy market.
Don't chase breakouts in choppy, mean-reverting conditions.

If you don't know which regime you're in, you're guessing.
"""

import numpy as np
import pandas as pd
from typing import Optional
from dataclasses import dataclass


@dataclass
class RegimeResult:
    """Market regime analysis result."""
    regime: str  # 'breakout', 'mean_reversion', 'transitional'
    confidence: float  # 0-100
    regime_strength: float  # 0-100, how strong the regime is
    metrics: dict  # Supporting metrics
    recommendation: str  # Trading approach for this regime


class RegimeDetector:
    """Detect whether market is in breakout or mean reversion regime.

    Uses multiple factors:
    - ADX (trend strength)
    - Bollinger Band behavior
    - Range expansion/contraction
    - Breakout success rate
    - Price vs moving averages
    """

    def __init__(
        self,
        breakout_threshold: float = 60.0,
        mean_reversion_threshold: float = 40.0
    ):
        """Initialize regime detector.

        Args:
            breakout_threshold: Score above this = breakout regime
            mean_reversion_threshold: Score below this = mean reversion regime
        """
        self.breakout_threshold = breakout_threshold
        self.mean_reversion_threshold = mean_reversion_threshold

    def detect(
        self,
        df: pd.DataFrame,
        lookback: int = 50
    ) -> RegimeResult:
        """Detect current market regime.

        Args:
            df: DataFrame with OHLCV data
            lookback: Number of periods to analyze

        Returns:
            RegimeResult with regime classification

        Algorithm:
            1. Calculate ADX (trend strength)
            2. Analyze BB behavior (squeezes vs expansions)
            3. Calculate range metrics (expanding vs contracting)
            4. Test breakout success rate
            5. Check price vs MA (trending vs oscillating)
            6. Combine into regime score
        """
        if len(df) < lookback:
            return self._default_result()

        metrics = {}

        # 1. ADX - Trend strength indicator
        adx_score = self._calculate_adx_score(df, lookback)
        metrics['adx_score'] = adx_score

        # 2. Bollinger Bands behavior
        bb_score = self._calculate_bb_score(df, lookback)
        metrics['bb_score'] = bb_score

        # 3. Range expansion/contraction
        range_score = self._calculate_range_score(df, lookback)
        metrics['range_score'] = range_score

        # 4. Breakout success rate
        breakout_score = self._calculate_breakout_success(df, lookback)
        metrics['breakout_success'] = breakout_score

        # 5. Price vs MA oscillation
        ma_score = self._calculate_ma_oscillation_score(df, lookback)
        metrics['ma_score'] = ma_score

        # Combine scores (weighted average)
        # ADX and breakout success are most important
        regime_score = (
            adx_score * 0.3 +
            bb_score * 0.2 +
            range_score * 0.2 +
            breakout_score * 0.2 +
            ma_score * 0.1
        )

        metrics['regime_score'] = regime_score

        # Determine regime
        if regime_score >= self.breakout_threshold:
            regime = 'breakout'
            recommendation = (
                "Trade breakouts with trend. Use trend-following strategies. "
                "Don't fade moves. Let winners run."
            )
        elif regime_score <= self.mean_reversion_threshold:
            regime = 'mean_reversion'
            recommendation = (
                "Fade extremes back to mean. Buy dips near support, "
                "sell rallies near resistance. Take profits quickly."
            )
        else:
            regime = 'transitional'
            recommendation = (
                "Mixed regime. Reduce position sizes. "
                "Wait for clearer regime or use hybrid approach."
            )

        # Calculate confidence based on distance from thresholds
        if regime == 'breakout':
            confidence = min(100, (regime_score - self.breakout_threshold) * 2 + 50)
        elif regime == 'mean_reversion':
            confidence = min(100, (self.mean_reversion_threshold - regime_score) * 2 + 50)
        else:
            # Transitional - low confidence
            confidence = 40.0

        return RegimeResult(
            regime=regime,
            confidence=confidence,
            regime_strength=abs(regime_score - 50) * 2,  # 0-100
            metrics=metrics,
            recommendation=recommendation
        )

    def _calculate_adx_score(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> float:
        """Calculate ADX-based score (0-100).

        Higher ADX = trending (breakout regime)
        Lower ADX = ranging (mean reversion regime)
        """
        high = df['high'].tail(lookback)
        low = df['low'].tail(lookback)
        close = df['close'].tail(lookback)

        # Calculate +DM and -DM
        high_diff = high.diff()
        low_diff = -low.diff()

        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Smooth with 14-period average
        period = 14
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        current_adx = adx.iloc[-1] if len(adx) > 0 and not np.isnan(adx.iloc[-1]) else 20

        # Convert ADX to score
        # ADX > 40 = strong trend (breakout regime)
        # ADX < 20 = weak trend (mean reversion regime)
        if current_adx >= 40:
            score = 80 + min(20, (current_adx - 40) / 2)
        elif current_adx <= 20:
            score = 20 - min(20, (20 - current_adx))
        else:
            # Linear interpolation between 20 and 80
            score = 20 + ((current_adx - 20) / 20) * 60

        return float(score)

    def _calculate_bb_score(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> float:
        """Calculate Bollinger Bands behavior score (0-100).

        Breakout regime: Bands expanding, price at/beyond bands
        Mean reversion regime: Bands contracting, price oscillating within bands
        """
        close = df['close'].tail(lookback)

        # Calculate BB
        period = 20
        sma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        upper = sma + (2 * std)
        lower = sma - (2 * std)

        # Calculate bandwidth
        bandwidth = (upper - lower) / sma

        # Check bandwidth trend (expanding vs contracting)
        bandwidth_ma = bandwidth.rolling(window=10).mean()
        current_bandwidth = bandwidth.iloc[-1]
        avg_bandwidth = bandwidth_ma.iloc[-1]

        if current_bandwidth > avg_bandwidth * 1.2:
            # Expanding - breakout regime
            expansion_score = 70
        elif current_bandwidth < avg_bandwidth * 0.8:
            # Contracting - mean reversion regime
            expansion_score = 30
        else:
            expansion_score = 50

        # Check price behavior at bands
        price_at_bands = ((close >= upper * 0.95) | (close <= lower * 1.05)).tail(10).sum()

        if price_at_bands >= 5:
            # Frequently at bands - breakout regime
            behavior_score = 70
        else:
            # Staying within bands - mean reversion
            behavior_score = 30

        # Combine
        score = (expansion_score + behavior_score) / 2
        return float(score)

    def _calculate_range_score(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> float:
        """Calculate range expansion/contraction score (0-100).

        Breakout: Ranges expanding
        Mean reversion: Ranges contracting or stable
        """
        close = df['close'].tail(lookback)

        # Calculate rolling ranges (10-period)
        rolling_range = close.rolling(window=10).max() - close.rolling(window=10).min()
        range_pct = rolling_range / close.rolling(window=10).mean() * 100

        # Compare recent range to average
        recent_range = range_pct.tail(10).mean()
        avg_range = range_pct.mean()

        if recent_range > avg_range * 1.3:
            # Expanding range - breakout regime
            score = 75
        elif recent_range < avg_range * 0.7:
            # Contracting range - mean reversion regime
            score = 25
        else:
            score = 50

        return float(score)

    def _calculate_breakout_success(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> float:
        """Calculate breakout success rate (0-100).

        Breakout regime: Breakouts succeed (price continues)
        Mean reversion: Breakouts fail (price reverses)
        """
        close = df['close'].tail(lookback)

        # Identify breakout attempts (price breaks 20-period high/low)
        high_20 = close.rolling(window=20).max()
        low_20 = close.rolling(window=20).min()

        breakouts = (close > high_20.shift(1)) | (close < low_20.shift(1))

        if breakouts.sum() < 3:
            return 50.0  # Not enough data

        # Check if breakouts followed through (price continued 5 periods later)
        successes = 0
        total_breakouts = 0

        for i in range(len(close) - 5):
            if breakouts.iloc[i]:
                total_breakouts += 1

                # Upside breakout
                if close.iloc[i] > high_20.shift(1).iloc[i]:
                    # Success if price higher 5 periods later
                    if close.iloc[i+5] > close.iloc[i]:
                        successes += 1
                # Downside breakout
                elif close.iloc[i] < low_20.shift(1).iloc[i]:
                    # Success if price lower 5 periods later
                    if close.iloc[i+5] < close.iloc[i]:
                        successes += 1

        if total_breakouts == 0:
            return 50.0

        success_rate = successes / total_breakouts

        # Convert to score
        # >60% success = breakout regime
        # <40% success = mean reversion regime
        score = success_rate * 100

        return float(score)

    def _calculate_ma_oscillation_score(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> float:
        """Calculate price vs MA oscillation score (0-100).

        Breakout regime: Price trends away from MA
        Mean reversion: Price oscillates around MA
        """
        close = df['close'].tail(lookback)

        # Calculate 20 SMA
        sma = close.rolling(window=20).mean()

        # Count crosses of the SMA
        above_sma = close > sma
        crosses = (above_sma != above_sma.shift()).sum()

        # More crosses = more oscillation = mean reversion
        # Fewer crosses = trending = breakout
        if crosses > lookback * 0.3:
            # Lots of crosses - mean reversion
            score = 30
        elif crosses < lookback * 0.15:
            # Few crosses - trending/breakout
            score = 70
        else:
            score = 50

        return float(score)

    def _default_result(self) -> RegimeResult:
        """Return default result when insufficient data."""
        return RegimeResult(
            regime='transitional',
            confidence=0.0,
            regime_strength=0.0,
            metrics={},
            recommendation="Insufficient data for regime detection."
        )
