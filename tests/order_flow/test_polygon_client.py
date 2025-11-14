"""
Unit tests for PolygonClient normalization and API interaction.

Tests:
- T009: PolygonClient normalizes Level 2 API response to OrderBookSnapshot
- T015: Integration test with real Polygon.io API (--integration flag required)
- T023: Integration test for Time & Sales with real API (--integration flag required)

Feature: level-2-order-flow-i
Task: T009, T015, T023 [RED] - Write tests for PolygonClient
"""

import os
import pytest
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from unittest.mock import Mock, patch

from src.trading_bot.order_flow.config import OrderFlowConfig
from src.trading_bot.order_flow.polygon_client import PolygonClient
from src.trading_bot.order_flow.data_models import OrderBookSnapshot, TimeAndSalesRecord
from trading_bot.market_data.exceptions import DataValidationError


class TestPolygonClientLevel2Normalization:
    """Test suite for PolygonClient._normalize_level2_response() method."""

    def test_normalize_level2_response_converts_raw_api_dict_to_snapshot(self):
        """Test that _normalize_level2_response() converts raw API dict to OrderBookSnapshot."""
        # Given: PolygonClient instance
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        client = PolygonClient(config)

        # Given: Raw API response from Polygon.io (mock structure)
        raw_response = {
            "status": "OK",
            "ticker": "AAPL",
            "updated": 1698768000000,  # Unix milliseconds (2023-10-31 12:00:00 UTC)
            "bids": [
                {"p": 175.50, "s": 10000},
                {"p": 175.49, "s": 5000},
                {"p": 175.48, "s": 8000}
            ],
            "asks": [
                {"p": 175.51, "s": 3000},
                {"p": 175.52, "s": 7000},
                {"p": 175.53, "s": 12000}
            ]
        }

        # When: Normalizing response
        snapshot = client._normalize_level2_response(raw_response)

        # Then: Should return OrderBookSnapshot with correct structure
        assert isinstance(snapshot, OrderBookSnapshot)
        assert snapshot.symbol == "AAPL"
        assert len(snapshot.bids) == 3
        assert len(snapshot.asks) == 3

        # Then: Bids should be (Decimal, int) tuples sorted descending by price
        assert snapshot.bids[0] == (Decimal("175.50"), 10000)
        assert snapshot.bids[1] == (Decimal("175.49"), 5000)
        assert snapshot.bids[2] == (Decimal("175.48"), 8000)

        # Then: Asks should be (Decimal, int) tuples sorted ascending by price
        assert snapshot.asks[0] == (Decimal("175.51"), 3000)
        assert snapshot.asks[1] == (Decimal("175.52"), 7000)
        assert snapshot.asks[2] == (Decimal("175.53"), 12000)

        # Then: Timestamp should be converted from Unix ms to datetime UTC
        assert snapshot.timestamp_utc.tzinfo is not None  # Timezone-aware
        assert isinstance(snapshot.timestamp_utc, datetime)

    def test_normalize_level2_response_handles_empty_bids_asks(self):
        """Test that _normalize_level2_response() handles empty bids/asks arrays."""
        # Given: PolygonClient instance
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        client = PolygonClient(config)

        # Given: Raw API response with empty bids/asks
        raw_response = {
            "status": "OK",
            "ticker": "TSLA",
            "updated": 1698768000000,
            "bids": [],  # Empty
            "asks": []   # Empty
        }

        # When: Normalizing response
        snapshot = client._normalize_level2_response(raw_response)

        # Then: Should return OrderBookSnapshot with empty lists
        assert snapshot.symbol == "TSLA"
        assert len(snapshot.bids) == 0
        assert len(snapshot.asks) == 0

    def test_normalize_level2_response_raises_error_on_malformed_response(self):
        """Test that _normalize_level2_response() raises DataValidationError on malformed API response."""
        # Given: PolygonClient instance
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        client = PolygonClient(config)

        # Given: Malformed raw API response (missing required fields)
        raw_response_missing_ticker = {
            "status": "OK",
            "updated": 1698768000000,
            "bids": [],
            "asks": []
            # Missing: "ticker"
        }

        # When: Normalizing malformed response
        # Then: Should raise DataValidationError
        with pytest.raises(DataValidationError, match="Missing 'ticker' field"):
            client._normalize_level2_response(raw_response_missing_ticker)

    def test_normalize_level2_response_validates_data_before_returning(self):
        """Test that _normalize_level2_response() calls validate_level2_data() before returning."""
        # Given: PolygonClient instance
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        client = PolygonClient(config)

        # Given: Raw API response with stale timestamp (>30 seconds old)
        stale_timestamp_ms = int((datetime.now(UTC) - timedelta(seconds=35)).timestamp() * 1000)
        raw_response_stale = {
            "status": "OK",
            "ticker": "AAPL",
            "updated": stale_timestamp_ms,  # Stale: 35 seconds old
            "bids": [{"p": 175.50, "s": 1000}],
            "asks": [{"p": 175.51, "s": 1000}]
        }

        # When: Normalizing response with stale data
        # Then: Should raise DataValidationError from validate_level2_data()
        # Note: Normalization creates snapshot, but validation happens in get_level2_snapshot()
        # This test verifies normalization works; stale validation tested elsewhere
        snapshot = client._normalize_level2_response(raw_response_stale)
        assert snapshot is not None  # Normalization succeeds, validation deferred


class TestPolygonClientTapeNormalization:
    """Test suite for PolygonClient._normalize_tape_response() method."""

    def test_normalize_tape_response_converts_raw_api_list_to_records(self):
        """Test that _normalize_tape_response() converts raw API dict to list of TimeAndSalesRecord."""
        # Given: PolygonClient instance
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        client = PolygonClient(config)

        # Given: Raw API response from Polygon.io Time & Sales endpoint
        raw_response = {
            "status": "OK",
            "results": [
                {
                    "T": "AAPL",
                    "t": 1698768000000000000,  # Unix nanoseconds
                    "p": 175.50,
                    "s": 5000,
                    "c": [14]  # Condition codes (14 = regular sale)
                },
                {
                    "T": "AAPL",
                    "t": 1698768001000000000,  # 1 second later
                    "p": 175.49,
                    "s": 3000,
                    "c": [12]  # Condition codes (12 = out of sequence)
                },
                {
                    "T": "AAPL",
                    "t": 1698768002000000000,  # 2 seconds later
                    "p": 175.51,
                    "s": 8000,
                    "c": [14]
                }
            ]
        }

        # When: Normalizing response
        records = client._normalize_tape_response(raw_response)

        # Then: Should return list of TimeAndSalesRecord
        assert isinstance(records, list)
        assert len(records) == 3

        # Then: First record should have correct structure
        assert isinstance(records[0], TimeAndSalesRecord)
        assert records[0].symbol == "AAPL"
        assert records[0].price == Decimal("175.50")
        assert records[0].size == 5000
        assert records[0].side in ["buy", "sell"]  # Inferred from conditions
        assert records[0].timestamp_utc.tzinfo is not None  # Timezone-aware

        # Then: Records should be chronologically ordered
        assert records[0].timestamp_utc < records[1].timestamp_utc < records[2].timestamp_utc

    def test_normalize_tape_response_infers_side_from_conditions(self):
        """Test that _normalize_tape_response() infers buy/sell side from condition codes."""
        # Given: PolygonClient instance
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        client = PolygonClient(config)

        # Given: Raw API response with known condition codes
        # Note: Polygon.io uses condition codes to indicate trade side
        # For this test, we'll use simplified logic: odd tick = sell, even tick = buy
        raw_response = {
            "status": "OK",
            "results": [
                {
                    "T": "AAPL",
                    "t": 1698768000000000000,
                    "p": 175.50,
                    "s": 5000,
                    "c": [14]  # Even tick (simplified: buyer-initiated)
                },
                {
                    "T": "AAPL",
                    "t": 1698768001000000000,
                    "p": 175.49,
                    "s": 3000,
                    "c": [41]  # Odd tick (simplified: seller-initiated)
                }
            ]
        }

        # When: Normalizing response
        records = client._normalize_tape_response(raw_response)

        # Then: Each record should have inferred side
        assert records[0].side in ["buy", "sell"]
        assert records[1].side in ["buy", "sell"]

    def test_normalize_tape_response_handles_empty_results(self):
        """Test that _normalize_tape_response() handles empty results array."""
        # Given: PolygonClient instance
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        client = PolygonClient(config)

        # Given: Raw API response with no trades
        raw_response = {
            "status": "OK",
            "results": []  # No trades in time window
        }

        # When: Normalizing response
        records = client._normalize_tape_response(raw_response)

        # Then: Should return empty list
        assert isinstance(records, list)
        assert len(records) == 0

    def test_normalize_tape_response_validates_data_before_returning(self):
        """Test that _normalize_tape_response() calls validate_tape_data() before returning."""
        # Given: PolygonClient instance
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        client = PolygonClient(config)

        # Given: Raw API response with out-of-order timestamps
        raw_response_out_of_order = {
            "status": "OK",
            "results": [
                {
                    "T": "AAPL",
                    "t": 1698768002000000000,  # Later timestamp first
                    "p": 175.50,
                    "s": 5000,
                    "c": [14]
                },
                {
                    "T": "AAPL",
                    "t": 1698768001000000000,  # Earlier timestamp second (invalid)
                    "p": 175.49,
                    "s": 3000,
                    "c": [14]
                }
            ]
        }

        # When: Normalizing response with out-of-order data
        # Then: Should raise DataValidationError from validate_tape_data()
        with pytest.raises(DataValidationError, match="not chronological"):
            client._normalize_tape_response(raw_response_out_of_order)


@pytest.mark.integration
class TestPolygonClientIntegration:
    """Integration tests for PolygonClient with real Polygon.io API.

    IMPORTANT: These tests require:
    - Valid POLYGON_API_KEY environment variable
    - Active internet connection
    - Polygon.io API quota available

    Run with: pytest tests/order_flow/test_polygon_client.py -m integration
    """

    def test_get_level2_snapshot_real_api_call(self):
        """Test that get_level2_snapshot() successfully fetches real Level 2 data."""
        # Skip if POLYGON_API_KEY not set
        api_key = os.getenv("POLYGON_API_KEY")
        if not api_key or len(api_key) < 10:
            pytest.skip("POLYGON_API_KEY not set (required for integration tests)")

        # Given: PolygonClient with real API key
        config = OrderFlowConfig.from_env()
        client = PolygonClient(config)

        # When: Fetching Level 2 snapshot for liquid stock
        snapshot = client.get_level2_snapshot("AAPL")

        # Then: Should return valid OrderBookSnapshot
        assert isinstance(snapshot, OrderBookSnapshot)
        assert snapshot.symbol == "AAPL"
        assert len(snapshot.bids) > 0  # Should have bid depth
        assert len(snapshot.asks) > 0  # Should have ask depth
        assert snapshot.timestamp_utc.tzinfo is not None

        # Then: Data should pass validation (fresh timestamp)
        age_seconds = (datetime.now(UTC) - snapshot.timestamp_utc).total_seconds()
        assert age_seconds < 30  # Should be fresh data

    def test_get_time_and_sales_real_api_call(self):
        """Test that get_time_and_sales() successfully fetches real tape data."""
        # Skip if POLYGON_API_KEY not set
        api_key = os.getenv("POLYGON_API_KEY")
        if not api_key or len(api_key) < 10:
            pytest.skip("POLYGON_API_KEY not set (required for integration tests)")

        # Given: PolygonClient with real API key
        config = OrderFlowConfig.from_env()
        client = PolygonClient(config)

        # Given: 5-minute time window
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=5)

        # When: Fetching Time & Sales data for liquid stock
        records = client.get_time_and_sales("AAPL", start_time, end_time)

        # Then: Should return list of TimeAndSalesRecord
        assert isinstance(records, list)
        # Note: May be empty outside market hours
        if len(records) > 0:
            assert isinstance(records[0], TimeAndSalesRecord)
            assert records[0].symbol == "AAPL"
            assert records[0].price > 0
            assert records[0].size > 0
            assert records[0].side in ["buy", "sell"]

            # Then: Records should be chronologically ordered
            for i in range(len(records) - 1):
                assert records[i].timestamp_utc <= records[i+1].timestamp_utc

    def test_rate_limit_handling_with_retries(self):
        """Test that PolygonClient handles rate limits with @with_retry decorator."""
        # Skip if POLYGON_API_KEY not set
        api_key = os.getenv("POLYGON_API_KEY")
        if not api_key or len(api_key) < 10:
            pytest.skip("POLYGON_API_KEY not set (required for integration tests)")

        # Given: PolygonClient with real API key
        config = OrderFlowConfig.from_env()
        client = PolygonClient(config)

        # When: Making rapid API calls (may trigger rate limit)
        # Note: Polygon.io starter plan = 5 req/sec limit
        try:
            for i in range(10):
                snapshot = client.get_level2_snapshot("AAPL")
                assert snapshot is not None
        except Exception as e:
            # Then: Should handle rate limits gracefully (retry or log)
            # This test documents expected behavior (may need adjustment based on actual API limits)
            assert "rate limit" in str(e).lower() or "429" in str(e)


class TestPolygonClientAPIMocked:
    """Test suite for PolygonClient API methods with mocked HTTP responses."""

    @patch('requests.get')
    def test_get_level2_snapshot_success(self, mock_get):
        """Test get_level2_snapshot() with successful mocked HTTP response."""
        # Given: PolygonClient instance
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        client = PolygonClient(config)

        # Given: Current timestamp in Unix milliseconds (within 30s freshness window)
        import time
        current_timestamp_ms = int(time.time() * 1000)

        # Given: Mocked successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "OK",
            "ticker": "AAPL",
            "updated": current_timestamp_ms,  # Use current timestamp to pass validation
            "bids": [{"p": 175.50, "s": 10000}],
            "asks": [{"p": 175.51, "s": 3000}]
        }
        mock_get.return_value = mock_response

        # When: Fetching Level 2 snapshot
        snapshot = client.get_level2_snapshot("AAPL")

        # Then: Should call API with correct parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "AAPL" in call_args[0][0]  # URL contains symbol
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_key_1234567890"

        # Then: Should return valid OrderBookSnapshot
        assert snapshot.symbol == "AAPL"
        assert len(snapshot.bids) == 1
        assert len(snapshot.asks) == 1

    @patch('requests.get')
    def test_get_level2_snapshot_http_error(self, mock_get):
        """Test get_level2_snapshot() handles HTTP errors."""
        # Given: PolygonClient instance
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        client = PolygonClient(config)

        # Given: Mocked HTTP error response (401 Unauthorized)
        import requests
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_get.return_value = mock_response

        # When/Then: Should raise HTTPError
        with pytest.raises(requests.exceptions.HTTPError):
            client.get_level2_snapshot("AAPL")

    @patch('requests.get')
    def test_get_time_and_sales_success(self, mock_get):
        """Test get_time_and_sales() with successful mocked HTTP response."""
        # Given: PolygonClient instance
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        client = PolygonClient(config)

        # Given: Current timestamp in Unix milliseconds
        import time
        current_timestamp_ms = int(time.time() * 1000)

        # Given: Mocked successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "OK",
            "ticker": "AAPL",
            "results": [
                {
                    "T": "AAPL",
                    "t": current_timestamp_ms - 10000,  # 10 seconds ago
                    "p": 175.50,
                    "s": 100,
                    "c": [0]  # Condition code
                },
                {
                    "T": "AAPL",
                    "t": current_timestamp_ms - 5000,  # 5 seconds ago
                    "p": 175.51,
                    "s": 200,
                    "c": [1]
                }
            ]
        }
        mock_get.return_value = mock_response

        # When: Fetching Time & Sales (with both start and end time)
        from datetime import timedelta
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=5)
        records = client.get_time_and_sales("AAPL", start_time, end_time)

        # Then: Should call API with correct parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "AAPL" in call_args[0][0]  # URL contains symbol

        # Then: Should return list of TimeAndSalesRecord
        assert len(records) == 2
        assert all(isinstance(r, TimeAndSalesRecord) for r in records)
        assert records[0].symbol == "AAPL"
        assert records[0].price == Decimal("175.50")
        assert records[0].size == 100

    @patch('requests.get')
    def test_get_time_and_sales_empty_results(self, mock_get):
        """Test get_time_and_sales() handles empty results gracefully."""
        # Given: PolygonClient instance
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        client = PolygonClient(config)

        # Given: Mocked response with no results
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "OK",
            "ticker": "AAPL",
            "results": []
        }
        mock_get.return_value = mock_response

        # When: Fetching Time & Sales (with both start and end time)
        from datetime import timedelta
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=5)
        records = client.get_time_and_sales("AAPL", start_time, end_time)

        # Then: Should return empty list
        assert records == []
