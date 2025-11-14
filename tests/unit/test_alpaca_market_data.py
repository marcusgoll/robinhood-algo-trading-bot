import pytest
from alpaca.data.timeframe import TimeFrame

from trading_bot.market_data.alpaca_market_data import AlpacaMarketData


def test_map_timeframe_valid_mappings():
    assert AlpacaMarketData._map_timeframe("1m") == TimeFrame.Minute
    assert AlpacaMarketData._map_timeframe("5m") == TimeFrame.FiveMinutes
    assert AlpacaMarketData._map_timeframe("1h") == TimeFrame.Hour
    assert AlpacaMarketData._map_timeframe("1d") == TimeFrame.Day
    assert AlpacaMarketData._map_timeframe("1w") == TimeFrame.Week


def test_map_timeframe_invalid():
    with pytest.raises(ValueError):
        AlpacaMarketData._map_timeframe("13h")
