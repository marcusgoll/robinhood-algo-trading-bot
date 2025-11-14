"""
Unit tests for ScreenerService

T024: Comprehensive unit tests for each filter (US1-US5)
Coverage target: ≥90%

Test cases:
- test_price_filter_basic: Verify 5 stocks across range boundaries
- test_price_filter_none: Skip if None
- test_relative_volume_filter: Below, at, above threshold
- test_volume_filter_missing_100d_avg: Use 1M default, log gap
- test_float_filter_missing_data: Skip None, log gap
- test_daily_change_filter_up_movers: Positive change
- test_daily_change_filter_down_movers: Negative change
- test_combined_filters_and_logic: 5+ combinations
- test_pagination_offset_limit: Slice correctly
- test_pagination_has_more_flag: Calculate correctly
- test_query_validation_errors: Invalid params raise ValueError
- test_retry_on_rate_limit: @with_retry integration
- test_logs_queries_to_jsonl: Verify logging calls
"""

from decimal import Decimal
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from trading_bot.logging.screener_logger import ScreenerLogger
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.schemas.screener_schemas import (
    ScreenerQuery,
    StockScreenerMatch,
)
from trading_bot.screener_config import ScreenerConfig
from trading_bot.services.screener_service import ScreenerService


@pytest.fixture
def mock_market_data() -> Mock:
    """Create mock MarketDataService for testing."""
    return Mock(spec=MarketDataService)


@pytest.fixture
def mock_logger() -> Mock:
    """Create mock ScreenerLogger for testing."""
    return Mock(spec=ScreenerLogger)


@pytest.fixture
def config() -> ScreenerConfig:
    """Create ScreenerConfig for testing."""
    return ScreenerConfig.default()


@pytest.fixture
def screener_service(
    mock_market_data: Mock, mock_logger: Mock, config: ScreenerConfig
) -> ScreenerService:
    """Create ScreenerService instance for testing."""
    return ScreenerService(mock_market_data, mock_logger, config)


# =========================================
# US1: Price Range Filter Tests
# =========================================


def test_price_filter_basic(screener_service: ScreenerService, mock_market_data: Mock) -> None:
    """
    Test price range filter with 5 stocks across boundaries.

    Boundaries tested:
    - Below min (excluded)
    - At min (included)
    - Within range (included)
    - At max (included)
    - Above max (excluded)
    """
    # Mock data: 5 stocks with various prices
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        # Setup quotes
        def get_quote_side_effect(symbol: str):
            prices = {
                "CHEAP": "1.50",  # Below min (excluded)
                "ATMIN": "2.00",  # At min (included)
                "MID": "10.00",  # Within range (included)
                "ATMAX": "20.00",  # At max (included)
                "EXPNS": "25.00",  # Above max (excluded)
            }
            return [{
                "symbol": symbol,
                "bid_price": prices[symbol],
                "ask_price": prices[symbol],
                "last_trade_price": prices[symbol],
                "previous_close": "10.00",
            }]

        mock_get_quotes.side_effect = get_quote_side_effect

        # Setup fundamentals
        def get_fundamentals_side_effect(symbol: str):
            return [{
                "volume": "10000000",
                "average_volume": "5000000",
                "float": "50000000",
            }]

        mock_get_fundamentals.side_effect = get_fundamentals_side_effect

        # Create query with price range $2-$20
        query = ScreenerQuery(min_price=Decimal("2.00"), max_price=Decimal("20.00"))

        # Execute filter
        result = screener_service.filter(
            query, ["CHEAP", "ATMIN", "MID", "ATMAX", "EXPNS"]
        )

        # Verify results
        assert result.result_count == 3  # ATMIN, MID, ATMAX
        assert result.total_count == 3

        symbols = {stock.symbol for stock in result.stocks}
        assert symbols == {"ATMIN", "MID", "ATMAX"}

        # Verify all matched stocks have "price_range" filter
        for stock in result.stocks:
            assert "price_range" in stock.matched_filters


def test_price_filter_min_only(screener_service: ScreenerService) -> None:
    """Test price filter with only min_price (no max)."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "5.00" if s == "CHEAP" else "10.00",
            "ask_price": "5.00",
            "last_trade_price": "5.00",
            "previous_close": "5.00",
        }]

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "50000000",
        }]

        query = ScreenerQuery(min_price=Decimal("8.00"))  # No max_price
        result = screener_service.filter(query, ["CHEAP", "EXPNS"])

        # Only EXPNS should pass (>= $8)
        assert result.result_count == 1
        assert result.stocks[0].symbol == "EXPNS"


def test_price_filter_max_only(screener_service: ScreenerService) -> None:
    """Test price filter with only max_price (no min)."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "5.00" if s == "CHEAP" else "25.00",
            "ask_price": "5.00",
            "last_trade_price": "5.00",
            "previous_close": "5.00",
        }]

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "50000000",
        }]

        query = ScreenerQuery(max_price=Decimal("10.00"))  # No min_price
        result = screener_service.filter(query, ["CHEAP", "EXPNS"])

        # Only CHEAP should pass (<= $10)
        assert result.result_count == 1
        assert result.stocks[0].symbol == "CHEAP"


def test_price_filter_none_skips_filter(screener_service: ScreenerService) -> None:
    """Test that price filter is skipped when min/max are both None."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "50000000",
        }]

        query = ScreenerQuery()  # No filters
        result = screener_service.filter(query, ["AAPL", "TSLA"])

        # All stocks should pass (no price filter applied)
        assert result.result_count == 2


# =========================================
# US2: Relative Volume Filter Tests
# =========================================


def test_relative_volume_filter_below_threshold(screener_service: ScreenerService) -> None:
    """Test relative volume filter excludes stocks below threshold."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        # LOW: 5M volume, 5M avg = 1x (below 5x threshold)
        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "5000000",  # Current volume
            "average_volume": "5000000",  # 100-day avg
            "float": "50000000",
        }]

        query = ScreenerQuery(relative_volume=5.0)  # 5x threshold
        result = screener_service.filter(query, ["LOW"])

        # Should be excluded (1x < 5x)
        assert result.result_count == 0


def test_relative_volume_filter_at_threshold(screener_service: ScreenerService) -> None:
    """Test relative volume filter includes stocks at exact threshold."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        # EXACT: 25M volume, 5M avg = 5x (exactly at threshold)
        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "25000000",  # 5x average
            "average_volume": "5000000",
            "float": "50000000",
        }]

        query = ScreenerQuery(relative_volume=5.0)
        result = screener_service.filter(query, ["EXACT"])

        # Should be included (5x >= 5x)
        assert result.result_count == 1
        assert result.stocks[0].symbol == "EXACT"
        assert "relative_volume" in result.stocks[0].matched_filters


def test_relative_volume_filter_above_threshold(screener_service: ScreenerService) -> None:
    """Test relative volume filter includes stocks above threshold."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        # HIGH: 50M volume, 5M avg = 10x (above 5x threshold)
        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "50000000",  # 10x average
            "average_volume": "5000000",
            "float": "50000000",
        }]

        query = ScreenerQuery(relative_volume=5.0)
        result = screener_service.filter(query, ["HIGH"])

        # Should be included (10x > 5x)
        assert result.result_count == 1
        assert result.stocks[0].symbol == "HIGH"


def test_volume_filter_missing_100d_avg_uses_default(
    screener_service: ScreenerService, mock_logger: Mock
) -> None:
    """Test volume filter uses 1M default for missing 100-day average and logs gap."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        # IPO: No 100-day average (None)
        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "6000000",  # 6M current volume
            "average_volume": None,  # Missing data
            "float": "50000000",
        }]

        query = ScreenerQuery(relative_volume=5.0)  # 5x threshold
        result = screener_service.filter(query, ["IPO"])

        # Should be included (6M >= 1M * 5x = 5M)
        assert result.result_count == 1
        assert result.stocks[0].symbol == "IPO"

        # Verify data gap was logged
        mock_logger.log_data_gap.assert_called_with(
            "IPO",
            "volume_avg_100d",
            "Using 1M default for missing 100d average"
        )


# =========================================
# US3: Float Size Filter Tests
# =========================================


def test_float_filter_under_threshold(screener_service: ScreenerService) -> None:
    """Test float filter includes stocks under threshold."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        # SMALL: 15M float (under 20M threshold)
        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "15000000",  # 15M shares
        }]

        query = ScreenerQuery(float_max=20)  # Max 20M shares
        result = screener_service.filter(query, ["SMALL"])

        # Should be included (15M < 20M)
        assert result.result_count == 1
        assert result.stocks[0].symbol == "SMALL"
        assert "float_size" in result.stocks[0].matched_filters


def test_float_filter_at_threshold(screener_service: ScreenerService) -> None:
    """Test float filter excludes stocks at exact threshold."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        # EXACT: 20M float (exactly at 20M threshold)
        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "20000000",  # Exactly 20M
        }]

        query = ScreenerQuery(float_max=20)
        result = screener_service.filter(query, ["EXACT"])

        # Should be excluded (20M >= 20M, filter is <)
        assert result.result_count == 0


def test_float_filter_above_threshold(screener_service: ScreenerService) -> None:
    """Test float filter excludes stocks above threshold."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        # LARGE: 100M float (above 20M threshold)
        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "100000000",  # 100M shares
        }]

        query = ScreenerQuery(float_max=20)
        result = screener_service.filter(query, ["LARGE"])

        # Should be excluded (100M > 20M)
        assert result.result_count == 0


def test_float_filter_missing_data_includes_with_gap_log(
    screener_service: ScreenerService, mock_logger: Mock
) -> None:
    """Test float filter includes stocks with missing data and logs gap."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        # MISS: No float data (None)
        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": None,  # Missing data
        }]

        query = ScreenerQuery(float_max=20)
        result = screener_service.filter(query, ["MISS"])

        # Should be included (graceful degradation)
        assert result.result_count == 1
        assert result.stocks[0].symbol == "MISS"
        assert result.stocks[0].float_shares is None
        assert "float_shares" in result.stocks[0].data_gaps

        # Verify data gap was logged
        mock_logger.log_data_gap.assert_called_with(
            "MISS",
            "float_shares",
            "Float data unavailable, including in results"
        )


# =========================================
# US4: Daily Performance Filter Tests
# =========================================


def test_daily_change_filter_up_movers(screener_service: ScreenerService) -> None:
    """Test daily change filter includes stocks with positive moves >= threshold."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "11.00",
            "ask_price": "11.00",
            "last_trade_price": "11.00",  # +10% from open
            "previous_close": "10.00",
        }]

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "50000000",
        }]

        query = ScreenerQuery(min_daily_change=10.0)  # 10% threshold
        result = screener_service.filter(query, ["UP"])

        # Should be included (10% >= 10%)
        assert result.result_count == 1
        assert result.stocks[0].symbol == "UP"
        assert result.stocks[0].daily_change_direction == "up"
        assert "daily_movers" in result.stocks[0].matched_filters


def test_daily_change_filter_down_movers(screener_service: ScreenerService) -> None:
    """Test daily change filter includes stocks with negative moves >= threshold."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "9.00",
            "ask_price": "9.00",
            "last_trade_price": "9.00",  # -10% from open
            "previous_close": "10.00",
        }]

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "50000000",
        }]

        query = ScreenerQuery(min_daily_change=10.0)
        result = screener_service.filter(query, ["DOWN"])

        # Should be included (|-10%| = 10% >= 10%)
        assert result.result_count == 1
        assert result.stocks[0].symbol == "DOWN"
        assert result.stocks[0].daily_change_direction == "down"


def test_daily_change_filter_below_threshold(screener_service: ScreenerService) -> None:
    """Test daily change filter excludes stocks below threshold."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.50",
            "ask_price": "10.50",
            "last_trade_price": "10.50",  # +5% from open
            "previous_close": "10.00",
        }]

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "50000000",
        }]

        query = ScreenerQuery(min_daily_change=10.0)  # 10% threshold
        result = screener_service.filter(query, ["SMALL"])

        # Should be excluded (5% < 10%)
        assert result.result_count == 0


# =========================================
# US5: Combined Filters Tests
# =========================================


def test_combined_filters_and_logic_all_pass(screener_service: ScreenerService) -> None:
    """Test combined filters with AND logic - stock passes all filters."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",  # Within $2-$20 range
            "ask_price": "10.00",
            "last_trade_price": "11.00",  # +10% move
            "previous_close": "10.00",
        }]

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "30000000",  # 6x average (30M / 5M)
            "average_volume": "5000000",
            "float": "15000000",  # 15M (under 20M)
        }]

        # Combine all filters
        query = ScreenerQuery(
            min_price=Decimal("2.00"),
            max_price=Decimal("20.00"),
            relative_volume=5.0,
            float_max=20,
            min_daily_change=10.0,
        )

        result = screener_service.filter(query, ["PRFCT"])

        # Should pass all filters
        assert result.result_count == 1
        stock = result.stocks[0]
        assert stock.symbol == "PRFCT"
        assert "price_range" in stock.matched_filters
        assert "relative_volume" in stock.matched_filters
        assert "float_size" in stock.matched_filters
        assert "daily_movers" in stock.matched_filters


def test_combined_filters_fails_one_filter(screener_service: ScreenerService) -> None:
    """Test combined filters - stock fails price filter, excluded entirely."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "25.00",  # Above max price ($20)
            "ask_price": "25.00",
            "last_trade_price": "27.50",  # +10% move
            "previous_close": "25.00",
        }]

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "30000000",  # 6x average
            "average_volume": "5000000",
            "float": "15000000",  # Under 20M
        }]

        query = ScreenerQuery(
            min_price=Decimal("2.00"),
            max_price=Decimal("20.00"),
            relative_volume=5.0,
            float_max=20,
            min_daily_change=10.0,
        )

        result = screener_service.filter(query, ["FAIL1"])

        # Should be excluded (AND logic - fails price filter)
        assert result.result_count == 0


def test_combined_filters_multiple_stocks(screener_service: ScreenerService) -> None:
    """Test combined filters with multiple stocks - verify AND logic isolation."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        def get_quote(symbol: str):
            quotes = {
                "PASS": {
                    "bid_price": "10.00",
                    "last_trade_price": "11.00",
                    "previous_close": "10.00",
                },
                "FP": {
                    "bid_price": "25.00",  # Fails price
                    "last_trade_price": "27.50",
                    "previous_close": "25.00",
                },
                "FV": {
                    "bid_price": "10.00",
                    "last_trade_price": "11.00",
                    "previous_close": "10.00",
                },
            }
            q = quotes[symbol]
            return [{
                "symbol": symbol,
                "bid_price": q["bid_price"],
                "ask_price": q["bid_price"],
                "last_trade_price": q["last_trade_price"],
                "previous_close": q["previous_close"],
            }]

        mock_get_quotes.side_effect = get_quote

        def get_fundamentals(symbol: str):
            funds = {
                "PASS": {
                    "volume": "30000000",  # 6x
                    "average_volume": "5000000",
                    "float": "15000000",
                },
                "FP": {
                    "volume": "30000000",
                    "average_volume": "5000000",
                    "float": "15000000",
                },
                "FV": {
                    "volume": "10000000",  # Only 2x (fails 5x threshold)
                    "average_volume": "5000000",
                    "float": "15000000",
                },
            }
            f = funds[symbol]
            return [{
                "volume": f["volume"],
                "average_volume": f["average_volume"],
                "float": f["float"],
            }]

        mock_get_fundamentals.side_effect = get_fundamentals

        query = ScreenerQuery(
            min_price=Decimal("2.00"),
            max_price=Decimal("20.00"),
            relative_volume=5.0,
            float_max=20,
            min_daily_change=10.0,
        )

        result = screener_service.filter(query, ["PASS", "FP", "FV"])

        # Only PASS should be included
        assert result.result_count == 1
        assert result.stocks[0].symbol == "PASS"


# =========================================
# Pagination Tests
# =========================================


def test_pagination_offset_limit_slices_correctly(screener_service: ScreenerService) -> None:
    """Test pagination correctly slices results using offset and limit."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        # Create 10 stocks
        symbols = [f"ST{i:02d}" for i in range(10)]

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "50000000",
        }]

        # Request page 2 (offset=3, limit=3)
        query = ScreenerQuery(offset=3, limit=3)
        result = screener_service.filter(query, symbols)

        # Should return stocks 3, 4, 5 (0-indexed)
        assert result.result_count == 3
        assert result.total_count == 10
        assert result.page_info.offset == 3
        assert result.page_info.limit == 3
        assert result.page_info.page_number == 2


def test_pagination_has_more_true_when_more_results(screener_service: ScreenerService) -> None:
    """Test pagination sets has_more=True when more results available."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        symbols = [f"ST{i:02d}" for i in range(10)]

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "50000000",
        }]

        # Request first 5 of 10
        query = ScreenerQuery(offset=0, limit=5)
        result = screener_service.filter(query, symbols)

        # Has more should be True
        assert result.page_info.has_more is True
        assert result.page_info.next_offset == 5


def test_pagination_has_more_false_at_end(screener_service: ScreenerService) -> None:
    """Test pagination sets has_more=False at end of results."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        symbols = [f"ST{i:02d}" for i in range(10)]

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "50000000",
        }]

        # Request all 10
        query = ScreenerQuery(offset=0, limit=10)
        result = screener_service.filter(query, symbols)

        # Has more should be False
        assert result.page_info.has_more is False
        assert result.page_info.next_offset is None


# =========================================
# Validation Tests
# =========================================


def test_query_validation_min_greater_than_max_raises_error() -> None:
    """Test ScreenerQuery validation rejects min_price >= max_price."""
    with pytest.raises(ValueError) as exc_info:
        ScreenerQuery(min_price=Decimal("20.00"), max_price=Decimal("10.00"))

    assert "min_price" in str(exc_info.value)
    assert "max_price" in str(exc_info.value)
    assert "must have min < max" in str(exc_info.value)


def test_query_validation_invalid_limit_raises_error() -> None:
    """Test ScreenerQuery validation rejects limit out of range."""
    # Test limit too small
    with pytest.raises(ValueError) as exc_info:
        ScreenerQuery(limit=0)
    assert "limit must be 1-500" in str(exc_info.value)

    # Test limit too large
    with pytest.raises(ValueError) as exc_info:
        ScreenerQuery(limit=501)
    assert "limit must be 1-500" in str(exc_info.value)


def test_query_validation_negative_offset_raises_error() -> None:
    """Test ScreenerQuery validation rejects negative offset."""
    with pytest.raises(ValueError) as exc_info:
        ScreenerQuery(offset=-1)
    assert "offset must be >= 0" in str(exc_info.value)


# =========================================
# Logging Tests
# =========================================


def test_logs_queries_to_jsonl(
    screener_service: ScreenerService, mock_logger: Mock
) -> None:
    """Test that all queries are logged with comprehensive metadata."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "50000000",
        }]

        query = ScreenerQuery(min_price=Decimal("2.00"), max_price=Decimal("20.00"))
        result = screener_service.filter(query, ["AAPL"])

        # Verify log_query was called
        assert mock_logger.log_query.called
        call_args = mock_logger.log_query.call_args

        # Verify query_id matches
        assert call_args.kwargs["query_id"] == query.query_id

        # Verify query params logged
        assert "min_price" in call_args.kwargs["query_params"]
        assert "max_price" in call_args.kwargs["query_params"]

        # Verify result metadata logged
        assert call_args.kwargs["result_count"] == result.result_count
        assert call_args.kwargs["total_count"] == result.total_count
        assert call_args.kwargs["execution_time_ms"] > 0
        assert call_args.kwargs["api_calls"] > 0


def test_logs_data_gaps_for_missing_fields(
    screener_service: ScreenerService, mock_logger: Mock
) -> None:
    """Test that data gaps are logged for missing fields."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        # Return missing float data
        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": None,  # Missing
        }]

        query = ScreenerQuery(float_max=20)
        result = screener_service.filter(query, ["MISS"])

        # Verify log_data_gap was called
        assert mock_logger.log_data_gap.called

        # Check that "float_shares" gap was logged
        data_gap_calls = [
            call for call in mock_logger.log_data_gap.call_args_list
            if "float_shares" in call[0]
        ]
        assert len(data_gap_calls) > 0


# =========================================
# Sorting Tests
# =========================================


def test_results_sorted_by_volume_descending(screener_service: ScreenerService) -> None:
    """Test that results are sorted by volume descending (highest first)."""
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "10.00",
            "ask_price": "10.00",
            "last_trade_price": "10.00",
            "previous_close": "10.00",
        }]

        def get_fundamentals(symbol: str):
            volumes = {
                "LOW": "5000000",  # 5M
                "HIGH": "50000000",  # 50M
                "MID": "20000000",  # 20M
            }
            return [{
                "volume": volumes[symbol],
                "average_volume": "5000000",
                "float": "50000000",
            }]

        mock_get_fundamentals.side_effect = get_fundamentals

        query = ScreenerQuery()
        result = screener_service.filter(query, ["LOW", "HIGH", "MID"])

        # Verify sorted by volume descending
        assert result.stocks[0].symbol == "HIGH"  # 50M
        assert result.stocks[1].symbol == "MID"  # 20M
        assert result.stocks[2].symbol == "LOW"  # 5M
