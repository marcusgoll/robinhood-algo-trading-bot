# Quickstart: telegram-command-handlers

## Prerequisites

- Trading bot running (src/trading_bot/main.py)
- FastAPI server running on port 8000
- Telegram bot created via @BotFather
- Telegram user ID obtained (via @userinfobot)

---

## Scenario 1: Initial Setup (First Time)

### Step 1: Configure environment variables

```bash
# Edit .env file
cd /d/Coding/Stocks

# Add Telegram command handler config
echo "TELEGRAM_AUTHORIZED_USER_IDS=123456789,987654321" >> .env
echo "TELEGRAM_COMMAND_COOLDOWN_SECONDS=5" >> .env

# Verify existing Telegram config (from Feature #030)
grep TELEGRAM_BOT_TOKEN .env  # Should exist
grep TELEGRAM_CHAT_ID .env    # Should exist
grep BOT_API_AUTH_TOKEN .env  # Should exist
```

### Step 2: Start bot with command handler

```bash
# Start all services via Docker Compose
docker-compose up -d

# OR start manually for development
# Terminal 1: Start API server
cd api
uvicorn app.main:app --reload --port 8000

# Terminal 2: Start trading bot with Telegram
cd src
python -m trading_bot.main
```

### Step 3: Verify command handler is running

```bash
# Check logs for initialization
docker-compose logs bot | grep "TelegramCommandHandler"

# Expected output:
# [INFO] TelegramCommandHandler initialized with 2 authorized users
# [INFO] Registered 7 command handlers: /start, /status, /pause, /resume, /positions, /performance, /help
# [INFO] Rate limit: 5 seconds per user
# [INFO] Command handler started
```

### Step 4: Send first command from Telegram

1. Open Telegram app on mobile
2. Find your bot (search by @bot_username from @BotFather)
3. Send: `/start`
4. Expected response:
   ```
   🤖 Welcome to Trading Bot Command Center!

   I can help you monitor and control your trading bot remotely.

   **Available Commands**:
   - /status - Check current bot status
   - /positions - View open positions
   - /performance - See trading metrics
   - /pause - Pause trading
   - /resume - Resume trading
   - /help - Show all commands

   **Authorization**: ✅ Authorized

   Send /help to see detailed command descriptions.
   ```

---

## Scenario 2: Testing All Commands

### /status - Check bot status

**Send**: `/status`

**Expected Response**:
```
📊 **Bot Status**

**Mode**: 🟢 Running
**Positions**: 2 open (+$125.50 / +2.3%)
**Account**: $10,500.00 (BP: $8,200.00)
**Last Signal**: 5 minutes ago
**Circuit Breakers**: None active

_Updated: 2025-10-27 14:30:00 UTC_
```

**Verification**:
- Mode matches bot actual state (running/paused)
- Position count matches GET /api/v1/summary
- P&L values are accurate
- Response time <3 seconds

---

### /positions - View open positions

**Send**: `/positions`

**Expected Response**:
```
💼 **Open Positions** (2)

**AAPL** 🟢
Entry: $150.00 | Current: $152.50
P/L: +$250.00 (+1.67%)
Size: 100 shares | Hold: 2h 15m

**MSFT** 🔴
Entry: $350.00 | Current: $348.00
P/L: -$100.00 (-0.57%)
Size: 50 shares | Hold: 45m

**Total P/L**: +$150.00 (+0.75%)

_Updated: 2025-10-27 14:30:00 UTC_
```

**Verification**:
- Position count matches bot state
- P&L calculations are correct
- Emoji indicators: 🟢 profit, 🔴 loss
- Hold duration formatted as human-readable

---

### /performance - Trading metrics

**Send**: `/performance`

**Expected Response**:
```
📈 **Performance Metrics**

**Win Rate**: 65.2% (30W / 16L)
**Total P/L**: +$2,450.00 (+24.5%)
**Streak**: 🔥 3 wins
**Best Trade**: +$850.00 (NVDA)
**Worst Trade**: -$320.00 (TSLA)

_Last 50 trades | Updated: 2025-10-27 14:30:00 UTC_
```

**Verification**:
- Win rate calculation: (30 / 46) * 100 = 65.2%
- Matches GET /api/v1/state performance field
- Streak shows consecutive wins/losses

---

### /pause - Pause trading

**Send**: `/pause`

**Expected Response**:
```
⏸️ **Trading Paused**

Bot will stop accepting new signals.
Existing positions remain open.

Paused at: 2025-10-27 14:35:00 UTC
User: @trader_joe

Send /resume to resume trading.
```

**Verification**:
- Bot status changes to "paused"
- New signals are rejected
- Existing positions untouched
- Audit log shows pause action with user ID

**Check logs**:
```bash
docker-compose logs bot | grep "telegram_command_executed"
# Expected:
# {"event": "telegram_command_executed", "command": "pause", "user_id": 123456789, "success": true}
```

---

### /resume - Resume trading

**Send**: `/resume`

**Expected Response**:
```
▶️ **Trading Resumed**

Bot is now accepting new signals.

Resumed at: 2025-10-27 14:40:00 UTC
User: @trader_joe

Send /status to check current state.
```

**Verification**:
- Bot status changes to "running"
- Signal processing resumes
- Audit log shows resume action

---

### /help - Show command list

**Send**: `/help`

**Expected Response**:
```
🤖 **Available Commands**

**/start** - Welcome message
**/status** - Current bot status
**/pause** - Pause trading (keeps positions)
**/resume** - Resume trading
**/positions** - List open positions
**/performance** - Show win rate and P&L
**/help** - This message

**Authorization**: ✅ Authorized

_Rate limit: 1 command per 5 seconds_
```

---

## Scenario 3: Error Handling Tests

### Test 1: Unauthorized user

**Setup**: Send command from Telegram account NOT in TELEGRAM_AUTHORIZED_USER_IDS

**Send**: `/status`

**Expected Response**:
```
❌ **Unauthorized Access**

You are not authorized to use this bot.

Contact the bot administrator to request access.
```

**Verification**:
- No bot state revealed
- Audit log shows auth failure
- User ID logged for security monitoring

**Check logs**:
```bash
docker-compose logs bot | grep "telegram_auth_failed"
# Expected:
# {"event": "telegram_auth_failed", "user_id": 999999999, "command": "status"}
```

---

### Test 2: Rate limit enforcement

**Setup**: Send 3 commands rapidly (within 5 seconds)

**Send**:
1. `/status` (succeeds)
2. `/positions` (within 2 seconds - rate limited)

**Expected Response (command 2)**:
```
⏱️ **Rate Limit Exceeded**

Please wait 3 more seconds before sending another command.

Rate limit: 1 command per 5 seconds
```

**Verification**:
- Second command blocked
- Cooldown message shows remaining time
- Rate limit resets after 5 seconds

---

### Test 3: API failure handling

**Setup**: Stop FastAPI server (simulate API downtime)

```bash
docker-compose stop api
```

**Send**: `/status`

**Expected Response**:
```
❌ **Service Temporarily Unavailable**

Unable to fetch bot status. Please try again in a moment.

If the issue persists, check bot logs.
```

**Verification**:
- Graceful error message (no stack trace)
- Error logged with context
- Command handler remains available

**Restart API**:
```bash
docker-compose start api
```

---

### Test 4: Unknown command

**Send**: `/unknown_command`

**Expected Response**:
```
❓ **Unknown Command**

I don't recognize that command.

Send /help to see available commands.
```

---

## Scenario 4: Integration Testing

### Full workflow test

```bash
# 1. Send /start (verify handler active)
# 2. Send /status (verify API integration)
# 3. Send /positions (verify position formatting)
# 4. Send /pause (verify control endpoint)
# 5. Verify bot stops accepting signals
# 6. Send /status (verify status shows "paused")
# 7. Send /resume (verify control endpoint)
# 8. Verify bot resumes signal processing
# 9. Send /performance (verify metrics calculation)
# 10. Send /help (verify documentation)
```

**Success Criteria**:
- All commands respond within 3 seconds
- No errors in logs
- Audit trail shows all 10 commands
- Rate limits enforced between commands

---

## Scenario 5: Load Testing

### Rate limit stress test

```bash
# Send 20 commands rapidly (automated)
# Expected: 1 success, 19 rate limited
# Verify: No API overload, graceful degradation
```

### Concurrent user test

```bash
# 3 authorized users send commands simultaneously
# Expected: All succeed (if rate limits respected)
# Verify: Per-user rate limiting works correctly
```

---

## Scenario 6: Manual Testing Checklist

### Mobile UX verification

- [ ] Open Telegram on mobile device
- [ ] Send `/status` - verify readability on small screen
- [ ] Check emoji rendering (🟢, 🔴, 📊, 💰)
- [ ] Verify markdown formatting (bold, code blocks)
- [ ] Test landscape orientation
- [ ] Test dark mode (Telegram theme)

### Response time verification

- [ ] Send `/help` - expect <500ms
- [ ] Send `/status` - expect <3s
- [ ] Send `/positions` - expect <3s
- [ ] Send `/pause` - expect <2s
- [ ] Send `/resume` - expect <2s

**Measure response time**:
```bash
# Check logs for response_time_ms field
docker-compose logs bot | grep "response_time_ms"
```

---

## Scenario 7: Debugging & Monitoring

### Check command handler status

```bash
# View command handler logs
docker-compose logs -f bot | grep "Telegram"

# View audit trail
docker-compose logs bot | grep "telegram_command_executed"

# View auth failures
docker-compose logs bot | grep "telegram_auth_failed"

# View rate limits
docker-compose logs bot | grep "telegram_rate_limited"
```

### Monitor API calls

```bash
# View API requests from command handler
docker-compose logs api | grep "GET /api/v1"

# Check for 401 Unauthorized (auth misconfiguration)
docker-compose logs api | grep "401"

# Check for 500 errors (API failures)
docker-compose logs api | grep "500"
```

### Verify environment configuration

```bash
# Check Telegram config
docker-compose exec bot env | grep TELEGRAM

# Expected output:
# TELEGRAM_BOT_TOKEN=123456789:ABC...
# TELEGRAM_AUTHORIZED_USER_IDS=123456789,987654321
# TELEGRAM_COMMAND_COOLDOWN_SECONDS=5
# TELEGRAM_ENABLED=true

# Check API config
docker-compose exec bot env | grep BOT_API

# Expected:
# BOT_API_AUTH_TOKEN=...
# BOT_API_PORT=8000
```

---

## Troubleshooting

### Command handler not responding

**Symptom**: No response from bot when sending commands

**Diagnosis**:
```bash
# Check if bot is running
docker-compose ps

# Check if command handler initialized
docker-compose logs bot | grep "TelegramCommandHandler"

# Check Telegram API connectivity
docker-compose logs bot | grep "Telegram API error"
```

**Fixes**:
- Verify TELEGRAM_BOT_TOKEN is correct
- Restart bot: `docker-compose restart bot`
- Check internet connectivity

---

### "Unauthorized access" for valid user

**Symptom**: Authorized user receives unauthorized message

**Diagnosis**:
```bash
# Check authorized user IDs
docker-compose exec bot env | grep TELEGRAM_AUTHORIZED_USER_IDS

# Check user ID in logs
docker-compose logs bot | grep "user_id"
```

**Fixes**:
- Verify user ID is in TELEGRAM_AUTHORIZED_USER_IDS
- Restart bot after changing .env: `docker-compose restart bot`
- Confirm user ID with @userinfobot on Telegram

---

### API timeout errors

**Symptom**: "Service temporarily unavailable" responses

**Diagnosis**:
```bash
# Check API server status
docker-compose logs api | tail -20

# Check API response time
docker-compose logs bot | grep "api_call_time_ms"
```

**Fixes**:
- Restart API: `docker-compose restart api`
- Check Redis cache: `docker-compose ps redis`
- Verify BOT_API_AUTH_TOKEN matches in bot and API

---

## Performance Benchmarks

**Expected Response Times** (from logs):

| Command | P50 | P95 | P99 |
|---------|-----|-----|-----|
| /help | 50ms | 100ms | 150ms |
| /start | 60ms | 120ms | 180ms |
| /status | 250ms | 500ms | 1000ms |
| /positions | 350ms | 700ms | 1500ms |
| /performance | 350ms | 700ms | 1500ms |
| /pause | 150ms | 300ms | 500ms |
| /resume | 150ms | 300ms | 500ms |

**Degradation indicators**:
- Response time >3s: API server overloaded or timeout
- Response time >10s: Telegram API connectivity issues
- Rate limit violations: User sending commands too rapidly
