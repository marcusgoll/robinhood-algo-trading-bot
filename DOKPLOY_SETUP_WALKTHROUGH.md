# Dokploy RH Bot Project Setup Walkthrough

**Date**: 2025-10-27
**Project**: RH Bot (Trading Bot Deployment)
**Dashboard**: http://178.156.129.179:9100
**Status**: Ready for configuration

---

## Overview

This guide walks you through setting up your trading bot project in Dokploy with:
- Trading Bot Service (main 24/7 trading)
- API Service (monitoring/control)
- Redis Service (caching)
- Persistent Storage (logs, config, session)
- Telegram Notifications (real-time alerts)

---

## Prerequisites

✅ Dokploy dashboard accessible at `http://178.156.129.179:9100`
✅ RH Bot project created in Dokploy
✅ GitHub repository: `robinhood-algo-trading-bot`
✅ Environment variables prepared (see Section 1)
✅ Telegram bot configured (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

---

## Part 1: Prepare Environment Variables

Before creating services, gather these credentials:

### Required Credentials

```bash
# Robinhood Trading Account
ROBINHOOD_USERNAME=<your-robinhood-email>
ROBINHOOD_PASSWORD=<your-robinhood-password>
ROBINHOOD_ACCOUNT_ID=<your-account-id>

# Telegram Notifications (Feature #030)
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=<your-bot-token-from-botfather>
TELEGRAM_CHAT_ID=<your-numeric-chat-id>

# Optional
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
PYTHONPATH=/app
```

**Keep these handy** - you'll paste them into Dokploy in Section 2.

---

## Part 2: Access Dokploy Dashboard

### Step 1: Login to Dashboard

1. **Open browser**: `http://178.156.129.179:9100`
2. **Enter credentials** (set during Dokploy installation)
3. **Click Login**

You should see the Dokploy dashboard with your "RH Bot" project visible.

### Step 2: Navigate to Your Project

1. **Click "RH Bot"** project card
2. **You should see**:
   - Project name: RH Bot
   - Branch: (should be `main` or your default branch)
   - Repository status
   - Services section (currently empty)

---

## Part 3: Create Trading Bot Service

### Step 3.1: Add New Service

1. **In RH Bot project**, click **"Add Service"** or **"New Service"**
2. **Choose Service Type**:
   - Select: **Docker** (not Compose, individual service)
   - Or: **GitHub** (Dokploy will auto-build from Dockerfile)

### Step 3.2: Configure Service

**Basic Settings:**
- **Service Name**: `trading-bot`
- **Description**: `Trading bot with Telegram notifications`
- **Build Type**: `Docker` (use Dockerfile)
- **Dockerfile Path**: `./Dockerfile`

**Container Settings:**
- **Image Name**: (auto-generated)
- **Port Mapping**:
  - Do NOT expose external port (internal only)
  - No public access needed
- **Restart Policy**: `Always`

**Commands:**
- **Override CMD**: Leave empty (use default from Dockerfile)
- **or Override Entrypoint**: Leave empty

### Step 3.3: Add Environment Variables

Click **"Environment Variables"** or **"Add Env Vars"**

**Paste all these variables:**

```
PYTHONUNBUFFERED=1
PYTHONPATH=/app
TRADING_BOT_ENABLED=true

ROBINHOOD_USERNAME=<your-username>
ROBINHOOD_PASSWORD=<your-password>
ROBINHOOD_ACCOUNT_ID=<your-account-id>

TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=<your-bot-token>
TELEGRAM_CHAT_ID=<your-chat-id>

REDIS_URL=redis://redis:6379/0
LOG_LEVEL=INFO
```

**Tips:**
- Paste each line individually, or use bulk import if available
- Click "Save" after each variable (or batch save)
- Do NOT include quotes around values
- Do NOT commit these to Git (only in Dokploy)

### Step 3.4: Configure Storage Volumes

Click **"Volumes"** or **"Persistent Storage"**

**Add these mount points:**

| Container Path | Host Path | Type | Notes |
|---|---|---|---|
| `/app/logs` | `/data/trading-bot/logs` | ReadWrite | Persistent logs |
| `/app/config.json` | `/data/trading-bot/config.json` | ReadWrite | Config file |
| `/app/.robinhood.pickle` | `/data/trading-bot/.robinhood.pickle` | ReadWrite | Session token |

**Actions:**
- Click "Add Volume" for each entry
- Container Path: (left column in Dokploy)
- Host Path: (right column or Mount Path in Dokploy)
- Select ReadWrite for all

### Step 3.5: Health Check (Optional)

Click **"Health Check"** if available

**Settings:**
- **Type**: Command
- **Command**: `python -c "import sys; sys.exit(0)"`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3
- **Start Period**: 40 seconds

### Step 3.6: Deploy Trading Bot

1. **Click "Deploy"** or **"Create & Deploy"**
2. **Watch deployment**:
   - Dokploy pulls code from GitHub
   - Builds Docker image
   - Starts container
   - Status should show "Running" (green)
3. **View logs**:
   - Click service → **Logs**
   - Should see bot starting up

**Expected log output:**
```
2025-10-27 11:30:15 - INFO - Trading Bot v1.7.0 initialized
2025-10-27 11:30:16 - INFO - Telegram notifications: ENABLED
2025-10-27 11:30:17 - INFO - Robinhood connection: SUCCESS
2025-10-27 11:30:18 - INFO - Bot ready for trading
```

---

## Part 4: Create API Service (Monitoring)

### Step 4.1: Add API Service

1. **In RH Bot project**, click **"Add Service"** again
2. **Service Name**: `trading-bot-api`
3. **Build Type**: Docker
4. **Dockerfile Path**: `./Dockerfile`

### Step 4.2: Configure API Command

**Override Command:**
```
uvicorn api.app.main:app --host 0.0.0.0 --port 8000
```

### Step 4.3: Expose Port

**Port Mapping:**
- **Container Port**: 8000
- **Host Port**: 8000
- **Protocol**: TCP
- **Expose Publicly**: YES (check if available)

### Step 4.4: Environment Variables

Use same variables as trading-bot service:
- Copy from trading-bot or paste again
- All required variables

### Step 4.5: Volumes

Same as trading-bot:
- `/app/logs` → `/data/trading-bot/logs`
- `/app/config.json` → `/data/trading-bot/config.json`

### Step 4.6: Health Check

**Type**: HTTP
**URL**: `http://localhost:8000/api/v1/health/healthz`
**Interval**: 30 seconds
**Timeout**: 10 seconds
**Retries**: 3

### Step 4.7: Deploy API

Click **"Deploy"**

**Verify:**
- Status: Running (green)
- Logs show: "Application startup complete"
- Test endpoint:
  ```bash
  curl http://178.156.129.179:8000/api/v1/health/healthz
  ```
  Should return: `{"status": "ok"}`

---

## Part 5: Create Redis Service

### Step 5.1: Add Redis Service

1. **In RH Bot project**, click **"Add Service"**
2. **Service Name**: `redis`
3. **Service Type**: Docker
4. **Image**: `redis:7-alpine` (pre-built image, not building from Dockerfile)

### Step 5.2: Configure Redis

**Image Settings:**
- **Image Name**: `redis:7-alpine`
- **Pull Image**: Yes (or Auto-pull)

**Command Override:**
```
redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

**Port Mapping:**
- **Container Port**: 6379
- **Host Port**: 6379 (internal only, do not expose)
- **Protocol**: TCP

### Step 5.3: Volumes

**Add Volume:**
- **Container Path**: `/data`
- **Host Path**: `/data/redis-data`
- **Type**: ReadWrite

### Step 5.4: Health Check

**Type**: Command
**Command**: `redis-cli ping`
**Expected Output**: PONG
**Interval**: 10 seconds
**Timeout**: 5 seconds
**Retries**: 3

### Step 5.5: Deploy Redis

Click **"Deploy"**

**Verify:**
- Status: Running (green)
- Logs should show: "Ready to accept connections"

---

## Part 6: Verify All Services Running

### Check Dashboard

1. **In RH Bot project**, all three services should show:
   - ✅ trading-bot: Running
   - ✅ trading-bot-api: Running
   - ✅ redis: Running

### Check Individual Service Health

**For Each Service:**

1. Click service card
2. Check **Status**: Green circle = Running
3. Click **Logs**: Should see recent activity
4. Check **Health**: Last health check timestamp

### Test Services from VPS

SSH into VPS and test:

```bash
ssh hetzner

# Check all containers running
docker ps | grep -E 'trading-bot|redis'

# Check trading bot logs
docker logs <container-id> -f

# Test API endpoint
curl http://localhost:8000/api/v1/health/healthz

# Test Redis connection
docker exec redis-<container-id> redis-cli ping
```

---

## Part 7: Verify Telegram Notifications

### Test Notification Delivery

**Option 1: Check Logs in Dokploy**

1. **Click trading-bot service**
2. **Click Logs**
3. **Search for**: `telegram` or `notification`
4. Should see:
   ```
   2025-10-27 11:35:22 - INFO - Telegram notification sent: message_id=...
   2025-10-27 11:35:22 - INFO - Delivery time: XXms
   ```

**Option 2: Check Telegram Notification Log File**

```bash
ssh hetzner
docker exec trading-bot tail -f /app/logs/telegram-notifications.jsonl
```

**Expected format:**
```json
{"timestamp": "2025-10-27T11:35:22Z", "notification_type": "position_entry", "status": "success", "delivery_time_ms": 245}
```

### Execute Test Trade

1. **From Dokploy Logs**, watch for bot activity:
   - Market open detection
   - Position entry signals
   - Telegram notification sent

2. **In Telegram App**, check your chat:
   - Should see notification with symbol, price, quantity
   - Example:
     ```
     📈 Position Entry
     Symbol: AAPL
     Entry: $150.00
     Quantity: 100
     Stop Loss: $147.00
     Target: $156.00
     ```

3. **Check delivery time**: Should be <10 seconds (NFR-001)

---

## Part 8: Monitor Service Health

### Dokploy Dashboard

1. **Go to RH Bot project**
2. **Watch service cards**:
   - Green circle = Healthy
   - Red circle = Unhealthy
   - Gray = Stopped

3. **Click service → Metrics** (if available):
   - CPU usage
   - Memory usage
   - Network I/O
   - Uptime

### System Logs

**Monitor from VPS:**

```bash
ssh hetzner

# Real-time trading bot logs
docker logs trading-bot -f

# Real-time API logs
docker logs trading-bot-api -f

# Real-time Redis logs
docker logs redis -f

# Telegram notification logs
docker exec trading-bot tail -f /app/logs/telegram-notifications.jsonl

# Check resource usage
docker stats
```

---

## Part 9: Troubleshooting

### Service Won't Start

**Issue**: Service stuck in "Creating" or shows error

**Fix**:
1. Click service → **Logs**
2. Look for error message
3. Common issues:
   - Port already in use → Change Host Port
   - Image build failed → Check Dockerfile syntax
   - Environment variable missing → Add it
   - Volume mount path doesn't exist → Create on VPS first

**Via SSH:**
```bash
ssh hetzner
# Check volume path exists
ls -la /data/trading-bot/
ls -la /data/redis-data/

# Create if missing
mkdir -p /data/trading-bot/logs
mkdir -p /data/redis-data
chmod 755 /data/trading-bot /data/redis-data
```

### Telegram Notifications Not Working

**Check**:
1. `TELEGRAM_ENABLED=true` is set
2. `TELEGRAM_BOT_TOKEN` is correct (starts with numbers:)
3. `TELEGRAM_CHAT_ID` is numeric (not a username)
4. Logs show: "Telegram notification sent" or errors
5. Run validation:
   ```bash
   ssh hetzner
   docker exec trading-bot python -m src.trading_bot.notifications.validate_config
   ```

### API Not Responding

**Check**:
1. Service is running (green circle)
2. Port 8000 is exposed
3. Test from VPS:
   ```bash
   ssh hetzner
   curl -v http://localhost:8000/api/v1/health/healthz
   ```
4. If 503: API still starting (wait 20-30s)
5. If Connection refused: Port not exposed correctly

### Redis Connection Errors

**Check**:
1. Redis service is running
2. `REDIS_URL=redis://redis:6379/0` is set correctly
3. Test connection:
   ```bash
   ssh hetzner
   docker exec redis redis-cli ping
   ```
4. If fails: Check Redis logs for errors

---

## Part 10: Post-Deployment Checklist

After all services are deployed:

- [ ] **trading-bot**: Running (green), logs show "Bot ready"
- [ ] **trading-bot-api**: Running (green), health check passing
- [ ] **redis**: Running (green), redis-cli ping returns PONG
- [ ] **Environment variables**: All configured correctly
- [ ] **Volumes**: Logs directory has files
- [ ] **Telegram**: Test notification sent successfully
- [ ] **API health**: `curl http://178.156.129.179:8000/api/v1/health/healthz` returns 200
- [ ] **Log aggregation**: Logs visible in Dokploy dashboard
- [ ] **No error messages** in any service logs
- [ ] **All services** survived a manual container restart

---

## Quick Reference

### Dokploy Dashboard Access
- **URL**: http://178.156.129.179:9100
- **Services**: 3 (trading-bot, trading-bot-api, redis)
- **Volumes**: 4 mount points

### Environment Variables Summary
| Variable | Value | Required |
|----------|-------|----------|
| ROBINHOOD_USERNAME | Your username | YES |
| ROBINHOOD_PASSWORD | Your password | YES |
| ROBINHOOD_ACCOUNT_ID | Account ID | YES |
| TELEGRAM_ENABLED | true | YES |
| TELEGRAM_BOT_TOKEN | Bot token | YES |
| TELEGRAM_CHAT_ID | Chat ID | YES |
| REDIS_URL | redis://redis:6379/0 | YES |
| LOG_LEVEL | INFO | NO |

### Service Ports
| Service | Port | Internal/External |
|---------|------|------------------|
| trading-bot | - | Internal only |
| trading-bot-api | 8000 | External (exposed) |
| redis | 6379 | Internal only |

---

## Next Steps

1. ✅ Prepare credentials (Part 1)
2. ✅ Login to Dokploy (Part 2)
3. → **Create trading-bot service** (Part 3)
4. → **Create trading-bot-api service** (Part 4)
5. → **Create redis service** (Part 5)
6. → **Verify all running** (Part 6)
7. → **Test Telegram notifications** (Part 7)
8. → **Monitor health** (Part 8)
9. → **Troubleshoot if needed** (Part 9)
10. → **Complete checklist** (Part 10)

---

**Status**: 🟡 Ready for manual setup via Dokploy dashboard

Open http://178.156.129.179:9100 and follow Parts 3-5 to deploy services!
