# Dokploy Environment Variables for RH Bot

**Date**: 2025-10-27
**Purpose**: Quick reference for environment variables to paste into Dokploy dashboard
**Format**: Copy-paste ready

---

## ⚠️ Before You Start

1. **Gather your credentials**:
   - Robinhood username and password
   - Robinhood account ID
   - Telegram bot token (from @BotFather)
   - Telegram chat ID (numeric, from @userinfobot)

2. **NEVER commit these to Git** - only put in Dokploy dashboard

3. **Test credentials first**:
   - Robinhood: Try logging in at robinhood.com
   - Telegram bot: Run `python -m src.trading_bot.notifications.validate_config`

---

## Environment Variables for RH Bot Project

### Trading Bot Service Variables

Add these variables when creating the **trading-bot** service in Dokploy:

```
PYTHONUNBUFFERED=1
PYTHONPATH=/app
TRADING_BOT_ENABLED=true
ROBINHOOD_USERNAME=your-email@example.com
ROBINHOOD_PASSWORD=your-robinhood-password
ROBINHOOD_ACCOUNT_ID=your-account-id-numbers
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=1234567890:ABCDEfghijklmnopqrstuvwxyz-ABCD
TELEGRAM_CHAT_ID=1234567890
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=INFO
```

### API Service Variables

Add these variables when creating the **trading-bot-api** service:

```
PYTHONUNBUFFERED=1
PYTHONPATH=/app
TRADING_BOT_ENABLED=true
ROBINHOOD_USERNAME=your-email@example.com
ROBINHOOD_PASSWORD=your-robinhood-password
ROBINHOOD_ACCOUNT_ID=your-account-id-numbers
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=1234567890:ABCDEfghijklmnopqrstuvwxyz-ABCD
TELEGRAM_CHAT_ID=1234567890
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=INFO
```

### Redis Service Variables

Redis doesn't need custom environment variables - it's pre-configured.

---

## Variable Definitions

### Robinhood Variables

| Variable | Value | How to Get | Example |
|----------|-------|-----------|---------|
| ROBINHOOD_USERNAME | Your Robinhood email | Account email | `john.doe@gmail.com` |
| ROBINHOOD_PASSWORD | Your Robinhood password | Account password | `MyPassword123!` |
| ROBINHOOD_ACCOUNT_ID | Account number (6-8 digits) | Robinhood app → Account → Account number | `1234567` |

**Where to find:**
1. Login at www.robinhood.com
2. Click profile icon (top right)
3. Select "Account"
4. Copy: Account Number (ROBINHOOD_ACCOUNT_ID)
5. Use your login email and password

### Telegram Variables

| Variable | Value | How to Get | Example |
|----------|-------|-----------|---------|
| TELEGRAM_BOT_TOKEN | Bot API token (format: `numbers:letters`) | @BotFather /newbot | `1234567890:ABCDEfghijklmnopqrstuvwxyz-ABCD` |
| TELEGRAM_CHAT_ID | Your numeric chat ID | @userinfobot /start | `9876543210` |

**Where to find:**
1. **TELEGRAM_BOT_TOKEN**:
   - Open Telegram
   - Search for @BotFather
   - Send: `/newbot`
   - Follow instructions
   - Copy the bot token (copy entire token including colon and letters)

2. **TELEGRAM_CHAT_ID**:
   - Open Telegram
   - Search for @userinfobot
   - Send: `/start`
   - Look for "Your user ID:" and copy the number
   - Start your bot (search for your bot name, send `/start`)

### Python Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| PYTHONUNBUFFERED | 1 | Don't buffer output (see logs in real-time) |
| PYTHONPATH | /app | Python can find modules |
| LOG_LEVEL | INFO | Show info-level logs (DEBUG for more details) |

### Redis Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| REDIS_URL | redis://redis:6379/0 | Connect to Redis service on internal network |

**Note**: `redis` is the service name in Dokploy, not localhost

### Other Variables

| Variable | Value | Required | Purpose |
|----------|-------|----------|---------|
| TRADING_BOT_ENABLED | true | YES | Enable bot startup |
| TELEGRAM_ENABLED | true | YES | Enable Telegram notifications |

---

## Copy-Paste Template

Replace the values in `<angle brackets>` with your actual credentials:

```
PYTHONUNBUFFERED=1
PYTHONPATH=/app
TRADING_BOT_ENABLED=true
ROBINHOOD_USERNAME=<your-robinhood-email>
ROBINHOOD_PASSWORD=<your-robinhood-password>
ROBINHOOD_ACCOUNT_ID=<your-6-8-digit-account-id>
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=<your-bot-token-with-colon>
TELEGRAM_CHAT_ID=<your-numeric-chat-id>
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=INFO
```

---

## Adding Variables to Dokploy

### Method 1: Add One at a Time

1. Click service in Dokploy
2. Click "Environment Variables"
3. Click "Add Variable"
4. **Name**: (e.g., `ROBINHOOD_USERNAME`)
5. **Value**: (e.g., `john.doe@gmail.com`)
6. Click "Save" or "Add"
7. Repeat for each variable

### Method 2: Bulk Import (if available)

1. Click service in Dokploy
2. Click "Environment Variables"
3. Click "Import" or "Bulk Edit"
4. Paste entire variable list (from Copy-Paste Template above)
5. Click "Save All"

### Method 3: Use Dokploy CLI (if configured)

Create `.env` file locally:
```bash
cat > .env.dokploy << 'EOF'
PYTHONUNBUFFERED=1
PYTHONPATH=/app
...
EOF
```

Then in Dokploy CLI:
```bash
dokploy env import .env.dokploy
```

---

## Security Checklist

Before deploying:

- [ ] Credentials are correct (test login)
- [ ] Bot token starts with numbers (not a channel name)
- [ ] Chat ID is numeric (not a username)
- [ ] Password is NOT in any Git files
- [ ] Variables NOT in `.env` that you committed
- [ ] Telegram bot has permission to message your chat
- [ ] Robinhood account has trading enabled

---

## Testing Variables

### Test Robinhood Credentials

```bash
python -c "
import os
from robinhood_python_client import Client

client = Client(
    username=os.getenv('ROBINHOOD_USERNAME'),
    password=os.getenv('ROBINHOOD_PASSWORD')
)
account = client.get_account(os.getenv('ROBINHOOD_ACCOUNT_ID'))
print(f'Account: {account.account_number}')
print(f'Status: Valid')
"
```

### Test Telegram Credentials

```bash
python -m src.trading_bot.notifications.validate_config
```

Expected output:
```
[SUCCESS] All checks passed!
```

---

## Troubleshooting

### "Permission denied" Error

**Issue**: Robinhood login fails

**Fix**:
1. Test password locally first
2. Check for special characters (!, @, #, etc.) - may need escaping
3. Check if account is locked (2FA needed?)
4. Check if account has trading enabled

### "Chat not found" Error

**Issue**: Telegram message won't send

**Fix**:
1. Verify chat ID is numeric (9-10 digits)
2. Verify bot has been started (send `/start` to bot in Telegram)
3. Verify bot is not blocked
4. Check bot is not in a private channel (use personal chat)

### "Cannot connect to Redis"

**Issue**: Redis URL is wrong

**Fix**:
1. **MUST be**: `redis://redis:6379/0`
2. NOT localhost or 127.0.0.1
3. NOT external IP
4. Service name is `redis` (as configured in Dokploy)

---

## Reference Files

- `DOKPLOY_SETUP_WALKTHROUGH.md` - Step-by-step Dokploy setup guide
- `DOKPLOY_DEPLOYMENT.md` - Full deployment architecture
- `DOKPLOY_SSH_SETUP.md` - SSH and VPS access configuration

---

**Status**: Ready to paste into Dokploy dashboard
**Last Updated**: 2025-10-27
