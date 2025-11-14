#!/usr/bin/env python3
"""
Backtest MCP Server

Exposes backtesting capabilities from trading_bot to Claude Code via MCP.

Tools provided:
- run_backtest: Run strategy backtest on historical data
- calculate_metrics: Calculate performance metrics (Sharpe, drawdown, etc.)
- compare_strategies: Compare multiple strategy results
- generate_equity_curve: Get equity curve data points
- test_parameter_sensitivity: Test strategy with different parameters

Usage:
    python mcp_servers/backtest_server.py
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
from trading_bot.backtest import BacktestEngine, PerformanceCalculator
from trading_bot.config import Config

# Initialize server
server = Server("backtest")

# Global state
_backtest_engine: Optional[BacktestEngine] = None
_perf_calculator: Optional[PerformanceCalculator] = None
_config: Optional[Config] = None


async def initialize_services():
    """Initialize trading_bot services"""
    global _backtest_engine, _perf_calculator, _config

    try:
        _config = Config.from_env_and_json()
        auth = RobinhoodAuth(_config)
        auth.login()

        _backtest_engine = BacktestEngine(_config)
        _perf_calculator = PerformanceCalculator()

        print("Backtest services initialized", file=sys.stderr)
    except Exception as e:
        print(f"ERROR initializing services: {e}", file=sys.stderr)
        raise


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available backtest tools"""
    return [
        Tool(
            name="run_backtest",
            description="Run strategy backtest on historical data",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol to test"},
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "initial_capital": {"type": "number", "description": "Starting capital", "default": 10000},
                    "strategy_params": {
                        "type": "object",
                        "description": "Strategy parameters (RSI thresholds, MA periods, etc.)"
                    }
                },
                "required": ["symbol", "start_date", "end_date"]
            }
        ),
        Tool(
            name="calculate_metrics",
            description="Calculate performance metrics from backtest results",
            inputSchema={
                "type": "object",
                "properties": {
                    "trades": {"type": "array", "description": "Array of trade results"},
                    "equity_curve": {"type": "array", "description": "Daily equity values"}
                },
                "required": ["trades"]
            }
        ),
        Tool(
            name="compare_strategies",
            description="Compare performance of multiple strategies",
            inputSchema={
                "type": "object",
                "properties": {
                    "strategies": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Array of strategy configs to compare"
                    }
                },
                "required": ["strategies"]
            }
        ),
        Tool(
            name="generate_equity_curve",
            description="Generate equity curve data for visualization",
            inputSchema={
                "type": "object",
                "properties": {
                    "backtest_id": {"type": "string", "description": "Backtest result ID"}
                },
                "required": ["backtest_id"]
            }
        ),
        Tool(
            name="test_parameter_sensitivity",
            description="Test strategy with parameter variations",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "parameter": {"type": "string", "description": "Parameter to vary"},
                    "values": {"type": "array", "items": {"type": "number"}, "description": "Values to test"}
                },
                "required": ["symbol", "start_date", "end_date", "parameter", "values"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "run_backtest":
            return await run_backtest_tool(arguments)
        elif name == "calculate_metrics":
            return await calculate_metrics_tool(arguments)
        elif name == "compare_strategies":
            return await compare_strategies_tool(arguments)
        elif name == "generate_equity_curve":
            return await generate_equity_curve_tool(arguments)
        elif name == "test_parameter_sensitivity":
            return await test_parameter_sensitivity_tool(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        print(error_msg, file=sys.stderr)
        return [TextContent(type="text", text=error_msg)]


async def run_backtest_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Run backtest"""
    if _backtest_engine is None:
        return [TextContent(type="text", text="ERROR: Backtest engine not initialized")]

    symbol = args["symbol"].upper()
    start_date = datetime.fromisoformat(args["start_date"])
    end_date = datetime.fromisoformat(args["end_date"])
    initial_capital = args.get("initial_capital", 10000)
    strategy_params = args.get("strategy_params", {})

    # Run backtest
    results = _backtest_engine.run(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        **strategy_params
    )

    # Calculate metrics
    metrics = _perf_calculator.calculate(results)

    result = {
        "symbol": symbol,
        "period": f"{start_date.date()} to {end_date.date()}",
        "initial_capital": initial_capital,
        "final_capital": results.get("final_capital", initial_capital),
        "total_return": metrics.get("total_return", 0),
        "total_return_pct": metrics.get("total_return_pct", 0),
        "sharpe_ratio": metrics.get("sharpe_ratio", 0),
        "max_drawdown": metrics.get("max_drawdown", 0),
        "max_drawdown_pct": metrics.get("max_drawdown_pct", 0),
        "win_rate": metrics.get("win_rate", 0),
        "profit_factor": metrics.get("profit_factor", 0),
        "total_trades": metrics.get("total_trades", 0),
        "winning_trades": metrics.get("winning_trades", 0),
        "losing_trades": metrics.get("losing_trades", 0),
        "avg_win": metrics.get("avg_win", 0),
        "avg_loss": metrics.get("avg_loss", 0),
        "largest_win": metrics.get("largest_win", 0),
        "largest_loss": metrics.get("largest_loss", 0)
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def calculate_metrics_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Calculate metrics"""
    if _perf_calculator is None:
        return [TextContent(type="text", text="ERROR: Performance calculator not initialized")]

    trades = args["trades"]
    equity_curve = args.get("equity_curve", [])

    # Calculate comprehensive metrics
    metrics = _perf_calculator.calculate_from_trades(trades, equity_curve)

    result = {
        "returns": {
            "total_return": metrics.get("total_return", 0),
            "total_return_pct": metrics.get("total_return_pct", 0),
            "annualized_return": metrics.get("annualized_return", 0),
            "monthly_return_avg": metrics.get("monthly_return_avg", 0)
        },
        "risk": {
            "sharpe_ratio": metrics.get("sharpe_ratio", 0),
            "sortino_ratio": metrics.get("sortino_ratio", 0),
            "max_drawdown": metrics.get("max_drawdown", 0),
            "max_drawdown_pct": metrics.get("max_drawdown_pct", 0),
            "volatility": metrics.get("volatility", 0)
        },
        "trades": {
            "total_trades": len(trades),
            "win_rate": metrics.get("win_rate", 0),
            "profit_factor": metrics.get("profit_factor", 0),
            "avg_win": metrics.get("avg_win", 0),
            "avg_loss": metrics.get("avg_loss", 0),
            "largest_win": metrics.get("largest_win", 0),
            "largest_loss": metrics.get("largest_loss", 0)
        }
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def compare_strategies_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Compare strategies"""
    if _backtest_engine is None:
        return [TextContent(type="text", text="ERROR: Backtest engine not initialized")]

    strategies = args["strategies"]
    comparison = []

    for i, strategy_config in enumerate(strategies):
        # Run backtest for each strategy
        results = _backtest_engine.run(**strategy_config)
        metrics = _perf_calculator.calculate(results)

        comparison.append({
            "strategy_id": i + 1,
            "name": strategy_config.get("name", f"Strategy {i+1}"),
            "total_return_pct": metrics.get("total_return_pct", 0),
            "sharpe_ratio": metrics.get("sharpe_ratio", 0),
            "max_drawdown_pct": metrics.get("max_drawdown_pct", 0),
            "win_rate": metrics.get("win_rate", 0),
            "profit_factor": metrics.get("profit_factor", 0)
        })

    # Sort by Sharpe ratio
    comparison.sort(key=lambda x: x["sharpe_ratio"], reverse=True)

    result = {
        "strategies_compared": len(comparison),
        "rankings": comparison,
        "best_strategy": comparison[0] if comparison else None
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def generate_equity_curve_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Generate equity curve"""
    backtest_id = args["backtest_id"]

    # Retrieve backtest results (from cache/DB)
    # For now, return mock data structure
    result = {
        "backtest_id": backtest_id,
        "equity_curve": [
            {"date": "2024-01-01", "equity": 10000},
            {"date": "2024-01-02", "equity": 10150},
            {"date": "2024-01-03", "equity": 10320},
            # ... more points
        ],
        "drawdown_curve": [
            {"date": "2024-01-01", "drawdown_pct": 0},
            {"date": "2024-01-02", "drawdown_pct": 0},
            {"date": "2024-01-03", "drawdown_pct": -2.5},
            # ... more points
        ]
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def test_parameter_sensitivity_tool(args: Dict[str, Any]) -> List[TextContent]:
    """Test parameter sensitivity"""
    if _backtest_engine is None:
        return [TextContent(type="text", text="ERROR: Backtest engine not initialized")]

    symbol = args["symbol"].upper()
    start_date = datetime.fromisoformat(args["start_date"])
    end_date = datetime.fromisoformat(args["end_date"])
    parameter = args["parameter"]
    values = args["values"]

    results = []

    for value in values:
        # Run backtest with parameter value
        strategy_params = {parameter: value}
        backtest_results = _backtest_engine.run(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            **strategy_params
        )

        metrics = _perf_calculator.calculate(backtest_results)

        results.append({
            "parameter_value": value,
            "total_return_pct": metrics.get("total_return_pct", 0),
            "sharpe_ratio": metrics.get("sharpe_ratio", 0),
            "max_drawdown_pct": metrics.get("max_drawdown_pct", 0),
            "win_rate": metrics.get("win_rate", 0)
        })

    # Find optimal value
    optimal = max(results, key=lambda x: x["sharpe_ratio"])

    result = {
        "parameter": parameter,
        "tested_values": values,
        "results": results,
        "optimal_value": optimal["parameter_value"],
        "optimal_sharpe": optimal["sharpe_ratio"]
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
