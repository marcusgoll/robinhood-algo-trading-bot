# Trading Bot - Deployment Quick Start

Complete deployment guide for running the bot 24/7 with LLM integration.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Deployment (Docker)](#local-deployment-docker)
- [Hetzner VPS Deployment](#hetzner-vps-deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

**Required:**
- Docker & Docker Compose
- Robinhood account (paper or live)
- OpenAI API key (for LLM features)

**Recommended:**
- 2GB+ RAM
- 10GB+ disk space
- Stable internet connection

---

## Local Deployment (Docker)

### Step 1: Clone Repository

```bash
git clone https://github.com/marcusgoll/robinhood-algo-trading-bot.git
cd robinhood-algo-trading-bot
```

### Step 2: Configure Environment

```bash
# Copy example files
cp .env.example .env
cp config.example.json config.json

# Edit configuration
nano .env
```

**Required `.env` settings:**
```bash
# Robinhood
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_password
ROBINHOOD_MFA_SECRET=YOUR_16_CHAR_SECRET

# OpenAI (optional - for LLM)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BUDGET_MONTHLY=100.00
```

### Step 3: Build and Start

```bash
# Build Docker images
bash scripts/deploy-docker.sh build

# Start services
bash scripts/deploy-docker.sh start
```

### Step 4: Verify

```bash
# Check status
bash scripts/deploy-docker.sh status

# View logs
bash scripts/deploy-docker.sh logs

# Check specific service
docker-compose logs -f trading-bot
```

**Expected output:**
```
============================================================
  TRADING BOT RUNNING - 24/7 OPERATION
============================================================
Trading Hours: 07:00 - 10:00 America/New_York
Press Ctrl+C to stop gracefully
============================================================

[21:34:00] Outside trading hours - idle
```

---

## Hetzner VPS Deployment

### Option 1: Automated Setup (Recommended)

**On your local machine:**

```bash
# Create VPS on Hetzner Cloud
# - Server type: CPX11 (2 vCPU, 2GB RAM, ~€4.51/month)
# - Image: Ubuntu 22.04
# - Location: Choose closest to NYSE

# Note the IP address, then SSH in:
ssh root@YOUR_VPS_IP
```

**On the VPS:**

```bash
# Download and run setup script
curl -o setup.sh https://raw.githubusercontent.com/marcusgoll/robinhood-algo-trading-bot/main/scripts/hetzner-setup.sh
bash setup.sh
```

The script will:
- ✅ Install Docker, Git, Python
- ✅ Create dedicated user
- ✅ Clone repository
- ✅ Setup systemd service
- ✅ Configure firewall
- ✅ Setup automated backups

**After setup completes:**

```bash
# Edit credentials
nano /opt/trading-bot/.env

# Build and start
cd /opt/trading-bot
sudo -u trading docker-compose build
sudo systemctl start trading-bot

# Verify
sudo -u trading docker-compose logs -f
```

### Option 2: Manual Setup

Follow steps in `docs/DEPLOYMENT.md` for full manual deployment guide.

---

## Configuration

### Trading Mode

**Paper Trading** (simulation - no real money):
```json
{
  "trading": {
    "mode": "paper"
  }
}
```

**Live Trading** (real money - ONLY after testing!):
```json
{
  "trading": {
    "mode": "live"
  },
  "phase_progression": {
    "current_phase": "proof"  # Start with 1 trade/day
  }
}
```

### LLM Integration

**Enable LLM analysis:**
```json
{
  "llm": {
    "enabled": true,
    "pre_trade_analysis": true,
    "min_confidence_threshold": 60
  }
}
```

Set in `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini  # or gpt-4o
OPENAI_BUDGET_MONTHLY=100.00
```

**Cost estimate:** $0.40-0.50/month with caching

### Trading Hours

Default: 7-10 AM EST (peak volatility)

```json
{
  "trading": {
    "hours": {
      "start_time": "07:00",
      "end_time": "10:00",
      "timezone": "America/New_York"
    }
  }
}
```

---

## Monitoring

### View Logs

```bash
# All logs
docker-compose logs -f

# Bot only
docker-compose logs -f trading-bot

# API only
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100
```

### API Monitoring

API runs on port 8000 (configure BOT_API_AUTH_TOKEN in .env):

```bash
# Health check
curl -H "X-API-Key: YOUR_TOKEN" http://localhost:8000/api/v1/health

# Bot state
curl -H "X-API-Key: YOUR_TOKEN" http://localhost:8000/api/v1/state

# Quick summary
curl -H "X-API-Key: YOUR_TOKEN" http://localhost:8000/api/v1/summary
```

Interactive docs: http://localhost:8000/api/docs

### Resource Usage

```bash
# Check resource usage
docker stats

# Disk usage
docker system df
```

---

## Management

### Start/Stop

```bash
# Stop services
docker-compose down

# Start services
docker-compose up -d

# Restart services
docker-compose restart

# Restart specific service
docker-compose restart trading-bot
```

### Backups

```bash
# Manual backup
bash scripts/docker-backup.sh

# Backups stored in: ./backups/
# Automated: Daily at 2 AM (cron)
```

### Updates

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## Troubleshooting

### Bot Won't Start

**Check logs:**
```bash
docker-compose logs trading-bot
```

**Common issues:**
- Missing `.env` or `config.json`
- Invalid Robinhood credentials
- MFA secret incorrect
- Docker not running

### Authentication Failed

```bash
# Check credentials in .env
cat .env | grep ROBINHOOD

# Test login manually
docker-compose exec trading-bot python -c "
from src.trading_bot.auth import RobinhoodAuth
from src.trading_bot.config import Config
auth = RobinhoodAuth(Config.from_env_and_json())
auth.login()
print('✓ Login successful')
"
```

### LLM Not Working

**Check API key:**
```bash
# Verify key is set
cat .env | grep OPENAI_API_KEY

# Test API
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $(grep OPENAI_API_KEY .env | cut -d= -f2)"
```

**Disable LLM** (bot will still work):
```json
{
  "llm": {
    "enabled": false
  }
}
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Increase swap (Hetzner VPS)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Firewall Blocking API

```bash
# Allow port 8000
sudo ufw allow 8000/tcp

# Check rules
sudo ufw status
```

---

## Quick Reference

### Docker Commands

```bash
# View containers
docker-compose ps

# View logs
docker-compose logs -f [service]

# Restart
docker-compose restart [service]

# Stop
docker-compose down

# Start
docker-compose up -d

# Exec into container
docker-compose exec trading-bot bash

# Remove everything
docker-compose down -v
```

### File Locations

```
/opt/trading-bot/              # Installation directory (VPS)
├── .env                       # Credentials (NEVER commit!)
├── config.json                # Trading configuration
├── logs/                      # All logs
│   ├── trading_bot.log       # Main log
│   ├── trades.log            # Trade history
│   └── llm_cache/            # LLM cache
├── backups/                   # Automated backups
└── scripts/                   # Management scripts
```

### Environment Variables

```bash
# Robinhood
ROBINHOOD_USERNAME=
ROBINHOOD_PASSWORD=
ROBINHOOD_MFA_SECRET=

# OpenAI
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_BUDGET_MONTHLY=100.00

# API
BOT_API_AUTH_TOKEN=
BOT_API_PORT=8000

# Redis (optional)
REDIS_URL=redis://redis:6379
```

---

## Support

- **Documentation**: `docs/` directory
- **Issues**: https://github.com/marcusgoll/robinhood-algo-trading-bot/issues
- **Deployment Guide**: `docs/DEPLOYMENT.md`
- **Operations Guide**: `docs/OPERATIONS.md`

---

**Last Updated:** 2025-10-26
**Version:** v1.8.0+llm
