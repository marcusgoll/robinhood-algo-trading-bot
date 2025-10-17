"""Pattern detection result dataclasses."""

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional


@dataclass
class FlagpoleData:
    """Captures flagpole phase characteristics (initial upward movement).

    The flagpole represents the initial strong upward price movement that
    precedes the consolidation phase in a bull flag pattern.

    Attributes:
        start_idx: Bar index where flagpole starts
        end_idx: Bar index where flagpole ends
        gain_pct: Percentage gain from start to end (e.g., Decimal('5.5') for 5.5%)
        high_price: Highest price reached during flagpole
        start_price: Price at the start of flagpole (low of first bar)
        open_price: Open price at the start of flagpole (for risk/reward calculation)
        avg_volume: Average volume during flagpole period
    """
    start_idx: int
    end_idx: int
    gain_pct: Decimal
    high_price: Decimal
    start_price: Decimal
    open_price: Decimal
    avg_volume: Decimal


@dataclass
class ConsolidationData:
    """Captures consolidation phase characteristics (flag formation).

    The consolidation represents the pullback/sideways movement that forms
    the 'flag' portion of the bull flag pattern.

    Attributes:
        start_idx: Bar index where consolidation starts
        end_idx: Bar index where consolidation ends
        upper_boundary: Resistance level during consolidation
        lower_boundary: Support level during consolidation
        avg_volume: Average volume during consolidation period
    """
    start_idx: int
    end_idx: int
    upper_boundary: Decimal
    lower_boundary: Decimal
    avg_volume: Decimal


@dataclass
class BullFlagResult:
    """Result of bull flag pattern detection.

    Encapsulates complete bull flag pattern detection results including
    pattern metadata, risk parameters, and signal validation.

    Attributes:
        symbol: Stock ticker symbol
        timestamp: When pattern was detected
        detected: Whether a valid bull flag pattern was found
        flagpole: Flagpole phase data (None if no pattern detected)
        consolidation: Consolidation phase data (None if no pattern detected)
        entry_price: Recommended entry price (None if no valid entry)
        stop_loss: Calculated stop-loss price (None if no valid entry)
        target_price: Calculated target price (None if no valid entry)
        quality_score: Pattern quality score 0-100 (None if no pattern)
        risk_reward_ratio: Risk/reward ratio (None if no valid entry)
    """
    symbol: str
    timestamp: datetime
    detected: bool
    flagpole: Optional[FlagpoleData]
    consolidation: Optional[ConsolidationData]
    entry_price: Optional[Decimal]
    stop_loss: Optional[Decimal]
    target_price: Optional[Decimal]
    quality_score: Optional[int]
    risk_reward_ratio: Optional[Decimal]
