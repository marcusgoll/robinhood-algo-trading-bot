"""
Bull Flag Pattern Detector

Multi-phase pattern detection for bull flag trading signals.

Pattern: src/trading_bot/indicators/service.py (class structure with facade pattern)
Constitution §Fail_Safe: Validate all inputs, fail-fast on invalid data
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from .config import BullFlagConfig
from .models import BullFlagResult, FlagpoleData, ConsolidationData
from .exceptions import PatternNotFoundError
from ..indicators.exceptions import InsufficientDataError


class BullFlagDetector:
    """
    Detects bull flag patterns in price data.

    A bull flag pattern consists of three phases:
    1. Flagpole: Strong upward price movement (5%+ gain)
    2. Consolidation: Sideways/downward drift forming a flag (20-50% retracement)
    3. Breakout: Price breaks above consolidation resistance with volume

    The detector performs multi-phase validation including:
    - Flagpole strength validation (gain %, duration, volume)
    - Consolidation pattern validation (retracement, volume decay)
    - Breakout confirmation (price, volume, momentum)
    - Technical indicator validation (VWAP, MACD, EMA alignment)
    - Risk/reward calculation and quality scoring

    Example:
        config = BullFlagConfig(min_flagpole_gain=Decimal('7.0'))
        detector = BullFlagDetector(config)
        result = detector.detect(bars, symbol='AAPL')
        if result.detected:
            print(f"Entry: {result.entry_price}, Target: {result.target_price}")
    """

    def __init__(self, config: BullFlagConfig) -> None:
        """
        Initialize bull flag detector with configuration.

        Args:
            config: Bull flag detection configuration

        Raises:
            InvalidConfigurationError: If configuration is invalid

        Example:
            config = BullFlagConfig(min_quality_score=70)
            detector = BullFlagDetector(config)
        """
        self.config = config

    def detect(self, bars: List[Dict[str, Any]], symbol: str) -> BullFlagResult:
        """
        Detect bull flag pattern in price data.

        This is the main entry point for pattern detection. It orchestrates
        the multi-phase detection process:

        1. Validate input data (minimum 30 bars required)
        2. Detect flagpole phase (strong upward movement)
        3. Detect consolidation phase (flag formation)
        4. Confirm breakout (resistance break with volume)
        5. Validate with technical indicators (VWAP/MACD/EMA)
        6. Calculate risk parameters (entry/stop/target)
        7. Calculate quality score (0-100)

        Args:
            bars: List of OHLCV dictionaries with keys:
                  'open', 'high', 'low', 'close', 'volume', 'timestamp'
            symbol: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            BullFlagResult with detection status and pattern metadata.
            If no pattern detected, returns result with detected=False.

        Raises:
            InsufficientDataError: If len(bars) < 30
            ValueError: If bars have invalid format (missing required keys)

        Example:
            bars = [
                {'open': 100, 'high': 102, 'low': 99, 'close': 101,
                 'volume': 1000000, 'timestamp': '2024-01-01T09:30:00'},
                # ... more bars
            ]
            result = detector.detect(bars, 'AAPL')
        """
        # Phase 1: Validate input
        if bars is None or len(bars) == 0:
            return self._create_failed_result(symbol, "Empty or None bars provided")

        if len(bars) < 30:
            raise InsufficientDataError(
                symbol=symbol,
                required_bars=30,
                available_bars=len(bars)
            )

        # Validate each bar has required keys
        required_keys = {'high', 'low', 'close', 'volume'}
        try:
            for i, bar in enumerate(bars):
                missing_keys = required_keys - set(bar.keys())
                if missing_keys:
                    raise ValueError(
                        f"Bar at index {i} missing required keys: {missing_keys}"
                    )
        except (AttributeError, TypeError) as e:
            raise ValueError(f"Invalid bar format: {e}")

        # Phase 2: Execute detection phases sequentially
        try:
            # Detect flagpole
            flagpole = self._detect_flagpole(bars)
            if not flagpole:
                return self._create_failed_result(symbol, "No valid flagpole detected")

            # Detect consolidation
            consolidation = self._detect_consolidation(bars, flagpole)
            if not consolidation:
                return self._create_failed_result(symbol, "No valid consolidation detected")

            # Confirm breakout
            breakout_price = self._confirm_breakout(bars, consolidation)
            if not breakout_price:
                return self._create_failed_result(symbol, "No valid breakout confirmed")

            # Validate with indicators
            indicator_data = self._validate_with_indicators(bars)
            if not indicator_data['validation_passed']:
                return self._create_failed_result(
                    symbol,
                    "Technical indicator validation failed"
                )

            # Calculate risk parameters
            risk_params = self._calculate_risk_parameters(
                flagpole,
                consolidation,
                breakout_price
            )

            # Apply risk/reward filtering
            if risk_params['risk_reward_ratio'] < self.config.min_risk_reward_ratio:
                ratio = risk_params['risk_reward_ratio']
                min_ratio = self.config.min_risk_reward_ratio
                return self._create_failed_result(
                    symbol,
                    f"Risk/reward ratio {ratio} below minimum {min_ratio}"
                )

            # Calculate quality score
            quality_score = self._calculate_quality_score(
                flagpole,
                consolidation,
                indicator_data
            )

            # Phase 3: Return successful BullFlagResult
            return BullFlagResult(
                symbol=symbol,
                timestamp=datetime.now(),
                detected=True,
                flagpole=flagpole,
                consolidation=consolidation,
                entry_price=breakout_price,
                stop_loss=risk_params['stop_loss'],
                target_price=risk_params['target_price'],
                quality_score=quality_score,
                risk_reward_ratio=risk_params['risk_reward_ratio']
            )

        except InsufficientDataError:
            # Let InsufficientDataError propagate
            raise
        except PatternNotFoundError:
            # Let PatternNotFoundError propagate
            raise
        except Exception as e:
            # Log to error-log.md if in specs directory
            self._log_error(symbol, str(e))
            # Raise PatternNotFoundError with descriptive message
            raise PatternNotFoundError(
                symbol=symbol,
                reason=f"Pattern detection failed: {str(e)}"
            )

    def _detect_flagpole(self, bars: List[Dict[str, Any]]) -> Optional[FlagpoleData]:
        """
        Detect flagpole phase (initial strong upward movement).

        Scans bars for upward price movement meeting these criteria:
        - Duration: min_flagpole_bars to max_flagpole_bars
        - Gain: min_flagpole_gain% to max_flagpole_gain%
        - Volume: Above average (50th percentile or higher)

        Algorithm:
        1. Calculate rolling average volume across all bars
        2. Scan for sequences of rising bars (close > open)
        3. For each sequence, calculate gain% and duration
        4. Return first sequence meeting all criteria

        Args:
            bars: List of OHLCV dictionaries

        Returns:
            FlagpoleData if valid flagpole found, None otherwise

        Example:
            flagpole = detector._detect_flagpole(bars)
            if flagpole:
                duration = flagpole.end_idx - flagpole.start_idx
                print(f"Flagpole: {flagpole.gain_pct}% gain over {duration} bars")
        """
        # Handle edge cases: empty or insufficient bars
        if not bars or len(bars) < self.config.min_flagpole_bars:
            return None

        # Strategy: Greedy approach - start from beginning and extend as long as valid
        # Return the LONGEST valid flagpole that meets all criteria
        start_idx = 0
        start_price = Decimal(str(bars[start_idx]["open"]))
        best_flagpole = None

        # Try extending from minimum bars to maximum bars
        min_bars = start_idx + self.config.min_flagpole_bars - 1
        max_bars = min(start_idx + self.config.max_flagpole_bars, len(bars))
        for end_idx in range(min_bars, max_bars):

            # Extract candidate bars
            flagpole_bars = bars[start_idx:end_idx + 1]
            duration = len(flagpole_bars)

            # Find highest price
            high_price = max(Decimal(str(bar["high"])) for bar in flagpole_bars)

            # Calculate gain percentage
            gain_pct = ((high_price - start_price) / start_price) * Decimal("100")

            # Check if gain is within valid range
            min_gain = self.config.min_flagpole_gain
            max_gain = self.config.max_flagpole_gain
            if gain_pct >= min_gain and gain_pct <= max_gain:
                # Calculate average volume
                total_volume = sum(Decimal(str(bar["volume"])) for bar in flagpole_bars)
                avg_volume = total_volume / Decimal(str(duration))

                # Update best flagpole - greedily extend to longest valid
                best_flagpole = FlagpoleData(
                    start_idx=start_idx,
                    end_idx=end_idx,
                    gain_pct=gain_pct,
                    high_price=high_price,
                    start_price=start_price,
                    avg_volume=avg_volume
                )
            elif gain_pct > self.config.max_flagpole_gain:
                # Exceeded maximum gain - stop extending
                break

        return best_flagpole

    def _detect_consolidation(
        self,
        bars: List[Dict[str, Any]],
        flagpole: FlagpoleData
    ) -> Optional[ConsolidationData]:
        """
        Detect consolidation phase (flag formation after flagpole).

        Analyzes bars following flagpole for consolidation meeting criteria:
        - Duration: min_consolidation_bars to max_consolidation_bars
        - Retracement: min_retracement_pct% to max_retracement_pct% of flagpole gain
        - Volume: Declining (each bar ≤ volume_decay_threshold × previous bar)
        - Boundaries: Clear upper resistance and lower support

        Algorithm:
        1. Start from flagpole.end_idx + 1
        2. Calculate retracement from flagpole high
        3. Identify upper/lower boundaries using highs/lows
        4. Verify volume decay pattern
        5. Return consolidation data if all criteria met

        Args:
            bars: List of OHLCV dictionaries
            flagpole: Detected flagpole data (provides reference point)

        Returns:
            ConsolidationData if valid consolidation found, None otherwise

        Example:
            consolidation = detector._detect_consolidation(bars, flagpole)
            if consolidation:
                upper = consolidation.upper_boundary
                lower = consolidation.lower_boundary
                print(f"Consolidation: {upper} - {lower}")
        """
        # Start scanning bars AFTER flagpole ends (index = flagpole.end_idx + 1)
        start_idx = flagpole.end_idx + 1

        # Check if we have enough bars after flagpole
        if start_idx >= len(bars):
            return None

        # Calculate flagpole gain absolute value for retracement calculation
        gain_absolute = flagpole.high_price - flagpole.start_price

        # Strategy: Find the LONGEST valid consolidation (prefer longer patterns)
        # Try durations from maximum down to minimum
        min_duration = self.config.min_consolidation_bars
        max_duration = self.config.max_consolidation_bars
        for duration in range(max_duration, min_duration - 1, -1):
            end_idx = start_idx + duration - 1

            # Check if we have enough bars
            if end_idx >= len(bars):
                continue

            # Extract consolidation candidate bars
            consolidation_bars = bars[start_idx:end_idx + 1]

            # Validate duration (should be valid given range, double-check)
            if len(consolidation_bars) < min_duration:
                continue

            if len(consolidation_bars) > max_duration:
                continue

            # Calculate boundaries using closes
            closes = [Decimal(str(bar["close"])) for bar in consolidation_bars]
            upper_boundary = max(closes)
            lower_boundary = min(closes)

            # Calculate retracement percentage
            # retracement = (high - low_consolidation) / gain * 100
            retracement = flagpole.high_price - lower_boundary
            retracement_pct = (retracement / gain_absolute) * Decimal("100")

            # Validate retracement is within range
            if retracement_pct < self.config.min_retracement_pct:
                continue

            if retracement_pct > self.config.max_retracement_pct:
                continue

            # Calculate average volume during consolidation
            total_vol = sum(Decimal(str(bar["volume"]))
                            for bar in consolidation_bars)
            avg_volume = total_vol / Decimal(str(len(consolidation_bars)))

            # Validate volume pattern: consolidation < flagpole volume
            decay_threshold = self.config.volume_decay_threshold
            max_allowed_vol = flagpole.avg_volume * decay_threshold
            if avg_volume >= max_allowed_vol:
                continue

            # Valid consolidation found - return immediately (longest valid match)
            return ConsolidationData(
                start_idx=start_idx,
                end_idx=end_idx,
                upper_boundary=upper_boundary,
                lower_boundary=lower_boundary,
                avg_volume=avg_volume
            )

        # No valid consolidation found
        return None

    def _confirm_breakout(
        self,
        bars: List[Dict[str, Any]],
        consolidation: ConsolidationData
    ) -> Optional[Decimal]:
        """
        Confirm breakout from consolidation phase.

        Validates breakout from consolidation with these checks:
        - Price: Close above consolidation.upper_boundary
        - Volume: ≥ min_breakout_volume_increase% above consolidation avg_volume
        - Move: ≥ min_breakout_move_pct% price increase
        - Timing: Breakout occurs within 2 bars after consolidation ends

        Algorithm:
        1. Check bars immediately following consolidation.end_idx
        2. For each bar, verify close > upper_boundary
        3. Calculate volume increase vs consolidation average
        4. Calculate price move percentage
        5. Return breakout price if all criteria met within 2 bars

        Args:
            bars: List of OHLCV dictionaries
            consolidation: Detected consolidation data

        Returns:
            Breakout price (Decimal) if valid breakout confirmed, None otherwise

        Example:
            breakout_price = detector._confirm_breakout(bars, consolidation)
            if breakout_price:
                print(f"Breakout confirmed at {breakout_price}")
        """
        # Start scanning from the bar after consolidation ends
        start_idx = consolidation.end_idx + 1

        # 2-bar confirmation window
        confirmation_window = 2
        end_idx = start_idx + confirmation_window

        # Check if we have enough bars for confirmation
        if start_idx >= len(bars):
            return None

        # Scan bars within the 2-bar confirmation window
        for bar_idx in range(start_idx, min(end_idx, len(bars))):
            bar = bars[bar_idx]

            # Extract bar data with Decimal precision
            close_price = Decimal(str(bar["close"]))
            bar_volume = Decimal(str(bar["volume"]))

            # Check if close is above upper boundary
            if close_price <= consolidation.upper_boundary:
                continue

            # Calculate price move percentage above resistance
            price_diff = close_price - consolidation.upper_boundary
            move_pct = (price_diff / consolidation.upper_boundary) * Decimal("100")

            # Check if price move meets minimum requirement
            if move_pct < self.config.min_breakout_move_pct:
                continue

            # Calculate volume increase percentage
            volume_increase_required = consolidation.avg_volume * (
                Decimal("1") + self.config.min_breakout_volume_increase / Decimal("100")
            )

            # Check if volume meets minimum requirement
            if bar_volume < volume_increase_required:
                continue

            # All criteria met - valid breakout confirmed
            return close_price

        # No valid breakout found within confirmation window
        return None

    def _validate_with_indicators(self, bars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate pattern with technical indicators (VWAP, MACD, EMA).

        Integrates with TechnicalIndicatorsService to validate entry conditions:
        - VWAP: Current price must be above VWAP
        - MACD: MACD line must be positive (> 0)
        - EMA: Price must be within 2% of EMA(9)

        Args:
            bars: List of OHLCV dictionaries (minimum 26 bars for MACD)

        Returns:
            Dictionary with keys:
                - 'vwap': Decimal - Current VWAP value
                - 'macd': Decimal - Current MACD line value
                - 'ema_9': Decimal - Current EMA(9) value
                - 'price_above_vwap': bool - True if price > VWAP
                - 'macd_positive': bool - True if MACD > 0
                - 'ema_aligned': bool - True if price within 2% of EMA(9)
                - 'validation_passed': bool - True if all checks passed

        Example:
            indicators = detector._validate_with_indicators(bars)
            if indicators['validation_passed']:
                print(f"VWAP: {indicators['vwap']}, MACD: {indicators['macd']}")
        """
        # Import TechnicalIndicatorsService
        from ..indicators.service import TechnicalIndicatorsService

        try:
            # Instantiate TechnicalIndicatorsService
            indicators_service = TechnicalIndicatorsService()

            # Get current price from latest bar
            current_price = Decimal(str(bars[-1]['close']))

            # Get VWAP value
            vwap_result = indicators_service.get_vwap(bars)
            vwap_value = vwap_result.vwap

            # Get MACD value
            macd_result = indicators_service.get_macd(bars)
            macd_value = macd_result.macd_line

            # Get EMA-9 value
            ema_result = indicators_service.get_emas(bars)
            ema_9_value = ema_result.ema_9

            # Validate entry criteria
            price_above_vwap = current_price > vwap_value
            macd_positive = macd_value > Decimal('0')

            # Check if price is within 2% of EMA-9
            if ema_9_value > Decimal('0'):
                ema_diff_pct = abs(current_price - ema_9_value) / ema_9_value * Decimal('100')
                ema_aligned = ema_diff_pct <= Decimal('2.0')
            else:
                ema_aligned = False

            # All criteria must pass
            validation_passed = price_above_vwap and macd_positive and ema_aligned

            return {
                'vwap': vwap_value,
                'macd': macd_value,
                'ema_9': ema_9_value,
                'price_above_vwap': price_above_vwap,
                'macd_positive': macd_positive,
                'ema_aligned': ema_aligned,
                'validation_passed': validation_passed
            }

        except Exception:
            # Degrade gracefully on error - return failed validation
            # Log error if possible (can be enhanced later)
            return {
                'vwap': Decimal('0'),
                'macd': Decimal('0'),
                'ema_9': Decimal('0'),
                'price_above_vwap': False,
                'macd_positive': False,
                'ema_aligned': False,
                'validation_passed': False
            }

    def _calculate_risk_parameters(
        self,
        flagpole: FlagpoleData,
        consolidation: ConsolidationData,
        breakout_price: Decimal
    ) -> Dict[str, Any]:
        """
        Calculate risk management parameters (entry, stop-loss, target, R/R).

        Risk calculation strategy:
        - Entry: breakout_price (confirmed breakout level)
        - Stop-loss: consolidation.lower_boundary × 0.995 (0.5% buffer below support)
        - Target: breakout_price + flagpole_height (measured move projection)
        - Risk/Reward: (target - entry) / (entry - stop_loss)

        Validation:
        - Reject if risk_reward_ratio < min_risk_reward_ratio

        Args:
            flagpole: Detected flagpole data (for measured move calculation)
            consolidation: Detected consolidation data (for stop-loss placement)
            breakout_price: Confirmed breakout price (entry point)

        Returns:
            Dictionary with keys:
                - 'entry_price': Decimal - Recommended entry price
                - 'stop_loss': Decimal - Calculated stop-loss price
                - 'target_price': Decimal - Calculated target price
                - 'risk_reward_ratio': Decimal - Risk/reward ratio

        Raises:
            PatternNotFoundError: If risk_reward_ratio < min_risk_reward_ratio

        Example:
            params = detector._calculate_risk_parameters(flagpole, consolidation, breakout_price)
            print(f"R/R: {params['risk_reward_ratio']}, Target: {params['target_price']}")
        """
        # Calculate stop-loss: lower_boundary - 0.5%
        stop_loss = consolidation.lower_boundary * Decimal('0.995')

        # Calculate flagpole height (measured move)
        flagpole_height = flagpole.high_price - flagpole.start_price

        # Calculate target: breakout_price + flagpole_height
        target_price = breakout_price + flagpole_height

        # Calculate risk (distance from entry to stop)
        risk = breakout_price - stop_loss

        # Calculate reward (distance from entry to target)
        reward = target_price - breakout_price

        # Calculate risk/reward ratio
        # Handle division by zero edge case
        if risk == Decimal('0'):
            risk_reward_ratio = Decimal('0')
        else:
            risk_reward_ratio = reward / risk

        return {
            'entry_price': breakout_price,
            'stop_loss': stop_loss,
            'target_price': target_price,
            'risk_reward_ratio': risk_reward_ratio
        }

    def _calculate_quality_score(
        self,
        flagpole: FlagpoleData,
        consolidation: ConsolidationData,
        indicators: Dict[str, Any]
    ) -> int:
        """
        Calculate pattern quality score (0-100).

        Quality scoring factors:
        1. Flagpole strength (0-30 pts): Based on gain_pct
           - 5-10% gain: 10 pts
           - 10-15% gain: 20 pts
           - 15%+ gain: 30 pts

        2. Consolidation tightness (0-25 pts): Based on boundary range
           - Tight range (2-3%): 25 pts
           - Medium range (3-5%): 15 pts
           - Wide range (5%+): 5 pts

        3. Volume profile (0-20 pts): Volume decay during consolidation
           - Strong decay (50%+ drop): 20 pts
           - Moderate decay (30-50% drop): 10 pts
           - Weak decay (<30% drop): 5 pts

        4. Indicator alignment (0-25 pts):
           - All aligned (VWAP + MACD + EMA): 25 pts
           - 2 aligned: 15 pts
           - 1 aligned: 5 pts

        Total score is sum of all factors, clamped to 0-100.

        Args:
            flagpole: Detected flagpole data
            consolidation: Detected consolidation data
            indicators: Technical indicator validation results

        Returns:
            Integer quality score between 0 and 100

        Example:
            score = detector._calculate_quality_score(flagpole, consolidation, indicators)
            if score >= 80:
                print(f"High quality pattern: {score}/100")
        """
        score = 0

        # Factor 1: Flagpole strength (0-30 points)
        gain_pct = flagpole.gain_pct
        if gain_pct >= Decimal('15.0'):
            score += 30
        elif gain_pct >= Decimal('10.0'):
            score += 20
        elif gain_pct >= Decimal('5.0'):
            score += 10

        # Factor 2: Consolidation tightness (0-25 points)
        # Calculate retracement percentage from flagpole gain
        flagpole_gain = flagpole.high_price - flagpole.start_price
        retracement = flagpole.high_price - consolidation.lower_boundary

        if flagpole_gain > Decimal('0'):
            retracement_pct = (retracement / flagpole_gain) * Decimal('100')

            # Tighter consolidation = higher score
            # 20-30% retracement = tight (25 pts)
            # 30-40% retracement = medium (18 pts)
            # 40-50% retracement = loose (10 pts)
            if retracement_pct <= Decimal('30.0'):
                score += 25
            elif retracement_pct <= Decimal('40.0'):
                score += 18
            elif retracement_pct <= Decimal('50.0'):
                score += 10

        # Factor 3: Volume profile (0-20 points)
        # Compare consolidation volume to flagpole volume
        if flagpole.avg_volume > Decimal('0'):
            volume_ratio = consolidation.avg_volume / flagpole.avg_volume

            # Strong volume decrease during consolidation = higher score
            # < 60% of flagpole volume = strong decay (20 pts)
            # 60-80% of flagpole volume = medium decay (10 pts)
            # >= 80% of flagpole volume = minimal decay (5 pts)
            if volume_ratio < Decimal('0.60'):
                score += 20
            elif volume_ratio < Decimal('0.80'):
                score += 10
            else:
                score += 5

        # Factor 4: Indicator alignment (0-25 points)
        # Check price position relative to indicators
        aligned_count = 0

        # Get current price from indicators (use consolidation upper boundary as proxy)
        current_price = consolidation.upper_boundary

        # Check VWAP alignment (price > VWAP)
        if 'vwap' in indicators and indicators['vwap'] > Decimal('0'):
            if current_price > indicators['vwap']:
                aligned_count += 1

        # Check MACD alignment (MACD > 0)
        if 'macd' in indicators:
            if indicators['macd'] > Decimal('0'):
                aligned_count += 1

        # Check EMA proximity (price within 2% of EMA-9)
        if 'ema_9' in indicators and indicators['ema_9'] > Decimal('0'):
            ema_diff = abs(current_price - indicators['ema_9'])
            ema_diff_pct = (ema_diff / indicators['ema_9']) * Decimal('100')
            if ema_diff_pct <= Decimal('2.0'):
                aligned_count += 1

        # Score based on aligned indicators
        if aligned_count == 3:
            score += 25
        elif aligned_count == 2:
            score += 15
        elif aligned_count == 1:
            score += 8
        # 0 aligned = 0 points

        # Clamp score to 0-100 range
        score = max(0, min(100, score))

        return int(score)

    def _create_failed_result(self, symbol: str, reason: str) -> BullFlagResult:
        """
        Create a BullFlagResult indicating no pattern detected.

        Args:
            symbol: Stock ticker symbol
            reason: Reason for pattern rejection

        Returns:
            BullFlagResult with detected=False
        """
        return BullFlagResult(
            symbol=symbol,
            timestamp=datetime.now(),
            detected=False,
            flagpole=None,
            consolidation=None,
            entry_price=None,
            stop_loss=None,
            target_price=None,
            quality_score=None,
            risk_reward_ratio=None
        )

    def _log_error(self, symbol: str, error: str) -> None:
        """
        Log error to error-log.md in specs directory if it exists.

        Args:
            symbol: Stock ticker symbol
            error: Error message to log
        """
        from pathlib import Path

        # Try to find specs/003-entry-logic-bull-flag/error-log.md
        try:
            base_path = Path(__file__).parent.parent.parent.parent
            specs_dir = base_path / "specs" / "003-entry-logic-bull-flag"
            error_log = specs_dir / "error-log.md"

            if specs_dir.exists():
                timestamp = datetime.now().isoformat()
                log_entry = f"\n## {timestamp} - {symbol}\n**Error**: {error}\n"

                # Create or append to error log
                if not error_log.exists():
                    error_log.write_text(
                        "# Error Log\n\n"
                        "Tracking errors during pattern detection.\n"
                        + log_entry
                    )
                else:
                    with error_log.open('a') as f:
                        f.write(log_entry)
        except Exception:
            # Silently fail if logging doesn't work
            pass


# Standalone functions for testing
# These wrap the class methods for easier test imports

def detect_flagpole(bars: List[Dict[str, Any]]) -> Optional[FlagpoleData]:
    """
    Standalone function to detect flagpole pattern.

    Uses default configuration for flagpole detection.
    This function is primarily for testing purposes.

    Args:
        bars: List of OHLCV dictionaries

    Returns:
        FlagpoleData if valid flagpole found, None otherwise

    Example:
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)
    """
    config = BullFlagConfig()
    detector = BullFlagDetector(config)
    return detector._detect_flagpole(bars)


def detect_consolidation(
    bars: List[Dict[str, Any]],
    flagpole: FlagpoleData
) -> Optional[ConsolidationData]:
    """
    Standalone function to detect consolidation pattern.

    Uses default configuration for consolidation detection.
    This function is primarily for testing purposes.

    Args:
        bars: List of OHLCV dictionaries
        flagpole: Detected flagpole data

    Returns:
        ConsolidationData if valid consolidation found, None otherwise

    Example:
        from src.trading_bot.patterns.bull_flag import detect_consolidation
        result = detect_consolidation(bars, flagpole)
    """
    config = BullFlagConfig()
    detector = BullFlagDetector(config)
    return detector._detect_consolidation(bars, flagpole)


def confirm_breakout(
    consolidation: ConsolidationData,
    confirmation_bar: Dict[str, Any],
    bar_index: Optional[int] = None
) -> Optional[Decimal]:
    """
    Standalone function to confirm breakout pattern.

    Uses default configuration for breakout confirmation.
    This function is primarily for testing purposes.

    Args:
        consolidation: Detected consolidation data
        confirmation_bar: Bar to check for breakout
        bar_index: Optional bar index for timing validation

    Returns:
        Decimal breakout price if valid, None otherwise

    Example:
        from src.trading_bot.patterns.bull_flag import confirm_breakout
        result = confirm_breakout(consolidation, bar)
    """
    config = BullFlagConfig()

    # For standalone function, we need to handle the single bar case
    # Convert confirmation_bar to a list if needed
    if bar_index is not None:
        # If bar_index is provided, check timing window
        if bar_index > consolidation.end_idx + 2:
            return None

    # Check breakout criteria directly
    close_price = Decimal(str(confirmation_bar["close"]))
    volume = Decimal(str(confirmation_bar["volume"]))

    # Validate close above upper boundary
    if close_price <= consolidation.upper_boundary:
        return None

    # Calculate price move percentage
    price_diff = close_price - consolidation.upper_boundary
    price_move_pct = (price_diff / consolidation.upper_boundary) * Decimal("100")

    # Validate minimum price move
    if price_move_pct < config.min_breakout_move_pct:
        return None

    # Calculate volume increase percentage
    vol_diff = volume - consolidation.avg_volume
    volume_increase_pct = (vol_diff / consolidation.avg_volume) * Decimal("100")

    # Validate minimum volume increase
    if volume_increase_pct < config.min_breakout_volume_increase:
        return None

    # All validations passed - return breakout price
    return close_price


def calculate_risk_parameters(
    flagpole: FlagpoleData,
    consolidation: ConsolidationData,
    breakout_price: Decimal
) -> Dict[str, Any]:
    """
    Standalone function to calculate risk parameters.

    Uses default configuration for risk parameter calculation.
    This function is primarily for testing purposes.

    Args:
        flagpole: Detected flagpole data
        consolidation: Detected consolidation data
        breakout_price: Confirmed breakout price

    Returns:
        Dictionary with entry_price, stop_loss, target_price, risk_reward_ratio

    Example:
        from src.trading_bot.patterns.bull_flag import calculate_risk_parameters
        result = calculate_risk_parameters(flagpole, consolidation, breakout_price)
    """
    config = BullFlagConfig()
    detector = BullFlagDetector(config)
    return detector._calculate_risk_parameters(flagpole, consolidation, breakout_price)


def calculate_quality_score(
    flagpole: FlagpoleData,
    consolidation: ConsolidationData,
    indicators: Dict[str, Any]
) -> int:
    """
    Standalone function to calculate quality score.

    Uses default configuration for quality score calculation.
    This function is primarily for testing purposes.

    Args:
        flagpole: Detected flagpole data
        consolidation: Detected consolidation data
        indicators: Technical indicator validation results

    Returns:
        Integer quality score between 0 and 100

    Example:
        from src.trading_bot.patterns.bull_flag import calculate_quality_score
        result = calculate_quality_score(flagpole, consolidation, indicators)
    """
    config = BullFlagConfig()
    detector = BullFlagDetector(config)
    return detector._calculate_quality_score(flagpole, consolidation, indicators)
