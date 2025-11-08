# 24/7 Crypto Trading Setup Guide

## Overview

This guide covers enabling 24/7 cryptocurrency paper trading via Alpaca alongside existing stock trading.

**Key Features:**
- 24/7 trading (no market hours restrictions)
- Parallel to stock trading (both run in same container)
- Aggressive monitoring (screen: 2hr, positions: 5min)
- 8 crypto symbols (BTC, ETH, LTC, BCH, LINK, UNI, AVAX, MATIC)
- Separate risk parameters (5% stops vs 2% for stocks)

## Architecture

**Unified Container Deployment:**
- Stock Orchestrator: Time-based (6:30am-4pm EST workflows)
- Crypto Orchestrator: Interval-based (every 2hr/5min)
- Shared Claude Manager: Combined LLM budget tracking
- Shared Telegram: Unified notifications

**Scheduling:**
- Stocks: Market hours only (weekdays 6:30am-4pm EST)
- Crypto: 24/7/365 (every 2 hours screening, every 5 minutes monitoring)

## Configuration

### 1. Update `.env`

Add crypto configuration to your `.env` file:

```bash
# Crypto Trading Configuration
CRYPTO_ENABLED=true
CRYPTO_MODE=paper
CRYPTO_SYMBOLS=BTC/USD,ETH/USD,LTC/USD,BCH/USD,LINK/USD,UNI/USD,AVAX/USD,MATIC/USD
CRYPTO_SCREENING_INTERVAL_HOURS=2
CRYPTO_MONITORING_INTERVAL_MINUTES=5
CRYPTO_STOP_LOSS_PCT=5.0
CRYPTO_MAX_POSITION_PCT=3.0
```

**Important:** `CRYPTO_MODE=paper` uses Alpaca paper trading (no real money).

### 2. Update `config.json`

Add crypto section to your `config.json`:

```json
{
  "trading": {
    "mode": "paper",
    "hours": {
      "start_time": "07:00",
      "end_time": "10:00",
      "timezone": "America/New_York"
    }
  },
  "crypto": {
    "enabled": true,
    "mode": "paper",
    "symbols": [
      "BTC/USD",
      "ETH/USD",
      "LTC/USD",
      "BCH/USD",
      "LINK/USD",
      "UNI/USD",
      "AVAX/USD",
      "MATIC/USD"
    ],
    "scheduling": {
      "screening_interval_hours": 2,
      "monitoring_interval_minutes": 5,
      "rebalance_interval_hours": 24
    },
    "risk_management": {
      "max_position_pct": 3.0,
      "max_daily_loss_pct": 5.0,
      "stop_loss_pct": 5.0,
      "risk_reward_ratio": 2.0,
      "position_size_usd": 100.0
    },
    "technical_indicators": {
      "rsi_overbought": 75,
      "rsi_oversold": 30,
      "min_volume_ratio": 150.0
    },
    "llm_budget_pct": 0.5
  },
  "risk_management": {
    "max_position_pct": 5.0,
    "max_daily_loss_pct": 3.0,
    "stop_loss_pct": 2.0
  }
}
```

### 3. Verify Alpaca Credentials

Ensure your `.env` has Alpaca API credentials (works for both stocks and crypto):

```bash
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

## Expected Behavior

After setup, you'll receive **Telegram notifications** for:

**Stocks (Market Hours Only):**
- 📊 6:30am EST: Pre-market screening
- 🔔 9:30am EST: Market open trades
- 📈 During day: Position updates
- 📊 4:00pm EST: Daily summary

**Crypto (24/7):**
- 🪙 Every 2 hours: Crypto screening (12 times/day)
- 🔍 Every 5 minutes: Position monitoring (if positions active)
- 💰 Daily: Portfolio rebalancing

## LLM Budget Impact

**WARNING:** Aggressive crypto monitoring = HIGH LLM usage

**Estimated Daily Calls:**
- Stocks: ~10-15 calls/day
- Crypto: ~300 calls/day
  - Screening: 12/day (every 2hr)
  - Monitoring: 288/day (every 5min, if positions)

**Recommended Budget:** Increase from $5/day to $10-15/day

Update in `src/trading_bot/orchestrator/trading_orchestrator.py`:

```python
llm_config = LLMConfig(
    daily_budget_usd=15.0,  # Increased for crypto
    model=LLMModel.HAIKU,
    ...
)
```

## Risk Parameters Comparison

| Parameter | Stocks | Crypto | Reason |
|-----------|--------|--------|--------|
| Stop Loss | 2% | 5% | Higher crypto volatility |
| Max Position | 5% | 3% | More conservative crypto sizing |
| Position Size | 100 shares | $100 | Fractional crypto trading |

## Testing Locally

Before deploying to VPS, test locally:

```bash
# 1. Ensure configs updated (.env + config.json)

# 2. Test crypto data fetching
python -c "from trading_bot.market_data.crypto_service import CryptoDataService; \
           svc = CryptoDataService(); \
           print(svc.get_current_price('BTC/USD'))"

# 3. Run orchestrator locally (will start both stock + crypto)
python -m trading_bot orchestrator --orchestrator-mode paper

# 4. Watch logs for crypto screening
tail -f logs/orchestrator/orchestrator.log | grep -i crypto
```

**Expected Output:**
```
CryptoOrchestrator initialized in paper mode
Symbols: BTC/USD, ETH/USD, LTC/USD, BCH/USD, LINK/USD, UNI/USD, AVAX/USD, MATIC/USD
Screening: every 2hr
Monitoring: every 5min
```

## Deployment to VPS

Once tested locally:

```bash
# 1. Commit crypto integration
git add .
git commit -m "feat: add 24/7 crypto trading via Alpaca paper"
git push

# 2. SSH to VPS
ssh hetzner

# 3. Update and rebuild
cd /opt/trading-bot
git pull
docker stop trading-bot-standalone
docker rm trading-bot-standalone
docker build -t trading-bot-standalone:latest -f Dockerfile .

# 4. Deploy with crypto enabled
docker run -d \
  --name trading-bot-standalone \
  --restart unless-stopped \
  -v /opt/trading-bot/logs:/app/logs \
  -v /opt/trading-bot/.env:/app/.env \
  -v /opt/trading-bot/config.json:/app/config.json \
  trading-bot-standalone:latest

# 5. Verify both orchestrators running
docker logs trading-bot-standalone 2>&1 | grep -i "orchestrator initialized"
```

**Expected Output:**
```
TradingOrchestrator initialized in paper mode
CryptoOrchestrator initialized in paper mode
```

## Monitoring

**Check Status:**
```bash
# VPS logs
ssh hetzner 'docker logs trading-bot-standalone --tail 50'

# Look for crypto workflows
ssh hetzner 'docker logs trading-bot-standalone 2>&1 | grep -i "crypto screening"'
```

**Telegram Notifications:**
You should receive notifications approximately every 2 hours when crypto screening runs.

## Troubleshooting

### No Crypto Notifications

**Check:**
1. Is `CRYPTO_ENABLED=true` in `.env`?
2. Are Alpaca credentials valid?
3. Is orchestrator running? `docker ps | grep trading-bot`
4. Check logs: `docker logs trading-bot-standalone | grep -i error`

### High LLM Costs

If budget exceeded:
1. Reduce monitoring frequency: `CRYPTO_MONITORING_INTERVAL_MINUTES=15` (instead of 5)
2. Reduce screening frequency: `CRYPTO_SCREENING_INTERVAL_HOURS=4` (instead of 2)
3. Disable crypto temporarily: `CRYPTO_ENABLED=false`

### Crypto Data Errors

If "No quote data for BTC/USD":
1. Verify Alpaca credentials in `.env`
2. Check Alpaca paper trading is enabled
3. Test manually: `python -c "from trading_bot.market_data.crypto_service import CryptoDataService; print(CryptoDataService().get_latest_quote('BTC/USD'))"`

## Disabling Crypto

To disable crypto trading without removing code:

**Option 1: Environment Variable**
```bash
# In .env
CRYPTO_ENABLED=false
```

**Option 2: Config File**
```json
{
  "crypto": {
    "enabled": false
  }
}
```

Restart container for changes to take effect.

## Next Steps

1. ✅ Configure `.env` and `config.json`
2. ✅ Test locally
3. ✅ Deploy to VPS
4. ✅ Monitor for 24 hours
5. ⏳ Adjust intervals based on LLM budget usage
6. ⏳ Review crypto trading performance weekly

## Support

For issues, check:
- Logs: `/opt/trading-bot/logs/orchestrator/orchestrator.log`
- Crypto errors: `/opt/trading-bot/logs/llm/llm-errors.jsonl`
- This guide: `CRYPTO_SETUP.md`
- Deployment guide: `DEPLOYMENT.md`
