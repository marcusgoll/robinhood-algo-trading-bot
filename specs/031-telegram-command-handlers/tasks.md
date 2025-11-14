# Tasks: Telegram Command Handlers for Bot Control and Reporting

## [CODEBASE REUSE ANALYSIS]
Scanned: D:\Coding\Stocks\src\trading_bot, D:\Coding\Stocks\api\app

[EXISTING - REUSE]
- ✅ TelegramClient (src/trading_bot/notifications/telegram_client.py)
- ✅ GET /api/v1/state (api/app/routes/state.py)
- ✅ GET /api/v1/summary (api/app/routes/state.py)
- ✅ GET /api/v1/health (api/app/routes/state.py)
- ✅ StateAggregator service (api/app/services/state_aggregator.py)
- ✅ python-telegram-bot v20.7 (requirements.txt)
- ✅ Environment config patterns (.env.example)
- ✅ API auth patterns (api/app/core/auth.py)
- ✅ Middleware patterns (api/app/middleware/rate_limiter.py)

[NEW - CREATE]
- 🆕 TelegramCommandHandler (no existing pattern)
- 🆕 CommandAuthMiddleware (no existing pattern)
- 🆕 CommandRateLimiter (pattern: api/app/middleware/rate_limiter.py)
- 🆕 ResponseFormatter (pattern: src/trading_bot/notifications/message_formatter.py)
- 🆕 InternalAPIClient (no existing async HTTP client pattern)
- 🆕 POST /api/v1/commands/pause (blocker: missing endpoint)
- 🆕 POST /api/v1/commands/resume (blocker: missing endpoint)
- 🆕 Command schemas (pattern: api/app/schemas/state.py)

## [DEPENDENCY GRAPH]
Task completion order:
1. Phase 1: Setup (T001-T003) - blocking all phases
2. Phase 2: Foundational (T004-T009) - control endpoints and API client
3. Phase 3: Command Infrastructure (T010-T016) - handler framework
4. Phase 4: Command Implementation (T017-T030) - 7 command handlers
5. Phase 5: Polish & Deployment (T031-T036) - integration, docs, deployment

**Critical Path**:
- T004-T009 (Control endpoints) MUST complete before T017-T030 (Commands that call pause/resume)
- T010-T016 (Handler framework) MUST complete before T017-T030 (Command handlers)
- T001-T003 (Setup) MUST complete before all phases

## [PARALLEL EXECUTION OPPORTUNITIES]
- Phase 1: T001, T002, T003 (independent setup tasks)
- Phase 2: T004+T005 (pause endpoint), T006+T007 (resume endpoint), T008+T009 (API client) - parallel streams
- Phase 3: T010, T011, T012 (auth middleware), T013+T014 (rate limiter), T015+T016 (formatter) - parallel after T008
- Phase 4: T017-T023 (read-only commands), T024-T025 (control commands) - 2 parallel groups
- Phase 5: T031-T036 (all parallel after T030)

## [IMPLEMENTATION STRATEGY]
**MVP Scope**: Phase 3 + Phase 4 (Commands T017-T023: /start, /help, /status, /positions, /performance)
**Incremental delivery**:
1. Read-only commands (T017-T023) → staging validation
2. Control commands (T024-T025: /pause, /resume) → staging validation
3. Full integration (T026-T030) → production

**Testing approach**: Unit tests required for all new components (80% coverage), integration tests for command flow, manual testing for Telegram UI/UX

## Phase 1: Setup

- [ ] T001 Add httpx dependency to requirements.txt
  - File: requirements.txt
  - Add: httpx==0.25.0 (async HTTP client for API calls)
  - Pattern: requirements.txt existing entries
  - From: plan.md [ARCHITECTURE DECISIONS] line 74

- [ ] T002 [P] Add new environment variables to .env.example
  - File: .env.example
  - Add: TELEGRAM_AUTHORIZED_USER_IDS (comma-separated integers)
  - Add: TELEGRAM_COMMAND_COOLDOWN_SECONDS (integer, default 5)
  - Pattern: .env.example existing TELEGRAM_* variables (lines 99-101)
  - From: plan.md [CI/CD IMPACT] lines 463-475

- [ ] T003 [P] Create telegram command module directory structure
  - Files: src/trading_bot/telegram/__init__.py
  - Create empty module for new command handler code
  - Pattern: src/trading_bot/notifications/ structure
  - From: plan.md [STRUCTURE] lines 88-90

## Phase 2: Foundational (blocking prerequisites)

**Goal**: Control endpoints and API client infrastructure that blocks command implementation

- [ ] T004 Create PauseRequest/ResumeRequest Pydantic schemas
  - File: api/app/schemas/commands.py (new)
  - Models: PauseRequest (reason: str, user_id: int), ResumeRequest (user_id: int), CommandResponse (success: bool, message: str, timestamp: datetime)
  - REUSE: BaseModel pattern from api/app/schemas/state.py
  - Pattern: api/app/schemas/order.py (Pydantic validation)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] lines 448-452

- [ ] T005 Create POST /api/v1/commands/pause endpoint
  - File: api/app/routes/commands.py (new)
  - Endpoint: POST /api/v1/commands/pause (accepts PauseRequest, returns CommandResponse)
  - Integration: Set bot state to "paused" (via state manager or workflow executor)
  - Auth: Requires X-API-Key header validation
  - Logging: Log pause action with user_id and timestamp
  - REUSE: verify_api_key dependency from api/app/core/auth.py
  - REUSE: Workflow execution pattern from api/app/routes/workflows.py
  - Pattern: api/app/routes/state.py (FastAPI endpoint structure)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] lines 428-436

- [ ] T006 [P] Create POST /api/v1/commands/resume endpoint
  - File: api/app/routes/commands.py (extend)
  - Endpoint: POST /api/v1/commands/resume (accepts ResumeRequest, returns CommandResponse)
  - Integration: Set bot state to "running" (via state manager or workflow executor)
  - Auth: Requires X-API-Key header validation
  - Logging: Log resume action with user_id and timestamp
  - REUSE: verify_api_key dependency from api/app/core/auth.py
  - REUSE: Workflow execution pattern from api/app/routes/workflows.py
  - Pattern: api/app/routes/state.py (FastAPI endpoint structure)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] lines 438-446

- [ ] T007 Register commands router in FastAPI application
  - File: api/app/main.py
  - Add: app.include_router(commands.router, prefix="/api/v1", tags=["commands"])
  - REUSE: Router registration pattern from api/app/main.py
  - Pattern: Existing router includes (state.router, workflows.router)
  - From: plan.md [STRUCTURE] line 101

- [ ] T008 Create InternalAPIClient for calling REST API
  - File: src/trading_bot/telegram/api_client.py (new)
  - Class: InternalAPIClient (httpx.AsyncClient wrapper)
  - Methods: get_state(), get_summary(), get_health(), pause(reason, user_id), resume(user_id)
  - Config: base_url from BOT_API_PORT, auth token from BOT_API_AUTH_TOKEN
  - Timeout: 2 seconds (per spec NFR-001)
  - Error handling: timeout, 401, 500, connection errors
  - Retry: Single retry on timeout (exponential backoff not needed)
  - Pattern: TelegramClient error handling (src/trading_bot/notifications/telegram_client.py lines 78-189)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] lines 416-424

- [ ] T009 [P] Write unit tests for InternalAPIClient
  - File: tests/telegram/test_api_client.py (new)
  - Tests: get_summary() success (200), get_state() success, pause() success, resume() success
  - Tests: Timeout handling, auth failure (401), server error (500)
  - Mock: httpx.AsyncClient using pytest-httpx or respx
  - Coverage: ≥90% (per constitution §Code_Quality, new code must be 100%)
  - Pattern: Existing test patterns from src/trading_bot/risk_management/tests/
  - From: plan.md [TESTING STRATEGY] lines 701-709

## Phase 3: Command Infrastructure

**Goal**: Command handler framework (auth, rate limiting, formatting, lifecycle)

- [ ] T010 Create ResponseFormatter with emoji and markdown helpers
  - File: src/trading_bot/telegram/formatters.py (new)
  - Functions: format_status_response(state: BotSummaryResponse) -> str
  - Functions: format_positions_response(positions: List) -> str
  - Functions: format_performance_response(metrics: dict) -> str
  - Functions: format_help_response(is_authorized: bool) -> str
  - Functions: format_error_response(error: str) -> str
  - Emoji: 🟢 running, ⏸️ paused, 🔴 error, 📊 metrics, 💰 money, ✅ success, ❌ error
  - Markdown: MarkdownV2 format (escape special characters)
  - REUSE: Emoji patterns from src/trading_bot/notifications/message_formatter.py
  - Pattern: src/trading_bot/notifications/message_formatter.py (formatting logic)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] lines 404-413

- [ ] T011 [P] Write unit tests for ResponseFormatter
  - File: tests/telegram/test_formatters.py (new)
  - Tests: format_status_response() with running/paused/error states
  - Tests: format_positions_response() with 0, 1, 10 positions
  - Tests: format_performance_response() with various metrics
  - Tests: Emoji rendering (check for correct emoji in output)
  - Tests: Markdown escaping (special characters like ., _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, })
  - Coverage: ≥90% (per constitution §Code_Quality, new code must be 100%)
  - Pattern: Unit test structure from src/trading_bot/risk_management/tests/test_calculator_atr.py
  - From: plan.md [TESTING STRATEGY] lines 693-699

- [ ] T012 Create CommandAuthMiddleware function
  - File: src/trading_bot/telegram/command_handler.py (new, inline function ~30 lines)
  - Function: async def auth_middleware(update, context) -> bool
  - Logic: Extract user_id from update.effective_user.id
  - Logic: Check against authorized_users set (parsed from TELEGRAM_AUTHORIZED_USER_IDS)
  - Reject: Send "Unauthorized access" message if not authorized
  - Logging: Log auth failures with WARNING level (include user_id)
  - Pattern: api/app/core/auth.py verify_api_key pattern
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] lines 386-392

- [ ] T013 Create CommandRateLimiter function
  - File: src/trading_bot/telegram/command_handler.py (extend, inline function ~40 lines)
  - Function: async def rate_limit_middleware(update, context) -> bool
  - State: Dict[int, float] mapping user_id → last_command_timestamp
  - Logic: Check (now - last_timestamp) >= TELEGRAM_COMMAND_COOLDOWN_SECONDS
  - Reject: Send cooldown message with time remaining if within cooldown
  - Update: Update timestamp on successful command execution
  - Pattern: api/app/middleware/rate_limiter.py (rate limiting logic)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] lines 394-401

- [ ] T014 [P] Write unit tests for auth and rate limiting middleware
  - File: tests/telegram/test_auth_middleware.py (new)
  - File: tests/telegram/test_rate_limiter.py (new)
  - Tests (auth): Authorized user passes, unauthorized rejected, logging verification
  - Tests (rate): First command allowed, second within cooldown rejected, second after cooldown allowed
  - Tests (rate): Timestamp updated on success, multiple users tracked independently
  - Mock: Telegram Update and Context objects
  - Coverage: ≥90% (per constitution §Code_Quality, new code must be 100%)
  - Pattern: Unit test structure from src/trading_bot/risk_management/tests/
  - From: plan.md [TESTING STRATEGY] lines 680-691

- [ ] T015 Create TelegramCommandHandler class with lifecycle methods
  - File: src/trading_bot/telegram/command_handler.py (extend, main orchestrator)
  - Class: TelegramCommandHandler
  - Init: Parse TELEGRAM_AUTHORIZED_USER_IDS, create Application, instantiate InternalAPIClient
  - Methods: start() - initialize Application and start polling
  - Methods: stop() - graceful shutdown, stop polling
  - Methods: register_handlers() - register 7 CommandHandler instances
  - Dependencies: InternalAPIClient, ResponseFormatter
  - REUSE: TelegramClient initialization pattern (src/trading_bot/notifications/telegram_client.py)
  - Pattern: src/trading_bot/notifications/telegram_client.py (class structure, lifecycle)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] lines 373-383

- [ ] T016 [P] Write unit tests for TelegramCommandHandler
  - File: tests/telegram/test_command_handler.py (new)
  - Tests: Handler initialization (authorized users parsed from env)
  - Tests: Command registration (7 commands registered)
  - Tests: Lifecycle (start, stop, graceful shutdown)
  - Tests: Error handling (Telegram API errors, unexpected exceptions)
  - Mock: python-telegram-bot Application
  - Coverage: ≥90% (per constitution §Code_Quality, new code must be 100%)
  - Pattern: Unit test structure from src/trading_bot/risk_management/tests/
  - From: plan.md [TESTING STRATEGY] lines 673-678

## Phase 4: Command Implementation

**Goal**: Implement 7 command handlers (/start, /help, /status, /positions, /performance, /pause, /resume)

### Read-Only Commands (Parallel Group 1)

- [ ] T017 [P] Implement /start command handler
  - File: src/trading_bot/telegram/command_handler.py (extend, method ~30 lines)
  - Function: async def start_handler(update, context)
  - Middleware: auth_middleware (check authorization)
  - Response: Welcome message with bot intro, capabilities overview, link to /help
  - Format: Use format_help_response() or inline markdown
  - From: spec.md FR-010 lines 187-193, plan.md line 127

- [ ] T018 [P] Implement /help command handler
  - File: src/trading_bot/telegram/command_handler.py (extend, method ~30 lines)
  - Function: async def help_handler(update, context)
  - Middleware: auth_middleware (check authorization)
  - Response: format_help_response(is_authorized=True) - command list with descriptions
  - Format: Markdown with emoji (🤖 header)
  - From: spec.md FR-009 lines 180-186, Appendix lines 475-489

- [ ] T019 [P] Implement /status command handler
  - File: src/trading_bot/telegram/command_handler.py (extend, method ~40 lines)
  - Function: async def status_handler(update, context)
  - Middleware: auth_middleware, rate_limit_middleware
  - API Call: await api_client.get_summary()
  - Response: format_status_response(summary) - mode, positions count, account, last signal
  - Error: format_error_response() if API call fails
  - Timeout: 2 seconds (httpx timeout)
  - From: spec.md FR-004 lines 138-146, Appendix lines 429-440

- [ ] T020 [P] Implement /positions command handler
  - File: src/trading_bot/telegram/command_handler.py (extend, method ~40 lines)
  - Function: async def positions_handler(update, context)
  - Middleware: auth_middleware, rate_limit_middleware
  - API Call: await api_client.get_state()
  - Response: format_positions_response(state.positions) - symbol, P/L, size, duration
  - Format: Color-coded emoji (🟢 profit, 🔴 loss, ⚪ break-even)
  - Error: format_error_response() if API call fails
  - From: spec.md FR-007 lines 161-170, Appendix lines 442-459

- [ ] T021 [P] Implement /performance command handler
  - File: src/trading_bot/telegram/command_handler.py (extend, method ~40 lines)
  - Function: async def performance_handler(update, context)
  - Middleware: auth_middleware, rate_limit_middleware
  - API Call: await api_client.get_state()
  - Response: format_performance_response(state.performance) - win rate, P/L, streak, best/worst
  - Format: Emoji for metrics (📈 performance, 🔥 streak)
  - Error: format_error_response() if API call fails
  - From: spec.md FR-008 lines 172-179, Appendix lines 461-472

- [ ] T022 [P] Implement unknown command handler
  - File: src/trading_bot/telegram/command_handler.py (extend, method ~20 lines)
  - Function: async def unknown_handler(update, context)
  - Response: "Unknown command. Use /help to see available commands."
  - Format: Simple error message with helpful suggestion
  - From: spec.md FR-001 line 122

- [ ] T023 [P] Write integration tests for read-only commands
  - File: tests/integration/test_telegram_commands.py (new)
  - Tests: /start returns welcome message
  - Tests: /help returns command list
  - Tests: /status calls get_summary() and formats response
  - Tests: /positions calls get_state() and formats positions
  - Tests: /performance calls get_state() and formats metrics
  - Tests: Unknown command shows error message
  - Mock: InternalAPIClient (httpx responses)
  - Mock: Telegram Update and Context
  - Coverage: ≥60% integration coverage
  - Pattern: Integration test structure from src/trading_bot/risk_management/tests/test_integration_atr.py
  - From: plan.md [TESTING STRATEGY] lines 712-717

### Control Commands (Parallel Group 2)

- [ ] T024 Implement /pause command handler
  - File: src/trading_bot/telegram/command_handler.py (extend, method ~40 lines)
  - Function: async def pause_handler(update, context)
  - Middleware: auth_middleware, rate_limit_middleware
  - API Call: await api_client.pause(reason="User command", user_id=update.effective_user.id)
  - Response: "⏸️ Trading paused. Existing positions remain open. Use /resume to continue."
  - Confirmation: Include timestamp
  - Error: format_error_response() if API call fails
  - From: spec.md FR-005 lines 147-153, Appendix pause command

- [ ] T025 Implement /resume command handler
  - File: src/trading_bot/telegram/command_handler.py (extend, method ~40 lines)
  - Function: async def resume_handler(update, context)
  - Middleware: auth_middleware, rate_limit_middleware
  - API Call: await api_client.resume(user_id=update.effective_user.id)
  - Response: "▶️ Trading resumed. Bot will process new signals."
  - Confirmation: Include timestamp
  - Error: format_error_response() if API call fails
  - From: spec.md FR-006 lines 154-160, Appendix resume command

- [ ] T026 Write integration tests for control commands
  - File: tests/integration/test_telegram_commands.py (extend)
  - Tests: /pause calls pause() endpoint and confirms state change
  - Tests: /resume calls resume() endpoint and confirms state change
  - Tests: Idempotency (pause when already paused, resume when running)
  - Mock: InternalAPIClient (httpx POST responses)
  - Mock: Telegram Update and Context
  - Coverage: ≥60% integration coverage
  - Pattern: Integration test structure from src/trading_bot/risk_management/tests/test_integration_atr.py
  - From: plan.md [TESTING STRATEGY] lines 712-717

### Handler Registration

- [ ] T027 Register all 7 command handlers in Application
  - File: src/trading_bot/telegram/command_handler.py (extend register_handlers() method)
  - Register: CommandHandler("start", start_handler)
  - Register: CommandHandler("help", help_handler)
  - Register: CommandHandler("status", status_handler)
  - Register: CommandHandler("pause", pause_handler)
  - Register: CommandHandler("resume", resume_handler)
  - Register: CommandHandler("positions", positions_handler)
  - Register: CommandHandler("performance", performance_handler)
  - Register: MessageHandler(filters.COMMAND, unknown_handler) - catch-all for unknown commands
  - Pattern: python-telegram-bot Application.add_handler() pattern
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] line 378

### Error Handling & Logging

- [ ] T028 Add global error handler for uncaught exceptions
  - File: src/trading_bot/telegram/command_handler.py (extend, method ~30 lines)
  - Function: async def error_handler(update, context)
  - Logging: Log error with ERROR level (include stack trace, user_id, command)
  - Response: Send user-friendly error message (no stack trace exposed)
  - Response: "An error occurred. Please try again later."
  - Pattern: TelegramClient error handling (src/trading_bot/notifications/telegram_client.py)
  - From: spec.md FR-012 lines 203-208, plan.md line 127

- [ ] T029 Add audit logging for all command executions
  - File: src/trading_bot/telegram/command_handler.py (extend all handlers)
  - Logging: Log all commands with INFO level (timestamp, user_id, command, success/failure)
  - Logging: Log auth failures with WARNING level (user_id, attempted command)
  - Logging: Log rate limit violations with WARNING level (user_id, time remaining)
  - Format: JSON-formatted log entries for structured logging
  - Pattern: Existing logging from src/trading_bot/logger.py
  - From: spec.md FR-013 lines 209-217, plan.md [SECURITY] lines 286-291

- [ ] T030 Write end-to-end integration test for complete command flow
  - File: tests/integration/test_telegram_commands.py (extend)
  - Test: Complete workflow (10-step sequence from quickstart.md)
  - Sequence: /start → /help → /status → /positions → /performance → /pause → /status (paused) → /resume → /status (running) → unknown command
  - Verify: All responses formatted correctly, API calls made, state changes applied
  - Mock: InternalAPIClient, Telegram Update/Context
  - Coverage: ≥90% critical path
  - Pattern: E2E test structure from plan.md [TESTING STRATEGY]
  - From: plan.md [INTEGRATION SCENARIOS] lines 655-666

## Phase 5: Polish & Cross-Cutting Concerns

### Deployment Preparation

- [ ] T031 [P] Add smoke tests for control endpoints to CI
  - File: tests/smoke/test_telegram_commands.py (new)
  - Tests: POST /api/v1/commands/pause (200 response)
  - Tests: POST /api/v1/commands/resume (200 response)
  - Tests: API auth validation (401 when missing token)
  - Duration: <90s total (smoke tests must be fast)
  - Pattern: Existing smoke test patterns (if any)
  - From: plan.md [CI/CD IMPACT] lines 508-524

- [ ] T032 [P] Document rollback procedure in NOTES.md
  - File: specs/031-telegram-command-handlers/NOTES.md (extend)
  - Document: Rollback trigger conditions (crashes, auth bypass, rate limit failure)
  - Document: 5-step rollback procedure (disable via TELEGRAM_ENABLED=false, restart, verify, investigate, fix)
  - Document: Special considerations (no DB rollback, feature flag, notifications continue)
  - Pattern: Standard 3-command rollback from docs/ROLLBACK_RUNBOOK.md (if exists)
  - From: plan.md [DEPLOYMENT ACCEPTANCE] lines 616-631

- [ ] T033 [P] Add feature startup integration in main bot
  - File: src/trading_bot/main.py or src/trading_bot/startup.py
  - Integration: Import TelegramCommandHandler
  - Integration: Check TELEGRAM_ENABLED flag before starting handler
  - Integration: Start handler in async context (await handler.start())
  - Integration: Register shutdown hook (await handler.stop() on SIGTERM/SIGINT)
  - REUSE: TelegramClient startup pattern from existing bot initialization
  - Pattern: Existing service startup in src/trading_bot/startup.py
  - From: plan.md [STRUCTURE] command_handler.py lifecycle

- [ ] T034 [P] Update Docker configuration for new dependency
  - File: requirements.txt (already done in T001, verify)
  - File: Dockerfile (verify httpx installed during build)
  - Rebuild: `docker-compose build bot` to include httpx
  - Pattern: Existing Docker build process
  - From: plan.md [CI/CD IMPACT] lines 478-481

- [ ] T035 [P] Create deployment validation checklist
  - File: specs/031-telegram-command-handlers/NOTES.md (extend)
  - Checklist: Environment variables set (TELEGRAM_AUTHORIZED_USER_IDS, TELEGRAM_COMMAND_COOLDOWN_SECONDS)
  - Checklist: Authorized user IDs validated (9-10 digit integers)
  - Checklist: BOT_API_AUTH_TOKEN matches between bot and API
  - Checklist: Send /start from staging Telegram bot (verify welcome message)
  - Checklist: Send /status from authorized user (verify <3s response)
  - Checklist: Send command from unauthorized user (verify rejection)
  - From: plan.md [DEPLOYMENT ACCEPTANCE] lines 553-559, [CI/CD IMPACT] lines 526-530

- [ ] T036 [P] Add manual testing checklist for mobile UX
  - File: specs/031-telegram-command-handlers/NOTES.md (extend)
  - Checklist: Emoji render correctly on iOS Telegram app
  - Checklist: Emoji render correctly on Android Telegram app
  - Checklist: Markdown formatting displays correctly (bold, code blocks)
  - Checklist: Response fits on screen without horizontal scroll
  - Checklist: Response times meet targets (/help <500ms, /status <3s, /positions <3s, /pause <2s, /resume <2s)
  - Checklist: Dark mode readable (if Telegram theme is dark)
  - From: plan.md [TESTING STRATEGY] lines 721-739

## [TEST GUARDRAILS]

**Coverage Requirements:**
- New code: 100% coverage (no untested lines in new features)
- Unit tests: ≥90% line coverage (per constitution §Code_Quality)
- Integration tests: ≥60% line coverage
- E2E tests: ≥90% critical path coverage

**Speed Requirements:**
- Unit tests: <2s each
- Integration tests: <10s each
- E2E tests: <30s each
- Full suite: <6 min total

**Measurement:**
- Python: `pytest --cov=src/trading_bot/telegram --cov=api/app/routes/commands --cov-report=term-missing`
- Run from project root: `pytest tests/telegram/ tests/integration/test_telegram_commands.py -v`

**Quality Gates:**
- All tests must pass before merge
- Coverage thresholds enforced in CI
- No skipped tests without documented reason

**Clarity Requirements:**
- One behavior per test
- Descriptive names: `test_unauthorized_user_receives_rejection_message()`
- Given-When-Then structure in test body

**Anti-Patterns:**
- ❌ NO UI snapshots (brittle, break on formatting changes)
- ❌ NO testing implementation details (test behavior, not internal state)
- ✅ USE behavior assertions (check response content, not object properties)
- ✅ USE clear test names (describe expected outcome)
