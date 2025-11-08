# Deployment Guide

## VPS Infrastructure

**Platform:** Hetzner VPS running Dokploy (Docker Swarm)
**Access:** `ssh hetzner`

## Services (via Dokploy)

All services managed through Docker Swarm:

- `trading-bot-wkulrv` - Main trading bot orchestrator
- `trading-bot-api` - REST API
- `trading-bot-frontend` - Web UI
- `trading-bot-redis` - Cache/session storage

## Deployment Process

### IMPORTANT: Use Dokploy, NOT standalone containers

The VPS uses Dokploy for all deployments. **Do NOT create standalone containers** - they conflict with Dokploy services.

### Option 1: Via Dokploy Web UI (Recommended)

1. Access Dokploy at your VPS IP (port configured in Dokploy)
2. Navigate to the trading-bot application
3. Click "Redeploy" or "Rebuild"
4. Monitor logs in the Dokploy UI

### Option 2: Via CLI (for urgent fixes)

```bash
# 1. SSH to VPS
ssh hetzner

# 2. Navigate to repo
cd /opt/trading-bot

# 3. Pull latest code
git pull

# 4. Rebuild image with Dokploy tag
docker build -t trading-bot-wkulrv:latest -f Dockerfile .

# 5. Update service
docker service update --image trading-bot-wkulrv:latest trading-bot-wkulrv

# 6. Monitor deployment
docker service ps trading-bot-wkulrv
docker service logs trading-bot-wkulrv --follow
```

## Checking Status

```bash
# List all services
docker service ls

# Check specific service
docker service ps trading-bot-wkulrv

# View logs
docker service logs trading-bot-wkulrv --tail 100

# Check mounted logs on VPS
tail -f /opt/trading-bot/logs/trading_bot.log
```

## Configuration

Environment variables and configs are managed via Dokploy volumes:
- `/opt/trading-bot/.env` - Telegram, API keys
- `/opt/trading-bot/config.json` - Trading config
- `/opt/trading-bot/logs/` - Log directory

## Troubleshooting

### Service failing with "No module named trading_bot"

The Dokploy image wasn't built correctly. Rebuild:
```bash
cd /opt/trading-bot
docker build -t trading-bot-wkulrv:latest -f Dockerfile .
docker service update --image trading-bot-wkulrv:latest trading-bot-wkulrv
```

### No Telegram notifications

1. Check service is running: `docker service ps trading-bot-wkulrv`
2. Check logs: `docker service logs trading-bot-wkulrv`
3. Verify env vars: `ssh hetzner 'grep TELEGRAM /opt/trading-bot/.env'`

### Container crash loop

Check logs for error:
```bash
docker service logs trading-bot-wkulrv --tail 200
```

Common issues:
- Missing Claude CLI → Rebuild image
- Bad .env config → Fix /opt/trading-bot/.env
- Import errors → Code issue, check git log

## Key Points

1. ✅ **DO:** Use Dokploy for all deployments
2. ✅ **DO:** Rebuild with tag `trading-bot-wkulrv:latest`
3. ✅ **DO:** Update service after rebuilding image
4. ❌ **DON'T:** Create standalone `docker run` containers
5. ❌ **DON'T:** Use `docker stop/rm` - use `docker service` commands
6. ❌ **DON'T:** Tag images as `trading-bot:latest` - use `trading-bot-wkulrv:latest`
