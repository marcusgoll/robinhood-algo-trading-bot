# Deployment Strategy

**Last Updated**: 2025-10-26
**Deployment Model**: staging-prod (paper trading → live trading)
**Related Docs**: See `system-architecture.md` for infrastructure, `tech-stack.md` for platform choices

## Deployment Model

**Choice**: staging-prod
**Rationale**:
- **Safety**: Paper trading mode validates strategy changes before risking real money
- **Regulatory**: Live trading requires validation (avoid accidental losses)
- **Solo developer**: Staging provides safety net without code review overhead
- **Rollback**: Easy rollback from live → paper if issues detected

**Environments**:
- **Local**: Development (laptop/desktop, dry-run mode)
- **Staging**: Paper trading on VPS (simulated trades, real market data)
- **Production**: Live trading on VPS (real money)

**Alternatives Rejected**:
- direct-prod: Too risky (no validation before live trading)
- local-only: Not applicable (deploying to VPS 24/7)

---

## Environments

### Development (Local)

**Purpose**: Local development, strategy testing, unit tests
**Location**: Developer laptop/desktop
**URL**: N/A (terminal-only, no web interface)
**Database**: File-based logs (local `logs/` directory)
**Data**: Simulated data + backtest data (Yahoo Finance historical)
**Secrets**: `.env` file (not committed)

**How to Run**:
```bash
# Dry-run mode (no orders submitted)
python -m trading_bot --dry-run

# Paper trading mode (local, simulated orders)
PAPER_TRADING=true python -m trading_bot

# Dashboard only
python -m trading_bot dashboard
```

**Key Differences from Production**:
- No VPS (local execution)
- No Docker (direct Python execution)
- Faster iteration (no deployment step)
- Backtest data (not real-time)

---

### Staging (Paper Trading)

**Purpose**: Pre-production validation with real market data, simulated orders
**Location**: Hetzner VPS (CX11)
**URL**: N/A (CLI dashboard via SSH)
**Database**: File-based logs (`/opt/trading-bot/logs/`)
**Branch**: `main` branch (same as production)
**Deploy Trigger**: Manual (git pull + docker-compose restart)

**Configuration**:
```env
# .env (staging)
PAPER_TRADING=true  # Critical: simulated orders only
ROBINHOOD_USERNAME=staging@example.com
ROBINHOOD_PASSWORD=<staging-password>
```

**Differences from Production**:
- `PAPER_TRADING=true` (no real orders submitted to Robinhood)
- Separate Robinhood account (paper trading account)
- Lower risk limits (test aggressive strategies)
- Verbose logging enabled (DEBUG level)

**Data**: Real market data (Alpaca, Polygon.io), simulated trade execution

**Validation Period**: 24-48 hours minimum before promoting to production

---

### Production (Live Trading)

**Purpose**: Live trading with real money
**Location**: Hetzner VPS (CX11)
**URL**: N/A (CLI dashboard via SSH)
**Database**: File-based logs (`/opt/trading-bot/logs/`)
**Branch**: `main` branch
**Deploy Trigger**: Manual approval after staging validation

**Configuration**:
```env
# .env (production)
PAPER_TRADING=false  # LIVE TRADING (real money)
ROBINHOOD_USERNAME=live@example.com
ROBINHOOD_PASSWORD=<production-password>
```

**Protections**:
- Circuit breakers enabled (daily loss limit, consecutive losses)
- Position size limits enforced (max 5% per position)
- Manual approval required before deployment
- Rollback plan documented

---

## CI/CD Pipeline

**Tool**: None currently (manual deployment)
**Future**: GitHub Actions for automated testing

**Current Deployment Process** (Manual):

### Deploying to Staging

**Trigger**: Manual (after local testing)

**Steps**:
```bash
# 1. SSH to VPS
ssh trader@vps.example.com

# 2. Navigate to bot directory
cd /opt/trading-bot

# 3. Pull latest code
git pull origin main

# 4. Rebuild Docker images (if Dockerfile changed)
docker-compose build

# 5. Restart bot
docker-compose restart trading-bot

# 6. Check logs for errors
docker-compose logs -f trading-bot
```

**Duration**: ~3 minutes

**Validation Checklist**:
- [ ] Bot starts without errors
- [ ] Robinhood authentication succeeds (paper account)
- [ ] Market data flows (Alpaca, Polygon.io)
- [ ] No circuit breaker trips (check logs)
- [ ] Dashboard shows correct status
- [ ] Simulated trades execute (verify in Robinhood paper account)

**If Issues Found**:
1. Check logs: `docker-compose logs trading-bot`
2. Rollback: `git reset --hard HEAD~1 && docker-compose restart`
3. Debug locally: `docker-compose down && docker-compose up` (foreground)

---

### Deploying to Production

**Trigger**: Manual (after 24-48 hours of staging validation)

**Steps**:
```bash
# 1. SSH to production VPS
ssh trader@prod-vps.example.com

# 2. Backup current configuration
cd /opt/trading-bot
cp .env .env.backup-$(date +%Y%m%d)
tar -czf backup-$(date +%Y%m%d).tar.gz logs/ .robinhood.pickle

# 3. Pull latest code
git pull origin main

# 4. Rebuild Docker images (if needed)
docker-compose build

# 5. CRITICAL: Verify PAPER_TRADING=false in .env
grep PAPER_TRADING .env  # Should show "false"

# 6. Restart bot (live trading begins)
docker-compose restart trading-bot

# 7. Monitor logs closely for first hour
docker-compose logs -f trading-bot
```

**Duration**: ~5 minutes (+ 1 hour monitoring)

**Quality Gates** (must pass before production):
- Staging validation complete (24-48 hours)
- No critical bugs in logs
- Win rate > 40% in staging (minimum viability)
- Circuit breaker not tripped in staging
- Backtest validates strategy change (if strategy modified)

**Post-Deployment Monitoring**:
- Watch logs for first 1 hour (errors, circuit breaker trips)
- Check first 3 trades execute correctly
- Verify positions show in dashboard
- Monitor P&L closely (alert if >-2% on first day)

---

## Deployment Artifacts

### Build Artifacts

**Docker Image**:
- **Name**: `trading-bot:latest`
- **Generated**: During `docker-compose build`
- **Stored**: Locally on VPS (no registry)
- **Layers**: Python 3.11 slim + dependencies + source code

**Configuration**:
- `.env` file (secrets, credentials)
- `config.json` (strategy parameters, risk limits)
- `.robinhood.pickle` (session state)

**Logs**:
- Persistent volume mount (`./logs:/app/logs`)
- Survives container restarts

---

## Database Migrations

**Tool**: None (no database, file-based logs)
**Strategy**: Schema evolution via code (backward-compatible reads)

**Adding New Fields to TradeRecord**:
```python
# v1.0.0 - Original TradeRecord
@dataclass
class TradeRecord:
    timestamp: str
    symbol: str
    # ... 25 other fields

# v1.1.0 - Add new field
@dataclass
class TradeRecord:
    timestamp: str
    symbol: str
    # ... 25 other fields
    new_field: Decimal | None = None  # Optional (backward-compatible)
```

**Reading Old Logs** (backward compatibility):
```python
# Parser handles missing fields gracefully
try:
    new_field = record.get("new_field", Decimal("0"))
except KeyError:
    new_field = Decimal("0")  # Default for old records
```

**No Downtime**: New code reads old logs seamlessly

---

## Rollback Procedure

**When to Rollback**:
- Bot crashes on startup (code error)
- Circuit breaker trips immediately (strategy bug)
- Unexpected losses (e.g., >-2% in first hour)

**How to Rollback** (< 5 minutes):

### Quick Rollback (Code)

```bash
# 1. SSH to VPS
ssh trader@vps.example.com
cd /opt/trading-bot

# 2. Revert to previous commit
git log --oneline -5  # Find previous commit hash
git reset --hard <previous-commit>

# 3. Restart bot
docker-compose restart trading-bot

# 4. Verify rollback
docker-compose logs trading-bot
```

**Duration**: ~2 minutes

### Full Rollback (Code + Config)

```bash
# 1. SSH to VPS
ssh trader@vps.example.com
cd /opt/trading-bot

# 2. Restore backup
cp .env.backup-20251026 .env
tar -xzf backup-20251026.tar.gz

# 3. Revert code
git reset --hard <previous-commit>

# 4. Restart bot
docker-compose restart trading-bot
```

**Duration**: ~5 minutes

**Testing**: Monthly rollback drills to ensure procedure works

---

## Monitoring & Alerts

**What to Monitor**:

| Metric | Tool | Alert Threshold | Action |
|--------|------|-----------------|--------|
| Bot process status | Docker health check | Process stopped | Restart container |
| Circuit breaker status | Bot logs | Tripped | Investigate, fix, resume |
| Daily P&L | Performance tracker | < -3% | Manual review, pause trading |
| API errors | Bot logs | > 5% error rate | Check API connectivity |
| Log file size | ls -lh | > 100MB | Rotate logs |

**Alert Channels**:
- **Critical** (bot stopped, circuit breaker): Email (manual check)
- **Warning** (high error rate, P&L): Bot logs (review at market close)

**Post-Deployment Monitoring Period**: 1 hour after production deploy

---

## Secrets Management

**Tool**: `.env` file (manual management)
**Storage**: Local file on VPS (not in git)
**Access**: SSH key-based auth only (no password login)

**Secrets Inventory**:
- `ROBINHOOD_USERNAME` - Robinhood email
- `ROBINHOOD_PASSWORD` - Robinhood password
- `ROBINHOOD_MFA_SECRET` - TOTP secret (for pyotp)
- `DEVICE_TOKEN` - Auto-populated after first auth
- `ALPACA_API_KEY` - Alpaca API key
- `ALPACA_SECRET_KEY` - Alpaca secret
- `POLYGON_API_KEY` - Polygon.io API key
- `OPENAI_API_KEY` - OpenAI API key
- `BOT_API_AUTH_TOKEN` - FastAPI bearer token

**Rotation**:
- API keys: Every 90 days (calendar reminder)
- Robinhood password: Every 180 days (forced by Robinhood)
- Process: Update `.env`, restart bot (zero downtime)

**Never Commit**:
- `.env` files (use `.env.example` as template)
- API keys in code
- Passwords in comments

**VPS Security**:
- SSH key-based auth only (no password login)
- Firewall: Only ports 22 (SSH), 8000 (API, future)
- Fail2ban: Auto-ban after 3 failed SSH attempts

---

## Deployment Schedule

**Recommended Schedule**: Weekdays, 10am-2pm EST (market hours)
**Why**: Allows monitoring during trading hours, avoid Sunday/Monday surprises

**Deployment Freeze**:
- Friday after 2pm (avoid weekend issues)
- Week of major economic events (FOMC, earnings week for major holdings)
- December 20 - January 2 (holidays, low liquidity)

**Emergency Hotfixes**: Anytime (for critical bugs, circuit breaker issues)

---

## Disaster Recovery

**Scenario**: VPS hardware failure (total loss)

**Recovery Plan**:
1. **Immediate** (0-15 min): Spin up new VPS (Hetzner console)
2. **Short-term** (15-60 min):
   - Install Docker + Docker Compose
   - Clone git repository
   - Restore `.env` from backup (manual, keep copy locally)
   - Restore logs from daily backup (S3-compatible storage)
3. **Long-term** (1-2 hours): Validate bot starts, resume trading

**RTO** (Recovery Time Objective): 1 hour
**RPO** (Recovery Point Objective): 24 hours (daily backup, acceptable to lose 1 day of trades)

**Backup Script** (cron job, 4:30 PM EST daily):
```bash
#!/bin/bash
# /opt/trading-bot/scripts/docker-backup.sh
DATE=$(date +%Y-%m-%d)
cd /opt/trading-bot
tar -czf /tmp/trading-bot-backup-$DATE.tar.gz logs/ .env config.json .robinhood.pickle
rsync -avz /tmp/trading-bot-backup-$DATE.tar.gz user@storage-box:/backups/
rm /tmp/trading-bot-backup-$DATE.tar.gz
```

---

## Compliance & Audit

**Deployment Audit Log**:
- Who deployed: Git commit author (tracked in git log)
- What changed: Git commit diff (`git show <commit>`)
- When: Git commit timestamp + deployment time (manual log)
- Where: Environment (staging/production)

**Manual Audit Log** (`docs/deployment-log.md`):
```markdown
| Date | Environment | Commit | Deployer | Notes |
|------|-------------|--------|----------|-------|
| 2025-10-26 | Production | abc123 | Marcus | Added LLM pattern validation |
| 2025-10-25 | Staging | def456 | Marcus | Testing new stop-loss logic |
```

**Retention**: 7 years (git history preserved indefinitely)

---

## Health Checks

**Docker Health Check** (bot process liveness):
```yaml
# docker-compose.yml
healthcheck:
  test: ["CMD", "python", "-c", "import os; os.path.exists('/app/logs/trading_bot.log')"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

**Manual Health Check** (after deployment):
```bash
# Check bot is running
docker-compose ps

# Check logs for errors
docker-compose logs --tail=100 trading-bot | grep ERROR

# Check Robinhood session valid
grep "Robinhood session valid" logs/trading_bot.log
```

---

## Performance Validation

**Pre-Deployment Checks**:
- Unit tests pass (pytest)
- Backtest validates strategy (if strategy changed)
- No linter errors (ruff)
- Type check passes (mypy/Pyright)

**Post-Deployment Checks**:
- First trade executes successfully (verify in Robinhood)
- Dashboard shows correct metrics
- No ERROR logs in first hour
- Circuit breaker not tripped

---

## Change Log

| Date | Change | Reason | Impact |
|------|--------|--------|--------|
| 2025-10-26 | Initial deployment strategy | Document manual deployment process | Foundation for automation |
| 2025-10-15 | Added daily backup script | Disaster recovery preparedness | Daily backups to S3-compatible storage |
| 2025-10-01 | Documented rollback procedure | Safety net for bad deploys | 5-minute rollback SLA |
| 2025-09-20 | Defined staging → production flow | Validate before live trading | Staging must pass 24-hour test |
