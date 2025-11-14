"""Pattern Detector - Tools 14-16 from TA framework.

Detects:
- Consolidation & Breakout Patterns (Tool 14)
- Pullback Entries (Tool 15)
- Gaps / Imbalances (Tool 16)

Trade breakouts WITH trend & volume confirmation.
Place stops just outside structure, not in the middle.

Crypto loves fakeouts - filter breakouts by volume + higher-TF bias.
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ConsolidationResult:
    """Consolidation pattern result."""
    is_consolidating: bool
    pattern_type: str  # 'range', 'triangle', 'flag', 'none'
    breakout_imminent: bool  # Tight consolidation suggesting breakout coming
    support_level: Optional[float]
    resistance_level: Optional[float]
    duration_periods: int
    consolidation_quality: float  # 0-100, how clean the pattern is


@dataclass
class BreakoutResult:
    """Breakout pattern result."""
    breakout_detected: bool
    breakout_direction: str  # 'up', 'down', 'none'
    breakout_strength: float  # 0-100
    volume_confirmed: bool
    false_breakout_risk: float  # 0-100, likelihood this is a fakeout
    entry_price: Optional[float]
    stop_loss: Optional[float]
    initial_target: Optional[float]


@dataclass
class PullbackResult:
    """Pullback entry pattern result."""
    pullback_detected: bool
    pullback_type: str  # 'fib_618', 'fib_50', 'ma_pullback', 'sr_test', 'none'
    entry_zone_low: Optional[float]
    entry_zone_high: Optional[float]
    stop_below: Optional[float]
    quality: float  # 0-100


@dataclass
class GapResult:
    """Gap / Imbalance result."""
    gaps_detected: List[dict]  # List of gap info
    nearest_gap: Optional[dict]  # Closest gap to current price
    gap_fill_probability: float  # 0-100


class PatternDetector:
    """Detect chart patterns and setups.

    No harmonic pattern astrology. Just clean, tradable setups:
    - Tight ranges before expansion
    - Breakouts with volume
    - Pullbacks to logical zones
    - Gaps acting as magnets
    """

    def __init__(self):
        """Initialize pattern detector."""
        pass

    # Tool 14: Consolidation & Breakout Patterns
    def detect_consolidation(
        self,
        df: pd.DataFrame,
        lookback: int = 20
    ) -> ConsolidationResult:
        """Detect consolidation patterns.

        Args:
            df: DataFrame with OHLC data
            lookback: Periods to analyze

        Returns:
            ConsolidationResult with pattern details

        Patterns:
        - Range: Price oscillating between clear S/R
        - Triangle: Converging highs/lows
        - Flag: Tight parallel channel after strong move
        """
        if len(df) < lookback:
            return self._default_consolidation()

        recent_df = df.tail(lookback)
        close = recent_df['close']
        high = recent_df['high']
        low = recent_df['low']

        # Calculate range metrics
        range_high = high.max()
        range_low = low.min()
        range_size = range_high - range_low
        avg_price = close.mean()
        range_pct = (range_size / avg_price) * 100

        # Check if consolidating (price within tight range)
        is_consolidating = range_pct < 10  # Within 10% range

        if not is_consolidating:
            return ConsolidationResult(
                is_consolidating=False,
                pattern_type='none',
                breakout_imminent=False,
                support_level=None,
                resistance_level=None,
                duration_periods=0,
                consolidation_quality=0.0
            )

        # Identify pattern type
        upper_highs = high.rolling(window=5).max()
        lower_lows = low.rolling(window=5).min()

        # Check if range is contracting (triangle/flag)
        early_range = upper_highs.iloc[:len(upper_highs)//2].mean() - lower_lows.iloc[:len(lower_lows)//2].mean()
        late_range = upper_highs.iloc[len(upper_highs)//2:].mean() - lower_lows.iloc[len(lower_lows)//2:].mean()

        if late_range < early_range * 0.7:
            # Range contracting - triangle or flag
            # Check if there was a strong move before (flag)
            pre_consolidation = df.iloc[-lookback-10:-lookback]
            if len(pre_consolidation) >= 10:
                pre_range = (pre_consolidation['close'].iloc[-1] - pre_consolidation['close'].iloc[0]) / pre_consolidation['close'].iloc[0]
                if abs(pre_range) > 0.15:  # >15% move before
                    pattern_type = 'flag'
                else:
                    pattern_type = 'triangle'
            else:
                pattern_type = 'triangle'
        else:
            # Sideways range
            pattern_type = 'range'

        # Determine support and resistance
        # Use 20th and 80th percentile
        support_level = float(low.quantile(0.2))
        resistance_level = float(high.quantile(0.8))

        # Breakout imminent if range very tight
        breakout_imminent = range_pct < 5

        # Quality: Based on how well price respects levels
        touches_support = (low <= support_level * 1.02).sum()
        touches_resistance = (high >= resistance_level * 0.98).sum()
        quality = min(100, (touches_support + touches_resistance) * 10)

        return ConsolidationResult(
            is_consolidating=True,
            pattern_type=pattern_type,
            breakout_imminent=breakout_imminent,
            support_level=support_level,
            resistance_level=resistance_level,
            duration_periods=lookback,
            consolidation_quality=quality
        )

    def detect_breakout(
        self,
        df: pd.DataFrame,
        consolidation: ConsolidationResult,
        volume_threshold: float = 1.5
    ) -> BreakoutResult:
        """Detect breakout from consolidation.

        Args:
            df: DataFrame with OHLCV data
            consolidation: Consolidation result
            volume_threshold: Volume multiplier for confirmation (default: 1.5x)

        Returns:
            BreakoutResult with breakout details

        Filters:
        - Volume confirmation (volume > average)
        - Clean break (price clearly outside range)
        - Reduced fakeout risk if higher-TF aligned
        """
        if not consolidation.is_consolidating:
            return self._default_breakout()

        current_price = float(df['close'].iloc[-1])
        current_volume = float(df['volume'].iloc[-1])
        avg_volume = float(df['volume'].tail(20).mean())

        volume_confirmed = current_volume > avg_volume * volume_threshold

        # Check for breakout
        breakout_detected = False
        breakout_direction = 'none'
        breakout_strength = 0.0

        if consolidation.resistance_level and current_price > consolidation.resistance_level:
            # Upside breakout
            breakout_detected = True
            breakout_direction = 'up'

            # Strength based on distance from resistance
            breakout_distance = (current_price - consolidation.resistance_level) / consolidation.resistance_level
            breakout_strength = min(100, breakout_distance * 1000)

            # Entry, stop, target
            entry_price = current_price
            stop_loss = consolidation.support_level
            # Target: Range height above breakout
            range_height = consolidation.resistance_level - consolidation.support_level
            initial_target = consolidation.resistance_level + range_height

        elif consolidation.support_level and current_price < consolidation.support_level:
            # Downside breakout
            breakout_detected = True
            breakout_direction = 'down'

            breakout_distance = (consolidation.support_level - current_price) / consolidation.support_level
            breakout_strength = min(100, breakout_distance * 1000)

            entry_price = current_price
            stop_loss = consolidation.resistance_level
            range_height = consolidation.resistance_level - consolidation.support_level
            initial_target = consolidation.support_level - range_height

        else:
            # No breakout
            return self._default_breakout()

        # Assess fakeout risk
        false_breakout_risk = 50.0  # Base risk

        if volume_confirmed:
            false_breakout_risk -= 20  # Lower risk with volume
        if consolidation.consolidation_quality > 70:
            false_breakout_risk -= 15  # Lower risk with clean pattern
        if breakout_strength > 50:
            false_breakout_risk -= 15  # Lower risk with strong move

        false_breakout_risk = max(0, min(100, false_breakout_risk))

        return BreakoutResult(
            breakout_detected=breakout_detected,
            breakout_direction=breakout_direction,
            breakout_strength=breakout_strength,
            volume_confirmed=volume_confirmed,
            false_breakout_risk=false_breakout_risk,
            entry_price=entry_price,
            stop_loss=stop_loss,
            initial_target=initial_target
        )

    # Tool 15: Pullback Entries
    def detect_pullback(
        self,
        df: pd.DataFrame,
        trend: str,  # 'uptrend' or 'downtrend'
        lookback: int = 50
    ) -> PullbackResult:
        """Detect pullback entry opportunities.

        Args:
            df: DataFrame with OHLC data
            trend: Overall trend direction
            lookback: Periods to analyze

        Returns:
            PullbackResult with entry zones

        Pullback types:
        - Fib retracement (38%, 50%, 61.8%)
        - MA pullback (pullback to 20/50 EMA)
        - S/R retest (prior resistance → support)
        """
        if len(df) < lookback or trend not in ['uptrend', 'downtrend']:
            return self._default_pullback()

        recent_df = df.tail(lookback)
        close = recent_df['close']
        high = recent_df['high']
        low = recent_df['low']

        current_price = float(close.iloc[-1])

        # Find recent swing high/low
        if trend == 'uptrend':
            # Look for pullback in uptrend
            swing_high = float(high.max())
            swing_low_before_high = float(low.iloc[:high.argmax()].min())

            # Calculate Fib levels from swing low to swing high
            range_size = swing_high - swing_low_before_high
            fib_382 = swing_high - (range_size * 0.382)
            fib_50 = swing_high - (range_size * 0.50)
            fib_618 = swing_high - (range_size * 0.618)

            # Check if price is pulling back to these levels
            if fib_618 * 0.98 <= current_price <= fib_618 * 1.02:
                pullback_type = 'fib_618'
                entry_zone_low = fib_618 * 0.98
                entry_zone_high = fib_618 * 1.02
                stop_below = swing_low_before_high
                quality = 90.0
            elif fib_50 * 0.98 <= current_price <= fib_50 * 1.02:
                pullback_type = 'fib_50'
                entry_zone_low = fib_50 * 0.98
                entry_zone_high = fib_50 * 1.02
                stop_below = swing_low_before_high
                quality = 80.0
            elif fib_382 * 0.98 <= current_price <= fib_382 * 1.02:
                pullback_type = 'fib_382'
                entry_zone_low = fib_382 * 0.98
                entry_zone_high = fib_382 * 1.02
                stop_below = swing_low_before_high
                quality = 70.0
            else:
                # Check MA pullback
                ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
                if ema_20 * 0.99 <= current_price <= ema_20 * 1.01:
                    pullback_type = 'ma_pullback'
                    entry_zone_low = ema_20 * 0.99
                    entry_zone_high = ema_20 * 1.01
                    stop_below = float(low.tail(10).min())
                    quality = 75.0
                else:
                    return self._default_pullback()

        else:  # downtrend
            # Look for pullback in downtrend
            swing_low = float(low.min())
            swing_high_before_low = float(high.iloc[:low.argmin()].max())

            range_size = swing_high_before_low - swing_low
            fib_382 = swing_low + (range_size * 0.382)
            fib_50 = swing_low + (range_size * 0.50)
            fib_618 = swing_low + (range_size * 0.618)

            if fib_618 * 0.98 <= current_price <= fib_618 * 1.02:
                pullback_type = 'fib_618'
                entry_zone_low = fib_618 * 0.98
                entry_zone_high = fib_618 * 1.02
                stop_below = swing_high_before_low
                quality = 90.0
            elif fib_50 * 0.98 <= current_price <= fib_50 * 1.02:
                pullback_type = 'fib_50'
                entry_zone_low = fib_50 * 0.98
                entry_zone_high = fib_50 * 1.02
                stop_below = swing_high_before_low
                quality = 80.0
            elif fib_382 * 0.98 <= current_price <= fib_382 * 1.02:
                pullback_type = 'fib_382'
                entry_zone_low = fib_382 * 0.98
                entry_zone_high = fib_382 * 1.02
                stop_below = swing_high_before_low
                quality = 70.0
            else:
                # Check MA pullback
                ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
                if ema_20 * 0.99 <= current_price <= ema_20 * 1.01:
                    pullback_type = 'ma_pullback'
                    entry_zone_low = ema_20 * 0.99
                    entry_zone_high = ema_20 * 1.01
                    stop_below = float(high.tail(10).max())
                    quality = 75.0
                else:
                    return self._default_pullback()

        return PullbackResult(
            pullback_detected=True,
            pullback_type=pullback_type,
            entry_zone_low=entry_zone_low,
            entry_zone_high=entry_zone_high,
            stop_below=stop_below,
            quality=quality
        )

    # Tool 16: Gaps / Imbalances
    def detect_gaps(
        self,
        df: pd.DataFrame,
        min_gap_pct: float = 2.0
    ) -> GapResult:
        """Detect price gaps and imbalances.

        Args:
            df: DataFrame with OHLC data
            min_gap_pct: Minimum gap size as % (default: 2%)

        Returns:
            GapResult with gap information

        Note:
        - Gaps often act as magnets / S/R
        - Not all gaps fill, but many do
        - Imbalances (unfilled gaps) attract price
        """
        if len(df) < 10:
            return GapResult(gaps_detected=[], nearest_gap=None, gap_fill_probability=0.0)

        gaps = []
        current_price = float(df['close'].iloc[-1])

        for i in range(1, len(df)):
            prev_high = float(df['high'].iloc[i-1])
            prev_low = float(df['low'].iloc[i-1])
            curr_high = float(df['high'].iloc[i])
            curr_low = float(df['low'].iloc[i])

            # Gap up (current low > previous high)
            if curr_low > prev_high:
                gap_size = curr_low - prev_high
                gap_pct = (gap_size / prev_high) * 100

                if gap_pct >= min_gap_pct:
                    # Check if gap has been filled
                    filled = False
                    for j in range(i+1, len(df)):
                        if df['low'].iloc[j] <= prev_high:
                            filled = True
                            break

                    gaps.append({
                        'type': 'gap_up',
                        'gap_low': prev_high,
                        'gap_high': curr_low,
                        'gap_size_pct': gap_pct,
                        'index': i,
                        'filled': filled,
                        'distance_from_current': abs(current_price - ((prev_high + curr_low) / 2))
                    })

            # Gap down (current high < previous low)
            elif curr_high < prev_low:
                gap_size = prev_low - curr_high
                gap_pct = (gap_size / prev_low) * 100

                if gap_pct >= min_gap_pct:
                    filled = False
                    for j in range(i+1, len(df)):
                        if df['high'].iloc[j] >= prev_low:
                            filled = True
                            break

                    gaps.append({
                        'type': 'gap_down',
                        'gap_low': curr_high,
                        'gap_high': prev_low,
                        'gap_size_pct': gap_pct,
                        'index': i,
                        'filled': filled,
                        'distance_from_current': abs(current_price - ((prev_low + curr_high) / 2))
                    })

        # Find nearest unfilled gap
        unfilled_gaps = [g for g in gaps if not g['filled']]
        nearest_gap = None

        if unfilled_gaps:
            nearest_gap = min(unfilled_gaps, key=lambda g: g['distance_from_current'])

        # Calculate fill probability (historical fill rate)
        if gaps:
            fill_rate = sum(1 for g in gaps if g['filled']) / len(gaps)
            gap_fill_probability = fill_rate * 100
        else:
            gap_fill_probability = 50.0  # Default

        return GapResult(
            gaps_detected=gaps,
            nearest_gap=nearest_gap,
            gap_fill_probability=gap_fill_probability
        )

    def _default_consolidation(self) -> ConsolidationResult:
        """Return default consolidation result."""
        return ConsolidationResult(
            is_consolidating=False,
            pattern_type='none',
            breakout_imminent=False,
            support_level=None,
            resistance_level=None,
            duration_periods=0,
            consolidation_quality=0.0
        )

    def _default_breakout(self) -> BreakoutResult:
        """Return default breakout result."""
        return BreakoutResult(
            breakout_detected=False,
            breakout_direction='none',
            breakout_strength=0.0,
            volume_confirmed=False,
            false_breakout_risk=100.0,
            entry_price=None,
            stop_loss=None,
            initial_target=None
        )

    def _default_pullback(self) -> PullbackResult:
        """Return default pullback result."""
        return PullbackResult(
            pullback_detected=False,
            pullback_type='none',
            entry_zone_low=None,
            entry_zone_high=None,
            stop_below=None,
            quality=0.0
        )
