# Implementation Plan: Telegram Notifications

## [RESEARCH DECISIONS]

See: research.md for full research findings

**Summary**:
- Stack: Python 3.11, python-telegram-bot v20.7 (async), asyncio for non-blocking delivery
- Components to reuse: 7 (AlertEvaluator, TradeRecord, retry logic, circuit_breaker, logging, dotenv, rate_limiter pattern)
- New components needed: 5 (telegram_client, message_formatter, notification_service, __init__, tests)
- Architecture: Integrate with existing alert/logging infrastructure, async fire-and-forget pattern

---

## [ARCHITECTURE DECISIONS]

### Stack

- **Language**: Python 3.11 (existing project standard from tech-stack.md)
- **Telegram Library**: python-telegram-bot v20.7 (async wrapper for Telegram Bot API)
  - Rationale: Mature async library, handles retry/rate limiting, non-blocking design fits project architecture
  - Alternative rejected: raw requests (need manual retry logic), aiogram (less mature), telebot (synchronous)
- **Async Framework**: asyncio (Python standard library)
  - Pattern: asyncio.create_task() for fire-and-forget delivery with 5s timeout
  - Rationale: Non-blocking requirement (FR-001), no trade execution delay
- **Environment Config**: python-dotenv (already in requirements.txt)
  - Pattern: TELEGRAM_* variables in .env, follows existing ROBINHOOD_*, ALPACA_* pattern
- **Validation**: Pydantic v2.5.0 (already in requirements.txt for FastAPI)
  - Use: Message schema validation (PositionEntryMessage, PositionExitMessage, RiskAlertMessage)
- **Logging**: Python logging module (existing infrastructure)
  - Output: logs/telegram-notifications.jsonl (append-only JSONL, grep-friendly)

### Patterns

- **Non-Blocking Async Delivery**:
  - Description: Use asyncio.create_task() to send notifications in background without blocking trading operations
  - Rationale: FR-001 requirement - notification failures cannot prevent trade execution
  - Implementation: Main thread creates async task with 5s timeout, immediately continues trading logic
  - Error handling: Catch all exceptions in async task, log error, continue trading

- **Graceful Degradation**:
  - Description: Check TELEGRAM_ENABLED flag at startup, log warning if credentials missing, continue trading
  - Rationale: FR-006 requirement - missing config cannot prevent bot startup
  - Implementation: NotificationService.__init__ checks credentials, sets self.enabled flag, logs warning if disabled
  - Failure mode: Notifications skipped silently (logged at INFO level), trading unaffected

- **Rate Limiting (In-Memory Cache)**:
  - Description: Track last notification timestamp per error type, enforce max 1 per hour limit
  - Rationale: NFR-004 requirement - prevent notification spam during system instability
  - Implementation: Python dict {error_type: last_sent_timestamp}, check elapsed time before sending
  - Expiry: Cache resets on bot restart (acceptable - rate limit is per-session protection)

- **Message Truncation**:
  - Description: Enforce Telegram 4096 character limit, truncate with "..." if exceeded
  - Rationale: FR-010 requirement - handle message size limits
  - Implementation: Check len(message) before sending, truncate to 4093 chars + "..." suffix if needed

- **Retry with Exponential Backoff**:
  - Description: Reuse existing retry.py logic for transient Telegram API errors (429, 500, network errors)
  - Rationale: Improve delivery reliability (NFR-002: >99% success rate target)
  - Implementation: Wrap telegram_client.send_message() with exponential backoff decorator (max 3 retries, 2s/4s/8s delays)

### Dependencies (new packages required)

- `python-telegram-bot==20.7`: Telegram Bot API wrapper (async, production-ready)
  - Purpose: Send messages to Telegram chat via Bot API
  - Alternatives rejected: raw requests (manual retry logic), aiogram (less mature)
  - Size: ~2.5 MB (reasonable for notification capability)

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns from system-architecture.md):

```
src/trading_bot/
├── notifications/                  # NEW MODULE
│   ├── __init__.py                 # Export NotificationService, ConfigurationError
│   ├── telegram_client.py          # Telegram Bot API wrapper (async send_message)
│   ├── message_formatter.py        # Format TradeRecord/AlertEvent → Telegram Markdown
│   ├── notification_service.py     # Orchestration (check config, format, send, log)
│   └── validate_config.py          # CLI tool for setup validation
│
├── performance/
│   └── alerts.py                   # MODIFY: Add Telegram notification on alert creation
│
├── logging/
│   └── trade_record.py             # REUSE: Extract trade data for notifications
│
└── error_handling/
    ├── circuit_breaker.py          # MODIFY: Add Telegram notification on circuit breaker trigger
    └── retry.py                    # REUSE: Exponential backoff for Telegram API errors

tests/
├── notifications/                  # NEW TEST MODULE
│   ├── __init__.py
│   ├── test_telegram_client.py     # Mock Telegram API, test send_message
│   ├── test_message_formatter.py   # Test Markdown formatting, emoji, truncation
│   ├── test_notification_service.py # Test orchestration, config checks, rate limiting
│   └── test_integration.py         # End-to-end test with mocked Telegram API
│
└── performance/
    └── test_alerts.py              # EXTEND: Test Telegram notification on alert

logs/
└── telegram-notifications.jsonl    # NEW LOG FILE (append-only, structured JSONL)

scripts/
└── test_telegram_notification.py   # NEW: Manual test script for quickstart validation

.env.example                        # MODIFY: Add TELEGRAM_* section with documentation
requirements.txt                    # MODIFY: Add python-telegram-bot==20.7
```

**Module Organization**:

- **notifications/__init__.py**: Public API - exports `NotificationService`, `ConfigurationError` exception
- **notifications/telegram_client.py**: Telegram Bot API abstraction - async `send_message(chat_id, text, parse_mode)` with timeout
- **notifications/message_formatter.py**: Message formatting logic - convert `TradeRecord` → Markdown, emoji insertion, truncation
- **notifications/notification_service.py**: Orchestration - check `TELEGRAM_ENABLED`, call formatter, send via client, log result, handle rate limiting
- **notifications/validate_config.py**: CLI tool - validate credentials, test Bot API connection, verify chat accessible

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- **Entities**: TelegramNotification (9 fields), ErrorNotificationCache (3 fields)
- **Storage**: File-based JSONL log (logs/telegram-notifications.jsonl)
- **Schemas**: Pydantic models for PositionEntryMessage, PositionExitMessage, RiskAlertMessage
- **Relationships**: References TradeRecord (via trade_id), AlertEvent (via alert_id)
- **Validation**: Message length ≤4096 chars, notification_type enum, delivery_status state machine

**Key Relationships**:
- TelegramNotification → TradeRecord (for position entry/exit notifications)
- TelegramNotification → AlertEvent (for risk alert notifications)
- ErrorNotificationCache (in-memory only, not persisted)

**Migrations required**: None (file-based storage, no database schema changes)

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- **NFR-001**: Notification delivery latency <10 seconds (P95) - from trigger to Telegram delivery
  - Measurement: Log timestamp difference (created_at → sent_at)
  - Target: 95% of notifications delivered within 10s

- **NFR-002**: Notification delivery success rate >99% under normal conditions
  - Measurement: `(sent / total) * 100` from logs/telegram-notifications.jsonl
  - Target: <1% failure rate over 30-day window

- **NFR-003**: Notification service CPU usage <5% (trading operations take priority)
  - Measurement: Profile async task CPU time via Python cProfile
  - Target: Notification processing <5% of total bot CPU time

- **NFR-004**: Rate limit error notifications (max 1 per error type per hour)
  - Measurement: Check ErrorNotificationCache hit rate in logs
  - Target: No more than 1 notification per error type per 60-minute window

**Lighthouse Targets**: Not applicable (backend-only feature, no frontend UI)

---

## [SECURITY]

### Authentication Strategy

- **Telegram Bot API**: Bot token-based authentication (bearer token in URL path)
  - Pattern: `https://api.telegram.org/bot<TOKEN>/sendMessage`
  - Token format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` (obtained from @BotFather)
  - Storage: Environment variable `TELEGRAM_BOT_TOKEN` (never committed to git)

- **Chat Access Control**: Only send to configured chat ID (single recipient)
  - Validation: `TELEGRAM_CHAT_ID` must be numeric string
  - Restriction: Bot only sends to this chat ID, no multi-user support

### Authorization Model

- **No RBAC needed**: Single-user system (solo trader) - Constitution §Security
- **Environment-based access**: Only user with access to .env file can configure notifications
- **No user authentication**: Bot assumes environment is secure (VPS with SSH key access only)

### Input Validation

- **Message sanitization**: Escape special characters for Markdown format (prevent injection)
  - Characters to escape: `_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`
  - Implementation: Use `telegram.helpers.escape_markdown()` from python-telegram-bot library

- **Schema validation**: Pydantic models for message data (PositionEntryMessage, PositionExitMessage, RiskAlertMessage)
  - Type safety: Decimal for prices, int for quantity, str for symbols
  - Bounds checking: Quantity >0, price >0, position_size >0

- **Rate limiting**: Enforce max 1 error notification per type per hour (prevent spam)
  - Implementation: Check ErrorNotificationCache before sending error notifications
  - Bypass: Position and alert notifications always sent (not rate-limited)

### Data Protection

- **Credentials at rest**: `.env` file with 0600 permissions (read/write for owner only)
  - Variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
  - Git: `.env` in `.gitignore` (never committed)
  - Template: `.env.example` committed with placeholder values

- **Credentials in transit**: HTTPS (TLS 1.2+) for all Telegram Bot API calls
  - URL: `https://api.telegram.org` (enforced by python-telegram-bot library)
  - Certificate validation: Enabled by default in requests library

- **Logging**: Never log `TELEGRAM_BOT_TOKEN` in logs (mask in error messages)
  - Implementation: Replace token with `***REDACTED***` in exception messages
  - Safe to log: `TELEGRAM_CHAT_ID` (not a secret, just an identifier)

- **No PII in notifications**: Trade data only (symbols, prices, P&L) - no personal information
  - Acceptable: AAPL, $150.25, +$242.50 (public market data)
  - Not included: User email, account number, session tokens

---

## [EXISTING INFRASTRUCTURE - REUSE] (7 components)

### Services/Modules

1. **src/trading_bot/performance/alerts.py** - AlertEvaluator class
   - **Reuse**: Integrate Telegram notification when alerts created
   - **Integration point**: `AlertEvaluator.evaluate()` method - call `notification_service.send_risk_alert()` after appending to alerts list
   - **Modification**: Add `notification_service: NotificationService` parameter to `__init__`, make `evaluate()` async

2. **src/trading_bot/logging/trade_record.py** - TradeRecord dataclass
   - **Reuse**: Extract position entry/exit details for notification messages
   - **Fields used**: symbol, action, quantity, price, total_value, stop_loss, target, execution_mode, outcome, profit_loss, exit_reasoning, hold_duration_seconds
   - **No modification**: Read-only access to dataclass fields

3. **src/trading_bot/error_handling/retry.py** - Exponential backoff retry logic
   - **Reuse**: Wrap `telegram_client.send_message()` with retry decorator
   - **Pattern**: `@retry(max_attempts=3, backoff_factor=2, exceptions=(NetworkError, TelegramAPIError))`
   - **No modification**: Use existing decorator as-is

4. **src/trading_bot/error_handling/circuit_breaker.py** - Circuit breaker events
   - **Reuse**: Trigger urgent Telegram alerts when circuit breaker trips
   - **Integration point**: Add `notification_service.send_risk_alert()` call after circuit breaker logs event
   - **Modification**: Add notification_service dependency, call async notification method

5. **src/trading_bot/llm/rate_limiter.py** - Rate limiting pattern
   - **Reuse**: Adapt in-memory cache pattern for error notification rate limiting
   - **Pattern**: Dict with timestamp tracking, check elapsed time before allowing operation
   - **Modification**: Simplified version (no token bucket, just timestamp check)

6. **python-dotenv** - Environment variable pattern
   - **Reuse**: Add `TELEGRAM_*` variables to .env, follow existing pattern
   - **Pattern**: Section headers with comments, boolean flags, secure token storage
   - **Files**: .env (local), .env.example (template in git)

7. **Python logging module** - Structured logging
   - **Reuse**: Add notification success/failure logs to existing logging infrastructure
   - **Log file**: `logs/telegram-notifications.jsonl` (new file, same JSONL pattern)
   - **Format**: Structured JSON with timestamp, notification_type, delivery_status, error_message

---

## [NEW INFRASTRUCTURE - CREATE] (5 components)

### Backend

1. **src/trading_bot/notifications/telegram_client.py** - Telegram Bot API wrapper
   - **Purpose**: Async send_message() method with timeout and error handling
   - **Public API**:
     ```python
     class TelegramClient:
         async def send_message(
             self,
             chat_id: str,
             text: str,
             parse_mode: str = "Markdown",
             timeout: float = 5.0
         ) -> dict:
             """Send message via Telegram Bot API with timeout."""
     ```
   - **Dependencies**: python-telegram-bot, asyncio
   - **Error handling**: Catch `telegram.error.TelegramError`, retry on transient errors (429, 500)

2. **src/trading_bot/notifications/message_formatter.py** - Message formatting logic
   - **Purpose**: Convert TradeRecord/AlertEvent → Telegram Markdown with emoji
   - **Public API**:
     ```python
     class MessageFormatter:
         def format_position_entry(self, trade: TradeRecord) -> str: ...
         def format_position_exit(self, trade: TradeRecord) -> str: ...
         def format_risk_alert(self, alert: AlertEvent) -> str: ...
         def _truncate(self, message: str, max_length: int = 4096) -> str: ...
     ```
   - **Features**: Emoji insertion (📈, ✅, ❌, 🚨), Markdown escaping, truncation with "..."

3. **src/trading_bot/notifications/notification_service.py** - Notification orchestration
   - **Purpose**: Check config, format message, send via client, log result, handle rate limiting
   - **Public API**:
     ```python
     class NotificationService:
         async def send_position_entry(self, trade: TradeRecord) -> TelegramNotification: ...
         async def send_position_exit(self, trade: TradeRecord) -> TelegramNotification: ...
         async def send_risk_alert(self, alert: AlertEvent) -> TelegramNotification: ...
         def is_enabled(self) -> bool: ...
     ```
   - **State**: enabled flag, bot_token, chat_id, error_cache (in-memory dict)
   - **Error handling**: Catch all exceptions, log error, return TelegramNotification with delivery_status="failed"

4. **src/trading_bot/notifications/__init__.py** - Module initialization
   - **Purpose**: Export public API (NotificationService, ConfigurationError exception)
   - **Contents**:
     ```python
     from .notification_service import NotificationService
     from .telegram_client import ConfigurationError
     __all__ = ["NotificationService", "ConfigurationError"]
     ```

5. **tests/notifications/** - Test suite
   - **Purpose**: Unit tests for formatter, integration tests for client (mocked Telegram API)
   - **Files**:
     - `test_telegram_client.py`: Mock Telegram API responses, test timeout, retry logic
     - `test_message_formatter.py`: Test Markdown formatting, emoji, truncation, escaping
     - `test_notification_service.py`: Test orchestration, config checks, rate limiting
     - `test_integration.py`: End-to-end test with mocked Telegram API (send position entry → verify log)
   - **Coverage target**: >90% (Constitution requirement)

---

## [CI/CD IMPACT]

### From spec.md deployment considerations

- **Platform**: Self-hosted VPS (Hetzner) with Docker Compose - no platform-specific features
  - Implementation: Pure Python, no Vercel/Railway-specific code
  - Docker: Standard Python 3.11-slim base image (no changes to Dockerfile)

- **Environment variables** (update .env.example):
  ```bash
  # New required variables
  TELEGRAM_ENABLED=false  # Set to 'true' after configuring credentials
  TELEGRAM_BOT_TOKEN=     # From @BotFather (format: 123456:ABC-DEF...)
  TELEGRAM_CHAT_ID=       # Numeric chat ID (get via @userinfobot)

  # New optional variables (with defaults)
  TELEGRAM_NOTIFY_POSITIONS=true
  TELEGRAM_NOTIFY_ALERTS=true
  TELEGRAM_PARSE_MODE=Markdown
  TELEGRAM_INCLUDE_EMOJIS=true
  TELEGRAM_ERROR_RATE_LIMIT_MINUTES=60
  ```

- **Breaking changes**: None (additive feature)
  - Backward compatible: Existing bot operation unchanged if TELEGRAM_ENABLED=false
  - No API changes: No modifications to existing function signatures
  - No data migration: File-based logs (new file, no schema changes)

- **Migration**: Not required
  - No database schema changes (file-based storage)
  - No data backfill (notifications start from feature activation)
  - Rollback: Set TELEGRAM_ENABLED=false, notifications skipped silently

### Build Commands

- **No changes**: Standard `pip install -r requirements.txt` (new dependency added to requirements.txt)
- **Test command**: `pytest tests/notifications/ --cov=trading_bot.notifications --cov-report=term-missing`
- **Type check**: `mypy src/trading_bot/notifications/` (new module added to type checking)

### Environment Variables (update secrets.schema.json if exists)

**New required**:
- `TELEGRAM_BOT_TOKEN`: Telegram Bot API token (format: `\d+:[A-Za-z0-9_-]+`)
- `TELEGRAM_CHAT_ID`: Numeric chat ID (format: `\d+`)

**New optional** (with defaults):
- `TELEGRAM_ENABLED`: Boolean flag (default: false)
- `TELEGRAM_NOTIFY_POSITIONS`: Boolean (default: true)
- `TELEGRAM_NOTIFY_ALERTS`: Boolean (default: true)
- `TELEGRAM_PARSE_MODE`: String enum ["Markdown", "HTML", "None"] (default: "Markdown")
- `TELEGRAM_INCLUDE_EMOJIS`: Boolean (default: true)
- `TELEGRAM_ERROR_RATE_LIMIT_MINUTES`: Integer (default: 60)

**Staging values**: Same as production (use same bot token, different chat ID for testing if desired)

**Production values**: Obtained from @BotFather (bot token) and @userinfobot (chat ID)

### Database Migrations

- **Not applicable**: No database, file-based logs only
- **New log file**: `logs/telegram-notifications.jsonl` (created automatically on first notification)
- **Log rotation**: Not implemented in MVP (append-only, manual cleanup if needed)

### Smoke Tests (for CI/CD)

```bash
# Test 1: Configuration validation
python -m trading_bot.notifications.validate_config
# Expected: Exit code 0 if configured correctly, 1 if missing credentials

# Test 2: Send test notification
python scripts/test_telegram_notification.py
# Expected: Notification delivered, exit code 0

# Test 3: Check notification logs
test -f logs/telegram-notifications.jsonl
# Expected: Log file exists after test notification

# Test 4: Verify delivery rate
python -c "
import json
from pathlib import Path
log_file = Path('logs/telegram-notifications.jsonl')
if log_file.exists():
    with open(log_file) as f:
        notifications = [json.loads(line) for line in f]
    sent = sum(1 for n in notifications if n['delivery_status'] == 'sent')
    total = len(notifications)
    success_rate = (sent / total * 100) if total > 0 else 0
    assert success_rate >= 99, f'Delivery rate {success_rate:.2f}% below 99% target'
    print(f'✅ Delivery rate: {success_rate:.2f}%')
"
# Expected: >99% delivery rate (NFR-002 requirement)
```

### Platform Coupling

- **None**: Pure Python implementation, no platform-specific features
- **Dependencies**: python-telegram-bot (cross-platform, pure Python)
- **External API**: Telegram Bot API (HTTPS, platform-agnostic)

---

## [DEPLOYMENT ACCEPTANCE]

### Production Invariants (must hold true)

1. **Non-blocking design**: Notification failures never prevent trade execution
   - Test: Simulate Telegram API down, verify trades execute normally
   - Assertion: Trade logs show successful executions even when notification logs show failures

2. **Graceful degradation**: Missing TELEGRAM_BOT_TOKEN does not crash bot
   - Test: Start bot without TELEGRAM_BOT_TOKEN, verify bot runs, notifications disabled
   - Assertion: Bot log shows "Telegram notifications disabled (missing credentials)" warning

3. **Rate limiting enforced**: Error notifications respect 1 per type per hour limit
   - Test: Trigger same error type 10 times in 1 minute, verify only 1 notification sent
   - Assertion: ErrorNotificationCache blocks subsequent notifications until 60 minutes elapsed

4. **Message size limits**: Messages exceeding 4096 characters are truncated
   - Test: Send notification with 5000 character message, verify truncated to 4093 + "..."
   - Assertion: Telegram API accepts message, no 400 "message too long" errors

### Staging Smoke Tests (Given/When/Then)

```gherkin
Given trading bot is running with TELEGRAM_ENABLED=true
When a position is opened (BUY order executes)
Then Telegram notification is received within 10 seconds
  And message includes symbol, entry price, shares, stop loss, target
  And message format is Markdown with emoji (📈)
  And notification log shows delivery_status="sent"

Given trading bot is running with TELEGRAM_ENABLED=true
When a circuit breaker triggers (max daily loss exceeded)
Then urgent Telegram alert is received within 5 seconds
  And message includes breach type, current value, threshold
  And message format includes 🚨 emoji and bold text
  And trading is halted (no new positions opened)

Given trading bot is running with TELEGRAM_ENABLED=false
When a position is opened
Then no Telegram notification is sent
  And trade executes normally
  And bot log shows "Telegram notifications disabled" message

Given same error occurs 3 times within 5 minutes
When error notifications are triggered
Then only 1 notification is sent (first occurrence)
  And subsequent notifications are rate-limited
  And notification log shows delivery_status="rate_limited" for 2nd and 3rd attempts
```

### Rollback Plan

- **Deployment IDs tracked in**: specs/030-telegram-notificatio/NOTES.md (Deployment Metadata section)
  - Record: Deploy ID, timestamp, commit SHA, docker image tag
  - Example: `deploy-20251027-143215, commit abc1234, image ghcr.io/user/trading-bot:abc1234`

- **Rollback commands**:
  ```bash
  # Option 1: Disable notifications (keep code, turn off feature)
  ssh user@vps
  cd /opt/trading-bot
  sed -i 's/TELEGRAM_ENABLED=true/TELEGRAM_ENABLED=false/' .env
  docker-compose restart trading-bot

  # Option 2: Revert to previous version (remove code)
  git checkout <previous-commit-sha>
  docker-compose down
  docker-compose build
  docker-compose up -d

  # Option 3: Use previous Docker image
  docker-compose down
  docker pull ghcr.io/user/trading-bot:<previous-sha>
  docker-compose up -d
  ```

- **Special considerations**: None
  - No migration needed (file-based logs, no schema changes)
  - No feature flag infrastructure (simple boolean TELEGRAM_ENABLED)
  - Data loss acceptable (notification logs ephemeral, can be deleted)

### Artifact Strategy (build-once-promote-many)

- **Build artifact**: Docker image `ghcr.io/user/trading-bot:<commit-sha>`
  - **NOT** `:latest` tag (prevent accidental production deployments)
  - **Build in**: Local development or CI (GitHub Actions if available)
  - **Push to**: GitHub Container Registry or Docker Hub

- **Deploy to staging**: Manual deployment on VPS
  ```bash
  ssh user@staging-vps
  cd /opt/trading-bot
  git pull origin feature/030-telegram-notificatio
  docker-compose down
  docker-compose build
  docker-compose up -d
  ```

- **Promote to production**: Same artifact (same Docker image tag)
  ```bash
  ssh user@production-vps
  cd /opt/trading-bot
  git pull origin feature/030-telegram-notificatio
  docker-compose down
  docker-compose build
  docker-compose up -d
  ```

- **No prebuilt artifacts**: Simpler workflow (build on VPS, no artifact registry needed for solo project)

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios

**Summary**:
- **Scenario 1**: Initial setup (create bot, get chat ID, configure .env, install dependencies, validate)
- **Scenario 2**: Testing notifications (manual test script, integration test with paper trading)
- **Scenario 3**: Validation & debugging (check logs, metrics, common issues, unit tests)
- **Scenario 4**: Disable notifications (rollback to pre-feature state)
- **Scenario 5**: Production deployment (Docker on VPS, verify delivery rate)

**Key Integration Points**:
1. **Bot startup**: NotificationService initialized, credentials validated, enabled flag set
2. **Position entry**: OrderManager executes trade → logs TradeRecord → NotificationService.send_position_entry()
3. **Position exit**: OrderManager closes position → updates TradeRecord → NotificationService.send_position_exit()
4. **Circuit breaker**: CircuitBreaker detects breach → logs event → NotificationService.send_risk_alert()
5. **Performance alert**: AlertEvaluator detects threshold breach → creates AlertEvent → NotificationService.send_risk_alert()

---

## [TESTING STRATEGY]

### Unit Tests (pytest)

**File**: tests/notifications/test_message_formatter.py
- Test Markdown formatting (bold, code, line breaks)
- Test emoji insertion (📈, ✅, ❌, 🚨)
- Test message truncation (4096 char limit, "..." suffix)
- Test Markdown escaping (special characters)
- Test [PAPER] prefix for paper trading mode

**File**: tests/notifications/test_telegram_client.py
- Test send_message success (mock Telegram API 200 response)
- Test send_message timeout (mock slow API, verify 5s timeout)
- Test send_message retry (mock 429 rate limit, verify exponential backoff)
- Test send_message error handling (mock 401 Unauthorized, verify exception caught)

**File**: tests/notifications/test_notification_service.py
- Test TELEGRAM_ENABLED=false (verify notifications skipped)
- Test missing credentials (verify ConfigurationError raised)
- Test rate limiting (send same error type twice, verify 2nd blocked)
- Test async delivery (verify non-blocking with asyncio.create_task)

### Integration Tests (pytest with mocked Telegram API)

**File**: tests/notifications/test_integration.py
- Test full flow: TradeRecord → format → send → log
- Test AlertEvent → format → send → log
- Test notification log created (verify logs/telegram-notifications.jsonl exists)
- Test delivery metrics (verify success rate calculation)

### Coverage Target

- **Target**: >90% (Constitution requirement from §Testing_Requirements)
- **Command**: `pytest tests/notifications/ --cov=trading_bot.notifications --cov-report=term-missing`
- **Exclusions**: Error handling for unreachable Telegram API scenarios (tested manually)

---

## [IMPLEMENTATION PHASES]

### Phase 1: Core Infrastructure (MVP - US1-US3)

1. Create module structure (notifications/, __init__.py)
2. Implement TelegramClient (send_message with timeout)
3. Implement MessageFormatter (position entry/exit, risk alert)
4. Implement NotificationService (orchestration, config checks)
5. Add TELEGRAM_* variables to .env.example
6. Update requirements.txt (python-telegram-bot==20.7)

### Phase 2: Integration (US1-US3)

7. Integrate with AlertEvaluator (performance/alerts.py)
8. Integrate with CircuitBreaker (error_handling/circuit_breaker.py)
9. Add notification calls to bot.py (position entry/exit)
10. Create notification log file (logs/telegram-notifications.jsonl)

### Phase 3: Testing & Validation

11. Write unit tests (formatter, client, service)
12. Write integration tests (end-to-end with mocked API)
13. Manual testing (quickstart scenarios 1-3)
14. Paper trading validation (run bot for 24 hours, verify notifications)

### Phase 4: Documentation & Deployment

15. Create quickstart.md (setup, testing, debugging)
16. Create validate_config.py CLI tool
17. Deploy to staging (Docker on VPS)
18. Monitor delivery rate (verify >99% for 48 hours)
19. Deploy to production (same artifact)

### Phase 5: Future Enhancements (Deferred to US4-US7)

- US4: Error notifications (system errors with rate limiting)
- US5: Performance summaries (daily/weekly scheduled notifications)
- US6: Momentum signal notifications (configurable threshold)
- US7: Bidirectional commands (/status, /stop, /start via Telegram)

---

## [RISK MITIGATION]

### Risk 1: Telegram API downtime breaks trading

- **Mitigation**: Non-blocking async design (FR-001), timeout enforced (5s max)
- **Fallback**: Notifications fail silently, trading continues, errors logged
- **Test**: Simulate API down (block api.telegram.org), verify trades execute

### Risk 2: Notification spam during system instability

- **Mitigation**: Rate limiting (NFR-004 - max 1 per error type per hour)
- **Implementation**: ErrorNotificationCache in-memory dict
- **Test**: Trigger 10 errors of same type, verify only 1 notification sent

### Risk 3: Credential leak in logs

- **Mitigation**: Never log TELEGRAM_BOT_TOKEN (mask with ***REDACTED***)
- **Validation**: Search all log files for token pattern, assert not found
- **Review**: Code review checklist item - "Token never logged"

### Risk 4: Message formatting breaks on edge cases

- **Mitigation**: Pydantic validation, Markdown escaping, truncation
- **Test**: Extreme values (negative P&L, 0 duration, None stop_loss, very long symbol names)
- **Fallback**: Plain text message if Markdown formatting fails

### Risk 5: Cost (Telegram API is free, but what if they start charging?)

- **Mitigation**: Telegram Bot API is free for bots (no usage-based pricing announced)
- **Contingency**: Feature toggle (TELEGRAM_ENABLED=false), no code changes needed
- **Alternative**: SMS notifications (Twilio - paid) or email (SMTP - free) as backup channels

