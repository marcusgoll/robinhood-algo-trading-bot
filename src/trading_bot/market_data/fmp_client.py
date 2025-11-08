"""Financial Modeling Prep (FMP) API client with rate limiting.

Free tier: 250 calls/day
Provides: EOD fundamental data, company metrics, analyst ratings, insider transactions
"""

import os
import logging
import time
from datetime import date, datetime
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger(__name__)


class FMPRateLimitExceeded(Exception):
    """Raised when daily FMP API limit is exceeded."""
    pass


class FMPClient:
    """Client for Financial Modeling Prep API with rate limiting.

    Free tier limits:
    - 250 calls per day
    - EOD data only (no real-time)
    - 5 years historical data

    Tracks usage and resets counter at midnight.
    """

    FREE_TIER_DAILY_LIMIT = 250
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize FMP client with API key and rate limiter.

        Args:
            api_key: FMP API key (uses FMP_API_KEY env var if None)
        """
        self.api_key = api_key or os.getenv("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY not found in environment")

        # Rate limiting state
        self.calls_today = 0
        self.last_reset_date = date.today()

        logger.info(f"FMPClient initialized (limit: {self.FREE_TIER_DAILY_LIMIT}/day)")

    def _check_and_increment_limit(self) -> None:
        """Check if rate limit exceeded and increment counter.

        Resets counter at midnight.

        Raises:
            FMPRateLimitExceeded: If daily limit reached
        """
        # Reset counter if new day
        today = date.today()
        if today != self.last_reset_date:
            logger.info(
                f"FMP rate limit reset: {self.calls_today} calls used yesterday"
            )
            self.calls_today = 0
            self.last_reset_date = today

        # Check limit
        if self.calls_today >= self.FREE_TIER_DAILY_LIMIT:
            raise FMPRateLimitExceeded(
                f"FMP daily limit reached ({self.FREE_TIER_DAILY_LIMIT}/day). "
                f"Resets at midnight."
            )

        self.calls_today += 1

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make API request to FMP with rate limiting.

        Args:
            endpoint: API endpoint (e.g., "profile/AAPL")
            params: Additional query parameters

        Returns:
            JSON response data

        Raises:
            FMPRateLimitExceeded: If daily limit reached
            requests.RequestException: If API call fails
        """
        self._check_and_increment_limit()

        # Build request
        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params['apikey'] = self.api_key

        # Make request
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            logger.debug(
                f"FMP API call successful: {endpoint} "
                f"(calls today: {self.calls_today}/{self.FREE_TIER_DAILY_LIMIT})"
            )

            return data

        except requests.RequestException as e:
            logger.error(f"FMP API error for {endpoint}: {e}")
            raise

    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Get company profile with fundamentals.

        Includes: sector, industry, market cap, P/E, beta, dividend yield, etc.

        Args:
            symbol: Stock symbol (e.g., "AAPL")

        Returns:
            {
                'symbol': 'AAPL',
                'companyName': 'Apple Inc.',
                'sector': 'Technology',
                'industry': 'Consumer Electronics',
                'mktCap': 3000000000000,
                'beta': 1.2,
                'pe': 30.5,
                'eps': 6.15,
                'dividend': 0.024,
                'dividendYield': 0.005,
                'debtToEquity': 1.5,
                'roe': 0.45,
                ...
            }
        """
        data = self._make_request(f"profile/{symbol}")
        return data[0] if data else {}

    def get_key_metrics(self, symbol: str, period: str = "annual", limit: int = 1) -> List[Dict[str, Any]]:
        """Get key financial metrics (P/E, P/B, ROE, ROA, etc.).

        Args:
            symbol: Stock symbol
            period: "annual" or "quarter"
            limit: Number of periods to retrieve

        Returns:
            List of metrics dictionaries with:
                - revenuePerShare
                - netIncomePerShare
                - operatingCashFlowPerShare
                - freeCashFlowPerShare
                - peRatio
                - priceToBookRatio
                - roe (return on equity)
                - roa (return on assets)
                - debtToEquity
                - evToEBITDA
                - etc.
        """
        data = self._make_request(
            f"key-metrics/{symbol}",
            params={'period': period, 'limit': limit}
        )
        return data if isinstance(data, list) else []

    def get_financial_ratios(self, symbol: str, period: str = "annual", limit: int = 1) -> List[Dict[str, Any]]:
        """Get financial ratios (profitability, liquidity, efficiency).

        Args:
            symbol: Stock symbol
            period: "annual" or "quarter"
            limit: Number of periods to retrieve

        Returns:
            List of ratio dictionaries with:
                - returnOnEquity
                - returnOnAssets
                - returnOnCapitalEmployed
                - netProfitMargin
                - operatingProfitMargin
                - currentRatio
                - quickRatio
                - debtEquityRatio
                - etc.
        """
        data = self._make_request(
            f"ratios/{symbol}",
            params={'period': period, 'limit': limit}
        )
        return data if isinstance(data, list) else []

    def get_analyst_recommendations(self, symbol: str) -> List[Dict[str, Any]]:
        """Get analyst buy/sell/hold recommendations.

        Args:
            symbol: Stock symbol

        Returns:
            List of recommendation dictionaries with:
                - symbol
                - date
                - analystRatingsbuy
                - analystRatingsHold
                - analystRatingsSell
                - analystRatingsStrongBuy
                - analystRatingsStrongSell
        """
        data = self._make_request(f"analyst-stock-recommendations/{symbol}")
        return data if isinstance(data, list) else []

    def get_insider_trades(self, symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get insider trading transactions.

        Args:
            symbol: Stock symbol
            limit: Number of transactions to retrieve

        Returns:
            List of insider trade dictionaries with:
                - filingDate
                - transactionDate
                - reportingName
                - transactionType (P-Purchase, S-Sale)
                - securitiesTransacted
                - price
                - securitiesOwned
        """
        data = self._make_request(
            f"insider-trading",
            params={'symbol': symbol, 'limit': limit}
        )
        return data if isinstance(data, list) else []

    def get_earnings_surprises(self, symbol: str, limit: int = 4) -> List[Dict[str, Any]]:
        """Get earnings surprise history (actual vs estimates).

        Args:
            symbol: Stock symbol
            limit: Number of quarters to retrieve

        Returns:
            List of earnings dictionaries with:
                - date
                - symbol
                - actualEarningResult
                - estimatedEarning
                - revenue
                - estimatedRevenue
        """
        data = self._make_request(f"earnings-surprises/{symbol}")
        return data[:limit] if isinstance(data, list) else []

    def get_company_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent company news.

        Args:
            symbol: Stock symbol
            limit: Number of articles

        Returns:
            List of news dictionaries with:
                - publishedDate
                - title
                - text (article excerpt)
                - url
                - symbol
        """
        data = self._make_request(
            f"stock_news",
            params={'tickers': symbol, 'limit': limit}
        )
        return data if isinstance(data, list) else []

    def get_eod_price(self, symbol: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """Get end-of-day historical prices.

        Args:
            symbol: Stock symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            List of price dictionaries with:
                - date
                - open
                - high
                - low
                - close
                - volume
        """
        data = self._make_request(
            f"historical-price-full/{symbol}",
            params={'from': from_date, 'to': to_date}
        )

        # Extract historical data
        if isinstance(data, dict) and 'historical' in data:
            return data['historical']
        return []

    def get_market_cap_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical market capitalization.

        Args:
            symbol: Stock symbol
            limit: Number of data points

        Returns:
            List of market cap dictionaries with:
                - date
                - marketCap
        """
        data = self._make_request(
            f"historical-market-capitalization/{symbol}",
            params={'limit': limit}
        )
        return data if isinstance(data, list) else []

    def get_rating(self, symbol: str) -> Dict[str, Any]:
        """Get overall company rating (A+ to D-).

        Combines financial metrics into single score.

        Args:
            symbol: Stock symbol

        Returns:
            {
                'symbol': 'AAPL',
                'date': '2025-01-07',
                'rating': 'A',
                'ratingScore': 4,
                'ratingRecommendation': 'Strong Buy',
                'ratingDetailsDCFScore': 5,
                'ratingDetailsROEScore': 5,
                'ratingDetailsROAScore': 5,
                'ratingDetailsDEScore': 4,
                'ratingDetailsPEScore': 3,
                'ratingDetailsPBScore': 2
            }
        """
        data = self._make_request(f"rating/{symbol}")
        return data[0] if data else {}

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics.

        Returns:
            {
                'calls_today': int,
                'remaining_calls': int,
                'limit': int,
                'reset_date': str (YYYY-MM-DD)
            }
        """
        return {
            'calls_today': self.calls_today,
            'remaining_calls': max(0, self.FREE_TIER_DAILY_LIMIT - self.calls_today),
            'limit': self.FREE_TIER_DAILY_LIMIT,
            'reset_date': str(self.last_reset_date)
        }
