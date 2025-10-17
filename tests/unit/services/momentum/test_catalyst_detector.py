"""
Unit tests for CatalystDetector service.

Tests:
- T011: categorize() classifies news headlines correctly
- T012: scan() fetches and filters news within 24 hours

Feature: momentum-detection
Task: T011, T012 [RED] - Write tests for CatalystDetector
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, Mock, patch
from typing import List

from src.trading_bot.momentum.catalyst_detector import CatalystDetector
from src.trading_bot.momentum.config import MomentumConfig
from src.trading_bot.momentum.logging.momentum_logger import MomentumLogger
from src.trading_bot.momentum.schemas.momentum_signal import (
    CatalystType,
    MomentumSignal,
    SignalType,
)


class TestCatalystDetectorCategorize:
    """Test suite for CatalystDetector.categorize() method."""

    def test_categorize_earnings_headline(self):
        """Test that earnings-related headlines are categorized as EARNINGS."""
        # Given: CatalystDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        detector = CatalystDetector(config=config, momentum_logger=logger)

        # When: Categorizing earnings headlines
        test_cases = [
            "Company announces Q4 earnings beat",
            "EPS exceeds expectations by 20%",
            "Revenue guidance raised for next quarter",
            "Quarterly earnings report released",
        ]

        # Then: All should be categorized as EARNINGS
        for headline in test_cases:
            result = detector.categorize(headline)
            assert result == CatalystType.EARNINGS, f"Failed for headline: {headline}"

    def test_categorize_fda_headline(self):
        """Test that FDA-related headlines are categorized as FDA."""
        # Given: CatalystDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        detector = CatalystDetector(config=config, momentum_logger=logger)

        # When: Categorizing FDA headlines
        test_cases = [
            "FDA approval granted for new drug",
            "Clinical trial results show promise",
            "FDA advisory panel recommends approval",
        ]

        # Then: All should be categorized as FDA
        for headline in test_cases:
            result = detector.categorize(headline)
            assert result == CatalystType.FDA, f"Failed for headline: {headline}"

    def test_categorize_merger_headline(self):
        """Test that merger-related headlines are categorized as MERGER."""
        # Given: CatalystDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        detector = CatalystDetector(config=config, momentum_logger=logger)

        # When: Categorizing merger headlines
        test_cases = [
            "Merger announced with competitor",
            "Acquisition deal valued at $10B",
            "Company to acquire startup",
        ]

        # Then: All should be categorized as MERGER
        for headline in test_cases:
            result = detector.categorize(headline)
            assert result == CatalystType.MERGER, f"Failed for headline: {headline}"

    def test_categorize_product_headline(self):
        """Test that product-related headlines are categorized as PRODUCT."""
        # Given: CatalystDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        detector = CatalystDetector(config=config, momentum_logger=logger)

        # When: Categorizing product headlines
        test_cases = [
            "New product launch announced",
            "Company unveils next-gen technology",
            "Product release scheduled for Q3",
            "Company announces new service offering",
        ]

        # Then: All should be categorized as PRODUCT
        for headline in test_cases:
            result = detector.categorize(headline)
            assert result == CatalystType.PRODUCT, f"Failed for headline: {headline}"

    def test_categorize_analyst_headline(self):
        """Test that analyst-related headlines are categorized as ANALYST."""
        # Given: CatalystDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        detector = CatalystDetector(config=config, momentum_logger=logger)

        # When: Categorizing analyst headlines
        test_cases = [
            "Analyst upgrades stock to Buy",
            "Price target downgraded by Goldman Sachs",
            "Coverage initiated with Outperform rating",
            "Analyst raises price target to $200",
        ]

        # Then: All should be categorized as ANALYST
        for headline in test_cases:
            result = detector.categorize(headline)
            assert result == CatalystType.ANALYST, f"Failed for headline: {headline}"

    def test_categorize_default_to_product(self):
        """Test that unknown headlines default to PRODUCT."""
        # Given: CatalystDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        detector = CatalystDetector(config=config, momentum_logger=logger)

        # When: Categorizing non-specific headlines
        test_cases = [
            "Company makes announcement",
            "News update about stock",
            "Breaking news alert",
        ]

        # Then: All should default to PRODUCT (most generic category)
        for headline in test_cases:
            result = detector.categorize(headline)
            assert result == CatalystType.PRODUCT, f"Failed for headline: {headline}"

    def test_categorize_case_insensitive(self):
        """Test that categorization is case-insensitive."""
        # Given: CatalystDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        detector = CatalystDetector(config=config, momentum_logger=logger)

        # When: Categorizing mixed-case headlines
        test_cases = [
            ("EARNINGS BEAT EXPECTATIONS", CatalystType.EARNINGS),
            ("fda approval granted", CatalystType.FDA),
            ("MeRgEr AnNoUnCeD", CatalystType.MERGER),
            ("PRODUCT LAUNCH", CatalystType.PRODUCT),
            ("upgrade to buy", CatalystType.ANALYST),
        ]

        # Then: Case should not affect categorization
        for headline, expected_type in test_cases:
            result = detector.categorize(headline)
            assert result == expected_type, f"Failed for headline: {headline}"


class TestCatalystDetectorScan:
    """Test suite for CatalystDetector.scan() method."""

    @pytest.mark.asyncio
    async def test_scan_filters_news_within_24_hours(self):
        """Test that scan() only returns news published within last 24 hours."""
        # Given: CatalystDetector with mocked Alpaca API
        config = MomentumConfig(news_api_key="test-key")
        logger = MomentumLogger()
        detector = CatalystDetector(config=config, momentum_logger=logger)

        # Mock Alpaca API response with fresh and stale news
        now = datetime.now(UTC)
        fresh_news = {
            "headline": "AAPL announces Q4 earnings beat",
            "created_at": (now - timedelta(hours=12)).isoformat(),
            "symbols": ["AAPL"],
        }
        stale_news = {
            "headline": "AAPL unveils new product",
            "created_at": (now - timedelta(hours=30)).isoformat(),
            "symbols": ["AAPL"],
        }

        mock_response = {"news": [fresh_news, stale_news]}

        with patch.object(detector, "_fetch_news_from_alpaca", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response

            # When: Scanning for catalysts
            symbols = ["AAPL"]
            signals = await detector.scan(symbols)

            # Then: Only fresh news should be in signals
            assert len(signals) == 1
            assert signals[0].symbol == "AAPL"
            assert "earnings" in signals[0].details["headline"].lower()

    @pytest.mark.asyncio
    async def test_scan_categorizes_catalyst_type(self):
        """Test that scan() correctly categorizes catalyst types."""
        # Given: CatalystDetector with mocked Alpaca API
        config = MomentumConfig(news_api_key="test-key")
        logger = MomentumLogger()
        detector = CatalystDetector(config=config, momentum_logger=logger)

        # Mock Alpaca API response with different catalyst types
        now = datetime.now(UTC)
        news_items = [
            {
                "headline": "AAPL Q4 earnings beat expectations",
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "symbols": ["AAPL"],
            },
            {
                "headline": "GOOGL gets FDA approval for health device",
                "created_at": (now - timedelta(hours=5)).isoformat(),
                "symbols": ["GOOGL"],
            },
        ]

        mock_response = {"news": news_items}

        with patch.object(detector, "_fetch_news_from_alpaca", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response

            # When: Scanning for catalysts
            symbols = ["AAPL", "GOOGL"]
            signals = await detector.scan(symbols)

            # Then: Catalyst types should be correct
            assert len(signals) == 2

            aapl_signal = next(s for s in signals if s.symbol == "AAPL")
            assert aapl_signal.details["catalyst_type"] == CatalystType.EARNINGS.value

            googl_signal = next(s for s in signals if s.symbol == "GOOGL")
            assert googl_signal.details["catalyst_type"] == CatalystType.FDA.value

    @pytest.mark.asyncio
    async def test_scan_builds_momentum_signals(self):
        """Test that scan() builds MomentumSignal objects with correct structure."""
        # Given: CatalystDetector with mocked Alpaca API
        config = MomentumConfig(news_api_key="test-key")
        logger = MomentumLogger()
        detector = CatalystDetector(config=config, momentum_logger=logger)

        # Mock Alpaca API response
        now = datetime.now(UTC)
        news_item = {
            "headline": "AAPL announces merger with competitor",
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "symbols": ["AAPL"],
            "source": "Benzinga",
        }

        mock_response = {"news": [news_item]}

        with patch.object(detector, "_fetch_news_from_alpaca", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response

            # When: Scanning for catalysts
            symbols = ["AAPL"]
            signals = await detector.scan(symbols)

            # Then: MomentumSignal should have correct structure
            assert len(signals) == 1
            signal = signals[0]

            assert isinstance(signal, MomentumSignal)
            assert signal.symbol == "AAPL"
            assert signal.signal_type == SignalType.CATALYST
            assert 0 <= signal.strength <= 100
            assert isinstance(signal.detected_at, datetime)
            assert "headline" in signal.details
            assert "catalyst_type" in signal.details
            assert "source" in signal.details

    @pytest.mark.asyncio
    async def test_scan_handles_api_error_gracefully(self):
        """Test that scan() handles API errors without crashing."""
        # Given: CatalystDetector with failing API
        config = MomentumConfig(news_api_key="test-key")
        logger = MomentumLogger()
        detector = CatalystDetector(config=config, momentum_logger=logger)

        # Mock API failure
        with patch.object(detector, "_fetch_news_from_alpaca", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ConnectionError("API timeout")

            # When: Scanning for catalysts
            symbols = ["AAPL"]
            signals = await detector.scan(symbols)

            # Then: Should return empty list and log error (graceful degradation)
            assert signals == []

    @pytest.mark.asyncio
    async def test_scan_handles_missing_api_key(self):
        """Test that scan() handles missing NEWS_API_KEY gracefully."""
        # Given: CatalystDetector without API key
        config = MomentumConfig(news_api_key="")
        logger = MomentumLogger()
        detector = CatalystDetector(config=config, momentum_logger=logger)

        # When: Scanning for catalysts
        symbols = ["AAPL"]
        signals = await detector.scan(symbols)

        # Then: Should return empty list with warning log
        assert signals == []

    @pytest.mark.asyncio
    async def test_scan_logs_signals(self):
        """Test that scan() logs detected signals via MomentumLogger."""
        # Given: CatalystDetector with mocked logger
        config = MomentumConfig(news_api_key="test-key")
        mock_logger = Mock(spec=MomentumLogger)
        detector = CatalystDetector(config=config, momentum_logger=mock_logger)

        # Mock Alpaca API response
        now = datetime.now(UTC)
        news_item = {
            "headline": "AAPL earnings beat",
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "symbols": ["AAPL"],
        }

        mock_response = {"news": [news_item]}

        with patch.object(detector, "_fetch_news_from_alpaca", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response

            # When: Scanning for catalysts
            symbols = ["AAPL"]
            signals = await detector.scan(symbols)

            # Then: Logger should be called for each signal
            assert mock_logger.log_signal.call_count == 1
            call_args = mock_logger.log_signal.call_args

            # Verify signal dict structure
            signal_dict = call_args[0][0]
            assert signal_dict["signal_type"] == SignalType.CATALYST.value
            assert signal_dict["symbol"] == "AAPL"

            # Verify metadata
            metadata = call_args[0][1]
            assert metadata["source"] == "catalyst"

    @pytest.mark.asyncio
    async def test_scan_processes_multiple_symbols(self):
        """Test that scan() processes multiple symbols correctly."""
        # Given: CatalystDetector with mocked Alpaca API
        config = MomentumConfig(news_api_key="test-key")
        logger = MomentumLogger()
        detector = CatalystDetector(config=config, momentum_logger=logger)

        # Mock Alpaca API response for multiple symbols
        now = datetime.now(UTC)
        news_items = [
            {
                "headline": "AAPL earnings beat",
                "created_at": (now - timedelta(hours=1)).isoformat(),
                "symbols": ["AAPL"],
            },
            {
                "headline": "GOOGL merger announced",
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "symbols": ["GOOGL"],
            },
            {
                "headline": "TSLA product launch",
                "created_at": (now - timedelta(hours=3)).isoformat(),
                "symbols": ["TSLA"],
            },
        ]

        mock_response = {"news": news_items}

        with patch.object(detector, "_fetch_news_from_alpaca", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response

            # When: Scanning for catalysts
            symbols = ["AAPL", "GOOGL", "TSLA"]
            signals = await detector.scan(symbols)

            # Then: All symbols should have signals
            assert len(signals) == 3
            symbols_with_signals = {s.symbol for s in signals}
            assert symbols_with_signals == {"AAPL", "GOOGL", "TSLA"}
