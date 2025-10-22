"""
Unit tests for order flow validators.

Tests:
- T032: validate_level2_data() rejects stale timestamps and malformed data
- T033: validate_tape_data() rejects chronological violations and edge cases

Feature: level-2-order-flow-i
Task: T032, T033 [RED] - Write tests for validators
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_bot.market_data.exceptions import DataValidationError
from trading_bot.order_flow.data_models import OrderBookSnapshot, TimeAndSalesRecord
from trading_bot.order_flow.validators import validate_level2_data, validate_tape_data


class TestValidateLevel2Data:
    """Test suite for validate_level2_data() function (T032)."""

    def test_rejects_stale_timestamp_over_30_seconds(self):
        """Test that validate_level2_data() rejects timestamps >30 seconds old."""
        # Given: OrderBookSnapshot with stale timestamp (35 seconds ago)
        stale_time = datetime.now(UTC) - timedelta(seconds=35)
        snapshot = OrderBookSnapshot(
            symbol="AAPL",
            timestamp_utc=stale_time,
            bids=[(Decimal("150.00"), 1000)],
            asks=[(Decimal("150.05"), 1000)],
        )

        # When/Then: Should raise DataValidationError
        with pytest.raises(DataValidationError, match="Level 2 data too stale"):
            validate_level2_data(snapshot)

    def test_rejects_very_stale_timestamp_over_60_seconds(self):
        """Test that validate_level2_data() rejects very stale timestamps."""
        # Given: OrderBookSnapshot with very stale timestamp (90 seconds ago)
        very_stale_time = datetime.now(UTC) - timedelta(seconds=90)
        snapshot = OrderBookSnapshot(
            symbol="TSLA",
            timestamp_utc=very_stale_time,
            bids=[(Decimal("200.00"), 5000)],
            asks=[(Decimal("200.10"), 5000)],
        )

        # When/Then: Should raise DataValidationError
        with pytest.raises(DataValidationError, match="Level 2 data too stale"):
            validate_level2_data(snapshot)

    def test_warns_on_aging_timestamp_10_to_30_seconds(self, caplog):
        """Test that validate_level2_data() warns for timestamps 10-30 seconds old."""
        # Given: OrderBookSnapshot with aging timestamp (15 seconds ago)
        aging_time = datetime.now(UTC) - timedelta(seconds=15)
        snapshot = OrderBookSnapshot(
            symbol="NVDA",
            timestamp_utc=aging_time,
            bids=[(Decimal("500.00"), 2000)],
            asks=[(Decimal("500.10"), 2000)],
        )

        # When: Validating snapshot
        validate_level2_data(snapshot)  # Should not raise

        # Then: Should log warning about aging data
        assert "Level 2 data aging" in caplog.text or any(
            "aging" in record.message.lower() for record in caplog.records
        )

    def test_accepts_fresh_timestamp_under_10_seconds(self):
        """Test that validate_level2_data() accepts fresh timestamps <10 seconds."""
        # Given: OrderBookSnapshot with fresh timestamp (5 seconds ago)
        fresh_time = datetime.now(UTC) - timedelta(seconds=5)
        snapshot = OrderBookSnapshot(
            symbol="MSFT",
            timestamp_utc=fresh_time,
            bids=[(Decimal("300.00"), 1500)],
            asks=[(Decimal("300.05"), 1500)],
        )

        # When/Then: Should succeed without error
        validate_level2_data(snapshot)  # Should not raise

    def test_rejects_unsorted_bids_descending_order(self):
        """Test that validate_level2_data() rejects bids not sorted descending."""
        # Given: OrderBookSnapshot with unsorted bids (ascending instead of descending)
        snapshot = OrderBookSnapshot(
            symbol="AAPL",
            timestamp_utc=datetime.now(UTC),
            bids=[
                (Decimal("149.00"), 1000),  # Invalid: lower price first
                (Decimal("150.00"), 1000),  # Should be higher price first
            ],
            asks=[(Decimal("150.05"), 1000)],
        )

        # When/Then: Should raise DataValidationError
        with pytest.raises(DataValidationError, match="bids not sorted descending"):
            validate_level2_data(snapshot)

    def test_rejects_unsorted_asks_ascending_order(self):
        """Test that validate_level2_data() rejects asks not sorted ascending."""
        # Given: OrderBookSnapshot with unsorted asks (descending instead of ascending)
        snapshot = OrderBookSnapshot(
            symbol="GOOGL",
            timestamp_utc=datetime.now(UTC),
            bids=[(Decimal("150.00"), 1000)],
            asks=[
                (Decimal("151.00"), 1000),  # Invalid: higher price first
                (Decimal("150.50"), 1000),  # Should be lower price first
            ],
        )

        # When/Then: Should raise DataValidationError
        with pytest.raises(DataValidationError, match="asks not sorted ascending"):
            validate_level2_data(snapshot)

    def test_accepts_properly_sorted_bids_and_asks(self):
        """Test that validate_level2_data() accepts properly sorted order book."""
        # Given: OrderBookSnapshot with correctly sorted bids (desc) and asks (asc)
        snapshot = OrderBookSnapshot(
            symbol="AMZN",
            timestamp_utc=datetime.now(UTC),
            bids=[
                (Decimal("150.00"), 1000),  # Highest bid
                (Decimal("149.95"), 1500),
                (Decimal("149.90"), 2000),  # Lowest bid
            ],
            asks=[
                (Decimal("150.05"), 1000),  # Lowest ask
                (Decimal("150.10"), 1500),
                (Decimal("150.15"), 2000),  # Highest ask
            ],
        )

        # When/Then: Should succeed without error
        validate_level2_data(snapshot)

    def test_accepts_empty_bids_or_asks(self):
        """Test that validate_level2_data() accepts empty bids or asks lists."""
        # Given: OrderBookSnapshot with empty asks (only bids)
        snapshot_no_asks = OrderBookSnapshot(
            symbol="META",
            timestamp_utc=datetime.now(UTC),
            bids=[(Decimal("300.00"), 1000)],
            asks=[],  # Empty asks
        )

        # When/Then: Should succeed without error
        validate_level2_data(snapshot_no_asks)

        # Given: OrderBookSnapshot with empty bids (only asks)
        snapshot_no_bids = OrderBookSnapshot(
            symbol="NFLX",
            timestamp_utc=datetime.now(UTC),
            bids=[],  # Empty bids
            asks=[(Decimal("400.00"), 1000)],
        )

        # When/Then: Should succeed without error
        validate_level2_data(snapshot_no_bids)


class TestValidateTapeData:
    """Test suite for validate_tape_data() function (T033)."""

    def test_rejects_chronological_violation_later_tick_earlier_timestamp(self):
        """Test that validate_tape_data() rejects later tick with earlier timestamp."""
        # Given: Tape records with timestamp going backwards
        records = [
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("150.00"),
                size=100,
                side="buy",
                timestamp_utc=datetime.now(UTC) - timedelta(seconds=10),
            ),
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("150.05"),
                size=200,
                side="sell",
                timestamp_utc=datetime.now(UTC) - timedelta(seconds=15),  # Earlier!
            ),
        ]

        # When/Then: Should raise DataValidationError
        with pytest.raises(DataValidationError, match="not chronological"):
            validate_tape_data(records)

    def test_rejects_multiple_chronological_violations(self):
        """Test that validate_tape_data() catches first chronological violation."""
        # Given: Multiple records with timestamps out of order
        base_time = datetime.now(UTC)
        records = [
            TimeAndSalesRecord(
                symbol="TSLA",
                price=Decimal("200.00"),
                size=100,
                side="buy",
                timestamp_utc=base_time - timedelta(seconds=30),
            ),
            TimeAndSalesRecord(
                symbol="TSLA",
                price=Decimal("200.10"),
                size=200,
                side="sell",
                timestamp_utc=base_time - timedelta(seconds=20),  # OK: later
            ),
            TimeAndSalesRecord(
                symbol="TSLA",
                price=Decimal("200.05"),
                size=150,
                side="buy",
                timestamp_utc=base_time - timedelta(seconds=25),  # Violation!
            ),
        ]

        # When/Then: Should raise DataValidationError on first violation
        with pytest.raises(DataValidationError, match="not chronological"):
            validate_tape_data(records)

    def test_accepts_chronological_sequence(self):
        """Test that validate_tape_data() accepts properly ordered timestamps."""
        # Given: Tape records with strictly increasing timestamps
        base_time = datetime.now(UTC)
        records = [
            TimeAndSalesRecord(
                symbol="NVDA",
                price=Decimal("500.00"),
                size=100,
                side="buy",
                timestamp_utc=base_time - timedelta(seconds=30),
            ),
            TimeAndSalesRecord(
                symbol="NVDA",
                price=Decimal("500.10"),
                size=200,
                side="sell",
                timestamp_utc=base_time - timedelta(seconds=20),
            ),
            TimeAndSalesRecord(
                symbol="NVDA",
                price=Decimal("500.05"),
                size=150,
                side="buy",
                timestamp_utc=base_time - timedelta(seconds=10),
            ),
        ]

        # When/Then: Should succeed without error
        validate_tape_data(records)

    def test_accepts_equal_timestamps(self):
        """Test that validate_tape_data() accepts simultaneous trades (equal timestamps)."""
        # Given: Tape records with identical timestamps (simultaneous trades)
        same_time = datetime.now(UTC)
        records = [
            TimeAndSalesRecord(
                symbol="MSFT",
                price=Decimal("300.00"),
                size=100,
                side="buy",
                timestamp_utc=same_time,
            ),
            TimeAndSalesRecord(
                symbol="MSFT",
                price=Decimal("300.00"),
                size=200,
                side="sell",
                timestamp_utc=same_time,  # Same timestamp
            ),
        ]

        # When/Then: Should succeed (not strictly increasing, but non-decreasing)
        validate_tape_data(records)

    def test_data_model_validates_price_at_construction(self):
        """Test that TimeAndSalesRecord validates price at construction time."""
        # Given: Attempt to create record with invalid price
        # When/Then: Should raise ValueError at construction (before validator)
        with pytest.raises(ValueError, match="price.*must be >\\$0"):
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("0.00"),  # Invalid: price must be >0
                size=100,
                side="buy",
                timestamp_utc=datetime.now(UTC),
            )

    def test_data_model_validates_size_at_construction(self):
        """Test that TimeAndSalesRecord validates size at construction time."""
        # Given: Attempt to create record with invalid size
        # When/Then: Should raise ValueError at construction (before validator)
        with pytest.raises(ValueError, match="size.*must be >0 shares"):
            TimeAndSalesRecord(
                symbol="TSLA",
                price=Decimal("200.00"),
                size=0,  # Invalid: size must be >0
                side="sell",
                timestamp_utc=datetime.now(UTC),
            )

    def test_accepts_empty_records_list(self):
        """Test that validate_tape_data() accepts empty list (no trades)."""
        # Given: Empty tape records list
        records = []

        # When/Then: Should succeed without error (empty is valid)
        validate_tape_data(records)

    def test_accepts_single_record(self):
        """Test that validate_tape_data() accepts single record (no comparison needed)."""
        # Given: Single tape record
        records = [
            TimeAndSalesRecord(
                symbol="GOOGL",
                price=Decimal("150.00"),
                size=500,
                side="buy",
                timestamp_utc=datetime.now(UTC),
            )
        ]

        # When/Then: Should succeed without error
        validate_tape_data(records)

    def test_validates_all_records_in_large_batch(self):
        """Test that validate_tape_data() checks all records in large batch."""
        # Given: Large batch of tape records (100 records)
        base_time = datetime.now(UTC)
        records = [
            TimeAndSalesRecord(
                symbol="SPY",
                price=Decimal("400.00") + Decimal(str(i * 0.01)),
                size=100 + i,
                side="buy" if i % 2 == 0 else "sell",
                timestamp_utc=base_time + timedelta(milliseconds=i * 100),
            )
            for i in range(100)
        ]

        # When/Then: Should succeed (all chronological and valid)
        validate_tape_data(records)
