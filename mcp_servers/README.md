# MCP Servers for Trading Bot

Model Context Protocol (MCP) servers expose trading_bot capabilities to Claude Code as tools.

## Overview

These MCP servers provide Claude Code with direct access to:
- Real-time market data and quotes
- Historical price data for analysis
- Technical indicators (RSI, MACD, ATR, etc.)
- Momentum stock scanning
- Position tracking and portfolio data
- Risk metrics and exposure analysis
- Backtesting capabilities

## Installation

### 1. Install MCP Package

```bash
pip install mcp
```

### 2. Configure Claude Code

Add the following to your Claude Code configuration (`~/.claude/mcp.json` or project-level):

```json
{
  "mcpServers": {
    "market-data": {
      "command": "python",
      "args": ["mcp_servers/market_data_server.py"],
      "cwd": "D:/Coding/Stocks"
    }
  }
}
```

### 3. Verify Environment

Make sure trading_bot credentials are configured:
- `.env` file with Robinhood credentials
- `config.json` with trading parameters

## Available Servers

### 1. Market Data Server (`market_data_server.py`)

**Status**: Implemented

**Tools**:
- `get_quote` - Get realtime quote for a symbol
- `get_historical` - Get historical price data (up to 1 year)
- `get_market_status` - Check if market is open
- `calculate_indicators` - Calculate RSI, MACD, ATR, SMA, EMA, BBands
- `scan_momentum` - Scan for high-momentum trading opportunities

**Example Usage** (from Claude Code):
```python
# Get quote
await call_tool("get_quote", {"symbol": "AAPL"})

# Get 30 days of historical data
await call_tool("get_historical", {
    "symbol": "AAPL",
    "days": 30,
    "interval": "1day"
})

# Calculate indicators
await call_tool("calculate_indicators", {
    "symbol": "AAPL",
    "indicators": ["rsi", "macd", "atr"]
})

# Scan for momentum stocks
await call_tool("scan_momentum", {
    "min_volume": 1000000,
    "min_price": 10.0,
    "max_price": 200.0,
    "limit": 10
})
```

### 2. Position Server (`position_server.py`)

**Status**: Planned (Phase 1.3)

**Planned Tools**:
- `get_positions` - Get current portfolio positions
- `get_position_details` - Get detailed position info for symbol
- `get_portfolio_summary` - Get portfolio value and metrics
- `get_buying_power` - Get available buying power
- `get_trade_history` - Get recent trade history

### 3. Risk Server (`risk_server.py`)

**Status**: Planned (Phase 1.4)

**Planned Tools**:
- `calculate_position_risk` - Calculate risk for position size
- `get_portfolio_exposure` - Get sector/category exposure
- `calculate_sharpe_ratio` - Calculate risk-adjusted returns
- `get_max_position_size` - Calculate max safe position size
- `check_trade_rules` - Validate trade against risk rules

### 4. Backtest Server (`backtest_server.py`)

**Status**: Planned (Phase 1.5)

**Planned Tools**:
- `run_backtest` - Run strategy backtest on historical data
- `calculate_metrics` - Calculate performance metrics (Sharpe, max drawdown, etc.)
- `compare_strategies` - Compare multiple strategy results
- `generate_equity_curve` - Generate equity curve visualization data
- `test_parameter_sensitivity` - Test strategy parameter robustness

## Testing MCP Servers

### Manual Test (Standalone)

```bash
cd D:/Coding/Stocks

# Test market data server directly
python mcp_servers/market_data_server.py
```

### Test via Claude Code

```bash
# Use Claude Code headless mode to test
claude -p "Use the get_quote tool to get a quote for AAPL" --model haiku
```

## Development

### Creating a New MCP Server

1. **Create server file** in `mcp_servers/`
2. **Implement required handlers**:
   - `list_tools()` - Return available tools
   - `call_tool()` - Handle tool invocations
3. **Add to configuration** in `mcp_config.json`
4. **Test standalone** before integration
5. **Document** in this README

### MCP Protocol Reference

- [MCP Specification](https://modelcontextprotocol.io/)
- [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)

## Architecture

```
Claude Code (via subprocess)
    |
    v
ClaudeCodeManager (Python)
    |
    v
MCP Servers (5 tools each)
    |
    v
trading_bot modules
    |
    v
Robinhood API / Market Data
```

**Data Flow**:
1. Python orchestrator invokes Claude Code via subprocess
2. Claude Code uses MCP tools to access trading_bot data
3. MCP servers query trading_bot modules
4. Results returned as JSON to Claude Code
5. Claude Code processes and returns decision to Python
6. Python executes trade via trading_bot

## Security

- MCP servers run in same process as trading_bot (trusted)
- No network exposure - stdio communication only
- Credentials loaded from environment (not passed via MCP)
- Rate limiting enforced by trading_bot, not MCP servers
- Read-only operations preferred (write operations gated)

## Performance

- MCP servers add ~50-100ms latency per tool call
- Caching implemented at trading_bot level
- Historical data requests cached for 1 hour
- Quote data cached for 10 seconds
- Indicator calculations cached for 5 minutes

## Troubleshooting

### "mcp package not installed"
```bash
pip install mcp
```

### "Trading_bot auth failed"
Check `.env` file has valid Robinhood credentials:
```
ROBINHOOD_USERNAME=your_username
ROBINHOOD_PASSWORD=your_password
```

### "Market data service not initialized"
MCP server may have failed to connect to Robinhood. Check logs:
```bash
python mcp_servers/market_data_server.py 2>&1 | tee mcp_debug.log
```

### "Tool not found"
Make sure MCP server is registered in Claude Code config and restarted Claude Code CLI.

## Cost Tracking

- MCP tool calls are free (no API costs)
- Claude Code subscription required ($20/month)
- LLM costs charged per Claude Code invocation (see claude_manager.py budget tracking)
- Estimated cost: $0.0001-0.0007 per LLM call with Haiku 4.5

## Monitoring

MCP server logs written to stderr:
```bash
# Watch MCP server logs
python mcp_servers/market_data_server.py 2>&1 | tee logs/mcp-market-data.log
```

Tool invocation metrics in `logs/llm-calls.jsonl` (logged by ClaudeCodeManager).

## Contributing

When adding new MCP tools:
1. Follow naming convention: `verb_noun` (e.g., `get_quote`, `calculate_indicators`)
2. Use JSON input/output schemas with clear descriptions
3. Add comprehensive error handling
4. Update this README with examples
5. Add tests to `tests/test_mcp_servers.py`

## License

Part of trading_bot - see main project LICENSE
