# Tasks: Telegram Notifications

## [CODEBASE REUSE ANALYSIS]

Scanned: D:\Coding\Stocks\src\trading_bot

### [EXISTING - REUSE]

- ✅ TradeRecord (src/trading_bot/logging/trade_record.py) - Extract position entry/exit data
- ✅ AlertEvaluator (src/trading_bot/performance/alerts.py) - Integrate risk alert notifications
- ✅ CircuitBreaker (src/trading_bot/error_handling/circuit_breaker.py) - Integrate circuit breaker alerts
- ✅ Retry logic (src/trading_bot/error_handling/retry.py) - Exponential backoff pattern
- ✅ Python logging module (src/trading_bot/logger.py) - Structured JSONL logging pattern
- ✅ python-dotenv - Environment variable pattern from .env
- ✅ Pydantic - Schema validation (already in requirements.txt)

### [NEW - CREATE]

- 🆕 TelegramClient (src/trading_bot/notifications/telegram_client.py) - Async Telegram Bot API wrapper
- 🆕 MessageFormatter (src/trading_bot/notifications/message_formatter.py) - Format trade data → Telegram Markdown
- 🆕 NotificationService (src/trading_bot/notifications/notification_service.py) - Orchestration layer
- 🆕 Test suite (tests/notifications/) - Unit and integration tests
- 🆕 Validation CLI (src/trading_bot/notifications/validate_config.py) - Setup validation tool

## [DEPENDENCY GRAPH]

Story completion order:
1. Phase 1: Setup (creates module structure, installs dependencies)
2. Phase 2: Foundational Infrastructure (core notification service - blocks all stories)
3. Phase 3: US1 [P1] - Position entry notifications (independent)
4. Phase 4: US2 [P1] - Position exit notifications (depends on US1 formatter patterns)
5. Phase 5: US3 [P1] - Risk alert notifications (independent of US1/US2)
6. Phase 6: Polish (error handling, testing, deployment prep)

## [PARALLEL EXECUTION OPPORTUNITIES]

- Phase 1: T001, T002, T003 (setup tasks, different files)
- Phase 2: T010, T011, T012 (core components, different files)
- Phase 3: T020, T021 (US1 implementation tasks)
- Phase 4: T030, T031 (US2 implementation tasks)
- Phase 5: T040, T041, T042 (US3 implementation tasks)
- Phase 6: T050, T051, T052, T053, T054, T055 (polish tasks, different files)

## [IMPLEMENTATION STRATEGY]

**MVP Scope**: Phase 3-5 (US1-US3: position entry/exit + risk alerts)
**Incremental delivery**: US1 → US2 → US3 → staging validation → production
**Testing approach**: Unit tests for formatters/client, integration tests for service orchestration, manual testing with paper trading

---

## Phase 1: Setup

- [ ] T001 Create notifications module structure
  - Files: src/trading_bot/notifications/__init__.py
  - Exports: NotificationService, ConfigurationError
  - Pattern: src/trading_bot/performance/__init__.py
  - From: plan.md [STRUCTURE]

- [ ] T002 [P] Add python-telegram-bot dependency to requirements.txt
  - Package: python-telegram-bot==20.7
  - Pattern: Existing requirements.txt format
  - From: plan.md [ARCHITECTURE DECISIONS]

- [ ] T003 [P] Add TELEGRAM_* environment variables to .env.example
  - Variables: TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_NOTIFY_POSITIONS, TELEGRAM_NOTIFY_ALERTS, TELEGRAM_PARSE_MODE, TELEGRAM_INCLUDE_EMOJIS, TELEGRAM_ERROR_RATE_LIMIT_MINUTES
  - Pattern: Existing .env.example sections with comments
  - From: plan.md [CI/CD IMPACT], spec.md Deployment Considerations

---

## Phase 2: Foundational Infrastructure

**Goal**: Core notification service that blocks all user stories

- [ ] T010 [P] Implement TelegramClient in src/trading_bot/notifications/telegram_client.py
  - Methods: async send_message(chat_id, text, parse_mode, timeout)
  - Dependencies: python-telegram-bot, asyncio
  - Error handling: Catch telegram.error.TelegramError, return dict with success status
  - REUSE: Retry logic pattern from src/trading_bot/error_handling/retry.py
  - Pattern: Async client pattern from src/trading_bot/llm/ modules
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T011 [P] Implement MessageFormatter in src/trading_bot/notifications/message_formatter.py
  - Methods: format_position_entry(), format_position_exit(), format_risk_alert(), _truncate(), _escape_markdown()
  - Features: Emoji insertion, Markdown escaping, 4096 char truncation
  - REUSE: TradeRecord fields from src/trading_bot/logging/trade_record.py
  - Pattern: Formatter pattern from src/trading_bot/dashboard/display_renderer.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T012 [P] Implement NotificationService in src/trading_bot/notifications/notification_service.py
  - Methods: async send_position_entry(), async send_position_exit(), async send_risk_alert(), is_enabled()
  - State: enabled flag, bot_token, chat_id, error_cache dict
  - Config checks: Validate TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID on init
  - Rate limiting: ErrorNotificationCache in-memory dict (error_type: last_sent_timestamp)
  - REUSE: Environment variable pattern from python-dotenv
  - Pattern: Service orchestration from src/trading_bot/services/screener_service.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

---

## Phase 3: User Story 1 [P1] - Position entry notifications

**Story Goal**: Traders receive Telegram notifications when positions are opened

**Independent Test Criteria**:
- [ ] Notification sent on successful position entry with all required fields
- [ ] Message distinguishes paper trading vs live trading with [PAPER] prefix
- [ ] Notification failure does not block trade execution (non-blocking delivery)
- [ ] Message includes: ticker, entry price, shares, position size ($), stop loss, target

### Implementation

- [ ] T020 [P] [US1] Add position entry notification to bot.py
  - Integration point: After successful order execution in execute_trade()
  - Call: await notification_service.send_position_entry(trade_record)
  - Error handling: Wrap in try/except, log error, continue execution
  - REUSE: TradeRecord from src/trading_bot/logging/trade_record.py
  - Pattern: Async integration from src/trading_bot/bot.py
  - From: spec.md US1 Acceptance Criteria

- [ ] T021 [P] [US1] Create notification log file logs/telegram-notifications.jsonl
  - Format: JSONL with fields (timestamp, notification_type, delivery_status, chat_id, error_message)
  - Pattern: Existing JSONL logs in logs/ directory
  - From: plan.md [STRUCTURE]

---

## Phase 4: User Story 2 [P1] - Position exit notifications

**Story Goal**: Traders receive Telegram notifications when positions are closed with P&L details

**Independent Test Criteria**:
- [ ] Notification sent on position exit with all required fields
- [ ] Message includes: ticker, exit price, exit reason, P&L ($), P&L (%), duration
- [ ] Message color-codes profit (✅) vs loss (❌) using emoji
- [ ] Notification failure does not block trade execution

### Implementation

- [ ] T030 [P] [US2] Add position exit notification to bot.py
  - Integration point: After position close in close_position() or exit logic
  - Call: await notification_service.send_position_exit(trade_record)
  - Error handling: Wrap in try/except, log error, continue execution
  - REUSE: TradeRecord with outcome/profit_loss fields
  - Pattern: Same async pattern as T020
  - From: spec.md US2 Acceptance Criteria

- [ ] T031 [P] [US2] Format position exit message with P&L calculation
  - Fields: ticker, exit_price, exit_reason (Stop Loss/Take Profit/Manual Close/End of Day/Circuit Breaker), profit_loss, hold_duration_seconds
  - Formatting: Convert duration to human-readable (e.g., "2h 15m"), format P&L with +/- prefix
  - Emoji: ✅ for profit, ❌ for loss
  - REUSE: MessageFormatter._truncate() from T011
  - Pattern: String formatting from src/trading_bot/dashboard/display_renderer.py
  - From: spec.md US2 Acceptance Criteria, plan.md [NEW INFRASTRUCTURE - CREATE]

---

## Phase 5: User Story 3 [P1] - Risk alert notifications

**Story Goal**: Traders receive urgent Telegram alerts when risk circuit breakers trigger

**Independent Test Criteria**:
- [ ] Notification sent within 5 seconds when circuit breaker triggers
- [ ] Message includes: breach type, current value, threshold, timestamp
- [ ] Message uses urgent emoji (🚨) and bold Markdown formatting
- [ ] Notification failure does not affect circuit breaker logic

### Implementation

- [ ] T040 [P] [US3] Integrate with CircuitBreaker in src/trading_bot/error_handling/circuit_breaker.py
  - Integration point: After circuit breaker logs breach event
  - Call: await notification_service.send_risk_alert(alert_event)
  - REUSE: CircuitBreaker breach event data
  - Pattern: Async notification pattern from T020
  - From: plan.md [EXISTING INFRASTRUCTURE - REUSE], spec.md US3

- [ ] T041 [P] [US3] Integrate with AlertEvaluator in src/trading_bot/performance/alerts.py
  - Integration point: AlertEvaluator.evaluate() method after appending alert to list
  - Modification: Add notification_service parameter to __init__, make evaluate() async
  - Call: await notification_service.send_risk_alert(alert_event)
  - REUSE: AlertEvaluator alert creation logic
  - Pattern: Dependency injection from src/trading_bot/performance/tracker.py
  - From: plan.md [EXISTING INFRASTRUCTURE - REUSE], spec.md US3

- [ ] T042 [P] [US3] Format risk alert message with urgent styling
  - Fields: breach_type (max_daily_loss/consecutive_losses/etc), current_value, threshold, timestamp
  - Formatting: Bold text for breach type, 🚨 emoji prefix, Markdown code blocks for values
  - Message template: "🚨 **RISK ALERT: {breach_type}**\nCurrent: `{current_value}`\nThreshold: `{threshold}`\nTime: {timestamp}"
  - REUSE: MessageFormatter._escape_markdown() from T011
  - Pattern: Markdown formatting from MessageFormatter
  - From: spec.md US3 Acceptance Criteria, plan.md [NEW INFRASTRUCTURE - CREATE]

---

## Phase 6: Polish & Cross-Cutting Concerns

### Error Handling & Resilience

- [ ] T050 [P] Add async fire-and-forget delivery with timeout
  - Pattern: asyncio.create_task() with 5s timeout (asyncio.wait_for)
  - Implementation: Wrap send_message() calls in notification_service
  - Error handling: Catch asyncio.TimeoutError, log error, return delivery_status="timeout"
  - REUSE: Async pattern from src/trading_bot/llm/ modules
  - From: plan.md [PATTERNS] Non-Blocking Async Delivery

- [ ] T051 [P] Add graceful degradation for missing credentials
  - Check: TELEGRAM_ENABLED flag and credentials on NotificationService.__init__
  - Behavior: Set self.enabled=False if credentials missing, log warning at INFO level
  - Error: Raise ConfigurationError if TELEGRAM_ENABLED=true but credentials missing
  - Pattern: Graceful degradation from src/trading_bot/startup.py
  - From: plan.md [PATTERNS] Graceful Degradation, spec.md FR-006

- [ ] T052 [P] Add rate limiting for error notifications
  - Implementation: ErrorNotificationCache dict {error_type: last_sent_timestamp}
  - Logic: Check elapsed time, skip notification if <60 minutes since last send
  - Log: delivery_status="rate_limited" for skipped notifications
  - REUSE: Rate limiting pattern from src/trading_bot/llm/rate_limiter.py (if exists)
  - From: plan.md [PATTERNS] Rate Limiting, spec.md NFR-004

### Testing

- [ ] T053 [P] Write unit tests for MessageFormatter in tests/notifications/test_message_formatter.py
  - Tests: Markdown formatting, emoji insertion, truncation (4096 chars), escaping special characters, [PAPER] prefix
  - Coverage: >90% (all public methods)
  - Pattern: Unit test structure from tests/unit/test_trade_record.py
  - From: plan.md [TESTING STRATEGY]

- [ ] T054 [P] Write unit tests for TelegramClient in tests/notifications/test_telegram_client.py
  - Tests: send_message success (mock 200 response), timeout (mock slow API), retry on 429, error handling (mock 401)
  - Mocking: Mock telegram.Bot with pytest-mock or unittest.mock
  - Coverage: >90% (all public methods)
  - Pattern: Unit test with mocking from tests/unit/test_error_handling/test_retry.py
  - From: plan.md [TESTING STRATEGY]

- [ ] T055 [P] Write integration tests for NotificationService in tests/notifications/test_notification_service.py
  - Tests: TELEGRAM_ENABLED=false (skipped notifications), missing credentials (ConfigurationError), rate limiting (same error twice), async delivery (non-blocking)
  - Setup: Use test fixtures for TradeRecord, mock TelegramClient
  - Coverage: >90% (all public methods)
  - Pattern: Integration test structure from tests/integration/test_trade_logging_integration.py
  - From: plan.md [TESTING STRATEGY]

### Deployment Preparation

- [ ] T056 [P] Create validate_config.py CLI tool in src/trading_bot/notifications/validate_config.py
  - Purpose: Validate Telegram credentials, test Bot API connection, verify chat accessible
  - Usage: python -m trading_bot.notifications.validate_config
  - Output: Exit code 0 if valid, 1 if invalid (with error message)
  - Tests: Send test message "✅ Telegram notifications configured successfully"
  - Pattern: CLI tool structure from src/trading_bot/performance/cli.py
  - From: plan.md [STRUCTURE], quickstart.md Scenario 1

- [ ] T057 Create manual test script scripts/test_telegram_notification.py
  - Purpose: Send test notification manually for quickstart validation
  - Usage: python scripts/test_telegram_notification.py
  - Tests: Position entry notification, position exit notification, risk alert notification
  - Output: Success/failure message with delivery time
  - Pattern: Manual test script from existing scripts/ directory
  - From: plan.md [CI/CD IMPACT] Smoke Tests

- [ ] T058 Update NOTES.md with Phase 2 checkpoint
  - Summary: Total tasks, user story breakdown, parallel opportunities, MVP strategy
  - Checkpoint: Tasks generated, dependency graph created, ready for /analyze
  - Pattern: Existing NOTES.md checkpoint format
  - From: /tasks command instructions

---

## [IMPLEMENTATION NOTES]

**Critical Paths**:
1. T010 → T020 → T030 (notification delivery pipeline)
2. T011 → T021 → T031 → T042 (message formatting pipeline)
3. T012 → T040 → T041 (service orchestration pipeline)

**Testing Priority**:
- High: T053, T054, T055 (core functionality)
- Medium: T056, T057 (validation and manual testing)

**Deployment Checklist**:
1. Install python-telegram-bot==20.7 (T002)
2. Configure .env with TELEGRAM_* variables (T003)
3. Run validate_config.py to test credentials (T056)
4. Run manual test script to verify delivery (T057)
5. Deploy to paper trading environment, monitor for 24 hours
6. Verify delivery rate >99% (check logs/telegram-notifications.jsonl)
7. Deploy to production

**Rollback Strategy**:
- Quick rollback: Set TELEGRAM_ENABLED=false in .env, restart bot
- Full rollback: Revert to previous commit, redeploy Docker container

---

## Summary

**Total tasks**: 28
**User story tasks**: 11 (US1: 2, US2: 2, US3: 3, Polish: 4)
**Parallel opportunities**: 20 tasks marked [P]
**Setup tasks**: 3
**MVP scope**: Phase 3-5 (US1-US3 only)

**Task breakdown**:
- Phase 1 (Setup): 3 tasks
- Phase 2 (Foundational): 3 tasks
- Phase 3 (US1): 2 tasks
- Phase 4 (US2): 2 tasks
- Phase 5 (US3): 3 tasks
- Phase 6 (Polish): 8 tasks
- Documentation: 1 task
