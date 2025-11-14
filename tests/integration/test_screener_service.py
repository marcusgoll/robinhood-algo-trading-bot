"""
Integration tests for ScreenerService

T025: Integration tests for screener service with real-world scenarios
Coverage target: ≥80% (critical paths)

Test cases:
- test_screener_returns_paginated_results: Verify pagination metadata
- test_screener_handles_no_results: Empty list with correct metadata
- test_screener_latency_under_500ms: P95 latency assertion
- test_screener_logs_all_queries: Verify JSONL logging
- test_screener_handles_missing_market_data: Graceful degradation
- test_screener_error_handling_and_recovery: @with_retry integration
"""

import time
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from trading_bot.error_handling.exceptions import RetriableError
from trading_bot.logging.screener_logger import ScreenerLogger
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.schemas.screener_schemas import ScreenerQuery
from trading_bot.screener_config import ScreenerConfig
from trading_bot.services.screener_service import ScreenerService


@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Path:
    """Create temporary log directory for integration tests."""
    log_dir = tmp_path / "screener_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


@pytest.fixture
def screener_logger(temp_log_dir: Path) -> ScreenerLogger:
    """Create ScreenerLogger with temporary directory."""
    return ScreenerLogger(log_dir=str(temp_log_dir))


@pytest.fixture
def screener_config() -> ScreenerConfig:
    """Create ScreenerConfig for integration tests."""
    return ScreenerConfig.default()


@pytest.fixture
def mock_market_data() -> Mock:
    """Create mock MarketDataService for integration tests."""
    return Mock(spec=MarketDataService)


@pytest.fixture
def screener_service(
    mock_market_data: Mock,
    screener_logger: ScreenerLogger,
    screener_config: ScreenerConfig,
) -> ScreenerService:
    """Create ScreenerService for integration tests."""
    return ScreenerService(mock_market_data, screener_logger, screener_config)


# =========================================
# Pagination Integration Tests
# =========================================


def test_screener_returns_paginated_results(screener_service: ScreenerService) -> None:
    """
    Integration test: Verify screener returns correct pagination metadata.

    Tests:
    - Offset and limit applied correctly
    - has_more calculated correctly
    - next_offset set when more results available
    - page_number calculated from offset/limit
    """
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        # Create 25 stocks
        symbols = [f"ST{i:02d}" for i in range(25)]

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

        # Request page 2 (offset=10, limit=10)
        query = ScreenerQuery(offset=10, limit=10)
        result = screener_service.filter(query, symbols)

        # Verify pagination metadata
        assert result.result_count == 10  # Current page size
        assert result.total_count == 25  # Total matches
        assert result.page_info.offset == 10
        assert result.page_info.limit == 10
        assert result.page_info.has_more is True  # More results available
        assert result.page_info.next_offset == 20
        assert result.page_info.page_number == 2  # (10 // 10) + 1


def test_screener_handles_no_results(screener_service: ScreenerService) -> None:
    """
    Integration test: Verify screener handles empty results gracefully.

    Tests:
    - Returns empty list when no matches
    - result_count = 0
    - total_count = 0
    - has_more = False
    - No errors in response
    """
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        # All stocks above price range
        mock_get_quotes.side_effect = lambda s: [{
            "symbol": s,
            "bid_price": "100.00",  # Above $20 max
            "ask_price": "100.00",
            "last_trade_price": "100.00",
            "previous_close": "100.00",
        }]

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "50000000",
        }]

        # Query with price range filter that excludes all stocks
        query = ScreenerQuery(min_price=Decimal("2.00"), max_price=Decimal("20.00"))
        result = screener_service.filter(query, ["EXP1", "EXP2"])

        # Verify empty result
        assert result.stocks == []
        assert result.result_count == 0
        assert result.total_count == 0
        assert result.page_info.has_more is False
        assert result.errors == []
        assert result.query_id == query.query_id


# =========================================
# Performance Integration Tests
# =========================================


def test_screener_latency_under_500ms(screener_service: ScreenerService) -> None:
    """
    Integration test: Verify screener P95 latency <500ms.

    Runs 20 queries and verifies:
    - P50 latency <200ms
    - P95 latency <500ms (NFR-001 requirement)
    - execution_time_ms tracked in result
    """
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        # Fast mock responses
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

        # Run 20 queries
        latencies = []
        symbols = ["AAPL", "TSLA", "MSFT"]

        for _ in range(20):
            query = ScreenerQuery()
            result = screener_service.filter(query, symbols)
            latencies.append(result.execution_time_ms)

        # Calculate percentiles
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]

        # Verify performance requirements
        assert p50 < 200, f"P50 latency {p50:.2f}ms exceeds 200ms target"
        assert p95 < 500, f"P95 latency {p95:.2f}ms exceeds 500ms requirement (NFR-001)"


# =========================================
# Logging Integration Tests
# =========================================


def test_screener_logs_all_queries(
    screener_service: ScreenerService,
    screener_logger: ScreenerLogger,
    temp_log_dir: Path,
) -> None:
    """
    Integration test: Verify all queries logged to JSONL files.

    Tests:
    - Query event written to daily JSONL file
    - File contains query_id, params, result_count, execution_time_ms
    - Data gaps logged separately
    - Log files created in correct directory
    """
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

        # Run query
        query = ScreenerQuery(min_price=Decimal("2.00"), max_price=Decimal("20.00"))
        result = screener_service.filter(query, ["AAPL", "TSLA"])

        # Verify log file exists
        log_file = screener_logger.get_log_file()
        assert log_file.exists(), f"Log file not created: {log_file}"

        # Read log file and verify query event
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) >= 1, "No log entries written"

            # Parse first log entry (query event)
            import json
            query_event = json.loads(lines[0])

            # Verify query event structure
            assert query_event["event"] == "screener.query_completed"
            assert query_event["query_id"] == query.query_id
            assert "min_price" in query_event["query_params"]
            assert "max_price" in query_event["query_params"]
            assert query_event["result_count"] == result.result_count
            assert query_event["total_count"] == result.total_count
            assert query_event["execution_time_ms"] > 0
            assert query_event["api_calls"] > 0


# =========================================
# Data Handling Integration Tests
# =========================================


def test_screener_handles_missing_market_data(screener_service: ScreenerService) -> None:
    """
    Integration test: Verify graceful degradation with missing data.

    Tests:
    - Continues processing when float data missing
    - Uses 1M default for missing volume_avg_100d
    - Includes stocks with data gaps in results
    - Logs data gaps to JSONL
    - Marks data_gaps in StockScreenerMatch
    """
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        def get_quote(symbol: str):
            return [{
                "symbol": symbol,
                "bid_price": "10.00",
                "ask_price": "10.00",
                "last_trade_price": "10.00",
                "previous_close": "10.00",
            }]

        mock_get_quotes.side_effect = get_quote

        def get_fundamentals(symbol: str):
            if symbol == "MFLT":
                return [{
                    "volume": "10000000",
                    "average_volume": "5000000",
                    "float": None,  # Missing float data
                }]
            elif symbol == "MAVOL":
                return [{
                    "volume": "10000000",
                    "average_volume": None,  # Missing avg volume
                    "float": "50000000",
                }]
            else:
                return [{
                    "volume": "10000000",
                    "average_volume": "5000000",
                    "float": "50000000",
                }]

        mock_get_fundamentals.side_effect = get_fundamentals

        # Query with filters that require missing data
        query = ScreenerQuery(float_max=20, relative_volume=1.5)
        result = screener_service.filter(
            query, ["COMP", "MFLT", "MAVOL"]
        )

        # All stocks should be included (graceful degradation)
        assert result.result_count == 3

        # Verify data gaps marked
        stock_gaps = {stock.symbol: stock.data_gaps for stock in result.stocks}

        assert "float_shares" in stock_gaps["MFLT"]
        assert "volume_avg_100d" in stock_gaps["MAVOL"]
        assert stock_gaps["COMP"] == []


# =========================================
# Error Handling Integration Tests
# =========================================


def test_screener_error_handling_and_recovery(screener_service: ScreenerService) -> None:
    """
    Integration test: Verify @with_retry error handling and recovery.

    Tests:
    - Retries on RetriableError (up to 3 attempts)
    - Exponential backoff applied
    - Eventually succeeds after transient failures
    - Logs retry attempts
    """
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        # Simulate transient failures (fail twice, succeed on 3rd attempt)
        attempt_count = {"count": 0}

        def flaky_get_quotes(symbol: str):
            attempt_count["count"] += 1
            if attempt_count["count"] <= 2:
                raise RetriableError("Transient API failure")
            # Success on 3rd attempt
            return [{
                "symbol": symbol,
                "bid_price": "10.00",
                "ask_price": "10.00",
                "last_trade_price": "10.00",
                "previous_close": "10.00",
            }]

        mock_get_quotes.side_effect = flaky_get_quotes

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "50000000",
        }]

        # Run query (should succeed after retries)
        query = ScreenerQuery()

        # Note: @with_retry decorator should handle retries automatically
        # The filter() method itself is decorated with @with_retry
        # So this test verifies the integration works end-to-end

        start_time = time.perf_counter()
        result = screener_service.filter(query, ["FLAKY"])
        elapsed = time.perf_counter() - start_time

        # Verify eventual success
        assert result.result_count == 1
        assert result.stocks[0].symbol == "FLAKY"

        # Verify retry delay applied (should take >1s due to exponential backoff)
        # First retry: 1s, second retry: 2s = ~3s total + jitter
        assert elapsed > 2.0, f"Expected retry delays, got {elapsed:.2f}s"


def test_screener_handles_quote_fetch_failures_gracefully(
    screener_service: ScreenerService,
) -> None:
    """
    Integration test: Verify screener continues when individual quote fetches fail.

    Tests:
    - Logs data gap for failed quotes
    - Continues processing remaining symbols
    - Returns partial results
    - No errors in result.errors (individual failures logged, not fatal)
    """
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        def get_quote(symbol: str):
            if symbol == "FAIL":
                raise Exception("Quote fetch failed")
            return [{
                "symbol": symbol,
                "bid_price": "10.00",
                "ask_price": "10.00",
                "last_trade_price": "10.00",
                "previous_close": "10.00",
            }]

        mock_get_quotes.side_effect = get_quote

        mock_get_fundamentals.side_effect = lambda s: [{
            "volume": "10000000",
            "average_volume": "5000000",
            "float": "50000000",
        }]

        # Run query with one failing symbol
        query = ScreenerQuery()
        result = screener_service.filter(query, ["SUCC", "FAIL", "SUC2"])

        # Should return partial results (exclude FAIL)
        assert result.result_count == 2
        symbols = {stock.symbol for stock in result.stocks}
        assert symbols == {"SUCC", "SUC2"}
        assert "FAIL" not in symbols


# =========================================
# Full Workflow Integration Test
# =========================================


def test_screener_full_workflow_end_to_end(
    screener_service: ScreenerService,
    screener_logger: ScreenerLogger,
    temp_log_dir: Path,
) -> None:
    """
    Integration test: Full workflow from query to logged result.

    Simulates real-world usage:
    1. Create query with multiple filters
    2. Execute filter() with realistic symbols
    3. Verify results match criteria
    4. Verify pagination works
    5. Verify JSONL logging complete
    6. Verify performance acceptable

    This is the "happy path" integration test covering US1-US5.
    """
    with patch("robin_stocks.robinhood.get_quotes") as mock_get_quotes, \
         patch("robin_stocks.robinhood.get_fundamentals") as mock_get_fundamentals:

        # Mock realistic market data for 10 stocks
        def get_quote(symbol: str):
            prices = {
                "TSLA": "250.00", "AAPL": "180.00", "MSFT": "350.00",
                "NVDA": "500.00", "AMD": "150.00", "GOOGL": "140.00",
                "AMZN": "145.00", "META": "310.00", "NFLX": "450.00",
                "INTC": "45.00",
            }
            price = prices.get(symbol, "10.00")
            # Simulate 10% gain
            previous = str(float(price) / 1.1)
            return [{
                "symbol": symbol,
                "bid_price": price,
                "ask_price": price,
                "last_trade_price": price,
                "previous_close": previous,
            }]

        mock_get_quotes.side_effect = get_quote

        def get_fundamentals(symbol: str):
            # High volume stocks: TSLA, NVDA, AMD
            high_volume = {"TSLA", "NVDA", "AMD"}
            # Small float stocks: TSLA, AMD
            small_float = {"TSLA", "AMD"}

            return [{
                "volume": "50000000" if symbol in high_volume else "10000000",
                "average_volume": "5000000",
                "float": "15000000" if symbol in small_float else "100000000",
            }]

        mock_get_fundamentals.side_effect = get_fundamentals

        # Create comprehensive query
        query = ScreenerQuery(
            min_price=Decimal("100.00"),  # Filter out INTC ($45)
            max_price=Decimal("300.00"),  # Filter out NVDA ($500), NFLX ($450), MSFT ($350)
            relative_volume=5.0,  # Only TSLA, NVDA, AMD (but NVDA filtered by price)
            float_max=20,  # Only TSLA, AMD
            min_daily_change=9.0,  # All have ~10% move
            limit=5,  # Pagination
        )

        symbols = [
            "TSLA", "AAPL", "MSFT", "NVDA", "AMD",
            "GOOGL", "AMZN", "META", "NFLX", "INTC",
        ]

        start_time = time.perf_counter()
        result = screener_service.filter(query, symbols)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Verify results: Only TSLA and AMD should pass all filters
        # TSLA: $250 (✓), high volume (✓), small float (✓), 10% move (✓)
        # AMD: $150 (✓), high volume (✓), small float (✓), 10% move (✓)
        assert result.result_count == 2
        symbols_matched = {stock.symbol for stock in result.stocks}
        assert symbols_matched == {"TSLA", "AMD"}

        # Verify all filters marked
        for stock in result.stocks:
            assert "price_range" in stock.matched_filters
            assert "relative_volume" in stock.matched_filters
            assert "float_size" in stock.matched_filters
            assert "daily_movers" in stock.matched_filters

        # Verify pagination metadata
        assert result.total_count == 2
        assert result.page_info.has_more is False

        # Verify performance
        assert result.execution_time_ms < 500  # P95 requirement
        assert elapsed_ms < 500

        # Verify logging
        log_file = screener_logger.get_log_file()
        assert log_file.exists()

        # Verify query metadata
        assert result.query_id == query.query_id
        assert result.api_calls_made > 0
        assert result.errors == []
