"""
Unit tests for momentum signal data models.

Tests validate:
- SignalType and CatalystType enums
- MomentumSignal dataclass validation
- CatalystEvent dataclass validation
- PreMarketMover dataclass validation
- BullFlagPattern dataclass validation
"""

import pytest
from datetime import datetime, timezone
from src.trading_bot.momentum.schemas.momentum_signal import (
    SignalType,
    CatalystType,
    MomentumSignal,
    CatalystEvent,
    PreMarketMover,
    BullFlagPattern,
)


class TestSignalType:
    """Test SignalType enum values."""

    def test_signal_type_has_catalyst(self):
        """Given SignalType enum, when accessing CATALYST, then returns 'catalyst'."""
        assert SignalType.CATALYST == "catalyst"

    def test_signal_type_has_premarket(self):
        """Given SignalType enum, when accessing PREMARKET, then returns 'premarket'."""
        assert SignalType.PREMARKET == "premarket"

    def test_signal_type_has_pattern(self):
        """Given SignalType enum, when accessing PATTERN, then returns 'pattern'."""
        assert SignalType.PATTERN == "pattern"

    def test_signal_type_has_composite(self):
        """Given SignalType enum, when accessing COMPOSITE, then returns 'composite'."""
        assert SignalType.COMPOSITE == "composite"


class TestCatalystType:
    """Test CatalystType enum values."""

    def test_catalyst_type_has_earnings(self):
        """Given CatalystType enum, when accessing EARNINGS, then returns 'earnings'."""
        assert CatalystType.EARNINGS == "earnings"

    def test_catalyst_type_has_fda(self):
        """Given CatalystType enum, when accessing FDA, then returns 'fda'."""
        assert CatalystType.FDA == "fda"

    def test_catalyst_type_has_merger(self):
        """Given CatalystType enum, when accessing MERGER, then returns 'merger'."""
        assert CatalystType.MERGER == "merger"

    def test_catalyst_type_has_product(self):
        """Given CatalystType enum, when accessing PRODUCT, then returns 'product'."""
        assert CatalystType.PRODUCT == "product"

    def test_catalyst_type_has_analyst(self):
        """Given CatalystType enum, when accessing ANALYST, then returns 'analyst'."""
        assert CatalystType.ANALYST == "analyst"


class TestMomentumSignal:
    """Test MomentumSignal dataclass validation."""

    def test_creates_valid_momentum_signal(self):
        """Given valid inputs, when creating MomentumSignal, then succeeds."""
        signal = MomentumSignal(
            symbol="AAPL",
            signal_type=SignalType.CATALYST,
            strength=85.5,
            detected_at=datetime(2025, 10, 16, 14, 30, 0, tzinfo=timezone.utc),
            details={"headline": "Apple announces earnings beat"},
        )
        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.CATALYST
        assert signal.strength == 85.5
        assert signal.details == {"headline": "Apple announces earnings beat"}

    def test_validates_strength_range_min(self):
        """Given strength < 0, when creating MomentumSignal, then raises ValueError."""
        with pytest.raises(ValueError, match=r"strength \(-1\.0\) must be between 0 and 100"):
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.CATALYST,
                strength=-1.0,
                detected_at=datetime(2025, 10, 16, 14, 30, 0, tzinfo=timezone.utc),
                details={},
            )

    def test_validates_strength_range_max(self):
        """Given strength > 100, when creating MomentumSignal, then raises ValueError."""
        with pytest.raises(ValueError, match=r"strength \(101\.0\) must be between 0 and 100"):
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.CATALYST,
                strength=101.0,
                detected_at=datetime(2025, 10, 16, 14, 30, 0, tzinfo=timezone.utc),
                details={},
            )

    def test_validates_symbol_uppercase(self):
        """Given lowercase symbol, when creating MomentumSignal, then raises ValueError."""
        with pytest.raises(ValueError, match=r"symbol \(aapl\) must be 1-5 uppercase characters"):
            MomentumSignal(
                symbol="aapl",
                signal_type=SignalType.CATALYST,
                strength=85.0,
                detected_at=datetime(2025, 10, 16, 14, 30, 0, tzinfo=timezone.utc),
                details={},
            )

    def test_validates_symbol_length_min(self):
        """Given empty symbol, when creating MomentumSignal, then raises ValueError."""
        with pytest.raises(ValueError, match=r"symbol \(\) must be 1-5 uppercase characters"):
            MomentumSignal(
                symbol="",
                signal_type=SignalType.CATALYST,
                strength=85.0,
                detected_at=datetime(2025, 10, 16, 14, 30, 0, tzinfo=timezone.utc),
                details={},
            )

    def test_validates_symbol_length_max(self):
        """Given symbol > 5 chars, when creating MomentumSignal, then raises ValueError."""
        with pytest.raises(ValueError, match=r"symbol \(TOOLONG\) must be 1-5 uppercase characters"):
            MomentumSignal(
                symbol="TOOLONG",
                signal_type=SignalType.CATALYST,
                strength=85.0,
                detected_at=datetime(2025, 10, 16, 14, 30, 0, tzinfo=timezone.utc),
                details={},
            )

    def test_validates_symbol_format(self):
        """Given symbol with numbers, when creating MomentumSignal, then raises ValueError."""
        with pytest.raises(ValueError, match=r"symbol \(APL1\) must be 1-5 uppercase characters"):
            MomentumSignal(
                symbol="APL1",
                signal_type=SignalType.CATALYST,
                strength=85.0,
                detected_at=datetime(2025, 10, 16, 14, 30, 0, tzinfo=timezone.utc),
                details={},
            )


class TestCatalystEvent:
    """Test CatalystEvent dataclass validation."""

    def test_creates_valid_catalyst_event(self):
        """Given valid inputs, when creating CatalystEvent, then succeeds."""
        event = CatalystEvent(
            headline="Apple announces Q4 earnings beat",
            catalyst_type=CatalystType.EARNINGS,
            published_at=datetime(2025, 10, 16, 14, 0, 0, tzinfo=timezone.utc),
            source="Alpaca News",
        )
        assert event.headline == "Apple announces Q4 earnings beat"
        assert event.catalyst_type == CatalystType.EARNINGS
        assert event.source == "Alpaca News"

    def test_validates_published_at_is_datetime(self):
        """Given published_at as string, when creating CatalystEvent, then raises TypeError."""
        with pytest.raises(ValueError, match="published_at must be a datetime object"):
            CatalystEvent(
                headline="Breaking news",
                catalyst_type=CatalystType.EARNINGS,
                published_at="2025-10-16T14:00:00Z",  # type: ignore
                source="News Source",
            )


class TestPreMarketMover:
    """Test PreMarketMover dataclass validation."""

    def test_creates_valid_premarket_mover(self):
        """Given valid inputs, when creating PreMarketMover, then succeeds."""
        mover = PreMarketMover(
            change_pct=7.5,
            volume_ratio=2.5,
        )
        assert mover.change_pct == 7.5
        assert mover.volume_ratio == 2.5

    def test_validates_change_pct_positive(self):
        """Given negative change_pct, when creating PreMarketMover, then accepts (price can drop)."""
        # Price can move in either direction, so negative should be valid
        mover = PreMarketMover(
            change_pct=-5.0,
            volume_ratio=2.0,
        )
        assert mover.change_pct == -5.0

    def test_validates_volume_ratio_positive(self):
        """Given negative volume_ratio, when creating PreMarketMover, then raises ValueError."""
        with pytest.raises(ValueError, match=r"volume_ratio \(-1\.0\) must be positive"):
            PreMarketMover(
                change_pct=5.0,
                volume_ratio=-1.0,
            )

    def test_validates_volume_ratio_zero_not_allowed(self):
        """Given zero volume_ratio, when creating PreMarketMover, then raises ValueError."""
        with pytest.raises(ValueError, match=r"volume_ratio \(0\.0\) must be positive"):
            PreMarketMover(
                change_pct=5.0,
                volume_ratio=0.0,
            )


class TestBullFlagPattern:
    """Test BullFlagPattern dataclass validation."""

    def test_creates_valid_bull_flag_pattern(self):
        """Given valid inputs, when creating BullFlagPattern, then succeeds."""
        pattern = BullFlagPattern(
            pole_gain_pct=12.5,
            flag_range_pct=4.0,
            breakout_price=195.50,
            price_target=210.00,
            pattern_valid=True,
        )
        assert pattern.pole_gain_pct == 12.5
        assert pattern.flag_range_pct == 4.0
        assert pattern.breakout_price == 195.50
        assert pattern.price_target == 210.00
        assert pattern.pattern_valid is True

    def test_validates_pole_gain_pct_minimum(self):
        """Given pole_gain_pct < 8%, when creating BullFlagPattern, then raises ValueError."""
        with pytest.raises(ValueError, match=r"pole_gain_pct \(7\.0\) must be >= 8\.0"):
            BullFlagPattern(
                pole_gain_pct=7.0,
                flag_range_pct=4.0,
                breakout_price=195.50,
                price_target=210.00,
                pattern_valid=True,
            )

    def test_validates_flag_range_pct_minimum(self):
        """Given flag_range_pct < 3%, when creating BullFlagPattern, then raises ValueError."""
        with pytest.raises(ValueError, match=r"flag_range_pct \(2\.0\) must be between 3\.0 and 5\.0"):
            BullFlagPattern(
                pole_gain_pct=12.0,
                flag_range_pct=2.0,
                breakout_price=195.50,
                price_target=210.00,
                pattern_valid=True,
            )

    def test_validates_flag_range_pct_maximum(self):
        """Given flag_range_pct > 5%, when creating BullFlagPattern, then raises ValueError."""
        with pytest.raises(ValueError, match=r"flag_range_pct \(6\.0\) must be between 3\.0 and 5\.0"):
            BullFlagPattern(
                pole_gain_pct=12.0,
                flag_range_pct=6.0,
                breakout_price=195.50,
                price_target=210.00,
                pattern_valid=True,
            )

    def test_validates_breakout_price_positive(self):
        """Given negative breakout_price, when creating BullFlagPattern, then raises ValueError."""
        with pytest.raises(ValueError, match=r"breakout_price \(-195\.5\) must be positive"):
            BullFlagPattern(
                pole_gain_pct=12.0,
                flag_range_pct=4.0,
                breakout_price=-195.50,
                price_target=210.00,
                pattern_valid=True,
            )

    def test_validates_price_target_positive(self):
        """Given negative price_target, when creating BullFlagPattern, then raises ValueError."""
        with pytest.raises(ValueError, match=r"price_target \(-210\.0\) must be positive"):
            BullFlagPattern(
                pole_gain_pct=12.0,
                flag_range_pct=4.0,
                breakout_price=195.50,
                price_target=-210.00,
                pattern_valid=True,
            )

    def test_validates_price_target_greater_than_breakout(self):
        """Given price_target < breakout_price, when creating BullFlagPattern, then raises ValueError."""
        with pytest.raises(ValueError, match=r"price_target \(190\.0\) must be >= breakout_price \(195\.5\)"):
            BullFlagPattern(
                pole_gain_pct=12.0,
                flag_range_pct=4.0,
                breakout_price=195.50,
                price_target=190.00,
                pattern_valid=True,
            )
