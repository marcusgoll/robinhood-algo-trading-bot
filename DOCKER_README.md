# Docker Deployment - Quick Reference

## Quick Start

```bash
# 1. Configure environment
cp .env.example .env
nano .env  # Add credentials

# 2. Deploy
docker compose up -d

# 3. Monitor
docker compose logs -f
```

## Commands

```bash
# Start
docker compose up -d

# Stop
docker compose down

# Restart
docker compose restart

# View logs
docker compose logs -f

# Check status
docker ps

# Update code
git pull && docker compose up -d --build
```

## Required Environment Variables

```bash
# .env
ROBINHOOD_USERNAME=your_email
ROBINHOOD_PASSWORD=your_password
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
TRADING_MODE=paper
```

## Modes

Edit `docker-compose.yml` command:

```yaml
# Paper trading (default)
command: ["python", "-m", "trading_bot", "orchestrator", "--orchestrator-mode", "paper"]

# Live trading
command: ["python", "-m", "trading_bot", "orchestrator", "--orchestrator-mode", "live"]
```

See `docs/DEPLOYMENT.md` for full documentation.

