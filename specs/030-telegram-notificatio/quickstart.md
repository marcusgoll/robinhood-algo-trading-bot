# Quickstart: telegram-notificatio

## Scenario 1: Initial Setup

### Step 1: Create Telegram Bot

```bash
# 1. Open Telegram app, search for @BotFather
# 2. Send /newbot command
# 3. Follow prompts to name your bot (e.g., "My Trading Bot")
# 4. Copy the API token (format: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11)
```

### Step 2: Get Your Chat ID

```bash
# Method 1: Using @userinfobot
# 1. Search for @userinfobot on Telegram
# 2. Send /start command
# 3. Copy your chat ID (numeric, e.g., 123456789)

# Method 2: Using API (after creating bot)
# 1. Send a message to your bot (e.g., "Hello")
# 2. Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
# 3. Find "chat":{"id":123456789} in JSON response
```

### Step 3: Configure Environment Variables

```bash
# Edit .env file in project root
cd D:/Coding/Stocks

# Add Telegram configuration section (copy from .env.example)
cat >> .env <<'EOF'

# ============================================
# TELEGRAM NOTIFICATIONS (Feature 030)
# ============================================
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789
TELEGRAM_NOTIFY_POSITIONS=true
TELEGRAM_NOTIFY_ALERTS=true
TELEGRAM_PARSE_MODE=Markdown
TELEGRAM_INCLUDE_EMOJIS=true
EOF
```

### Step 4: Install Dependencies

```bash
# Add python-telegram-bot to requirements.txt
echo "python-telegram-bot==20.7  # Telegram notifications (Feature 030)" >> requirements.txt

# Install dependencies (using pip or uv)
pip install python-telegram-bot==20.7

# Or using uv (if in project)
uv pip install python-telegram-bot==20.7
```

### Step 5: Verify Configuration

```bash
# Run configuration validator (test script)
python -m trading_bot.notifications.validate_config

# Expected output:
# ✅ TELEGRAM_ENABLED: true
# ✅ TELEGRAM_BOT_TOKEN: configured (123456:ABC-DEF...)
# ✅ TELEGRAM_CHAT_ID: 123456789
# ✅ Bot API connection: OK
# ✅ Chat accessible: OK
```

---

## Scenario 2: Testing Notifications

### Manual Test: Send Test Notification

```python
# Create test script: scripts/test_telegram_notification.py

import asyncio
from trading_bot.notifications import NotificationService
from trading_bot.logging.trade_record import TradeRecord
from decimal import Decimal
from datetime import datetime

async def test_position_entry():
    """Test position entry notification."""
    service = NotificationService()

    # Create mock trade record
    trade = TradeRecord(
        timestamp=datetime.utcnow().isoformat(),
        symbol="AAPL",
        action="BUY",
        quantity=50,
        price=Decimal("150.25"),
        total_value=Decimal("7512.50"),
        order_id="test-order-001",
        execution_mode="PAPER",
        account_id=None,
        strategy_name="manual-test",
        entry_type="test",
        stop_loss=Decimal("148.50"),
        target=Decimal("155.00"),
        decision_reasoning="Manual test of Telegram notification",
        indicators_used=["manual"],
        risk_reward_ratio=2.5,
        outcome="open",
        profit_loss=None,
        hold_duration_seconds=None,
        exit_timestamp=None,
        exit_reasoning=None,
        slippage=None,
        commission=None,
        net_profit_loss=None,
        session_id="test-session",
        bot_version="1.0.0",
        config_hash="test-hash"
    )

    # Send notification
    result = await service.send_position_entry(trade)

    print(f"Notification sent: {result.delivery_status}")
    print(f"Message ID: {result.id}")
    print(f"Sent at: {result.sent_at}")

if __name__ == "__main__":
    asyncio.run(test_position_entry())
```

```bash
# Run test script
python scripts/test_telegram_notification.py

# Check Telegram app - should receive message:
# 📈 **Position Opened [PAPER]**
#
# **Symbol**: AAPL
# **Entry**: $150.25
# **Shares**: 50
# **Position Size**: $7,512.50
# **Stop Loss**: $148.50
# **Target**: $155.00
```

### Integration Test: Full Trading Flow

```bash
# Run bot in paper trading mode with notifications enabled
export PAPER_TRADING=true
export TELEGRAM_ENABLED=true

# Start bot (will send notifications on trade entry/exit)
python -m trading_bot

# Expected Telegram notifications during trading session:
# 1. Position entry notification when trade enters
# 2. Position exit notification when trade closes (with P&L)
# 3. Risk alert if circuit breaker triggers
```

---

## Scenario 3: Validation & Debugging

### Check Notification Logs

```bash
# View notification delivery log
cat logs/telegram-notifications.jsonl

# Query successful notifications
jq 'select(.delivery_status == "sent")' logs/telegram-notifications.jsonl

# Query failed notifications
jq 'select(.delivery_status == "failed")' logs/telegram-notifications.jsonl

# Count notifications by type
jq -r '.notification_type' logs/telegram-notifications.jsonl | sort | uniq -c
```

### Check Notification Metrics

```python
# Query notification success rate from logs
import json
from pathlib import Path

log_file = Path("logs/telegram-notifications.jsonl")

notifications = []
with open(log_file) as f:
    for line in f:
        notifications.append(json.loads(line))

total = len(notifications)
sent = sum(1 for n in notifications if n['delivery_status'] == 'sent')
failed = sum(1 for n in notifications if n['delivery_status'] == 'failed')

success_rate = (sent / total * 100) if total > 0 else 0

print(f"Total notifications: {total}")
print(f"Sent: {sent}")
print(f"Failed: {failed}")
print(f"Success rate: {success_rate:.2f}%")

# Target: >99% (NFR-002 from spec.md)
```

### Debug Common Issues

```bash
# Issue 1: "Unauthorized" error (invalid bot token)
# Fix: Verify TELEGRAM_BOT_TOKEN in .env matches BotFather token
cat .env | grep TELEGRAM_BOT_TOKEN

# Issue 2: "Chat not found" error (invalid chat ID)
# Fix: Verify TELEGRAM_CHAT_ID in .env
# - Send /start to your bot in Telegram
# - Re-check chat ID using getUpdates API
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates"

# Issue 3: Notifications not sending (TELEGRAM_ENABLED=false)
# Fix: Enable notifications in .env
sed -i 's/TELEGRAM_ENABLED=false/TELEGRAM_ENABLED=true/' .env

# Issue 4: Rate limiting errors (429 Too Many Requests)
# Fix: Check error notification rate limit configuration
cat .env | grep TELEGRAM_ERROR_RATE_LIMIT_MINUTES
# Increase from 60 to 120 if too aggressive

# Issue 5: No notifications received but no errors in logs
# Fix: Check Telegram notification settings
# - Ensure bot is not blocked in Telegram
# - Check if disable_notification flag is set to true (should be false)
```

### Run Unit Tests

```bash
# Run all notification tests
pytest tests/notifications/ -v

# Run specific test file
pytest tests/notifications/test_message_formatter.py -v

# Run with coverage
pytest tests/notifications/ --cov=trading_bot.notifications --cov-report=term-missing

# Expected coverage: >90% (Constitution requirement)
```

---

## Scenario 4: Disable Notifications (Rollback)

```bash
# Temporarily disable without removing configuration
# Edit .env
sed -i 's/TELEGRAM_ENABLED=true/TELEGRAM_ENABLED=false/' .env

# Restart bot
# Notifications will be skipped, trading continues normally

# Verify disabled in logs
grep "Telegram notifications disabled" logs/trading_bot.log

# Re-enable when ready
sed -i 's/TELEGRAM_ENABLED=false/TELEGRAM_ENABLED=true/' .env
```

---

## Scenario 5: Production Deployment (Docker)

```bash
# 1. Update .env on VPS with production credentials
ssh user@your-vps.com
cd /opt/trading-bot
nano .env
# Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# 2. Rebuild Docker containers
docker-compose down
docker-compose build
docker-compose up -d

# 3. Verify notifications working
docker-compose logs -f trading-bot | grep "Telegram notification sent"

# 4. Check Telegram app for test message
docker-compose exec trading-bot python scripts/test_telegram_notification.py

# 5. Monitor notification delivery rate
docker-compose exec trading-bot python -c "
from pathlib import Path
import json

log_file = Path('/app/logs/telegram-notifications.jsonl')
if log_file.exists():
    with open(log_file) as f:
        notifications = [json.loads(line) for line in f]
    sent = sum(1 for n in notifications if n['delivery_status'] == 'sent')
    total = len(notifications)
    print(f'Delivery rate: {sent}/{total} ({sent/total*100:.2f}%)')
else:
    print('No notifications sent yet')
"
```

---

## Environment Variable Reference

```bash
# Required
TELEGRAM_ENABLED=true                    # Enable/disable notifications
TELEGRAM_BOT_TOKEN=<token>               # From @BotFather
TELEGRAM_CHAT_ID=<chat_id>               # Your chat ID (numeric)

# Optional (with defaults)
TELEGRAM_NOTIFY_POSITIONS=true           # Position entry/exit notifications
TELEGRAM_NOTIFY_ALERTS=true              # Circuit breaker and risk alerts
TELEGRAM_NOTIFY_ERRORS=true              # System error notifications (future)
TELEGRAM_NOTIFY_SUMMARIES=true           # Daily/weekly summaries (future)
TELEGRAM_PARSE_MODE=Markdown             # Message formatting (Markdown|HTML|None)
TELEGRAM_INCLUDE_EMOJIS=true             # Use emojis in messages
TELEGRAM_ERROR_RATE_LIMIT_MINUTES=60     # Max 1 error notification per N minutes
TELEGRAM_SUMMARY_TIME=16:00              # Daily summary time (future)
```

---

## Troubleshooting Tips

1. **Start with PAPER_TRADING=true**: Test notifications without risking real trades
2. **Check logs first**: `logs/telegram-notifications.jsonl` and `logs/trading_bot.log`
3. **Verify bot token**: Use getMe API: `curl https://api.telegram.org/bot<TOKEN>/getMe`
4. **Test manually**: Run `scripts/test_telegram_notification.py` before live trading
5. **Monitor delivery rate**: Target >99% success (NFR-002 requirement)

