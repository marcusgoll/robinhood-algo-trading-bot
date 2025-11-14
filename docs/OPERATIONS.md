# Operations Guide

This guide covers day-to-day operations, monitoring, and maintenance of the Robinhood Trading Bot.

---

## Table of Contents

- [Daily Operations](#daily-operations)
- [Monitoring](#monitoring)
- [Log Management](#log-management)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)
- [Backup & Recovery](#backup--recovery)
- [Alerting](#alerting)
- [Maintenance](#maintenance)
- [Emergency Procedures](#emergency-procedures)

---

## Daily Operations

### Morning Checklist (Pre-Market)

**Time**: 6:00 AM - 7:00 AM EST (before market open)

```bash
# 1. Check bot status
curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/health

# 2. Review overnight logs
tail -100 logs/trading_bot.log | grep -i error

# 3. Verify API connectivity
python -c "from src.trading_bot.auth import RobinhoodAuth; \
           from src.trading_bot.config import Config; \
           auth = RobinhoodAuth(Config.from_env_and_json()); \
           auth.login(); \
           print('✓ Connected')"

# 4. Check account status
curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/state | jq '.account'

# 5. Review configuration
cat config.json | jq '.phase_progression, .risk_management'

# 6. Start bot (if not running as service)
python -m src.trading_bot
```

**Pre-Market Checklist**:
- [ ] Bot health status: healthy
- [ ] Robinhood API connected: true
- [ ] Circuit breakers: inactive
- [ ] Emotional control: check state
- [ ] Profit protection: review yesterday's peak
- [ ] Account balance verified
- [ ] Configuration reviewed
- [ ] Logs checked for errors

---

### During Trading Hours (7:00 AM - 10:00 AM EST)

**Active Monitoring** (every 30 minutes):

```bash
# Quick status check
curl -s -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/summary | jq '{
  health: .health_status,
  positions: .position_count,
  daily_pnl: .daily_pnl,
  circuit_breaker: .circuit_breaker_status
}'

# Check for errors in last 5 minutes
tail -50 logs/errors.log

# Monitor active positions
curl -s -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/state | jq '.positions'
```

**What to Watch**:
- Position count (should match expectations)
- Daily P&L trend
- Circuit breaker status (should be inactive)
- Error rate (should be near zero)
- API health (should be connected)

**Warning Signs**:
- ⚠️ Health status: degraded or offline
- ⚠️ Circuit breaker: active
- ⚠️ Errors increasing rapidly
- ⚠️ Positions stuck (not exiting)
- ⚠️ Daily loss approaching limit

---

### Post-Market Review (After 10:00 AM EST)

**Time**: 10:30 AM - 11:00 AM EST

```bash
# 1. Get performance summary
curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/state | jq '.performance'

# 2. Review all trades
tail -50 logs/trades.log

# 3. Check for circuit breaker trips
grep -i "circuit breaker" logs/trading_bot.log

# 4. Review emotional control state
cat logs/emotional-control/state.json | jq

# 5. Check profit protection state
cat logs/profit-protection/daily-profit-state.json | jq

# 6. Generate daily report
python scripts/generate_daily_report.py  # If available
```

**Post-Market Checklist**:
- [ ] Review win rate for the day
- [ ] Check if profit target met
- [ ] Verify all positions closed (if strategy requires)
- [ ] Review max drawdown
- [ ] Check for any errors that need investigation
- [ ] Update trading journal (optional)
- [ ] Backup logs and state files

---

## Monitoring

### Key Metrics

**Health Metrics** (Real-time):
```bash
# WebSocket streaming (for dashboards)
wscat -c ws://localhost:8000/api/v1/stream \
  -H "X-API-Key: $API_TOKEN"

# Or HTTP polling
watch -n 5 'curl -s -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/metrics | jq'
```

**Performance Metrics** (Daily):
- **Win Rate**: Target ≥55%
- **Average R:R**: Target ≥2.0
- **Daily P&L**: Monitor vs. profit target
- **Max Drawdown**: Should stay <15% of peak
- **Trades Today**: Monitor for overtrading

**System Metrics**:
- **API Latency**: Target <100ms P95
- **Error Rate**: Target <1% of requests
- **Session Uptime**: Track disconnections
- **Circuit Breaker Trips**: Should be rare

---

### Log Locations

All logs are in `logs/` directory:

```
logs/
├── trading_bot.log              # General application logs
├── trades.log                   # Trade execution audit trail
├── errors.log                   # Errors and exceptions
├── startup.log                  # Startup sequence logs
│
├── health/
│   └── health-checks.jsonl      # Session health monitoring
│
├── emotional-control/
│   ├── state.json              # Current emotional control state
│   └── events-YYYY-MM-DD.jsonl # Daily event log
│
├── profit-protection/
│   ├── daily-profit-state.json # Profit protection state
│   └── events-YYYY-MM-DD.jsonl # Daily event log
│
├── performance/
│   └── metrics-YYYY-MM-DD.json # Daily performance metrics
│
└── orders.jsonl                 # Order execution audit trail
```

---

### What to Monitor

#### 1. Bot Health

```bash
# Check health endpoint
curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/health

# Expected response
{
  "status": "healthy",  # ← Should be "healthy"
  "circuit_breaker_active": false,  # ← Should be false
  "api_connected": true,  # ← Should be true
  "last_trade_timestamp": "2025-10-26T09:45:00Z",
  "last_heartbeat": "2025-10-26T10:00:00Z",
  "error_count_last_hour": 0  # ← Should be low
}
```

**Red Flags**:
- `status: "offline"` - Bot not running
- `status: "degraded"` - Issues detected
- `circuit_breaker_active: true` - Safety triggered
- `api_connected: false` - Robinhood disconnected
- `error_count_last_hour: >10` - High error rate

---

#### 2. Trading Activity

```bash
# Monitor trades in real-time
tail -f logs/trades.log

# Count trades today
grep "$(date +%Y-%m-%d)" logs/trades.log | wc -l

# Check for failed orders
grep -i "failed\|rejected" logs/trades.log
```

**What to Watch**:
- Trade frequency (are we trading too much/little?)
- Entry/exit prices (slippage acceptable?)
- Failed orders (why are they failing?)
- Stop loss hits (too tight? Too loose?)

---

#### 3. Error Monitoring

```bash
# Tail errors in real-time
tail -f logs/errors.log

# Count errors today
grep "$(date +%Y-%m-%d)" logs/errors.log | wc -l

# Group errors by type
grep "$(date +%Y-%m-%d)" logs/errors.log | \
  grep -oP '(?<=ERROR.{20})[A-Za-z]+' | sort | uniq -c
```

**Common Errors**:
- **APIError**: Robinhood API issues (retry with backoff)
- **AuthenticationError**: Session expired (re-login)
- **ValidationError**: Bad data (check market data source)
- **CircuitBreakerError**: Safety triggered (review why)

---

#### 4. Performance Tracking

```bash
# Get current P&L
curl -s -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/state | jq '.performance.daily_pnl'

# Get win rate
curl -s -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/state | jq '.performance.win_rate'

# Check current streak
curl -s -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/state | jq '.performance | {
    streak: .current_streak,
    type: .streak_type
  }'
```

---

## Log Management

### Log Rotation

Logs automatically rotate at 10MB with 5 backups:

```
trading_bot.log         # Current
trading_bot.log.1       # Previous
trading_bot.log.2
trading_bot.log.3
trading_bot.log.4
trading_bot.log.5       # Oldest
```

**Manual Rotation** (if needed):
```bash
# Archive current logs
DATE=$(date +%Y%m%d)
mkdir -p logs/archive/$DATE
cp logs/*.log logs/archive/$DATE/

# Clear current logs (bot must be stopped)
> logs/trading_bot.log
> logs/trades.log
> logs/errors.log
```

---

### Log Analysis

**Find specific errors**:
```bash
# All errors today
grep "$(date +%Y-%m-%d)" logs/errors.log

# Authentication errors
grep -i "auth" logs/errors.log

# Circuit breaker trips
grep -i "circuit breaker" logs/trading_bot.log

# Failed orders
grep -i "order.*failed" logs/trades.log
```

**Performance analysis**:
```bash
# Trades per day (last 7 days)
for i in {0..6}; do
  DATE=$(date -d "$i days ago" +%Y-%m-%d 2>/dev/null || date -v-${i}d +%Y-%m-%d)
  COUNT=$(grep "$DATE" logs/trades.log | wc -l)
  echo "$DATE: $COUNT trades"
done

# Win rate calculation
WINS=$(grep "$(date +%Y-%m-%d)" logs/trades.log | grep -c "SELL.*profit")
TOTAL=$(grep "$(date +%Y-%m-%d)" logs/trades.log | grep -c "SELL")
echo "Win rate: $(( $WINS * 100 / $TOTAL ))%"
```

---

## Common Tasks

### Restart the Bot

```bash
# Stop bot (Ctrl+C if running in terminal)
# Or if running as systemd service:
sudo systemctl stop trading-bot

# Check logs for clean shutdown
tail -20 logs/trading_bot.log

# Start bot
python -m src.trading_bot
# Or:
sudo systemctl start trading-bot

# Verify startup
curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/health
```

---

### Update Configuration

```bash
# 1. Stop bot (positions should be closed first!)
python -m src.trading_bot --dry-run  # Verify config loads

# 2. Backup current config
cp config.json config.json.backup.$(date +%Y%m%d)

# 3. Edit configuration
vim config.json

# 4. Validate new config
python validate_startup.py

# 5. Test with dry run
python -m src.trading_bot --dry-run

# 6. Restart bot with new config
python -m src.trading_bot
```

**Safe Config Changes** (can do while bot running):
- Trading hours
- Phase progression settings
- Position size limits (reduce only)

**Requires Restart** (stop bot first):
- Risk management thresholds (increase)
- Strategy parameters
- Mode changes (paper ↔ live)

---

### Check Positions

```bash
# All positions
curl -s -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/state | jq '.positions'

# Positions with unrealized P&L
curl -s -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/state | jq '.positions[] | {
    symbol,
    quantity,
    unrealized_pl,
    unrealized_pl_pct
  }'

# Count positions
curl -s -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/summary | jq '.position_count'
```

---

### Manual Intervention

**Emergency Stop All Trading**:
```python
from src.trading_bot.circuit_breakers import CircuitBreaker

breaker = CircuitBreaker()
breaker.trip("Manual emergency stop")
# Bot will stop taking new positions
```

**Reset Circuit Breaker**:
```python
from src.trading_bot.circuit_breakers import CircuitBreaker

breaker = CircuitBreaker()
if breaker.is_tripped():
    # Review why it tripped first!
    breaker.reset()
```

**Reset Emotional Control** (requires confirmation):
```bash
python -m src.trading_bot.emotional_control.cli reset
# Prompts for confirmation
```

---

## Troubleshooting

### Bot Won't Start

**Symptom**: Bot exits immediately on startup

**Diagnosis**:
```bash
# Check startup log
cat logs/startup.log

# Validate configuration
python validate_startup.py

# Check environment
python -c "from src.trading_bot.config import Config; Config.from_env_and_json()"
```

**Common Causes**:
1. Missing .env file → Copy from .env.example
2. Invalid config.json → Validate JSON syntax
3. Phase-mode conflict → Can't use live trading in experience phase
4. Missing credentials → Set ROBINHOOD_USERNAME/PASSWORD

---

### Authentication Failures

**Symptom**: "Authentication failed" or "Session expired"

**Diagnosis**:
```bash
# Check session health
grep "health_check" logs/health/health-checks.jsonl | tail -10

# Test authentication
python -c "from src.trading_bot.auth import RobinhoodAuth; \
           from src.trading_bot.config import Config; \
           auth = RobinhoodAuth(Config.from_env_and_json()); \
           auth.login()"
```

**Solutions**:
1. **Session expired**: Normal, bot auto-re-authenticates
2. **Invalid credentials**: Check .env file
3. **MFA required**: Set ROBINHOOD_MFA_SECRET or respond to prompt
4. **Device token invalid**: Delete DEVICE_TOKEN, will regenerate

---

### No Trades Executing

**Symptom**: Bot running but not taking trades

**Diagnosis**:
```bash
# Check health
curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/health

# Check circuit breakers
grep -i "circuit breaker" logs/trading_bot.log | tail -5

# Check emotional control
cat logs/emotional-control/state.json

# Check profit protection
cat logs/profit-protection/daily-profit-state.json

# Check market hours
curl -s -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/state | jq '.market_status'
```

**Common Causes**:
1. **Circuit breaker active**: Reset after reviewing logs
2. **Emotional control active**: Need 3 wins to recover or manual reset
3. **Profit protection active**: Gave back 50% of peak profit
4. **Market closed**: Bot only trades during configured hours
5. **Phase limits**: Proof phase limited to 1 trade/day
6. **No entry signals**: Strategy conditions not met

---

### High Error Rate

**Symptom**: Many errors in logs/errors.log

**Diagnosis**:
```bash
# Count errors by type
grep "$(date +%Y-%m-%d)" logs/errors.log | \
  grep -oP 'ERROR.*?(?=\s)' | sort | uniq -c | sort -rn

# Check API health
curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/health
```

**Common Causes**:
1. **API rate limiting**: Reduce polling frequency
2. **Network issues**: Check internet connection
3. **Robinhood API down**: Check Robinhood status page
4. **Invalid data**: Verify market data sources

---

### Performance Issues

**Symptom**: API slow or bot unresponsive

**Diagnosis**:
```bash
# Check API response time
time curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/summary

# Check system resources
top
df -h
```

**Solutions**:
1. **High CPU**: Check for infinite loops in logs
2. **High memory**: May need to restart bot
3. **Disk full**: Clean old logs and backups
4. **Slow API**: Check cache settings (BOT_STATE_CACHE_TTL)

---

## Performance Tuning

### Optimize API Response Times

```bash
# Current cache TTL (default: 60 seconds)
echo "BOT_STATE_CACHE_TTL=60" >> .env

# Increase cache for less frequent updates
echo "BOT_STATE_CACHE_TTL=120" >> .env  # 2 minutes

# Decrease for more real-time data
echo "BOT_STATE_CACHE_TTL=30" >> .env  # 30 seconds
```

### Reduce Log Volume

```python
# In logger.py, adjust log levels
logging.getLogger("urllib3").setLevel(logging.WARNING)  # Reduce HTTP logs
logging.getLogger("robin_stocks").setLevel(logging.INFO)  # Reduce API logs
```

### Optimize Memory Usage

```bash
# Monitor memory
watch -n 5 'ps aux | grep trading_bot | grep -v grep'

# If memory high, restart daily:
# Add to crontab:
0 4 * * * systemctl restart trading-bot
```

---

## Backup & Recovery

### Daily Backups

```bash
#!/bin/bash
# backup.sh - Run daily at midnight

DATE=$(date +%Y%m%d)
BACKUP_DIR="backups/$DATE"

mkdir -p "$BACKUP_DIR"

# Backup configuration
cp config.json "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"  # Secure this directory!

# Backup state files
cp -r logs/emotional-control "$BACKUP_DIR/"
cp -r logs/profit-protection "$BACKUP_DIR/"

# Backup logs
tar -czf "$BACKUP_DIR/logs.tar.gz" logs/*.log

# Keep only last 30 days
find backups/ -type d -mtime +30 -exec rm -rf {} \;

echo "Backup complete: $BACKUP_DIR"
```

**Add to crontab**:
```bash
0 0 * * * /path/to/backup.sh
```

---

### Disaster Recovery

**Lost Configuration**:
```bash
# Restore from backup
cp backups/YYYYMMDD/config.json ./
cp backups/YYYYMMDD/.env ./

# Or recreate from examples
cp config.example.json config.json
cp .env.example .env
# Then edit with your values
```

**Lost State Files**:
```bash
# Restore emotional control state
cp backups/YYYYMMDD/emotional-control/state.json \
   logs/emotional-control/state.json

# Restore profit protection state
cp backups/YYYYMMDD/profit-protection/daily-profit-state.json \
   logs/profit-protection/daily-profit-state.json
```

**Corrupted State** (safe defaults):
- Emotional control defaults to ACTIVE (25% sizing)
- Profit protection defaults to inactive

---

## Alerting

### Email Alerts (Example)

```python
# alerts.py
import smtplib
from email.message import EmailMessage

def send_alert(subject: str, body: str):
    """Send email alert."""
    msg = EmailMessage()
    msg['Subject'] = f"Trading Bot Alert: {subject}"
    msg['From'] = "bot@example.com"
    msg['To'] = "trader@example.com"
    msg.set_content(body)

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login("bot@example.com", "app-password")
        server.send_message(msg)

# Usage
if circuit_breaker.is_tripped():
    send_alert(
        "Circuit Breaker Triggered",
        f"Reason: {circuit_breaker.reason}\nTime: {datetime.now()}"
    )
```

### Slack/Discord Webhooks

```bash
# Send to Slack
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"🚨 Circuit breaker triggered!"}' \
  YOUR_SLACK_WEBHOOK_URL

# Send to Discord
curl -X POST -H 'Content-Type: application/json' \
  --data '{"content":"🚨 Circuit breaker triggered!"}' \
  YOUR_DISCORD_WEBHOOK_URL
```

---

## Maintenance

### Weekly Maintenance

**Every Sunday Night**:

```bash
# 1. Review weekly performance
python scripts/generate_weekly_report.py  # If available

# 2. Clean old logs
find logs/archive -type f -mtime +30 -delete

# 3. Update dependencies (if needed)
pip list --outdated

# 4. Run security scan
bandit -r src/

# 5. Backup everything
./backup.sh

# 6. Restart bot for fresh start
sudo systemctl restart trading-bot
sudo systemctl restart trading-bot-api
```

---

### Monthly Maintenance

**First Sunday of Month**:

```bash
# 1. Full system update
pip install --upgrade -r requirements.txt

# 2. Review and update config
vim config.json  # Adjust based on performance

# 3. Clean up old backups
find backups/ -type d -mtime +90 -delete

# 4. Performance review
# - Review monthly P&L
# - Adjust strategy parameters if needed
# - Review circuit breaker trips

# 5. Update credentials (if needed)
# - Rotate API keys
# - Update passwords
```

---

## Emergency Procedures

### Emergency Stop

```bash
# 1. Stop bot immediately
sudo systemctl stop trading-bot

# Or if running in terminal:
# Ctrl+C

# 2. Close all open positions (manual)
# Log into Robinhood app and close positions

# 3. Trip circuit breaker to prevent restart
python -c "from src.trading_bot.circuit_breakers import CircuitBreaker; \
           CircuitBreaker().trip('Manual emergency stop')"

# 4. Investigate issue
tail -100 logs/trading_bot.log
tail -50 logs/errors.log
```

---

### Recovery After Incident

```bash
# 1. Identify root cause
grep -A 20 "ERROR" logs/trading_bot.log | tail -50

# 2. Fix issue
# - Update config
# - Fix code bug
# - Resolve external issue

# 3. Test fix
python -m src.trading_bot --dry-run

# 4. Reset circuit breaker
python -c "from src.trading_bot.circuit_breakers import CircuitBreaker; \
           CircuitBreaker().reset()"

# 5. Restart bot
sudo systemctl start trading-bot

# 6. Monitor closely
tail -f logs/trading_bot.log
```

---

## Support

- **Documentation**: See [README.md](../README.md) and other docs in `docs/`
- **Issues**: [GitHub Issues](https://github.com/marcusgoll/robinhood-algo-trading-bot/issues)
- **API Reference**: [docs/API.md](API.md)
- **Architecture**: [docs/ARCHITECTURE.md](ARCHITECTURE.md)

---

**Last Updated**: 2025-10-26
**Version**: v1.8.0
