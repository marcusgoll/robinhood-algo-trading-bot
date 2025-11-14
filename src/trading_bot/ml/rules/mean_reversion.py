"""Mean-reversion trading rules.

These rules exploit temporary price dislocations, betting on return to average.
Work best in ranging/sideways markets.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from trading_bot.ml.features import FeatureExtractor
from trading_bot.ml.generators.rule_based import RuleBasedStrategy, RuleSignal

logger = logging.getLogger(__name__)


class BollingerBounceRule(RuleBasedStrategy):
    """Buy when price touches lower Bollinger Band.

    Entry: Price < BB_Lower AND RSI < 40
    Exit: Price > SMA(20) OR RSI > 60

    Logic: Oversold + price at support band = bounce opportunity.
    """

    def __init__(self):
        super().__init__("Bollinger_Bounce")
        self.entry_logic = "Price < BB_Lower(20,2) AND RSI(14) < 40"
        self.exit_logic = "Price > SMA(20) OR RSI(14) > 60"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate bounce signals from Bollinger Bands."""
        extractor = FeatureExtractor()
        features = extractor.extract(data, symbol="BACKTEST")

        # Calculate Bollinger Bands
        sma_20 = data["close"].rolling(window=20).mean()
        std_20 = data["close"].rolling(window=20).std()
        bb_upper = sma_20 + (std_20 * 2)
        bb_lower = sma_20 - (std_20 * 2)

        signals = []
        position = 0

        for i, fs in enumerate(features):
            if i < 20:  # Need 20 bars
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Warmup"))
                continue

            price = float(data["close"].iloc[i])
            lower_band = float(bb_lower.iloc[i])
            sma20_val = float(sma_20.iloc[i])

            # Entry: Price below lower band + oversold RSI
            if position == 0 and price < lower_band and fs.rsi_14 < 40:
                distance_pct = (lower_band - price) / lower_band
                signals.append(RuleSignal(
                    action=1,
                    confidence=min(distance_pct * 20, 1.0),  # Farther below = stronger
                    reason=f"BB bounce setup (RSI={fs.rsi_14:.1f})"
                ))
                position = 1

            # Exit: Price recovers to SMA or RSI normalizes
            elif position == 1 and (price > sma20_val or fs.rsi_14 > 60):
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason="Mean reversion complete"
                ))
                position = 0

            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

        return signals


class BollingerBreakoutRule(RuleBasedStrategy):
    """Buy on breakout above upper Bollinger Band with volume.

    Entry: Price > BB_Upper AND Volume > 2x Average
    Exit: Price < SMA(20)

    Logic: Strong breakouts with volume often continue (not mean revert).
    """

    def __init__(self):
        super().__init__("Bollinger_Breakout")
        self.entry_logic = "Price > BB_Upper(20,2) AND Volume > 2x Avg"
        self.exit_logic = "Price < SMA(20)"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate breakout signals."""
        extractor = FeatureExtractor()
        features = extractor.extract(data, symbol="BACKTEST")

        # Calculate Bollinger Bands
        sma_20 = data["close"].rolling(window=20).mean()
        std_20 = data["close"].rolling(window=20).std()
        bb_upper = sma_20 + (std_20 * 2)

        # Volume average
        vol_avg = data["volume"].rolling(window=20).mean()

        signals = []
        position = 0

        for i, fs in enumerate(features):
            if i < 20:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Warmup"))
                continue

            price = float(data["close"].iloc[i])
            upper_band = float(bb_upper.iloc[i])
            sma20_val = float(sma_20.iloc[i])
            volume = float(data["volume"].iloc[i])
            avg_vol = float(vol_avg.iloc[i])

            # Entry: Price above upper band + volume surge
            if position == 0 and price > upper_band and volume > avg_vol * 2:
                signals.append(RuleSignal(
                    action=1,
                    confidence=min((volume / avg_vol - 2) / 2, 1.0),
                    reason=f"BB breakout ({volume/avg_vol:.1f}x vol)"
                ))
                position = 1

            # Exit: Price falls back below SMA
            elif position == 1 and price < sma20_val:
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason="Breakout failed"
                ))
                position = 0

            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

        return signals


class SMADeviationRule(RuleBasedStrategy):
    """Buy when price deviates significantly below SMA(20).

    Entry: (Price - SMA(20)) / SMA(20) < -5%
    Exit: (Price - SMA(20)) / SMA(20) > 0%

    Logic: Excessive deviation likely to correct.
    """

    def __init__(self):
        super().__init__("SMA_Deviation_Reversion")
        self.entry_logic = "(Price - SMA(20)) / SMA(20) < -5%"
        self.exit_logic = "(Price - SMA(20)) / SMA(20) > 0%"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate deviation reversion signals."""
        extractor = FeatureExtractor()
        features = extractor.extract(data, symbol="BACKTEST")

        sma_20 = data["close"].rolling(window=20).mean()

        signals = []
        position = 0

        for i, fs in enumerate(features):
            if i < 20:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Warmup"))
                continue

            price = float(data["close"].iloc[i])
            sma20_val = float(sma_20.iloc[i])

            deviation_pct = (price - sma20_val) / sma20_val

            # Entry: Price > 5% below SMA
            if position == 0 and deviation_pct < -0.05:
                signals.append(RuleSignal(
                    action=1,
                    confidence=min(abs(deviation_pct) / 0.10, 1.0),  # Cap at 10%
                    reason=f"Excessive deviation ({deviation_pct:.1%})"
                ))
                position = 1

            # Exit: Price back at or above SMA
            elif position == 1 and deviation_pct > 0:
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason="Reversion complete"
                ))
                position = 0

            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

        return signals


class ZScoreReversionRule(RuleBasedStrategy):
    """Buy when Z-Score indicates extreme oversold.

    Entry: Z-Score(Close, 20) < -2
    Exit: Z-Score(Close, 20) > 0

    Logic: Statistical measure of how far price is from mean.
    """

    def __init__(self):
        super().__init__("Z_Score_Reversion")
        self.entry_logic = "Z-Score(Close, 20) < -2"
        self.exit_logic = "Z-Score(Close, 20) > 0"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate Z-Score reversion signals."""
        # Calculate Z-Score: (Price - Mean) / StdDev
        window = 20
        sma = data["close"].rolling(window=window).mean()
        std = data["close"].rolling(window=window).std()
        z_score = (data["close"] - sma) / std

        signals = []
        position = 0

        for i in range(len(data)):
            if i < window:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Warmup"))
                continue

            z = float(z_score.iloc[i])

            # Entry: Z-Score < -2 (2 standard deviations below mean)
            if position == 0 and z < -2:
                signals.append(RuleSignal(
                    action=1,
                    confidence=min(abs(z) / 3, 1.0),  # Cap at -3
                    reason=f"Statistical extreme (Z={z:.2f})"
                ))
                position = 1

            # Exit: Z-Score back above 0
            elif position == 1 and z > 0:
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason="Reversion complete"
                ))
                position = 0

            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

        return signals


class DonchianChannelBreakoutRule(RuleBasedStrategy):
    """Buy on breakout above Donchian Channel (20-day high).

    Entry: Price > Donchian_Upper(20)
    Exit: Price < Donchian_Lower(20)

    Logic: Turtle Trading system - trend following via channel breakouts.
    """

    def __init__(self):
        super().__init__("Donchian_Channel_Breakout")
        self.entry_logic = "Price > Highest_High(20)"
        self.exit_logic = "Price < Lowest_Low(20)"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate Donchian channel signals."""
        window = 20
        donchian_upper = data["high"].rolling(window=window).max()
        donchian_lower = data["low"].rolling(window=window).min()

        signals = []
        position = 0

        for i in range(len(data)):
            if i < window:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Warmup"))
                continue

            price = float(data["close"].iloc[i])
            upper = float(donchian_upper.iloc[i])
            lower = float(donchian_lower.iloc[i])

            # Entry: Price breaks above channel
            if position == 0 and price > upper:
                signals.append(RuleSignal(
                    action=1,
                    confidence=0.8,  # High confidence - clean breakout
                    reason=f"Donchian breakout (20-day high)"
                ))
                position = 1

            # Exit: Price breaks below channel
            elif position == 1 and price < lower:
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason="Channel exit"
                ))
                position = 0

            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

        return signals
