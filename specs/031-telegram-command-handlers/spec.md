# Feature Specification: Telegram Command Handlers for Bot Control and Reporting

**Feature Number**: 031
**Feature Slug**: telegram-command-handlers
**GitHub Issue**: #40
**Status**: Specification Phase
**Created**: 2025-10-27
**Last Updated**: 2025-10-27

## Overview

Enable remote control and monitoring of the trading bot through interactive Telegram commands. Users can check bot status, view positions, pause/resume trading, and access performance metrics directly from their mobile device via Telegram chat.

This feature bridges the existing Telegram notification system (Feature #030) with the REST API control layer (Feature #029), transforming the bot from a one-way notification channel into a fully interactive control interface.

## Problem Statement

**Current Limitation**: The trading bot sends notifications to Telegram but users cannot interact with it or query status on demand. To check bot status or pause trading, users must access the server directly or use API calls manually.

**User Need**: Traders need instant access to bot status, positions, and controls while away from their computer. Mobile-first workflow is critical for active trading scenarios.

**Business Value**:
- Reduces response time to market events (instant pause/resume from anywhere)
- Improves user confidence through on-demand status checks
- Enables mobile-first trading workflow
- Provides audit trail of manual interventions

## User Scenarios

### Scenario 1: Check bot status during market hours

**Given** the trading bot is running and connected to Telegram
**When** user sends `/status` command to the bot
**Then** bot responds with:
- Current operating mode (running/paused)
- Number of open positions with P/L
- Account balance and buying power
- Recent activity summary
- Response time under 3 seconds

### Scenario 2: Emergency pause during high volatility

**Given** the trading bot is actively running
**When** user sends `/pause` command
**Then** bot:
- Stops accepting new signals
- Confirms pause with timestamp
- Maintains existing positions
- Logs pause action with user ID
- Responds within 2 seconds

### Scenario 3: View open positions remotely

**Given** the bot has 3 open positions
**When** user sends `/positions` command
**Then** bot displays:
- Symbol, entry price, current price
- Unrealized P/L (dollar and percentage)
- Position size and hold duration
- Color-coded P/L (green/red emoji)
- Response time under 3 seconds

### Scenario 4: Unauthorized user attempts command

**Given** an unauthorized Telegram user ID
**When** user sends any command
**Then** bot:
- Does not execute the command
- Sends error message "Unauthorized access"
- Logs unauthorized attempt with user ID
- Does not reveal bot status or configuration

### Scenario 5: Command spam prevention

**Given** user sent a command 2 seconds ago
**When** user sends another command
**Then** bot:
- Does not execute the command
- Responds with cooldown message "Please wait 3 more seconds"
- Maintains rate limit tracking per user
- Logs rate limit violation

### Scenario 6: View performance metrics

**Given** the bot has executed 50+ trades
**When** user sends `/performance` command
**Then** bot displays:
- Overall win rate (percentage)
- Total P/L (dollar and percentage)
- Current streak (wins/losses)
- Best and worst trade
- Response time under 3 seconds

### Scenario 7: Get help on available commands

**Given** user is unsure of available commands
**When** user sends `/help` command
**Then** bot displays:
- List of all commands with brief descriptions
- Usage examples for each command
- Current authorization status
- Response time under 2 seconds

### Scenario 8: Resume trading after manual pause

**Given** the bot was manually paused via `/pause`
**When** user sends `/resume` command
**Then** bot:
- Resumes accepting new signals
- Confirms resume with timestamp
- Logs resume action with user ID
- Begins processing signals immediately
- Responds within 2 seconds

## Functional Requirements

### FR-001: Command Routing
The system shall provide a command router that:
- Registers handlers for each supported command (/start, /status, /pause, /resume, /positions, /performance, /help)
- Parses incoming Telegram messages to extract commands
- Routes commands to appropriate handler functions
- Handles unknown commands with helpful error message

### FR-002: User Authentication
The system shall authenticate all commands by:
- Extracting Telegram user ID from incoming message
- Comparing against authorized user IDs from TELEGRAM_AUTHORIZED_USER_IDS environment variable
- Rejecting unauthorized users with error message
- Logging all authentication attempts (success and failure) with timestamp and user ID

### FR-003: Rate Limiting
The system shall prevent command spam by:
- Tracking last command timestamp per user ID
- Enforcing configurable cooldown period (TELEGRAM_COMMAND_COOLDOWN_SECONDS, default 5 seconds)
- Rejecting commands within cooldown period with time-remaining message
- Resetting cooldown after successful command execution

### FR-004: Status Command (/status)
The system shall provide current bot status including:
- Operating mode (running/paused/error)
- Number of open positions with aggregate P/L
- Account balance and buying power
- Last signal timestamp
- Active circuit breakers (if any)
- Data retrieved via GET /api/v1/state endpoint

### FR-005: Pause Command (/pause)
The system shall pause trading operations by:
- Calling appropriate REST API endpoint to set bot to paused state
- Confirming pause with timestamp
- Explaining that existing positions remain open
- Logging pause action with user ID

### FR-006: Resume Command (/resume)
The system shall resume trading operations by:
- Calling appropriate REST API endpoint to set bot to running state
- Confirming resume with timestamp
- Explaining that bot will begin processing signals
- Logging resume action with user ID

### FR-007: Positions Command (/positions)
The system shall display all open positions with:
- Symbol and position side (long/short)
- Entry price and current price
- Unrealized P/L (dollar amount and percentage)
- Position size (shares)
- Hold duration (time since entry)
- Color-coded emoji indicators (🟢 profit, 🔴 loss, ⚪ break-even)
- Data retrieved via GET /api/v1/state endpoint

### FR-008: Performance Command (/performance)
The system shall display performance metrics including:
- Overall win rate (wins / total trades)
- Total realized P/L (dollar and percentage)
- Current streak (consecutive wins/losses)
- Best trade (highest profit)
- Worst trade (largest loss)
- Data retrieved via GET /api/v1/state or metrics endpoint

### FR-009: Help Command (/help)
The system shall provide command documentation:
- List of all available commands
- Brief description of each command
- Usage examples (e.g., "/status - Check current bot status")
- Authorization status (whether user is authorized)

### FR-010: Start Command (/start)
The system shall welcome new users with:
- Bot introduction message
- Overview of capabilities
- Link to full command list (/help)
- Authorization status

### FR-011: Response Formatting
The system shall format all responses with:
- Markdown formatting for structure (bold, code blocks, lists)
- Emoji for visual indicators (✅ success, ❌ error, 📊 metrics, 💰 money, ⏸️ pause, ▶️ resume)
- Compact layout optimized for mobile screens
- Timestamp for time-sensitive data
- Configurable via TELEGRAM_PARSE_MODE environment variable

### FR-012: Error Handling
The system shall handle errors gracefully by:
- Catching API call failures (timeout, connection error, 500 errors)
- Sending user-friendly error messages (avoid stack traces)
- Logging detailed error information with context
- Maintaining bot availability (errors in one command do not crash handler)

### FR-013: Audit Logging
The system shall log all command executions with:
- Timestamp (ISO 8601 format)
- User ID (Telegram user ID)
- Command name (e.g., "status", "pause")
- Execution result (success/failure)
- Error details (if applicable)
- Log level: INFO for successful commands, WARNING for auth failures, ERROR for execution failures

### FR-014: API Integration
The system shall integrate with existing REST API by:
- Making HTTP requests to localhost:8000/api/v1/* endpoints
- Including X-API-Key header from BOT_API_AUTH_TOKEN environment variable
- Using async HTTP client (e.g., httpx) for non-blocking calls
- Handling API response errors (401 Unauthorized, 500 Internal Server Error)
- Respecting API rate limits (100 requests/minute from Feature #029)

### FR-015: Async Command Execution
The system shall execute commands asynchronously:
- All command handlers are async functions
- API calls are awaited (non-blocking)
- Message sending is non-blocking
- Command processing does not block main bot loop

## Non-Functional Requirements

### NFR-001: Response Time
- Command responses shall be delivered within 3 seconds (P95)
- Acknowledgment of command receipt shall occur within 500ms
- Timeout for API calls shall be 2 seconds with retry

### NFR-002: Availability
- Command handler shall remain available during API failures (graceful degradation)
- Telegram API failures shall not crash the command handler
- Handler shall recover automatically from transient errors

### NFR-003: Security
- All commands require user ID authentication
- Unauthorized users receive no information about bot status
- API token shall never be exposed in Telegram messages
- Command execution shall be logged for audit trail

### NFR-004: Scalability
- Handler shall support up to 10 authorized users
- Rate limiting shall prevent abuse (5 second cooldown default)
- Command processing shall not interfere with trading operations

### NFR-005: Maintainability
- Command handlers shall be modular (one function per command)
- New commands shall be addable without modifying existing handlers
- Configuration shall be externalized to environment variables
- Code shall follow existing TelegramClient patterns

### NFR-006: Compatibility
- Shall use existing python-telegram-bot library (v20.7)
- Shall integrate with existing REST API (no breaking changes)
- Shall reuse TelegramClient for message sending
- Shall follow existing logging patterns

### NFR-007: Mobile UX
- Responses shall be optimized for mobile screens (concise, scannable)
- Emoji shall enhance readability and visual hierarchy
- Critical information shall appear first (above the fold)
- Markdown formatting shall improve structure without clutter

## Success Criteria

1. **Command Availability**: All 7 core commands (/start, /status, /pause, /resume, /positions, /performance, /help) are functional and return expected responses
2. **Response Time**: 95% of commands respond within 3 seconds
3. **Security**: 100% of unauthorized command attempts are rejected and logged
4. **Rate Limiting**: Users cannot execute more than 1 command per 5 seconds
5. **Error Resilience**: API failures do not crash the command handler (graceful error messages sent)
6. **Audit Trail**: All command executions are logged with user ID, timestamp, and result
7. **Mobile UX**: All responses render correctly in Telegram mobile app with proper emoji and markdown formatting

## Out of Scope

The following are explicitly excluded from this feature:

1. **Order Placement**: Users cannot place orders via Telegram (only view positions and control bot state)
2. **Configuration Changes**: Users cannot modify bot configuration (risk limits, strategies) via Telegram
3. **Multi-User Permissions**: All authorized users have equal permissions (no role-based access)
4. **Natural Language Processing**: Commands use fixed syntax (/command), no AI interpretation
5. **Historical Data**: Commands show current/recent data only (no historical backtesting results)
6. **Position Management**: Users cannot close individual positions via Telegram (only pause entire bot)
7. **Alert Configuration**: Users cannot configure custom alerts via Telegram
8. **Inline Keyboards**: Commands use text responses only (no interactive buttons/menus)

## Assumptions

1. **Single Bot Instance**: Only one trading bot instance runs per Telegram bot token
2. **Trusted Users**: All authorized users are trusted (no granular permission system needed)
3. **API Availability**: REST API (Feature #029) is running on localhost:8000
4. **Internet Connectivity**: Server has stable internet connection for Telegram API access
5. **User ID Discovery**: Users know how to find their Telegram user ID (documented in setup instructions)
6. **Desktop Setup**: Initial authorization setup happens on desktop (adding user ID to .env)
7. **English Only**: All command names and responses are in English
8. **UTC Timestamps**: All timestamps use UTC timezone (consistent with existing bot)

## Dependencies

### Technical Dependencies
- **Feature #030 (Telegram Notifications)**: Provides TelegramClient class and bot token configuration
- **Feature #029 (LLM-Friendly Bot Operations)**: Provides REST API endpoints for state queries and control operations
- python-telegram-bot library v20.7 (already in requirements.txt)
- httpx or aiohttp for async HTTP client (to call REST API)
- Existing logging infrastructure
- Existing environment configuration patterns

### External Services
- Telegram Bot API (messaging and command receipt)
- Trading bot REST API (localhost:8000)

### Configuration
- TELEGRAM_BOT_TOKEN (already exists)
- TELEGRAM_AUTHORIZED_USER_IDS (new - comma-separated user IDs)
- TELEGRAM_COMMAND_COOLDOWN_SECONDS (new - default 5)
- BOT_API_AUTH_TOKEN (already exists)
- BOT_API_PORT (already exists - default 8000)

## Deployment Considerations

### Platform Dependencies
- None (pure Python code, no new platform requirements)

### Environment Variables

**New Variables**:
- `TELEGRAM_AUTHORIZED_USER_IDS` - Comma-separated list of authorized Telegram user IDs (e.g., "123456789,987654321")
- `TELEGRAM_COMMAND_COOLDOWN_SECONDS` - Cooldown period between commands per user (default: 5)

**Existing Variables** (reused):
- `TELEGRAM_BOT_TOKEN` - Bot token from Feature #030
- `TELEGRAM_ENABLED` - Enable/disable Telegram functionality
- `BOT_API_AUTH_TOKEN` - API key for REST API calls
- `BOT_API_PORT` - API server port (default 8000)

### Breaking Changes
- **None**: Feature is additive only. Existing Telegram notifications continue to work unchanged.

### Migration Required
- **None**: No database schema changes. No data migration needed.

### Rollback Considerations
- Standard rollback: Remove command handler initialization, revert to notification-only mode
- No special rollback procedures needed (stateless feature)
- Can be disabled via TELEGRAM_ENABLED=false without code changes

## Context Strategy

### Command Context Requirements
Each command handler needs different data from the REST API:

**Minimal Context Commands** (fast, <1KB):
- `/help` - Static documentation (no API call)
- `/start` - Static welcome message (no API call)

**State Context Commands** (medium, GET /api/v1/state or /summary):
- `/status` - Requires: operating mode, positions count, account balance, recent signals
- `/positions` - Requires: open positions list with P/L
- `/performance` - Requires: win rate, total P/L, best/worst trades

**Control Commands** (POST operations, state change):
- `/pause` - Calls control endpoint to set bot state to paused
- `/resume` - Calls control endpoint to set bot state to running

### API Endpoint Mapping

| Command | HTTP Method | Endpoint | Response Size | Expected Latency |
|---------|-------------|----------|---------------|------------------|
| /status | GET | /api/v1/summary | <10KB | <200ms |
| /positions | GET | /api/v1/state | <50KB | <300ms |
| /performance | GET | /api/v1/state | <50KB | <300ms |
| /pause | POST | /api/v1/control/pause | <1KB | <100ms |
| /resume | POST | /api/v1/control/resume | <1KB | <100ms |

**Note**: Control endpoints (/pause, /resume) will need to be verified or created in Feature #029 API. If missing, will use workflow execution endpoints as fallback.

### Caching Strategy
- Use API's built-in cache (60 second TTL from Feature #029)
- No client-side caching in command handler (always fetch fresh data)
- Rationale: Users expect real-time data when querying status

## Signal Design

### Success Signals (User Perspective)

1. **Fast Response**: Commands respond within 3 seconds → "Bot is responsive and accessible"
2. **Clear Formatting**: Emoji + markdown make data scannable → "Easy to read on mobile"
3. **Real-Time Data**: Status reflects current state → "I can trust this information"
4. **Control Confirmation**: Pause/resume commands confirm action → "I know the command worked"

### Error Signals (User Perspective)

1. **Unauthorized Access**: Clear rejection message → "I need to get authorized"
2. **Rate Limit Hit**: Cooldown message with time remaining → "I'm sending commands too fast"
3. **API Failure**: User-friendly error message → "Something is wrong, try again"
4. **Unknown Command**: Helpful error with suggestion → "Use /help to see valid commands"

### System Signals (Developer/Operations)

1. **Audit Logs**: All commands logged with user ID → Trace user actions, security monitoring
2. **Error Logs**: API failures logged with context → Diagnose integration issues
3. **Auth Failures**: Unauthorized attempts logged → Detect potential security issues
4. **Rate Limit Violations**: Logged for abuse detection → Identify spam patterns

## Open Questions

None - specification is complete with reasonable defaults for all ambiguous points.

## References

- **Feature #030**: D:\Coding\Stocks\src\trading_bot\notifications\telegram_client.py
- **Feature #029**: D:\Coding\Stocks\api\app\routes\state.py
- **Environment Config**: D:\Coding\Stocks\.env.example
- **python-telegram-bot Documentation**: https://docs.python-telegram-bot.org/en/v20.7/
- **Telegram Bot API**: https://core.telegram.org/bots/api

## Appendix: Example Command Responses

### /status Response
```
📊 **Bot Status**

**Mode**: 🟢 Running
**Positions**: 2 open (+$125.50 / +2.3%)
**Account**: $10,500.00 (BP: $8,200.00)
**Last Signal**: 5 minutes ago
**Circuit Breakers**: None active

_Updated: 2025-10-27 14:30:00 UTC_
```

### /positions Response
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

### /performance Response
```
📈 **Performance Metrics**

**Win Rate**: 65.2% (30W / 16L)
**Total P/L**: +$2,450.00 (+24.5%)
**Streak**: 🔥 3 wins
**Best Trade**: +$850.00 (NVDA)
**Worst Trade**: -$320.00 (TSLA)

_Last 50 trades | Updated: 2025-10-27 14:30:00 UTC_
```

### /help Response
```
🤖 **Available Commands**

**/start** - Welcome message
**/status** - Current bot status
**/pause** - Pause trading (keeps positions)
**/resume** - Resume trading
**/positions** - List open positions
**/performance** - Show win rate and P/L
**/help** - This message

**Authorization**: ✅ Authorized

_Rate limit: 1 command per 5 seconds_
```
