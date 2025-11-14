#!/usr/bin/env python3
"""
Crypto Market Data Service

Provides cryptocurrency market data using Alpaca CryptoHistoricalDataClient.

Key differences from stock data:
- 24/7 data availability (no market hours)
- Different symbols (BTC/USD vs AAPL)
- Higher volatility / wider spreads
- Uses CryptoHistoricalDataClient instead of StockHistoricalDataClient
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, CryptoLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

logger = logging.getLogger(__name__)


@dataclass
class CryptoQuote:
    """Crypto quote data."""
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    timestamp: datetime


@dataclass
class CryptoBar:
    """Crypto bar/candlestick data."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float  # Volume-weighted average price


class CryptoDataService:
    """
    Service for fetching cryptocurrency market data via Alpaca.

    Uses Alpaca's free crypto data (no subscription required for paper trading).
    Supports 24/7 data access since crypto markets never close.
    """

    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None):
        """
        Initialize crypto data service.

        Args:
            api_key: Alpaca API key (or uses ALPACA_API_KEY from env)
            secret_key: Alpaca secret key (or uses ALPACA_SECRET_KEY from env)
        """
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Alpaca API credentials required. Set ALPACA_API_KEY and ALPACA_SECRET_KEY "
                "in .env file or pass to constructor"
            )

        # Initialize Alpaca crypto data client
        self.client = CryptoHistoricalDataClient(self.api_key, self.secret_key)
        logger.info("CryptoDataService initialized")

    def get_latest_quote(self, symbol: str) -> Optional[CryptoQuote]:
        """
        Get the latest bid/ask quote for a crypto symbol.

        Args:
            symbol: Crypto symbol (e.g., "BTC/USD", "ETH/USD")

        Returns:
            CryptoQuote or None if fetch fails
        """
        try:
            request = CryptoLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self.client.get_crypto_latest_quote(request)

            if symbol not in quotes:
                logger.warning(f"No quote data for {symbol}")
                return None

            quote = quotes[symbol]

            return CryptoQuote(
                symbol=symbol,
                bid=float(quote.bid_price),
                ask=float(quote.ask_price),
                bid_size=float(quote.bid_size),
                ask_size=float(quote.ask_size),
                timestamp=quote.timestamp
            )

        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None

    def get_bars(
        self,
        symbol: str,
        timeframe: str = "1h",
        days: int = 30,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[CryptoBar]:
        """
        Get historical bar data for a crypto symbol.

        Args:
            symbol: Crypto symbol (e.g., "BTC/USD")
            timeframe: Bar timeframe ("1m", "5m", "15m", "1h", "4h", "1d")
            days: Number of days of history (if start/end not provided)
            start: Start datetime (optional)
            end: End datetime (optional)

        Returns:
            List of CryptoBar objects
        """
        try:
            # Map timeframe string to Alpaca TimeFrame
            timeframe_map = {
                "1m": TimeFrame.Minute,
                "5m": TimeFrame(5, "Min"),
                "15m": TimeFrame(15, "Min"),
                "1h": TimeFrame.Hour,
                "4h": TimeFrame(4, "Hour"),
                "1d": TimeFrame.Day,
            }

            if timeframe not in timeframe_map:
                raise ValueError(f"Invalid timeframe: {timeframe}. Use: {list(timeframe_map.keys())}")

            tf = timeframe_map[timeframe]

            # Calculate start/end if not provided
            if not end:
                end = datetime.now()
            if not start:
                start = end - timedelta(days=days)

            request = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=start,
                end=end
            )

            bars_data = self.client.get_crypto_bars(request)

            if symbol not in bars_data:
                logger.warning(f"No bar data for {symbol}")
                return []

            bars = []
            for bar in bars_data[symbol]:
                bars.append(CryptoBar(
                    symbol=symbol,
                    timestamp=bar.timestamp,
                    open=float(bar.open),
                    high=float(bar.high),
                    low=float(bar.low),
                    close=float(bar.close),
                    volume=float(bar.volume),
                    vwap=float(bar.vwap) if bar.vwap else 0.0
                ))

            logger.info(f"Fetched {len(bars)} bars for {symbol} ({timeframe})")
            return bars

        except Exception as e:
            logger.error(f"Error fetching bars for {symbol}: {e}")
            return []

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a crypto symbol (mid-point of bid/ask).

        Args:
            symbol: Crypto symbol (e.g., "BTC/USD")

        Returns:
            Current price or None if unavailable
        """
        quote = self.get_latest_quote(symbol)
        if quote:
            # Return mid-point of bid/ask spread
            return (quote.bid + quote.ask) / 2.0
        return None

    def get_24h_volume(self, symbol: str) -> Optional[float]:
        """
        Get 24-hour trading volume for a crypto symbol.

        Args:
            symbol: Crypto symbol

        Returns:
            24-hour volume or None if unavailable
        """
        bars = self.get_bars(symbol, timeframe="1h", days=1)
        if bars:
            return sum(bar.volume for bar in bars)
        return None

    def get_price_change_pct(self, symbol: str, hours: int = 24) -> Optional[float]:
        """
        Get percentage price change over the last N hours.

        Args:
            symbol: Crypto symbol
            hours: Number of hours to look back

        Returns:
            Percentage change or None if unavailable
        """
        days = max(1, hours // 24 + 1)
        bars = self.get_bars(symbol, timeframe="1h", days=days)

        if len(bars) < 2:
            return None

        # Get oldest and newest bars
        old_price = bars[0].close
        new_price = bars[-1].close

        if old_price == 0:
            return None

        pct_change = ((new_price - old_price) / old_price) * 100
        return round(pct_change, 2)

    def is_market_open(self, symbol: str) -> bool:
        """
        Check if crypto market is open.

        For crypto, this always returns True since crypto markets are 24/7.
        Included for API compatibility with stock data service.

        Args:
            symbol: Crypto symbol (unused)

        Returns:
            Always True (crypto markets never close)
        """
        return True

    def get_multi_symbol_quotes(self, symbols: List[str]) -> Dict[str, Optional[CryptoQuote]]:
        """
        Get latest quotes for multiple crypto symbols at once.

        Args:
            symbols: List of crypto symbols

        Returns:
            Dict mapping symbol to CryptoQuote (or None if failed)
        """
        quotes = {}

        try:
            request = CryptoLatestQuoteRequest(symbol_or_symbols=symbols)
            data = self.client.get_crypto_latest_quote(request)

            for symbol in symbols:
                if symbol in data:
                    quote = data[symbol]
                    quotes[symbol] = CryptoQuote(
                        symbol=symbol,
                        bid=float(quote.bid_price),
                        ask=float(quote.ask_price),
                        bid_size=float(quote.bid_size),
                        ask_size=float(quote.ask_size),
                        timestamp=quote.timestamp
                    )
                else:
                    quotes[symbol] = None

        except Exception as e:
            logger.error(f"Error fetching multi-symbol quotes: {e}")
            for symbol in symbols:
                quotes[symbol] = None

        return quotes
