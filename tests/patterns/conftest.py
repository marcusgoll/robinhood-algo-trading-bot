"""
Test Configuration and Fixtures for Pattern Detection Tests

Provides reusable fixtures for testing bull flag pattern detection,
including sample OHLCV bars and configuration objects.

Feature: 003-entry-logic-bull-flag
Task: T010 - Create pytest fixtures for pattern detection tests
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, UTC
from typing import List, Dict


@pytest.fixture
def sample_bars() -> List[Dict]:
    """
    Basic OHLCV bars for testing pattern detection.

    Returns 35 bars with realistic price progression:
    - Bars 0-9: Uptrend (increasing prices)
    - Bars 10-29: Consolidation (sideways movement)
    - Bars 30+: Additional bars for testing

    Returns:
        List[dict] with keys: high, low, close, volume, open
    """
    bars = []
    base_date = datetime.now(UTC)
    base_price = Decimal("100.00")
    base_volume = Decimal("1000000")

    # Bars 0-9: Uptrend (1% gain per bar)
    for i in range(10):
        price = base_price + Decimal(str(i * 1.0))
        bars.append({
            "timestamp": base_date + timedelta(minutes=i*5),
            "open": float(price),
            "high": float(price + Decimal("0.50")),
            "low": float(price - Decimal("0.50")),
            "close": float(price + Decimal("0.25")),
            "volume": float(base_volume + Decimal(str(i * 10000)))
        })

    # Bars 10-29: Consolidation (sideways movement around 109)
    consolidation_price = Decimal("109.00")
    for i in range(10, 30):
        # Small random variation within 1%
        variation = Decimal(str((i % 5) * 0.2))
        price = consolidation_price + variation
        bars.append({
            "timestamp": base_date + timedelta(minutes=i*5),
            "open": float(price),
            "high": float(price + Decimal("0.50")),
            "low": float(price - Decimal("0.50")),
            "close": float(price),
            "volume": float(base_volume * Decimal("0.8"))
        })

    # Bars 30-34: Additional bars for testing
    for i in range(30, 35):
        price = consolidation_price + Decimal("1.0")
        bars.append({
            "timestamp": base_date + timedelta(minutes=i*5),
            "open": float(price),
            "high": float(price + Decimal("0.50")),
            "low": float(price - Decimal("0.50")),
            "close": float(price + Decimal("0.25")),
            "volume": float(base_volume)
        })

    return bars


@pytest.fixture
def valid_bull_flag_bars() -> List[Dict]:
    """
    OHLCV bars showing a perfect bull flag pattern.

    Structure:
    - Bars 0-10: Flagpole (5% gain, high volume)
    - Bars 11-18: Consolidation (30% retracement, volume decreases)
    - Bars 19-22: Breakout (volume increase, price above consolidation)

    Returns:
        List[dict] with clear flagpole, consolidation, and breakout
    """
    bars = []
    base_date = datetime.now(UTC)
    base_price = Decimal("175.00")
    base_volume = Decimal("2000000")

    # Bars 0-10: Flagpole - Strong upward move (8.5% gain)
    flagpole_start = base_price
    flagpole_end = base_price * Decimal("1.085")  # 8.5% gain
    flagpole_bars = 11
    gain_per_bar = (flagpole_end - flagpole_start) / Decimal(str(flagpole_bars))

    for i in range(flagpole_bars):
        price = flagpole_start + (gain_per_bar * Decimal(str(i)))
        bars.append({
            "timestamp": base_date + timedelta(minutes=i*5),
            "open": float(price),
            "high": float(price + Decimal("0.50")),
            "low": float(price - Decimal("0.30")),
            "close": float(price + Decimal("0.40")),
            "volume": float(base_volume * Decimal("1.2"))  # High volume
        })

    # Bars 11-18: Consolidation - 35% retracement with decreasing volume
    # Retracement = 35% of flagpole gain
    flagpole_gain = flagpole_end - flagpole_start
    retracement = flagpole_gain * Decimal("0.35")
    consolidation_high = flagpole_end
    consolidation_low = flagpole_end - retracement
    consolidation_bars = 8

    for i in range(consolidation_bars):
        # Price oscillates between high and low (downward sloping)
        if i % 2 == 0:
            price = consolidation_high - (retracement * Decimal(str(i)) / Decimal(str(consolidation_bars)))
        else:
            price = consolidation_low + (retracement * Decimal(str(i)) / Decimal(str(consolidation_bars * 2)))

        bars.append({
            "timestamp": base_date + timedelta(minutes=(11+i)*5),
            "open": float(price),
            "high": float(max(price, consolidation_high - Decimal(str(i * 0.5)))),
            "low": float(min(price, consolidation_low + Decimal(str(i * 0.3)))),
            "close": float(price - Decimal("0.20")),  # Downward slope
            "volume": float(base_volume * Decimal("0.6"))  # Volume decrease (40% drop)
        })

    # Bars 19-22: Breakout - Price moves above consolidation with volume spike
    breakout_price = consolidation_high + Decimal("1.50")
    for i in range(4):
        price = consolidation_high + Decimal(str(i * 0.5))
        bars.append({
            "timestamp": base_date + timedelta(minutes=(19+i)*5),
            "open": float(price),
            "high": float(price + Decimal("0.80")),
            "low": float(price - Decimal("0.20")),
            "close": float(price + Decimal("0.60")),
            "volume": float(base_volume * Decimal("1.5"))  # Volume spike (50% increase)
        })

    # Add padding bars to reach 30+ bars minimum
    for i in range(7):
        price = breakout_price + Decimal(str(i * 0.3))
        bars.append({
            "timestamp": base_date + timedelta(minutes=(23+i)*5),
            "open": float(price),
            "high": float(price + Decimal("0.50")),
            "low": float(price - Decimal("0.30")),
            "close": float(price + Decimal("0.20")),
            "volume": float(base_volume)
        })

    return bars


@pytest.fixture
def invalid_pattern_bars() -> List[Dict]:
    """
    OHLCV bars with no valid bull flag pattern.

    Shows sideways/downtrend movement with:
    - No clear flagpole (insufficient gain)
    - No consolidation phase
    - No breakout

    Returns:
        List[dict] with 35 bars showing no pattern
    """
    bars = []
    base_date = datetime.now(UTC)
    base_price = Decimal("150.00")
    base_volume = Decimal("1500000")

    # Bars 0-34: Sideways movement with small variations
    for i in range(35):
        # Small random variations (< 2% total range)
        variation = Decimal(str((i % 7 - 3) * 0.3))  # -0.9 to +0.9
        price = base_price + variation

        bars.append({
            "timestamp": base_date + timedelta(minutes=i*5),
            "open": float(price),
            "high": float(price + Decimal("0.40")),
            "low": float(price - Decimal("0.40")),
            "close": float(price + Decimal("0.10")),
            "volume": float(base_volume + Decimal(str((i % 10) * 10000)))
        })

    return bars


@pytest.fixture
def default_config():
    """
    BullFlagConfig with default parameters.

    Returns:
        BullFlagConfig with standard technical analysis defaults
    """
    # Import here to avoid circular dependencies
    from src.trading_bot.patterns.config import BullFlagConfig

    return BullFlagConfig()


@pytest.fixture
def aggressive_config():
    """
    BullFlagConfig with loose/aggressive pattern parameters.

    Looser criteria for pattern detection:
    - Lower minimum flagpole gain (2%)
    - Lower quality score threshold (40)
    - Wider retracement range (10-60%)
    - Lower volume requirements

    Returns:
        BullFlagConfig configured for aggressive pattern detection
    """
    from src.trading_bot.patterns.config import BullFlagConfig

    return BullFlagConfig(
        min_flagpole_gain=Decimal("2.0"),
        max_flagpole_gain=Decimal("30.0"),
        min_flagpole_bars=2,
        max_flagpole_bars=20,
        min_consolidation_bars=2,
        max_consolidation_bars=15,
        min_retracement_pct=Decimal("10.0"),
        max_retracement_pct=Decimal("60.0"),
        min_breakout_volume_increase=Decimal("15.0"),
        min_breakout_move_pct=Decimal("0.5"),
        min_risk_reward_ratio=Decimal("1.5"),
        min_quality_score=40,
        volume_decay_threshold=Decimal("0.95")
    )


@pytest.fixture
def conservative_config():
    """
    BullFlagConfig with strict/conservative pattern parameters.

    Stricter criteria for pattern detection:
    - Higher minimum flagpole gain (10%)
    - Higher quality score threshold (80)
    - Tighter retracement range (25-40%)
    - Higher volume requirements

    Returns:
        BullFlagConfig configured for conservative pattern detection
    """
    from src.trading_bot.patterns.config import BullFlagConfig

    return BullFlagConfig(
        min_flagpole_gain=Decimal("10.0"),
        max_flagpole_gain=Decimal("25.0"),
        min_flagpole_bars=4,
        max_flagpole_bars=12,
        min_consolidation_bars=4,
        max_consolidation_bars=8,
        min_retracement_pct=Decimal("25.0"),
        max_retracement_pct=Decimal("40.0"),
        min_breakout_volume_increase=Decimal("50.0"),
        min_breakout_move_pct=Decimal("2.0"),
        min_risk_reward_ratio=Decimal("3.0"),
        min_quality_score=80,
        volume_decay_threshold=Decimal("0.7")
    )
