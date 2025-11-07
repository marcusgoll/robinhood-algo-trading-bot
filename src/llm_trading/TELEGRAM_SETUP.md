# Telegram Notifications Setup

Get real-time notifications for your LLM trading system via Telegram.

## What You'll Receive

**Morning (9am):**
- Watchlist generation started
- Final watchlist with top picks

**Trading Session (9:30am-4pm):**
- Trade entries with setup details
- Trade exits with P&L
- Circuit breaker alerts (if triggered)

**Evening (5pm):**
- Optimization started
- Parameter adjustments (auto-applied or pending approval)
- Optimization summary

**Daily:**
- End-of-day summary with metrics

## Setup Steps

### 1. Create Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Choose a name (e.g., "My Trading Bot")
4. Choose a username (e.g., "my_llm_trading_bot")
5. **BotFather will give you a bot token** - save this!

Example token: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789`

### 2. Get Your Chat ID

**Option A: Use @userinfobot**
1. Search for **@userinfobot** in Telegram
2. Send `/start`
3. Bot will reply with your chat ID

**Option B: Use @RawDataBot**
1. Search for **@RawDataBot** in Telegram
2. Send any message
3. Look for `"id"` field in the JSON response

Example chat ID: `123456789`

### 3. Start Your Bot

1. Search for your bot username in Telegram (e.g., @my_llm_trading_bot)
2. Click **START** or send `/start`

**IMPORTANT:** You must start the bot before it can send you messages!

### 4. Add Credentials to .env

Edit `D:\Coding\Stocks\.env` and add:

```env
# Telegram Notifications
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789
TELEGRAM_CHAT_ID=123456789
```

### 5. Test Notifications

```bash
cd llm_trading
python telegram_notifier.py
```

You should receive a test message on Telegram!

## Usage in LLM Trading System

Notifications are automatically sent by all components:

**Morning Screener:**
```python
from llm_screener import LLMScreener
from telegram_notifier import create_notifier

notifier = create_notifier()
notifier.notify_screener_start(20)

screener = LLMScreener(...)
watchlist = screener.generate_watchlist(...)

notifier.notify_watchlist_generated(watchlist)
```

**Rule Executor:**
```python
from rule_executor import RuleExecutor
from telegram_notifier import create_notifier

notifier = create_notifier()
notifier.notify_session_start()

executor = RuleExecutor(...)
# ... trading happens ...

notifier.notify_session_end(num_trades, daily_pnl)
```

**Optimizer:**
```python
from llm_optimizer import LLMOptimizer
from telegram_notifier import create_notifier

notifier = create_notifier()
notifier.notify_optimizer_start(autonomy_level=1)

optimizer = LLMOptimizer(...)
# ... optimization happens ...

notifier.notify_optimization_summary(num_proposals, num_applied, num_rejected)
```

## Notification Examples

### Watchlist Generated
```
📋 Watchlist Generated

5 stocks selected for trading:

• NVDA (75%)
  oversold_bounce - RSI 28 + touching lower BB + high volume...

• TSLA (68%)
  breakout - Breaking above resistance with strong volume...

• AAPL (72%)
  pullback_to_support - Pullback to 50-day MA with strong...

[...]
```

### Trade Entry
```
🟢 Trade Entry

Symbol: NVDA
Setup: oversold_bounce
Entry: $145.23 x 100 shares
Value: $14,523.00

Target: +2.0%
Stop: -1.0%
Max Hold: 120 min

Reason: RSI 28 + touching lower BB + high volume spike
```

### Trade Exit
```
✅ Trade Exit

Symbol: NVDA
Reason: take_profit

Entry: $145.23
Exit: $148.14

P&L: +$291.00 (+2.0%)
```

### Parameter Adjustment (Level 2)
```
✅ Parameter Adjustment

Status: AUTO-APPLIED

Parameter: rsi_oversold
Old: 30
New: 28

Reasoning: Win rate 42% suggests entries too early. Lowering RSI threshold to 28 catches deeper oversold bounces with better risk/reward.
```

### Circuit Breaker
```
🚨 CIRCUIT BREAKER TRIGGERED

Daily loss exceeded threshold:
Loss: -10.5%
Threshold: -10.0%

All positions closed.
Trading HALTED for safety.
```

## Disabling Notifications

To disable notifications (e.g., during testing):

**Option 1: Remove from .env**
```env
# Comment out or remove these lines
# TELEGRAM_BOT_TOKEN=...
# TELEGRAM_CHAT_ID=...
```

**Option 2: Disable in code**
```python
notifier = create_notifier(enabled=False)
```

## Troubleshooting

### "Telegram notifications disabled"
- Check that `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are in `.env`
- Verify you have `python-telegram-bot` installed: `pip install python-telegram-bot`

### "Test message failed to send"
- Verify bot token is correct (check with @BotFather)
- Verify chat ID is correct (check with @userinfobot)
- Make sure you clicked **START** on your bot
- Check your firewall/proxy settings

### "401 Unauthorized"
- Bot token is incorrect
- Get a new token from @BotFather

### "403 Forbidden"
- You haven't started the bot yet
- Search for your bot in Telegram and click **START**

### "Message not received"
- Wrong chat ID
- Double-check with @userinfobot
- Make sure it's YOUR chat ID, not the bot's ID

## Privacy & Security

- Bot token: Keep secret! Anyone with this can send messages as your bot
- Chat ID: Less sensitive, but still keep private
- Add to `.gitignore`: `.env` file should NEVER be committed to git
- Telegram messages: Only you and Telegram can see them (end-to-end encrypted)

## Advanced: Group Notifications

To send to a Telegram group:

1. Create a group in Telegram
2. Add your bot to the group (search for bot username)
3. Make bot admin (Settings → Administrators → Add)
4. Get group chat ID:
   - Add @RawDataBot to group
   - Send a message
   - Look for `"id"` (will be negative number like `-123456789`)
5. Use group chat ID in `.env`:
   ```env
   TELEGRAM_CHAT_ID=-123456789
   ```

## Cost

Telegram API is **100% FREE**. No limits, no API keys beyond the bot token.

## Support

- Telegram Bot API docs: https://core.telegram.org/bots/api
- BotFather commands: https://core.telegram.org/bots#6-botfather
- Can't find bot: Search for exact username (e.g., @my_llm_trading_bot)
