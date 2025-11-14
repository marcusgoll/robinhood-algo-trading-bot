# Deployment Guide

Complete guide for deploying the Robinhood Trading Bot to production.

---

## Table of Contents

- [Deployment Options](#deployment-options)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Local Deployment](#local-deployment)
- [Production Deployment](#production-deployment)
- [Systemd Service Setup](#systemd-service-setup)
- [Reverse Proxy Setup](#reverse-proxy-setup)
- [Monitoring Setup](#monitoring-setup)
- [Security Hardening](#security-hardening)
- [Environment Configuration](#environment-configuration)
- [Backup Strategy](#backup-strategy)
- [Disaster Recovery](#disaster-recovery)
- [Rollback Procedures](#rollback-procedures)

---

## Deployment Options

### Option 1: Local Development (Default)

**Best for**: Testing, paper trading, development

```
Your Computer → Trading Bot Process → Robinhood API
```

**Pros**:
- Easy to debug
- No hosting costs
- Quick iterations

**Cons**:
- Computer must stay on
- No automatic restart
- No monitoring

---

### Option 2: Cloud VPS (Recommended for Production)

**Best for**: Live trading, 24/7 operation

**Providers**:
- **DigitalOcean** ($6/month) - Droplet
- **Linode** ($5/month) - Nanode
- **AWS EC2** (t2.micro free tier)
- **Google Cloud** (e2-micro free tier)

**Pros**:
- Always on (24/7)
- Automatic restart (systemd)
- Professional monitoring
- Backup/restore capabilities

**Cons**:
- Monthly cost
- More complex setup
- Requires Linux knowledge

---

### Option 3: Dedicated Server

**Best for**: High-volume trading, multiple strategies

**Pros**:
- Full control
- High performance
- No resource limits

**Cons**:
- Expensive ($50+/month)
- Overkill for single bot

---

## Pre-Deployment Checklist

Before deploying to production, ensure:

### Testing

- [ ] All tests passing (`pytest`)
- [ ] 90%+ code coverage
- [ ] Type checking clean (`mypy src/`)
- [ ] Security scan clean (`bandit -r src/`)
- [ ] Backtesting complete (Sharpe ≥1.0, Win Rate ≥55%)
- [ ] Paper trading validated (1-2 weeks minimum)

### Configuration

- [ ] `.env` configured with real credentials
- [ ] `config.json` reviewed and validated
- [ ] Phase progression appropriate (not "experience" for live)
- [ ] Risk limits set correctly
- [ ] Trading hours configured
- [ ] API token generated (BOT_API_AUTH_TOKEN)

### Safety

- [ ] Circuit breakers enabled
- [ ] Emotional control enabled
- [ ] Profit protection configured
- [ ] Position limits appropriate for account size
- [ ] Stop losses validated

### Infrastructure

- [ ] Server provisioned (if cloud deployment)
- [ ] Domain configured (if using API publicly)
- [ ] SSL certificate ready (if using HTTPS)
- [ ] Monitoring tools selected
- [ ] Backup strategy defined

---

## Local Deployment

### Quick Setup

```bash
# 1. Clone repository
git clone https://github.com/marcusgoll/robinhood-algo-trading-bot.git
cd robinhood-algo-trading-bot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
cp config.example.json config.json
# Edit both files with your settings

# 5. Validate configuration
python validate_startup.py

# 6. Start bot (paper trading)
python -m src.trading_bot

# 7. Start API service (separate terminal)
bash scripts/start_api.sh
```

### Running as Background Process (Linux/Mac)

```bash
# Using nohup
nohup python -m src.trading_bot > logs/bot.out 2>&1 &
nohup bash scripts/start_api.sh > logs/api.out 2>&1 &

# Check processes
ps aux | grep trading_bot
ps aux | grep uvicorn

# Stop processes
pkill -f "trading_bot"
pkill -f "uvicorn"
```

---

## Production Deployment

### 1. Provision Cloud Server

**DigitalOcean Example**:

```bash
# Create droplet (via web UI or doctl CLI)
doctl compute droplet create trading-bot \
  --image ubuntu-22-04-x64 \
  --size s-1vcpu-1gb \
  --region nyc3 \
  --ssh-keys YOUR_SSH_KEY_ID

# SSH into server
ssh root@YOUR_DROPLET_IP
```

---

### 2. Server Setup

```bash
# Update system
apt update && apt upgrade -y

# Install Python 3.11
apt install -y python3.11 python3.11-venv python3-pip

# Install system dependencies
apt install -y git nginx certbot python3-certbot-nginx

# Create dedicated user (security best practice)
useradd -m -s /bin/bash trading
usermod -aG sudo trading

# Switch to trading user
su - trading
```

---

### 3. Application Setup

```bash
# Clone repository
git clone https://github.com/marcusgoll/robinhood-algo-trading-bot.git
cd robinhood-algo-trading-bot

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
vim .env  # Add your credentials

cp config.example.json config.json
vim config.json  # Configure for production

# Validate
python validate_startup.py
```

---

### 4. Directory Structure

```bash
# Create necessary directories
mkdir -p logs/health
mkdir -p logs/emotional-control
mkdir -p logs/profit-protection
mkdir -p logs/performance
mkdir -p data
mkdir -p backups

# Set permissions
chmod 700 .env  # Only owner can read credentials
chmod 755 logs data backups
```

---

## Systemd Service Setup

### Trading Bot Service

Create `/etc/systemd/system/trading-bot.service`:

```ini
[Unit]
Description=Robinhood Trading Bot
After=network.target

[Service]
Type=simple
User=trading
Group=trading
WorkingDirectory=/home/trading/robinhood-algo-trading-bot
Environment="PATH=/home/trading/robinhood-algo-trading-bot/venv/bin"
ExecStart=/home/trading/robinhood-algo-trading-bot/venv/bin/python -m src.trading_bot
Restart=on-failure
RestartSec=10
StandardOutput=append:/home/trading/robinhood-algo-trading-bot/logs/trading_bot.log
StandardError=append:/home/trading/robinhood-algo-trading-bot/logs/errors.log

[Install]
WantedBy=multi-user.target
```

### API Service

Create `/etc/systemd/system/trading-bot-api.service`:

```ini
[Unit]
Description=Trading Bot API Service
After=network.target trading-bot.service

[Service]
Type=simple
User=trading
Group=trading
WorkingDirectory=/home/trading/robinhood-algo-trading-bot
Environment="PATH=/home/trading/robinhood-algo-trading-bot/venv/bin"
Environment="BOT_API_PORT=8000"
Environment="BOT_API_HOST=127.0.0.1"
ExecStart=/home/trading/robinhood-algo-trading-bot/venv/bin/uvicorn api.app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=10
StandardOutput=append:/home/trading/robinhood-algo-trading-bot/logs/api.log
StandardError=append:/home/trading/robinhood-algo-trading-bot/logs/api_errors.log

[Install]
WantedBy=multi-user.target
```

### Enable and Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable trading-bot
sudo systemctl enable trading-bot-api

# Start services
sudo systemctl start trading-bot
sudo systemctl start trading-bot-api

# Check status
sudo systemctl status trading-bot
sudo systemctl status trading-bot-api

# View logs
sudo journalctl -u trading-bot -f
sudo journalctl -u trading-bot-api -f
```

---

## Reverse Proxy Setup

### Nginx Configuration

Create `/etc/nginx/sites-available/trading-bot-api`:

```nginx
# HTTP server (redirects to HTTPS)
server {
    listen 80;
    server_name api.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL Configuration (certbot will add these)
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Proxy to API service
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket support
    location /api/v1/stream {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }

    # Access and error logs
    access_log /var/log/nginx/trading-bot-api.access.log;
    error_log /var/log/nginx/trading-bot-api.error.log;
}
```

### Enable Site and Get SSL

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/trading-bot-api \
           /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Get SSL certificate
sudo certbot --nginx -d api.yourdomain.com

# Reload nginx
sudo systemctl reload nginx
```

---

## Monitoring Setup

### Option 1: Simple Monitoring Script

Create `scripts/monitor.sh`:

```bash
#!/bin/bash
# Simple monitoring script

WEBHOOK_URL="YOUR_SLACK_WEBHOOK"

# Check bot health
HEALTH=$(curl -s -H "X-API-Key: $BOT_API_AUTH_TOKEN" \
  http://localhost:8000/api/v1/health | jq -r '.status')

if [ "$HEALTH" != "healthy" ]; then
    # Send alert
    curl -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"🚨 Trading Bot Health: $HEALTH\"}" \
      $WEBHOOK_URL
fi

# Check for errors in last hour
ERROR_COUNT=$(grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')" logs/errors.log | wc -l)

if [ $ERROR_COUNT -gt 10 ]; then
    curl -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"⚠️ High error count: $ERROR_COUNT errors in last hour\"}" \
      $WEBHOOK_URL
fi
```

Add to crontab:
```bash
*/15 * * * * /home/trading/robinhood-algo-trading-bot/scripts/monitor.sh
```

---

### Option 2: Prometheus + Grafana

**Install Prometheus**:

```bash
# Download and install
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*

# Create service
sudo cp prometheus /usr/local/bin/
sudo cp promtool /usr/local/bin/
```

**Configure Prometheus** (`prometheus.yml`):

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'trading-bot'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/metrics'
```

**Install Grafana**:

```bash
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install grafana

sudo systemctl enable grafana-server
sudo systemctl start grafana-server
```

**Access Grafana**: http://your-server:3000 (admin/admin)

---

## Security Hardening

### 1. Firewall Setup

```bash
# Install UFW
sudo apt install ufw

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (for API)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

### 2. SSH Hardening

Edit `/etc/ssh/sshd_config`:

```bash
# Disable root login
PermitRootLogin no

# Disable password authentication (use keys only)
PasswordAuthentication no

# Change default port (optional)
Port 2222
```

Restart SSH:
```bash
sudo systemctl restart sshd
```

---

### 3. Fail2Ban Setup

```bash
# Install fail2ban
sudo apt install fail2ban

# Configure
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Enable for SSH
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

### 4. Secure Credentials

```bash
# Set strict permissions on .env
chmod 600 .env

# Set ownership
sudo chown trading:trading .env

# Encrypt backup (if storing remotely)
tar -czf - .env | gpg -c > env.tar.gz.gpg
```

---

## Environment Configuration

### Production .env

```bash
# Robinhood Credentials
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_secure_password
ROBINHOOD_MFA_SECRET=YOUR_MFA_SECRET
DEVICE_TOKEN=  # Auto-populated

# API Configuration
BOT_API_PORT=8000
BOT_API_HOST=127.0.0.1  # Bind to localhost (nginx proxies)
BOT_API_AUTH_TOKEN=your_very_long_random_secure_token_here_32plus_chars
BOT_API_CORS_ORIGINS=https://dashboard.yourdomain.com
BOT_STATE_CACHE_TTL=60

# Polygon.io (if using Order Flow)
POLYGON_API_KEY=your_polygon_api_key

# Risk Management
PROFIT_TARGET_DAILY=500.00
EMOTIONAL_CONTROL_ENABLED=true

# Mode (IMPORTANT)
PAPER_TRADING=false  # Set to true initially, false for live trading
```

---

### Production config.json

```json
{
  "mode": "live",
  "phase_progression": {
    "current_phase": "proof",
    "proof": {
      "mode": "live",
      "max_trades_per_day": 1
    }
  },
  "risk_management": {
    "max_position_pct": 2.0,
    "max_daily_loss_pct": 2.0,
    "atr_enabled": true
  },
  "trading_hours": {
    "start": "07:00",
    "end": "10:00",
    "timezone": "America/New_York"
  }
}
```

---

## Backup Strategy

### Automated Backup Script

Create `/home/trading/backup.sh`:

```bash
#!/bin/bash

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/trading/backups/$DATE"
BOT_DIR="/home/trading/robinhood-algo-trading-bot"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup configuration
cp "$BOT_DIR/config.json" "$BACKUP_DIR/"
cp "$BOT_DIR/.env" "$BACKUP_DIR/"

# Backup state files
cp -r "$BOT_DIR/logs/emotional-control" "$BACKUP_DIR/"
cp -r "$BOT_DIR/logs/profit-protection" "$BACKUP_DIR/"

# Backup logs (compress)
tar -czf "$BACKUP_DIR/logs.tar.gz" "$BOT_DIR/logs"/*.log

# Backup to remote (optional)
# rsync -avz "$BACKUP_DIR" user@backup-server:/backups/trading-bot/

# Keep only last 30 backups
cd /home/trading/backups
ls -t | tail -n +31 | xargs rm -rf

echo "Backup complete: $BACKUP_DIR"
```

Add to crontab:
```bash
0 1 * * * /home/trading/backup.sh
```

---

## Disaster Recovery

### Scenario 1: Server Failure

**Recovery Steps**:

```bash
# 1. Provision new server
doctl compute droplet create trading-bot-recovery \
  --image ubuntu-22-04-x64 \
  --size s-1vcpu-1gb \
  --region nyc3

# 2. Setup new server (follow Production Deployment steps)

# 3. Restore from backup
scp -r backup-server:/backups/trading-bot/latest/* .

# 4. Restore configuration
cp backups/latest/config.json ./
cp backups/latest/.env ./

# 5. Restore state
cp -r backups/latest/emotional-control/* logs/emotional-control/
cp -r backups/latest/profit-protection/* logs/profit-protection/

# 6. Start services
sudo systemctl start trading-bot
sudo systemctl start trading-bot-api

# 7. Verify
curl -H "X-API-Key: $BOT_API_AUTH_TOKEN" http://localhost:8000/api/v1/health
```

**RTO (Recovery Time Objective)**: 30-60 minutes
**RPO (Recovery Point Objective)**: 24 hours (daily backups)

---

### Scenario 2: Corrupted State

**Recovery Steps**:

```bash
# 1. Stop bot
sudo systemctl stop trading-bot

# 2. Backup corrupted state
cp logs/emotional-control/state.json logs/emotional-control/state.json.corrupted

# 3. Restore from backup
cp backups/YYYYMMDD/emotional-control/state.json logs/emotional-control/

# 4. Restart bot
sudo systemctl start trading-bot

# 5. Monitor logs
tail -f logs/trading_bot.log
```

---

## Rollback Procedures

### Rollback to Previous Version

```bash
# 1. Stop services
sudo systemctl stop trading-bot
sudo systemctl stop trading-bot-api

# 2. Switch to previous version
cd /home/trading/robinhood-algo-trading-bot
git fetch --all
git checkout v1.7.0  # Or specific commit

# 3. Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt

# 4. Restore compatible config
cp backups/YYYYMMDD/config.json ./

# 5. Restart services
sudo systemctl start trading-bot
sudo systemctl start trading-bot-api

# 6. Verify
curl -H "X-API-Key: $BOT_API_AUTH_TOKEN" http://localhost:8000/api/v1/health
```

---

### Emergency Shutdown

```bash
# 1. Stop all trading
sudo systemctl stop trading-bot

# 2. Trip circuit breaker
python -c "from src.trading_bot.circuit_breakers import CircuitBreaker; \
           CircuitBreaker().trip('Emergency shutdown')"

# 3. Close positions manually via Robinhood app

# 4. Investigate logs
tail -100 logs/errors.log
tail -100 logs/trading_bot.log

# 5. Fix issue

# 6. Reset and restart when safe
python -c "from src.trading_bot.circuit_breakers import CircuitBreaker; \
           CircuitBreaker().reset()"
sudo systemctl start trading-bot
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Tests passing
- [ ] Security scan clean
- [ ] Backtest results acceptable
- [ ] Paper trading validated
- [ ] Configuration reviewed
- [ ] Credentials secured

### Deployment

- [ ] Server provisioned
- [ ] Application deployed
- [ ] Systemd services configured
- [ ] Nginx configured (if using)
- [ ] SSL certificate installed
- [ ] Firewall configured
- [ ] Monitoring setup
- [ ] Backups automated

### Post-Deployment

- [ ] Services running
- [ ] Health check passing
- [ ] Logs being written
- [ ] API accessible
- [ ] Monitoring working
- [ ] Alerts configured
- [ ] First backup completed
- [ ] Documentation updated

---

## Support

- **Operations Guide**: [docs/OPERATIONS.md](OPERATIONS.md)
- **Architecture**: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- **API Documentation**: [docs/API.md](API.md)
- **Issues**: [GitHub Issues](https://github.com/marcusgoll/robinhood-algo-trading-bot/issues)

---

**Last Updated**: 2025-10-26
**Version**: v1.8.0
