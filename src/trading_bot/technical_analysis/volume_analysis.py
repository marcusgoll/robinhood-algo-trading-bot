"""Volume Analysis - Advanced volume and order flow analysis.

Extends the basic volume indicators (tools 11-13) with deeper analysis:
- Volume confirmation for signals
- Climactic volume detection
- Volume divergence
- Composite volume analysis
"""

import numpy as np
import pandas as pd
from typing import Optional
from dataclasses import dataclass


@dataclass
class VolumeAnalysisResult:
    """Comprehensive volume analysis result."""
    volume_trend: str  # 'increasing', 'decreasing', 'stable'
    volume_confirmation: bool  # Does volume confirm price action?
    volume_divergence: Optional[str]  # 'bullish', 'bearish', None
    climax_detected: bool
    accumulation_detected: bool  # Stealth accumulation (OBV rising, price flat)
    distribution_detected: bool  # Distribution (OBV falling, price flat)
    volume_quality: float  # 0-100, overall volume health
    recommendation: str


class VolumeAnalyzer:
    """Analyze volume to confirm or reject price signals.

    Volume is truth. Price is just opinion.
    - Breakouts without volume = fakeouts
    - Trends with declining volume = weakening
    - Volume climax at extremes = exhaustion
    """

    def __init__(self):
        """Initialize volume analyzer."""
        pass

    def analyze(
        self,
        df: pd.DataFrame,
        price_signal: Optional[str] = None,  # 'bullish', 'bearish', None
        lookback: int = 20
    ) -> VolumeAnalysisResult:
        """Comprehensive volume analysis.

        Args:
            df: DataFrame with OHLCV data
            price_signal: Current price signal to validate
            lookback: Periods to analyze

        Returns:
            VolumeAnalysisResult with volume assessment
        """
        if len(df) < lookback:
            return self._default_result()

        # Calculate volume trend
        volume_trend = self._calculate_volume_trend(df, lookback)

        # Check volume confirmation
        volume_confirmation = self._check_volume_confirmation(
            df, price_signal, lookback
        )

        # Detect divergence
        volume_divergence = self._detect_volume_divergence(df, lookback)

        # Detect climax
        climax_detected = self._detect_climax(df, lookback)

        # Detect accumulation/distribution
        accumulation_detected = self._detect_accumulation(df, lookback)
        distribution_detected = self._detect_distribution(df, lookback)

        # Calculate volume quality
        volume_quality = self._calculate_volume_quality(
            volume_trend, volume_confirmation, volume_divergence,
            climax_detected, accumulation_detected, distribution_detected
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(
            volume_trend, volume_confirmation, volume_divergence,
            climax_detected, accumulation_detected, distribution_detected,
            price_signal
        )

        return VolumeAnalysisResult(
            volume_trend=volume_trend,
            volume_confirmation=volume_confirmation,
            volume_divergence=volume_divergence,
            climax_detected=climax_detected,
            accumulation_detected=accumulation_detected,
            distribution_detected=distribution_detected,
            volume_quality=volume_quality,
            recommendation=recommendation
        )

    def _calculate_volume_trend(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> str:
        """Calculate volume trend (increasing, decreasing, stable)."""
        volume = df['volume'].tail(lookback)

        # Compare recent volume to older volume
        recent_avg = volume.tail(lookback // 2).mean()
        older_avg = volume.head(lookback // 2).mean()

        if recent_avg > older_avg * 1.2:
            return 'increasing'
        elif recent_avg < older_avg * 0.8:
            return 'decreasing'
        else:
            return 'stable'

    def _check_volume_confirmation(
        self,
        df: pd.DataFrame,
        price_signal: Optional[str],
        lookback: int
    ) -> bool:
        """Check if volume confirms price signal."""
        if price_signal is None:
            return True  # No signal to confirm

        volume = df['volume'].tail(lookback)
        current_volume = volume.iloc[-1]
        avg_volume = volume.mean()

        # Volume should be above average for confirmation
        if price_signal in ['bullish', 'bearish']:
            return current_volume > avg_volume * 1.2

        return True

    def _detect_volume_divergence(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> Optional[str]:
        """Detect volume divergence from price.

        Bullish: Price making lower lows, but volume declining (selling exhaustion)
        Bearish: Price making higher highs, but volume declining (buying exhaustion)
        """
        recent_df = df.tail(lookback)
        close = recent_df['close']
        volume = recent_df['volume']

        # Simple approach: Compare first half vs second half
        mid = lookback // 2

        price_first = close.iloc[:mid].mean()
        price_second = close.iloc[mid:].mean()
        volume_first = volume.iloc[:mid].mean()
        volume_second = volume.iloc[mid:].mean()

        # Bullish divergence: Price down, volume down (exhaustion)
        if price_second < price_first * 0.95 and volume_second < volume_first * 0.8:
            return 'bullish'

        # Bearish divergence: Price up, volume down (exhaustion)
        if price_second > price_first * 1.05 and volume_second < volume_first * 0.8:
            return 'bearish'

        return None

    def _detect_climax(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> bool:
        """Detect volume climax (exhaustion).

        Climax: Extreme volume spike at price extreme
        """
        recent_df = df.tail(lookback)
        close = recent_df['close']
        volume = recent_df['volume']

        current_volume = volume.iloc[-1]
        avg_volume = volume.mean()

        # Volume spike (>3x average)
        volume_spike = current_volume > avg_volume * 3

        if not volume_spike:
            return False

        # Check if price is at extreme
        current_price = close.iloc[-1]
        recent_high = close.max()
        recent_low = close.min()

        price_range = recent_high - recent_low
        if price_range == 0:
            return False

        price_position = (current_price - recent_low) / price_range

        # Climax if at top (>0.9) or bottom (<0.1)
        return price_position > 0.9 or price_position < 0.1

    def _detect_accumulation(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> bool:
        """Detect stealth accumulation.

        Accumulation: OBV rising while price flat/down (buyers accumulating)
        """
        recent_df = df.tail(lookback)
        close = recent_df['close']
        volume = recent_df['volume']

        # Calculate OBV
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()

        # Compare price change vs OBV change
        price_change = (close.iloc[-1] - close.iloc[0]) / close.iloc[0]
        obv_change = (obv.iloc[-1] - obv.iloc[0]) / abs(obv.iloc[0])

        # Accumulation: Price flat/down (<5% change) but OBV up (>10% change)
        return price_change < 0.05 and obv_change > 0.1

    def _detect_distribution(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> bool:
        """Detect distribution.

        Distribution: OBV falling while price flat/up (sellers distributing)
        """
        recent_df = df.tail(lookback)
        close = recent_df['close']
        volume = recent_df['volume']

        # Calculate OBV
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()

        # Compare price change vs OBV change
        price_change = (close.iloc[-1] - close.iloc[0]) / close.iloc[0]
        obv_change = (obv.iloc[-1] - obv.iloc[0]) / abs(obv.iloc[0])

        # Distribution: Price flat/up (>-5% change) but OBV down (<-10% change)
        return price_change > -0.05 and obv_change < -0.1

    def _calculate_volume_quality(
        self,
        volume_trend: str,
        volume_confirmation: bool,
        volume_divergence: Optional[str],
        climax_detected: bool,
        accumulation_detected: bool,
        distribution_detected: bool
    ) -> float:
        """Calculate overall volume quality (0-100)."""
        quality = 50.0  # Base

        # Volume trend
        if volume_trend == 'increasing':
            quality += 15
        elif volume_trend == 'decreasing':
            quality -= 15

        # Confirmation
        if volume_confirmation:
            quality += 20
        else:
            quality -= 20

        # Divergence (warning sign)
        if volume_divergence:
            quality -= 10

        # Climax (warning sign)
        if climax_detected:
            quality -= 15

        # Accumulation (positive)
        if accumulation_detected:
            quality += 15

        # Distribution (negative)
        if distribution_detected:
            quality -= 15

        return max(0, min(100, quality))

    def _generate_recommendation(
        self,
        volume_trend: str,
        volume_confirmation: bool,
        volume_divergence: Optional[str],
        climax_detected: bool,
        accumulation_detected: bool,
        distribution_detected: bool,
        price_signal: Optional[str]
    ) -> str:
        """Generate trading recommendation based on volume."""
        recommendations = []

        if climax_detected:
            recommendations.append("Volume climax detected - potential reversal")

        if accumulation_detected:
            recommendations.append("Accumulation phase - bullish for future")

        if distribution_detected:
            recommendations.append("Distribution phase - bearish for future")

        if price_signal and not volume_confirmation:
            recommendations.append(f"WARNING: {price_signal} price signal lacks volume confirmation")

        if volume_divergence:
            recommendations.append(f"{volume_divergence.capitalize()} volume divergence - trend weakening")

        if volume_trend == 'increasing' and price_signal == 'bullish':
            recommendations.append("Strong bullish volume trend confirms upside")
        elif volume_trend == 'increasing' and price_signal == 'bearish':
            recommendations.append("WARNING: Strong volume against bearish signal")

        if not recommendations:
            return "Volume analysis neutral"

        return " | ".join(recommendations)

    def _default_result(self) -> VolumeAnalysisResult:
        """Return default result."""
        return VolumeAnalysisResult(
            volume_trend='stable',
            volume_confirmation=False,
            volume_divergence=None,
            climax_detected=False,
            accumulation_detected=False,
            distribution_detected=False,
            volume_quality=50.0,
            recommendation="Insufficient data for volume analysis"
        )
