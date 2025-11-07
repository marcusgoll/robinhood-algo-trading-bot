# Trading Bot Monitoring Guide

**Purpose**: Comprehensive monitoring for multi-week paper trading test run

**Status**: Bot deployed and operational on Hetzner (65.109.177.235)

---

## Quick Health Check

**1-minute verification that bot is alive and functioning:**

```bash
# Check bot container is running
ssh hetzner "docker ps | grep trading-bot"

# Check last heartbeat (should be within last 5 minutes)
ssh hetzner "docker logs trading-bot 2>&1 | grep HEARTBEAT | tail -1"

# Check recent momentum scans (should be within last 15 minutes during market hours)
ssh hetzner "docker logs trading-bot 2>&1 | grep 'Momentum scan complete' | tail -3"
```

**Expected output**:
- Container STATUS: "Up X hours"
- Heartbeat: Recent timestamp with `Market=OPEN` or `CLOSED`
- Scan: Shows signal count and top symbol

---

## Monitoring Capabilities

### 1. Heartbeat Logging (Every 5 Minutes)

**Purpose**: Proves bot is alive and shows current state

**How to check**:
```bash
# View last 5 heartbeats
ssh hetzner "docker logs trading-bot 2>&1 | grep HEARTBEAT | tail -5"
```

**Sample output**:
```
2025-10-28 19:13:44 UTC | INFO | 💓 HEARTBEAT | Status=running | Market=CLOSED | Positions=0 | LastScan=0s_ago
```

**What to look for**:
- Timestamp should be recent (within 5 minutes)
- Status=running (not stopped/error)
- Market=OPEN during 9:30-16:00 ET
- LastScan should update every 15 minutes during market hours

### 2. Momentum Scanning (Every 15 Minutes During Market Hours)

**Purpose**: Verifies signal detection system is working

**How to check**:
```bash
# View last 10 scans
ssh hetzner "docker logs trading-bot 2>&1 | grep 'Momentum scan' | tail -10"
```

**Sample output**:
```
2025-10-28 19:13:44 UTC | INFO | Momentum scan complete | Signals=1 | TopSymbol=MSFT | Score=20.32
```

**What to look for**:
- Scans occurring every 15 minutes (900 seconds) during market hours
- Signal count > 0 indicates active opportunities detected
- TopSymbol and Score show highest-ranked opportunity

### 3. Scan Activity Logs (Audit Trail)

**Purpose**: JSONL files with complete scan details for analysis

**Location**: `/opt/trading-bot/logs/scan_activity_YYYY-MM-DD.jsonl`

**How to check**:
```bash
# View today's scan activity (last 3 scans)
ssh hetzner "cat /opt/trading-bot/logs/scan_activity_$(date +%Y-%m-%d).jsonl | tail -3 | jq ."
```

**Sample output**:
```json
{
  "timestamp": "2025-10-28T19:13:44.803851",
  "scan_count": 1,
  "signals": [
    {
      "symbol": "MSFT",
      "strength": 20.32,
      "signal_type": "composite",
      "detected_at": "2025-10-28T19:13:43.885128+00:00",
      "details": {
        "pattern_type": "bull_flag",
        "pole_gain_pct": 9.03,
        "flag_range_pct": 3.82,
        "breakout_price": 537.3,
        "price_target": 583.315,
        "pattern_valid": true
      }
    }
  ]
}
```

**What to look for**:
- File exists and grows daily
- Each entry contains complete signal details
- Pattern detection working (bull_flag, etc.)

### 4. Trading Activity Logs

**Purpose**: Monitor order execution and trading decisions

**How to check**:
```bash
# View main trading log (last 50 lines)
ssh hetzner "docker logs trading-bot --tail 50 2>&1"

# Search for specific events
ssh hetzner "docker logs trading-bot 2>&1 | grep -E '(ORDER|TRADE|POSITION)' | tail -20"
```

**What to look for**:
- Order submissions (should show [PAPER] prefix in paper mode)
- Position entries/exits
- Stop loss triggers
- Circuit breaker activations

### 5. Configuration Verification

**Purpose**: Confirm bot is running with correct settings

**How to check**:
```bash
# View current config
ssh hetzner "cat /opt/trading-bot/config.json"

# Check startup banner
ssh hetzner "docker logs trading-bot 2>&1 | grep -A 10 'Robinhood Trading Bot'"
```

**What to verify**:
- `mode: "paper"` (not "live")
- Trading hours: `09:30` to `16:00` ET
- Risk parameters: max_position_pct, max_daily_loss_pct, etc.
- Circuit breaker: Active

---

## Monitoring Frequency Recommendations

### Daily Checks (5 minutes)

**Morning (before market open - 9:00 AM ET)**:
```bash
# Verify bot is running and ready
ssh hetzner "docker ps && docker logs trading-bot --tail 20 2>&1"
```

**Mid-day (12:00 PM ET)**:
```bash
# Check scan activity and any position entries
ssh hetzner "docker logs trading-bot 2>&1 | grep -E '(Momentum scan|POSITION|ORDER)' | tail -20"
```

**After market close (4:30 PM ET)**:
```bash
# Review day's activity
ssh hetzner "cat /opt/trading-bot/logs/scan_activity_$(date +%Y-%m-%d).jsonl | jq '.scan_count' | paste -sd+ | bc"
echo "Total scans today: ^"

# Check for any errors
ssh hetzner "docker logs trading-bot 2>&1 | grep -E '(ERROR|CRITICAL)' | tail -20"
```

### Weekly Checks (15 minutes)

**Every Friday after market close**:

1. **Archive logs**:
```bash
ssh hetzner "cd /opt/trading-bot/logs && tar -czf archive_$(date +%Y-%m-%d).tar.gz scan_activity_*.jsonl trading_bot.log"
```

2. **Check storage**:
```bash
ssh hetzner "df -h /opt/trading-bot && du -sh /opt/trading-bot/logs"
```

3. **Review error patterns**:
```bash
ssh hetzner "docker logs trading-bot 2>&1 | grep -E 'ERROR|WARNING' | sort | uniq -c | sort -rn | head -20"
```

4. **Verify Docker health**:
```bash
ssh hetzner "docker compose ps && docker stats --no-stream"
```

---

## Troubleshooting

### Issue: Heartbeat stopped

**Symptom**: No heartbeat in logs for > 10 minutes

**Check**:
```bash
ssh hetzner "docker ps -a | grep trading-bot"
```

**If container stopped**:
```bash
ssh hetzner "cd /opt/trading-bot && docker compose up -d"
```

**If container running but frozen**:
```bash
ssh hetzner "cd /opt/trading-bot && docker compose restart trading-bot"
```

### Issue: No momentum scans during market hours

**Symptom**: No "Momentum scan complete" logs between 9:30-16:00 ET

**Check trading hours config**:
```bash
ssh hetzner "cat /opt/trading-bot/config.json | jq '.trading.hours'"
```

**Expected**:
```json
{
  "start_time": "09:30",
  "end_time": "16:00",
  "timezone": "America/New_York"
}
```

**If wrong, update and restart**:
```bash
ssh hetzner "cd /opt/trading-bot && docker compose restart trading-bot"
```

### Issue: Errors in logs

**Check error details**:
```bash
ssh hetzner "docker logs trading-bot 2>&1 | grep -A 5 'ERROR' | tail -30"
```

**Common errors**:

1. **API rate limits**: Wait 1 minute, should recover automatically
2. **Network timeouts**: Temporary, should retry automatically
3. **Authentication failures**: Check Robinhood credentials in .env (not needed for paper mode)

### Issue: Container won't start

**View full startup logs**:
```bash
ssh hetzner "docker logs trading-bot 2>&1 | head -100"
```

**Rebuild if needed**:
```bash
ssh hetzner "cd /opt/trading-bot && git pull && docker compose down && docker compose build --no-cache && docker compose up -d"
```

---

## Data Collection for Analysis

### Export scan activity for analysis

**Download last week's scans**:
```bash
scp hetzner:/opt/trading-bot/logs/scan_activity_*.jsonl ./analysis/
```

**Count total signals by symbol**:
```bash
ssh hetzner "cat /opt/trading-bot/logs/scan_activity_*.jsonl | jq -r '.signals[].symbol' | sort | uniq -c | sort -rn"
```

**Find high-strength signals (>50)**:
```bash
ssh hetzner "cat /opt/trading-bot/logs/scan_activity_*.jsonl | jq -c '.signals[] | select(.strength > 50)'"
```

### Export trading activity

**Download logs**:
```bash
ssh hetzner "docker logs trading-bot 2>&1" > trading_bot_full.log
```

**Filter position entries**:
```bash
grep "POSITION ENTRY" trading_bot_full.log
```

---

## Telegram Monitoring (Optional)

If Telegram is configured in `.env`:

**Bot commands**:
- `/status` - Current bot state
- `/positions` - Active positions
- `/scan` - Force momentum scan
- `/help` - Command list

**Notifications sent for**:
- Position entries/exits
- Stop loss triggers
- Circuit breaker activations
- Critical errors

---

## Paper Trading Safety Checks

**Before going live, verify**:

1. **No real Robinhood API calls**:
```bash
ssh hetzner "docker logs trading-bot 2>&1 | grep -i 'robin_stocks' | grep -v 'PAPER'"
# Should be empty or only show paper mode logs
```

2. **All orders show [PAPER] prefix**:
```bash
ssh hetzner "docker logs trading-bot 2>&1 | grep 'ORDER' | grep -v '\[PAPER\]'"
# Should be empty
```

3. **Config mode is paper**:
```bash
ssh hetzner "cat /opt/trading-bot/config.json | jq '.trading.mode'"
# Should output: "paper"
```

---

## Current Status Summary

**Deployment**:
- Server: Hetzner (65.109.177.235)
- Container: trading-bot (running)
- Mode: Paper trading (no real trades)

**Configuration**:
- Trading hours: 9:30 AM - 4:00 PM ET
- Heartbeat interval: 5 minutes
- Scan interval: 15 minutes
- Circuit breaker: Active

**Verified Working**:
- ✅ Trading loop running
- ✅ Heartbeat logging every 5 minutes
- ✅ Momentum scanning every 15 minutes
- ✅ Scan activity JSONL logs created
- ✅ Paper trading isolation (no Robinhood API calls)
- ✅ Bull flag pattern detection working (MSFT detected with score 20.32)

**Next Momentum Scan**: Within 15 minutes of market open tomorrow (9:45 AM ET)

---

## Support

**Logs location**: `/opt/trading-bot/logs/`
**Config file**: `/opt/trading-bot/config.json`
**Docker compose**: `/opt/trading-bot/docker-compose.yml`

**Useful commands**:
```bash
# Full status check
ssh hetzner "cd /opt/trading-bot && docker compose ps && docker logs trading-bot --tail 20 2>&1"

# Restart if needed
ssh hetzner "cd /opt/trading-bot && docker compose restart"

# Update code and redeploy
ssh hetzner "cd /opt/trading-bot && git pull && docker compose down && docker compose build && docker compose up -d"
```
