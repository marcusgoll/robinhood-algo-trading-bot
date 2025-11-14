"""TA Coordinator - Main orchestrator for the Technical Analysis framework.

This is your main interface. It coordinates all 20 technical analysis tools
and provides actionable trading signals with proper risk management.

No astrology. No feelings. Just quantifiable, backtestable signals.
"""

import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

from .enhanced_indicators import EnhancedIndicators
from .market_structure import MarketStructureAnalyzer, MultiTimeframeAnalyzer
from .regime_detector import RegimeDetector
from .pattern_detector import PatternDetector
from .volume_analysis import VolumeAnalyzer
from .risk_calculator import RiskCalculator

logger = logging.getLogger(__name__)


@dataclass
class TASignal:
    """Complete technical analysis signal with all components."""
    # Symbol and timing
    symbol: str
    timestamp: pd.Timestamp

    # Signal direction
    signal: str  # 'LONG', 'SHORT', 'HOLD', 'SKIP'
    confidence: float  # 0-100

    # Entry and exit levels
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Position sizing
    position_size_shares: Optional[float] = None
    position_size_usd: Optional[float] = None
    risk_amount_usd: Optional[float] = None
    reward_amount_usd: Optional[float] = None

    # Risk metrics
    r_multiple: Optional[float] = None
    risk_pct_of_account: Optional[float] = None
    quality_score: Optional[float] = None

    # Supporting analysis
    trend: str = 'unknown'  # Overall trend
    structure: str = 'unknown'  # Market structure
    regime: str = 'unknown'  # Breakout or mean reversion
    pattern: Optional[str] = None  # Chart pattern detected

    # Indicators
    rsi: Optional[float] = None
    macd_signal: Optional[str] = None
    volume_confirmation: bool = False

    # Reasoning
    bullish_factors: List[str] = None
    bearish_factors: List[str] = None
    warnings: List[str] = None
    reasoning: str = ""

    def __post_init__(self):
        """Initialize lists if None."""
        if self.bullish_factors is None:
            self.bullish_factors = []
        if self.bearish_factors is None:
            self.bearish_factors = []
        if self.warnings is None:
            self.warnings = []


class TACoordinator:
    """Coordinate all technical analysis components.

    This is the main class you interact with. It:
    1. Runs all technical analysis tools
    2. Synthesizes signals into actionable recommendations
    3. Calculates proper position sizing and risk management
    4. Provides clear reasoning for each decision

    Usage:
        ta = TACoordinator(account_size=10000)
        signal = ta.analyze(
            symbol='BTCUSD',
            data={'1h': df_1h, '4h': df_4h, '1d': df_1d}
        )

        if signal.signal == 'LONG' and signal.quality_score > 70:
            # Execute trade with signal.position_size_shares
            # Stop at signal.stop_loss
            # Target at signal.take_profit
    """

    def __init__(
        self,
        account_size: float = 10000,
        risk_per_trade: float = 1.0,  # 1% per trade
        min_confidence: float = 60.0,
        min_r_multiple: float = 2.0,
        min_quality_score: float = 50.0
    ):
        """Initialize TA Coordinator.

        Args:
            account_size: Total account size in USD
            risk_per_trade: Max risk per trade as % of account
            min_confidence: Minimum confidence for signals (0-100)
            min_r_multiple: Minimum R-multiple required
            min_quality_score: Minimum quality score for trades
        """
        self.account_size = account_size
        self.risk_per_trade = risk_per_trade
        self.min_confidence = min_confidence
        self.min_r_multiple = min_r_multiple
        self.min_quality_score = min_quality_score

        # Initialize all components
        self.indicators = EnhancedIndicators()
        self.structure_analyzer = MarketStructureAnalyzer()
        self.mtf_analyzer = MultiTimeframeAnalyzer()
        self.regime_detector = RegimeDetector()
        self.pattern_detector = PatternDetector()
        self.volume_analyzer = VolumeAnalyzer()
        self.risk_calculator = RiskCalculator(
            min_r_multiple=min_r_multiple,
            max_risk_per_trade=risk_per_trade
        )

        logger.info(f"TACoordinator initialized with account_size=${account_size:,.2f}")

    def analyze(
        self,
        symbol: str,
        data: Dict[str, pd.DataFrame],
        primary_timeframe: str = '1h',
        win_rate: Optional[float] = None
    ) -> TASignal:
        """Run complete technical analysis and generate trading signal.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSD', 'AAPL')
            data: Dict mapping timeframe to DataFrame
                  e.g., {'15m': df_15m, '1h': df_1h, '4h': df_4h, '1d': df_1d}
            primary_timeframe: Which timeframe to use for entry/exit (default: '1h')
            win_rate: Historical win rate for EV calculation (optional)

        Returns:
            TASignal with complete analysis and trading recommendation

        Process:
            1. Multi-timeframe trend analysis (Tool 1)
            2. Market structure (Tool 2)
            3. Support/Resistance zones (Tool 3)
            4. Regime detection (Tool 4)
            5. Indicators (Tools 5-10)
            6. Volume analysis (Tools 11-13)
            7. Pattern detection (Tools 14-16)
            8. Risk/position sizing (Tools 17-18)
            9. Synthesize into signal
        """
        logger.info(f"Analyzing {symbol} across {len(data)} timeframes")

        if primary_timeframe not in data:
            raise ValueError(f"Primary timeframe {primary_timeframe} not in data")

        primary_df = data[primary_timeframe]
        current_price = float(primary_df['close'].iloc[-1])
        timestamp = primary_df.index[-1] if isinstance(primary_df.index, pd.DatetimeIndex) else pd.Timestamp.now()

        # Lists to track factors
        bullish_factors = []
        bearish_factors = []
        warnings = []

        # 1. Multi-timeframe trend analysis
        mtf_result = self.mtf_analyzer.analyze(data)
        overall_trend = mtf_result['overall_trend']
        trend_confidence = mtf_result['confidence']

        if overall_trend == 'bullish':
            bullish_factors.append(f"Multi-TF trend bullish (confidence: {trend_confidence:.0f}%)")
        elif overall_trend == 'bearish':
            bearish_factors.append(f"Multi-TF trend bearish (confidence: {trend_confidence:.0f}%)")
        else:
            warnings.append("Multi-TF trend mixed - reduce size or wait")

        # 2. Market structure
        structure_result = self.structure_analyzer.analyze(primary_df)

        if structure_result.trend == 'uptrend':
            bullish_factors.append(f"Market structure: {structure_result.structure}")
        elif structure_result.trend == 'downtrend':
            bearish_factors.append(f"Market structure: {structure_result.structure}")

        if structure_result.structure_broken:
            warnings.append(f"Structure broken {structure_result.structure_break_direction}")

        # 3 & 4. Regime detection
        regime_result = self.regime_detector.detect(primary_df)

        # 5-10. Technical indicators
        ma_result = self.indicators.calculate_moving_averages(primary_df)
        rsi_result = self.indicators.calculate_rsi(primary_df)
        macd_result = self.indicators.calculate_macd(primary_df)
        stoch_result = self.indicators.calculate_stochastic(primary_df)
        atr_result = self.indicators.calculate_atr(primary_df)
        bb_result = self.indicators.calculate_bollinger_bands(primary_df)

        # MA analysis
        if ma_result.ma_alignment == 'bullish':
            bullish_factors.append("MA alignment bullish")
        elif ma_result.ma_alignment == 'bearish':
            bearish_factors.append("MA alignment bearish")

        if ma_result.golden_cross:
            bullish_factors.append("Golden cross detected")
        if ma_result.death_cross:
            bearish_factors.append("Death cross detected")

        # RSI analysis
        if rsi_result.bullish_bias:
            bullish_factors.append(f"RSI bullish bias ({rsi_result.rsi:.1f})")
        else:
            bearish_factors.append(f"RSI bearish bias ({rsi_result.rsi:.1f})")

        if rsi_result.divergence == 'bullish':
            bullish_factors.append("Bullish RSI divergence")
        elif rsi_result.divergence == 'bearish':
            bearish_factors.append("Bearish RSI divergence")

        # MACD analysis
        macd_signal = None
        if macd_result.cross_up:
            bullish_factors.append("MACD bullish cross")
            macd_signal = 'bullish'
        elif macd_result.cross_down:
            bearish_factors.append("MACD bearish cross")
            macd_signal = 'bearish'

        # BB analysis
        if bb_result.squeeze:
            warnings.append("Bollinger Band squeeze - breakout imminent")

        # 11-13. Volume analysis
        volume_result = self.volume_analyzer.analyze(
            primary_df,
            price_signal='bullish' if len(bullish_factors) > len(bearish_factors) else 'bearish'
        )

        if volume_result.accumulation_detected:
            bullish_factors.append("Accumulation detected (bullish)")
        if volume_result.distribution_detected:
            bearish_factors.append("Distribution detected (bearish)")
        if volume_result.climax_detected:
            warnings.append("Volume climax - potential reversal")

        # 14-16. Pattern detection
        consolidation = self.pattern_detector.detect_consolidation(primary_df)
        pullback = self.pattern_detector.detect_pullback(
            primary_df, structure_result.trend
        )
        gaps = self.pattern_detector.detect_gaps(primary_df)

        pattern_detected = None
        if consolidation.is_consolidating:
            pattern_detected = consolidation.pattern_type
            if consolidation.breakout_imminent:
                warnings.append(f"{pattern_detected} - breakout imminent")

        # Determine initial signal direction
        bullish_score = len(bullish_factors)
        bearish_score = len(bearish_factors)

        if bullish_score > bearish_score * 1.5:
            signal_direction = 'LONG'
        elif bearish_score > bullish_score * 1.5:
            signal_direction = 'SHORT'
        else:
            signal_direction = 'SKIP'

        # Calculate entry, stop, target
        entry_price = current_price
        stop_loss = None
        take_profit = None

        if signal_direction == 'LONG':
            # Use ATR for stop and target
            atr_value = atr_result.atr
            stop_loss = entry_price - (atr_value * 2)  # 2 ATR stop
            take_profit = entry_price + (atr_value * 4)  # 4 ATR target (2R)

            # Adjust if pullback entry available
            if pullback.pullback_detected:
                stop_loss = pullback.stop_below

        elif signal_direction == 'SHORT':
            atr_value = atr_result.atr
            stop_loss = entry_price + (atr_value * 2)
            take_profit = entry_price - (atr_value * 4)

            if pullback.pullback_detected:
                stop_loss = pullback.stop_below

        # 17-18. Calculate position sizing and risk
        position_size_shares = None
        position_size_usd = None
        risk_amount_usd = None
        reward_amount_usd = None
        r_multiple = None
        risk_pct = None
        quality_score = None

        if signal_direction in ['LONG', 'SHORT'] and stop_loss and take_profit:
            try:
                setup = self.risk_calculator.calculate_complete_setup(
                    symbol=symbol,
                    direction=signal_direction.lower(),
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    account_size=self.account_size,
                    risk_per_trade_pct=self.risk_per_trade,
                    win_rate=win_rate,
                    atr=atr_result.atr
                )

                position_size_shares = setup.position_size_shares
                position_size_usd = setup.position_size_usd
                risk_amount_usd = setup.risk_amount_usd
                reward_amount_usd = setup.reward_amount_usd
                r_multiple = setup.r_multiple
                risk_pct = setup.risk_pct_of_account
                quality_score = setup.quality_score

                # Filter by risk/quality thresholds
                if r_multiple < self.min_r_multiple:
                    warnings.append(f"R-multiple too low ({r_multiple:.2f}R < {self.min_r_multiple}R)")
                    signal_direction = 'SKIP'

                if quality_score < self.min_quality_score:
                    warnings.append(f"Quality score too low ({quality_score:.0f} < {self.min_quality_score})")
                    signal_direction = 'SKIP'

            except Exception as e:
                logger.error(f"Error calculating risk: {e}")
                warnings.append(f"Risk calculation error: {e}")
                signal_direction = 'SKIP'

        # Calculate confidence
        total_factors = bullish_score + bearish_score
        if total_factors == 0:
            confidence = 0.0
        else:
            max_score = max(bullish_score, bearish_score)
            confidence = (max_score / total_factors) * 100

        # Adjust confidence by regime and structure
        if regime_result.regime == 'transitional':
            confidence *= 0.8  # Reduce confidence in unclear regime

        if structure_result.confidence < 50:
            confidence *= 0.9  # Reduce confidence with unclear structure

        # Build reasoning
        reasoning_parts = []
        reasoning_parts.append(f"Trend: {overall_trend.upper()}")
        reasoning_parts.append(f"Structure: {structure_result.structure}")
        reasoning_parts.append(f"Regime: {regime_result.regime}")
        reasoning_parts.append(f"Bullish factors: {bullish_score}, Bearish factors: {bearish_score}")

        if signal_direction != 'SKIP':
            reasoning_parts.append(f"R-multiple: {r_multiple:.2f}R")
            reasoning_parts.append(f"Quality score: {quality_score:.0f}/100")

        reasoning = " | ".join(reasoning_parts)

        # Final filtering
        if confidence < self.min_confidence:
            warnings.append(f"Confidence too low ({confidence:.0f}% < {self.min_confidence}%)")
            signal_direction = 'SKIP'

        # Create signal
        signal = TASignal(
            symbol=symbol,
            timestamp=timestamp,
            signal=signal_direction,
            confidence=confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size_shares=position_size_shares,
            position_size_usd=position_size_usd,
            risk_amount_usd=risk_amount_usd,
            reward_amount_usd=reward_amount_usd,
            r_multiple=r_multiple,
            risk_pct_of_account=risk_pct,
            quality_score=quality_score,
            trend=overall_trend,
            structure=structure_result.structure,
            regime=regime_result.regime,
            pattern=pattern_detected,
            rsi=rsi_result.rsi,
            macd_signal=macd_signal,
            volume_confirmation=volume_result.volume_confirmation,
            bullish_factors=bullish_factors,
            bearish_factors=bearish_factors,
            warnings=warnings,
            reasoning=reasoning
        )

        logger.info(
            f"{symbol} signal: {signal.signal} "
            f"(confidence: {confidence:.0f}%, quality: {quality_score or 0:.0f}/100)"
        )

        return signal

    def analyze_simple(
        self,
        symbol: str,
        df: pd.DataFrame,
        win_rate: Optional[float] = None
    ) -> TASignal:
        """Simplified analysis with single timeframe.

        Args:
            symbol: Trading symbol
            df: DataFrame with OHLCV data
            win_rate: Historical win rate (optional)

        Returns:
            TASignal with analysis
        """
        # Use same timeframe for all analysis
        return self.analyze(
            symbol=symbol,
            data={'main': df},
            primary_timeframe='main',
            win_rate=win_rate
        )

    def to_dict(self, signal: TASignal) -> dict:
        """Convert TASignal to dictionary for serialization."""
        return asdict(signal)

    def print_signal(self, signal: TASignal):
        """Print formatted signal to console."""
        print(f"\n{'='*80}")
        print(f"TA SIGNAL: {signal.symbol}")
        print(f"{'='*80}")
        print(f"Signal: {signal.signal} | Confidence: {signal.confidence:.1f}%")
        print(f"Trend: {signal.trend} | Structure: {signal.structure} | Regime: {signal.regime}")

        if signal.signal != 'SKIP':
            print(f"\nENTRY & EXIT:")
            print(f"  Entry: ${signal.entry_price:.2f}")
            print(f"  Stop: ${signal.stop_loss:.2f}")
            print(f"  Target: ${signal.take_profit:.2f}")
            print(f"  R-Multiple: {signal.r_multiple:.2f}R")

            print(f"\nPOSITION SIZING:")
            print(f"  Shares: {signal.position_size_shares:.2f}")
            print(f"  USD: ${signal.position_size_usd:.2f}")
            print(f"  Risk: ${signal.risk_amount_usd:.2f} ({signal.risk_pct_of_account:.2f}% of account)")
            print(f"  Quality Score: {signal.quality_score:.0f}/100")

        print(f"\nBULLISH FACTORS ({len(signal.bullish_factors)}):")
        for factor in signal.bullish_factors:
            print(f"  ✓ {factor}")

        print(f"\nBEARISH FACTORS ({len(signal.bearish_factors)}):")
        for factor in signal.bearish_factors:
            print(f"  ✗ {factor}")

        if signal.warnings:
            print(f"\nWARNINGS:")
            for warning in signal.warnings:
                print(f"  ⚠ {warning}")

        print(f"\nREASONING:")
        print(f"  {signal.reasoning}")
        print(f"{'='*80}\n")
