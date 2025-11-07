"""
Market Context Builder for LLM Trading System

Transforms raw market data into human-readable context with interpretations.
LLM gets structured narrative instead of raw numbers.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import alpaca_trade_api as tradeapi
from dotenv import load_dotenv


class MarketContextBuilder:
    """Builds rich context for LLM decision making"""

    def __init__(self, api_key: str, api_secret: str):
        self.api = tradeapi.REST(
            api_key,
            api_secret,
            "https://paper-api.alpaca.markets",
            api_version='v2'
        )

    def build_full_context(self, symbol: str) -> Dict:
        """
        Build comprehensive market context for a symbol.

        Returns structured dict with:
        - Price action
        - Technical indicators with interpretations
        - Volume analysis
        - Market context (SPY, VIX, sector)
        - Recent patterns
        """
        # Fetch recent data
        bars = self._fetch_recent_bars(symbol, days=60)

        if bars is None or len(bars) < 50:
            return {'error': f'Insufficient data for {symbol}'}

        # Build context components
        context = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'price_action': self._analyze_price_action(bars),
            'technicals': self._analyze_technicals(bars),
            'volume': self._analyze_volume(bars),
            'market_context': self._get_market_context(),
            'patterns': self._detect_patterns(bars),
            'risk_metrics': self._calculate_risk_metrics(bars)
        }

        # Convert numpy types to Python native types for JSON serialization
        return self._convert_to_native_types(context)

    def _convert_to_native_types(self, obj):
        """Convert numpy types to Python native types for JSON serialization"""
        if isinstance(obj, dict):
            return {key: self._convert_to_native_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_native_types(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj

    def _fetch_recent_bars(self, symbol: str, days: int = 60) -> Optional[pd.DataFrame]:
        """Fetch recent 5min bars"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            bars = self.api.get_bars(
                symbol,
                '5Min',
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                limit=10000,
                feed='iex'  # Use IEX feed for free tier
            ).df

            if bars.empty:
                return None

            bars = bars.reset_index()
            bars['timestamp'] = pd.to_datetime(bars['timestamp'])

            return bars

        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None

    def _analyze_price_action(self, bars: pd.DataFrame) -> Dict:
        """Analyze current price action with context"""
        current = bars.iloc[-1]
        prev_close = bars.iloc[-2]['close']
        day_open = bars[bars['timestamp'].dt.date == current['timestamp'].date()].iloc[0]['close']

        # Calculate price metrics
        change_pct = ((current['close'] - prev_close) / prev_close) * 100
        from_open_pct = ((current['close'] - day_open) / day_open) * 100

        # Day range
        day_high = bars[bars['timestamp'].dt.date == current['timestamp'].date()]['high'].max()
        day_low = bars[bars['timestamp'].dt.date == current['timestamp'].date()]['low'].min()
        range_pct = ((day_high - day_low) / day_low) * 100

        # Position in day range
        if day_high != day_low:
            position_in_range = ((current['close'] - day_low) / (day_high - day_low)) * 100
        else:
            position_in_range = 50.0

        return {
            'current_price': round(current['close'], 2),
            'change_pct': round(change_pct, 2),
            'change_interpretation': self._interpret_price_change(change_pct),
            'from_open_pct': round(from_open_pct, 2),
            'day_high': round(day_high, 2),
            'day_low': round(day_low, 2),
            'day_range_pct': round(range_pct, 2),
            'position_in_range': round(position_in_range, 1),
            'range_position_interpretation': self._interpret_range_position(position_in_range),
            'trend_short_term': self._detect_short_term_trend(bars)
        }

    def _analyze_technicals(self, bars: pd.DataFrame) -> Dict:
        """Calculate technical indicators with interpretations"""
        # RSI
        rsi_14 = self._calculate_rsi(bars, period=14)
        rsi_value = rsi_14.iloc[-1]
        rsi_prev = rsi_14.iloc[-5]

        # MACD
        macd_line, signal_line, histogram = self._calculate_macd(bars)

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(bars)
        current_price = bars.iloc[-1]['close']
        bb_position = ((current_price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])) * 100
        bb_width = ((bb_upper.iloc[-1] - bb_lower.iloc[-1]) / bb_middle.iloc[-1]) * 100

        # Moving Averages
        sma_20 = bars['close'].rolling(20).mean()
        sma_50 = bars['close'].rolling(50).mean()
        ema_12 = bars['close'].ewm(span=12).mean()

        return {
            'rsi_14': {
                'value': round(rsi_value, 1),
                'level': self._interpret_rsi(rsi_value),
                'trend': 'rising' if rsi_value > rsi_prev else 'falling',
                'divergence': self._check_rsi_divergence(bars, rsi_14),
                'interpretation': self._get_rsi_interpretation(rsi_value, rsi_prev)
            },
            'macd': {
                'value': round(macd_line.iloc[-1], 3),
                'signal': round(signal_line.iloc[-1], 3),
                'histogram': round(histogram.iloc[-1], 3),
                'crossover': self._detect_macd_crossover(macd_line, signal_line),
                'trend': self._get_macd_trend(histogram),
                'interpretation': self._get_macd_interpretation(macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1])
            },
            'bollinger_bands': {
                'upper': round(bb_upper.iloc[-1], 2),
                'middle': round(bb_middle.iloc[-1], 2),
                'lower': round(bb_lower.iloc[-1], 2),
                'position_pct': round(bb_position, 1),
                'width_pct': round(bb_width, 2),
                'squeeze': bb_width < 2.0,  # Tight bands = low volatility
                'interpretation': self._get_bb_interpretation(bb_position, bb_width, current_price, bb_upper.iloc[-1], bb_lower.iloc[-1])
            },
            'moving_averages': {
                'sma_20': round(sma_20.iloc[-1], 2),
                'sma_50': round(sma_50.iloc[-1], 2),
                'ema_12': round(ema_12.iloc[-1], 2),
                'price_vs_sma20': self._compare_price_to_ma(current_price, sma_20.iloc[-1]),
                'price_vs_sma50': self._compare_price_to_ma(current_price, sma_50.iloc[-1]),
                'ma_alignment': self._get_ma_alignment(current_price, sma_20.iloc[-1], sma_50.iloc[-1])
            }
        }

    def _analyze_volume(self, bars: pd.DataFrame) -> Dict:
        """Analyze volume with context"""
        current_volume = bars.iloc[-1]['volume']
        avg_volume_20 = bars['volume'].rolling(20).mean().iloc[-1]
        volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 1.0

        # Recent volume trend
        recent_avg = bars['volume'].tail(5).mean()
        older_avg = bars['volume'].tail(20).head(15).mean()
        volume_trending = 'increasing' if recent_avg > older_avg * 1.1 else 'decreasing' if recent_avg < older_avg * 0.9 else 'stable'

        return {
            'current': int(current_volume),
            'avg_20day': int(avg_volume_20),
            'ratio': round(volume_ratio, 2),
            'interpretation': self._interpret_volume(volume_ratio),
            'trend': volume_trending,
            'spike_detected': volume_ratio > 2.0
        }

    def _get_market_context(self) -> Dict:
        """Get broader market context (SPY, VIX)"""
        try:
            # Get SPY for market direction
            spy_bars = self._fetch_recent_bars('SPY', days=5)
            if spy_bars is not None and len(spy_bars) > 0:
                spy_change = ((spy_bars.iloc[-1]['close'] - spy_bars.iloc[-2]['close']) / spy_bars.iloc[-2]['close']) * 100
                spy_trend = 'bullish' if spy_change > 0.5 else 'bearish' if spy_change < -0.5 else 'neutral'
            else:
                spy_change = 0.0
                spy_trend = 'unknown'

            # VIX for volatility (would need separate data source in production)
            # For now, estimate from SPY volatility
            spy_returns = spy_bars['close'].pct_change().tail(20) if spy_bars is not None else pd.Series([0])
            implied_vix = spy_returns.std() * np.sqrt(252) * 100  # Annualized vol

            return {
                'spy_change_pct': round(spy_change, 2),
                'spy_trend': spy_trend,
                'market_sentiment': 'risk-on' if spy_change > 0 else 'risk-off',
                'implied_volatility': round(implied_vix, 1),
                'regime': self._determine_market_regime(implied_vix)
            }
        except Exception as e:
            return {
                'error': f'Could not fetch market context: {e}'
            }

    def _detect_patterns(self, bars: pd.DataFrame) -> Dict:
        """Detect common chart patterns"""
        recent_highs = bars['high'].tail(10)
        recent_lows = bars['low'].tail(10)
        current_price = bars.iloc[-1]['close']

        # Higher highs/lows
        higher_highs = all(recent_highs.iloc[i] >= recent_highs.iloc[i-1] for i in range(1, len(recent_highs)))
        higher_lows = all(recent_lows.iloc[i] >= recent_lows.iloc[i-1] for i in range(1, len(recent_lows)))

        # Support/Resistance
        support_level = recent_lows.tail(20).min()
        resistance_level = recent_highs.tail(20).max()

        return {
            'trend_pattern': 'uptrend' if (higher_highs and higher_lows) else 'downtrend' if not (higher_highs or higher_lows) else 'sideways',
            'near_support': abs(current_price - support_level) / current_price < 0.01,
            'near_resistance': abs(current_price - resistance_level) / current_price < 0.01,
            'support_level': round(support_level, 2),
            'resistance_level': round(resistance_level, 2)
        }

    def _calculate_risk_metrics(self, bars: pd.DataFrame) -> Dict:
        """Calculate risk metrics"""
        returns = bars['close'].pct_change().dropna()

        # ATR (Average True Range)
        high_low = bars['high'] - bars['low']
        high_close = abs(bars['high'] - bars['close'].shift())
        low_close = abs(bars['low'] - bars['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]
        atr_pct = (atr / bars.iloc[-1]['close']) * 100

        return {
            'atr': round(atr, 2),
            'atr_pct': round(atr_pct, 2),
            'volatility_20d': round(returns.tail(20).std() * 100, 2),
            'risk_level': 'high' if atr_pct > 3.0 else 'medium' if atr_pct > 1.5 else 'low'
        }

    # Helper methods for calculations
    def _calculate_rsi(self, bars: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = bars['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, bars: pd.DataFrame, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        ema_fast = bars['close'].ewm(span=fast).mean()
        ema_slow = bars['close'].ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _calculate_bollinger_bands(self, bars: pd.DataFrame, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        middle = bars['close'].rolling(window=period).mean()
        std = bars['close'].rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    # Interpretation helpers
    def _interpret_price_change(self, change_pct: float) -> str:
        if change_pct > 2.0:
            return "strong rally"
        elif change_pct > 0.5:
            return "moderate gain"
        elif change_pct > -0.5:
            return "flat"
        elif change_pct > -2.0:
            return "moderate decline"
        else:
            return "sharp selloff"

    def _interpret_range_position(self, position: float) -> str:
        if position > 80:
            return "near day highs (resistance)"
        elif position > 60:
            return "upper range (bullish)"
        elif position > 40:
            return "mid-range (neutral)"
        elif position > 20:
            return "lower range (bearish)"
        else:
            return "near day lows (support)"

    def _detect_short_term_trend(self, bars: pd.DataFrame) -> str:
        recent_5 = bars['close'].tail(5)
        if all(recent_5.iloc[i] > recent_5.iloc[i-1] for i in range(1, len(recent_5))):
            return "strong uptrend (5 consecutive higher closes)"
        elif all(recent_5.iloc[i] < recent_5.iloc[i-1] for i in range(1, len(recent_5))):
            return "strong downtrend (5 consecutive lower closes)"
        else:
            return "choppy (no clear direction)"

    def _interpret_rsi(self, rsi: float) -> str:
        if rsi > 70:
            return "overbought"
        elif rsi > 60:
            return "strong"
        elif rsi > 40:
            return "neutral"
        elif rsi > 30:
            return "weak"
        else:
            return "oversold"

    def _get_rsi_interpretation(self, rsi: float, rsi_prev: float) -> str:
        level = self._interpret_rsi(rsi)
        trend = "rising" if rsi > rsi_prev else "falling"

        if rsi < 30:
            return f"{level} ({trend}) - potential bounce opportunity but confirm with price action"
        elif rsi > 70:
            return f"{level} ({trend}) - potential pullback risk, consider taking profits"
        else:
            return f"{level} ({trend})"

    def _check_rsi_divergence(self, bars: pd.DataFrame, rsi: pd.Series) -> Optional[str]:
        """Check for bullish/bearish divergence"""
        recent_prices = bars['close'].tail(10)
        recent_rsi = rsi.tail(10)

        # Bullish divergence: price making lower lows, RSI making higher lows
        price_trend = recent_prices.iloc[-1] < recent_prices.iloc[0]
        rsi_trend = recent_rsi.iloc[-1] > recent_rsi.iloc[0]

        if price_trend and not rsi_trend:
            return "bullish divergence detected (price down but RSI up)"
        elif not price_trend and rsi_trend:
            return "bearish divergence detected (price up but RSI down)"

        return None

    def _detect_macd_crossover(self, macd: pd.Series, signal: pd.Series) -> Optional[str]:
        """Detect recent MACD crossovers"""
        if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
            return "bullish crossover just occurred"
        elif macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]:
            return "bearish crossover just occurred"
        elif macd.iloc[-1] > signal.iloc[-1]:
            return "bullish (MACD above signal)"
        else:
            return "bearish (MACD below signal)"

    def _get_macd_trend(self, histogram: pd.Series) -> str:
        recent = histogram.tail(5)
        if all(recent.iloc[i] > recent.iloc[i-1] for i in range(1, len(recent))):
            return "strengthening"
        elif all(recent.iloc[i] < recent.iloc[i-1] for i in range(1, len(recent))):
            return "weakening"
        else:
            return "mixed"

    def _get_macd_interpretation(self, macd: float, signal: float, histogram: float) -> str:
        if macd > signal and histogram > 0:
            return "bullish momentum (MACD above signal, positive histogram)"
        elif macd < signal and histogram < 0:
            return "bearish momentum (MACD below signal, negative histogram)"
        else:
            return "mixed signals (momentum unclear)"

    def _get_bb_interpretation(self, position: float, width: float, price: float, upper: float, lower: float) -> str:
        interpretations = []

        if width < 2.0:
            interpretations.append("BB squeeze detected (low volatility, breakout likely)")

        if position > 95:
            interpretations.append("touching upper band (overbought, potential reversal)")
        elif position < 5:
            interpretations.append("touching lower band (oversold, potential bounce)")
        elif 45 <= position <= 55:
            interpretations.append("near middle band (neutral)")

        return " | ".join(interpretations) if interpretations else "within normal range"

    def _compare_price_to_ma(self, price: float, ma: float) -> str:
        diff_pct = ((price - ma) / ma) * 100
        if diff_pct > 2:
            return f"above by {abs(diff_pct):.1f}% (bullish)"
        elif diff_pct < -2:
            return f"below by {abs(diff_pct):.1f}% (bearish)"
        else:
            return "near MA (neutral)"

    def _get_ma_alignment(self, price: float, sma20: float, sma50: float) -> str:
        if price > sma20 > sma50:
            return "bullish alignment (price > SMA20 > SMA50)"
        elif price < sma20 < sma50:
            return "bearish alignment (price < SMA20 < SMA50)"
        else:
            return "mixed alignment (no clear trend)"

    def _interpret_volume(self, ratio: float) -> str:
        if ratio > 2.0:
            return "exceptional volume (2x+ average) - significant event"
        elif ratio > 1.5:
            return "high volume (1.5x+ average) - strong interest"
        elif ratio > 0.8:
            return "normal volume"
        else:
            return "low volume (weak conviction)"

    def _determine_market_regime(self, implied_vix: float) -> str:
        if implied_vix < 15:
            return "low volatility (calm market, range-bound likely)"
        elif implied_vix < 25:
            return "normal volatility (trending possible)"
        else:
            return "high volatility (choppy, risk elevated)"


if __name__ == "__main__":
    # Test the context builder
    load_dotenv()
    builder = MarketContextBuilder(
        api_key=os.getenv('ALPACA_API_KEY'),
        api_secret=os.getenv('ALPACA_SECRET_KEY')
    )

    # Build context for NVDA
    context = builder.build_full_context('NVDA')

    # Print formatted context
    import json
    print(json.dumps(context, indent=2))
