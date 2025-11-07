"""
Market Data Service

Main service class for retrieving real-time and historical market data
from Robinhood API with validation and error handling.

Constitution v1.0.0:
- §Data_Integrity: All market data validated before use
- §Audit_Everything: All API calls logged
- §Safety_First: Fail-fast on validation errors
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Dict, List

import pandas as pd
import robin_stocks.robinhood as r

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.error_handling.policies import DEFAULT_POLICY
from trading_bot.error_handling.retry import with_retry
from trading_bot.logger import TradingLogger
from trading_bot.market_data.data_models import MarketDataConfig, MarketStatus, Quote
from trading_bot.market_data.validators import (
    validate_historical_data,
    validate_quote,
    validate_trade_time,
)


class MarketDataService:
    """
    Market data service for fetching and validating stock market data.

    Handles real-time quotes, historical data, and market status with
    built-in validation and error handling.
    """

    # Mapping from standard timeframe notation to Robinhood API intervals
    # Robinhood supports: 5minute, 10minute, day, week
    TIMEFRAME_TO_INTERVAL = {
        "1min": "5minute",    # Robinhood doesn't support 1min, use 5min as closest
        "5min": "5minute",
        "15min": "5minute",   # Will need resampling from 5min to 15min
        "1hr": "5minute",     # Will need resampling from 5min to 1hr
        "4hr": "5minute",     # Will need resampling from 5min to 4hr
        "1day": "day",
        "daily": "day",
        "1week": "week",
        "weekly": "week"
    }

    # Resampling rules for timeframes that need aggregation
    RESAMPLE_FREQ = {
        "1min": None,         # Not supported
        "5min": None,         # Native
        "15min": "15T",       # Resample from 5min
        "1hr": "1H",          # Resample from 5min
        "4hr": "4H",          # Resample from 5min
        "1day": None,         # Native
        "daily": None,        # Native
        "1week": None,        # Native
        "weekly": None        # Native
    }

    def __init__(
        self,
        auth: RobinhoodAuth,
        config: MarketDataConfig | None = None,
        logger: logging.Logger | None = None
    ) -> None:
        """
        Initialize MarketDataService.

        Args:
            auth: Authenticated RobinhoodAuth instance
            config: Optional MarketDataConfig (uses defaults if not provided)
            logger: Optional custom logger (uses TradingLogger if not provided)
        """
        self.auth = auth
        self.config = config if config is not None else MarketDataConfig()
        self.logger = logger if logger is not None else TradingLogger.get_logger(__name__)

    @with_retry(policy=DEFAULT_POLICY)
    def get_quote(self, symbol: str) -> Quote:
        """
        Get real-time stock quote for a symbol.

        T033: Fetches latest price from robin_stocks, validates with validate_quote,
        and returns Quote dataclass.
        T035: Added @with_retry decorator for automatic retry on rate limits.
        T045-T051: Added trading hours validation.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "TSLA")

        Returns:
            Quote: Validated Quote dataclass with current price and timestamp

        Raises:
            DataValidationError: If price is invalid or timestamp is stale
            RateLimitError: After 3 retries on HTTP 429
            TradingHoursError: If called outside trading hours (7am-10am EST)
        """
        # T045-T051: Validate trading hours before fetching quote
        validate_trade_time()

        # Log the request (T044)
        self._log_request("get_quote", {"symbol": symbol})

        # Fetch latest price from robin_stocks
        price_list = r.get_latest_price(symbol, includeExtendedHours=True)

        # Extract price (robin_stocks returns list with single string)
        price_str = price_list[0]
        price = float(price_str)

        # Get current timestamp in UTC
        timestamp_utc = datetime.now(UTC)

        # Determine market state based on current time
        market_state = self._determine_market_state()

        # Build quote data dict for validation
        quote_data = {
            'symbol': symbol,
            'price': price,
            'timestamp': timestamp_utc,
            'market_state': market_state
        }

        # Validate quote data (raises DataValidationError if invalid)
        validate_quote(quote_data)

        # Return validated Quote dataclass
        return Quote(
            symbol=symbol,
            current_price=Decimal(str(price)),  # Convert to Decimal for precision
            timestamp_utc=timestamp_utc,
            market_state=market_state
        )

    @with_retry(policy=DEFAULT_POLICY)
    def get_historical_data(
        self,
        symbol: str,
        interval: str = "day",
        span: str = "3month"
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data for a symbol.

        T036-T038: Fetches historical data from robin_stocks, normalizes column names,
        validates with validate_historical_data, and returns DataFrame.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "TSLA")
            interval: Data interval ("day", "week", "10minute", "5minute")
            span: Time span ("day", "week", "month", "3month", "year", "5year")

        Returns:
            DataFrame with columns: date, open, high, low, close, volume

        Raises:
            DataValidationError: If historical data is invalid or incomplete
            RateLimitError: After 3 retries on HTTP 429
        """
        # Log the request (T044)
        self._log_request("get_historical_data", {"symbol": symbol, "interval": interval, "span": span})

        # Fetch historical data from robin_stocks
        data = r.get_stock_historicals(symbol, interval=interval, span=span)

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Normalize column names to standard OHLCV format
        df = df.rename(columns={
            'begins_at': 'date',
            'open_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'close_price': 'close',
            'volume': 'volume'
        })

        # Validate historical data (raises DataValidationError if invalid)
        validate_historical_data(df)

        return df

    @with_retry(policy=DEFAULT_POLICY)
    def get_multi_timeframe_data(
        self,
        symbol: str,
        timeframes: List[str],
        span: str = "year"
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical data across multiple timeframes.

        Handles timeframe mapping, data resampling where needed, and validation
        for all requested timeframes. Used for multi-timeframe ML models.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "TSLA")
            timeframes: List of timeframes (e.g., ["5min", "1hr", "1day"])
                       Supported: 1min, 5min, 15min, 1hr, 4hr, 1day, daily, 1week, weekly
            span: Time span for all timeframes ("day", "week", "month", "year", "5year")

        Returns:
            Dict mapping timeframe -> OHLCV DataFrame
            Example: {"5min": df_5min, "1hr": df_1hr, "1day": df_daily}

        Raises:
            ValueError: If unsupported timeframe requested
            DataValidationError: If data validation fails for any timeframe
            RateLimitError: After 3 retries on HTTP 429

        Example:
            >>> data = service.get_multi_timeframe_data(
            ...     "SPY",
            ...     ["5min", "1hr", "1day"],
            ...     span="year"
            ... )
            >>> print(data["1day"].head())
        """
        # Log the request
        self._log_request(
            "get_multi_timeframe_data",
            {"symbol": symbol, "timeframes": timeframes, "span": span}
        )

        # Validate requested timeframes
        unsupported = [tf for tf in timeframes if tf not in self.TIMEFRAME_TO_INTERVAL]
        if unsupported:
            raise ValueError(
                f"Unsupported timeframes: {unsupported}. "
                f"Supported: {list(self.TIMEFRAME_TO_INTERVAL.keys())}"
            )

        data_by_timeframe = {}

        # Group timeframes by required API interval to minimize API calls
        interval_to_timeframes = {}
        for tf in timeframes:
            interval = self.TIMEFRAME_TO_INTERVAL[tf]
            if interval not in interval_to_timeframes:
                interval_to_timeframes[interval] = []
            interval_to_timeframes[interval].append(tf)

        # Fetch data for each unique interval
        for interval, tfs in interval_to_timeframes.items():
            try:
                # Fetch raw data from Robinhood
                self.logger.info(f"Fetching {interval} data for {symbol} (span={span})")
                raw_data = r.get_stock_historicals(symbol, interval=interval, span=span)

                # Convert to DataFrame
                df = pd.DataFrame(raw_data)

                # Normalize column names
                df = df.rename(columns={
                    'begins_at': 'date',
                    'open_price': 'open',
                    'high_price': 'high',
                    'low_price': 'low',
                    'close_price': 'close',
                    'volume': 'volume'
                })

                # Convert date to datetime and set as index
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')

                # Convert price/volume columns to numeric
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                # Process each timeframe that needs this interval
                for tf in tfs:
                    resample_freq = self.RESAMPLE_FREQ.get(tf)

                    if resample_freq is None:
                        # No resampling needed (native timeframe)
                        tf_df = df.copy()
                    else:
                        # Resample to target timeframe
                        self.logger.info(f"Resampling {interval} → {tf} using {resample_freq}")
                        tf_df = df.resample(resample_freq).agg({
                            'open': 'first',
                            'high': 'max',
                            'low': 'min',
                            'close': 'last',
                            'volume': 'sum'
                        })

                        # Drop rows with NaN (incomplete bars)
                        tf_df = tf_df.dropna()

                    # Reset index to have 'date' as column (for compatibility)
                    tf_df = tf_df.reset_index()

                    # Validate the data
                    validate_historical_data(tf_df)

                    # Store in result dict
                    data_by_timeframe[tf] = tf_df

                    self.logger.info(
                        f"Loaded {len(tf_df)} bars for {symbol} {tf} "
                        f"({tf_df['date'].iloc[0]} to {tf_df['date'].iloc[-1]})"
                    )

            except Exception as e:
                self.logger.error(
                    f"Failed to fetch {interval} data for timeframes {tfs}: {e}"
                )
                # Mark all dependent timeframes as failed
                for tf in tfs:
                    data_by_timeframe[tf] = pd.DataFrame()  # Empty DataFrame as error indicator

        # Verify all timeframes were successfully fetched
        failed_tfs = [tf for tf, df in data_by_timeframe.items() if df.empty]
        if failed_tfs:
            raise ValueError(
                f"Failed to fetch data for timeframes: {failed_tfs}. "
                f"Check API connectivity and rate limits."
            )

        return data_by_timeframe

    @with_retry(policy=DEFAULT_POLICY)
    def is_market_open(self) -> MarketStatus:
        """
        Check if market is currently open.

        T039-T041: Fetches market hours from robin_stocks and returns MarketStatus.

        Returns:
            MarketStatus with is_open, next_open, and next_close times

        Raises:
            RateLimitError: After 3 retries on HTTP 429
        """
        # Log the request (T044)
        self._log_request("is_market_open", {"date": datetime.now().strftime('%Y-%m-%d')})

        # Fetch market hours for NYSE (representative of US stock market)
        market_hours = r.get_market_hours('XNYS', datetime.now().strftime('%Y-%m-%d'))

        # Parse market status
        is_open = market_hours.get('is_open', False)
        next_open = datetime.fromisoformat(market_hours['next_open_hours'])
        next_close = datetime.fromisoformat(market_hours['next_close_hours'])

        return MarketStatus(
            is_open=is_open,
            next_open=next_open,
            next_close=next_close
        )

    def get_quotes_batch(self, symbols: list[str]) -> dict[str, Quote]:
        """
        Get quotes for multiple symbols.

        T042-T043: Fetches quotes for a list of symbols, continues on individual failures.

        Args:
            symbols: List of stock ticker symbols

        Returns:
            Dictionary mapping symbols to Quote objects (excludes failed symbols)
        """
        # Log the request (T044)
        self._log_request("get_quotes_batch", {"symbols": symbols, "count": len(symbols)})

        quotes = {}
        for symbol in symbols:
            try:
                quotes[symbol] = self.get_quote(symbol)
            except Exception as e:
                self.logger.warning(f"Failed to get quote for {symbol}: {e}")

        return quotes

    def _determine_market_state(self) -> str:
        """
        Determine current market state based on time.

        Returns market state as one of: "pre", "regular", "post", "closed"
        based on current time in EST timezone.

        Market states:
        - "pre": Pre-market (4am-9:30am EST, weekdays)
        - "regular": Regular hours (9:30am-4pm EST, weekdays)
        - "post": After-hours (4pm-8pm EST, weekdays)
        - "closed": Market closed (weekends, late night/early morning)

        Returns:
            str: Market state ("pre", "regular", "post", or "closed")
        """
        from zoneinfo import ZoneInfo

        # Get current time in EST
        est_tz = ZoneInfo("America/New_York")
        now_est = datetime.now(UTC).astimezone(est_tz)

        # Check if weekend
        if now_est.weekday() >= 5:  # Saturday=5, Sunday=6
            return "closed"

        # Get hour and minute
        hour = now_est.hour
        minute = now_est.minute

        # Determine market state based on time
        if hour < 4 or hour >= 20:  # Before 4am or after 8pm
            return "closed"
        elif hour < 9 or (hour == 9 and minute < 30):  # 4am-9:30am
            return "pre"
        elif hour < 16:  # 9:30am-4pm
            return "regular"
        elif hour < 20:  # 4pm-8pm
            return "post"
        else:
            return "closed"

    def _log_request(self, method: str, params: dict) -> None:
        """
        Log API request with method name and parameters.

        T044: Helper for standardized API request logging.

        Args:
            method: API method name (e.g., "get_quote", "get_historical_data")
            params: Request parameters dictionary
        """
        self.logger.info(f"API Request: {method}", extra={'params': params})
