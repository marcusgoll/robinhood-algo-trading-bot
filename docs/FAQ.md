# Frequently Asked Questions (FAQ)

Common questions about the Robinhood Trading Bot.

---

## Table of Contents

- [General Questions](#general-questions)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Trading](#trading)
- [Safety & Risk Management](#safety--risk-management)
- [Performance](#performance)
- [API & Monitoring](#api--monitoring)
- [Troubleshooting](#troubleshooting)
- [Legal & Compliance](#legal--compliance)

---

## General Questions

### What is this trading bot?

The Robinhood Trading Bot is a Python-based algorithmic trading system that automatically executes trades on Robinhood based on technical analysis strategies. It's designed with safety-first principles and includes multiple risk management features.

### Is this free to use?

Yes, the bot is open-source and free to use. However, you'll need:
- A Robinhood account (free)
- Optional: Polygon.io subscription for order flow data ($99/month)

### Is this safe?

The bot includes multiple safety features:
- Paper trading mode (no real money)
- Circuit breakers (automatic trading halt)
- Position size limits (max 5% per position)
- Daily loss limits (auto-stop at 3% loss)
- Emotional control (reduces sizing after losses)
- Comprehensive audit logging

**However**: You are responsible for all trading decisions and should thoroughly test in paper trading mode first.

### Can I make money with this?

**There are no guarantees**. Past performance doesn't predict future results. Always:
- Start with paper trading
- Test thoroughly before using real money
- Never invest more than you can afford to lose
- Understand the risks of algorithmic trading

### What strategies does it use?

Current strategies include:
- Bull Flag Breakout
- Momentum Detection
- VWAP Mean Reversion
- Support/Resistance Zone Trading
- Order Flow Analysis (Level 2)

See [README.md](../README.md) for detailed strategy descriptions.

---

## Installation & Setup

### What are the system requirements?

- **Python**: 3.11 or higher
- **OS**: Windows, macOS, or Linux
- **RAM**: 2GB minimum (4GB recommended)
- **Disk**: 1GB for bot + logs
- **Internet**: Stable connection required

### Do I need a Robinhood account with money in it?

**For paper trading**: No real money needed
**For live trading**: Yes, but start small (recommend $1,000+)

### How do I get my Robinhood credentials?

Use your regular Robinhood login (email + password). For MFA:
1. Enable 2FA in Robinhood app
2. During setup, save the secret key (16 characters)
3. Add to `ROBINHOOD_MFA_SECRET` in `.env`

### Can I run this on a Raspberry Pi?

Yes, but performance may be limited. Minimum: Raspberry Pi 4 with 4GB RAM.

---

## Configuration

### What's the difference between .env and config.json?

- **.env**: Sensitive credentials (never commit to git)
  - Robinhood username/password
  - API keys
  - MFA secrets

- **config.json**: Trading parameters (gitignored but shareable structure)
  - Position sizes
  - Risk limits
  - Trading hours
  - Strategy settings

### What does "phase progression" mean?

A safety system that gradually increases risk as you prove profitability:

1. **Experience** (paper only): Learn the system
2. **Proof** (1 trade/day live): Prove it works with real money
3. **Trial** (unlimited live): Build confidence
4. **Scaling** (increasing size): Gradually scale up

### How do I change trading hours?

Edit `config.json`:
```json
"trading_hours": {
  "start": "07:00",
  "end": "10:00",
  "timezone": "America/New_York"
}
```

**Note**: Times are in 24-hour format (EST timezone).

### Can I trade all day?

The bot is designed for the first 3 hours (7-10 AM EST) when volatility is highest. Trading all day increases risk and is not recommended.

---

## Trading

### Why isn't the bot trading?

Common reasons:
1. **Market closed**: Only trades during configured hours (7-10 AM EST default)
2. **No signals**: Strategy conditions not met (normal!)
3. **Circuit breaker active**: Safety feature triggered (check logs)
4. **Emotional control active**: Needs 3 wins to recover or manual reset
5. **Profit protection active**: Gave back 50% of daily peak profit
6. **Phase limits**: Proof phase limited to 1 trade/day

**Check status**:
```bash
curl -H "X-API-Key: $TOKEN" http://localhost:8000/api/v1/summary
```

### How many trades per day should I expect?

Depends on market conditions and strategy:
- **Typical**: 0-3 trades per day
- **Active days**: 3-5 trades
- **Slow days**: 0-1 trades

**Quality over quantity**. The bot waits for high-probability setups.

### Can I manually place trades?

The bot is fully automated. Manual intervention requires:
1. Stopping the bot
2. Placing trade via Robinhood app
3. Restarting the bot (will detect existing position)

**Not recommended** - can interfere with bot logic.

### What happens if my position is still open at end of trading hours?

Depends on strategy configuration. Most strategies will:
1. Exit at market close (default)
2. Hold overnight if configured
3. Use tighter stops for overnight positions

### How do I close all positions immediately?

**Emergency shutdown**:
```bash
# Stop bot
sudo systemctl stop trading-bot

# Close positions manually via Robinhood app
```

---

## Safety & Risk Management

### What are circuit breakers?

Automatic safety mechanisms that halt trading when:
1. **Daily loss** exceeds 3% (default)
2. **Consecutive losses** reach 3 (default)
3. **Manual trigger** (emergency stop)

**Recovery**: Review logs, fix issue, manually reset circuit breaker.

### What is "emotional control"?

A feature that reduces position sizing to 25% after:
- Single loss ≥3% of account, OR
- 3 consecutive losses

**Recovery**: Requires 3 consecutive wins OR manual admin reset.

**Purpose**: Prevents revenge trading and protects capital during drawdowns.

### What is "profit protection"?

Automatically blocks new entries when you've given back 50% of your daily peak profit.

**Example**:
- Peak profit: $400
- Current profit: $200 (50% drawdown from peak)
- Protection activates: No new trades, can still exit

### Can I disable safety features?

**Not recommended**. Safety features are designed to protect your capital. If you must:

```bash
# Disable emotional control
EMOTIONAL_CONTROL_ENABLED=false  # in .env

# Increase circuit breaker limits
# Edit config.json risk_management section
```

**Warning**: Disabling safety features significantly increases risk.

### What's the maximum position size?

Default: **5% of account per position**

**Example**: $10,000 account → max $500 position

Configure in `config.json`:
```json
"risk_management": {
  "max_position_pct": 5.0  // 5%
}
```

---

## Performance

### What win rate should I expect?

**Target**: ≥55% win rate with 2:1 risk:reward

**Reality**: Performance varies by:
- Market conditions
- Strategy used
- Risk management settings
- Account size

**Backtest first** to validate expected performance.

### How do I track performance?

**Via API**:
```bash
curl -H "X-API-Key: $TOKEN" \
  http://localhost:8000/api/v1/state | jq '.performance'
```

**Via logs**:
```bash
grep "SELL" logs/trades.log
```

**Metrics tracked**:
- Win rate
- Average risk:reward
- Daily P&L
- Max drawdown
- Streak (consecutive wins/losses)

### What's a good Sharpe ratio?

**Sharpe Ratio** measures risk-adjusted returns:
- **<1.0**: Poor (high risk for returns)
- **1.0-2.0**: Good (target range)
- **>2.0**: Excellent (rare)

Run backtests to calculate Sharpe ratio before live trading.

### Why am I losing money?

Common causes:
1. **Market conditions changed**: Strategy not suited for current market
2. **Position sizing too large**: Reduce max_position_pct
3. **Stops too tight**: Getting stopped out prematurely
4. **Overtrading**: Too many trades, too much slippage
5. **Not following rules**: Manual intervention interfering

**Action**: Stop live trading, return to paper trading, review logs.

---

## API & Monitoring

### What's the API for?

The Trading Bot API (v1.8.0+) enables:
- Real-time monitoring via HTTP/WebSocket
- Integration with dashboards
- Natural language queries
- Workflow automation
- Remote bot management

See [API Documentation](API.md) for details.

### How do I access the API?

```bash
# 1. Set API token in .env
echo "BOT_API_AUTH_TOKEN=your-secret-token" >> .env

# 2. Start API service
bash scripts/start_api.sh

# 3. Access Swagger UI
open http://localhost:8000/api/docs

# 4. Make requests
curl -H "X-API-Key: your-secret-token" \
  http://localhost:8000/api/v1/summary
```

### Can I access the API remotely?

Yes, but **secure it first**:
1. Set strong `BOT_API_AUTH_TOKEN` (32+ characters)
2. Use HTTPS (nginx + certbot)
3. Configure firewall (only allow your IP)
4. Set CORS to specific domains (not `*`)

See [Deployment Guide](DEPLOYMENT.md) for production setup.

### What's the natural language CLI?

Execute commands in plain English:

```bash
python -m src.trading_bot.cli.nl_commands "show today's performance"
python -m src.trading_bot.cli.nl_commands "check bot health"
python -m src.trading_bot.cli.nl_commands "what positions are open?"
```

The bot extracts intent and calls appropriate API.

---

## Troubleshooting

### "Authentication failed" error

**Causes**:
1. Wrong username/password in `.env`
2. MFA secret incorrect or missing
3. Robinhood requires 2FA approval

**Solution**:
```bash
# 1. Verify credentials
cat .env | grep ROBINHOOD_

# 2. Test login manually
python -c "from src.trading_bot.auth import RobinhoodAuth; \
           from src.trading_bot.config import Config; \
           RobinhoodAuth(Config.from_env_and_json()).login()"

# 3. If MFA prompt appears, approve on phone
```

### "Circuit breaker tripped" - how to reset?

**Step 1**: Investigate why it tripped
```bash
grep "circuit breaker" logs/trading_bot.log | tail -10
```

**Step 2**: Fix the issue (e.g., bad config, market volatility)

**Step 3**: Reset
```python
from src.trading_bot.circuit_breakers import CircuitBreaker

breaker = CircuitBreaker()
breaker.reset()
```

### Bot crashes on startup

**Check**:
1. Log files: `cat logs/startup.log`
2. Configuration: `python validate_startup.py`
3. Dependencies: `pip install -r requirements.txt`

**Common causes**:
- Missing .env file
- Invalid JSON in config.json
- Phase-mode conflict (can't use live in experience phase)

### Positions not showing in API

**Possible causes**:
1. Cache stale: Add `Cache-Control: no-cache` header
2. Bot not running: Check `systemctl status trading-bot`
3. No active positions: Check `logs/trades.log`

**Solution**:
```bash
curl -H "X-API-Key: $TOKEN" \
     -H "Cache-Control: no-cache" \
     http://localhost:8000/api/v1/state | jq '.positions'
```

### High memory usage

**Check usage**:
```bash
ps aux | grep trading_bot
```

**If high**:
1. Restart bot: `sudo systemctl restart trading-bot`
2. Check for memory leaks in logs
3. Reduce cache TTL: `BOT_STATE_CACHE_TTL=30`

**Prevention**: Schedule daily restart via cron.

---

## Legal & Compliance

### Is algorithmic trading legal?

**Yes**, but with restrictions:
- Must comply with SEC/FINRA regulations
- Pattern Day Trading rule (4+ day trades in 5 days requires $25k)
- No market manipulation
- Proper tax reporting required

**This bot is for personal use only, not financial advice.**

### Do I need to report taxes?

**Yes**. All trading activity must be reported:
- Short-term capital gains (held <1 year)
- Tax forms provided by Robinhood (1099)
- Consult a tax professional

### What about Pattern Day Trading (PDT) rule?

**PDT Rule**: If you make 4+ day trades in 5 rolling business days, you need $25k in your account.

**The bot**:
- Tracks day trade count
- Will block trades if PDT limit approached (configurable)
- Default: Max 3 day trades per week to stay under limit

**Configure in config.json**:
```json
"risk_management": {
  "max_day_trades_per_week": 3
}
```

### Can I use this for clients?

**No**. This bot is for personal use only. Managing others' money requires:
- Investment adviser registration (SEC)
- Series 65/66 license
- Proper legal structure (RIA)

**Violation of securities laws can result in fines and criminal prosecution.**

### What's Robinhood's policy on bots?

Robinhood's Terms of Service prohibit automated trading via their official API. However:
- This bot uses the same API that the mobile app uses
- Many users run similar bots without issue
- Robinhood may change their policy at any time

**Use at your own risk**. Robinhood could:
- Revoke API access
- Close your account
- Change API endpoints

### Am I responsible for bot actions?

**Yes, completely**. You are responsible for:
- All trades executed
- Tax reporting
- Compliance with regulations
- Losses incurred

**This software is provided "AS IS" without warranty.**

---

## Still Have Questions?

- **Documentation**: See other docs in `docs/` directory
- **GitHub Issues**: [Open an issue](https://github.com/marcusgoll/robinhood-algo-trading-bot/issues)
- **Tutorial**: [Beginner Tutorial](TUTORIAL.md)
- **API Reference**: [API Documentation](API.md)

---

**Last Updated**: 2025-10-26
**Version**: v1.8.0
