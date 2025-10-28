# Research & Discovery: telegram-command-handlers

## Project Documentation Context

**Source**: `docs/project/` (8 project-level documents)

### Overview (from overview.md)
- **Vision**: Autonomous trading bot for momentum-based day trading strategies with disciplined risk management
- **Target Users**: Solo retail traders seeking 24/7 automated trading with emotional discipline
- **Success Metrics**: Win rate >60%, profit factor >1.5, max drawdown <5%, uptime >99%
- **Scope Boundaries**: Day trading only (no swing trades), momentum strategies only, Robinhood-specific

### System Architecture (from system-architecture.md)
- **Components**: Trading bot (Python 3.11), FastAPI service (port 8000), Redis cache, file-based logs
- **Integration Points**:
  - Feature #030: TelegramClient (message sending)
  - Feature #029: REST API endpoints (/api/v1/state, /api/v1/summary, /api/v1/health)
- **Data Flows**: Bot state → StateAggregator → API → TelegramCommandHandler → TelegramClient
- **Constraints**: Monolithic architecture (single process), no traditional database

### Tech Stack (from tech-stack.md)
- **Language**: Python 3.11
- **Framework**: FastAPI 0.104.1 (REST API), python-telegram-bot 20.7
- **Cache**: Redis 7.x (LLM response caching)
- **Deployment**: Docker Compose multi-container (bot + API + Redis)

### Data Architecture (from data-architecture.md)
- **Existing Entities**: TradeRecord (logs/trades.jsonl), DashboardSnapshot (memory), PerformanceMetrics (memory)
- **Relationships**: No foreign keys (file-based logging), state managed in-memory
- **Naming Conventions**: snake_case for Python, PascalCase for classes
- **Migration Strategy**: N/A (no database migrations needed)

### API Strategy (from api-strategy.md)
- **API Style**: REST over HTTPS
- **Auth**: Bearer token via X-API-Key header (BOT_API_AUTH_TOKEN)
- **Versioning**: /api/v1/* prefix
- **Error Format**: FastAPI standard (HTTP status codes + detail field)
- **Rate Limiting**: None currently (100 req/min planned in Feature #029)

### Capacity Planning (from capacity-planning.md)
- **Current Scale**: Micro (<10 trades/day, 1-2 positions, <100 API calls/hour)
- **Performance Targets**: API response <500ms P95, Telegram response <3s P95
- **Resource Limits**: Single VPS, 2GB RAM, 1 vCPU
- **Cost Constraints**: <$20/month infrastructure

### Deployment Strategy (from deployment-strategy.md)
- **Deployment Model**: remote-staging-prod (Hetzner VPS)
- **Platform**: Hetzner Cloud (VPS), Docker Compose orchestration
- **CI/CD Pipeline**: Manual deployment (no GitHub Actions currently)
- **Environments**: Local dev, staging (VPS), production (VPS)

### Development Workflow (from development-workflow.md)
- **Git Workflow**: Feature branches → main (GitHub Flow)
- **Testing Strategy**: pytest (unit tests), pytest-asyncio (async tests), manual testing
- **Code Style**: ruff (linting), mypy (type checking)
- **Definition of Done**: Tests pass, type checks pass, no ruff violations, manual verification

---

## Research Decisions

### Decision 1: Use python-telegram-bot Application Framework

**Decision**: Use python-telegram-bot's Application and CommandHandler framework
**Rationale**:
- Built-in command routing and argument parsing
- Error handling middleware support
- Async/await compatible
- Already in requirements.txt (v20.7)
- Reduces boilerplate vs manual if/else routing

**Alternatives**:
- Manual if/else routing: More code, harder to maintain
- aiogram: Different library, would need to add dependency
- telebot: Sync-only, incompatible with async bot

**Source**: python-telegram-bot docs (https://docs.python-telegram-bot.org/en/v20.7/)

---

### Decision 2: Call REST API Endpoints (not direct database access)

**Decision**: Use httpx async client to call localhost:8000/api/v1/* endpoints
**Rationale**:
- Leverage existing StateAggregator service (api/app/services/state_aggregator.py)
- Benefit from existing 60-second cache (reduces redundant state reads)
- Maintain consistency with API contract (single source of truth)
- Avoid duplicating state aggregation logic

**Alternatives**:
- Direct database access: No database exists (file-based logging only)
- Import StateAggregator directly: Tight coupling, breaks service boundaries
- Duplicate state logic: Violates DRY, creates drift risk

**Source**: api/app/routes/state.py (Feature #029)

---

### Decision 3: Store Authorized User IDs in Environment Variables

**Decision**: TELEGRAM_AUTHORIZED_USER_IDS comma-separated in .env
**Rationale**:
- Follows existing config pattern (all config in .env)
- Simple for single-user/small-team use case
- No database needed
- Fast lookup (parse once on startup)

**Alternatives**:
- Database table: Overkill (no database exists, <10 users expected)
- Config file: Redundant with .env pattern
- Hardcode: Violates §Security principle (no credentials in code)

**Source**: .env.example (Feature #030 pattern)

---

### Decision 4: Per-User Global Cooldown (5 seconds)

**Decision**: Single cooldown timer per user ID (blocks all commands for 5 seconds)
**Rationale**:
- Simplest implementation (dict[user_id] = last_command_time)
- Protects both Telegram API (rate limits) and REST API (no spam)
- Adequate for expected use pattern (1-2 commands/minute)

**Alternatives**:
- Per-command cooldown: More complex, not needed for current scale
- Token bucket: Overkill for micro-scale bot
- No rate limiting: Vulnerable to spam, could crash API

**Source**: Spec NFR-004 (Scalability)

---

### Decision 5: Emoji + Markdown Formatting for Mobile UX

**Decision**: Use Telegram MarkdownV2 parse mode + emoji for visual hierarchy
**Rationale**:
- Mobile-first design (users access from phone)
- Emoji provides instant visual cues (🟢 = good, 🔴 = bad)
- Markdown improves readability without clutter
- Spec requirement (FR-011: Response Formatting)

**Alternatives**:
- Plain text: Harder to scan on mobile
- HTML: More verbose, MarkdownV2 is simpler
- Inline keyboards: Out of scope (spec excludes interactive buttons)

**Source**: Spec FR-011 (Response Formatting)

---

### Decision 6: Async Command Handlers (non-blocking)

**Decision**: All command handlers are async functions with await
**Rationale**:
- Matches existing TelegramClient pattern (async send_message)
- Prevents blocking main bot loop during API calls
- python-telegram-bot v20.7 is async-first
- Spec requirement (FR-015: Async Command Execution)

**Alternatives**:
- Sync handlers: Would block bot, incompatible with TelegramClient
- Threading: More complex, async is Python standard for I/O
- Celery tasks: Overkill for micro-scale bot

**Source**: src/trading_bot/notifications/telegram_client.py (Feature #030)

---

## Components to Reuse (7 found)

### From Feature #030 (Telegram Notifications)
- **TelegramClient.send_message()**: src/trading_bot/notifications/telegram_client.py:78-189
  - Async message sending with timeout (5s default)
  - Retry logic with exponential backoff
  - Error handling (TelegramError, asyncio.TimeoutError)
  - Usage: `await client.send_message(chat_id, text, parse_mode="Markdown")`

- **TelegramClient.validate_credentials()**: src/trading_bot/notifications/telegram_client.py:191-223
  - Bot token validation via getMe API
  - Usage: `response = await client.validate_credentials()`

- **python-telegram-bot library**: requirements.txt:59
  - Version 20.7 already installed
  - No new dependencies needed

### From Feature #029 (REST API)
- **GET /api/v1/state**: api/app/routes/state.py:28-66
  - Complete bot state (positions, account, health, performance)
  - 60-second cache (configurable via BOT_STATE_CACHE_TTL)
  - Response model: BotStateResponse
  - Auth: X-API-Key header (BOT_API_AUTH_TOKEN)

- **GET /api/v1/summary**: api/app/routes/state.py:68-101
  - Compressed state summary (<10KB, <2500 tokens)
  - Ideal for status command (less data to parse)
  - Response model: BotSummaryResponse

- **GET /api/v1/health**: api/app/routes/state.py:104-134
  - Health status (circuit breaker, API connectivity, error count)
  - Response model: HealthStatus

- **StateAggregator service**: api/app/services/state_aggregator.py
  - Aggregates state from dashboard, performance tracker, health monitor
  - 60-second cache with configurable TTL
  - Methods: get_bot_state(), get_health_status(), get_summary()

### Environment Configuration Pattern
- **TELEGRAM_BOT_TOKEN**: .env.example:100
  - Already exists from Feature #030
- **TELEGRAM_CHAT_ID**: .env.example:101
  - Already exists from Feature #030
- **TELEGRAM_ENABLED**: .env.example:99
  - Graceful degradation flag
- **BOT_API_AUTH_TOKEN**: .env.example:91
  - API key for REST API calls
- **BOT_API_PORT**: .env.example:90
  - Default 8000

---

## New Components Needed (5 required)

### Backend Components

1. **TelegramCommandHandler class**: src/trading_bot/telegram/command_handler.py (new file)
   - Manages python-telegram-bot Application instance
   - Registers command handlers (/start, /status, /pause, /resume, /positions, /performance, /help)
   - Integrates with TelegramClient for message sending
   - Middleware: authentication, rate limiting, error handling
   - Lifecycle: start(), stop(), graceful shutdown

2. **CommandAuthMiddleware**: src/trading_bot/telegram/command_handler.py (inline)
   - Extracts Telegram user ID from update.effective_user.id
   - Compares against TELEGRAM_AUTHORIZED_USER_IDS (parsed on startup)
   - Rejects unauthorized users with error message + log warning
   - Returns early (no command execution)

3. **CommandRateLimiter**: src/trading_bot/telegram/command_handler.py (inline)
   - Dict[user_id, last_command_timestamp]
   - Checks if (now - last_command_time) < TELEGRAM_COMMAND_COOLDOWN_SECONDS
   - Rejects if within cooldown, sends time-remaining message
   - Updates timestamp on successful command

4. **ResponseFormatter**: src/trading_bot/telegram/formatters.py (new file)
   - format_status_response(state: BotSummaryResponse) -> str
   - format_positions_response(positions: List[PositionResponse]) -> str
   - format_performance_response(metrics: PerformanceMetricsResponse) -> str
   - format_help_response(is_authorized: bool) -> str
   - Emoji mapping: 🟢 running, ⏸️ paused, 🔴 error, 📊 metrics, 💰 money, ✅ success, ❌ error

5. **Internal API Client**: src/trading_bot/telegram/api_client.py (new file)
   - httpx.AsyncClient wrapper for calling localhost:8000/api/v1/*
   - Methods: get_state(), get_summary(), get_health(), pause(), resume()
   - Includes X-API-Key header from BOT_API_AUTH_TOKEN
   - Timeout: 2 seconds (spec NFR-001: API call timeout)
   - Error handling: timeout, 401 Unauthorized, 500 Internal Server Error

### Integration Points
- TelegramClient.send_message() for sending responses
- StateAggregator (via REST API) for state data
- Environment variables for config (TELEGRAM_AUTHORIZED_USER_IDS, TELEGRAM_COMMAND_COOLDOWN_SECONDS)
- Logging infrastructure (existing logger)

---

## Unknowns & Questions

None - all technical questions resolved during research phase.

---

## Command to API Endpoint Mapping

| Command | HTTP Method | Endpoint | Data Source | Expected Latency |
|---------|-------------|----------|-------------|------------------|
| /start | None | N/A | Static text | <10ms |
| /help | None | N/A | Static text | <10ms |
| /status | GET | /api/v1/summary | StateAggregator cache | <200ms |
| /positions | GET | /api/v1/state | StateAggregator cache | <300ms |
| /performance | GET | /api/v1/state | StateAggregator cache | <300ms |
| /pause | POST | /api/v1/commands/pause | Bot state mutation | <100ms |
| /resume | POST | /api/v1/commands/resume | Bot state mutation | <100ms |

**Note**: Pause/resume endpoints need verification in Feature #029 API. If missing, will need to be added to api/app/routes/commands.py (new file).

---

## Risk Assessment

### Technical Risks

**Risk 1: Control Endpoints Missing**
- **Impact**: Pause/resume commands won't work
- **Likelihood**: High (spec references endpoints not yet implemented)
- **Mitigation**: Create api/app/routes/commands.py with POST /pause and POST /resume
- **Validation**: Verify during task breakdown phase

**Risk 2: Telegram API Rate Limits**
- **Impact**: Message delivery failures during rapid command spam
- **Likelihood**: Low (5-second cooldown prevents most spam)
- **Mitigation**: Rate limiter + exponential backoff in TelegramClient
- **Validation**: Load test with 10 commands in 10 seconds

**Risk 3: API Timeout During High Load**
- **Impact**: Commands timeout, user gets no response
- **Likelihood**: Low (micro-scale bot, <10 trades/day)
- **Mitigation**: 2-second timeout + fallback error message
- **Validation**: Stress test API with 100 concurrent requests

### Security Risks

**Risk 4: User ID Discovery**
- **Impact**: Unauthorized users could attempt to guess authorized IDs
- **Likelihood**: Low (user IDs are 9-10 digit integers, brute force impractical)
- **Mitigation**: Log all unauthorized attempts, add IP-based rate limiting in future
- **Validation**: Monitor logs for repeated auth failures

---

## Performance Budget

Based on spec NFR-001 (Response Time):

| Command | Target P95 | Budget Breakdown |
|---------|------------|------------------|
| /help | <500ms | 10ms static + 100ms Telegram API |
| /start | <500ms | 10ms static + 100ms Telegram API |
| /status | <3s | 200ms API + 50ms formatting + 100ms Telegram API + 2.65s buffer |
| /positions | <3s | 300ms API + 100ms formatting + 100ms Telegram API + 2.5s buffer |
| /performance | <3s | 300ms API + 100ms formatting + 100ms Telegram API + 2.5s buffer |
| /pause | <2s | 100ms API + 50ms formatting + 100ms Telegram API + 1.75s buffer |
| /resume | <2s | 100ms API + 50ms formatting + 100ms Telegram API + 1.75s buffer |

**Buffer allocation**: Accounts for network latency, Telegram API variability, and cold-start delays

---

## Caching Strategy

**Client-side caching**: None
- Rationale: Users expect real-time data when querying status
- All commands fetch fresh data from API

**Server-side caching**: Leverage existing 60-second cache in StateAggregator
- /status → GET /api/v1/summary (cached)
- /positions → GET /api/v1/state (cached)
- /performance → GET /api/v1/state (cached)

**Cache invalidation**: Automatic TTL-based (60 seconds)
- No manual invalidation needed
- Acceptable staleness for status queries

---

## Testing Strategy

### Unit Tests
- CommandAuthMiddleware: authorized/unauthorized users
- CommandRateLimiter: cooldown enforcement, timer reset
- ResponseFormatter: all command response formats
- InternalAPIClient: API call success/failure, timeout, auth errors

### Integration Tests
- TelegramCommandHandler + TelegramClient: end-to-end message flow
- TelegramCommandHandler + REST API: data retrieval and formatting
- Authentication flow: authorized user gets response, unauthorized gets rejection

### Manual Tests
- Send commands from authorized Telegram user
- Send commands from unauthorized user
- Spam commands to trigger rate limit
- Verify emoji and markdown rendering on mobile
- Test during API downtime (error handling)

---

## Deployment Checklist

### Pre-deployment
- Add TELEGRAM_AUTHORIZED_USER_IDS to .env (staging and production)
- Add TELEGRAM_COMMAND_COOLDOWN_SECONDS to .env (default: 5)
- Verify BOT_API_AUTH_TOKEN exists in .env
- Document how to find Telegram user ID in README

### Post-deployment
- Send /start command from authorized user (verify response)
- Send /status command (verify data accuracy)
- Send command from unauthorized user (verify rejection + log)
- Spam 3 commands rapidly (verify rate limit kicks in)
- Check logs for command execution audit trail

### Rollback Plan
- Feature is additive only (no breaking changes)
- Disable via TELEGRAM_ENABLED=false
- No database rollback needed (stateless feature)
