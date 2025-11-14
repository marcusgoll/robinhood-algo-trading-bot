# Implementation Plan: Telegram Command Handlers for Bot Control and Reporting

## [RESEARCH DECISIONS]

See: research.md for full research findings (Decision 1-6 documented)

**Summary**:
- Stack: Python 3.11, python-telegram-bot v20.7 (Application framework), httpx (async HTTP client)
- Components to reuse: 7 (TelegramClient, StateAggregator, REST API endpoints, env config patterns)
- New components needed: 5 (TelegramCommandHandler, auth/rate limiting middleware, formatters, API client)
- Control endpoints: Need to add POST /api/v1/commands/pause and POST /api/v1/commands/resume

**Key Architectural Decisions**:
1. Use python-telegram-bot Application framework for command routing (built-in, maintainable)
2. Call REST API endpoints via httpx (reuse StateAggregator, leverage cache, maintain consistency)
3. Store authorized user IDs in .env (follows existing pattern, simple for micro-scale)
4. Per-user global cooldown (5 seconds, protects both Telegram and REST APIs)
5. Async command handlers (non-blocking, matches existing TelegramClient pattern)
6. Emoji + MarkdownV2 for mobile-first UX (scannable, visually clear)

---

## [ARCHITECTURE DECISIONS]

### Stack

**Backend**:
- Language: Python 3.11 (existing)
- Framework: python-telegram-bot 20.7 (existing from Feature #030)
- HTTP Client: httpx (new dependency - async HTTP client for API calls)
- API Server: FastAPI 0.104.1 (existing from Feature #029)
- Cache: Redis 7.x (existing - used by StateAggregator)

**Deployment**:
- Platform: Hetzner VPS (Docker Compose)
- Orchestration: Docker Compose 3.8
- Model: remote-staging-prod (staging and production on VPS)

### Patterns

**Command Handler Pattern**:
- Python-telegram-bot Application with CommandHandler instances
- Each command mapped to async handler function
- Middleware chain: authentication → rate limiting → command execution
- Rationale: Built-in routing, error handling, maintainable, reduces boilerplate

**API Gateway Pattern**:
- TelegramCommandHandler acts as gateway to REST API
- All state queries proxied through Internal API Client (httpx)
- No direct access to StateAggregator or database
- Rationale: Service boundary separation, reuse API cache, single source of truth

**Middleware Pattern**:
- CommandAuthMiddleware: Checks user_id against authorized set (before execution)
- CommandRateLimiter: Enforces cooldown per user (before execution)
- Error handling: Catch all exceptions, send user-friendly messages, log errors
- Rationale: Cross-cutting concerns handled in one place, testable in isolation

**Repository Pattern** (for API client):
- InternalAPIClient wraps httpx operations
- Methods: get_state(), get_summary(), get_health(), pause(), resume()
- Handles: auth headers, timeouts, retries, error responses
- Rationale: Encapsulates HTTP concerns, easier to mock for testing

**Formatter Pattern**:
- ResponseFormatter static methods for each command
- Input: API response schemas, Output: Telegram-formatted strings (emoji + markdown)
- Pure functions (no side effects, easily testable)
- Rationale: Separates formatting logic from command handlers, reusable

### Dependencies

**New packages required**:
- `httpx==0.25.0` - Async HTTP client for API calls (add to requirements.txt)

**Existing packages reused**:
- `python-telegram-bot==20.7` - Already installed from Feature #030
- `fastapi==0.104.1` - Already installed from Feature #029
- `uvicorn==0.24.0` - Already installed from Feature #029

---

## [STRUCTURE]

### Directory Layout

```
src/trading_bot/
├── telegram/                      # NEW: Telegram command handler module
│   ├── __init__.py
│   ├── command_handler.py         # TelegramCommandHandler, auth, rate limiting
│   ├── formatters.py              # Response formatting (emoji + markdown)
│   └── api_client.py              # Internal API client (httpx wrapper)
│
├── notifications/                 # EXISTING: From Feature #030
│   └── telegram_client.py         # TelegramClient.send_message() (reused)
│
api/app/
├── routes/
│   ├── state.py                   # EXISTING: GET /state, /summary, /health
│   └── commands.py                # NEW: POST /pause, /resume endpoints
│
├── services/
│   └── state_aggregator.py       # EXISTING: Reused for state queries
│
├── schemas/
│   ├── state.py                   # EXISTING: BotStateResponse, BotSummaryResponse
│   └── commands.py                # NEW: PauseRequest, ResumeRequest, CommandResponse
│
tests/
├── telegram/                      # NEW: Tests for command handler
│   ├── test_command_handler.py    # Handler initialization, lifecycle
│   ├── test_auth_middleware.py    # Authorization logic
│   ├── test_rate_limiter.py       # Rate limiting logic
│   ├── test_formatters.py         # Response formatting
│   └── test_api_client.py         # HTTP client operations
│
└── api/
    └── test_commands.py           # NEW: Tests for pause/resume endpoints
```

### Module Organization

**src/trading_bot/telegram/command_handler.py** (350-400 lines):
- TelegramCommandHandler class (main orchestrator)
- CommandAuthMiddleware (inline function, 30 lines)
- CommandRateLimiter (inline function, 40 lines)
- Command handler functions (7 functions × 30 lines = 210 lines)
- Lifecycle methods: start(), stop(), graceful_shutdown()

**src/trading_bot/telegram/formatters.py** (200-250 lines):
- format_status_response(state: BotSummaryResponse) -> str
- format_positions_response(positions: List[PositionResponse]) -> str
- format_performance_response(metrics: PerformanceMetricsResponse) -> str
- format_help_response(is_authorized: bool) -> str
- format_error_response(error: str) -> str
- Emoji constants, markdown helpers

**src/trading_bot/telegram/api_client.py** (150-200 lines):
- InternalAPIClient class
- Methods: get_state(), get_summary(), get_health(), pause(), resume()
- Error handling, timeout, retry logic
- HTTP header management (X-API-Key)

**api/app/routes/commands.py** (100-150 lines):
- POST /api/v1/commands/pause
- POST /api/v1/commands/resume
- Integration with bot state management (pause/resume logic)
- Audit logging

**api/app/schemas/commands.py** (50-80 lines):
- PauseRequest, ResumeRequest, CommandResponse Pydantic models

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- Entities: 0 persistent (feature is stateless)
- Ephemeral state: CommandRateLimitState (in-memory dict), AuthorizedUserSet (in-memory set)
- Relationships: None (no database)
- Migrations required: No
- Audit trail: Structured logging (JSON-formatted log entries)

**Key Data Structures**:
- Rate limit state: `Dict[int, Dict[str, float]]` - Maps user_id → {last_command_timestamp, command_name}
- Authorized users: `Set[int]` - Set of authorized Telegram user IDs (parsed from env on startup)

---

## [PERFORMANCE TARGETS]

### From spec.md NFRs

**Response Time** (spec NFR-001):
- Command responses within 3 seconds (P95)
- Acknowledgment within 500ms
- API call timeout: 2 seconds

**Availability** (spec NFR-002):
- Command handler available during API failures (graceful degradation)
- Telegram API failures do not crash handler
- Auto-recovery from transient errors

**Security** (spec NFR-003):
- 100% of unauthorized attempts rejected and logged
- API token never exposed in Telegram messages
- All commands logged with user ID and timestamp

**Scalability** (spec NFR-004):
- Support 10 authorized users
- Rate limiting: 5-second cooldown (configurable)
- Command processing does not block trading operations

### Lighthouse Targets

N/A - No web interface (backend-only feature)

### Performance Budget Breakdown

| Command | API Call | Format | Telegram API | Buffer | Total Target |
|---------|----------|--------|--------------|--------|--------------|
| /help | 0ms | 10ms | 100ms | 390ms | 500ms |
| /start | 0ms | 10ms | 100ms | 390ms | 500ms |
| /status | 200ms | 50ms | 100ms | 2650ms | 3000ms |
| /positions | 300ms | 100ms | 100ms | 2500ms | 3000ms |
| /performance | 300ms | 100ms | 100ms | 2500ms | 3000ms |
| /pause | 100ms | 50ms | 100ms | 1750ms | 2000ms |
| /resume | 100ms | 50ms | 100ms | 1750ms | 2000ms |

**Buffer allocation**: Accounts for network latency (staging: 50ms, production: 100ms), Telegram API variability (50-150ms), cold-start delays (0-500ms)

---

## [SECURITY]

### Authentication Strategy

**User ID Authentication**:
- Extract user_id from `update.effective_user.id` (Telegram API)
- Check against `TELEGRAM_AUTHORIZED_USER_IDS` environment variable
- Reject if not in authorized set (send error + log warning)
- No token-based auth (Telegram provides user_id validation)

**API Authentication**:
- Include `X-API-Key` header in all API calls
- Value from `BOT_API_AUTH_TOKEN` environment variable
- API server validates via `verify_api_key` dependency

### Authorization Model

**Single Role**:
- All authorized users have equal permissions (no RBAC)
- Rationale: Micro-scale bot, single trader or small team
- Future: Could add admin/viewer roles if multi-user needs emerge

**Protected Operations**:
- /pause, /resume: Control commands (audit logged)
- /status, /positions, /performance: Read-only (no state changes)
- /help, /start: Public (but still require authorization)

### Input Validation

**Telegram Inputs**:
- user_id: Integer validation (Telegram API guarantees format)
- command: Parsed by python-telegram-bot framework (validated at routing layer)
- No user-provided arguments in v1 (all commands are fixed syntax)

**API Request Validation**:
- Pydantic schemas for pause/resume requests (PauseRequest, ResumeRequest)
- Timeout validation: 2 seconds max (httpx timeout)
- Response validation: Check HTTP status codes (200, 401, 500)

### Rate Limiting

**Per-User Cooldown**:
- Default: 5 seconds (configurable via `TELEGRAM_COMMAND_COOLDOWN_SECONDS`)
- Enforcement: Check `(now - last_command_timestamp) >= cooldown`
- Storage: In-memory dict (ephemeral, resets on restart)
- Bypass: None (all users subject to rate limiting, including admins)

**Telegram API Rate Limits**:
- Telegram enforces 30 messages/second per bot (unlikely to hit with 5s cooldown)
- TelegramClient has built-in timeout and retry logic (from Feature #030)

**REST API Rate Limits**:
- Feature #029 spec mentions 100 requests/minute (not yet implemented)
- Command handler cooldown (5s) = max 12 requests/minute per user
- 10 users × 12 req/min = 120 req/min (slightly above API limit)
- Mitigation: API cache (60s TTL) reduces actual backend load

### Data Protection

**PII Handling**:
- User ID logged (necessary for audit trail)
- Username logged if available (optional, for human readability)
- No email, phone, or sensitive data exposed in logs or responses

**Secret Management**:
- TELEGRAM_BOT_TOKEN: Environment variable only (never in code)
- BOT_API_AUTH_TOKEN: Environment variable only
- No secrets in error messages or Telegram responses

**Audit Logging**:
- All command executions logged with timestamp, user_id, command, success/failure
- Auth failures logged with WARNING level
- Rate limit violations logged with WARNING level
- Command execution logged with INFO level

---

## [EXISTING INFRASTRUCTURE - REUSE] (7 components)

### From Feature #030 (Telegram Notifications)

**TelegramClient.send_message()**
- File: src/trading_bot/notifications/telegram_client.py:78-189
- Capability: Async message sending with timeout (5s default), retry logic, error handling
- Usage: `await telegram_client.send_message(chat_id, formatted_text, parse_mode="Markdown")`
- Reuse strategy: Import and instantiate in TelegramCommandHandler

**TelegramClient.validate_credentials()**
- File: src/trading_bot/notifications/telegram_client.py:191-223
- Capability: Bot token validation via getMe API
- Usage: Validate token on startup before starting command handler

**python-telegram-bot library**
- File: requirements.txt:59
- Version: 20.7
- Capability: Telegram Bot API wrapper (Application, CommandHandler, async support)
- Reuse strategy: No new installation needed

### From Feature #029 (REST API)

**GET /api/v1/state**
- File: api/app/routes/state.py:28-66
- Capability: Complete bot state (positions, account, health, performance)
- Cache: 60-second TTL (configurable via BOT_STATE_CACHE_TTL)
- Response: BotStateResponse (api/app/schemas/state.py)
- Auth: X-API-Key header (BOT_API_AUTH_TOKEN)
- Usage: /positions and /performance commands

**GET /api/v1/summary**
- File: api/app/routes/state.py:68-101
- Capability: Compressed state summary (<10KB, <2500 tokens)
- Cache: Same as /state (60s TTL)
- Response: BotSummaryResponse (api/app/schemas/state.py)
- Usage: /status command (faster, less data to parse)

**GET /api/v1/health**
- File: api/app/routes/state.py:104-134
- Capability: Health status (circuit breaker, API connectivity, error count)
- Response: HealthStatus (api/app/schemas/state.py)
- Usage: Fallback for /status if /summary unavailable

**StateAggregator service**
- File: api/app/services/state_aggregator.py
- Capability: Aggregates state from dashboard, performance tracker, health monitor
- Cache: 60-second TTL with automatic invalidation
- Methods: get_bot_state(), get_health_status(), get_summary()
- Reuse strategy: Called indirectly via REST API endpoints (not direct import)

### Environment Configuration Pattern

**TELEGRAM_BOT_TOKEN** (.env.example:100)
- Existing from Feature #030
- Used to initialize TelegramClient and Application

**TELEGRAM_CHAT_ID** (.env.example:101)
- Existing from Feature #030
- Used for sending command responses

**TELEGRAM_ENABLED** (.env.example:99)
- Existing flag for graceful degradation
- Command handler respects this flag (no startup if disabled)

**BOT_API_AUTH_TOKEN** (.env.example:91)
- Existing from Feature #029
- Included in X-API-Key header for API calls

**BOT_API_PORT** (.env.example:90)
- Existing from Feature #029
- Used to construct API base URL (http://localhost:{port})

---

## [NEW INFRASTRUCTURE - CREATE] (5 components)

### Backend Components

**1. TelegramCommandHandler class**
- File: src/trading_bot/telegram/command_handler.py (new)
- Lines: 350-400
- Responsibilities:
  - Initialize python-telegram-bot Application
  - Register 7 command handlers (/start, /status, /pause, /resume, /positions, /performance, /help)
  - Manage authentication and rate limiting middleware
  - Lifecycle management (start, stop, graceful shutdown)
  - Error handling and logging
- Dependencies: TelegramClient (message sending), InternalAPIClient (API calls), ResponseFormatter (formatting)
- Testing: Unit tests for handler initialization, command routing, error handling

**2. CommandAuthMiddleware**
- File: src/trading_bot/telegram/command_handler.py (inline function, 30 lines)
- Responsibilities:
  - Extract user_id from Telegram update
  - Check against authorized_users set (parsed from env on startup)
  - Reject unauthorized users with error message
  - Log auth failures with WARNING level
- Testing: Unit tests for authorized/unauthorized users, logging verification

**3. CommandRateLimiter**
- File: src/trading_bot/telegram/command_handler.py (inline function, 40 lines)
- Responsibilities:
  - Track last_command_timestamp per user_id (in-memory dict)
  - Enforce cooldown period (TELEGRAM_COMMAND_COOLDOWN_SECONDS)
  - Reject commands within cooldown with time-remaining message
  - Update timestamp on successful execution
- Testing: Unit tests for cooldown enforcement, timestamp updates, edge cases (first command, exactly at cooldown boundary)

**4. ResponseFormatter**
- File: src/trading_bot/telegram/formatters.py (new, 200-250 lines)
- Responsibilities:
  - format_status_response(state: BotSummaryResponse) -> str
  - format_positions_response(positions: List[PositionResponse]) -> str
  - format_performance_response(metrics: PerformanceMetricsResponse) -> str
  - format_help_response(is_authorized: bool) -> str
  - format_error_response(error: str) -> str
- Emoji mapping: 🟢 running, ⏸️ paused, 🔴 error, 📊 metrics, 💰 money, ✅ success, ❌ error, 🟢 profit, 🔴 loss
- Markdown formatting: Bold for headers, code blocks for data, lists for items
- Testing: Unit tests for each formatter, emoji rendering, markdown escaping

**5. InternalAPIClient**
- File: src/trading_bot/telegram/api_client.py (new, 150-200 lines)
- Responsibilities:
  - Wrapper around httpx.AsyncClient for calling localhost:8000/api/v1/*
  - Methods: get_state(), get_summary(), get_health(), pause(), resume()
  - Include X-API-Key header from BOT_API_AUTH_TOKEN
  - Timeout: 2 seconds (spec NFR-001)
  - Error handling: timeout, 401 Unauthorized, 500 Internal Server Error
  - Retry logic: Single retry on timeout (exponential backoff not needed for internal API)
- Testing: Unit tests with httpx mock, timeout scenarios, auth errors, HTTP status codes

### API Components (Feature #029 extension)

**6. POST /api/v1/commands/pause**
- File: api/app/routes/commands.py (new, 50-70 lines)
- Responsibilities:
  - Accept PauseRequest (reason, user_id)
  - Set bot state to "paused" (via state manager)
  - Return CommandResponse (success, message, timestamp)
  - Log pause action with user_id
- Integration: Calls bot state manager to update running flag
- Testing: Integration tests for state change, idempotency (pause when already paused), auth

**7. POST /api/v1/commands/resume**
- File: api/app/routes/commands.py (new, 50-70 lines)
- Responsibilities:
  - Accept ResumeRequest (user_id)
  - Set bot state to "running" (via state manager)
  - Return CommandResponse (success, message, timestamp)
  - Log resume action with user_id
- Integration: Calls bot state manager to update running flag
- Testing: Integration tests for state change, idempotency (resume when already running), auth

**8. Pydantic schemas for commands**
- File: api/app/schemas/commands.py (new, 50-80 lines)
- Models: PauseRequest, ResumeRequest, CommandResponse
- Validation: Required fields, field types, string length limits
- Testing: Unit tests for validation (valid inputs, missing fields, invalid types)

---

## [CI/CD IMPACT]

### Platform Dependencies

**None** - Pure Python code, no new platform requirements

### Environment Variables

**New Variables** (required):
- `TELEGRAM_AUTHORIZED_USER_IDS` - Comma-separated Telegram user IDs (e.g., "123456789,987654321")
  - Format: Comma-separated integers
  - Validation: Parse to list, reject if empty or invalid format
  - Staging value: Single test user ID
  - Production value: 1-3 trader user IDs

- `TELEGRAM_COMMAND_COOLDOWN_SECONDS` - Rate limit cooldown period
  - Format: Integer (1-60 seconds)
  - Default: 5 seconds
  - Staging value: 3 (faster testing)
  - Production value: 5 (production rate limit)

**New Dependencies**:
- `httpx==0.25.0` - Async HTTP client
  - Add to requirements.txt
  - Docker image rebuild required

**Existing Variables** (reused):
- `TELEGRAM_BOT_TOKEN` - From Feature #030
- `TELEGRAM_CHAT_ID` - From Feature #030
- `TELEGRAM_ENABLED` - From Feature #030
- `BOT_API_AUTH_TOKEN` - From Feature #029
- `BOT_API_PORT` - From Feature #029

### Breaking Changes

**None** - Feature is additive only

- Existing Telegram notifications continue to work unchanged
- No API endpoint removals or signature changes
- No configuration file format changes
- Backward compatibility: Can be disabled via TELEGRAM_ENABLED=false without code changes

### Migration Required

**None** - No database schema changes

- No new tables
- No data migration scripts
- No Alembic migrations
- Stateless feature (ephemeral state only)

### Smoke Tests

**API Smoke Tests** (add to deployment validation):
```bash
# Test pause endpoint
curl -X POST http://localhost:8000/api/v1/commands/pause \
  -H "X-API-Key: $BOT_API_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "smoke test", "user_id": 123456789}'
# Expected: 200 {"success": true, "message": "Trading paused", ...}

# Test resume endpoint
curl -X POST http://localhost:8000/api/v1/commands/resume \
  -H "X-API-Key: $BOT_API_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123456789}'
# Expected: 200 {"success": true, "message": "Trading resumed", ...}
```

**Telegram Smoke Tests** (manual):
- Send /start command from authorized user (expect welcome message)
- Send /status command (expect bot status with <3s response)
- Send /help command (expect command list)
- Send command from unauthorized user (expect rejection message)

### Platform Coupling

**Hetzner VPS**:
- No changes needed (same Docker Compose deployment)
- Restart required after .env update (to load new TELEGRAM_AUTHORIZED_USER_IDS)

**Docker**:
- Dockerfile: No changes (Python 3.11 base image unchanged)
- docker-compose.yml: No changes (bot service already defined)
- Dependencies: Add httpx to requirements.txt → rebuild image

**Telegram API**:
- New dependency: Bot must maintain persistent connection for receiving commands
- Polling vs Webhook: Use polling (simpler, no public IP needed)
- Rationale: Telegram API is external service (unavoidable coupling)

---

## [DEPLOYMENT ACCEPTANCE]

### Production Invariants

**Must hold true before production deployment**:
1. All authorized user IDs validated (must be 9-10 digit integers)
2. BOT_API_AUTH_TOKEN matches between bot and API services
3. Command handler does not crash bot on Telegram API failures
4. Rate limiting prevents API overload (max 12 req/min per user)
5. Unauthorized access attempts logged (security monitoring)

### Staging Smoke Tests

**Given/When/Then scenarios**:

```gherkin
Scenario: Authorized user queries status
  Given bot is running on staging
    And user 123456789 is in TELEGRAM_AUTHORIZED_USER_IDS
  When user sends /status command via Telegram
  Then bot responds within 3 seconds
    And response contains current bot status (running/paused)
    And response contains position count and P&L
    And no errors logged

Scenario: Unauthorized user attempts command
  Given bot is running on staging
    And user 999999999 is NOT in TELEGRAM_AUTHORIZED_USER_IDS
  When user sends /status command via Telegram
  Then bot responds with "Unauthorized access" message
    And does not reveal bot status
    And logs WARNING level auth failure with user_id

Scenario: Rate limit enforcement
  Given bot is running on staging
    And user sends /status command at T=0
  When user sends /positions command at T=2 seconds
  Then bot responds with rate limit message
    And includes time remaining (3 seconds)
    And does not execute /positions command
    And logs WARNING level rate limit violation

Scenario: API failure handling
  Given bot is running on staging
    And API server is stopped (simulate downtime)
  When user sends /status command via Telegram
  Then bot responds with error message within 3 seconds
    And error message is user-friendly (no stack trace)
    And command handler remains available (does not crash)
    And logs ERROR level with API timeout details

Scenario: Pause/resume commands
  Given bot is running on staging
  When user sends /pause command
  Then bot status changes to "paused"
    And bot stops accepting new signals
    And existing positions remain open
    And /status command shows "paused" mode
  When user sends /resume command
  Then bot status changes to "running"
    And bot resumes signal processing
    And /status command shows "running" mode
```

### Rollback Plan

**Rollback Trigger**: Critical failures
- Command handler crashes bot repeatedly (>3 crashes/hour)
- Unauthorized users gain access (auth bypass vulnerability)
- Rate limiting fails (API overload)

**Rollback Steps**:
1. Set TELEGRAM_ENABLED=false in .env
2. Restart bot: `docker-compose restart bot`
3. Verify: Telegram commands disabled, notifications still work
4. Investigate: Check logs for root cause
5. Fix: Deploy hotfix or revert to previous commit

**Special Considerations**:
- No database rollback needed (stateless feature)
- Feature flag: Can disable without code rollback (TELEGRAM_ENABLED=false)
- Notifications: Telegram notifications (Feature #030) continue working (separate functionality)

### Artifact Strategy

**Build Artifact**: Docker image with httpx dependency
- Build: `docker-compose build bot`
- Tag: `trading-bot:031-telegram-commands-{git-sha}`
- Registry: N/A (local deployment, no registry)

**Deploy to Staging**:
1. Update .env with staging TELEGRAM_AUTHORIZED_USER_IDS
2. Rebuild image: `docker-compose build bot`
3. Restart: `docker-compose up -d bot`
4. Validate: Send /start command from staging Telegram bot

**Promote to Production**:
1. Update .env with production TELEGRAM_AUTHORIZED_USER_IDS
2. Use same image as staging (no rebuild)
3. Restart: `docker-compose up -d bot`
4. Validate: Send /start command from production Telegram bot
5. Monitor: Check logs for 1 hour (watch for auth failures, rate limits, errors)

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios (7 scenarios documented)

**Summary**:
1. Initial setup: Configure env vars, start bot, verify handler initialization
2. Testing all commands: /start, /status, /positions, /performance, /pause, /resume, /help
3. Error handling: Unauthorized user, rate limit, API failure, unknown command
4. Integration testing: Full workflow (10-step command sequence)
5. Load testing: Rate limit stress test, concurrent users
6. Manual testing: Mobile UX, response times, emoji rendering
7. Debugging: Logs, monitoring, troubleshooting

---

## [TESTING STRATEGY]

### Unit Tests (80% coverage target)

**src/trading_bot/telegram/test_command_handler.py**:
- Handler initialization (authorized users parsed from env)
- Command registration (7 commands registered)
- Lifecycle (start, stop, graceful shutdown)
- Error handling (Telegram API errors, unexpected exceptions)

**src/trading_bot/telegram/test_auth_middleware.py**:
- Authorized user passes through
- Unauthorized user rejected with error message
- Logging (auth failure logged with WARNING level)
- Edge cases (empty authorized_users set, invalid user_id format)

**src/trading_bot/telegram/test_rate_limiter.py**:
- First command allowed (no timestamp exists)
- Second command within cooldown rejected
- Second command after cooldown allowed
- Timestamp updated on successful execution
- Multiple users tracked independently

**src/trading_bot/telegram/test_formatters.py**:
- format_status_response() with running/paused/error states
- format_positions_response() with 0, 1, 10 positions
- format_performance_response() with various metrics
- format_help_response() for authorized/unauthorized users
- Emoji rendering (check for correct emoji in output)
- Markdown escaping (special characters handled correctly)

**src/trading_bot/telegram/test_api_client.py**:
- get_summary() success (200 response)
- get_state() success (200 response)
- pause() success (200 response)
- resume() success (200 response)
- Timeout handling (httpx.TimeoutException)
- Auth failure (401 response)
- Server error (500 response)
- Retry logic (single retry on timeout)

### Integration Tests

**tests/integration/test_telegram_commands.py**:
- End-to-end: Send /status command, verify response format
- API integration: Command handler → httpx → FastAPI → StateAggregator
- Auth integration: Authorized user succeeds, unauthorized fails
- Error propagation: API 500 error → user-friendly Telegram message

### Manual Tests (Checklist)

**Mobile UX**:
- [ ] Emoji render correctly on iOS Telegram app
- [ ] Emoji render correctly on Android Telegram app
- [ ] Markdown formatting displays correctly (bold, code blocks)
- [ ] Response fits on screen without horizontal scroll
- [ ] Dark mode readable (if Telegram theme is dark)

**Response Times**:
- [ ] /help responds <500ms
- [ ] /status responds <3s
- [ ] /positions responds <3s
- [ ] /pause responds <2s
- [ ] /resume responds <2s

**Error Scenarios**:
- [ ] Unauthorized user receives rejection message (no status revealed)
- [ ] Rate limit enforced (spam 3 commands, 2nd and 3rd rejected)
- [ ] API timeout handled gracefully (stop API, send command, verify error message)
- [ ] Unknown command shows helpful message with /help suggestion

---

## [RISK MITIGATION]

### Technical Risks

**Risk 1: Control Endpoints Missing in Feature #029**
- Impact: /pause and /resume commands will fail
- Likelihood: High (spec references endpoints not yet implemented)
- Mitigation: Add api/app/routes/commands.py with POST /pause and POST /resume before testing
- Validation: Call endpoints via curl during smoke testing

**Risk 2: Telegram API Rate Limits**
- Impact: Message delivery failures if rate limits exceeded
- Likelihood: Low (5s cooldown = 12 req/min, well below 30 msg/sec Telegram limit)
- Mitigation: Rate limiter enforced before any Telegram API call
- Validation: Load test with 10 users sending commands simultaneously

**Risk 3: API Timeout Under Load**
- Impact: Commands timeout, users get error messages
- Likelihood: Low (micro-scale bot, StateAggregator has 60s cache)
- Mitigation: 2-second timeout + fallback error message, cache reduces backend load
- Validation: Stress test API with 100 concurrent requests, verify command handler degrades gracefully

### Security Risks

**Risk 4: User ID Spoofing**
- Impact: Attacker could impersonate authorized user
- Likelihood: Very Low (user_id provided by Telegram API, not user input)
- Mitigation: Telegram API validates user identity via OAuth, no client-side input
- Validation: N/A (trust Telegram's authentication)

**Risk 5: Brute Force User ID Discovery**
- Impact: Unauthorized user could guess authorized IDs
- Likelihood: Low (user IDs are 9-10 digit integers, 10^9 combinations)
- Mitigation: Log all auth failures for monitoring, add IP-based rate limiting in future
- Validation: Monitor logs for repeated auth failures from same user

---

## [SUCCESS METRICS]

**Feature Success** (from spec.md):
1. Command Availability: All 7 commands functional ✅
2. Response Time: 95% respond <3s ✅
3. Security: 100% unauthorized attempts rejected ✅
4. Rate Limiting: Max 1 command per 5 seconds ✅
5. Error Resilience: API failures don't crash handler ✅
6. Audit Trail: All commands logged ✅
7. Mobile UX: Emoji + markdown render correctly ✅

**Performance Metrics**:
- P50 response time: <1s
- P95 response time: <3s
- P99 response time: <5s
- Error rate: <1% (excluding user errors like rate limits)

**Monitoring** (post-deployment):
- Command execution count per hour (Grafana dashboard)
- Auth failure rate (alerts if >10/hour)
- Rate limit violation rate (alerts if >50/hour)
- API timeout rate (alerts if >5%)

---

## [OPEN QUESTIONS]

None - all technical decisions resolved during planning phase.

**Deferred to Future Iterations**:
- Natural language command parsing (out of scope, spec uses fixed syntax)
- Inline keyboards for interactive menus (out of scope, spec excludes buttons)
- Historical data queries (out of scope, spec is current/recent data only)
- Multi-user permission levels (out of scope, all authorized users equal)
