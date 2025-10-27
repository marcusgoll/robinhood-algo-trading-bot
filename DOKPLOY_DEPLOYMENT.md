# Dokploy Deployment Guide: Trading Bot

**Date**: 2025-10-27
**Purpose**: Migrate trading bot from Docker Compose to Dokploy for managed production deployment
**Status**: Ready for deployment

---

## Overview

Dokploy is a self-hosted deployment platform that simplifies container management. This guide walks through deploying your trading bot with:

- **Trading Bot Service** (main trading operations)
- **API Service** (monitoring/control endpoint)
- **Redis Service** (LLM response caching)
- **Persistent Storage** (logs, configuration, session state)
- **Environment Configuration** (including Telegram notifications)

---

## Prerequisites

✅ Dokploy installed on Hetzner VPS
✅ Docker and Docker Compose running
✅ SSH access to VPS (`ssh hetzner`)
✅ Git repository with trading bot code
✅ Environment variables prepared (.env)

---

## Step 1: Prepare Your Git Repository

Dokploy deploys from Git. Ensure your repository is ready:

```bash
# Push latest code to main branch
git push origin main

# Verify trading bot code is committed
git log --oneline -5
```

**Key files Dokploy needs:**
- `Dockerfile` ✓ (exists)
- `docker-compose.yml` ✓ (exists)
- `.dockerignore` ✓ (exists)
- `requirements.txt` ✓ (exists)

---

## Step 2: Access Dokploy Dashboard

1. **SSH into your VPS:**
   ```bash
   ssh hetzner
   ```

2. **Access Dokploy Dashboard:**
   - Open browser: `http://<your-vps-ip>:3000`
   - Or use reverse proxy if configured

3. **Login** with your Dokploy credentials

---

## Step 3: Create New Dokploy Project

### Via Dokploy Dashboard:

1. **Click "New Project"**
2. **Enter Project Details:**
   - Name: `trading-bot-prod`
   - Description: `Trading bot with Telegram notifications`

3. **Connect Git Repository:**
   - Select: GitHub / GitLab / Self-hosted Git
   - Connect account
   - Select repository: `robinhood-algo-trading-bot`
   - Branch: `main`

4. **Save Project**

---

## Step 4: Add Services to Dokploy Project

### Service 1: Trading Bot (Primary Service)

1. **Add New Service**
   - Type: Docker Compose / Docker
   - Name: `trading-bot`

2. **Configure Container:**
   - Image: Build from Dockerfile
   - Dockerfile path: `./Dockerfile`
   - Port: No external port (internal only)
   - Restart policy: Always

3. **Environment Variables:**
   ```
   PYTHONUNBUFFERED=1
   PYTHONPATH=/app
   TRADING_BOT_ENABLED=true

   # Robinhood Configuration
   ROBINHOOD_USERNAME=<your-username>
   ROBINHOOD_PASSWORD=<your-password>
   ROBINHOOD_ACCOUNT_ID=<your-account-id>

   # Telegram Configuration (NEW)
   TELEGRAM_ENABLED=true
   TELEGRAM_BOT_TOKEN=<your-bot-token>
   TELEGRAM_CHAT_ID=<your-chat-id>

   # Optional
   REDIS_URL=redis://redis:6379/0
   LOG_LEVEL=INFO
   ```

4. **Persistent Volumes:**
   - `/app/logs` → `/data/trading-bot/logs`
   - `/app/config.json` → `/data/trading-bot/config.json`
   - `/app/.robinhood.pickle` → `/data/trading-bot/.robinhood.pickle`

5. **Health Check:**
   - Type: Command
   - Command: `python -c "import sys; sys.exit(0)"`
   - Interval: 30s
   - Timeout: 10s
   - Retries: 3

6. **Deploy**

### Service 2: API Service (Monitoring)

1. **Add New Service**
   - Type: Docker
   - Name: `trading-bot-api`

2. **Configure Container:**
   - Image: Build from Dockerfile
   - Dockerfile path: `./Dockerfile`
   - Command: `uvicorn api.app.main:app --host 0.0.0.0 --port 8000`
   - Port: 8000 (expose for external access)
   - Restart policy: Always

3. **Environment Variables:**
   Same as trading-bot service (will inherit from project)

4. **Health Check:**
   - Type: HTTP
   - URL: `http://localhost:8000/api/v1/health/healthz`
   - Interval: 30s
   - Timeout: 10s
   - Retries: 3

5. **Deploy**

### Service 3: Redis (Caching)

1. **Add New Service**
   - Type: Docker
   - Name: `redis`

2. **Configure Container:**
   - Image: `redis:7-alpine`
   - Port: 6379 (internal only)
   - Restart policy: Always

3. **Command:**
   ```
   redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
   ```

4. **Persistent Volumes:**
   - `/data` → `/data/redis-data`

5. **Health Check:**
   - Type: Command
   - Command: `redis-cli ping`
   - Interval: 10s
   - Timeout: 5s
   - Retries: 3

6. **Deploy**

---

## Step 5: Configure Networking

In Dokploy, services in the same project can communicate by service name:

- Trading bot connects to Redis: `redis://redis:6379/0`
- API connects to Redis: `redis://redis:6379/0`
- Both services share environment variables

---

## Step 6: Set Up Persistent Storage

Create volumes for:

1. **Trading Bot Logs:**
   ```bash
   ssh hetzner
   mkdir -p /data/trading-bot/logs
   mkdir -p /data/trading-bot
   chmod 755 /data/trading-bot
   ```

2. **Redis Data:**
   ```bash
   mkdir -p /data/redis-data
   chmod 755 /data/redis-data
   ```

3. **Backup Configuration:**
   ```bash
   cp /path/to/config.json /data/trading-bot/config.json
   chmod 644 /data/trading-bot/config.json
   ```

---

## Step 7: Configure Domain/SSL (Optional)

If you want external access to the API:

1. **Set up reverse proxy** (Nginx, Caddy, etc.)
2. **Point domain** to VPS IP + port 8000
3. **Enable SSL** with Let's Encrypt

Example Nginx config:
```nginx
server {
    listen 443 ssl http2;
    server_name api.trading-bot.example.com;

    ssl_certificate /etc/letsencrypt/live/api.trading-bot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.trading-bot.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Step 8: Deploy and Verify

### In Dokploy Dashboard:

1. **Deploy All Services**
   - Click "Deploy" on each service
   - Monitor logs in real-time

2. **Watch Deployment Progress:**
   - Trading Bot: Should start trading within 30s
   - API: Should respond to health check within 20s
   - Redis: Should be ready within 5s

3. **Check Logs:**
   - Trading Bot logs: `Dokploy → trading-bot → Logs`
   - API logs: `Dokploy → trading-bot-api → Logs`
   - Redis logs: `Dokploy → redis → Logs`

### Via SSH:

```bash
ssh hetzner

# Check Docker services
docker ps

# View trading bot logs
docker logs trading-bot -f

# Check API health
curl http://localhost:8000/api/v1/health/healthz

# Check Redis
docker exec redis redis-cli ping
```

---

## Step 9: Verify Telegram Notifications

Your trading bot should now send Telegram notifications when:
1. A new position enters
2. A position exits with P&L
3. Risk alerts trigger

**Test notifications:**

1. **Monitor logs:**
   ```bash
   ssh hetzner
   docker exec trading-bot tail -f /app/logs/telegram-notifications.jsonl
   ```

2. **Trigger a test trade** (if using paper mode)

3. **Check Telegram** for notifications

4. **Verify success rate** in logs (should be >99%)

---

## Step 10: Set Up Backups

Dokploy can auto-backup Docker volumes:

1. **Configure Backup Schedule:**
   - Frequency: Daily at 2 AM
   - Retention: 30 days
   - Destination: `/backups/trading-bot`

2. **Manual Backup Command:**
   ```bash
   ssh hetzner
   tar czf /backups/trading-bot-$(date +%Y%m%d).tar.gz /data/trading-bot
   ```

---

## Monitoring & Maintenance

### Health Checks

Dokploy automatically monitors:
- ✅ Trading Bot: Running 24/7
- ✅ API: Responding to health checks
- ✅ Redis: Available for caching

### Logs

Access logs via Dokploy dashboard or SSH:

```bash
ssh hetzner

# Trading bot main log
docker logs trading-bot

# Telegram notification log
docker exec trading-bot tail -f /app/logs/telegram-notifications.jsonl

# API log
docker logs trading-bot-api

# Redis log
docker logs redis
```

### Resource Usage

Monitor via Dokploy Dashboard:
- CPU usage
- Memory usage
- Disk I/O
- Network I/O

---

## Rollback Strategy

If deployment fails:

1. **Via Dokploy:**
   - Click "Rollback" to previous working deployment
   - Or redeploy from git: `git revert <commit-hash>`

2. **Manual Rollback:**
   ```bash
   ssh hetzner
   docker-compose down
   git revert <commit-hash>
   docker-compose up -d
   ```

---

## Environment Variables Reference

### Required Variables

```
# Telegram (NEW - Feature #030)
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=<bot-token-from-botfather>
TELEGRAM_CHAT_ID=<numeric-user-id>

# Robinhood
ROBINHOOD_USERNAME=<your-username>
ROBINHOOD_PASSWORD=<your-password>
ROBINHOOD_ACCOUNT_ID=<your-account-id>
```

### Optional Variables

```
# Logging
LOG_LEVEL=INFO
VERBOSE=false

# Redis
REDIS_URL=redis://redis:6379/0

# Python
PYTHONUNBUFFERED=1
PYTHONPATH=/app
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Services not starting** | Check Docker logs: `docker logs <service-name>` |
| **Telegram notifications not working** | Run validator: `python -m src.trading_bot.notifications.validate_config` |
| **Redis connection errors** | Verify `REDIS_URL` environment variable matches service name |
| **API not responding** | Check port 8000 is exposed and firewall allows it |
| **Out of disk space** | Cleanup old logs: `docker system prune -a` |
| **Memory issues** | Increase VPS RAM or reduce `--maxmemory` in Redis config |

---

## Post-Deployment Checklist

- [ ] All 3 services deployed and healthy in Dokploy
- [ ] Telegram notifications validated (test message received)
- [ ] API health check passing at `http://localhost:8000/api/v1/health/healthz`
- [ ] Logs accessible and rotating properly
- [ ] Persistent volumes mounted correctly
- [ ] Backup schedule configured
- [ ] Monitoring alerts set up (optional)
- [ ] DNS/domain configured for API (optional)
- [ ] Trade execution verified (small test trade)

---

## Next Steps

1. **Create Dokploy project** (Step 3-4)
2. **Deploy services** (Step 8)
3. **Verify Telegram notifications** (Step 9)
4. **Monitor for 24 hours** to ensure stability
5. **Migrate from Docker Compose** when confident

---

## Support

For issues:
1. Check Dokploy logs in dashboard
2. SSH into VPS and check Docker logs
3. Validate Telegram config: `python -m src.trading_bot.notifications.validate_config`
4. Review trading bot logs: `/app/logs/trading_bot.log`

---

**Status**: 🟢 Ready for Dokploy deployment
**Last Updated**: 2025-10-27
**Version**: 1.0
