# Beginner Tutorial: Your First Trade with the Trading Bot

This step-by-step tutorial will guide you through setting up and executing your first paper trade.

**Time Required**: 30-45 minutes
**Prerequisites**: Python 3.11+, Robinhood account
**Difficulty**: Beginner

---

## Table of Contents

- [Before You Begin](#before-you-begin)
- [Step 1: Installation](#step-1-installation)
- [Step 2: Configuration](#step-2-configuration)
- [Step 3: First Startup](#step-3-first-startup)
- [Step 4: Understanding the Interface](#step-4-understanding-the-interface)
- [Step 5: Your First Paper Trade](#step-5-your-first-paper-trade)
- [Step 6: Monitoring Performance](#step-6-monitoring-performance)
- [Step 7: Using the API](#step-7-using-the-api)
- [Next Steps](#next-steps)
- [Troubleshooting](#troubleshooting)

---

## Before You Begin

### What You'll Learn

- How to install and configure the trading bot
- How to execute your first paper trade (no real money)
- How to monitor bot performance
- How to use the API for monitoring
- How safety features protect your capital

### What You'll Need

✅ **Computer**: Windows, Mac, or Linux
✅ **Python 3.11+**: [Download here](https://www.python.org/downloads/)
✅ **Robinhood Account**: [Sign up](https://robinhood.com) (no money required for paper trading)
✅ **Text Editor**: VSCode, Sublime, or Notepad++
✅ **Terminal/Command Prompt**: Basic familiarity

### Safety First

This tutorial uses **paper trading** (simulation) by default. No real money will be used. You'll see exactly how the bot works before risking any capital.

---

## Step 1: Installation

### 1.1 Download the Bot

Open your terminal and run:

```bash
# Navigate to where you want to install
cd ~/projects  # Mac/Linux
cd C:\Projects  # Windows

# Clone the repository
git clone https://github.com/marcusgoll/robinhood-algo-trading-bot.git

# Enter the directory
cd robinhood-algo-trading-bot
```

### 1.2 Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate      # Windows

# Your prompt should now show (venv)
```

### 1.3 Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# This will take 1-2 minutes
```

**Expected output**: `Successfully installed...` (long list of packages)

---

## Step 2: Configuration

### 2.1 Create Configuration Files

```bash
# Copy example files
cp .env.example .env
cp config.example.json config.json

# These are the files you'll edit
```

### 2.2 Configure Credentials (.env file)

Open `.env` in your text editor and add your Robinhood credentials:

```bash
# Required
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_password

# Optional (but recommended)
ROBINHOOD_MFA_SECRET=  # We'll set this up later

# Leave this empty for now
DEVICE_TOKEN=
```

**How to get MFA secret** (optional but recommended):

1. In Robinhood app: Settings → Security → Two-Factor Authentication
2. Choose "Authentication App"
3. Copy the SECRET KEY (16 characters, like `ABCD1234EFGH5678`)
4. Paste into `ROBINHOOD_MFA_SECRET=ABCD1234EFGH5678`

### 2.3 Configure Trading Parameters (config.json)

Open `config.json` and verify these settings:

```json
{
  "mode": "paper",
  "phase_progression": {
    "current_phase": "experience"
  },
  "risk_management": {
    "max_position_pct": 5.0,
    "max_daily_loss_pct": 3.0
  },
  "trading_hours": {
    "start": "07:00",
    "end": "10:00",
    "timezone": "America/New_York"
  }
}
```

**Key settings explained**:
- `"mode": "paper"` → Simulation only, no real money
- `"current_phase": "experience"` → Safe learning phase
- `"max_position_pct": 5.0` → Max 5% of account per trade
- `"max_daily_loss_pct": 3.0` → Stop trading if you lose 3%

### 2.4 Validate Configuration

```bash
# Run validation script
python validate_startup.py
```

**Expected output**:
```
✅ All checks passed - Ready to start bot!
```

If you see errors, double-check your `.env` and `config.json` files.

---

## Step 3: First Startup

### 3.1 Start the Trading Bot

```bash
# Start the bot
python -m src.trading_bot
```

**What you'll see**:

```
╔════════════════════════════════════════════════════════════╗
║                    PAPER TRADING MODE                      ║
║                  (Simulation - No Real Money)              ║
╚════════════════════════════════════════════════════════════╝

2025-10-26 10:00:00 UTC | INFO | Bot initialized
2025-10-26 10:00:01 UTC | INFO | Logged into Robinhood
2025-10-26 10:00:02 UTC | INFO | Phase: EXPERIENCE (paper trading)
2025-10-26 10:00:03 UTC | INFO | Trading hours: 7:00 AM - 10:00 AM EST
2025-10-26 10:00:04 UTC | INFO | Bot ready - waiting for market open
```

**Congratulations!** Your bot is now running.

### 3.2 Start the API Service (Optional)

Open a **new terminal window**:

```bash
# Navigate to bot directory
cd robinhood-algo-trading-bot

# Activate virtual environment
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate      # Windows

# Set API token
echo "BOT_API_AUTH_TOKEN=my-secure-token-123" >> .env

# Start API service
bash scripts/start_api.sh
```

**What you'll see**:
```
Starting Trading Bot API...
API Configuration:
  Host: 0.0.0.0
  Port: 8000
  Auth: Configured
Starting uvicorn server...
INFO: Started server process
INFO: Uvicorn running on http://0.0.0.0:8000
```

The API is now accessible at `http://localhost:8000/api/docs`

---

## Step 4: Understanding the Interface

### 4.1 Bot Terminal Output

The bot logs everything to the terminal:

```
# Startup
INFO | Bot initialized
INFO | Logged into Robinhood

# Strategy signals
INFO | Bull flag detected: AAPL
INFO | Entry signal: BUY 100 AAPL @ $150.50

# Trade execution
INFO | BUY 100 AAPL @ 150.50 [PAPER]
INFO | Stop loss: $148.00 | Target: $155.50

# Monitoring
INFO | Position update: AAPL +$200 (+1.33%)

# Exit
INFO | SELL 100 AAPL @ 152.50 [PAPER]
INFO | Trade result: +$200 profit (+1.33%)
```

### 4.2 Log Files

All activity is logged to `logs/` directory:

```
logs/
├── trading_bot.log    # General logs
├── trades.log         # Trade audit trail
└── errors.log         # Errors and warnings
```

**View logs in real-time**:
```bash
tail -f logs/trading_bot.log
tail -f logs/trades.log
```

### 4.3 API Interface

Open browser to `http://localhost:8000/api/docs` to see interactive API documentation (Swagger UI).

---

## Step 5: Your First Paper Trade

### 5.1 Wait for Trading Hours

The bot only trades during configured hours (7:00 AM - 10:00 AM EST by default).

**Check current status**:
```bash
# Via API
curl -H "X-API-Key: my-secure-token-123" \
  http://localhost:8000/api/v1/summary
```

### 5.2 Watch for Entry Signals

The bot will automatically look for trading opportunities. You'll see:

```
INFO | Scanning for bull flag patterns
INFO | Candidate found: AAPL (consolidation after 5% move)
INFO | Entry conditions met: AAPL
INFO | Calculating position size...
INFO | Position: 100 shares | Risk: 2.5% | Stop: $148.00
```

### 5.3 Entry Execution

When conditions are perfect:

```
INFO | BUY 100 AAPL @ 150.50 [PAPER]
INFO | Entry: $150.50 | Stop: $148.00 | Target: $155.50
INFO | Risk/Reward: 1:2.0
INFO | Position opened: AAPL
```

**Check your logs**:
```bash
grep "BUY" logs/trades.log | tail -1
```

**Expected output**:
```
2025-10-26 09:30:00 UTC | INFO | BUY 100 AAPL @ 150.50 [PAPER] | Strategy: Bull Flag | Stop: 148.00 | Target: 155.50
```

### 5.4 Monitor the Trade

**Via terminal**:
```
INFO | Position update: AAPL +$50 (+0.33%)
INFO | Position update: AAPL +$150 (+1.00%)
INFO | Position update: AAPL +$300 (+2.00%)
```

**Via API**:
```bash
curl -H "X-API-Key: my-secure-token-123" \
  http://localhost:8000/api/v1/state | jq '.positions'
```

**Expected output**:
```json
[
  {
    "symbol": "AAPL",
    "quantity": 100,
    "entry_price": "150.50",
    "current_price": "153.50",
    "unrealized_pl": "300.00",
    "unrealized_pl_pct": "2.00"
  }
]
```

### 5.5 Exit

The bot will automatically exit when:

1. **Target hit** ($155.50): `+$500 profit (+3.3%)`
2. **Stop loss hit** ($148.00): `-$250 loss (-1.7%)`
3. **Time-based exit**: End of trading hours

**Exit example**:
```
INFO | Target reached: AAPL @ $155.50
INFO | SELL 100 AAPL @ 155.50 [PAPER]
INFO | Trade result: +$500 profit (+3.32%)
INFO | Position closed: AAPL
```

**Congratulations!** You've completed your first (paper) trade.

---

## Step 6: Monitoring Performance

### 6.1 Daily Performance

**Via API**:
```bash
curl -H "X-API-Key: my-secure-token-123" \
  http://localhost:8000/api/v1/state | jq '.performance'
```

**Expected output**:
```json
{
  "win_rate": 1.0,
  "avg_risk_reward": 2.0,
  "total_realized_pl": "500.00",
  "total_unrealized_pl": "0.00",
  "total_pl": "500.00",
  "current_streak": 1,
  "streak_type": "WIN",
  "trades_today": 1,
  "session_count": 1,
  "max_drawdown": "0.00"
}
```

### 6.2 Trade History

**View all trades**:
```bash
cat logs/trades.log
```

**Count trades today**:
```bash
grep "$(date +%Y-%m-%d)" logs/trades.log | wc -l
```

### 6.3 Win Rate Calculation

**Count wins**:
```bash
grep "SELL" logs/trades.log | grep -c "profit"
```

**Count total trades**:
```bash
grep "SELL" logs/trades.log | wc -l
```

**Calculate win rate**:
```bash
# (Wins / Total) * 100 = Win Rate %
```

---

## Step 7: Using the API

### 7.1 Quick Health Check

```bash
curl -H "X-API-Key: my-secure-token-123" \
  http://localhost:8000/api/v1/health
```

**Response**:
```json
{
  "status": "healthy",
  "circuit_breaker_active": false,
  "api_connected": true,
  "error_count_last_hour": 0
}
```

### 7.2 Get Bot Summary

```bash
curl -H "X-API-Key: my-secure-token-123" \
  http://localhost:8000/api/v1/summary
```

**Response** (compressed, <10KB):
```json
{
  "health_status": "healthy",
  "position_count": 0,
  "open_orders_count": 0,
  "daily_pnl": "500.00",
  "circuit_breaker_status": "inactive",
  "recent_errors": [],
  "timestamp": "2025-10-26T10:30:00Z"
}
```

### 7.3 Natural Language Queries

```bash
# Ask questions in plain English
python -m src.trading_bot.cli.nl_commands "show today's performance"

python -m src.trading_bot.cli.nl_commands "check bot health"

python -m src.trading_bot.cli.nl_commands "what positions are open?"
```

---

## Next Steps

### Level Up Your Trading

**Week 1: Paper Trading**
- [x] Complete first trade
- [ ] Execute 5-10 more paper trades
- [ ] Track performance in a spreadsheet
- [ ] Understand win rate and risk:reward

**Week 2: Strategy Exploration**
- [ ] Try different strategies (see `config.json` strategies section)
- [ ] Backtest strategies (see `examples/simple_backtest.py`)
- [ ] Read strategy documentation in `specs/` directory

**Week 3: Advanced Features**
- [ ] Enable emotional control monitoring
- [ ] Set up profit protection
- [ ] Configure order flow monitoring (requires Polygon.io)
- [ ] Explore support/resistance zone trading

**Month 2: Live Trading Preparation**
- [ ] Review 2 weeks of consistent paper trading profits
- [ ] Validate win rate ≥55%
- [ ] Progress to "proof" phase (1 trade/day with real money)
- [ ] Start with small position sizes

### Recommended Reading

1. [README.md](../README.md) - Full feature documentation
2. [API Documentation](API.md) - Complete API reference
3. [Operations Guide](OPERATIONS.md) - Daily operations
4. [Architecture](ARCHITECTURE.md) - How it all works

### Join the Community

- **GitHub Issues**: Ask questions, report bugs
- **Discussions**: Share your experiences

---

## Troubleshooting

### Problem: Bot Won't Start

**Error**: `Missing .env file`

**Solution**:
```bash
cp .env.example .env
# Then edit .env with your credentials
```

---

### Problem: Authentication Failed

**Error**: `AuthenticationError: Invalid credentials`

**Solution**:
1. Double-check username/password in `.env`
2. If using MFA, verify `ROBINHOOD_MFA_SECRET` is correct
3. Try logging in via Robinhood app to verify credentials work

---

### Problem: No Trades Executing

**Possible causes**:
1. **Market closed**: Bot only trades during configured hours (7-10 AM EST)
2. **No signals**: Strategy conditions not met (this is normal!)
3. **Circuit breaker**: Check logs for "circuit breaker active"

**Check market status**:
```bash
curl -H "X-API-Key: my-secure-token-123" \
  http://localhost:8000/api/v1/state | jq '.market_status'
```

---

### Problem: API Not Working

**Error**: `Connection refused`

**Solution**:
1. Make sure API service is running: `bash scripts/start_api.sh`
2. Check API is on port 8000: `curl http://localhost:8000/api/v1/health/healthz`
3. Verify `BOT_API_AUTH_TOKEN` is set in `.env`

---

### Problem: Position Stuck

**Symptom**: Position not exiting

**Check**:
1. Is market still open?
2. Has stop loss been hit?
3. Has target been reached?

**Manual exit** (if needed):
```python
# Close position manually via Robinhood app
# Bot will detect and update state
```

---

## Summary

**What you learned**:
- ✅ How to install and configure the trading bot
- ✅ How to execute paper trades safely
- ✅ How to monitor performance
- ✅ How to use the API for real-time data
- ✅ How safety features protect your capital

**Key safety features you saw**:
- 🛡️ Paper trading mode (no real money)
- 🛡️ Position size limits (max 5% per trade)
- 🛡️ Daily loss limits (max 3% daily loss)
- 🛡️ Circuit breakers (automatic trading halt)
- 🛡️ Audit logging (complete trade history)

**Next goal**: Execute 10 successful paper trades before considering live trading.

---

**Need help?** Open an issue on GitHub or check the [FAQ](FAQ.md)

**Ready for more?** Read the [Operations Guide](OPERATIONS.md) for advanced monitoring and management.

---

**Last Updated**: 2025-10-26
**Difficulty**: Beginner
**Estimated Time**: 30-45 minutes
