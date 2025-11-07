#!/usr/bin/env python3
"""
Position MCP Server

Exposes portfolio and position data from trading_bot to Claude Code via MCP.

Tools provided:
- get_positions: Get all current portfolio positions
- get_position_details: Get detailed info for specific position
- get_portfolio_summary: Get portfolio value and performance metrics
- get_buying_power: Get available buying power and margin info
- get_trade_history: Get recent trade history

Usage:
    python mcp_servers/position_server.py
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    import mcp.server.stdio
except ImportError:
    print("ERROR: mcp package not installed. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.account import AccountData, Position
from trading_bot.performance import PerformanceTracker
from trading_bot.config import Config

# Initialize server
server = Server("position")

# Global state
_account_data: Optional[AccountData] = None
_performance_tracker: Optional[PerformanceTracker] = None
_auth: Optional[RobinhoodAuth] = None


async def initialize_services():
    """Initialize trading_bot services"""
    global _account_data, _performance_tracker, _auth

    try:
        # Load config
        config = Config.from_env_and_json()

        # Auth
        _auth = RobinhoodAuth(config)
        _auth.login()

        # Initialize services
        _account_data = AccountData(_auth)
        _performance_tracker = PerformanceTracker(config)

        print("Position services initialized", file=sys.stderr)
    except Exception as e:
        print(f"ERROR initializing services: {e}", file=sys.stderr)
        raise


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available position tools"""
    return [
        Tool(
            name="get_positions",
            description="Get all current portfolio positions with P&L",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_closed": {
                        "type": "boolean",
                        "description": "Include recently closed positions (default: false)",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="get_position_details",
            description="Get detailed information for a specific position",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol"
                    }
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="get_portfolio_summary",
            description="Get portfolio value, total P&L, and performance metrics",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_buying_power",
            description="Get available buying power and margin information",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_trade_history",
            description="Get recent trade history with P&L",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days of history (default: 7)",
                        "default": 7
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Filter by symbol (optional)"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "get_positions":
            return await get_positions_tool(arguments)
        elif name == "get_position_details":
            return await get_position_details_tool(arguments)
        elif name == "get_portfolio_summary":
            return await get_portfolio_summary_tool(arguments)
        elif name == "get_buying_power":
            return await get_buying_power_tool(arguments)
        elif name == "get_trade_history":
            return await get_trade_history_tool(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        print(error_msg, file=sys.stderr)
        return [TextContent(type="text", text=error_msg)]


async def get_positions_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Get all positions"""
    include_closed = args.get("include_closed", False)

    if _account_data is None:
        return [TextContent(type="text", text="ERROR: Account data service not initialized")]

    # Get positions from Robinhood
    positions = _account_data.get_positions()

    # Filter out closed positions unless requested
    if not include_closed:
        positions = [p for p in positions if float(p.quantity) > 0]

    # Format results
    result = {
        "timestamp": datetime.now().isoformat(),
        "position_count": len(positions),
        "positions": [
            {
                "symbol": p.symbol,
                "quantity": float(p.quantity),
                "average_cost": float(p.average_buy_price),
                "current_price": float(p.current_price) if hasattr(p, 'current_price') else None,
                "market_value": float(p.quantity) * float(p.current_price) if hasattr(p, 'current_price') else None,
                "total_cost": float(p.quantity) * float(p.average_buy_price),
                "unrealized_pl": float(p.unrealized_pl) if hasattr(p, 'unrealized_pl') else None,
                "unrealized_pl_pct": float(p.unrealized_pl_percent) if hasattr(p, 'unrealized_pl_percent') else None,
            }
            for p in positions
        ]
    }

    # Calculate totals
    total_market_value = sum(
        p["market_value"] for p in result["positions"] if p["market_value"] is not None
    )
    total_cost = sum(p["total_cost"] for p in result["positions"])
    total_unrealized_pl = sum(
        p["unrealized_pl"] for p in result["positions"] if p["unrealized_pl"] is not None
    )

    result["totals"] = {
        "market_value": total_market_value,
        "total_cost": total_cost,
        "unrealized_pl": total_unrealized_pl,
        "unrealized_pl_pct": (total_unrealized_pl / total_cost * 100) if total_cost > 0 else 0
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_position_details_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Get detailed position info"""
    symbol = args["symbol"].upper()

    if _account_data is None:
        return [TextContent(type="text", text="ERROR: Account data service not initialized")]

    # Get all positions and filter for symbol
    positions = _account_data.get_positions()
    position = next((p for p in positions if p.symbol == symbol), None)

    if position is None:
        return [TextContent(type="text", text=f"No position found for {symbol}")]

    # Get additional details
    result = {
        "symbol": position.symbol,
        "quantity": float(position.quantity),
        "average_cost": float(position.average_buy_price),
        "current_price": float(position.current_price) if hasattr(position, 'current_price') else None,
        "market_value": float(position.quantity) * float(position.current_price) if hasattr(position, 'current_price') else None,
        "total_cost": float(position.quantity) * float(position.average_buy_price),
        "unrealized_pl": float(position.unrealized_pl) if hasattr(position, 'unrealized_pl') else None,
        "unrealized_pl_pct": float(position.unrealized_pl_percent) if hasattr(position, 'unrealized_pl_percent') else None,
        "created_at": position.created_at.isoformat() if hasattr(position, 'created_at') else None,
        "updated_at": datetime.now().isoformat()
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_portfolio_summary_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Get portfolio summary"""
    if _account_data is None:
        return [TextContent(type="text", text="ERROR: Account data service not initialized")]

    # Get account balance and positions
    balance = _account_data.get_account_balance()
    positions = _account_data.get_positions()

    # Calculate portfolio metrics
    active_positions = [p for p in positions if float(p.quantity) > 0]

    total_market_value = sum(
        float(p.quantity) * float(p.current_price)
        for p in active_positions
        if hasattr(p, 'current_price')
    )

    total_cost = sum(
        float(p.quantity) * float(p.average_buy_price)
        for p in active_positions
    )

    total_unrealized_pl = sum(
        float(p.unrealized_pl)
        for p in active_positions
        if hasattr(p, 'unrealized_pl')
    )

    result = {
        "timestamp": datetime.now().isoformat(),
        "account": {
            "equity": float(balance.equity),
            "buying_power": float(balance.buying_power),
            "cash": float(balance.cash),
            "market_value": float(balance.market_value) if hasattr(balance, 'market_value') else total_market_value
        },
        "positions": {
            "count": len(active_positions),
            "total_market_value": total_market_value,
            "total_cost": total_cost,
            "total_unrealized_pl": total_unrealized_pl,
            "total_unrealized_pl_pct": (total_unrealized_pl / total_cost * 100) if total_cost > 0 else 0
        },
        "performance": {
            "total_return_pct": (total_unrealized_pl / total_cost * 100) if total_cost > 0 else 0
        }
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_buying_power_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Get buying power"""
    if _account_data is None:
        return [TextContent(type="text", text="ERROR: Account data service not initialized")]

    balance = _account_data.get_account_balance()

    result = {
        "timestamp": datetime.now().isoformat(),
        "buying_power": float(balance.buying_power),
        "cash": float(balance.cash),
        "equity": float(balance.equity),
        "buying_power_pct": (float(balance.buying_power) / float(balance.equity) * 100) if float(balance.equity) > 0 else 0,
        "margin_used": float(balance.equity) - float(balance.cash) if hasattr(balance, 'cash') else None
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_trade_history_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Get trade history"""
    days = args.get("days", 7)
    filter_symbol = args.get("symbol")

    if _performance_tracker is None:
        return [TextContent(type="text", text="ERROR: Performance tracker not initialized")]

    # Get trade history from performance tracker
    start_date = datetime.now() - timedelta(days=days)
    trades = _performance_tracker.get_trades_since(start_date)

    # Filter by symbol if requested
    if filter_symbol:
        filter_symbol = filter_symbol.upper()
        trades = [t for t in trades if t.get('symbol') == filter_symbol]

    # Format results
    result = {
        "timestamp": datetime.now().isoformat(),
        "period_days": days,
        "filter_symbol": filter_symbol,
        "trade_count": len(trades),
        "trades": [
            {
                "timestamp": t.get('timestamp'),
                "symbol": t.get('symbol'),
                "side": t.get('side'),  # buy or sell
                "quantity": float(t.get('quantity', 0)),
                "price": float(t.get('price', 0)),
                "total_value": float(t.get('quantity', 0)) * float(t.get('price', 0)),
                "realized_pl": float(t.get('realized_pl', 0)) if 'realized_pl' in t else None,
                "realized_pl_pct": float(t.get('realized_pl_pct', 0)) if 'realized_pl_pct' in t else None
            }
            for t in trades[:100]  # Limit to 100 most recent
        ]
    }

    # Calculate summary stats
    if result["trades"]:
        winning_trades = [t for t in result["trades"] if t.get("realized_pl", 0) > 0]
        losing_trades = [t for t in result["trades"] if t.get("realized_pl", 0) < 0]

        result["summary"] = {
            "total_realized_pl": sum(t.get("realized_pl", 0) for t in result["trades"] if t.get("realized_pl") is not None),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": (len(winning_trades) / len(result["trades"]) * 100) if result["trades"] else 0,
            "avg_win": (sum(t.get("realized_pl", 0) for t in winning_trades) / len(winning_trades)) if winning_trades else 0,
            "avg_loss": (sum(t.get("realized_pl", 0) for t in losing_trades) / len(losing_trades)) if losing_trades else 0
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
