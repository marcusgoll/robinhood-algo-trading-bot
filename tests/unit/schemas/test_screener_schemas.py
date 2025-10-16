"""
Unit tests for stock screener schemas.

Tests cover validation logic in ScreenerQuery, StockScreenerMatch, PageInfo, and ScreenerResult.
"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from trading_bot.schemas.screener_schemas import (
    PageInfo,
    ScreenerQuery,
    ScreenerResult,
    StockScreenerMatch,
)


class TestScreenerQuery:
    """Tests for ScreenerQuery dataclass validation."""

    def test_screener_query_validation_min_max(self) -> None:
        """Test that min_price >= max_price raises ValueError."""
        with pytest.raises(ValueError, match="min_price.*max_price.*must have min < max"):
            ScreenerQuery(min_price=Decimal("20.00"), max_price=Decimal("10.00"))

    def test_screener_query_validation_equal_prices(self) -> None:
        """Test that min_price == max_price raises ValueError."""
        with pytest.raises(ValueError, match="min_price.*max_price.*must have min < max"):
            ScreenerQuery(min_price=Decimal("10.00"), max_price=Decimal("10.00"))

    def test_screener_query_validation_limit_too_low(self) -> None:
        """Test that limit < 1 raises ValueError."""
        with pytest.raises(ValueError, match="limit must be 1-500"):
            ScreenerQuery(limit=0)

    def test_screener_query_validation_limit_too_high(self) -> None:
        """Test that limit > 500 raises ValueError."""
        with pytest.raises(ValueError, match="limit must be 1-500"):
            ScreenerQuery(limit=501)

    def test_screener_query_validation_offset_negative(self) -> None:
        """Test that offset < 0 raises ValueError."""
        with pytest.raises(ValueError, match="offset must be >= 0"):
            ScreenerQuery(offset=-1)

    def test_screener_query_valid_defaults(self) -> None:
        """Test ScreenerQuery with valid defaults."""
        query = ScreenerQuery()
        assert query.min_price is None
        assert query.max_price is None
        assert query.relative_volume is None
        assert query.float_max is None
        assert query.min_daily_change is None
        assert query.limit == 500
        assert query.offset == 0
        assert len(query.query_id) == 36  # UUID format

    def test_screener_query_valid_with_filters(self) -> None:
        """Test ScreenerQuery with valid filter parameters."""
        query = ScreenerQuery(
            min_price=Decimal("2.00"),
            max_price=Decimal("20.00"),
            relative_volume=5.0,
            float_max=20,
            min_daily_change=10.0,
            limit=100,
            offset=50,
        )
        assert query.min_price == Decimal("2.00")
        assert query.max_price == Decimal("20.00")
        assert query.relative_volume == 5.0
        assert query.float_max == 20
        assert query.min_daily_change == 10.0
        assert query.limit == 100
        assert query.offset == 50


class TestStockScreenerMatch:
    """Tests for StockScreenerMatch dataclass validation."""

    def test_stock_match_symbol_validation_too_long(self) -> None:
        """Test that symbol > 5 chars raises ValueError."""
        with pytest.raises(ValueError, match="Symbol must be 1-5 chars"):
            StockScreenerMatch(
                symbol="TOOLONG",
                bid_price=Decimal("10.00"),
                volume=1000000,
                daily_open=Decimal("9.50"),
                daily_close=Decimal("10.00"),
                daily_change_pct=5.26,
                matched_filters=["price_range"],
            )

    def test_stock_match_symbol_validation_empty(self) -> None:
        """Test that empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol must be 1-5 chars"):
            StockScreenerMatch(
                symbol="",
                bid_price=Decimal("10.00"),
                volume=1000000,
                daily_open=Decimal("9.50"),
                daily_close=Decimal("10.00"),
                daily_change_pct=5.26,
                matched_filters=["price_range"],
            )

    def test_stock_match_price_validation_zero(self) -> None:
        """Test that bid_price == 0 raises ValueError."""
        with pytest.raises(ValueError, match="bid_price must be > 0"):
            StockScreenerMatch(
                symbol="AAPL",
                bid_price=Decimal("0.00"),
                volume=1000000,
                daily_open=Decimal("9.50"),
                daily_close=Decimal("10.00"),
                daily_change_pct=5.26,
                matched_filters=["price_range"],
            )

    def test_stock_match_price_validation_negative(self) -> None:
        """Test that bid_price < 0 raises ValueError."""
        with pytest.raises(ValueError, match="bid_price must be > 0"):
            StockScreenerMatch(
                symbol="AAPL",
                bid_price=Decimal("-5.00"),
                volume=1000000,
                daily_open=Decimal("9.50"),
                daily_close=Decimal("10.00"),
                daily_change_pct=5.26,
                matched_filters=["price_range"],
            )

    def test_stock_match_change_pct_validation_negative(self) -> None:
        """Test that daily_change_pct < 0 raises ValueError."""
        with pytest.raises(ValueError, match="daily_change_pct must be 0-1000"):
            StockScreenerMatch(
                symbol="AAPL",
                bid_price=Decimal("10.00"),
                volume=1000000,
                daily_open=Decimal("9.50"),
                daily_close=Decimal("10.00"),
                daily_change_pct=-5.0,
                matched_filters=["price_range"],
            )

    def test_stock_match_change_pct_validation_too_high(self) -> None:
        """Test that daily_change_pct > 1000 raises ValueError."""
        with pytest.raises(ValueError, match="daily_change_pct must be 0-1000"):
            StockScreenerMatch(
                symbol="AAPL",
                bid_price=Decimal("10.00"),
                volume=1000000,
                daily_open=Decimal("9.50"),
                daily_close=Decimal("10.00"),
                daily_change_pct=1500.0,
                matched_filters=["price_range"],
            )

    def test_stock_match_valid_basic(self) -> None:
        """Test StockScreenerMatch with valid basic data."""
        match = StockScreenerMatch(
            symbol="TSLA",
            bid_price=Decimal("250.50"),
            volume=50000000,
            daily_open=Decimal("240.00"),
            daily_close=Decimal("250.50"),
            daily_change_pct=4.38,
            matched_filters=["price_range", "volume_spike"],
        )
        assert match.symbol == "TSLA"
        assert match.bid_price == Decimal("250.50")
        assert match.volume == 50000000
        assert match.daily_open == Decimal("240.00")
        assert match.daily_close == Decimal("250.50")
        assert match.daily_change_pct == 4.38
        assert match.matched_filters == ["price_range", "volume_spike"]
        assert match.daily_change_direction == "up"
        assert match.data_gaps == []
        assert match.volume_avg_100d is None
        assert match.float_shares is None

    def test_stock_match_with_optional_fields(self) -> None:
        """Test StockScreenerMatch with all optional fields."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        match = StockScreenerMatch(
            symbol="AAPL",
            bid_price=Decimal("175.00"),
            volume=80000000,
            daily_open=Decimal("170.00"),
            daily_close=Decimal("175.00"),
            daily_change_pct=2.94,
            matched_filters=["price_range", "float_size"],
            volume_avg_100d=60000000,
            float_shares=15000000,
            daily_change_direction="up",
            data_gaps=["fundamentals"],
            timestamp=timestamp,
        )
        assert match.volume_avg_100d == 60000000
        assert match.float_shares == 15000000
        assert match.daily_change_direction == "up"
        assert match.data_gaps == ["fundamentals"]
        assert match.timestamp == timestamp


class TestPageInfo:
    """Tests for PageInfo dataclass."""

    def test_page_info_calculation_has_more_true(self) -> None:
        """Test PageInfo calculation when has_more is True."""
        page = PageInfo(offset=0, limit=500, has_more=True)
        assert page.offset == 0
        assert page.limit == 500
        assert page.has_more is True
        assert page.next_offset == 500  # Auto-calculated
        assert page.page_number == 1

    def test_page_info_calculation_has_more_false(self) -> None:
        """Test PageInfo calculation when has_more is False."""
        page = PageInfo(offset=1000, limit=500, has_more=False)
        assert page.offset == 1000
        assert page.limit == 500
        assert page.has_more is False
        assert page.next_offset is None
        assert page.page_number == 3  # (1000 // 500) + 1

    def test_page_info_page_number_calculation(self) -> None:
        """Test page_number calculation for various offsets."""
        # Page 1
        page1 = PageInfo(offset=0, limit=500, has_more=True)
        assert page1.page_number == 1

        # Page 2
        page2 = PageInfo(offset=500, limit=500, has_more=True)
        assert page2.page_number == 2

        # Page 3
        page3 = PageInfo(offset=1000, limit=500, has_more=False)
        assert page3.page_number == 3

    def test_page_info_next_offset_explicit(self) -> None:
        """Test that explicitly provided next_offset is preserved."""
        page = PageInfo(offset=0, limit=100, has_more=True, next_offset=200)
        assert page.next_offset == 200  # Explicit value overridden


class TestScreenerResult:
    """Tests for ScreenerResult dataclass."""

    def test_screener_result_structure_minimal(self) -> None:
        """Test ScreenerResult with minimal data."""
        query_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        page_info = PageInfo(offset=0, limit=500, has_more=False)

        result = ScreenerResult(
            query_id=query_id,
            stocks=[],
            query_timestamp=timestamp,
            result_count=0,
            total_count=0,
            execution_time_ms=125.5,
            page_info=page_info,
        )

        assert result.query_id == query_id
        assert result.stocks == []
        assert result.query_timestamp == timestamp
        assert result.result_count == 0
        assert result.total_count == 0
        assert result.execution_time_ms == 125.5
        assert result.page_info == page_info
        assert result.errors == []
        assert result.api_calls_made == 0
        assert result.cache_hit is False

    def test_screener_result_structure_with_stocks(self) -> None:
        """Test ScreenerResult with stock matches."""
        query_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"

        stocks = [
            StockScreenerMatch(
                symbol="TSLA",
                bid_price=Decimal("250.00"),
                volume=50000000,
                daily_open=Decimal("240.00"),
                daily_close=Decimal("250.00"),
                daily_change_pct=4.17,
                matched_filters=["price_range"],
            ),
            StockScreenerMatch(
                symbol="AAPL",
                bid_price=Decimal("175.00"),
                volume=80000000,
                daily_open=Decimal("170.00"),
                daily_close=Decimal("175.00"),
                daily_change_pct=2.94,
                matched_filters=["volume_spike"],
            ),
        ]

        page_info = PageInfo(offset=0, limit=500, has_more=False)

        result = ScreenerResult(
            query_id=query_id,
            stocks=stocks,
            query_timestamp=timestamp,
            result_count=2,
            total_count=2,
            execution_time_ms=187.3,
            page_info=page_info,
            errors=["1 stock missing float data"],
            api_calls_made=5,
            cache_hit=False,
        )

        assert len(result.stocks) == 2
        assert result.result_count == 2
        assert result.total_count == 2
        assert result.errors == ["1 stock missing float data"]
        assert result.api_calls_made == 5
        assert result.cache_hit is False

    def test_screener_result_all_fields_present(self) -> None:
        """Test that all required fields are present and correct types."""
        query_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        page_info = PageInfo(offset=0, limit=500, has_more=False)

        result = ScreenerResult(
            query_id=query_id,
            stocks=[],
            query_timestamp=timestamp,
            result_count=0,
            total_count=0,
            execution_time_ms=100.0,
            page_info=page_info,
            errors=[],
            api_calls_made=3,
            cache_hit=True,
        )

        # Type checks
        assert isinstance(result.query_id, str)
        assert isinstance(result.stocks, list)
        assert isinstance(result.query_timestamp, str)
        assert isinstance(result.result_count, int)
        assert isinstance(result.total_count, int)
        assert isinstance(result.execution_time_ms, float)
        assert isinstance(result.page_info, PageInfo)
        assert isinstance(result.errors, list)
        assert isinstance(result.api_calls_made, int)
        assert isinstance(result.cache_hit, bool)
