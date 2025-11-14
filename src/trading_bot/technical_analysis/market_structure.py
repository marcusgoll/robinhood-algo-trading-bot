"""Market Structure Analysis - Tool 2 from TA framework.

Identifies price swing patterns to determine trend:
- Higher Highs & Higher Lows (HH/HL) = Uptrend
- Lower Highs & Lower Lows (LH/LL) = Downtrend

If you can't mark swings consistently, your "strategy" is just vibes.
This module makes it quantifiable and systematic.
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Tuple
from dataclasses import dataclass
from scipy.signal import argrelextrema


@dataclass
class SwingPoint:
    """A swing high or swing low."""
    price: float
    index: int
    timestamp: pd.Timestamp
    type: str  # 'high' or 'low'


@dataclass
class MarketStructureResult:
    """Market structure analysis result."""
    trend: str  # 'uptrend', 'downtrend', 'sideways'
    structure: str  # 'HH/HL', 'LH/LL', 'choppy'
    swing_highs: List[SwingPoint]
    swing_lows: List[SwingPoint]
    last_higher_high: Optional[SwingPoint]
    last_higher_low: Optional[SwingPoint]
    last_lower_high: Optional[SwingPoint]
    last_lower_low: Optional[SwingPoint]
    structure_broken: bool  # True if recent structure break
    structure_break_direction: Optional[str]  # 'bullish' or 'bearish'
    confidence: float  # 0-100, based on clarity of structure


class MarketStructureAnalyzer:
    """Analyze market structure using swing highs and lows.

    No subjectivity. Clear swing detection rules.
    Entry in direction of structure after pullbacks.
    Exit when structure breaks.
    """

    def __init__(
        self,
        swing_window: int = 5,
        min_swing_size: float = 0.01  # 1% minimum swing
    ):
        """Initialize market structure analyzer.

        Args:
            swing_window: Window for detecting swings (default: 5)
                         A high is a swing high if it's the highest in this window
            min_swing_size: Minimum price movement to count as swing (default: 1%)
        """
        self.swing_window = swing_window
        self.min_swing_size = min_swing_size

    def analyze(
        self,
        df: pd.DataFrame,
        price_col_high: str = 'high',
        price_col_low: str = 'low',
        price_col_close: str = 'close'
    ) -> MarketStructureResult:
        """Analyze market structure from price data.

        Args:
            df: DataFrame with OHLC data and timestamp index
            price_col_high: Column name for highs
            price_col_low: Column name for lows
            price_col_close: Column name for close

        Returns:
            MarketStructureResult with structure analysis

        Algorithm:
            1. Detect swing highs and lows using local extrema
            2. Compare consecutive swings to identify HH/HL or LH/LL
            3. Determine overall trend based on sequence
            4. Detect structure breaks (e.g., HL broken to downside)
        """
        if len(df) < self.swing_window * 2:
            return self._default_result()

        # Make sure we have a datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.copy()
            if 'timestamp' in df.columns:
                df.index = pd.to_datetime(df['timestamp'])
            else:
                # Create dummy timestamps
                df.index = pd.date_range(start='2024-01-01', periods=len(df), freq='1h')

        # Detect swing highs and lows
        swing_highs = self._detect_swing_highs(df, price_col_high)
        swing_lows = self._detect_swing_lows(df, price_col_low)

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return self._default_result()

        # Analyze structure
        structure, trend = self._analyze_structure(swing_highs, swing_lows)

        # Find last key swings
        last_hh = self._find_last_higher_high(swing_highs)
        last_hl = self._find_last_higher_low(swing_lows)
        last_lh = self._find_last_lower_high(swing_highs)
        last_ll = self._find_last_lower_low(swing_lows)

        # Detect structure breaks
        current_price = float(df[price_col_close].iloc[-1])
        structure_broken, break_direction = self._detect_structure_break(
            current_price, swing_highs, swing_lows, structure
        )

        # Calculate confidence
        confidence = self._calculate_confidence(swing_highs, swing_lows, structure)

        return MarketStructureResult(
            trend=trend,
            structure=structure,
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            last_higher_high=last_hh,
            last_higher_low=last_hl,
            last_lower_high=last_lh,
            last_lower_low=last_ll,
            structure_broken=structure_broken,
            structure_break_direction=break_direction,
            confidence=confidence
        )

    def _detect_swing_highs(
        self,
        df: pd.DataFrame,
        price_col: str
    ) -> List[SwingPoint]:
        """Detect swing highs using local maxima."""
        highs = df[price_col].values

        # Find local maxima
        maxima_indices = argrelextrema(highs, np.greater, order=self.swing_window)[0]

        swing_highs = []
        for idx in maxima_indices:
            if idx < len(df):
                price = float(highs[idx])

                # Filter out small swings
                if swing_highs:
                    last_swing = swing_highs[-1]
                    if abs(price - last_swing.price) / last_swing.price < self.min_swing_size:
                        continue

                swing_highs.append(SwingPoint(
                    price=price,
                    index=idx,
                    timestamp=df.index[idx],
                    type='high'
                ))

        return swing_highs

    def _detect_swing_lows(
        self,
        df: pd.DataFrame,
        price_col: str
    ) -> List[SwingPoint]:
        """Detect swing lows using local minima."""
        lows = df[price_col].values

        # Find local minima
        minima_indices = argrelextrema(lows, np.less, order=self.swing_window)[0]

        swing_lows = []
        for idx in minima_indices:
            if idx < len(df):
                price = float(lows[idx])

                # Filter out small swings
                if swing_lows:
                    last_swing = swing_lows[-1]
                    if abs(price - last_swing.price) / last_swing.price < self.min_swing_size:
                        continue

                swing_lows.append(SwingPoint(
                    price=price,
                    index=idx,
                    timestamp=df.index[idx],
                    type='low'
                ))

        return swing_lows

    def _analyze_structure(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint]
    ) -> Tuple[str, str]:
        """Analyze swing structure to determine trend.

        Returns:
            (structure, trend) tuple
        """
        # Need at least 2 swings of each type
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return 'choppy', 'sideways'

        # Check last 3-4 swings for structure
        recent_highs = swing_highs[-min(4, len(swing_highs)):]
        recent_lows = swing_lows[-min(4, len(swing_lows)):]

        # Count HH/HL vs LH/LL
        hh_count = 0
        hl_count = 0
        lh_count = 0
        ll_count = 0

        # Check highs
        for i in range(1, len(recent_highs)):
            if recent_highs[i].price > recent_highs[i-1].price:
                hh_count += 1
            else:
                lh_count += 1

        # Check lows
        for i in range(1, len(recent_lows)):
            if recent_lows[i].price > recent_lows[i-1].price:
                hl_count += 1
            else:
                ll_count += 1

        # Determine structure
        if hh_count > 0 and hl_count > 0 and lh_count == 0 and ll_count == 0:
            structure = 'HH/HL'
            trend = 'uptrend'
        elif lh_count > 0 and ll_count > 0 and hh_count == 0 and hl_count == 0:
            structure = 'LH/LL'
            trend = 'downtrend'
        elif hh_count >= lh_count and hl_count >= ll_count:
            structure = 'HH/HL'
            trend = 'uptrend'
        elif lh_count > hh_count and ll_count > hl_count:
            structure = 'LH/LL'
            trend = 'downtrend'
        else:
            structure = 'choppy'
            trend = 'sideways'

        return structure, trend

    def _find_last_higher_high(
        self,
        swing_highs: List[SwingPoint]
    ) -> Optional[SwingPoint]:
        """Find the most recent higher high."""
        for i in range(len(swing_highs) - 1, 0, -1):
            if swing_highs[i].price > swing_highs[i-1].price:
                return swing_highs[i]
        return None

    def _find_last_higher_low(
        self,
        swing_lows: List[SwingPoint]
    ) -> Optional[SwingPoint]:
        """Find the most recent higher low."""
        for i in range(len(swing_lows) - 1, 0, -1):
            if swing_lows[i].price > swing_lows[i-1].price:
                return swing_lows[i]
        return None

    def _find_last_lower_high(
        self,
        swing_highs: List[SwingPoint]
    ) -> Optional[SwingPoint]:
        """Find the most recent lower high."""
        for i in range(len(swing_highs) - 1, 0, -1):
            if swing_highs[i].price < swing_highs[i-1].price:
                return swing_highs[i]
        return None

    def _find_last_lower_low(
        self,
        swing_lows: List[SwingPoint]
    ) -> Optional[SwingPoint]:
        """Find the most recent lower low."""
        for i in range(len(swing_lows) - 1, 0, -1):
            if swing_lows[i].price < swing_lows[i-1].price:
                return swing_lows[i]
        return None

    def _detect_structure_break(
        self,
        current_price: float,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        structure: str
    ) -> Tuple[bool, Optional[str]]:
        """Detect if market structure has broken.

        Structure breaks:
        - In uptrend (HH/HL): Breaking below last HL = bearish break
        - In downtrend (LH/LL): Breaking above last LH = bullish break

        Returns:
            (broken, direction) tuple
        """
        if structure == 'HH/HL' and len(swing_lows) >= 2:
            # Find last higher low
            last_hl = None
            for i in range(len(swing_lows) - 1, 0, -1):
                if swing_lows[i].price > swing_lows[i-1].price:
                    last_hl = swing_lows[i]
                    break

            if last_hl and current_price < last_hl.price:
                return True, 'bearish'

        elif structure == 'LH/LL' and len(swing_highs) >= 2:
            # Find last lower high
            last_lh = None
            for i in range(len(swing_highs) - 1, 0, -1):
                if swing_highs[i].price < swing_highs[i-1].price:
                    last_lh = swing_highs[i]
                    break

            if last_lh and current_price > last_lh.price:
                return True, 'bullish'

        return False, None

    def _calculate_confidence(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        structure: str
    ) -> float:
        """Calculate confidence in structure analysis.

        Higher confidence when:
        - More swings available
        - Clear, consistent pattern
        - Larger swing sizes

        Returns:
            Confidence score 0-100
        """
        if structure == 'choppy':
            return 25.0

        # Base confidence on number of swings
        num_swings = len(swing_highs) + len(swing_lows)
        swing_confidence = min(100, num_swings * 10)

        # Check consistency (last 3 swings should match structure)
        consistency = 100.0
        if structure == 'HH/HL':
            recent_highs = swing_highs[-min(3, len(swing_highs)):]
            recent_lows = swing_lows[-min(3, len(swing_lows)):]

            inconsistent = 0
            for i in range(1, len(recent_highs)):
                if recent_highs[i].price <= recent_highs[i-1].price:
                    inconsistent += 1
            for i in range(1, len(recent_lows)):
                if recent_lows[i].price <= recent_lows[i-1].price:
                    inconsistent += 1

            consistency = max(0, 100 - (inconsistent * 25))

        elif structure == 'LH/LL':
            recent_highs = swing_highs[-min(3, len(swing_highs)):]
            recent_lows = swing_lows[-min(3, len(swing_lows)):]

            inconsistent = 0
            for i in range(1, len(recent_highs)):
                if recent_highs[i].price >= recent_highs[i-1].price:
                    inconsistent += 1
            for i in range(1, len(recent_lows)):
                if recent_lows[i].price >= recent_lows[i-1].price:
                    inconsistent += 1

            consistency = max(0, 100 - (inconsistent * 25))

        # Average the two scores
        confidence = (swing_confidence + consistency) / 2
        return confidence

    def _default_result(self) -> MarketStructureResult:
        """Return default result when insufficient data."""
        return MarketStructureResult(
            trend='sideways',
            structure='choppy',
            swing_highs=[],
            swing_lows=[],
            last_higher_high=None,
            last_higher_low=None,
            last_lower_high=None,
            last_lower_low=None,
            structure_broken=False,
            structure_break_direction=None,
            confidence=0.0
        )


class MultiTimeframeAnalyzer:
    """Multi-Timeframe Trend Analysis - Tool 1 from TA framework.

    Check trend on higher TF before trading lower TF.
    Only long when higher TF trend is up, short when down.
    If daily is sideways, reduce size or skip trend-based trades.

    Fighting the higher-TF trend is how accounts quietly die.
    """

    def __init__(self):
        """Initialize multi-timeframe analyzer."""
        self.structure_analyzer = MarketStructureAnalyzer()

    def analyze(
        self,
        timeframe_data: dict[str, pd.DataFrame],
        timeframe_hierarchy: List[str] = None
    ) -> dict:
        """Analyze trend across multiple timeframes.

        Args:
            timeframe_data: Dict mapping timeframe to DataFrame
                           e.g., {'15m': df_15m, '1h': df_1h, '4h': df_4h, '1d': df_1d}
            timeframe_hierarchy: List of timeframes in order (highest to lowest)
                                If None, uses sorted keys

        Returns:
            {
                'overall_trend': str,  # 'bullish', 'bearish', 'mixed'
                'timeframe_trends': {tf: trend_dict},
                'alignment': float,  # 0-100, higher = more aligned
                'trade_direction': str,  # 'long', 'short', 'none'
                'confidence': float  # 0-100
            }

        Logic:
            - If all TFs bullish: Strong long bias
            - If higher TFs bullish, lower TF bearish: Wait for pullback
            - If higher TF bearish: NO LONGS (reduce size or skip)
        """
        if not timeframe_data:
            return self._default_mtf_result()

        if timeframe_hierarchy is None:
            # Sort timeframes (longest to shortest)
            tf_order = {'1w': 1, '1d': 2, '4h': 3, '1h': 4, '30m': 5, '15m': 6, '5m': 7, '1m': 8}
            timeframe_hierarchy = sorted(
                timeframe_data.keys(),
                key=lambda x: tf_order.get(x, 99)
            )

        # Analyze each timeframe
        timeframe_trends = {}
        for tf in timeframe_hierarchy:
            if tf not in timeframe_data:
                continue

            df = timeframe_data[tf]
            structure_result = self.structure_analyzer.analyze(df)

            timeframe_trends[tf] = {
                'trend': structure_result.trend,
                'structure': structure_result.structure,
                'confidence': structure_result.confidence,
                'structure_broken': structure_result.structure_broken
            }

        # Determine overall trend (weighted by timeframe importance)
        bullish_score = 0
        bearish_score = 0
        total_weight = 0

        for i, tf in enumerate(timeframe_hierarchy):
            if tf not in timeframe_trends:
                continue

            # Higher timeframes get more weight
            weight = len(timeframe_hierarchy) - i
            total_weight += weight

            trend_data = timeframe_trends[tf]
            if trend_data['trend'] == 'uptrend':
                bullish_score += weight * (trend_data['confidence'] / 100)
            elif trend_data['trend'] == 'downtrend':
                bearish_score += weight * (trend_data['confidence'] / 100)

        # Normalize scores
        if total_weight > 0:
            bullish_score /= total_weight
            bearish_score /= total_weight

        # Determine overall trend
        if bullish_score > 0.6:
            overall_trend = 'bullish'
            trade_direction = 'long'
        elif bearish_score > 0.6:
            overall_trend = 'bearish'
            trade_direction = 'short'
        else:
            overall_trend = 'mixed'
            trade_direction = 'none'

        # Calculate alignment (how well timeframes agree)
        alignment = 0.0
        if timeframe_trends:
            aligned_count = sum(
                1 for tf_data in timeframe_trends.values()
                if (overall_trend == 'bullish' and tf_data['trend'] == 'uptrend') or
                   (overall_trend == 'bearish' and tf_data['trend'] == 'downtrend')
            )
            alignment = (aligned_count / len(timeframe_trends)) * 100

        # Calculate confidence
        confidence = max(bullish_score, bearish_score) * 100

        return {
            'overall_trend': overall_trend,
            'timeframe_trends': timeframe_trends,
            'alignment': alignment,
            'trade_direction': trade_direction,
            'confidence': confidence,
            'bullish_score': bullish_score * 100,
            'bearish_score': bearish_score * 100
        }

    def _default_mtf_result(self) -> dict:
        """Return default result when no data."""
        return {
            'overall_trend': 'mixed',
            'timeframe_trends': {},
            'alignment': 0.0,
            'trade_direction': 'none',
            'confidence': 0.0,
            'bullish_score': 0.0,
            'bearish_score': 0.0
        }
