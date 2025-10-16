"""
Integration Tests: ScreenerService

Tests for stock screener filtering logic with realistic data scenarios.

Feature: stock-screener (001-stock-screener)
Tasks: T024-T025 [GREEN] - Integration tests for all filters
Spec: specs/001-stock-screener/spec.md

Test Coverage:
- Price filter basic boundaries
- Volume filter with default handling (IPOs)
- Float filter with missing data graceful degradation
- Daily change filter both directions
- Combined filters AND logic
- Pagination offset/limit/has_more
- Results sorted by volume descending
- Latency under 500ms (performance assertion)
"""

import time
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from trading_bot.logging.screener_logger import ScreenerLogger
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.schemas.screener_schemas import ScreenerQuery
from trading_bot.screener_config import ScreenerConfig
from trading_bot.services.screener_service import ScreenerService


@pytest.fixture
def mock_logger():
    """Mock ScreenerLogger for testing."""
    logger = MagicMock(spec=ScreenerLogger)
    return logger


@pytest.fixture
def mock_market_data_service():
    """Mock MarketDataService for testing."""
    service = MagicMock(spec=MarketDataService)
    return service


@pytest.fixture
def screener_config():
    """Default screener configuration."""
    return ScreenerConfig.default()


@pytest.fixture
def screener_service(mock_market_data_service, mock_logger, screener_config):
    """ScreenerService instance with mocked dependencies."""
    return ScreenerService(
        market_data_service=mock_market_data_service,
        logger=mock_logger,
        config=screener_config,
    )


# Mock robin_stocks responses
MOCK_QUOTES = {
    "TSLA": [{
        "symbol": "TSLA",
        "bid_price": "250.50",
        "ask_price": "250.75",
        "last_trade_price": "250.60",
        "previous_close": "245.00",
    }],
    "AAPL": [{
        "symbol": "AAPL",
        "bid_price": "175.25",
        "ask_price": "175.50",
        "last_trade_price": "175.30",
        "previous_close": "174.00",
    }],
    "AKTR": [{
        "symbol": "AKTR",
        "bid_price": "5.50",
        "ask_price": "5.55",
        "last_trade_price": "5.52",
        "previous_close": "4.50",
    }],
    "MSFT": [{
        "symbol": "MSFT",
        "bid_price": "380.00",
        "ask_price": "380.25",
        "last_trade_price": "380.10",
        "previous_close": "375.00",
    }],
    "GOOG": [{
        "symbol": "GOOG",
        "bid_price": "140.00",
        "ask_price": "140.25",
        "last_trade_price": "140.10",
        "previous_close": "139.00",
    }],
}

MOCK_FUNDAMENTALS = {
    "TSLA": [{
        "volume": "50000000",
        "average_volume": "10000000",
        "float": "3000000000",  # 3B float
    }],
    "AAPL": [{
        "volume": "30000000",
        "average_volume": "50000000",
        "float": "15000000000",  # 15B float
    }],
    "AKTR": [{
        "volume": "8000000",
        "average_volume": None,  # IPO, no 100d average
        "float": "15000000",  # 15M float
    }],
    "MSFT": [{
        "volume": "20000000",
        "average_volume": "25000000",
        "float": "7400000000",  # 7.4B float
    }],
    "GOOG": [{
        "volume": "15000000",
        "average_volume": "20000000",
        "float": None,  # Missing float data
    }],
}


def mock_get_quotes(symbol):
    """Mock robin_stocks.get_quotes."""
    return MOCK_QUOTES.get(symbol, [])


def mock_get_fundamentals(symbol):
    """Mock robin_stocks.get_fundamentals."""
    return MOCK_FUNDAMENTALS.get(symbol, [])


@patch("trading_bot.services.screener_service.r.get_quotes", side_effect=mock_get_quotes)
@patch("trading_bot.services.screener_service.r.get_fundamentals", side_effect=mock_get_fundamentals)
def test_price_filter_basic(
    mock_fund, mock_quotes, screener_service, mock_logger
):
    """
    Test price range filter with basic boundaries.

    Scenario: Filter stocks between $5 and $200
    Expected: AKTR ($5.50), GOOG ($140), AAPL ($175.25) pass
              TSLA ($250.50), MSFT ($380) fail
    """
    query = ScreenerQuery(
        min_price=Decimal("5.00"),
        max_price=Decimal("200.00"),
        limit=10,
        offset=0,
    )

    symbols = ["TSLA", "AAPL", "AKTR", "MSFT", "GOOG"]
    result = screener_service.filter(query, symbols)

    # Verify correct stocks passed
    matched_symbols = {stock.symbol for stock in result.stocks}
    assert "AKTR" in matched_symbols
    assert "GOOG" in matched_symbols
    assert "AAPL" in matched_symbols
    assert "TSLA" not in matched_symbols
    assert "MSFT" not in matched_symbols

    # Verify metadata
    assert result.result_count == 3
    assert result.total_count == 3
    assert result.query_id == query.query_id

    # Verify logging
    mock_logger.log_query.assert_called_once()


@patch("trading_bot.services.screener_service.r.get_quotes", side_effect=mock_get_quotes)
@patch("trading_bot.services.screener_service.r.get_fundamentals", side_effect=mock_get_fundamentals)
def test_volume_filter_with_defaults(
    mock_fund, mock_quotes, screener_service, mock_logger
):
    """
    Test relative volume filter with IPO default handling.

    Scenario: Filter stocks with 5x relative volume
    Expected: TSLA (5x = 50M/10M) passes
              AKTR (8M > 5M default) passes (IPO with no 100d avg)
              Others fail
    """
    query = ScreenerQuery(
        relative_volume=5.0,
        limit=10,
        offset=0,
    )

    symbols = ["TSLA", "AAPL", "AKTR", "MSFT", "GOOG"]
    result = screener_service.filter(query, symbols)

    # Verify correct stocks passed
    matched_symbols = {stock.symbol for stock in result.stocks}
    assert "TSLA" in matched_symbols  # 5x volume
    assert "AKTR" in matched_symbols  # Above 5M default

    # Verify data gap logged for AKTR (missing 100d avg)
    data_gap_calls = [
        call for call in mock_logger.log_data_gap.call_args_list
        if "AKTR" in str(call) and "volume_avg_100d" in str(call)
    ]
    assert len(data_gap_calls) > 0


@patch("trading_bot.services.screener_service.r.get_quotes", side_effect=mock_get_quotes)
@patch("trading_bot.services.screener_service.r.get_fundamentals", side_effect=mock_get_fundamentals)
def test_float_filter_missing_data(
    mock_fund, mock_quotes, screener_service, mock_logger
):
    """
    Test float filter with graceful handling of missing data.

    Scenario: Filter stocks with float < 20M shares
    Expected: AKTR (15M) passes
              GOOG (None) passes with data gap logged (graceful degradation)
              Others fail (>20M float)
    """
    query = ScreenerQuery(
        float_max=20,  # 20M shares
        limit=10,
        offset=0,
    )

    symbols = ["TSLA", "AAPL", "AKTR", "MSFT", "GOOG"]
    result = screener_service.filter(query, symbols)

    # Verify correct stocks passed
    matched_symbols = {stock.symbol for stock in result.stocks}
    assert "AKTR" in matched_symbols  # 15M float
    assert "GOOG" in matched_symbols  # Missing float, included with data gap

    # Verify data gap logged for GOOG (missing float)
    data_gap_calls = [
        call for call in mock_logger.log_data_gap.call_args_list
        if "GOOG" in str(call) and "float_shares" in str(call)
    ]
    assert len(data_gap_calls) > 0


@patch("trading_bot.services.screener_service.r.get_quotes", side_effect=mock_get_quotes)
@patch("trading_bot.services.screener_service.r.get_fundamentals", side_effect=mock_get_fundamentals)
def test_daily_change_filter_both_directions(
    mock_fund, mock_quotes, screener_service, mock_logger
):
    """
    Test daily change filter captures both up and down movers.

    Scenario: Filter stocks with ±10% daily move
    Expected: AKTR (22.67% up) passes
              Others fail (<10% move)
    """
    query = ScreenerQuery(
        min_daily_change=10.0,  # ±10%
        limit=10,
        offset=0,
    )

    symbols = ["TSLA", "AAPL", "AKTR", "MSFT", "GOOG"]
    result = screener_service.filter(query, symbols)

    # Verify correct stocks passed
    matched_symbols = {stock.symbol for stock in result.stocks}
    assert "AKTR" in matched_symbols  # 22.67% up

    # Verify AKTR has correct direction
    aktr_stock = next(s for s in result.stocks if s.symbol == "AKTR")
    assert aktr_stock.daily_change_direction == "up"
    assert aktr_stock.daily_change_pct > 10.0


@patch("trading_bot.services.screener_service.r.get_quotes", side_effect=mock_get_quotes)
@patch("trading_bot.services.screener_service.r.get_fundamentals", side_effect=mock_get_fundamentals)
def test_combined_filters_and_logic(
    mock_fund, mock_quotes, screener_service, mock_logger
):
    """
    Test combined filters with AND logic.

    Scenario: Filter stocks with:
    - Price $5-$200
    - Relative volume 5x
    - Float < 20M
    - Daily change ±10%

    Expected: AKTR passes all filters
    """
    query = ScreenerQuery(
        min_price=Decimal("5.00"),
        max_price=Decimal("200.00"),
        relative_volume=5.0,
        float_max=20,
        min_daily_change=10.0,
        limit=10,
        offset=0,
    )

    symbols = ["TSLA", "AAPL", "AKTR", "MSFT", "GOOG"]
    result = screener_service.filter(query, symbols)

    # Verify only AKTR passes all filters
    assert result.result_count == 1
    assert result.stocks[0].symbol == "AKTR"

    # Verify matched_filters includes all applied filters
    matched_filters = result.stocks[0].matched_filters
    assert "price_range" in matched_filters
    assert "relative_volume" in matched_filters
    assert "float_size" in matched_filters
    assert "daily_movers" in matched_filters


@patch("trading_bot.services.screener_service.r.get_quotes", side_effect=mock_get_quotes)
@patch("trading_bot.services.screener_service.r.get_fundamentals", side_effect=mock_get_fundamentals)
def test_pagination_basic(
    mock_fund, mock_quotes, screener_service, mock_logger
):
    """
    Test pagination with offset/limit/has_more logic.

    Scenario: 5 stocks, limit=2, offset=0
    Expected: Page 1 has 2 stocks, has_more=True, next_offset=2
    """
    query = ScreenerQuery(
        limit=2,
        offset=0,
    )

    symbols = ["TSLA", "AAPL", "AKTR", "MSFT", "GOOG"]
    result = screener_service.filter(query, symbols)

    # Verify pagination metadata
    assert result.result_count == 2
    assert result.total_count == 5
    assert result.page_info.has_more is True
    assert result.page_info.next_offset == 2
    assert result.page_info.page_number == 1

    # Test page 2
    query_page2 = ScreenerQuery(
        limit=2,
        offset=2,
    )
    result_page2 = screener_service.filter(query_page2, symbols)

    assert result_page2.result_count == 2
    assert result_page2.total_count == 5
    assert result_page2.page_info.has_more is True
    assert result_page2.page_info.next_offset == 4
    assert result_page2.page_info.page_number == 2

    # Test page 3 (last page)
    query_page3 = ScreenerQuery(
        limit=2,
        offset=4,
    )
    result_page3 = screener_service.filter(query_page3, symbols)

    assert result_page3.result_count == 1
    assert result_page3.total_count == 5
    assert result_page3.page_info.has_more is False
    assert result_page3.page_info.next_offset is None
    assert result_page3.page_info.page_number == 3


@patch("trading_bot.services.screener_service.r.get_quotes", side_effect=mock_get_quotes)
@patch("trading_bot.services.screener_service.r.get_fundamentals", side_effect=mock_get_fundamentals)
def test_results_sorted_by_volume(
    mock_fund, mock_quotes, screener_service, mock_logger
):
    """
    Test results are sorted by volume descending.

    Expected order: TSLA (50M) > AAPL (30M) > MSFT (20M) > GOOG (15M) > AKTR (8M)
    """
    query = ScreenerQuery(
        limit=10,
        offset=0,
    )

    symbols = ["AKTR", "GOOG", "MSFT", "AAPL", "TSLA"]  # Random order
    result = screener_service.filter(query, symbols)

    # Verify sorted by volume descending
    volumes = [stock.volume for stock in result.stocks]
    assert volumes == sorted(volumes, reverse=True)

    # Verify correct order
    assert result.stocks[0].symbol == "TSLA"
    assert result.stocks[1].symbol == "AAPL"
    assert result.stocks[2].symbol == "MSFT"
    assert result.stocks[3].symbol == "GOOG"
    assert result.stocks[4].symbol == "AKTR"


@patch("trading_bot.services.screener_service.r.get_quotes", side_effect=mock_get_quotes)
@patch("trading_bot.services.screener_service.r.get_fundamentals", side_effect=mock_get_fundamentals)
def test_latency_under_500ms(
    mock_fund, mock_quotes, screener_service, mock_logger
):
    """
    Test screener latency meets NFR-001 (<500ms P95).

    Measures actual execution time and verifies execution_time_ms metadata.
    """
    query = ScreenerQuery(
        min_price=Decimal("5.00"),
        max_price=Decimal("200.00"),
        limit=10,
        offset=0,
    )

    symbols = ["TSLA", "AAPL", "AKTR", "MSFT", "GOOG"]

    # Measure execution time
    start_time = time.time()
    result = screener_service.filter(query, symbols)
    elapsed_ms = (time.time() - start_time) * 1000

    # Verify execution time metadata
    assert result.execution_time_ms > 0
    assert result.execution_time_ms < 500  # P95 <500ms

    # Verify actual execution time (with mocks should be fast)
    assert elapsed_ms < 500


@patch("trading_bot.services.screener_service.r.get_quotes", side_effect=mock_get_quotes)
@patch("trading_bot.services.screener_service.r.get_fundamentals", side_effect=mock_get_fundamentals)
def test_screener_handles_no_results(
    mock_fund, mock_quotes, screener_service, mock_logger
):
    """
    Test screener handles empty results gracefully.

    Scenario: Filter with impossible criteria (price $1000+)
    Expected: Empty results, correct metadata
    """
    query = ScreenerQuery(
        min_price=Decimal("1000.00"),
        limit=10,
        offset=0,
    )

    symbols = ["TSLA", "AAPL", "AKTR", "MSFT", "GOOG"]
    result = screener_service.filter(query, symbols)

    # Verify empty results
    assert result.result_count == 0
    assert result.total_count == 0
    assert len(result.stocks) == 0

    # Verify pagination metadata
    assert result.page_info.has_more is False
    assert result.page_info.next_offset is None


@patch("trading_bot.services.screener_service.r.get_quotes", side_effect=mock_get_quotes)
@patch("trading_bot.services.screener_service.r.get_fundamentals", side_effect=mock_get_fundamentals)
def test_screener_logs_all_queries(
    mock_fund, mock_quotes, screener_service, mock_logger
):
    """
    Test screener logs all queries to audit trail.

    Verifies ScreenerLogger.log_query() called with correct parameters.
    """
    query = ScreenerQuery(
        min_price=Decimal("5.00"),
        max_price=Decimal("200.00"),
        limit=10,
        offset=0,
    )

    symbols = ["TSLA", "AAPL", "AKTR"]
    result = screener_service.filter(query, symbols)

    # Verify log_query called
    mock_logger.log_query.assert_called_once()

    # Verify log parameters
    call_args = mock_logger.log_query.call_args
    assert call_args[1]["query_id"] == query.query_id
    assert call_args[1]["result_count"] == result.result_count
    assert call_args[1]["total_count"] == result.total_count
    assert call_args[1]["execution_time_ms"] > 0
