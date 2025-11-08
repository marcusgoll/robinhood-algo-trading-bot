# DEPLOYMENT FIX - Trading Bot on Dokploy

## Current Issue

Bot service `trading-bot-wkulrv` is failing with:
```
/usr/local/bin/python: No module named trading_bot
```

## Root Cause

VPS uses **Dokploy** (Docker Swarm platform). The service image was built incorrectly by Dokploy and lacks the `trading_bot` Python module.

## Solution: Fix via Dokploy Web UI

### Step 1: Access Dokploy

1. Open browser to your Dokploy URL (check your setup - usually `http://vps-ip:3000` or custom domain)
2. Login with your Dokploy credentials

### Step 2: Locate Trading Bot Application

1. Navigate to "Projects" or "Applications"
2. Find `trading-bot-wkulrv` or similar name
3. Click to open application settings

### Step 3: Verify Build Configuration

Check these settings:
- **Repository**: Should point to `https://github.com/marcusgoll/robinhood-algo-trading-bot`
- **Branch**: `main`
- **Dockerfile path**: `./Dockerfile` or `Dockerfile`
- **Build context**: `.` (root of repo)

### Step 4: Trigger Rebuild

1. Click "Redeploy" or "Rebuild" button
2. Monitor build logs in Dokploy UI
3. Look for:
   - ✅ `COPY src/ ./src/` - should copy trading_bot module
   - ✅ `pip install -r requirements.txt` - should complete
   - ✅ Image build success

### Step 5: Verify Deployment

After rebuild completes:
1. Check service status in Dokploy UI (should show "Running")
2. View logs - should see "TradingOrchestrator initialized" NOT "No module named trading_bot"

## Alternative: Deploy as Standalone Container (Not Recommended)

If Dokploy continues to fail, you can temporarily run standalone:

```bash
ssh hetzner

# Stop Dokploy service
docker service scale trading-bot-wkulrv=0

# Run standalone container
cd /opt/trading-bot
git pull
docker build -t trading-bot:latest -f Dockerfile .
docker run -d \
  --name trading-bot-standalone \
  --restart unless-stopped \
  -v /opt/trading-bot/logs:/app/logs \
  -v /opt/trading-bot/.env:/app/.env \
  -v /opt/trading-bot/config.json:/app/config.json \
  trading-bot:latest
```

**BUT:** This bypasses Dokploy management. Only use for testing.

## Verification Commands

```bash
# Check service status
ssh hetzner 'docker service ps trading-bot-wkulrv'

# View logs
ssh hetzner 'docker service logs trading-bot-wkulrv --tail 100'

# Check if orchestrator is running
ssh hetzner 'docker service logs trading-bot-wkulrv 2>&1 | grep -i "orchestrator initialized"'
```

## Expected Success Output

When working correctly, you should see:
```
TradingOrchestrator initialized in paper mode
Daily budget: $5.00
Scheduled workflows:
  - 6:30am EST: Pre-market screening
  ...
```

And you'll receive Telegram notifications when workflows run.

## Documentation Created

- `DEPLOYMENT.md` - Standard deployment procedures
- This file - Troubleshooting Dokploy issues

## Next Steps

1. Access Dokploy web UI
2. Trigger rebuild of trading-bot application
3. Monitor logs for successful start
4. Confirm Telegram notifications work

Once working, **document the Dokploy URL and access details** so we don't lose this information again.
