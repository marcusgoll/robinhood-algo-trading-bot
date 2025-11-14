"""Momentum-based trading rules.

These rules follow trend and momentum indicators.
Based on well-known technical analysis principles.
"""

from __future__ import annotations

import logging

import pandas as pd

from trading_bot.ml.features import FeatureExtractor
from trading_bot.ml.generators.rule_based import RuleBasedStrategy, RuleSignal

logger = logging.getLogger(__name__)


class RSIOversoldRule(RuleBasedStrategy):
    """Buy when RSI oversold AND price above long-term trend.

    Entry: RSI(14) < 30 AND Price > SMA(50)
    Exit: RSI(14) > 70 OR Price < SMA(50)

    Logic: Buy dips in an uptrend.
    """

    def __init__(self):
        super().__init__("RSI_Oversold")
        self.entry_logic = "RSI(14) < 30 AND Price > SMA(50)"
        self.exit_logic = "RSI(14) > 70 OR Price < SMA(50)"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate buy signals on oversold conditions in uptrend."""
        extractor = FeatureExtractor()
        features = extractor.extract(data, symbol="BACKTEST")

        signals = []
        position = 0  # Track current position

        for i, fs in enumerate(features):
            price = float(data["close"].iloc[i])
            sma_50 = price / fs.price_to_sma50 if fs.price_to_sma50 > 0 else price

            # Entry condition
            if position == 0 and fs.rsi_14 < 30 and price > sma_50:
                signals.append(RuleSignal(
                    action=1,
                    confidence=min((30 - fs.rsi_14) / 30, 1.0),  # More oversold = higher confidence
                    reason=f"RSI oversold ({fs.rsi_14:.1f}) in uptrend"
                ))
                position = 1

            # Exit condition
            elif position == 1 and (fs.rsi_14 > 70 or price < sma_50):
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason=f"RSI overbought or trend broken"
                ))
                position = 0

            # Hold
            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

        return signals


class RSIOverboughtShortRule(RuleBasedStrategy):
    """Short when RSI overbought AND price below trend.

    Entry: RSI(14) > 70 AND Price < SMA(50)
    Exit: RSI(14) < 30

    Logic: Fade rallies in a downtrend.
    Note: Converted to long-only by inverting - exit when oversold.
    """

    def __init__(self):
        super().__init__("RSI_Overbought_Fade")
        self.entry_logic = "RSI(14) < 40 AND Price < SMA(50)"  # Inverted for long-only
        self.exit_logic = "RSI(14) > 60"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate signals to buy oversold in downtrend (contrarian)."""
        extractor = FeatureExtractor()
        features = extractor.extract(data, symbol="BACKTEST")

        signals = []
        position = 0

        for i, fs in enumerate(features):
            price = float(data["close"].iloc[i])
            sma_50 = price / fs.price_to_sma50 if fs.price_to_sma50 > 0 else price

            # Entry: Oversold in downtrend (mean reversion)
            if position == 0 and fs.rsi_14 < 40 and price < sma_50:
                signals.append(RuleSignal(
                    action=1,
                    confidence=min((40 - fs.rsi_14) / 40, 1.0),
                    reason=f"Oversold bounce in downtrend ({fs.rsi_14:.1f})"
                ))
                position = 1

            # Exit: RSI recovers
            elif position == 1 and fs.rsi_14 > 60:
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason="Mean reversion complete"
                ))
                position = 0

            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

        return signals


class MACDBullishCrossRule(RuleBasedStrategy):
    """Buy on MACD bullish crossover below zero.

    Entry: MACD crosses above Signal AND MACD < 0
    Exit: MACD crosses below Signal

    Logic: Early trend reversal from bearish to bullish.
    """

    def __init__(self):
        super().__init__("MACD_Bullish_Cross")
        self.entry_logic = "MACD crosses above Signal AND MACD < 0"
        self.exit_logic = "MACD crosses below Signal"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate signals on MACD crossover."""
        extractor = FeatureExtractor()
        features = extractor.extract(data, symbol="BACKTEST")

        signals = []
        position = 0
        prev_macd = 0.0
        prev_signal = 0.0

        for i, fs in enumerate(features):
            macd = fs.macd
            macd_signal = fs.macd_signal  # MACD signal line

            # Detect crossover
            bullish_cross = (macd > macd_signal and prev_macd <= prev_signal)
            bearish_cross = (macd < macd_signal and prev_macd >= prev_signal)

            # Entry: Bullish cross below zero
            if position == 0 and bullish_cross and macd < 0:
                signals.append(RuleSignal(
                    action=1,
                    confidence=min(abs(macd) / 10, 1.0),  # Farther below zero = stronger signal
                    reason=f"MACD bullish cross at {macd:.3f}"
                ))
                position = 1

            # Exit: Bearish cross
            elif position == 1 and bearish_cross:
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason="MACD bearish cross"
                ))
                position = 0

            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

            prev_macd = macd
            prev_signal = macd_signal

        return signals


class MACDTrendRule(RuleBasedStrategy):
    """Buy when MACD confirms uptrend.

    Entry: MACD > Signal AND Price > SMA(200)
    Exit: MACD < Signal OR Price < SMA(200)

    Logic: Trend following with momentum confirmation.
    """

    def __init__(self):
        super().__init__("MACD_Trend_Following")
        self.entry_logic = "MACD > Signal AND Price > SMA(200)"
        self.exit_logic = "MACD < Signal OR Price < SMA(200)"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate trend-following signals."""
        extractor = FeatureExtractor()
        features = extractor.extract(data, symbol="BACKTEST")

        # Calculate SMA(200)
        sma_200 = data["close"].rolling(window=200).mean()

        signals = []
        position = 0

        for i, fs in enumerate(features):
            if i < 200:  # Need 200 bars for SMA
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Warmup"))
                continue

            price = float(data["close"].iloc[i])
            sma200_val = float(sma_200.iloc[i])

            macd = fs.macd
            macd_signal = fs.macd_signal

            # Entry: MACD bullish AND above SMA(200)
            if position == 0 and macd > macd_signal and price > sma200_val:
                signals.append(RuleSignal(
                    action=1,
                    confidence=min((price - sma200_val) / sma200_val * 10, 1.0),
                    reason=f"Uptrend confirmed (MACD={macd:.3f})"
                ))
                position = 1

            # Exit: MACD bearish OR below SMA(200)
            elif position == 1 and (macd < macd_signal or price < sma200_val):
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason="Trend weakening"
                ))
                position = 0

            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

        return signals


class MomentumVolumeRule(RuleBasedStrategy):
    """Buy on price breakout with volume confirmation.

    Entry: Price > SMA(20) AND Volume > 1.5x Average
    Exit: Price < SMA(20) OR Volume drops

    Logic: Volume confirms price breakouts.
    """

    def __init__(self):
        super().__init__("Momentum_Volume_Breakout")
        self.entry_logic = "Price > SMA(20) AND Volume > 1.5 * Avg(Volume)"
        self.exit_logic = "Price < SMA(20)"

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate volume-confirmed momentum signals."""
        extractor = FeatureExtractor()
        features = extractor.extract(data, symbol="BACKTEST")

        # Calculate volume average
        vol_avg = data["volume"].rolling(window=20).mean()

        signals = []
        position = 0

        for i, fs in enumerate(features):
            if i < 20:  # Need 20 bars
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Warmup"))
                continue

            price = float(data["close"].iloc[i])
            sma_20 = price / fs.price_to_sma20 if fs.price_to_sma20 > 0 else price
            volume = float(data["volume"].iloc[i])
            avg_vol = float(vol_avg.iloc[i])

            # Entry: Price breakout + volume surge
            if position == 0 and price > sma_20 and volume > avg_vol * 1.5:
                signals.append(RuleSignal(
                    action=1,
                    confidence=min((volume / avg_vol - 1.5) / 1.5, 1.0),
                    reason=f"Volume breakout ({volume/avg_vol:.1f}x avg)"
                ))
                position = 1

            # Exit: Price falls below SMA(20)
            elif position == 1 and price < sma_20:
                signals.append(RuleSignal(
                    action=-1,
                    confidence=1.0,
                    reason="Momentum broken"
                ))
                position = 0

            else:
                signals.append(RuleSignal(action=0, confidence=0.0, reason="Hold"))

        return signals
