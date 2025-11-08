# VPS Deployment Guide - Multi-Agent Trading System

Quick guide for deploying the multi-agent trading system to your VPS using existing PostgreSQL.

## Prerequisites

- VPS with PostgreSQL already installed and running
- SSH access configured (`ssh hetzner`)
- Git repository cloned to `/opt/trading-bot`
- API keys from Anthropic and Financial Modeling Prep

## Step-by-Step Deployment

### 1. SSH into VPS

```bash
ssh hetzner
cd /opt/trading-bot
```

### 2. Pull Latest Code

```bash
git pull origin main
```

### 3. Set Up Database

Run the database setup script:

```bash
bash scripts/setup-database.sh
```

This will:
- Create `trading_bot` database
- Create `trading_bot` user
- Grant all privileges
- Optionally run migrations

Or manually:

```bash
sudo -u postgres psql
CREATE DATABASE trading_bot;
CREATE USER trading_bot WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE trading_bot TO trading_bot;
\q
```

### 4. Configure Environment

Update `.env` file on VPS:

```bash
nano /opt/trading-bot/.env
```

Add/update these variables:

```bash
# Anthropic Claude API
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Financial Modeling Prep API
FMP_API_KEY=your_fmp_key

# PostgreSQL (using localhost since it's on same VPS)
DATABASE_URL=postgresql://trading_bot:your_password@localhost:5432/trading_bot

# Enable multi-agent system
MULTI_AGENT_ENABLED=true
MULTI_AGENT_MIN_AGREEMENT=2
MULTI_AGENT_DAILY_LLM_BUDGET=5.00

# Self-learning (start disabled)
SELF_LEARNING_ENABLED=false
SELF_LEARNING_MIN_TRADES=10
SELF_LEARNING_AUTO_APPLY_THRESHOLD=80.0
SELF_LEARNING_LOOKBACK_DAYS=30
```

Save and exit (Ctrl+X, Y, Enter).

### 5. Install Python Dependencies

```bash
pip install anthropic sqlalchemy psycopg2-binary alembic
```

Or if using a virtual environment:

```bash
source venv/bin/activate
pip install anthropic sqlalchemy psycopg2-binary alembic
```

### 6. Run Database Migrations

```bash
cd /opt/trading-bot
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema
INFO  [alembic.runtime.migration] Running upgrade 001_initial_schema -> 002_add_trade_metadata
INFO  [alembic.runtime.migration] Running upgrade 002_add_trade_metadata -> 003_add_agent_daily_metrics
```

### 7. Verify Database Setup

```bash
bash scripts/verify-database.sh
```

Expected output:
```
==============================================================
Trading Bot Database Verification
==============================================================

Database Connection Details:
  Host: localhost
  Port: 5432
  Database: trading_bot
  User: trading_bot

✓ PostgreSQL service is running
✓ Successfully connected to database
✓ Table 'agent_interactions' exists
✓ Table 'agent_prompts' exists
✓ Table 'trade_outcomes' exists
✓ Table 'strategy_adjustments' exists
✓ Table 'agent_daily_metrics' exists
✓ Table 'trade_metadata' exists
✓ Alembic migrations applied (version: 003_add_agent_daily_metrics)
✓ User has INSERT permissions
✓ PostgreSQL 14.x
✓ Successfully inserted test record
✓ Successfully deleted test record

==============================================================
All tests passed! Database is ready for use.
==============================================================
```

### 8. Test Multi-Agent System

```bash
python -m trading_bot.llm.examples.multi_agent_consensus_workflow
```

### 9. Update Docker Container (if using Docker)

The docker-compose.yml has been updated to use external PostgreSQL. Build and restart:

```bash
cd /opt/trading-bot

# Stop existing container
docker stop trading-bot
docker rm trading-bot

# Rebuild image
docker build -t trading-bot:latest -f Dockerfile .

# Run with multi-agent system enabled
docker run -d \
  --name trading-bot \
  --restart unless-stopped \
  -v /opt/trading-bot/logs:/app/logs \
  -v /opt/trading-bot/.env:/app/.env:ro \
  -v /opt/trading-bot/config.json:/app/config.json:ro \
  -v /opt/trading-bot/.robinhood.pickle:/app/.robinhood.pickle \
  trading-bot:latest
```

Or use docker-compose:

```bash
docker-compose up -d --build
```

### 10. Monitor Logs

```bash
# Docker logs
docker logs -f trading-bot

# Or direct logs
tail -f /opt/trading-bot/logs/trading_bot.log
```

## Monitoring Multi-Agent System

### Check Agent Performance

SSH into VPS and connect to PostgreSQL:

```bash
ssh hetzner
sudo -u postgres psql -d trading_bot
```

Run queries:

```sql
-- Daily costs by agent
SELECT
    agent_name,
    COUNT(*) as calls,
    ROUND(AVG(cost_usd)::numeric, 4) as avg_cost,
    ROUND(SUM(cost_usd)::numeric, 4) as total_cost
FROM agent_interactions
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY agent_name
ORDER BY total_cost DESC;

-- Recent trade outcomes
SELECT
    symbol,
    decision,
    entry_price,
    exit_price,
    ROUND(pnl_pct::numeric, 2) as pnl_pct,
    exit_reason,
    created_at
FROM trade_outcomes
ORDER BY created_at DESC
LIMIT 10;

-- Strategy adjustments
SELECT
    parameter_name,
    old_value,
    new_value,
    ROUND(confidence_score::numeric, 1) as confidence,
    status,
    LEFT(reasoning, 60) as reasoning_preview
FROM strategy_adjustments
ORDER BY created_at DESC
LIMIT 5;
```

### Check Daily Budget

```bash
# Via Python
python -c "
from trading_bot.llm.memory_service import AgentMemory
memory = AgentMemory()
stats = memory.get_daily_cost_by_agent()
total = sum(stats.values())
print(f'Today: \${total:.4f}')
for agent, cost in sorted(stats.items(), key=lambda x: x[1], reverse=True):
    print(f'  {agent}: \${cost:.4f}')
"
```

### Check FMP Usage

```bash
# Grep logs for FMP calls
grep "FMP API call" /opt/trading-bot/logs/trading_bot.log | tail -20

# Count calls today
grep "FMP API call" /opt/trading-bot/logs/trading_bot.log | \
  grep "$(date +%Y-%m-%d)" | wc -l
```

## Enabling Self-Learning (After 10+ Trades)

Once you have 10+ completed trades:

1. Update `.env`:
```bash
nano /opt/trading-bot/.env
# Change SELF_LEARNING_ENABLED=false to true
```

2. Restart bot:
```bash
docker restart trading-bot
```

3. Learning loop runs nightly at 2 AM UTC
4. Check results:
```sql
SELECT * FROM strategy_adjustments WHERE created_at >= NOW() - INTERVAL '7 days';
```

## Troubleshooting

### Database Connection Errors

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check if database exists
sudo -u postgres psql -l | grep trading_bot

# Check user permissions
sudo -u postgres psql -c "SELECT * FROM pg_roles WHERE rolname='trading_bot';"

# Test connection
PGPASSWORD=your_password psql -h localhost -U trading_bot -d trading_bot -c "SELECT 1;"
```

### Migration Errors

```bash
# Check current version
alembic current

# Show all revisions
alembic history

# Force stamp
alembic stamp head

# Try upgrade again
alembic upgrade head
```

### Docker Container Issues

```bash
# Check container status
docker ps -a | grep trading-bot

# View logs
docker logs trading-bot

# Enter container shell
docker exec -it trading-bot bash

# Test database connection from container
docker exec -it trading-bot python -c "
from trading_bot.llm.memory_service import AgentMemory
memory = AgentMemory()
print('Connection successful!')
"
```

### API Key Errors

```bash
# Verify .env file has keys
grep ANTHROPIC_API_KEY /opt/trading-bot/.env
grep FMP_API_KEY /opt/trading-bot/.env

# Test Anthropic API
python -c "
import anthropic
import os
from dotenv import load_dotenv
load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
message = client.messages.create(
    model='claude-haiku-4-20250514',
    max_tokens=10,
    messages=[{'role': 'user', 'content': 'Hello'}]
)
print('Anthropic API: OK')
"

# Test FMP API
curl "https://financialmodelingprep.com/api/v3/profile/AAPL?apikey=YOUR_FMP_KEY"
```

## Performance Optimization

### PostgreSQL Tuning

For better performance with frequent agent queries:

```bash
sudo nano /etc/postgresql/*/main/postgresql.conf
```

Add/update:
```ini
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### Add Database Indexes

For faster queries:

```sql
-- Index on agent_interactions for daily cost queries
CREATE INDEX idx_agent_interactions_created_at ON agent_interactions(created_at);
CREATE INDEX idx_agent_interactions_agent_name ON agent_interactions(agent_name);

-- Index on trade_outcomes for learning queries
CREATE INDEX idx_trade_outcomes_created_at ON trade_outcomes(created_at);
CREATE INDEX idx_trade_outcomes_symbol ON trade_outcomes(symbol);

-- Index on strategy_adjustments
CREATE INDEX idx_strategy_adjustments_created_at ON strategy_adjustments(created_at);
CREATE INDEX idx_strategy_adjustments_status ON strategy_adjustments(status);
```

## Backup and Recovery

### Backup Database

```bash
# Create backup directory
mkdir -p /opt/trading-bot/backups

# Backup trading_bot database
sudo -u postgres pg_dump trading_bot > /opt/trading-bot/backups/trading_bot_$(date +%Y%m%d).sql

# Compress backup
gzip /opt/trading-bot/backups/trading_bot_$(date +%Y%m%d).sql
```

### Automated Daily Backups

Create cron job:

```bash
crontab -e
```

Add:
```bash
# Backup trading_bot database daily at 3 AM
0 3 * * * sudo -u postgres pg_dump trading_bot | gzip > /opt/trading-bot/backups/trading_bot_$(date +\%Y\%m\%d).sql.gz

# Delete backups older than 30 days
0 4 * * * find /opt/trading-bot/backups -name "trading_bot_*.sql.gz" -mtime +30 -delete
```

### Restore from Backup

```bash
# Stop trading bot
docker stop trading-bot

# Drop and recreate database
sudo -u postgres psql -c "DROP DATABASE IF EXISTS trading_bot;"
sudo -u postgres psql -c "CREATE DATABASE trading_bot;"

# Restore backup
gunzip -c /opt/trading-bot/backups/trading_bot_20250108.sql.gz | sudo -u postgres psql trading_bot

# Restart trading bot
docker start trading-bot
```

## Security Checklist

- [ ] Strong PostgreSQL password in `.env`
- [ ] PostgreSQL only listening on localhost (not exposed to internet)
- [ ] `.env` file permissions set to 600 (only owner can read)
- [ ] API keys stored in `.env` (not in code)
- [ ] Regular backups enabled
- [ ] Logs rotated to prevent disk fill
- [ ] Firewall configured (only necessary ports open)
- [ ] SSH key-based authentication (no password login)
- [ ] Trading bot running in Docker container (isolated)
- [ ] Regular security updates applied

## Next Steps

1. ✓ Deploy multi-agent system to VPS
2. ✓ Verify database setup
3. ✓ Test with paper trading mode
4. Collect 10+ trades
5. Enable self-learning loop
6. Review and approve medium-confidence adjustments
7. Monitor performance for 1-2 weeks
8. Switch to live trading (with caution)

## Support

For issues or questions:
- Check logs: `tail -f /opt/trading-bot/logs/trading_bot.log`
- Review database: `sudo -u postgres psql -d trading_bot`
- Test connectivity: `bash scripts/verify-database.sh`
- Read documentation: `docs/multi-agent-setup.md`
