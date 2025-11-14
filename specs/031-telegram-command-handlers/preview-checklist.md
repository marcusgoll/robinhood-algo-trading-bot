# Preview Testing Checklist: 031-telegram-command-handlers

**Generated**: 2025-10-28 15:45:00 UTC
**Tester**: [Your name]
**Feature Type**: Backend/CLI (Telegram Bot Commands)

---

## ⚠️ Backend-Only Feature

This feature has no web UI routes. Testing focuses on:
- Telegram bot command functionality
- API endpoint behavior
- Integration with bot startup
- Security (auth, rate limiting)
- Error handling

---

## Prerequisites

### Environment Setup

- [ ] **TELEGRAM_BOT_TOKEN** set in .env
- [ ] **TELEGRAM_CHAT_ID** set in .env
- [ ] **TELEGRAM_ENABLED** set to `true` in .env
- [ ] **TELEGRAM_AUTHORIZED_USER_IDS** set (comma-separated user IDs)
- [ ] **TELEGRAM_COMMAND_COOLDOWN_SECONDS** set (default: 5)
- [ ] **BOT_API_AUTH_TOKEN** set (for internal API calls)
- [ ] **BOT_API_PORT** set (default: 8000)

### Bot Startup

- [ ] Bot starts without errors
- [ ] Telegram command handler initializes (check logs)
- [ ] 7 commands registered successfully
- [ ] No errors in startup logs

**Startup command**: `python -m trading_bot`

---

## Telegram Command Testing

### Test Environment

**Bot username**: @[YourBotUsername]
**Test user ID**: [Your Telegram user ID]
**Testing device**: [Mobile/Desktop]

### 1. /start Command

- [ ] Send `/start` to bot
- [ ] Receives welcome message
- [ ] Message shows authorization status (✅ Authorized)
- [ ] Message lists available commands
- [ ] Markdown formatting renders correctly
- [ ] Emoji displays correctly (🤖)

**Expected response**:
```
🤖 **Trading Bot Controller**

Welcome to the Robinhood Trading Bot Telegram interface!

**Authorization Status**: ✅ Authorized

You can use the following commands:
• /status - Check bot status
• /pause / /resume - Control trading
• /positions - View open positions
• /performance - View performance metrics
• /help - Full command list

_For help, use /help_
```

### 2. /help Command

- [ ] Send `/help` to bot
- [ ] Receives command list with descriptions
- [ ] All 7 commands listed
- [ ] Authorization status shown
- [ ] Rate limit info displayed
- [ ] Response time < 500ms

**Expected response**: Command list with descriptions and rate limit notice

### 3. /status Command

- [ ] Send `/status` to bot
- [ ] Receives current bot status
- [ ] Shows mode (🟢 Running / ⏸️ Paused / 🔴 Error)
- [ ] Shows position count and P/L
- [ ] Shows account balance and buying power
- [ ] Shows last signal timestamp
- [ ] Shows circuit breaker status
- [ ] Timestamp in UTC
- [ ] Response time < 3000ms

**Sample response format**:
```
📊 **Bot Status**

**Mode**: 🟢 Running
**Positions**: 2 open (+$125.50 / +2.3%)
**Account**: $10,500.00 (BP: $8,200.00)
**Last Signal**: 5 minutes ago
**Circuit Breakers**: None active

_Updated: 2025-10-28 15:30:00 UTC_
```

### 4. /positions Command

- [ ] Send `/positions` to bot
- [ ] Shows all open positions (or "0 open")
- [ ] Each position shows: symbol, entry price, current price, P/L, size, hold duration
- [ ] Color-coded emoji (🟢 profit, 🔴 loss, ⚪ break-even)
- [ ] Total P/L aggregated correctly
- [ ] Negative numbers format correctly (-$100.00, not $-100.00)
- [ ] Response time < 3000ms

**Sample response format**:
```
💼 **Open Positions** (2)

**AAPL** 🟢
Entry: $150.00 | Current: $152.50
P/L: +$250.00 (+1.67%)
Size: 100 shares | Hold: 2h 15m

**TSLA** 🔴
Entry: $220.00 | Current: $215.00
P/L: -$500.00 (-2.27%)
Size: 100 shares | Hold: 1h 45m

**Total P/L**: -$250.00 (-0.30%)

_Updated: 2025-10-28 15:30:00 UTC_
```

### 5. /performance Command

- [ ] Send `/performance` to bot
- [ ] Shows win rate with W/L counts
- [ ] Shows total P/L (absolute and percentage)
- [ ] Shows current streak (🔥 wins or ❄️ losses)
- [ ] Shows best trade with symbol
- [ ] Shows worst trade with symbol
- [ ] Negative numbers format correctly
- [ ] Response time < 3000ms

**Sample response format**:
```
📈 **Performance Metrics**

**Win Rate**: 65.2% (30W / 16L)
**Total P/L**: +$2,450.00 (+24.5%)
**Streak**: 🔥 3 wins
**Best Trade**: +$450.00 (AAPL)
**Worst Trade**: -$320.00 (TSLA)

_Last 46 trades | Updated: 2025-10-28 15:30:00 UTC_
```

### 6. /pause Command

- [ ] Send `/pause` to bot
- [ ] Receives confirmation message
- [ ] Bot state changes to "paused" (verify with `/status`)
- [ ] Existing positions remain open
- [ ] New signals are not processed (if applicable)
- [ ] Emoji displays correctly (⏸️)
- [ ] Response time < 2000ms

**Expected response**:
```
✅ **Bot Paused**

Trading paused successfully.
```

### 7. /resume Command

- [ ] Send `/resume` to bot (after `/pause`)
- [ ] Receives confirmation message
- [ ] Bot state changes to "running" (verify with `/status`)
- [ ] Bot begins processing signals again
- [ ] Emoji displays correctly (▶️)
- [ ] Response time < 2000ms

**Expected response**:
```
▶️ **Bot Resumed**

Trading resumed successfully.
```

---

## Security Testing

### Authentication

- [ ] **Authorized user**: All commands work
- [ ] **Unauthorized user**: Commands rejected with error message
- [ ] Error message: "❌ **Unauthorized Access**" with contact info
- [ ] `/start` works for unauthorized users (shows authorization status)
- [ ] Auth failures logged with WARNING level

**Test with**: Second Telegram account not in TELEGRAM_AUTHORIZED_USER_IDS

### Rate Limiting

- [ ] Send 2 commands rapidly (< 5 seconds apart)
- [ ] Second command blocked with rate limit error
- [ ] Error shows time remaining (e.g., "4 seconds")
- [ ] After cooldown expires, command works
- [ ] Rate limit is per-user (other users not affected)
- [ ] Rate limit violations logged with WARNING level

**Expected error**:
```
⏱️ **Rate Limit**

Please wait 4 seconds before sending another command.
```

### Error Handling

- [ ] API timeout: Command gracefully fails with error message
- [ ] API unreachable: Shows connection error
- [ ] Invalid API response: Handled gracefully
- [ ] Bot crashes: Command handler continues (non-blocking)
- [ ] All errors logged at ERROR level

---

## Integration Testing

### Bot Lifecycle

- [ ] **Startup**: Command handler starts with bot
- [ ] **Graceful shutdown**: Handler stops cleanly (Ctrl+C)
- [ ] **Restart**: Handler reconnects after bot restart
- [ ] **TELEGRAM_ENABLED=false**: Handler skipped, bot continues
- [ ] **Missing TELEGRAM_BOT_TOKEN**: Handler skipped with warning

### API Integration

- [ ] **GET /api/v1/state**: Returns bot state for `/status`
- [ ] **GET /api/v1/state**: Returns positions for `/positions`
- [ ] **GET /api/v1/state**: Returns metrics for `/performance`
- [ ] **POST /api/v1/commands/pause**: Pauses bot from `/pause`
- [ ] **POST /api/v1/commands/resume**: Resumes bot from `/resume`
- [ ] **X-API-Key header**: Validated on all API calls
- [ ] **API timeout**: Commands fail gracefully after 2 seconds

### Logging

- [ ] All commands logged with INFO level (user_id, command, timestamp)
- [ ] Auth failures logged with WARNING level
- [ ] Rate limit violations logged with WARNING level
- [ ] API errors logged with ERROR level
- [ ] Logs include user_id for audit trail
- [ ] No sensitive data in logs (tokens, full user info)

---

## Mobile UX Testing

### Telegram Mobile App

**Device**: [iPhone/Android model]
**Telegram version**: [Version]

- [ ] All emoji render correctly
- [ ] Markdown formatting works (bold, italic, code)
- [ ] Messages fit on screen without horizontal scroll
- [ ] Touch targets are adequate (buttons, links)
- [ ] Dark mode readable (if using dark theme)
- [ ] Light mode readable (if using light theme)
- [ ] Monospace code blocks render correctly
- [ ] Line breaks display correctly

---

## Performance Testing

### Response Times

| Command | Target (P95) | Actual | Pass/Fail |
|---------|--------------|--------|-----------|
| `/help` | <500ms | ___ ms | ___ |
| `/start` | <500ms | ___ ms | ___ |
| `/status` | <3000ms | ___ ms | ___ |
| `/positions` | <3000ms | ___ ms | ___ |
| `/performance` | <3000ms | ___ ms | ___ |
| `/pause` | <2000ms | ___ ms | ___ |
| `/resume` | <2000ms | ___ ms | ___ |

**Measurement method**: [Telegram timestamp or manual stopwatch]

### Load Testing

- [ ] Send 10 commands sequentially (rate limit aware)
- [ ] All commands succeed
- [ ] No memory leaks (check bot logs)
- [ ] No connection failures
- [ ] Bot remains responsive

---

## Issues Found

*Document any issues below with format:*

### Issue 1: [Title]
- **Severity**: Critical | High | Medium | Low
- **Command**: [Which command]
- **Description**: [What's wrong]
- **Expected**: [What should happen]
- **Actual**: [What actually happens]
- **Logs**: [Relevant log excerpts]
- **Reproducible**: Always | Sometimes | Once

---

## Console Validation

### Python Bot Logs

- [ ] No errors on startup
- [ ] "TelegramCommandHandler initialized" message
- [ ] "Registered 7 command handlers" message
- [ ] "Telegram command handler started (polling)" message
- [ ] Command execution logs (INFO level)
- [ ] No exception stack traces
- [ ] No warning messages (except expected auth/rate limit)

**Log file location**: [Console output or log file path]

### API Server Logs

- [ ] API calls from Telegram handler logged
- [ ] X-API-Key authentication succeeds
- [ ] GET /api/v1/state returns 200
- [ ] POST /api/v1/commands/pause returns 200
- [ ] POST /api/v1/commands/resume returns 200
- [ ] No 500 errors
- [ ] No timeout errors

---

## Test Results Summary

**Total scenarios tested**: ___ / 7 commands
**Security tests passed**: ___ / 3 (auth, rate limit, error handling)
**Integration tests passed**: ___ / 3 (startup, API, logging)
**Mobile UX validated**: ✅ / ⚠️ / ❌
**Performance targets met**: ___ / 7 commands
**Issues found**: ___

**Overall status**:
- ✅ Ready to ship (all tests pass, no critical issues)
- ⚠️ Minor issues (non-critical, can be fixed post-deployment)
- ❌ Blocking issues (must fix before deployment)

**Tester signature**: _______________
**Date**: _______________

---

## Next Steps

### If All Tests Pass ✅

1. Run `/ship-staging` to deploy to staging environment
2. Validate on staging with real bot
3. Monitor logs for 24 hours
4. Run `/ship-prod` to promote to production

### If Issues Found ⚠️

1. Document all issues above
2. Run `/debug` to fix critical issues
3. Re-run `/preview` to verify fixes
4. Proceed to staging when clean

### Staging Validation Checklist

Will be tested during `/validate-staging` phase:
- [ ] Staging bot responds to commands
- [ ] Auth works with staging user IDs
- [ ] API calls reach staging backend
- [ ] Logs show correct environment (staging)
- [ ] No production data visible

---

## Notes

- This is a backend-only feature with no web UI
- Testing requires access to a Telegram bot and authorized user account
- Manual testing is required due to Telegram's interactive nature
- Automated E2E tests not feasible without Telegram test environment
- Focus on security (auth, rate limiting) and integration (API calls)
