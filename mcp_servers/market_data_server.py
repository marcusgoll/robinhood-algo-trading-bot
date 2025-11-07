#!/usr/bin/env python3
"""
Market Data MCP Server

Exposes market data from trading_bot to Claude Code via Model Context Protocol.

Tools provided:
- get_quote: Get realtime quote for a symbol
- get_historical: Get historical price data
- get_market_status: Check if market is open
- calculate_indicators: Calculate technical indicators (RSI, MACD, etc.)
- scan_momentum: Scan for high-momentum stocks

Usage:
    python mcp_servers/market_data_server.py
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Add src to path for trading_bot imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    import mcp.server.stdio
except ImportError:
    print("ERROR: mcp package not installed. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.market_data import MarketDataService, Quote
from trading_bot.indicators import IndicatorService
from trading_bot.momentum.premarket_scanner import PremarketScanner
from trading_bot.config import Config

# Initialize server
server = Server("market-data")

# Global state
_market_data_service: Optional[MarketDataService] = None
_indicator_service: Optional[IndicatorService] = None
_scanner: Optional[PremarketScanner] = None


async def initialize_services():
    """Initialize trading_bot services"""
    global _market_data_service, _indicator_service, _scanner

    try:
        # Load config
        config = Config.from_env_and_json()

        # Auth
        auth = RobinhoodAuth(config)
        auth.login()

        # Initialize services
        _market_data_service = MarketDataService(auth)
        _indicator_service = IndicatorService(_market_data_service)
        _scanner = PremarketScanner(_market_data_service)

        print("Market data services initialized", file=sys.stderr)
    except Exception as e:
        print(f"ERROR initializing services: {e}", file=sys.stderr)
        raise


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available market data tools"""
    return [
        Tool(
            name="get_quote",
            description="Get realtime quote for a stock symbol",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, TSLA)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="get_historical",
            description="Get historical price data for backtesting and analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days of historical data (default: 30)",
                        "default": 30
                    },
                    "interval": {
                        "type": "string",
                        "description": "Data interval: 1min, 5min, 15min, 1hour, 1day",
                        "enum": ["1min", "5min", "15min", "1hour", "1day"],
                        "default": "1day"
                    }
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="get_market_status",
            description="Check if market is currently open for trading",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="calculate_indicators",
            description="Calculate technical indicators (RSI, MACD, ATR, etc.) for a symbol",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol"
                    },
                    "indicators": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["rsi", "macd", "atr", "sma_20", "sma_50", "ema_12", "ema_26", "bbands"]
                        },
                        "description": "List of indicators to calculate",
                        "default": ["rsi", "macd", "atr"]
                    }
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="scan_momentum",
            description="Scan for high-momentum stocks suitable for day trading",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_volume": {
                        "type": "integer",
                        "description": "Minimum volume threshold",
                        "default": 1000000
                    },
                    "min_price": {
                        "type": "number",
                        "description": "Minimum price per share",
                        "default": 5.0
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price per share",
                        "default": 500.0
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "get_quote":
            return await get_quote_tool(arguments)
        elif name == "get_historical":
            return await get_historical_tool(arguments)
        elif name == "get_market_status":
            return await get_market_status_tool(arguments)
        elif name == "calculate_indicators":
            return await calculate_indicators_tool(arguments)
        elif name == "scan_momentum":
            return await scan_momentum_tool(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        print(error_msg, file=sys.stderr)
        return [TextContent(type="text", text=error_msg)]


async def get_quote_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Get realtime quote"""
    symbol = args["symbol"].upper()

    if _market_data_service is None:
        return [TextContent(type="text", text="ERROR: Market data service not initialized")]

    quote = _market_data_service.get_quote(symbol)

    result = {
        "symbol": quote.symbol,
        "price": float(quote.current_price),
        "change": float(quote.price_change),
        "change_pct": float(quote.price_change_percent),
        "volume": int(quote.volume),
        "timestamp": quote.timestamp.isoformat() if quote.timestamp else None
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_historical_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Get historical price data"""
    symbol = args["symbol"].upper()
    days = args.get("days", 30)
    interval = args.get("interval", "1day")

    if _market_data_service is None:
        return [TextContent(type="text", text="ERROR: Market data service not initialized")]

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Get historical data via trading_bot
    historical = _market_data_service.get_historical_data(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        interval=interval
    )

    # Format as JSON
    result = {
        "symbol": symbol,
        "interval": interval,
        "days": days,
        "data_points": len(historical),
        "data": [
            {
                "timestamp": bar.timestamp.isoformat(),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume)
            }
            for bar in historical[:50]  # Limit to 50 bars for readability
        ]
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_market_status_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Check market status"""
    if _market_data_service is None:
        return [TextContent(type="text", text="ERROR: Market data service not initialized")]

    status = _market_data_service.get_market_status()

    result = {
        "is_open": status.is_open,
        "is_extended_hours": status.is_extended_hours,
        "next_open": status.next_open.isoformat() if status.next_open else None,
        "next_close": status.next_close.isoformat() if status.next_close else None,
        "timestamp": datetime.now().isoformat()
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def calculate_indicators_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Calculate technical indicators"""
    symbol = args["symbol"].upper()
    indicators = args.get("indicators", ["rsi", "macd", "atr"])

    if _indicator_service is None:
        return [TextContent(type="text", text="ERROR: Indicator service not initialized")]

    # Calculate each requested indicator
    result = {
        "symbol": symbol,
        "indicators": {}
    }

    for indicator in indicators:
        try:
            if indicator == "rsi":
                value = _indicator_service.calculate_rsi(symbol, period=14)
                result["indicators"]["rsi_14"] = float(value)
            elif indicator == "macd":
                macd_line, signal_line, histogram = _indicator_service.calculate_macd(symbol)
                result["indicators"]["macd"] = {
                    "macd_line": float(macd_line),
                    "signal_line": float(signal_line),
                    "histogram": float(histogram)
                }
            elif indicator == "atr":
                value = _indicator_service.calculate_atr(symbol, period=14)
                result["indicators"]["atr_14"] = float(value)
            elif indicator.startswith("sma"):
                period = int(indicator.split("_")[1])
                value = _indicator_service.calculate_sma(symbol, period=period)
                result["indicators"][f"sma_{period}"] = float(value)
            elif indicator.startswith("ema"):
                period = int(indicator.split("_")[1])
                value = _indicator_service.calculate_ema(symbol, period=period)
                result["indicators"][f"ema_{period}"] = float(value)
        except Exception as e:
            result["indicators"][indicator] = f"ERROR: {str(e)}"

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def scan_momentum_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Scan for momentum stocks"""
    min_volume = args.get("min_volume", 1000000)
    min_price = args.get("min_price", 5.0)
    max_price = args.get("max_price", 500.0)
    limit = args.get("limit", 10)

    if _scanner is None:
        return [TextContent(type="text", text="ERROR: Scanner not initialized")]

    # Run momentum scan
    scan_results = _scanner.scan(
        min_volume=min_volume,
        min_price=min_price,
        max_price=max_price
    )

    # Format results
    result = {
        "timestamp": datetime.now().isoformat(),
        "criteria": {
            "min_volume": min_volume,
            "min_price": min_price,
            "max_price": max_price
        },
        "results": [
            {
                "symbol": r.symbol,
                "price": float(r.price),
                "change_pct": float(r.change_percent),
                "volume": int(r.volume),
                "momentum_score": float(r.momentum_score)
            }
            for r in scan_results[:limit]
        ]
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    """Main entry point"""
    try:
        # Initialize services
        await initialize_services()

        # Run MCP server over stdio
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except Exception as e:
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
