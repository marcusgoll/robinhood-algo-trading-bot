# Production Deployment Guide

Complete guide for deploying and maintaining the trading bot on a VPS with 24/7 operation.

## VPS Infrastructure

**Platform:** Hetzner VPS running Dokploy (Docker Swarm)
**Access:** `ssh hetzner`

**Recommended Specifications:**
- **CPU**: 4 vCPUs
- **RAM**: 8 GB
- **Storage**: 40 GB SSD
- **OS**: Ubuntu 22.04 LTS
- **Network**: Reliable connection with low latency

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

---

## Health Monitoring & Auto-Recovery

### Setup Health Monitor

The repository includes automated health monitoring scripts in `/deployment/`:

```bash
# SSH to VPS
ssh hetzner

# Setup health monitoring
cd /opt/trading-bot
chmod +x deployment/health-monitor.sh

# Add to crontab (runs every 5 minutes)
crontab -e
```

Add this line:
```
*/5 * * * * /opt/trading-bot/deployment/health-monitor.sh
```

### What Gets Monitored

1. **Service Status** - Docker service running and healthy
2. **API Health** - REST API responding correctly
3. **Resource Usage** - Memory and CPU within limits
4. **Error Rate** - Recent log errors tracked
5. **Disk Space** - Sufficient storage available
6. **Trading State** - Bot in valid operational state

### Auto-Recovery Features

- **Service Restart** - Automatically restarts failed containers
- **Alert System** - Sends notifications via Telegram/Email
- **Log Analysis** - Tracks error patterns
- **Resource Limits** - Alerts on high memory/CPU usage

### Configure Alerts

Edit `/opt/trading-bot/.env` to enable alerts:

```bash
# Telegram Alerts (recommended)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Email Alerts (optional)
ALERT_EMAIL=your@email.com
```

### Manual Health Check

```bash
# Run health check manually
ssh hetzner '/opt/trading-bot/deployment/health-monitor.sh'

# View health logs
ssh hetzner 'tail -f /opt/trading-bot/logs/health-monitor.log'

# Check service health via CLI
python cli.py bot status
```

---

## Backup & Recovery

### Automated Backups

Setup daily automated backups:

```bash
ssh hetzner

# Make backup script executable
chmod +x /opt/trading-bot/deployment/backup.sh

# Add daily backup to crontab (2 AM)
crontab -e
```

Add this line:
```
0 2 * * * /opt/trading-bot/deployment/backup.sh
```

### What Gets Backed Up

- Configuration files (`.env`, `config.json`)
- Trading data (`data/` directory)
- Trade logs (`logs/trades/`)
- Database files (if using SQLite)

**Retention:** Last 7 days kept locally

**Location:** `/opt/trading-bot/backups/`

### Manual Backup

```bash
# Create immediate backup
ssh hetzner '/opt/trading-bot/deployment/backup.sh'

# List backups
ssh hetzner 'ls -lh /opt/trading-bot/backups/'

# Download backup to local machine
scp hetzner:/opt/trading-bot/backups/backup_*.tar.gz ./
```

### Restore from Backup

```bash
# SSH to VPS
ssh hetzner

# Stop service
docker service scale trading-bot-wkulrv=0

# Extract backup
cd /opt/trading-bot
tar -xzf backups/backup_YYYYMMDD_HHMMSS.tar.gz

# Restart service
docker service scale trading-bot-wkulrv=1

# Monitor restart
docker service logs trading-bot-wkulrv --follow
```

### Off-site Backup (Highly Recommended)

```bash
# Setup rsync to backup server
ssh hetzner

# Add to crontab (daily at 3 AM)
crontab -e
```

Add:
```
0 3 * * * rsync -avz /opt/trading-bot/backups/ user@backup-server:/backups/trading-bot/
```

Or use cloud storage:
```bash
# AWS S3
0 3 * * * aws s3 sync /opt/trading-bot/backups/ s3://your-bucket/trading-bot-backups/

# Google Cloud Storage
0 3 * * * gsutil -m rsync -r /opt/trading-bot/backups/ gs://your-bucket/trading-bot-backups/
```

---

## Maintenance & Monitoring

### Daily Tasks

```bash
# Check bot status
python cli.py bot status

# View positions and P&L
python cli.py trading positions
python cli.py trading portfolio

# Check risk metrics
python cli.py risk metrics

# View recent errors
python cli.py logs view --level ERROR --tail 50

# Monitor service health
ssh hetzner 'docker service ps trading-bot-wkulrv'
```

### Weekly Tasks

```bash
# Review weekly performance
python cli.py workflow execute weekly-review

# Export trade logs for analysis
python cli.py logs export --start-date $(date -d '7 days ago' +%Y-%m-%d) --output weekly.json

# Check disk usage
ssh hetzner 'df -h /opt/trading-bot'

# Review agent performance
python cli.py agents metrics

# Check backup status
ssh hetzner 'ls -lh /opt/trading-bot/backups/ | tail -10'

# Review health monitor logs
ssh hetzner 'tail -100 /opt/trading-bot/logs/health-monitor.log | grep ALERT'
```

### Monthly Tasks

- **Security Updates**: `ssh hetzner 'apt-get update && apt-get upgrade -y'`
- **Rotate API Keys**: Update keys in `.env` and redeploy
- **Archive Old Logs**: Move logs older than 30 days to cold storage
- **Review Strategy**: Analyze performance and adjust parameters
- **Test Disaster Recovery**: Verify backup restoration works
- **Update Dependencies**: Check for security patches

### Updating the Bot

```bash
# 1. SSH to VPS
ssh hetzner

# 2. Navigate to repo
cd /opt/trading-bot

# 3. Create backup before update
./deployment/backup.sh

# 4. Pull latest code
git pull origin main

# 5. Rebuild Docker image
docker build -t trading-bot-wkulrv:latest -f Dockerfile .

# 6. Update service (rolling update, zero downtime)
docker service update --image trading-bot-wkulrv:latest trading-bot-wkulrv

# 7. Monitor deployment
docker service ps trading-bot-wkulrv
docker service logs trading-bot-wkulrv --follow --tail 100

# 8. Verify bot is healthy
python cli.py bot status
```

---

## Using the CLI Tool

The bot includes a comprehensive CLI for management:

### Bot Control

```bash
# Check status
python cli.py bot status

# View all commands
python cli.py --help

# View trading operations
python cli.py trading --help
```

### Remote Management

You can manage the bot remotely by SSH port forwarding:

```bash
# Forward API port
ssh -L 8000:localhost:8000 hetzner

# Now run CLI commands locally
python cli.py bot status
python cli.py trading positions
python cli.py agents status
```

### Common CLI Commands

```bash
# Trading operations
python cli.py trading positions
python cli.py trading orders --days 7
python cli.py trading portfolio

# Agent management
python cli.py agents status
python cli.py agents metrics

# Workflow execution
python cli.py workflow list
python cli.py workflow execute end-of-day-review

# Risk monitoring
python cli.py risk metrics
python cli.py risk limits
python cli.py risk emotional-control

# Configuration
python cli.py config view
python cli.py config validate

# Logs
python cli.py logs view --follow
python cli.py logs export --start-date 2025-01-01
```

See `CLI_README.md` for complete documentation.

---

## Security Best Practices

### 1. Secure Environment Variables

```bash
ssh hetzner

# Set proper permissions
chmod 600 /opt/trading-bot/.env
chmod 600 /opt/trading-bot/config.json

# Verify
ls -la /opt/trading-bot/{.env,config.json}
```

### 2. Firewall Configuration

```bash
ssh hetzner

# Enable UFW if not already
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow Dokploy (if needed)
sudo ufw allow 3000/tcp

# Deny direct API access from outside
sudo ufw deny 8000/tcp

# Check rules
sudo ufw status verbose
```

### 3. SSH Hardening

```bash
# Use SSH keys only (disable password auth)
ssh hetzner 'sudo sed -i "s/#PasswordAuthentication yes/PasswordAuthentication no/" /etc/ssh/sshd_config'
ssh hetzner 'sudo systemctl restart sshd'

# Change default SSH port (optional but recommended)
ssh hetzner 'sudo sed -i "s/#Port 22/Port 2222/" /etc/ssh/sshd_config'
```

### 4. Secret Management

- Store credentials in `.env` only
- Never commit `.env` to git
- Use environment-specific configs
- Rotate API keys monthly
- Use read-only API keys where possible

### 5. Network Security

- Keep API on localhost only
- Use VPN for remote access
- Enable DDoS protection via Cloudflare
- Monitor for unauthorized access attempts

### 6. Docker Security

```bash
# Run as non-root user in container
# Use multi-stage builds
# Scan images for vulnerabilities
ssh hetzner 'docker scan trading-bot-wkulrv:latest'
```

### 7. Regular Security Audits

```bash
# Check for vulnerabilities in Python packages
ssh hetzner 'cd /opt/trading-bot && pip-audit'

# Review system logs
ssh hetzner 'sudo journalctl -p err -n 100'

# Check failed login attempts
ssh hetzner 'sudo grep "Failed password" /var/log/auth.log | tail -20'
```

---

## Performance Optimization

### Resource Monitoring

```bash
# Real-time resource usage
ssh hetzner 'htop'

# Docker stats
ssh hetzner 'docker stats trading-bot-wkulrv'

# Memory usage
ssh hetzner 'docker service ps trading-bot-wkulrv --format "table {{.Name}}\t{{.CurrentState}}"'

# Check logs for performance issues
python cli.py logs view | grep -i "slow\|timeout\|performance"
```

### Log Management

```bash
# Compress old logs (saves disk space)
ssh hetzner 'find /opt/trading-bot/logs -name "*.log" -mtime +7 -exec gzip {} \;'

# Archive trade logs
ssh hetzner 'find /opt/trading-bot/logs/trades -name "*.jsonl" -mtime +30 -exec gzip {} \;'

# Clean old Docker logs
ssh hetzner 'docker system prune -a --volumes --force'
```

### Database Optimization

If using SQLite for order tracking:

```bash
ssh hetzner 'sqlite3 /opt/trading-bot/data/orders.db "VACUUM;"'
```

---

## Troubleshooting Extended

### High Memory Usage

```bash
# Check container memory
ssh hetzner 'docker stats trading-bot-wkulrv --no-stream'

# View memory trends
python cli.py bot status

# Force garbage collection and restart
ssh hetzner 'docker service update --force trading-bot-wkulrv'
```

### Slow Response Times

```bash
# Check API latency
curl -w "@-" -o /dev/null -s http://localhost:8000/health <<'EOF'
time_total: %{time_total}\n
EOF

# Check database locks
ssh hetzner 'lsof /opt/trading-bot/data/*.db'

# Monitor agent response times
python cli.py agents metrics
```

### Authentication Failures

```bash
# Check credentials
ssh hetzner 'grep ROBINHOOD /opt/trading-bot/.env'

# Clear auth cache
ssh hetzner 'rm -f /opt/trading-bot/data/auth_token.json'

# Test authentication
ssh hetzner 'cd /opt/trading-bot && python -c "from trading_bot.auth import AlpacaAuth; AlpacaAuth().login()"'
```

### Network Issues

```bash
# Test connectivity
ssh hetzner 'ping -c 4 api.robinhood.com'

# Check DNS resolution
ssh hetzner 'nslookup api.robinhood.com'

# Test API endpoints
ssh hetzner 'curl -I https://api.robinhood.com'
```

---

## Disaster Recovery

### Complete System Failure

1. **Provision new VPS** with same specs
2. **Install Dokploy** and Docker
3. **Restore from backup**:
   ```bash
   scp backup_YYYYMMDD.tar.gz newserver:/opt/trading-bot/
   ssh newserver 'cd /opt/trading-bot && tar -xzf backup_YYYYMMDD.tar.gz'
   ```
4. **Redeploy** via Dokploy
5. **Verify** bot operation

### Data Corruption

1. **Stop bot** immediately
2. **Assess damage** - check logs for corruption point
3. **Restore from backup** before corruption
4. **Replay trades** if needed from JSONL logs
5. **Restart** and monitor

### Emergency Stop

If bot is misbehaving:

```bash
# Immediate stop
ssh hetzner 'docker service scale trading-bot-wkulrv=0'

# Cancel all open orders via CLI
python cli.py trading orders --status pending

# Review what happened
python cli.py logs view --level ERROR --tail 500

# Fix issue and restart when safe
ssh hetzner 'docker service scale trading-bot-wkulrv=1'
```

---

## Monitoring Dashboards

### Grafana + Prometheus (Optional)

For advanced monitoring:

```bash
# Deploy monitoring stack
docker stack deploy -c monitoring-stack.yml monitoring

# Access Grafana
http://your-vps-ip:3001

# Import trading bot dashboard
# Dashboard ID: [create custom]
```

### Simple Monitoring

```bash
# Create monitoring script
cat > /opt/trading-bot/deployment/status.sh <<'EOF'
#!/bin/bash
echo "=== Trading Bot Status ==="
date
echo ""
echo "Service Status:"
docker service ps trading-bot-wkulrv --format "{{.Name}}\t{{.CurrentState}}"
echo ""
echo "Resource Usage:"
docker stats trading-bot-wkulrv --no-stream
echo ""
echo "Recent Errors:"
tail -20 /opt/trading-bot/logs/trading_bot.log | grep ERROR
EOF

chmod +x /opt/trading-bot/deployment/status.sh

# Run daily status report
crontab -e
# Add: 0 9 * * * /opt/trading-bot/deployment/status.sh | mail -s "Trading Bot Status" you@email.com
```

---

## Quick Reference

### Essential Commands

```bash
# Service management
docker service ls                                    # List all services
docker service ps trading-bot-wkulrv                 # Check service
docker service logs trading-bot-wkulrv --follow      # View logs
docker service scale trading-bot-wkulrv=0            # Stop
docker service scale trading-bot-wkulrv=1            # Start

# Bot management via CLI
python cli.py bot status                             # Check status
python cli.py trading positions                      # View positions
python cli.py logs view --follow                     # Watch logs

# Maintenance
/opt/trading-bot/deployment/health-monitor.sh        # Health check
/opt/trading-bot/deployment/backup.sh                # Create backup
docker system prune -a --volumes                     # Clean up

# Emergency
docker service scale trading-bot-wkulrv=0            # EMERGENCY STOP
python cli.py trading orders --status pending        # Check open orders
```

### Important Paths

- **Config**: `/opt/trading-bot/.env`, `/opt/trading-bot/config.json`
- **Logs**: `/opt/trading-bot/logs/`
- **Trade Logs**: `/opt/trading-bot/logs/trades/`
- **Backups**: `/opt/trading-bot/backups/`
- **Scripts**: `/opt/trading-bot/deployment/`

### Support Resources

- **CLI Docs**: `CLI_README.md`
- **Architecture**: `CODEBASE_ARCHITECTURE.md`
- **Main README**: `README.md`

---

## Checklist

### Initial Deployment
- [ ] VPS provisioned and accessible
- [ ] Dokploy installed and configured
- [ ] Repository cloned to `/opt/trading-bot`
- [ ] `.env` configured with credentials
- [ ] `config.json` created with trading parameters
- [ ] Services deployed via Dokploy
- [ ] Health monitoring enabled
- [ ] Automated backups configured
- [ ] Alerts configured (Telegram/Email)
- [ ] Firewall rules set
- [ ] SSH hardening completed

### Daily Operations
- [ ] Check bot status
- [ ] Review positions and P&L
- [ ] Check risk metrics
- [ ] Review error logs
- [ ] Verify backups are running

### Weekly Operations
- [ ] Export and analyze trade logs
- [ ] Review agent performance
- [ ] Check disk usage
- [ ] Review health monitor alerts
- [ ] Test API connectivity

### Monthly Operations
- [ ] Apply security updates
- [ ] Rotate API keys
- [ ] Archive old logs
- [ ] Review strategy performance
- [ ] Test disaster recovery
- [ ] Update dependencies
