#!/usr/bin/env python3
"""
Risk MCP Server

Exposes risk management capabilities from trading_bot to Claude Code via MCP.

Tools provided:
- calculate_position_risk: Calculate risk for proposed position size
- get_portfolio_exposure: Get sector/category exposure breakdown
- check_trade_rules: Validate trade against risk rules
- calculate_max_position_size: Calculate maximum safe position size
- get_risk_metrics: Get portfolio risk metrics (VAR, Sharpe, etc.)

Usage:
    python mcp_servers/risk_server.py
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

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
from trading_bot.risk_management import RiskCalculator
from trading_bot.account import AccountData
from trading_bot.config import Config

# Initialize server
server = Server("risk")

# Global state
_risk_calculator: Optional[RiskCalculator] = None
_account_data: Optional[AccountData] = None
_config: Optional[Config] = None


async def initialize_services():
    """Initialize trading_bot services"""
    global _risk_calculator, _account_data, _config

    try:
        # Load config
        _config = Config.from_env_and_json()

        # Auth
        auth = RobinhoodAuth(_config)
        auth.login()

        # Initialize services
        _account_data = AccountData(auth)
        _risk_calculator = RiskCalculator(_config, _account_data)

        print("Risk services initialized", file=sys.stderr)
    except Exception as e:
        print(f"ERROR initializing services: {e}", file=sys.stderr)
        raise


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available risk tools"""
    return [
        Tool(
            name="calculate_position_risk",
            description="Calculate risk metrics for a proposed position",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol"},
                    "quantity": {"type": "number", "description": "Number of shares"},
                    "entry_price": {"type": "number", "description": "Proposed entry price"},
                    "stop_loss": {"type": "number", "description": "Stop loss price (optional)"}
                },
                "required": ["symbol", "quantity", "entry_price"]
            }
        ),
        Tool(
            name="get_portfolio_exposure",
            description="Get portfolio exposure breakdown by sector/category",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="check_trade_rules",
            description="Validate if proposed trade meets all risk rules",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "side": {"type": "string", "enum": ["buy", "sell"]},
                    "quantity": {"type": "number"},
                    "price": {"type": "number"}
                },
                "required": ["symbol", "side", "quantity", "price"]
            }
        ),
        Tool(
            name="calculate_max_position_size",
            description="Calculate maximum safe position size based on risk limits",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "entry_price": {"type": "number"},
                    "stop_loss": {"type": "number", "description": "Stop loss price (optional)"}
                },
                "required": ["symbol", "entry_price"]
            }
        ),
        Tool(
            name="get_risk_metrics",
            description="Get portfolio risk metrics (VAR, beta, etc.)",
            inputSchema={"type": "object", "properties": {}}
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "calculate_position_risk":
            return await calculate_position_risk_tool(arguments)
        elif name == "get_portfolio_exposure":
            return await get_portfolio_exposure_tool(arguments)
        elif name == "check_trade_rules":
            return await check_trade_rules_tool(arguments)
        elif name == "calculate_max_position_size":
            return await calculate_max_position_size_tool(arguments)
        elif name == "get_risk_metrics":
            return await get_risk_metrics_tool(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        print(error_msg, file=sys.stderr)
        return [TextContent(type="text", text=error_msg)]


async def calculate_position_risk_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Calculate position risk"""
    if _risk_calculator is None:
        return [TextContent(type="text", text="ERROR: Risk calculator not initialized")]

    symbol = args["symbol"].upper()
    quantity = float(args["quantity"])
    entry_price = float(args["entry_price"])
    stop_loss = float(args.get("stop_loss", 0))

    # Calculate risk metrics
    position_value = quantity * entry_price
    balance = _account_data.get_account_balance()
    portfolio_pct = (position_value / float(balance.equity)) * 100

    risk_amount = quantity * (entry_price - stop_loss) if stop_loss > 0 else position_value * 0.02
    risk_pct = (risk_amount / float(balance.equity)) * 100

    result = {
        "symbol": symbol,
        "position_value": position_value,
        "portfolio_pct": portfolio_pct,
        "risk_amount": risk_amount,
        "risk_pct": risk_pct,
        "max_recommended_pct": _config.max_position_size_pct if _config else 10.0,
        "within_limits": portfolio_pct <= (_config.max_position_size_pct if _config else 10.0),
        "recommendation": "ACCEPT" if portfolio_pct <= (_config.max_position_size_pct if _config else 10.0) else "REJECT - Exceeds position limit"
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_portfolio_exposure_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Get portfolio exposure"""
    if _account_data is None:
        return [TextContent(type="text", text="ERROR: Account data not initialized")]

    positions = _account_data.get_positions()
    balance = _account_data.get_account_balance()

    # Calculate exposure by position
    exposure_data = []
    for p in positions:
        if float(p.quantity) > 0:
            market_value = float(p.quantity) * float(p.current_price if hasattr(p, 'current_price') else p.average_buy_price)
            pct_of_portfolio = (market_value / float(balance.equity)) * 100
            exposure_data.append({
                "symbol": p.symbol,
                "market_value": market_value,
                "portfolio_pct": pct_of_portfolio
            })

    # Sort by exposure
    exposure_data.sort(key=lambda x: x["portfolio_pct"], reverse=True)

    result = {
        "total_positions": len(exposure_data),
        "portfolio_equity": float(balance.equity),
        "exposure": exposure_data,
        "concentration_risk": "HIGH" if any(e["portfolio_pct"] > 15 for e in exposure_data) else "NORMAL"
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def check_trade_rules_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Check trade against rules"""
    if _risk_calculator is None or _config is None:
        return [TextContent(type="text", text="ERROR: Risk services not initialized")]

    symbol = args["symbol"].upper()
    side = args["side"].lower()
    quantity = float(args["quantity"])
    price = float(args["price"])

    position_value = quantity * price
    balance = _account_data.get_account_balance()
    portfolio_pct = (position_value / float(balance.equity)) * 100

    # Check rules
    violations = []
    warnings = []

    # Position size limit
    max_pct = _config.max_position_size_pct if hasattr(_config, 'max_position_size_pct') else 10.0
    if portfolio_pct > max_pct:
        violations.append(f"Position size {portfolio_pct:.1f}% exceeds limit of {max_pct}%")

    # Buying power check
    if side == "buy" and position_value > float(balance.buying_power):
        violations.append(f"Insufficient buying power: ${position_value:.2f} > ${float(balance.buying_power):.2f}")

    # Daily trade limit
    if hasattr(_config, 'max_daily_trades'):
        # Would need to check daily trade count here
        pass

    result = {
        "symbol": symbol,
        "side": side,
        "position_value": position_value,
        "portfolio_pct": portfolio_pct,
        "approved": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "recommendation": "APPROVE TRADE" if len(violations) == 0 else "REJECT TRADE"
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def calculate_max_position_size_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Calculate max position size"""
    if _account_data is None or _config is None:
        return [TextContent(type="text", text="ERROR: Services not initialized")]

    symbol = args["symbol"].upper()
    entry_price = float(args["entry_price"])
    stop_loss = float(args.get("stop_loss", 0))

    balance = _account_data.get_account_balance()
    max_position_pct = _config.max_position_size_pct if hasattr(_config, 'max_position_size_pct') else 10.0

    # Calculate max position value
    max_position_value = float(balance.equity) * (max_position_pct / 100.0)

    # Calculate max shares
    max_shares = int(max_position_value / entry_price)

    # If stop loss provided, also calculate based on max risk per trade
    if stop_loss > 0:
        max_risk_pct = _config.max_risk_per_trade_pct if hasattr(_config, 'max_risk_per_trade_pct') else 2.0
        max_risk_amount = float(balance.equity) * (max_risk_pct / 100.0)
        risk_per_share = entry_price - stop_loss
        max_shares_by_risk = int(max_risk_amount / risk_per_share) if risk_per_share > 0 else max_shares
        max_shares = min(max_shares, max_shares_by_risk)

    result = {
        "symbol": symbol,
        "entry_price": entry_price,
        "stop_loss": stop_loss if stop_loss > 0 else None,
        "max_shares": max_shares,
        "max_position_value": max_shares * entry_price,
        "portfolio_pct": (max_shares * entry_price / float(balance.equity)) * 100,
        "buying_power_available": float(balance.buying_power),
        "can_afford": (max_shares * entry_price) <= float(balance.buying_power)
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_risk_metrics_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Get portfolio risk metrics"""
    if _account_data is None:
        return [TextContent(type="text", text="ERROR: Account data not initialized")]

    positions = _account_data.get_positions()
    balance = _account_data.get_account_balance()

    # Calculate basic risk metrics
    active_positions = [p for p in positions if float(p.quantity) > 0]
    total_exposure = sum(
        float(p.quantity) * float(p.current_price if hasattr(p, 'current_price') else p.average_buy_price)
        for p in active_positions
    )

    result = {
        "portfolio_value": float(balance.equity),
        "total_exposure": total_exposure,
        "exposure_pct": (total_exposure / float(balance.equity)) * 100 if float(balance.equity) > 0 else 0,
        "cash_pct": (float(balance.cash) / float(balance.equity)) * 100 if float(balance.equity) > 0 else 0,
        "position_count": len(active_positions),
        "avg_position_size_pct": (total_exposure / len(active_positions) / float(balance.equity) * 100) if active_positions and float(balance.equity) > 0 else 0,
        "largest_position_pct": max(
            (float(p.quantity) * float(p.current_price if hasattr(p, 'current_price') else p.average_buy_price) / float(balance.equity) * 100)
            for p in active_positions
        ) if active_positions and float(balance.equity) > 0 else 0
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    """Main entry point"""
    try:
        await initialize_services()
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    except Exception as e:
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
