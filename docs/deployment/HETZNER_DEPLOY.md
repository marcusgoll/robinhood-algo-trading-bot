# Deploy Trading Bot to Hetzner VPS - Step by Step

**Time Required:** 15-20 minutes
**Monthly Cost:** ~€4.51 ($5/month)

---

## Prerequisites

✅ Hetzner Cloud account (sign up at: https://www.hetzner.com/cloud)
✅ SSH client installed (PuTTY on Windows, or built-in terminal on Mac/Linux)
✅ All API keys configured in local `.env` file

---

## Step 1: Create Hetzner VPS

### 1.1 Log into Hetzner Cloud Console

Go to: https://console.hetzner.cloud/

### 1.2 Create New Server

1. Click **"+ New Project"** or select existing project
2. Click **"Add Server"**

### 1.3 Configure Server

**Location:**
- Choose: **Ashburn, VA (US)** (closest to NYSE)
- Alternative: **Hillsboro, OR (US)**

**Image:**
- Select: **Ubuntu 22.04**

**Type:**
- Select: **Shared vCPU**
- Choose: **CPX11** (2 vCPU, 2 GB RAM, 40 GB SSD)
- Cost: €4.51/month

**Networking:**
- IPv4: ✓ (included)
- IPv6: ✓ (optional)

**SSH Keys:**
- Add your SSH public key (optional but recommended)
- Or use password authentication

**Name:**
- Name: `trading-bot-prod`

### 1.4 Create Server

Click **"Create & Buy Now"**

Wait 30-60 seconds for server to be created.

**Copy the IP address** - you'll need it!

---

## Step 2: Connect to VPS via SSH

### Windows (PowerShell or PuTTY):
```powershell
ssh root@YOUR_VPS_IP
```

### Mac/Linux:
```bash
ssh root@YOUR_VPS_IP
```

**First time connection:**
- Type `yes` when asked about authenticity
- Enter password (sent to your email if no SSH key)

---

## Step 3: Automated Setup Script

### 3.1 Download Setup Script

Once connected to VPS, run:

```bash
curl -o setup.sh https://raw.githubusercontent.com/marcusgoll/robinhood-algo-trading-bot/main/scripts/hetzner-setup.sh
```

Or, if you haven't pushed to GitHub yet:

```bash
# Create setup script manually
nano setup.sh
```

Then paste the contents from `scripts/hetzner-setup.sh` and save (Ctrl+X, Y, Enter).

### 3.2 Make Executable

```bash
chmod +x setup.sh
```

### 3.3 Run Setup

```bash
bash setup.sh
```

**This will:**
- ✓ Update Ubuntu packages
- ✓ Install Docker & Docker Compose
- ✓ Install Python 3.11
- ✓ Create `trading` user
- ✓ Clone repository
- ✓ Setup systemd service
- ✓ Configure firewall
- ✓ Setup automated backups

**Takes:** 3-5 minutes

---

## Step 4: Configure Credentials

### 4.1 Edit .env File

```bash
cd /opt/trading-bot
nano .env
```

**Add your credentials:**

```bash
# Robinhood
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_password
ROBINHOOD_MFA_SECRET=YOUR_16_CHAR_SECRET

# OpenAI (for LLM)
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BUDGET_MONTHLY=100.00

# Alpaca (market data)
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret

# Polygon (optional - order flow)
POLYGON_API_KEY=your_polygon_key

# API Authentication
BOT_API_AUTH_TOKEN=your_random_secure_token
```

**Save:** Ctrl+X, Y, Enter

### 4.2 Verify Config

```bash
cat config.json | grep -A 5 "llm\|trading"
```

Should show:
```json
{
  "trading": {
    "mode": "paper"  ← IMPORTANT: Start with paper!
  },
  "llm": {
    "enabled": true
  }
}
```

---

## Step 5: Build and Start Bot

### 5.1 Build Docker Images

```bash
cd /opt/trading-bot
sudo -u trading docker-compose build
```

**Takes:** 2-3 minutes

### 5.2 Start Services

```bash
sudo systemctl start trading-bot
```

### 5.3 Check Status

```bash
# Systemd status
sudo systemctl status trading-bot

# Docker containers
sudo -u trading docker-compose ps

# View logs
sudo -u trading docker-compose logs -f trading-bot
```

**Expected output:**
```
============================================================
  TRADING BOT RUNNING - 24/7 OPERATION
============================================================
Trading Hours: 07:00 - 10:00 America/New_York
[21:34:00] Outside trading hours - idle
```

---

## Step 6: Verify Everything Works

### 6.1 Check Bot Health

```bash
curl -H "X-API-Key: YOUR_API_TOKEN" http://localhost:8000/api/v1/health
```

**Should return:**
```json
{
  "status": "healthy",
  "circuit_breaker_active": false,
  "api_connected": true
}
```

### 6.2 Check LLM Integration

```bash
# View logs for LLM activity
sudo -u trading docker-compose logs -f | grep "LLM\|OpenAI"
```

### 6.3 Check Resource Usage

```bash
# CPU and Memory
sudo -u trading docker stats --no-stream

# Disk space
df -h /opt/trading-bot
```

---

## Step 7: Enable Auto-Start on Reboot

```bash
# Already enabled by setup script
# Verify:
sudo systemctl is-enabled trading-bot
```

Should output: `enabled`

**Test reboot:**
```bash
sudo reboot
```

Wait 2 minutes, then reconnect and check:
```bash
ssh root@YOUR_VPS_IP
sudo -u trading docker-compose ps
```

Bot should be running automatically!

---

## Step 8: Setup Monitoring (Optional)

### 8.1 Install Monitoring Script

```bash
cd /opt/trading-bot
nano scripts/monitor.sh
```

Add monitoring script (can send alerts to email/Slack).

### 8.2 Add to Cron

```bash
sudo crontab -e -u trading
```

Add:
```cron
*/15 * * * * /opt/trading-bot/scripts/monitor.sh
```

Runs every 15 minutes to check bot health.

---

## Management Commands

### View Logs
```bash
# All logs
sudo -u trading docker-compose logs -f

# Bot only
sudo -u trading docker-compose logs -f trading-bot

# Last 100 lines
sudo -u trading docker-compose logs --tail=100 trading-bot
```

### Restart Bot
```bash
sudo systemctl restart trading-bot
```

### Stop Bot
```bash
sudo systemctl stop trading-bot
```

### Update Code
```bash
cd /opt/trading-bot
sudo -u trading git pull
sudo -u trading docker-compose build --no-cache
sudo systemctl restart trading-bot
```

### View Backups
```bash
ls -lh /opt/trading-bot/backups/
```

### Manual Backup
```bash
sudo -u trading bash /opt/trading-bot/scripts/docker-backup.sh
```

---

## Troubleshooting

### Bot Won't Start

**Check logs:**
```bash
sudo journalctl -u trading-bot -n 50
sudo -u trading docker-compose logs trading-bot
```

**Common issues:**
- Missing `.env` file → Add credentials
- Invalid Robinhood credentials → Check `.env`
- Docker not running → `sudo systemctl start docker`

### Can't Connect via SSH

**Reset from Hetzner Console:**
1. Go to console.hetzner.cloud
2. Select your server
3. Click "Rescue" tab
4. Enable rescue mode
5. Reboot server

### Out of Memory

**Check usage:**
```bash
free -h
docker stats
```

**Add swap:**
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Firewall Blocking

**Check rules:**
```bash
sudo ufw status
```

**Allow port:**
```bash
sudo ufw allow 8000/tcp  # For API access
```

---

## Security Checklist

✅ **SSH:**
- [ ] SSH key authentication (recommended)
- [ ] Password authentication disabled
- [ ] Non-default SSH port (optional)

✅ **Firewall:**
- [ ] UFW enabled
- [ ] Only required ports open (22, 8000)

✅ **Credentials:**
- [ ] `.env` has 600 permissions
- [ ] API tokens are strong (32+ chars)

✅ **Updates:**
- [ ] System auto-updates enabled
- [ ] Docker images updated monthly

---

## Cost Breakdown

**Hetzner VPS:**
- CPX11: €4.51/month (~$5/month)
- Includes: 20GB SSD, 20TB traffic

**OpenAI API:**
- Pre-trade analysis: ~$0.50/month (with caching)

**Total:** ~$5.50/month

**For comparison:**
- Local PC (24/7): ~$10-15/month (electricity)
- AWS EC2 t2.micro: ~$8.50/month
- DigitalOcean Droplet: ~$6/month

**Hetzner = Best Value!**

---

## Performance Expectations

**CPX11 (2 vCPU, 2GB RAM):**
- ✓ Handles bot + API + Redis easily
- ✓ <20% CPU usage typical
- ✓ ~500MB RAM usage
- ✓ Plenty of headroom

**Can handle:**
- 100+ trades/day
- Multiple strategy scans
- LLM analysis per trade
- Historical backtesting

---

## Monitoring Dashboard

**Access API:** (from your local machine)

```bash
# Health check
curl -H "X-API-Key: YOUR_TOKEN" http://YOUR_VPS_IP:8000/api/v1/health

# Bot state
curl -H "X-API-Key: YOUR_TOKEN" http://YOUR_VPS_IP:8000/api/v1/state

# Interactive docs
# Open in browser: http://YOUR_VPS_IP:8000/api/docs
```

**Note:** Replace `YOUR_VPS_IP` with your actual IP address.

---

## Next Steps After Deployment

### Week 1: Paper Trading Validation
1. ☐ Monitor for 7 days straight
2. ☐ Check logs daily
3. ☐ Verify trades execute correctly
4. ☐ Review LLM analysis quality

### Week 2: Performance Analysis
1. ☐ Calculate win rate
2. ☐ Review risk/reward ratio
3. ☐ Analyze LLM cost
4. ☐ Check system resource usage

### Week 3: Optimization
1. ☐ Tune LLM prompts
2. ☐ Adjust trading hours if needed
3. ☐ Optimize cache hit rate
4. ☐ Fine-tune risk parameters

### Month 2: Consider Live Trading
1. ☐ Paper trading profitable?
2. ☐ Win rate ≥55%?
3. ☐ System stable?
4. ☐ Ready to risk real money?

**Only then:** Change `"mode": "paper"` → `"mode": "live"` in `config.json`

---

## Support

**Issues?**
- Check logs first: `sudo -u trading docker-compose logs -f`
- Review: `DEPLOYMENT_QUICKSTART.md`
- Full docs: `docs/` directory
- GitHub Issues: https://github.com/marcusgoll/robinhood-algo-trading-bot/issues

**Emergency Stop:**
```bash
sudo systemctl stop trading-bot
```

---

## Summary

**You now have:**
✅ Trading bot running 24/7 on Hetzner VPS
✅ Auto-restart on failure (systemd)
✅ Auto-start on reboot
✅ LLM-enhanced trade validation
✅ Automated daily backups
✅ Monitoring and logging
✅ Professional deployment

**Total time:** 15-20 minutes
**Monthly cost:** ~$5.50
**Maintenance:** ~10 minutes/week

**Your bot is now trading around the clock!**

---

**Last Updated:** 2025-10-26
**Tested On:** Ubuntu 22.04, Hetzner CPX11
