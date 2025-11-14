# Trading Bot CLI Documentation

Comprehensive command-line interface for managing and monitoring the Robinhood algorithmic trading bot.

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make the CLI executable:
```bash
chmod +x cli.py
```

3. Verify installation:
```bash
python cli.py --help
```

## Quick Start

### Start the bot in paper trading mode
```bash
python cli.py bot start --mode paper
```

### View current positions
```bash
python cli.py trading positions
```

### Check bot status
```bash
python cli.py bot status
```

### Launch interactive dashboard
```bash
python cli.py dashboard
```

---

## Command Reference

### Bot Control (`bot`)

Manage the trading bot lifecycle.

#### Start Bot
```bash
python cli.py bot start [OPTIONS]
```

**Options:**
- `--dry-run` - Run in validation mode without real trades
- `--mode [paper|live|backtest]` - Trading mode (default: paper)
- `--orchestrator` - Enable LLM orchestrator

**Examples:**
```bash
# Start in paper trading mode
python cli.py bot start --mode paper

# Start with dry-run for validation
python cli.py bot start --dry-run

# Start with LLM orchestrator
python cli.py bot start --orchestrator --mode paper

# Start in live mode (CAUTION!)
python cli.py bot start --mode live
```

#### Stop Bot
```bash
python cli.py bot stop
```

Gracefully stops all running bot processes.

#### Check Status
```bash
python cli.py bot status
```

Shows:
- Running status
- Current workflow state
- Uptime
- Last update timestamp

#### Restart Bot
```bash
python cli.py bot restart [OPTIONS]
```

**Options:**
- `--dry-run` - Restart in validation mode
- `--mode [paper|live|backtest]` - Trading mode

**Example:**
```bash
python cli.py bot restart --mode paper
```

---

### Trading Operations (`trading`)

View and manage trading activity.

#### View Positions
```bash
python cli.py trading positions [OPTIONS]
```

**Options:**
- `--format [table|json]` - Output format (default: table)

**Example:**
```bash
# View as table
python cli.py trading positions

# Export as JSON
python cli.py trading positions --format json > positions.json
```

**Output includes:**
- Symbol
- Quantity
- Average cost
- Current price
- P&L (absolute and percentage)

#### View Orders
```bash
python cli.py trading orders [OPTIONS]
```

**Options:**
- `--days N` - Number of days to look back (default: 1)
- `--status [all|filled|pending|cancelled]` - Filter by status

**Examples:**
```bash
# View today's orders
python cli.py trading orders

# View last 7 days
python cli.py trading orders --days 7

# View only filled orders
python cli.py trading orders --status filled
```

#### Portfolio Summary
```bash
python cli.py trading portfolio
```

Shows:
- Total equity
- Buying power
- Total invested
- Total P&L
- Number of positions

---

### Agent Management (`agents`)

Monitor and interact with the multi-agent system.

#### View Agent Status
```bash
python cli.py agents status
```

Lists all 9 agents:
- NewsAnalystAgent
- ResearchAgent
- RiskManagerAgent
- StrategyBuilderAgent
- RegimeDetectorAgent
- TrendAnalystAgent (Crypto)
- MomentumAnalystAgent (Crypto)
- VolatilityAnalystAgent (Crypto)
- LearningAgent

#### View Agent Metrics
```bash
python cli.py agents metrics [OPTIONS]
```

**Options:**
- `--agent NAME` - Show metrics for specific agent

**Examples:**
```bash
# View all agent metrics
python cli.py agents metrics

# View specific agent
python cli.py agents metrics --agent NewsAnalystAgent
```

**Metrics include:**
- Total calls
- Success rate
- Average response time

#### Get Consensus Decision
```bash
python cli.py agents consensus SYMBOL TASK_TYPE
```

**Arguments:**
- `SYMBOL` - Stock/crypto symbol
- `TASK_TYPE` - One of: analyze, risk_check, strategy

**Example:**
```bash
# Get consensus on analyzing AAPL
python cli.py agents consensus AAPL analyze

# Get risk check consensus for BTC
python cli.py agents consensus BTC-USD risk_check
```

---

### Workflow Management (`workflow`)

Execute and monitor trading workflows.

#### Execute Workflow
```bash
python cli.py workflow execute WORKFLOW_NAME [OPTIONS]
```

**Workflow Names:**
- `pre-market-screening` - Scan for trading opportunities
- `trade-analysis` - Analyze potential trades
- `position-optimization` - Optimize existing positions
- `market-execution` - Execute planned trades
- `intraday-monitoring` - Monitor active positions
- `end-of-day-review` - Review day's performance
- `weekly-review` - Weekly performance analysis

**Options:**
- `--dry-run` - Simulate without executing

**Examples:**
```bash
# Run pre-market screening
python cli.py workflow execute pre-market-screening

# Dry-run EOD review
python cli.py workflow execute end-of-day-review --dry-run

# Execute market trades
python cli.py workflow execute market-execution
```

#### List Workflows
```bash
python cli.py workflow list
```

Shows all available workflows with descriptions and typical execution times.

---

### Risk Management (`risk`)

Monitor and manage risk parameters.

#### View Risk Metrics
```bash
python cli.py risk metrics
```

Shows:
- Total equity
- Daily loss (absolute and percentage)
- Risk limits

#### View Risk Limits
```bash
python cli.py risk limits
```

Displays configured limits:
- Max daily loss percentage
- Max position size percentage
- Stop loss percentage
- Take profit percentage
- Max open positions

#### Emotional Control Status
```bash
python cli.py risk emotional-control
```

Shows:
- Loss streak count
- Position size multiplier
- Circuit breaker status
- Last update timestamp

**Note:** Emotional control reduces position sizes during loss streaks to prevent revenge trading.

---

### Configuration (`config`)

Manage bot configuration.

#### View Configuration
```bash
python cli.py config view [OPTIONS]
```

**Options:**
- `--format [table|json]` - Output format

**Examples:**
```bash
# View as table
python cli.py config view

# Export as JSON
python cli.py config view --format json > config_backup.json
```

#### Validate Configuration
```bash
python cli.py config validate
```

Checks:
- .env file exists
- config.json exists
- data directory exists
- logs directory exists

---

### Log Management (`logs`)

View and export trading logs.

#### View Logs
```bash
python cli.py logs view [OPTIONS]
```

**Options:**
- `--tail N` - Show last N lines (default: 50)
- `--follow` / `-f` - Follow log output (like `tail -f`)
- `--level [DEBUG|INFO|WARNING|ERROR]` - Filter by level

**Examples:**
```bash
# View last 50 lines
python cli.py logs view

# View last 100 lines
python cli.py logs view --tail 100

# Follow log in real-time
python cli.py logs view --follow

# View only errors
python cli.py logs view --level ERROR
```

#### Export Trade Logs
```bash
python cli.py logs export [OPTIONS]
```

**Options:**
- `--start-date YYYY-MM-DD` - Start date
- `--end-date YYYY-MM-DD` - End date
- `--output FILE` - Output file path

**Examples:**
```bash
# Export all trade logs
python cli.py logs export

# Export specific date range
python cli.py logs export --start-date 2025-01-01 --end-date 2025-01-31

# Export to specific file
python cli.py logs export --output january_trades.json
```

---

### Watchlist (`watchlist`)

Manage trading watchlist.

#### Generate Watchlist
```bash
python cli.py watchlist generate [OPTIONS]
```

**Options:**
- `--preview` - Preview without saving
- `--min-volume N` - Minimum volume filter

**Examples:**
```bash
# Generate and save
python cli.py watchlist generate

# Preview without saving
python cli.py watchlist generate --preview

# Filter by volume
python cli.py watchlist generate --min-volume 1000000
```

#### View Watchlist
```bash
python cli.py watchlist view
```

Shows current watchlist with:
- Symbol
- Company name
- Sector
- Score

---

### Dashboard

Launch the interactive Rich terminal dashboard.

```bash
python cli.py dashboard
```

Features:
- Real-time P&L tracking
- Position monitoring
- Trade execution status
- Risk metrics display
- Agent activity

**Controls:**
- Press `Ctrl+C` to exit

---

## Usage Patterns

### Daily Trading Routine

```bash
# 1. Morning - Check status and validate config
python cli.py bot status
python cli.py config validate

# 2. Pre-market - Generate watchlist and review
python cli.py watchlist generate
python cli.py watchlist view

# 3. Market open - Start bot
python cli.py bot start --mode paper

# 4. Monitor during day
python cli.py trading positions
python cli.py risk metrics

# 5. End of day - Review and stop
python cli.py workflow execute end-of-day-review
python cli.py bot stop
```

### Performance Analysis

```bash
# View recent trades
python cli.py trading orders --days 7

# Check portfolio performance
python cli.py trading portfolio

# Export trade history for analysis
python cli.py logs export --start-date 2025-01-01 --output monthly.json

# View agent performance
python cli.py agents metrics
```

### Troubleshooting

```bash
# Check bot status
python cli.py bot status

# View recent errors
python cli.py logs view --level ERROR --tail 100

# Validate configuration
python cli.py config validate

# Check risk limits
python cli.py risk limits
python cli.py risk emotional-control

# Restart bot
python cli.py bot restart --mode paper
```

---

## Environment Setup

The CLI requires the following environment variables (in `.env`):

```bash
# Robinhood Credentials
ROBINHOOD_USERNAME=your_username
ROBINHOOD_PASSWORD=your_password
ROBINHOOD_MFA_CODE=your_mfa_code

# API Keys
ANTHROPIC_API_KEY=your_anthropic_key
FMP_API_KEY=your_fmp_key
POLYGON_API_KEY=your_polygon_key

# Trading Mode
TRADING_MODE=paper  # or live
```

---

## Output Formats

### Table Format (Default)
Clean, human-readable tables with color-coded data.

### JSON Format
Machine-readable JSON for scripting and integration.

Example:
```bash
# Get positions as JSON
python cli.py trading positions --format json | jq '.[] | select(.symbol == "AAPL")'
```

---

## Integration Examples

### Bash Script
```bash
#!/bin/bash
# Daily trading script

echo "Starting daily trading routine..."

# Generate watchlist
python cli.py watchlist generate

# Start bot
python cli.py bot start --mode paper &

# Wait for market close
sleep 23400  # 6.5 hours

# Run EOD review
python cli.py workflow execute end-of-day-review

# Stop bot
python cli.py bot stop
```

### Python Script
```python
import subprocess
import json

# Get positions as JSON
result = subprocess.run(
    ["python", "cli.py", "trading", "positions", "--format", "json"],
    capture_output=True,
    text=True
)

positions = json.loads(result.stdout)

# Analyze positions
for pos in positions:
    if pos['pnl_pct'] < -5:
        print(f"Alert: {pos['symbol']} down {pos['pnl_pct']:.2f}%")
```

---

## Error Codes

- `0` - Success
- `1` - General error
- `2` - Configuration error
- `3` - Authentication error
- `4` - API error

---

## Tips and Best Practices

1. **Always start with paper trading** until comfortable with the bot
2. **Use dry-run mode** to test changes: `python cli.py bot start --dry-run`
3. **Monitor logs** regularly: `python cli.py logs view --follow`
4. **Check risk metrics** before trading: `python cli.py risk metrics`
5. **Export trades regularly** for analysis and backup
6. **Use watchlist preview** before committing changes
7. **Validate config** after making changes: `python cli.py config validate`

---

## Support

For issues or questions:
- Check logs: `python cli.py logs view --level ERROR`
- Validate setup: `python cli.py config validate`
- Review documentation: `README.md` and `CLAUDE.md`

---

## Version History

**v1.0.0** - Initial CLI release
- Bot control commands
- Trading operations
- Agent management
- Workflow execution
- Risk monitoring
- Configuration management
- Log viewing and export
- Watchlist management
- Interactive dashboard
