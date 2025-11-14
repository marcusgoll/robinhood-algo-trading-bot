# Dokploy Deployment Guide

**Date**: 2025-10-29
**Target**: Hetzner VPS via Dokploy
**Status**: Ready to Deploy ✅

---

## Prerequisites Checklist

### ✅ Code Ready
- [x] All tests passing (31/31)
- [x] Blockers resolved
- [x] Docker configuration present
- [x] Environment variables documented

### ⚠️ VPS Setup Required
- [ ] Dokploy installed on Hetzner VPS
- [ ] SSH access configured (`ssh hetzner`)
- [ ] Domain/subdomain configured (optional)
- [ ] Environment variables set in Dokploy

---

## Deployment Method: Docker Compose via Dokploy

Dokploy supports deploying Docker Compose applications directly from Git repositories.

### Step 1: Connect to VPS

```bash
# Test SSH connection
ssh hetzner

# Check Dokploy status
docker ps | grep dokploy
```

### Step 2: Create New Application in Dokploy

**Via Dokploy Web UI**:

1. Navigate to: `http://your-vps-ip:3000` (or your Dokploy domain)
2. Click "New Application"
3. Configure:
   - **Name**: `trading-bot`
   - **Type**: Docker Compose
   - **Source**: Git Repository
   - **Repository**: `https://github.com/marcusgoll/robinhood-algo-trading-bot.git`
   - **Branch**: `main`
   - **Compose File**: `docker-compose.yml`

### Step 3: Configure Environment Variables

In Dokploy, add these environment variables:

#### Required Credentials
```bash
ROBINHOOD_USERNAME=your_username
ROBINHOOD_PASSWORD=your_password
ROBINHOOD_MFA_SECRET=your_mfa_secret
DEVICE_TOKEN=  # Auto-populated after first auth

# Alpaca API (for news)
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Sentiment Analysis (Reddit working, Twitter rate limited)
TWITTER_BEARER_TOKEN=your_twitter_token
REDDIT_CLIENT_ID=your_reddit_id
REDDIT_CLIENT_SECRET=your_reddit_secret
REDDIT_USER_AGENT=trading-bot:v1.0.0 (by /u/your_username)

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
```

#### Configuration Settings
```bash
# Safety Settings
PAPER_TRADING=true  # IMPORTANT: Keep true for testing
MAX_POSITION_PCT=5.0
MAX_DAILY_LOSS_PCT=3.0
MAX_CONSECUTIVE_LOSSES=3

# Features
SENTIMENT_ENABLED=true
TELEGRAM_ENABLED=true
EMOTIONAL_CONTROL_ENABLED=true

# Thresholds
SENTIMENT_THRESHOLD=0.6
MIN_CATALYST_STRENGTH=60.0
```

### Step 4: Deploy Application

In Dokploy UI:
1. Click "Deploy" button
2. Wait for build to complete (~2-3 minutes)
3. Check deployment logs for errors

### Step 5: Verify Deployment

```bash
# SSH into VPS
ssh hetzner

# Check running containers
docker ps

# Expected containers:
# - trading-bot (main bot)
# - trading-bot-api (FastAPI service, port 8000)
# - trading-bot-frontend (React dashboard, port 3002)
# - trading-bot-redis (caching)

# Check bot logs
docker logs trading-bot -f

# Check for startup success
docker logs trading-bot | grep "Trading bot started"
docker logs trading-bot | grep "Paper Trading: True"

# Verify API health
curl http://localhost:8000/api/v1/health/healthz
```

---

## Docker Compose Services

The deployment includes 4 services:

### 1. Trading Bot (Main Service)
- **Container**: `trading-bot`
- **Purpose**: Main trading bot (24/7 operation)
- **Restart**: `unless-stopped`
- **Volumes**:
  - `./logs:/app/logs` (persist logs)
  - `./.env:/app/.env:ro` (environment variables)
  - `./config.json:/app/config.json:ro` (configuration)
  - `./.robinhood.pickle:/app/.robinhood.pickle` (session persistence)

### 2. FastAPI Service (Monitoring/Control)
- **Container**: `trading-bot-api`
- **Purpose**: HTTP API for monitoring and control
- **Port**: 8000
- **Endpoints**:
  - `GET /api/v1/health/healthz` - Health check
  - `GET /api/v1/state` - Bot state
  - `POST /api/v1/control/pause` - Pause bot
  - `POST /api/v1/control/resume` - Resume bot

### 3. Frontend Dashboard (React)
- **Container**: `trading-bot-frontend`
- **Purpose**: Web UI for monitoring
- **Port**: 3002
- **URL**: `http://your-vps-ip:3002`

### 4. Redis (Caching)
- **Container**: `trading-bot-redis`
- **Purpose**: LLM response caching
- **Memory**: 256MB (LRU eviction)

---

## Post-Deployment Checklist

### Immediate (First Hour)

```bash
# 1. Verify all containers running
docker ps | grep trading-bot

# 2. Check bot started successfully
docker logs trading-bot | tail -50

# 3. Verify paper trading mode
docker logs trading-bot | grep "Paper Trading"
# Should show: "Paper Trading: True"

# 4. Check for any errors
docker logs trading-bot | grep -i error | tail -20

# 5. Verify session health
docker logs trading-bot | grep "health check"

# 6. Check API accessibility
curl http://localhost:8000/api/v1/health/healthz

# 7. Test Telegram notifications (if enabled)
# Bot should send startup notification to your Telegram

# 8. Monitor first trading signals
docker logs trading-bot -f
```

### First Day

- [ ] Verify bot is running continuously (no crashes)
- [ ] Check logs for trading signals
- [ ] Verify risk management (position sizes, stop losses)
- [ ] Monitor Telegram notifications
- [ ] Check API dashboard (http://your-vps-ip:3002)

### First Week

- [ ] Review trade history in logs
- [ ] Verify all safety mechanisms (circuit breakers, emotional control)
- [ ] Check sentiment analysis working (Reddit data)
- [ ] Monitor performance metrics
- [ ] No unexpected errors or crashes

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker logs trading-bot

# Common issues:
# 1. Missing environment variables
docker exec trading-bot env | grep ROBINHOOD

# 2. Configuration file issues
docker exec trading-bot cat /app/config.json

# 3. Permission issues
docker exec trading-bot ls -la /app/logs
```

### Bot Not Trading

```bash
# Check if market hours are configured
docker logs trading-bot | grep "trading hours"

# Verify paper trading mode
docker logs trading-bot | grep "Paper Trading"

# Check circuit breaker status
docker logs trading-bot | grep "circuit breaker"

# Verify API credentials
docker logs trading-bot | grep "Authentication"
```

### Health Check Failing

```bash
# Check health check endpoint
docker exec trading-bot python -c "import os; print(os.path.exists('/app/logs/trading_bot.log'))"

# Restart container
docker-compose restart trading-bot

# Check Robinhood session
docker logs trading-bot | grep "Session"
```

### Redis Connection Issues

```bash
# Check Redis running
docker ps | grep redis

# Test Redis connection
docker exec trading-bot-redis redis-cli ping
# Should return: PONG

# Restart Redis
docker-compose restart redis
```

---

## Updating the Bot

### Method 1: Via Dokploy UI
1. Go to Dokploy dashboard
2. Select "trading-bot" application
3. Click "Redeploy" (pulls latest from main branch)

### Method 2: Via SSH
```bash
ssh hetzner

# Pull latest code (if deployed via Git)
cd /path/to/bot
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Check logs
docker logs trading-bot -f
```

### Method 3: Via Docker Hub (if using registry)
```bash
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d

# Verify update
docker logs trading-bot | head -20
```

---

## Monitoring Commands

### Quick Status Check
```bash
# All in one
docker ps | grep trading-bot && \
docker logs trading-bot --tail 5 && \
curl -s http://localhost:8000/api/v1/health/healthz | jq
```

### Detailed Monitoring
```bash
# Container stats
docker stats trading-bot trading-bot-api trading-bot-redis

# Disk usage
docker system df

# Logs by time
docker logs trading-bot --since 1h

# Follow all services
docker-compose logs -f
```

### Log Locations (in container)
```
/app/logs/trading_bot.log - Main bot log
/app/logs/trades.log - Trade executions
/app/logs/errors.log - Error tracking
/app/logs/health_check.log - Session health
/app/logs/startup.log - Startup sequence
```

---

## Security Checklist

- [x] `.env` file NOT in Git (in .gitignore)
- [ ] SSH key-based auth for VPS
- [ ] Firewall configured (only necessary ports open)
- [ ] Regular backups of logs and config
- [ ] Environment variables encrypted in Dokploy
- [ ] API authentication enabled (BOT_API_AUTH_TOKEN)
- [ ] HTTPS for frontend dashboard (optional, via reverse proxy)

---

## Rollback Procedure

If deployment fails or bot misbehaves:

```bash
# Stop all services
docker-compose down

# Roll back to previous version
git checkout <previous-commit-hash>

# Rebuild and start
docker-compose up -d --build

# Verify
docker logs trading-bot -f
```

---

## Performance Optimization

### Resource Limits (Optional)
Add to `docker-compose.yml`:

```yaml
services:
  trading-bot:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          memory: 512M
```

### Log Rotation
Already configured in docker-compose.yml:
- Max size: 10MB per file
- Max files: 3
- Total: ~30MB per service

---

## Next Steps

1. **Now**: Test SSH connection to VPS
   ```bash
   ssh hetzner
   ```

2. **Configure Dokploy**: Set up new application with environment variables

3. **Deploy**: Click deploy in Dokploy UI

4. **Verify**: Check all containers running and bot started

5. **Monitor**: Watch logs for first hour

6. **Iterate**: Adjust configuration as needed

---

## Support

**Issues**: https://github.com/marcusgoll/robinhood-algo-trading-bot/issues
**Logs**: Check `docker logs trading-bot` for all runtime information
**Monitoring**: Access dashboard at `http://your-vps-ip:3002`
**API**: Health check at `http://your-vps-ip:8000/api/v1/health/healthz`

---

## Production Checklist (Before Live Trading)

⚠️ **DO NOT switch to live trading until:**

- [ ] Bot runs successfully in paper trading for 2-4 weeks
- [ ] All safety mechanisms verified (circuit breakers, position limits)
- [ ] No unexpected errors or crashes
- [ ] Performance meets expectations
- [ ] Risk management validated with paper trades
- [ ] Monitoring and alerting confirmed working
- [ ] Backup and recovery procedures tested

**Then and only then**: Change `PAPER_TRADING=false` in environment variables.
