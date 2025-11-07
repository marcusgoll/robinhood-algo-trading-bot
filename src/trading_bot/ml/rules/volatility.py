"""Volatility-based trading rules.

These rules use volatility measures to time entries and position sizing.
Work well in both trending and ranging markets.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from trading_bot.ml.features import FeatureExtractor
from trading_bot.ml.generators.rule_based import RuleBasedStrategy, RuleSignal

logger = logging.getLogger(__name__)


class ATRExpansionRule(RuleBasedStrategy):
    """Buy when volatility expands in uptrend.

    Entry: ATR(14) > 1.5 * SMA(ATR, 50) AND RSI > 50
    Exit: ATR < SMA(ATR, 50) OR RSI < 40

    Logic: Volatility expansion often precedes strong moves.
    """

    def __init__(self):
        super().__init__("ATR_Volatility_Expansion")
        self.entry_logic = "ATR(14) > 1.5 * SMA(ATR, 50) AND RSI > 50"
        self.exit_logic = "ATR < SMA(ATR, 50) OR RSI < 40"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate ATR expansion signals."""
        extractor = FeatureExtractor()
        features = extractor.extract(data, symbol="BACKTEST")

        # Calculate ATR and its moving average
        atr_values = [fs.atr_14 for fs in features]
        atr_series = pd.Series(atr_values)
        atr_sma = atr_series.rolling(window=50).mean()

        signals = []
        position = 0

        for i, fs in enumerate(features):
            if i < 50:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Warmup"))
                continue

            atr = fs.atr_14
            atr_avg = float(atr_sma.iloc[i])

            # Entry: ATR expansion + bullish momentum
            if position == 0 and atr > atr_avg * 1.5 and fs.rsi_14 > 50:
                expansion_ratio = atr / atr_avg
                signals.append(RuleSignal(
                    action=1,
                    confidence=min((expansion_ratio - 1.5) / 1.5, 1.0),
                    reason=f"Volatility surge ({expansion_ratio:.2f}x)"
                ))
                position = 1

            # Exit: Volatility normalizes or momentum weakens
            elif position == 1 and (atr < atr_avg or fs.rsi_14 < 40):
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason="Volatility contraction"
                ))
                position = 0

            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

        return signals


class LowVolatilityBreakoutRule(RuleBasedStrategy):
    """Buy on breakout after low volatility compression.

    Entry: ATR < 0.7 * Avg(ATR) AND Price > SMA(50)
    Exit: Price < SMA(20)

    Logic: Volatility compression followed by expansion (coiled spring).
    """

    def __init__(self):
        super().__init__("Low_Vol_Breakout")
        self.entry_logic = "ATR < 0.7 * Avg(ATR) AND Price > SMA(50)"
        self.exit_logic = "Price < SMA(20)"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate low volatility breakout signals."""
        extractor = FeatureExtractor()
        features = extractor.extract(data, symbol="BACKTEST")

        # ATR average
        atr_values = [fs.atr_14 for fs in features]
        atr_series = pd.Series(atr_values)
        atr_avg = atr_series.rolling(window=50).mean()

        # SMA
        sma_50 = data["close"].rolling(window=50).mean()
        sma_20 = data["close"].rolling(window=20).mean()

        signals = []
        position = 0

        for i, fs in enumerate(features):
            if i < 50:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Warmup"))
                continue

            price = float(data["close"].iloc[i])
            atr = fs.atr_14
            atr_a = float(atr_avg.iloc[i])
            sma50_val = float(sma_50.iloc[i])
            sma20_val = float(sma_20.iloc[i])

            # Entry: Low volatility + price in uptrend
            if position == 0 and atr < atr_a * 0.7 and price > sma50_val:
                compression_ratio = atr / atr_a
                signals.append(RuleSignal(
                    action=1,
                    confidence=1.0 - compression_ratio,  # Lower vol = higher confidence
                    reason=f"Volatility squeeze ({compression_ratio:.2f}x)"
                ))
                position = 1

            # Exit: Price breaks SMA(20)
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


class KeltnerChannelRule(RuleBasedStrategy):
    """Buy on Keltner Channel breakout with volume.

    Entry: Price > Keltner_Upper AND Volume > 1.5x Avg
    Exit: Price < EMA(20)

    Logic: Keltner uses ATR for bands, better for volatility-adjusted entries.
    """

    def __init__(self):
        super().__init__("Keltner_Channel_Breakout")
        self.entry_logic = "Price > EMA(20) + 2*ATR AND Volume confirmed"
        self.exit_logic = "Price < EMA(20)"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate Keltner channel signals."""
        extractor = FeatureExtractor()
        features = extractor.extract(data, symbol="BACKTEST")

        # Calculate EMA(20) and Keltner Channels
        ema_20 = data["close"].ewm(span=20, adjust=False).mean()

        # Volume average
        vol_avg = data["volume"].rolling(window=20).mean()

        signals = []
        position = 0

        for i, fs in enumerate(features):
            if i < 20:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Warmup"))
                continue

            price = float(data["close"].iloc[i])
            ema20_val = float(ema_20.iloc[i])
            atr = fs.atr_14

            # Keltner upper band: EMA + 2*ATR
            keltner_upper = ema20_val + (2 * atr)

            volume = float(data["volume"].iloc[i])
            avg_vol = float(vol_avg.iloc[i])

            # Entry: Price above Keltner upper + volume
            if position == 0 and price > keltner_upper and volume > avg_vol * 1.5:
                signals.append(RuleSignal(
                    action=1,
                    confidence=min((volume / avg_vol - 1.5) / 1.5, 1.0),
                    reason=f"Keltner breakout confirmed"
                ))
                position = 1

            # Exit: Price back below EMA
            elif position == 1 and price < ema20_val:
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason="Channel exit"
                ))
                position = 0

            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

        return signals


class ADXTrendStrengthRule(RuleBasedStrategy):
    """Buy when ADX confirms strong trend.

    Entry: ADX > 25 AND +DI > -DI AND Price > SMA(50)
    Exit: ADX < 20 OR +DI < -DI

    Logic: ADX measures trend strength, not direction. Use DI for direction.
    """

    def __init__(self):
        super().__init__("ADX_Trend_Strength")
        self.entry_logic = "ADX > 25 AND +DI > -DI AND Uptrend"
        self.exit_logic = "ADX < 20 OR Trend reverses"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate ADX trend strength signals."""
        extractor = FeatureExtractor()
        features = extractor.extract(data, symbol="BACKTEST")

        # Calculate ADX and Directional Indicators
        # Simplified version - real ADX needs +DI/-DI calculation
        # Using ATR and price movement as proxy
        sma_50 = data["close"].rolling(window=50).mean()

        signals = []
        position = 0

        for i, fs in enumerate(features):
            if i < 50:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Warmup"))
                continue

            price = float(data["close"].iloc[i])
            sma50_val = float(sma_50.iloc[i])

            # Proxy for ADX: High ATR + clear trend
            # In real implementation, would calculate actual ADX
            atr_normalized = fs.atr_14 / price
            trend_strength = abs(price - sma50_val) / sma50_val

            # Simulate ADX > 25 as combination of ATR and trend
            strong_trend = atr_normalized > 0.02 and trend_strength > 0.05

            # Entry: Strong trend confirmed + price above SMA
            if position == 0 and strong_trend and price > sma50_val:
                signals.append(RuleSignal(
                    action=1,
                    confidence=min(trend_strength / 0.10, 1.0),
                    reason=f"Strong uptrend (ADX proxy)"
                ))
                position = 1

            # Exit: Trend weakens or reverses
            elif position == 1 and (not strong_trend or price < sma50_val):
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason="Trend weakening"
                ))
                position = 0

            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

        return signals


class VolatilitySqueezeRule(RuleBasedStrategy):
    """Buy on volatility squeeze breakout (Bollinger inside Keltner).

    Entry: BB_Width < SMA(BB_Width, 20) * 0.5 AND Price > SMA(20)
    Exit: BB_Width > SMA(BB_Width, 20)

    Logic: Bollinger Bands contracting inside Keltner = squeeze.
    """

    def __init__(self):
        super().__init__("Volatility_Squeeze")
        self.entry_logic = "BB_Width < 0.5 * Avg(BB_Width) AND Price > SMA(20)"
        self.exit_logic = "BB_Width expands"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate volatility squeeze signals."""
        extractor = FeatureExtractor()
        features = extractor.extract(data, symbol="BACKTEST")

        # Calculate Bollinger Band width
        sma_20 = data["close"].rolling(window=20).mean()
        std_20 = data["close"].rolling(window=20).std()
        bb_upper = sma_20 + (std_20 * 2)
        bb_lower = sma_20 - (std_20 * 2)
        bb_width = (bb_upper - bb_lower) / sma_20  # Normalized width

        # BB width average
        bb_width_avg = bb_width.rolling(window=20).mean()

        signals = []
        position = 0

        for i in range(len(data)):
            if i < 40:  # Need 40 bars (20 + 20)
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Warmup"))
                continue

            price = float(data["close"].iloc[i])
            sma20_val = float(sma_20.iloc[i])
            width = float(bb_width.iloc[i])
            width_avg = float(bb_width_avg.iloc[i])

            # Entry: Squeeze (width < 50% of average) + uptrend
            if position == 0 and width < width_avg * 0.5 and price > sma20_val:
                compression = width / width_avg
                signals.append(RuleSignal(
                    action=1,
                    confidence=1.0 - compression,  # Tighter = higher confidence
                    reason=f"Volatility squeeze ({compression:.2f}x)"
                ))
                position = 1

            # Exit: Squeeze releases (width expands)
            elif position == 1 and width > width_avg:
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason="Squeeze released"
                ))
                position = 0

            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

        return signals
