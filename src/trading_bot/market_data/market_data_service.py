"""
Market Data Service

Provides real-time and historical market data backed by the Alpaca Market Data API.

Constitution v1.0.0:
- §Data_Integrity: All market data validated before use
- §Audit_Everything: All API calls logged
- §Safety_First: Fail-fast on validation errors
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Dict, List

import pandas as pd

from trading_bot.auth import AlpacaAuth
from trading_bot.error_handling.policies import DEFAULT_POLICY
from trading_bot.error_handling.retry import with_retry
from trading_bot.logger import TradingLogger
from trading_bot.market_data.alpaca_market_data import AlpacaMarketData
from trading_bot.market_data.data_models import MarketDataConfig, MarketStatus, Quote
from trading_bot.market_data.validators import (
    validate_historical_data,
    validate_quote,
    validate_trade_time,
)


class MarketDataService:
    """Alpaca-backed market data service."""

    TIMEFRAME_ALIAS = {
        "1min": "1m",
        "5min": "5m",
        "10minute": "5m",
        "15min": "15m",
        "1hr": "1h",
        "4hr": "4h",
        "1day": "1d",
        "daily": "1d",
        "day": "1d",
        "1week": "1w",
        "weekly": "1w",
        "week": "1w",
    }

    SPAN_DEFAULT_BARS = {
        "day": 90,
        "week": 390,
        "month": 1000,
        "3month": 2000,
        "year": 2500,
        "5year": 10000,
    }

    def __init__(
        self,
        auth: AlpacaAuth,
        config: MarketDataConfig | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.auth = auth
        self.config = config if config is not None else MarketDataConfig()
        self.logger = logger if logger is not None else TradingLogger.get_logger(__name__)
        self._data_helper = AlpacaMarketData(auth)
        self._trading_client = auth.get_trading_client()

    # ------------------------------------------------------------------
    # Quotes
    # ------------------------------------------------------------------
    @with_retry(policy=DEFAULT_POLICY)
    def get_quote(self, symbol: str) -> Quote:
        validate_trade_time()
        self._log_request("get_quote", {"symbol": symbol})

        df = self._data_helper.get_dataframe(symbol=symbol, timeframe="1m", limit=1)
        if df.empty:
            raise ValueError(f"No quote data returned for {symbol}")

        row = df.iloc[-1]
        timestamp = row["timestamp"]
        if hasattr(timestamp, "to_pydatetime"):
            timestamp = timestamp.to_pydatetime()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        quote_data = {
            "symbol": symbol,
            "price": float(row["close"]),
            "timestamp": timestamp,
            "market_state": self._determine_market_state(),
        }
        validate_quote(quote_data)

        return Quote(
            symbol=symbol,
            current_price=Decimal(str(row["close"])),
            timestamp_utc=timestamp,
            market_state=quote_data["market_state"],
        )

    # ------------------------------------------------------------------
    # Historical data
    # ------------------------------------------------------------------
    @with_retry(policy=DEFAULT_POLICY)
    def get_historical_data(
        self,
        symbol: str,
        interval: str = "day",
        span: str = "3month",
    ) -> pd.DataFrame:
        timeframe = self._map_timeframe(interval)
        limit = self._span_to_limit(span)
        self._log_request("get_historical_data", {"symbol": symbol, "interval": interval, "span": span})

        df = self._data_helper.get_dataframe(symbol=symbol, timeframe=timeframe, limit=limit)
        df = self._prepare_ohlcv_dataframe(df)
        validate_historical_data(df)
        return df

    @with_retry(policy=DEFAULT_POLICY)
    def get_multi_timeframe_data(
        self,
        symbol: str,
        timeframes: List[str],
        span: str = "year",
    ) -> Dict[str, pd.DataFrame]:
        self._log_request(
            "get_multi_timeframe_data",
            {"symbol": symbol, "timeframes": timeframes, "span": span},
        )

        data: Dict[str, pd.DataFrame] = {}
        for tf in timeframes:
            timeframe = self._map_timeframe(tf)
            limit = self._span_to_limit(span)
            df = self._data_helper.get_dataframe(symbol=symbol, timeframe=timeframe, limit=limit)
            tf_df = self._prepare_ohlcv_dataframe(df)
            validate_historical_data(tf_df)
            data[tf] = tf_df

        return data

    # ------------------------------------------------------------------
    # Market status
    # ------------------------------------------------------------------
    @with_retry(policy=DEFAULT_POLICY)
    def is_market_open(self) -> MarketStatus:
        clock = self._trading_client.get_clock()
        next_open = clock.next_open.replace(tzinfo=UTC) if clock.next_open.tzinfo is None else clock.next_open.astimezone(UTC)
        next_close = clock.next_close.replace(tzinfo=UTC) if clock.next_close.tzinfo is None else clock.next_close.astimezone(UTC)

        return MarketStatus(
            is_open=clock.is_open,
            next_open=next_open,
            next_close=next_close,
        )

    def get_quotes_batch(self, symbols: list[str]) -> dict[str, Quote]:
        self._log_request("get_quotes_batch", {"symbols": symbols, "count": len(symbols)})
        quotes: dict[str, Quote] = {}
        for symbol in symbols:
            try:
                quotes[symbol] = self.get_quote(symbol)
            except Exception as exc:
                self.logger.warning(f"Failed to get quote for {symbol}: {exc}")
        return quotes

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _prepare_ohlcv_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        if "timestamp" in result.columns:
            result["date"] = pd.to_datetime(result["timestamp"], utc=True)
            result = result.drop(columns=["timestamp"])
        result = result.rename(columns=str.lower)
        columns = ["date", "open", "high", "low", "close", "volume"]
        return result[columns]

    def _map_timeframe(self, key: str) -> str:
        if key not in self.TIMEFRAME_ALIAS:
            raise ValueError(
                f"Unsupported timeframe '{key}'. Supported: {sorted(self.TIMEFRAME_ALIAS.keys())}"
            )
        return self.TIMEFRAME_ALIAS[key]

    def _span_to_limit(self, span: str) -> int:
        return self.SPAN_DEFAULT_BARS.get(span, 1000)

    def _determine_market_state(self) -> str:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(self.config.trading_timezone)
        now_est = datetime.now(tz)
        weekday = now_est.weekday()
        hour = now_est.hour + now_est.minute / 60

        if weekday >= 5:
            return "closed"
        if 4 <= hour < 9.5:
            return "pre"
        if 9.5 <= hour < 16:
            return "regular"
        if 16 <= hour < 20:
            return "post"
        return "closed"

    def _log_request(self, endpoint: str, params: dict) -> None:
        self.logger.info(
            "market_data.request",
            extra={
                "event": "market_data.request",
                "endpoint": endpoint,
                "params": params,
            },
        )
