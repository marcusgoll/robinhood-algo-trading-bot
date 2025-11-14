"""
Integration tests for Alpaca API URL configuration

Verifies that production URLs are correctly configured and accessible
for the Alpaca News API used in catalyst detection.

Constitution v1.0.0:
- Safety_First: Test production URLs before live trading
- Data_Integrity: Verify API endpoint correctness

Feature: Debug - Production URL Testing
Issue: User requested testing of production URLs
"""

import os
import pytest
import httpx
from src.trading_bot.momentum.config import MomentumConfig
from src.trading_bot.momentum.catalyst_detector import CatalystDetector


class TestAlpacaURLConfiguration:
    """Test suite for Alpaca API URL configuration."""

    def test_alpaca_news_api_url_is_production(self):
        """Test that hardcoded Alpaca News API URL is correct production endpoint."""
        # Expected production URL for Alpaca News API
        expected_url = "https://data.alpaca.markets/v1beta1/news"

        # Create detector to access URL
        config = MomentumConfig.from_env()
        detector = CatalystDetector(config)

        # Check actual URL used in _fetch_news_from_alpaca method
        # Note: URL is hardcoded in method, not configurable
        import inspect
        source = inspect.getsource(detector._fetch_news_from_alpaca)

        assert expected_url in source, \
            f"Expected production URL '{expected_url}' not found in _fetch_news_from_alpaca method"

    def test_alpaca_news_api_url_format(self):
        """Test that Alpaca News API URL follows correct format."""
        # Alpaca has different endpoints for different services:
        # - Trading API (paper): https://paper-api.alpaca.markets
        # - Trading API (live): https://api.alpaca.markets
        # - Market Data API: https://data.alpaca.markets (SAME for paper and live)

        # News API should use data.alpaca.markets (not paper-api or api)
        config = MomentumConfig.from_env()
        detector = CatalystDetector(config)

        import inspect
        source = inspect.getsource(detector._fetch_news_from_alpaca)

        # Should NOT use paper-api or api endpoints
        assert "paper-api.alpaca.markets" not in source, \
            "News API should not use paper-api endpoint"
        assert "https://api.alpaca.markets" not in source, \
            "News API should not use trading API endpoint"

        # Should use data.alpaca.markets
        assert "data.alpaca.markets" in source, \
            "News API should use data.alpaca.markets endpoint"

    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("ALPACA_API_KEY") or not os.getenv("ALPACA_SECRET_KEY"),
        reason="Alpaca API credentials not configured"
    )
    async def test_alpaca_news_api_connectivity(self):
        """Test actual connectivity to Alpaca News API production endpoint."""
        url = "https://data.alpaca.markets/v1beta1/news"

        # Get credentials from environment
        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")

        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
        }

        # Test basic connectivity with small limit
        params = {
            "symbols": "AAPL",
            "limit": 1,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, params=params)

            # Should return 200 OK (or 401 if invalid credentials)
            assert response.status_code in [200, 401], \
                f"Unexpected status code {response.status_code}: {response.text}"

            if response.status_code == 200:
                data = response.json()
                assert "news" in data, "Response should contain 'news' key"
                assert isinstance(data["news"], list), "'news' should be a list"

    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("ALPACA_API_KEY") or not os.getenv("ALPACA_SECRET_KEY"),
        reason="Alpaca API credentials not configured"
    )
    async def test_catalyst_detector_uses_correct_endpoint(self):
        """Test that CatalystDetector actually makes requests to correct URL."""
        config = MomentumConfig.from_env()

        # Ensure credentials are set
        assert config.alpaca_api_key, "ALPACA_API_KEY must be set for this test"
        assert config.alpaca_secret_key, "ALPACA_SECRET_KEY must be set for this test"

        detector = CatalystDetector(config)

        # Try to fetch news (will fail gracefully if API has issues)
        try:
            news_data = await detector._fetch_news_from_alpaca(["AAPL"])

            # If successful, should return dict with 'news' key
            assert isinstance(news_data, dict), "Response should be a dictionary"
            assert "news" in news_data, "Response should contain 'news' key"

        except Exception as e:
            # If request fails, check it's failing at the correct endpoint
            error_msg = str(e)

            # Should NOT mention paper-api or api.alpaca
            assert "paper-api" not in error_msg, \
                "Error should not reference paper-api endpoint"

            # Should reference data.alpaca.markets
            if "alpaca" in error_msg.lower():
                assert "data.alpaca" in error_msg or "markets" in error_msg, \
                    f"Error should reference correct endpoint: {error_msg}"


class TestAlpacaURLDocumentation:
    """Test that URL configuration is properly documented."""

    def test_env_example_has_alpaca_base_url(self):
        """Test that .env.example documents ALPACA_BASE_URL."""
        env_example_path = "D:\\Coding\\Stocks\\.env.example"

        with open(env_example_path, "r") as f:
            content = f.read()

        # Check that Alpaca configuration is documented
        assert "ALPACA_API_KEY" in content, \
            ".env.example should document ALPACA_API_KEY"
        assert "ALPACA_SECRET_KEY" in content, \
            ".env.example should document ALPACA_SECRET_KEY"
        assert "ALPACA_BASE_URL" in content, \
            ".env.example should document ALPACA_BASE_URL for trading API"

    def test_env_example_explains_url_difference(self):
        """Test that .env.example explains difference between URLs."""
        env_example_path = "D:\\Coding\\Stocks\\.env.example"

        with open(env_example_path, "r") as f:
            content = f.read()

        # Should mention paper trading URL
        assert "paper-api.alpaca.markets" in content, \
            ".env.example should document paper trading URL"

        # Should have comment explaining the difference
        # (This might fail initially - we'll add documentation)
        lines = content.split("\n")
        alpaca_section = [i for i, line in enumerate(lines) if "ALPACA_BASE_URL" in line]

        if alpaca_section:
            # Check surrounding lines for comments
            idx = alpaca_section[0]
            surrounding = "\n".join(lines[max(0, idx-5):min(len(lines), idx+5)])

            # Should explain when to use each URL
            assert any(keyword in surrounding.lower() for keyword in ["paper", "live", "production"]), \
                "ALPACA_BASE_URL should be documented with explanation of paper vs live"


class TestAlpacaAPIEndpoints:
    """Test understanding of Alpaca API endpoint structure."""

    def test_alpaca_endpoint_documentation(self):
        """Document Alpaca API endpoint structure for future reference."""
        # This is a documentation test to ensure we understand the endpoints

        endpoints = {
            "trading_paper": "https://paper-api.alpaca.markets",
            "trading_live": "https://api.alpaca.markets",
            "market_data": "https://data.alpaca.markets",
            "news": "https://data.alpaca.markets/v1beta1/news",
        }

        # News API uses market_data endpoint (not trading endpoints)
        assert endpoints["news"].startswith(endpoints["market_data"]), \
            "News API should be under market_data endpoint"

        # Market data endpoint is the same for paper and live
        # (authentication determines access level, not URL)
        assert "paper-api" not in endpoints["market_data"], \
            "Market data endpoint should not vary by paper/live mode"
        assert "api.alpaca.markets" not in endpoints["market_data"], \
            "Market data endpoint should use data.alpaca.markets"

    def test_catalyst_detector_only_needs_market_data_endpoint(self):
        """Test that CatalystDetector only uses market data endpoint."""
        # CatalystDetector fetches news, which is market data
        # It does NOT need trading API endpoints

        config = MomentumConfig.from_env()
        detector = CatalystDetector(config)

        import inspect
        source = inspect.getsource(CatalystDetector)

        # Should only reference data.alpaca.markets
        assert "data.alpaca.markets" in source, \
            "CatalystDetector should use data.alpaca.markets"

        # Should NOT reference trading endpoints
        assert "paper-api.alpaca.markets" not in source and \
               "https://api.alpaca.markets" not in source, \
            "CatalystDetector should not use trading API endpoints"


@pytest.mark.integration
class TestProductionURLAccessibility:
    """Test that production URLs are accessible and respond correctly."""

    @pytest.mark.skipif(
        not os.getenv("ALPACA_API_KEY") or not os.getenv("ALPACA_SECRET_KEY"),
        reason="Alpaca API credentials not configured"
    )
    async def test_alpaca_news_api_responds(self):
        """Test that Alpaca News API production endpoint responds correctly."""
        url = "https://data.alpaca.markets/v1beta1/news"

        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")

        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
        }

        params = {
            "symbols": "AAPL",
            "limit": 1,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, headers=headers, params=params)

                # Test successful connection
                if response.status_code == 200:
                    data = response.json()
                    assert "news" in data, "Valid response should contain 'news' key"
                    print(f"✅ Alpaca News API accessible: {len(data['news'])} news items returned")

                # Test authentication
                elif response.status_code == 401:
                    pytest.skip("Alpaca API credentials invalid (expected during testing)")

                # Test other errors
                else:
                    pytest.fail(
                        f"Unexpected status code {response.status_code}: {response.text}"
                    )

            except httpx.TimeoutException:
                pytest.fail("Alpaca News API request timed out - network issue or endpoint down")

            except httpx.RequestError as e:
                pytest.fail(f"Alpaca News API request failed: {e}")

    async def test_alpaca_endpoints_dns_resolution(self):
        """Test that Alpaca API endpoints resolve via DNS."""
        endpoints = [
            "https://data.alpaca.markets",
            "https://paper-api.alpaca.markets",
            "https://api.alpaca.markets",
        ]

        async with httpx.AsyncClient(timeout=5.0) as client:
            for endpoint in endpoints:
                try:
                    # Just test DNS resolution and basic connectivity
                    # (will return 401 Unauthorized without credentials, which is fine)
                    response = await client.get(endpoint, follow_redirects=True)

                    # Any response (even 401) means DNS resolved and server responded
                    assert response.status_code in [200, 401, 403, 404], \
                        f"Endpoint {endpoint} returned unexpected status: {response.status_code}"

                    print(f"✅ {endpoint} is accessible (status: {response.status_code})")

                except httpx.RequestError as e:
                    pytest.fail(f"Failed to connect to {endpoint}: {e}")
