"""
Stock Screener Service

Core service for filtering stocks based on technical criteria:
- Price range (min/max bid price)
- Relative volume (vs 100-day average)
- Float size (public shares outstanding)
- Daily performance (percentage move)

Constitution v1.0.0:
- §Data_Integrity: All queries logged with audit trail
- §Safety_First: Fail-fast on validation errors, graceful degradation on missing data
- §Code_Quality: Type hints required, immutable dataclasses

Feature: stock-screener (001-stock-screener)
Tasks: T010-T020 [IN PROGRESS] - Core ScreenerService implementation
Spec: specs/001-stock-screener/spec.md (FR-001 to FR-012)
"""

import time
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal

import robin_stocks.robinhood as r

from trading_bot.error_handling.policies import DEFAULT_POLICY
from trading_bot.error_handling.retry import with_retry
from trading_bot.logging.screener_logger import ScreenerLogger
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.schemas.screener_schemas import (
    PageInfo,
    ScreenerQuery,
    ScreenerResult,
    StockScreenerMatch,
)
from trading_bot.screener_config import ScreenerConfig


class ScreenerService:
    """
    Stock screener service for filtering stocks by technical criteria.

    Features:
    - Price range filter (min/max bid price)
    - Relative volume filter (vs 100-day average)
    - Float size filter (public shares outstanding)
    - Daily performance filter (percentage move)
    - Pagination support (limit/offset)
    - Audit logging (JSONL)

    Example:
        >>> service = ScreenerService(market_data_service, logger, config)
        >>> query = ScreenerQuery(min_price=Decimal("2.0"), max_price=Decimal("20.0"))
        >>> result = service.filter(query, symbols=["TSLA", "AAPL", "MSFT"])
        >>> print(f"Found {result.result_count} stocks")
    """

    def __init__(
        self,
        market_data_service: MarketDataService,
        logger: ScreenerLogger,
        config: ScreenerConfig,
    ) -> None:
        """
        Initialize ScreenerService.

        Args:
            market_data_service: MarketDataService instance for quote fetching
            logger: ScreenerLogger instance for audit trail
            config: ScreenerConfig instance with service configuration
        """
        self.market_data_service = market_data_service
        self.logger = logger
        self.config = config

    @with_retry(policy=DEFAULT_POLICY)
    def filter(
        self, query: ScreenerQuery, symbols: list[str]
    ) -> ScreenerResult:
        """
        Filter stocks based on query criteria.

        Applies filters sequentially (AND logic):
        1. Price range filter (if min_price or max_price set)
        2. Relative volume filter (if relative_volume set)
        3. Float size filter (if float_max set)
        4. Daily performance filter (if min_daily_change set)

        Results sorted by volume descending (highest first).

        Args:
            query: ScreenerQuery with filter parameters
            symbols: List of stock symbols to screen

        Returns:
            ScreenerResult with matched stocks and metadata

        Raises:
            ValueError: If query validation fails

        Example:
            >>> query = ScreenerQuery(min_price=Decimal("2.0"), relative_volume=5.0)
            >>> result = service.filter(query, symbols=["TSLA", "AAPL"])
            >>> print(result.result_count)  # Number of matches
        """
        start_time = time.perf_counter()
        query_id = query.query_id

        # Track API calls
        api_calls = 0

        # Fetch quotes for all symbols
        quotes_data = []
        for symbol in symbols:
            try:
                # Fetch quote data from robin_stocks (detailed quote)
                quote_list = r.get_quotes(symbol)
                if quote_list and len(quote_list) > 0:
                    quote_data = quote_list[0]

                    # Extract required fields
                    bid_price = float(quote_data.get("bid_price", 0))
                    if bid_price > 0:  # Only include valid quotes
                        quotes_data.append({
                            "symbol": symbol,
                            "bid_price": Decimal(str(bid_price)),
                            "ask_price": Decimal(str(float(quote_data.get("ask_price", 0)))),
                            "last_trade_price": Decimal(str(float(quote_data.get("last_trade_price", 0)))),
                            "previous_close": Decimal(str(float(quote_data.get("previous_close", 0)))),
                        })
                        api_calls += 1
            except Exception as e:
                # Log data gap but continue
                self.logger.log_data_gap(
                    symbol=symbol,
                    field="quote",
                    reason=f"Failed to fetch quote: {str(e)}"
                )

        # Get historical data for volume and float information (batch call)
        # For MVP, we'll fetch fundamentals separately
        stocks = []
        for quote_data in quotes_data:
            symbol = quote_data["symbol"]

            try:
                # Fetch fundamentals for volume and float data
                fundamentals = r.get_fundamentals(symbol)
                if fundamentals and len(fundamentals) > 0:
                    fund = fundamentals[0]

                    # Extract volume data
                    volume = int(fund.get("volume", 0))
                    volume_avg = fund.get("average_volume")  # Can be None

                    # Extract float data
                    float_shares_str = fund.get("float")
                    float_shares = int(float(float_shares_str)) if float_shares_str else None

                    # Calculate daily change
                    current_price = quote_data["last_trade_price"]
                    previous_close = quote_data["previous_close"]

                    if previous_close > 0:
                        daily_change_pct = float(abs((current_price - previous_close) / previous_close * 100))
                        daily_change_pct = min(daily_change_pct, 1000)  # Cap at 1000%

                        daily_change_direction = "up" if current_price >= previous_close else "down"
                    else:
                        daily_change_pct = 0.0
                        daily_change_direction = "up"

                    # Build stock data structure
                    stock_data = {
                        "symbol": symbol,
                        "bid_price": quote_data["bid_price"],
                        "volume": volume,
                        "volume_avg_100d": int(float(volume_avg)) if volume_avg else None,
                        "float_shares": float_shares,
                        "daily_open": previous_close,  # Approximation for MVP
                        "daily_close": current_price,
                        "daily_change_pct": daily_change_pct,
                        "daily_change_direction": daily_change_direction,
                    }

                    stocks.append(stock_data)
                    api_calls += 1

            except Exception as e:
                # Log data gap but continue
                self.logger.log_data_gap(
                    symbol=symbol,
                    field="fundamentals",
                    reason=f"Failed to fetch fundamentals: {str(e)}"
                )

        # Apply filters sequentially (AND logic)
        matched_filters_map = {}  # Track which filters each stock passed

        # Initialize matched filters for all stocks
        for stock in stocks:
            matched_filters_map[stock["symbol"]] = []

        # Apply price filter
        if query.min_price is not None or query.max_price is not None:
            stocks = self._apply_price_filter(stocks, query.min_price, query.max_price)
            for stock in stocks:
                matched_filters_map[stock["symbol"]].append("price_range")

        # Apply volume filter
        if query.relative_volume is not None:
            stocks = self._apply_volume_filter(stocks, query.relative_volume)
            for stock in stocks:
                matched_filters_map[stock["symbol"]].append("relative_volume")

        # Apply float filter
        if query.float_max is not None:
            stocks = self._apply_float_filter(stocks, query.float_max)
            for stock in stocks:
                matched_filters_map[stock["symbol"]].append("float_size")

        # Apply daily change filter
        if query.min_daily_change is not None:
            stocks = self._apply_daily_change_filter(stocks, query.min_daily_change)
            for stock in stocks:
                matched_filters_map[stock["symbol"]].append("daily_movers")

        # Sort by volume descending
        stocks.sort(key=lambda s: s["volume"], reverse=True)

        # Total count before pagination
        total_count = len(stocks)

        # Paginate results
        paginated_stocks, page_info = self._paginate_results(
            stocks, query.offset, query.limit
        )

        # Build StockScreenerMatch objects
        matched_stocks = []
        for stock_data in paginated_stocks:
            symbol = stock_data["symbol"]

            # Check for data gaps
            data_gaps = []
            if stock_data["volume_avg_100d"] is None:
                data_gaps.append("volume_avg_100d")
            if stock_data["float_shares"] is None:
                data_gaps.append("float_shares")

            matched_stock = StockScreenerMatch(
                symbol=symbol,
                bid_price=stock_data["bid_price"],
                volume=stock_data["volume"],
                daily_open=stock_data["daily_open"],
                daily_close=stock_data["daily_close"],
                daily_change_pct=stock_data["daily_change_pct"],
                matched_filters=matched_filters_map.get(symbol, []),
                volume_avg_100d=stock_data["volume_avg_100d"],
                float_shares=stock_data["float_shares"],
                daily_change_direction=stock_data["daily_change_direction"],
                data_gaps=data_gaps,
            )
            matched_stocks.append(matched_stock)

        # Calculate execution time (use perf_counter for microsecond precision)
        execution_time_ms = (time.perf_counter() - start_time) * 1000

        # Build result
        result = ScreenerResult(
            query_id=query_id,
            stocks=matched_stocks,
            query_timestamp=datetime.utcnow().isoformat() + "Z",
            result_count=len(matched_stocks),
            total_count=total_count,
            execution_time_ms=execution_time_ms,
            page_info=page_info,
            errors=[],
            api_calls_made=api_calls,
            cache_hit=False,
        )

        # Log query (convert Decimal to string for JSON serialization)
        query_params_dict = asdict(query)
        # Convert Decimal fields to strings
        if query_params_dict.get("min_price") is not None:
            query_params_dict["min_price"] = str(query_params_dict["min_price"])
        if query_params_dict.get("max_price") is not None:
            query_params_dict["max_price"] = str(query_params_dict["max_price"])

        self.logger.log_query(
            query_id=query_id,
            query_params=query_params_dict,
            result_count=result.result_count,
            total_count=result.total_count,
            execution_time_ms=execution_time_ms,
            api_calls=api_calls,
            errors=result.errors,
        )

        return result

    def _apply_price_filter(
        self,
        stocks: list[dict],
        min_price: Decimal | None,
        max_price: Decimal | None,
    ) -> list[dict]:
        """
        Filter stocks by price range.

        Args:
            stocks: List of stock data dictionaries
            min_price: Minimum bid price (None to skip)
            max_price: Maximum bid price (None to skip)

        Returns:
            Filtered list of stocks within price range
        """
        if min_price is None and max_price is None:
            return stocks

        filtered = []
        for stock in stocks:
            bid_price = stock["bid_price"]

            # Check min price
            if min_price is not None and bid_price < min_price:
                continue

            # Check max price
            if max_price is not None and bid_price > max_price:
                continue

            filtered.append(stock)

        return filtered

    def _apply_volume_filter(
        self, stocks: list[dict], relative_volume: float
    ) -> list[dict]:
        """
        Filter stocks by relative volume (vs 100-day average).

        Args:
            stocks: List of stock data dictionaries
            relative_volume: Volume multiplier threshold (e.g., 5.0 = 5x average)

        Returns:
            Filtered list of stocks meeting volume criteria
        """
        filtered = []
        for stock in stocks:
            volume = stock["volume"]
            volume_avg = stock["volume_avg_100d"]

            # Use default 1M baseline for IPOs or missing data
            if volume_avg is None:
                volume_avg = 1_000_000
                self.logger.log_data_gap(
                    stock["symbol"],
                    "volume_avg_100d",
                    "Using 1M default for missing 100d average"
                )

            # Check if volume meets threshold
            if volume >= (volume_avg * relative_volume):
                filtered.append(stock)

        return filtered

    def _apply_float_filter(
        self, stocks: list[dict], float_max: int
    ) -> list[dict]:
        """
        Filter stocks by maximum float size.

        Args:
            stocks: List of stock data dictionaries
            float_max: Maximum float in millions (e.g., 20 = under 20M shares)

        Returns:
            Filtered list of stocks with float under threshold
        """
        filtered = []
        float_max_shares = float_max * 1_000_000  # Convert millions to shares

        for stock in stocks:
            float_shares = stock["float_shares"]

            # If float data missing, include with data gap logged (graceful degradation)
            if float_shares is None:
                self.logger.log_data_gap(
                    stock["symbol"],
                    "float_shares",
                    "Float data unavailable, including in results"
                )
                filtered.append(stock)
                continue

            # Check if float is under threshold
            if float_shares < float_max_shares:
                filtered.append(stock)

        return filtered

    def _apply_daily_change_filter(
        self, stocks: list[dict], min_daily_change: float
    ) -> list[dict]:
        """
        Filter stocks by minimum daily percentage change.

        Args:
            stocks: List of stock data dictionaries
            min_daily_change: Minimum daily change percent (e.g., 10.0 = ±10%)

        Returns:
            Filtered list of stocks meeting daily change criteria
        """
        filtered = []
        for stock in stocks:
            daily_change_pct = stock["daily_change_pct"]

            # Check if change meets threshold
            if daily_change_pct >= min_daily_change:
                filtered.append(stock)

        return filtered

    def _paginate_results(
        self, stocks: list[dict], offset: int, limit: int
    ) -> tuple[list[dict], PageInfo]:
        """
        Paginate stock results.

        Args:
            stocks: List of stock data dictionaries
            offset: Starting index
            limit: Maximum results per page

        Returns:
            Tuple of (paginated stocks, PageInfo metadata)
        """
        total = len(stocks)
        paginated = stocks[offset : offset + limit]

        has_more = (offset + limit) < total
        next_offset = (offset + limit) if has_more else None
        page_number = (offset // limit) + 1

        page_info = PageInfo(
            offset=offset,
            limit=limit,
            has_more=has_more,
            next_offset=next_offset,
            page_number=page_number,
        )

        return paginated, page_info
