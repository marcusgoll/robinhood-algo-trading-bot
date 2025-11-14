# Rollback Procedure

This document describes how to roll back to a previous version in case of deployment issues.

## Quick Rollback (Production)

If the current deployment is causing issues, roll back to the previous version:

```bash
# SSH into server
ssh hetzner

# Navigate to deployment directory
cd /opt/trading-bot

# Pull previous working version from git
git log --oneline -n 5  # Find last working commit
git checkout <commit-hash>

# Rebuild and restart services
docker compose down
docker compose build
docker compose up -d

# Verify services are healthy
docker compose ps
docker compose logs -f
```

## Service-Specific Rollback

### Frontend Only

```bash
# On server
cd /opt/trading-bot/frontend
git checkout <previous-commit>
docker compose build frontend
docker compose up -d frontend

# Verify
curl http://localhost:3000
```

### API Only

```bash
# On server
cd /opt/trading-bot
git checkout <previous-commit> -- api/
docker compose build api
docker compose up -d api

# Verify
curl http://localhost:8000/api/v1/health/healthz
```

### Trading Bot Only

```bash
# On server
cd /opt/trading-bot
git checkout <previous-commit> -- src/
docker compose build trading-bot
docker compose up -d trading-bot

# Verify
docker logs trading-bot --tail 50
```

## Docker Image Rollback

If you have tagged Docker images:

```bash
# List available images
docker images | grep trading-bot

# Tag current version as broken
docker tag trading-bot:latest trading-bot:broken

# Roll back to previous tag
docker tag trading-bot:v1.7.0 trading-bot:latest

# Restart services
docker compose up -d

# Verify
docker compose ps
```

## Configuration Rollback

If the issue is configuration-related:

```bash
# On server
cd /opt/trading-bot

# Restore .env from backup
cp .env.backup .env

# Restore config.json from backup
cp config.json.backup config.json

# Restart services
docker compose restart
```

## Database/State Rollback

If backtest data is corrupted:

```bash
# On server
cd /opt/trading-bot

# Restore backtest results from backup
rm -rf backtest_results/
cp -r backtest_results.backup/ backtest_results/

# Restart API to reload data
docker compose restart api
```

## Health Check Commands

After rollback, verify all services:

```bash
# Check all container health
docker compose ps

# Check API health
curl http://localhost:8000/api/v1/health/healthz

# Check frontend
curl http://localhost:3000

# Check logs for errors
docker compose logs --tail 100 api
docker compose logs --tail 100 frontend
docker compose logs --tail 100 trading-bot

# Check Redis connectivity
docker exec -it trading-bot-redis redis-cli ping
```

## Common Issues

### Frontend not loading
- Check nginx logs: `docker logs trading-bot-frontend`
- Verify API proxy: `curl http://localhost:3000/api/v1/health/healthz`
- Rebuild with no cache: `docker compose build --no-cache frontend`

### API errors
- Check environment variables: `docker exec trading-bot-api env | grep API`
- Verify backtest_results mount: `docker exec trading-bot-api ls -la /app/backtest_results`
- Check FastAPI logs: `docker logs trading-bot-api --tail 200`

### Trading bot crashes
- Check .env file is mounted: `docker exec trading-bot cat .env`
- Verify Robinhood session: `docker exec trading-bot ls -la .robinhood.pickle`
- Review crash logs: `docker logs trading-bot --tail 500`

## Prevention

To minimize rollback needs:

1. **Always test locally first**:
   ```bash
   docker compose -f docker-compose.yml build
   docker compose -f docker-compose.yml up
   ```

2. **Use staging environment** (if available)

3. **Tag releases properly**:
   ```bash
   git tag -a v1.8.0 -m "Add backtest dashboard"
   git push origin v1.8.0
   docker tag trading-bot:latest trading-bot:v1.8.0
   ```

4. **Backup before deployment**:
   ```bash
   # Backup on server
   cp .env .env.backup
   cp config.json config.json.backup
   cp -r backtest_results/ backtest_results.backup/
   ```

## Emergency Contacts

If rollback fails or causes further issues:

1. Check GitHub Issues: https://github.com/yourusername/trading-bot/issues
2. Review recent commits: `git log --oneline -n 10`
3. Restore from full backup: See `scripts/docker-backup.sh`

## Monitoring After Rollback

Monitor these metrics for 15 minutes after rollback:

- API response times: `curl http://localhost:8000/api/v1/backtests`
- Frontend load time: Chrome DevTools Network tab
- Container memory usage: `docker stats`
- Error rate in logs: `docker compose logs -f | grep ERROR`
