# Telegram Bot Monitoring Guide

## Status: ✅ ACTIVE

Your trading bot is configured to send real-time notifications to your Telegram account.

**Configuration**:
- Bot Token: `8418061509:AAHz7YWLXLrHVzmVXvzkt5y-cQzMlCcZXCE`
- Chat ID: `8088154013`
- Status: ENABLED ✅

---

## Notifications You'll Receive

### 🔔 Trading Alerts

#### Position Entry
```
🟢 POSITION ENTRY

Symbol: AAPL
Strategy: breakout
Entry: $150.00 x 100 shares
Total: $15,000.00

Stop Loss: $147.00 (-2.0%)
Target: $156.00 (+4.0%)

Mode: PAPER TRADING
```

#### Position Exit
```
✅ POSITION EXIT

Symbol: AAPL
Exit: $156.25 (+4.2%)

Entry: $150.00 → Exit: $156.25
P&L: +$625.00 (+4.2%)
Hold: 2h 15m

Reason: Take profit target hit
Mode: PAPER TRADING
```

### 🪙 Crypto Screening (Every 2 Hours)

```
🔍 Crypto Screening Started

Analyzing 8 symbols:
BTC/USD, ETH/USD, LTC/USD, BCH/USD
LINK/USD, UNI/USD, AVAX/USD, MATIC/USD
```

```
✅ Screening Complete

Found 2 candidates:
• BTC/USD - Strong uptrend, RSI 45
• ETH/USD - Breaking resistance
```

### 📈 Stock Screening

#### Pre-Market (6:30 AM EST)
```
🔍 Pre-Market Screening Started

Scanning watchlist for setups...
```

#### Screening Complete
```
✅ Watchlist Generated

45 symbols screened:
• 20 mega-cap
• 25 large-cap

Top candidates:
• NVDA - Momentum breakout
• TSLA - Oversold bounce
• AAPL - Bull flag pattern
```

### 🚨 Risk Alerts

#### Circuit Breaker
```
🚨 CIRCUIT BREAKER TRIGGERED

Daily loss: -$350.00 (-5.2%)
Threshold: -$300.00 (-5.0%)

Action: All positions closed
Status: Trading HALTED
```

#### Position Risk
```
⚠️ RISK ALERT

Symbol: NVDA
Current: $145.00
Stop Loss: $147.00

Position underwater -$200
Monitor closely
```

### 📊 Daily Summaries

#### End of Day (4:00 PM EST)
```
📊 END-OF-DAY SUMMARY

Date: 2025-11-10
Mode: Paper Trading

Trades: 5 total
Win Rate: 60% (3W / 2L)

P&L: +$425.00 (+1.3%)
Best: NVDA +$300.00
Worst: TSLA -$125.00

Portfolio: $32,695.76
```

### 🤖 LLM Activity

#### Multi-Agent Decisions
```
🤖 LLM Analysis Complete

Consensus: 6/8 agents agree
Recommendation: BUY AAPL

Confidence: 75%
Cost: $0.0012

Entry: $150.00
Target: $156.00 (+4.0%)
Stop: $147.00 (-2.0%)
```

### ⚙️ System Events

#### Bot Startup
```
✅ Trading Bot Started

Environment: Production VPS
Mode: Paper Trading
Balance: $32,270.76

Orchestrators:
• Stock: ACTIVE
• Crypto: ACTIVE (24/7)

Next screening: 6:30 AM EST
```

#### Configuration Changes
```
⚙️ Configuration Updated

Change: Stop loss threshold
Old: 2.0% → New: 2.5%

Reason: Reduce whipsaw exits
Applied: Immediately
```

---

## Notification Schedule

### Stock Trading (EST/EDT)
- **6:30 AM** - Pre-market screening starts
- **9:30 AM** - Market open, execution begins
- **10:00 AM - 3:00 PM** - Hourly monitoring (6 scans)
- **4:00 PM** - End-of-day review
- **6:00 PM, 8:00 PM, 10:00 PM** - After-hours scans

**Total**: 13 stock scans per day

### Crypto Trading (24/7)
- **Every 2 hours** - Screening run (12x per day)
- **Every 5 minutes** - Position monitoring (288x per day)
- **Daily** - Portfolio rebalancing

### Risk Alerts
- **Immediate** - Circuit breakers
- **Immediate** - Stop loss hits
- **Immediate** - Target hits
- **Rate Limited** - Errors (max 1 per hour per type)

---

## Controlling Notifications

### Disable All Notifications

Edit `/opt/trading-bot/.env` on VPS:
```bash
ssh hetzner
nano /opt/trading-bot/.env

# Change this line:
TELEGRAM_ENABLED=false

# Restart container:
docker restart trading-bot-standalone
```

### Selective Notifications

Control what you receive:
```env
# Position trades
TELEGRAM_NOTIFY_POSITIONS=true   # Entry/exit notifications

# Risk alerts
TELEGRAM_NOTIFY_ALERTS=true      # Circuit breakers, stop losses

# Message formatting
TELEGRAM_INCLUDE_EMOJIS=true     # Visual indicators
TELEGRAM_PARSE_MODE=Markdown     # Rich text formatting
```

### Rate Limiting

Prevent notification spam:
```env
# Max 1 error notification per type per 60 minutes
TELEGRAM_ERROR_RATE_LIMIT_MINUTES=60
```

---

## Testing Notifications

### Send Test Message

```bash
ssh hetzner
docker exec trading-bot-standalone python3 -c "
import asyncio
import os
import sys
sys.path.insert(0, '/app/src')

async def test():
    from trading_bot.notifications.telegram_client import TelegramClient
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    client = TelegramClient(bot_token=token, timeout=5.0)

    response = await client.send_message(
        chat_id=chat_id,
        text='✅ Trading bot test notification',
        parse_mode='Markdown'
    )

    print('✅ Sent!' if response.success else f'❌ Failed: {response.error_message}')

asyncio.run(test())
"
```

---

## Troubleshooting

### Not Receiving Notifications

1. **Check bot is running**:
   ```bash
   ssh hetzner
   docker ps | grep trading-bot
   ```

2. **Verify Telegram config**:
   ```bash
   docker exec trading-bot-standalone env | grep TELEGRAM
   ```

3. **Check logs**:
   ```bash
   docker logs trading-bot-standalone | grep -i telegram
   ```

4. **Test bot token**:
   - Open Telegram
   - Search for your bot username
   - Send `/start` command
   - Should reply "Bot is active"

### Common Issues

#### "403 Forbidden"
- **Problem**: Haven't started the bot
- **Fix**: Search for bot in Telegram, click START

#### "Chat not found"
- **Problem**: Wrong chat ID
- **Fix**: Use @userinfobot to get your chat ID

#### "Unauthorized"
- **Problem**: Invalid bot token
- **Fix**: Get new token from @BotFather

#### Notifications delayed
- **Problem**: Network latency or rate limiting
- **Fix**: Check VPS network, verify rate limits

### Checking Notification Logs

```bash
# On VPS
ssh hetzner
cd /opt/trading-bot/logs

# View notification history
cat telegram-notifications.jsonl | tail -20

# Count successful notifications
grep '"status":"success"' telegram-notifications.jsonl | wc -l
```

---

## Interactive Commands (Coming Soon)

Your bot supports interactive commands for real-time control:

```
/status - Get current bot status
/portfolio - View current positions
/stop - Emergency stop trading
/watchlist - View active watchlist
/metrics - Daily performance metrics
```

**Note**: Command handlers require `TELEGRAM_AUTHORIZED_USER_IDS` to be configured.

---

## Privacy & Security

### What's Sent to Telegram
- Trade entries and exits (paper trading only)
- Performance metrics
- System status updates
- Risk alerts

### What's NOT Sent
- API credentials
- Database credentials
- Full position details
- Personal information

### Telegram Message Security
- Messages are end-to-end encrypted by Telegram
- Only you and Telegram can read them
- Bot token allows sending messages only (not reading)

### Protecting Your Bot Token

**Never commit to git**:
```bash
# Always in .gitignore
.env
```

**Rotate if exposed**:
1. Open Telegram → @BotFather
2. Send `/revoke`
3. Get new token
4. Update `.env` on VPS
5. Restart container

---

## Notification Examples in Production

### First Trade of the Day
```
🟢 POSITION ENTRY #1

Symbol: NVDA
Setup: bull-flag-breakout
Entry: $500.00 x 50 shares
Total: $25,000.00

Stop: $490.00 (-2.0%)
Target: $520.00 (+4.0%)

Confidence: 85% (LLM consensus 7/8)
Mode: PAPER TRADING
Time: 9:35 AM EST
```

### Circuit Breaker Event
```
🚨 CIRCUIT BREAKER TRIGGERED

Loss: -$350.00 (-5.2%)
Threshold: -$300.00 (-5.0%)

Positions Closed:
• NVDA: -$200.00
• TSLA: -$150.00

Status: HALTED until tomorrow
Next screening: 6:30 AM EST
```

### Crypto Opportunity
```
🪙 CRYPTO ALERT

Symbol: BTC/USD
Signal: Strong momentum + volume spike
Current: $67,500
Change: +2.3% (24h)

RSI: 52 (neutral)
Volume: 150% average

Recommendation: Monitor for breakout
Entry Zone: $68,000-$68,500
```

---

## Next Steps

1. ✅ Telegram is configured and working
2. ⏳ Wait for first screening run (next: 6:00 PM EST)
3. 📱 Check Telegram for notification
4. 🔄 Monitor throughout the day
5. 📊 Review end-of-day summary (4:00 PM EST)

---

## Support

**Issues with notifications?**
1. Check this guide first
2. Review logs: `/opt/trading-bot/logs/`
3. Test with script above
4. Verify bot token with @BotFather

**Configuration**:
- File: `/opt/trading-bot/.env`
- Section: `TELEGRAM NOTIFICATIONS`
- Required: `TELEGRAM_ENABLED`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

---

**Last Updated**: 2025-11-10
**Status**: ✅ Operational
**Next Notification**: Crypto screening (every 2 hours)
