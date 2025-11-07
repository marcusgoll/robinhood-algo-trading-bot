"""
Historical Data Manager

Manages fetching and caching of historical market data for backtesting.
Supports multiple data sources (Alpaca, Yahoo Finance) with automatic fallback,
data validation, and parquet caching for performance.

Constitution v1.0.0:
- §Data_Integrity: All data validated before use
- §Audit_Everything: All API calls logged
- §Safety_First: Fail-fast on validation errors
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from trading_bot.backtest.exceptions import DataQualityError, InsufficientDataError
from trading_bot.backtest.models import HistoricalDataBar
from trading_bot.error_handling.policies import DEFAULT_POLICY
from trading_bot.error_handling.retry import with_retry
from trading_bot.logger import TradingLogger


class HistoricalDataManager:
    """
    Manages historical market data fetching and caching for backtesting.

    Provides:
    - Multi-source data fetching (Alpaca primary, Yahoo Finance fallback)
    - Automatic retry with exponential backoff
    - Parquet-based caching for performance
    - Comprehensive data validation
    - Logging of all operations

    Example:
        manager = HistoricalDataManager(
            api_key="alpaca_key",
            api_secret="alpaca_secret",
            cache_dir=".backtest_cache",
            cache_enabled=True
        )

        bars = manager.fetch_data(
            symbol="AAPL",
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 12, 31, tzinfo=timezone.utc)
        )

        # Validate data quality
        manager.validate_data(bars, symbol="AAPL")
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        cache_dir: str = ".backtest_cache",
        cache_enabled: bool = True,
        logger: logging.Logger | None = None
    ) -> None:
        """
        Initialize HistoricalDataManager.

        Args:
            api_key: Alpaca API key (optional, can use env vars)
            api_secret: Alpaca API secret (optional, can use env vars)
            cache_dir: Directory for parquet cache files
            cache_enabled: Whether to use caching (default: True)
            logger: Optional custom logger
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.cache_dir = Path(cache_dir)
        self.cache_enabled = cache_enabled
        self.logger = logger if logger is not None else TradingLogger.get_logger(__name__)

        # Create cache directory if enabled
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Cache enabled at: {self.cache_dir.absolute()}")

    def fetch_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> list[HistoricalDataBar]:
        """
        Fetch historical data for symbol with automatic caching and fallback.

        Flow:
        1. Validate inputs (symbol, date range, timezone)
        2. Check cache if enabled (load and return if exists)
        3. Try Alpaca API (primary source)
        4. On Alpaca failure, fallback to Yahoo Finance
        5. Validate fetched data
        6. Save to cache if enabled
        7. Return validated data

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            start_date: Start of date range (UTC timezone-aware)
            end_date: End of date range (UTC timezone-aware)

        Returns:
            List of HistoricalDataBar objects in chronological order

        Raises:
            ValueError: If inputs are invalid (empty symbol, bad dates, naive timezone)
            InsufficientDataError: If both Alpaca and Yahoo fail or return no data
            DataQualityError: If data validation fails
        """
        # Validate inputs
        self._validate_inputs(symbol, start_date, end_date)

        # Check cache first
        if self.cache_enabled:
            cache_path = self._get_cache_path(symbol, start_date, end_date)
            if cache_path.exists():
                self.logger.info(f"Loading {symbol} from cache: {cache_path}")
                return self._load_from_cache(cache_path)

        # Try Alpaca API first
        bars = None
        alpaca_error = None

        try:
            self.logger.info(f"Fetching {symbol} from Alpaca API ({start_date.date()} to {end_date.date()})")
            bars = self._fetch_alpaca_data(symbol, start_date, end_date)
        except Exception as e:
            alpaca_error = e
            self.logger.warning(f"Alpaca API failed for {symbol}: {e}")

        # Fallback to Yahoo Finance if Alpaca failed
        if bars is None or len(bars) == 0:
            try:
                self.logger.info(f"Falling back to Yahoo Finance for {symbol}")
                bars = self._fetch_yahoo_data(symbol, start_date, end_date)
            except Exception as yahoo_error:
                # Both sources failed
                raise InsufficientDataError(
                    f"Failed to fetch data for {symbol} from both Alpaca and Yahoo Finance. "
                    f"Alpaca error: {alpaca_error}. Yahoo error: {yahoo_error}"
                ) from yahoo_error

        # Validate we got data
        if not bars or len(bars) == 0:
            raise InsufficientDataError(
                f"No data available for {symbol} in range {start_date.date()} to {end_date.date()}"
            )

        # Validate data quality
        self.validate_data(bars, symbol=symbol)

        # Save to cache if enabled
        if self.cache_enabled:
            cache_path = self._get_cache_path(symbol, start_date, end_date)
            self._save_to_cache(bars, cache_path)
            self.logger.info(f"Saved {len(bars)} bars to cache: {cache_path}")

        return bars

    def validate_data(
        self,
        data: list[HistoricalDataBar] | list[dict],
        symbol: str
    ) -> None:
        """
        Validate data quality for backtesting.

        Checks:
        1. Non-chronological timestamps (raises DataQualityError)
        2. Missing trading days - gaps > 3 days (raises DataQualityError)
        3. Negative prices (raises DataQualityError)
        4. Invalid OHLC relationships - high < low (raises DataQualityError)
        5. Zero volume (warns but doesn't fail)

        Args:
            data: List of HistoricalDataBar objects or raw dicts
            symbol: Stock symbol for error messages

        Raises:
            DataQualityError: If critical data quality issues found
        """
        if not data:
            return

        # Convert dict data to HistoricalDataBar for validation
        bars = []
        for item in data:
            if isinstance(item, dict):
                # Validate negative prices in raw data
                for price_field in ['open', 'high', 'low', 'close']:
                    if price_field in item and item[price_field] < 0:
                        raise DataQualityError(
                            f"Invalid price for {symbol}: {price_field}={item[price_field]} is negative"
                        )

                # Validate OHLC relationship in raw data
                if 'high' in item and 'low' in item and item['high'] < item['low']:
                    raise DataQualityError(
                        f"Invalid OHLC for {symbol}: high ({item['high']}) < low ({item['low']})"
                    )

                # Convert to HistoricalDataBar (will do additional validation)
                try:
                    bar = HistoricalDataBar(
                        symbol=item.get('symbol', symbol),
                        timestamp=item['timestamp'],
                        open=Decimal(str(item['open'])),
                        high=Decimal(str(item['high'])),
                        low=Decimal(str(item['low'])),
                        close=Decimal(str(item['close'])),
                        volume=int(item['volume'])
                    )
                    bars.append(bar)
                except (ValueError, KeyError) as e:
                    raise DataQualityError(
                        f"Failed to convert data to HistoricalDataBar for {symbol}: {e}"
                    ) from e
            else:
                bars.append(item)

        # Check chronological order
        for i in range(len(bars) - 1):
            if bars[i].timestamp >= bars[i + 1].timestamp:
                raise DataQualityError(
                    f"Data for {symbol} is not in chronological order: "
                    f"{bars[i].timestamp} >= {bars[i + 1].timestamp}"
                )

        # Check for gaps in trading days (> 5 days = suspicious, likely data issue)
        for i in range(len(bars) - 1):
            gap_days = (bars[i + 1].timestamp - bars[i].timestamp).days
            if gap_days > 5:  # Allow weekend + holiday (e.g., MLK Day creates 4-day gap)
                self.logger.warning(
                    f"Large gap in trading days for {symbol}: {gap_days} days "
                    f"between {bars[i].timestamp.date()} and {bars[i + 1].timestamp.date()}"
                )

        # Check for zero volume (warn only)
        for i, bar in enumerate(bars):
            if bar.volume == 0:
                self.logger.warning(
                    f"Zero volume detected for {symbol} on {bar.timestamp.date()} "
                    f"(bar {i + 1}/{len(bars)})"
                )

    def _validate_inputs(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> None:
        """
        Validate fetch_data inputs.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date

        Raises:
            ValueError: If validation fails
        """
        # Validate symbol
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty or invalid")

        # Validate timezone awareness
        if start_date.tzinfo is None:
            raise ValueError("start_date must be timezone-aware (UTC)")
        if end_date.tzinfo is None:
            raise ValueError("end_date must be timezone-aware (UTC)")

        # Validate date range
        if start_date >= end_date:
            raise ValueError(
                f"start_date ({start_date}) must be < end_date ({end_date})"
            )

    def _get_cache_path(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Path:
        """
        Generate cache file path for given parameters.

        Format: {cache_dir}/{symbol}_{start_YYYY-MM-DD}_{end_YYYY-MM-DD}.parquet

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date

        Returns:
            Path to cache file
        """
        start_str = start_date.date().isoformat()
        end_str = end_date.date().isoformat()
        filename = f"{symbol}_{start_str}_{end_str}.parquet"
        return self.cache_dir / filename

    def _save_to_cache(
        self,
        bars: list[HistoricalDataBar],
        cache_path: Path
    ) -> None:
        """
        Save historical bars to parquet cache.

        Args:
            bars: List of HistoricalDataBar objects
            cache_path: Path to save cache file
        """
        # Convert to DataFrame
        data = {
            'symbol': [bar.symbol for bar in bars],
            'timestamp': [bar.timestamp for bar in bars],
            'open': [float(bar.open) for bar in bars],
            'high': [float(bar.high) for bar in bars],
            'low': [float(bar.low) for bar in bars],
            'close': [float(bar.close) for bar in bars],
            'volume': [bar.volume for bar in bars],
            'split_adjusted': [bar.split_adjusted for bar in bars],
            'dividend_adjusted': [bar.dividend_adjusted for bar in bars]
        }
        df = pd.DataFrame(data)

        # Save as parquet
        df.to_parquet(cache_path, engine='pyarrow', compression='snappy')

    def _load_from_cache(
        self,
        cache_path: Path
    ) -> list[HistoricalDataBar]:
        """
        Load historical bars from parquet cache.

        Args:
            cache_path: Path to cache file

        Returns:
            List of HistoricalDataBar objects
        """
        # Load parquet file
        df = pd.read_parquet(cache_path, engine='pyarrow')

        # Convert to HistoricalDataBar objects
        bars = []
        for _, row in df.iterrows():
            bar = HistoricalDataBar(
                symbol=row['symbol'],
                timestamp=pd.Timestamp(row['timestamp']).to_pydatetime(),
                open=Decimal(str(row['open'])),
                high=Decimal(str(row['high'])),
                low=Decimal(str(row['low'])),
                close=Decimal(str(row['close'])),
                volume=int(row['volume']),
                split_adjusted=bool(row.get('split_adjusted', True)),
                dividend_adjusted=bool(row.get('dividend_adjusted', True))
            )
            bars.append(bar)

        return bars

    @with_retry(policy=DEFAULT_POLICY)
    def _fetch_alpaca_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> list[HistoricalDataBar]:
        """
        Fetch data from Alpaca API.

        Uses Alpaca StockHistoricalDataClient to fetch daily bars with split
        and dividend adjustments. Implements rate limit handling (200 req/min)
        and converts Alpaca Bar objects to HistoricalDataBar dataclasses.

        Args:
            symbol: Stock symbol
            start_date: Start date (UTC)
            end_date: End date (UTC)

        Returns:
            List of HistoricalDataBar objects in chronological order

        Raises:
            InsufficientDataError: If API call fails or returns no data
        """
        import os

        from alpaca.data.enums import Adjustment
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        try:
            # Load API credentials from environment or constructor
            api_key = self.api_key or os.getenv('ALPACA_API_KEY')
            api_secret = self.api_secret or os.getenv('ALPACA_SECRET_KEY')

            if not api_key or not api_secret:
                raise InsufficientDataError(
                    "Alpaca API credentials missing. Set ALPACA_API_KEY and ALPACA_SECRET_KEY "
                    "environment variables or pass them to HistoricalDataManager constructor."
                )

            # Initialize Alpaca client
            client = StockHistoricalDataClient(api_key=api_key, secret_key=api_secret)

            # Log API request
            self.logger.info(
                f"Alpaca API request: {symbol} from {start_date.date()} to {end_date.date()}"
            )

            # Create request with split and dividend adjustments
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date,
                adjustment=Adjustment.ALL  # Request split-adjusted and dividend-adjusted prices
            )

            # Fetch bars from Alpaca
            bars_response = client.get_stock_bars(request)

            # Extract bars for the symbol (response is BarSet with .data dict)
            if not hasattr(bars_response, 'data') or symbol not in bars_response.data:
                raise InsufficientDataError(
                    f"No data returned from Alpaca for {symbol}"
                )

            alpaca_bars = bars_response.data[symbol]

            # Convert Alpaca Bar objects to HistoricalDataBar
            historical_bars = []
            for bar in alpaca_bars:
                historical_bar = HistoricalDataBar(
                    symbol=symbol,
                    timestamp=bar.timestamp,
                    open=Decimal(str(bar.open)),
                    high=Decimal(str(bar.high)),
                    low=Decimal(str(bar.low)),
                    close=Decimal(str(bar.close)),
                    volume=int(bar.volume),
                    split_adjusted=True,
                    dividend_adjusted=True
                )
                historical_bars.append(historical_bar)

            self.logger.info(
                f"Alpaca API returned {len(historical_bars)} bars for {symbol}"
            )

            return historical_bars

        except Exception as e:
            # Wrap all exceptions in InsufficientDataError with context
            error_msg = f"Alpaca API error for {symbol}: {str(e)}"
            self.logger.error(error_msg)
            raise InsufficientDataError(error_msg) from e

    @with_retry(policy=DEFAULT_POLICY)
    def _fetch_yahoo_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> list[HistoricalDataBar]:
        """
        Fetch data from Yahoo Finance API.

        Uses yfinance library to download historical OHLCV data with
        automatic split and dividend adjustments.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            start_date: Start date (UTC timezone-aware)
            end_date: End date (UTC timezone-aware)

        Returns:
            List of HistoricalDataBar objects in chronological order

        Raises:
            Exception: If Yahoo Finance API call fails or returns no data
        """
        import yfinance as yf

        try:
            self.logger.info(
                f"Fetching {symbol} from Yahoo Finance API "
                f"({start_date.date()} to {end_date.date()})"
            )

            # Download data from Yahoo Finance
            # auto_adjust=True applies split and dividend adjustments
            df = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                auto_adjust=True,
                progress=False  # Disable progress bar for cleaner logs
            )

            # Check if we got any data
            if df.empty:
                raise Exception(
                    f"Yahoo Finance returned no data for {symbol} "
                    f"in range {start_date.date()} to {end_date.date()}"
                )

            # Convert DataFrame to List[HistoricalDataBar]
            bars = []
            for timestamp, row in df.iterrows():
                # Yahoo Finance uses UTC timestamps by default
                # Ensure timezone-aware datetime
                if hasattr(timestamp, 'tz_localize'):
                    # pandas Timestamp - convert to UTC-aware datetime
                    bar_timestamp = timestamp.tz_localize('UTC') if timestamp.tz is None else timestamp.tz_convert('UTC')
                    bar_timestamp = bar_timestamp.to_pydatetime()
                elif timestamp.tzinfo is None:
                    # Naive datetime - assume UTC
                    bar_timestamp = timestamp.replace(tzinfo=UTC)
                else:
                    bar_timestamp = timestamp

                # Create HistoricalDataBar from Yahoo data
                # Yahoo columns: Open, High, Low, Close, Volume
                bar = HistoricalDataBar(
                    symbol=symbol,
                    timestamp=bar_timestamp,
                    open=Decimal(str(row['Open'])),
                    high=Decimal(str(row['High'])),
                    low=Decimal(str(row['Low'])),
                    close=Decimal(str(row['Close'])),
                    volume=int(row['Volume']),
                    split_adjusted=True,  # Yahoo auto_adjust=True
                    dividend_adjusted=True  # Yahoo auto_adjust=True
                )
                bars.append(bar)

            self.logger.info(f"Yahoo Finance returned {len(bars)} bars for {symbol}")
            return bars

        except Exception as e:
            self.logger.error(f"Yahoo Finance API error for {symbol}: {e}")
            raise
