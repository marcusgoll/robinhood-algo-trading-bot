# Dokploy Deployment Checklist: RH Bot

**Date**: 2025-10-27
**Project**: RH Bot - Trading Bot with Telegram Notifications
**Status**: 🟡 Ready for deployment
**Dashboard**: http://178.156.129.179:9100

---

## Executive Summary

You have:
✅ Prepared comprehensive Dokploy deployment guides
✅ Created Telegram notification feature (#030) with 98.89% test coverage
✅ Set up SSH access to VPS (178.156.129.179)
✅ Configured all deployment documentation

**Next Step**: Open Dokploy dashboard and deploy 3 services (trading-bot, api, redis)

---

## Documentation You Have

### 1. **DOKPLOY_DEPLOYMENT.md** (11 KB)
- High-level deployment architecture
- Service configuration options
- Multi-phase deployment strategy
- Rollback procedures
- Monitoring setup

**Use This For**: Understanding the overall architecture

---

### 2. **DOKPLOY_SSH_SETUP.md** (5.8 KB)
- SSH key configuration
- VPS access details
- Dokploy dashboard access
- Security best practices

**Use This For**: SSH troubleshooting, terminal access to VPS

---

### 3. **DOKPLOY_SETUP_WALKTHROUGH.md** (15 KB) ⭐ **START HERE**
- 10-part step-by-step guide
- Screenshots/instructions for dashboard
- How to create each service
- Environment variable configuration
- Health check setup
- Troubleshooting guide

**Use This For**: Actually setting up services in Dokploy

---

### 4. **DOKPLOY_ENV_VARS.md** (6.5 KB) ⭐ **NEEDED FOR WALKTHROUGH**
- Copy-paste environment variable templates
- Where to get each credential
- Security checklist
- Testing procedures

**Use This For**: Gathering and validating credentials before deployment

---

## Quick Start Path (30 minutes)

### Step 1: Gather Credentials (5 minutes)
**File**: DOKPLOY_ENV_VARS.md

What you need:
```
✓ Robinhood username
✓ Robinhood password
✓ Robinhood account ID
✓ Telegram bot token (from @BotFather)
✓ Telegram chat ID (from @userinfobot)
```

### Step 2: Access Dokploy Dashboard (1 minute)
**URL**: http://178.156.129.179:9100

What you should see:
- Dokploy login screen
- Your "RH Bot" project

### Step 3: Deploy Services (20 minutes)
**File**: DOKPLOY_SETUP_WALKTHROUGH.md (Parts 3-5)

Follow these in order:
1. **Part 3**: Create trading-bot service
2. **Part 4**: Create trading-bot-api service
3. **Part 5**: Create redis service

Each service takes 5-10 minutes:
- Configure basic settings
- Add environment variables (use template from DOKPLOY_ENV_VARS.md)
- Add storage volumes
- Click Deploy
- Watch logs until "Running" status

### Step 4: Verify Deployment (5 minutes)
**File**: DOKPLOY_SETUP_WALKTHROUGH.md (Parts 6-7)

Check:
- All 3 services show "Running" (green)
- API responds to health check
- Telegram notifications working
- Logs visible in dashboard

---

## Detailed Deployment Steps

### Phase 1: Pre-Deployment (Do Now)

- [ ] **Gather credentials**
  - Robinhood username
  - Robinhood password
  - Robinhood account ID
  - Telegram bot token
  - Telegram chat ID
  - Command: Read `DOKPLOY_ENV_VARS.md` "Variable Definitions" section

- [ ] **Test Telegram bot**
  ```bash
  python -m src.trading_bot.notifications.validate_config
  ```
  Expected: `[SUCCESS] All checks passed!`

- [ ] **Verify Robinhood credentials**
  - Try logging into robinhood.com
  - Note your account ID (6-8 digit number)

- [ ] **Check Dokploy dashboard is accessible**
  - Open: http://178.156.129.179:9100
  - See "RH Bot" project

### Phase 2: Service Creation (30 minutes)

**Service 1: trading-bot** (10 minutes)
- [ ] Follow: DOKPLOY_SETUP_WALKTHROUGH.md → Part 3
- [ ] Configure service basics
- [ ] Add environment variables (from DOKPLOY_ENV_VARS.md)
- [ ] Add volumes (3 mount points)
- [ ] Add health check
- [ ] Click Deploy
- [ ] Wait for "Running" status

**Service 2: trading-bot-api** (10 minutes)
- [ ] Follow: DOKPLOY_SETUP_WALKTHROUGH.md → Part 4
- [ ] Configure service basics
- [ ] Override command: `uvicorn api.app.main:app --host 0.0.0.0 --port 8000`
- [ ] Add environment variables (same as trading-bot)
- [ ] Add volumes (same as trading-bot)
- [ ] Add HTTP health check
- [ ] Click Deploy
- [ ] Wait for "Running" status

**Service 3: redis** (10 minutes)
- [ ] Follow: DOKPLOY_SETUP_WALKTHROUGH.md → Part 5
- [ ] Use image: `redis:7-alpine`
- [ ] Override command: `redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru`
- [ ] Add volume: `/data` → `/data/redis-data`
- [ ] Add command health check
- [ ] Click Deploy
- [ ] Wait for "Running" status

### Phase 3: Verification (10 minutes)

- [ ] **Check all services running**
  - trading-bot: Green circle, running
  - trading-bot-api: Green circle, running
  - redis: Green circle, running

- [ ] **Test API endpoint**
  ```bash
  curl http://178.156.129.179:8000/api/v1/health/healthz
  ```
  Expected: `{"status": "ok"}`

- [ ] **Check Telegram notifications**
  - Look for notification in Telegram chat
  - Or check logs: `docker logs trading-bot | grep -i telegram`

- [ ] **Monitor logs**
  - View each service's logs in Dokploy dashboard
  - Should see: "Running", "healthy", "connected"

- [ ] **Test trading bot**
  - Run in paper trading mode
  - Execute test trade
  - Verify Telegram notification arrives

---

## Common Issues & Fixes

### Issue: Service Stuck in "Creating"

**Fix**:
1. Click service → Logs
2. Look for error message
3. Common causes:
   - Missing environment variable → Add it
   - Port already in use → Use different port
   - Dockerfile error → Check syntax
4. Fix the issue, click Deploy again

### Issue: "Permission Denied" on Robinhood

**Fix**:
1. Test password works on robinhood.com
2. Check for special characters (!, @, #, $, %)
3. Check if 2FA is enabled (you may need to handle MFA)
4. Check if account is locked
5. Regenerate password if changed recently

### Issue: "Chat Not Found" on Telegram

**Fix**:
1. Verify chat ID is numeric (9-10 digits)
2. **NOT** a username (doesn't start with @)
3. Start the bot in Telegram:
   - Open Telegram app
   - Search for your bot name (created with @BotFather)
   - Send `/start`
4. Try validation again:
   ```bash
   python -m src.trading_bot.notifications.validate_config
   ```

### Issue: Redis Connection Refused

**Fix**:
1. Verify REDIS_URL is exactly: `redis://redis:6379/0`
2. **NOT**: localhost, 127.0.0.1, or VPS IP
3. Check Redis service is running (green)
4. Check logs: `docker logs redis`

---

## Success Criteria

✅ **Deployment is successful when:**

- [ ] All 3 services show "Running" in Dokploy
- [ ] API responds: `curl http://178.156.129.179:8000/api/v1/health/healthz`
- [ ] Telegram test message appears in your chat
- [ ] No error messages in any service logs
- [ ] Trading bot logs show "Bot ready for trading"
- [ ] Redis logs show "Ready to accept connections"
- [ ] Services stay running for 5+ minutes without restarts

---

## Next Steps After Deployment

### Short-term (Today)

1. **Monitor for 24 hours**
   - Watch logs in Dokploy
   - Ensure services don't restart unexpectedly
   - Check memory/CPU usage

2. **Test live trading** (optional)
   - Start with very small position
   - Verify Telegram notifications arrive
   - Monitor for any errors

3. **Set up backups** (optional)
   ```bash
   ssh hetzner
   tar czf /backups/trading-bot-$(date +%Y%m%d).tar.gz /data/trading-bot
   ```

### Medium-term (This Week)

1. **Document your setup**
   - Save Dokploy dashboard screenshots
   - Document any custom configurations
   - Keep notes on what worked/what didn't

2. **Set up automated backups** (optional)
   - Use Dokploy backup feature
   - Or cron job: `0 2 * * * tar czf /backups/trading-bot-$(date +%Y%m%d).tar.gz /data/trading-bot`

3. **Monitor production performance**
   - Check notification delivery times
   - Monitor trading bot performance
   - Verify success rates

### Long-term (Next Month)

1. **Update to new versions**
   - New trading features
   - Performance improvements
   - Security patches

2. **Fine-tune configuration**
   - Adjust trading parameters
   - Optimize notification frequency
   - Configure monitoring alerts

3. **Consider High Availability** (optional)
   - Add database backup
   - Set up failover
   - Configure health monitoring

---

## Documentation Map

```
📁 Dokploy Configuration
├── DOKPLOY_DEPLOYMENT.md
│   └── High-level architecture & strategy
├── DOKPLOY_SSH_SETUP.md
│   └── VPS access & SSH configuration
├── DOKPLOY_SETUP_WALKTHROUGH.md ⭐
│   └── Step-by-step dashboard guide (USE THIS)
├── DOKPLOY_ENV_VARS.md ⭐
│   └── Environment variable reference (USE WITH WALKTHROUGH)
└── DOKPLOY_DEPLOYMENT_CHECKLIST.md (THIS FILE)
    └── Master checklist & troubleshooting

📁 Trading Bot
├── DEPLOYMENT_SUMMARY.md
│   └── Feature #030 completion summary
├── CHANGELOG.md
│   └── v1.7.0 release notes with Telegram notifications
└── docker-compose.yml
    └── Local Docker setup (for reference)
```

---

## Support

### If Something Goes Wrong

1. **Check Dokploy logs first**
   - Click service → Logs
   - Look for error messages

2. **Check service health**
   - Green circle = healthy
   - Red circle = unhealthy
   - Gray = stopped

3. **Reference troubleshooting**
   - DOKPLOY_SETUP_WALKTHROUGH.md → Part 9
   - DOKPLOY_ENV_VARS.md → Troubleshooting section

4. **Reset a service**
   - Click service → Settings
   - Click "Stop" or "Restart"
   - Wait for automatic restart

5. **Check VPS logs**
   ```bash
   ssh hetzner
   docker logs <service-name> -f
   ```

---

## Timeline

| Phase | Time | Status |
|-------|------|--------|
| Prepare credentials | 5 min | ⬜ TODO |
| Deploy trading-bot | 10 min | ⬜ TODO |
| Deploy trading-bot-api | 10 min | ⬜ TODO |
| Deploy redis | 10 min | ⬜ TODO |
| Verify all services | 5 min | ⬜ TODO |
| Test Telegram notifications | 5 min | ⬜ TODO |
| **TOTAL** | **~45 min** | |

---

## Ready to Deploy?

### Follow this order:

1. **Read**: DOKPLOY_ENV_VARS.md (5 min)
2. **Gather**: Your credentials (5 min)
3. **Open**: Dokploy dashboard (1 min)
4. **Follow**: DOKPLOY_SETUP_WALKTHROUGH.md (30 min)
   - Part 3: trading-bot
   - Part 4: trading-bot-api
   - Part 5: redis
5. **Verify**: Services running (5 min)
6. **Test**: Telegram notifications (2 min)

---

**Total Time**: ~48 minutes
**Difficulty**: Medium (dashboard navigation)
**Risk**: Low (can restart/redeploy easily)

---

**Status**: 🟢 Ready to deploy! Open http://178.156.129.179:9100 now.

