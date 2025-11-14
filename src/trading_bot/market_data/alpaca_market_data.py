"""
Alpaca Market Data Helper

Lightweight wrapper around Alpaca's StockHistoricalDataClient for fetching
bars used by CLI commands and analysis tools.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from alpaca.data.enums import Adjustment
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from trading_bot.auth import AlpacaAuth

TimeframeStr = Literal["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]


class AlpacaMarketData:
    """Simple facade over Alpaca historical data client."""

    def __init__(self, auth: AlpacaAuth | None = None):
        self.auth = auth or AlpacaAuth(None)
        if not self.auth.is_authenticated():
            self.auth.login()
        self._client = self.auth.get_stock_data_client()

    def get_dataframe(self, *, symbol: str, timeframe: TimeframeStr, limit: int):
        """Fetch market data and return as pandas DataFrame sorted by timestamp."""
        import pandas as pd

        bars = self._fetch_bars(symbol=symbol, timeframe=timeframe, limit=limit)

        data = [
            {
                "timestamp": bar.timestamp,
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume),
            }
            for bar in bars
        ]

        df = pd.DataFrame(data)
        if not df.empty:
            df.sort_values("timestamp", inplace=True)
            df.reset_index(drop=True, inplace=True)
        return df

    def _fetch_bars(self, *, symbol: str, timeframe: TimeframeStr, limit: int):
        timeframe_enum = self._map_timeframe(timeframe)
        end = datetime.now(UTC)
        start = end - timedelta(days=max(limit // 2, 1))

        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=timeframe_enum,
            limit=limit,
            start=start,
            end=end,
            adjustment=Adjustment.ALL,
        )

        response = self._client.get_stock_bars(request)
        data = getattr(response, "data", None)
        if not data or symbol not in data:
            raise RuntimeError(f"Alpaca returned no bars for {symbol} ({timeframe})")
        return data[symbol]

    @staticmethod
    def _map_timeframe(timeframe: TimeframeStr) -> TimeFrame:
        mapping: dict[TimeframeStr, TimeFrame] = {
            "1m": TimeFrame.Minute,
            "5m": TimeFrame.FiveMinutes,
            "15m": TimeFrame.FifteenMinutes,
            "30m": TimeFrame.ThirtyMinutes,
            "1h": TimeFrame.Hour,
            "4h": TimeFrame.FourHours,
            "1d": TimeFrame.Day,
            "1w": TimeFrame.Week,
        }
        if timeframe not in mapping:
            raise ValueError(f"Unsupported timeframe '{timeframe}'")
        return mapping[timeframe]
