# Research & Discovery: telegram-notificatio

## Project Documentation Context

**Source**: `docs/project/` (8 project-level documents)

### Overview (from overview.md)
- **Vision**: Automated momentum trading bot with real-time risk management and observability
- **Target Users**: Solo retail traders running automated day trading strategies
- **Success Metrics**: Win rate >60%, profit factor >1.5, notification reliability >99%
- **Scope Boundaries**: Single-account trading, momentum strategies only, Python-based implementation

### System Architecture (from system-architecture.md)
- **Components**: Modular monolith with domain-based organization (momentum/, risk_management/, performance/, logging/)
- **Integration Points**:
  - `src/trading_bot/performance/alerts.py` - Existing alert evaluation system (AlertEvaluator class)
  - `src/trading_bot/logging/trade_record.py` - Structured trade logging (TradeRecord with 27 fields)
  - `src/trading_bot/error_handling/circuit_breaker.py` - Risk management circuit breakers
- **Data Flows**: Event-driven architecture with non-blocking external API calls
- **Constraints**: Non-blocking design critical - trading operations must continue regardless of notification status

### Tech Stack (from tech-stack.md)
- **Language**: Python 3.11
- **Async Framework**: asyncio for non-blocking operations
- **HTTP Client**: requests library (already in dependencies) or httpx for async
- **Environment Config**: python-dotenv (already used for credentials)
- **Logging**: Python logging module with structured JSON output
- **Current Dependencies**: FastAPI, Pydantic for validation (can reuse for Telegram message schemas)

### Data Architecture (from data-architecture.md)
- **Existing Entities**: TradeRecord (27 fields), AlertEvent, PerformanceSummary
- **Storage Strategy**: File-based JSONL logs (append-only, grep-friendly)
- **Naming Conventions**: snake_case for variables/functions, PascalCase for classes
- **Log Structure**: `logs/` directory with categorized logs (trading_bot.log, trades.jsonl, performance-alerts.jsonl)

### API Strategy (from api-strategy.md)
- **External API Integration**: Pattern established with Robinhood, Alpaca, Polygon.io
- **Auth Pattern**: Environment variables for credentials (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- **Error Handling**: Exponential backoff retry logic in `error_handling/retry.py`
- **Rate Limiting**: Implemented in existing codebase (60 req/min for Robinhood)

### Capacity Planning (from capacity-planning.md)
- **Current Scale**: Micro tier (single account, <100 trades/day)
- **Performance Targets**: Notification latency <10s acceptable (not real-time trading critical path)
- **Resource Limits**: Notification service must use <5% CPU (NFR-003 from spec)
- **Cost Constraints**: Free Telegram Bot API (no additional cost)

### Deployment Strategy (from deployment-strategy.md)
- **Deployment Model**: Docker Compose multi-container (bot + API + Redis)
- **Platform**: Self-hosted VPS (Hetzner)
- **Environments**: Single environment with PAPER_TRADING flag for safety
- **Configuration**: .env file with docker-compose integration

### Development Workflow (from development-workflow.md)
- **Testing Strategy**: pytest with >90% coverage target (Constitution requirement)
- **Code Style**: Type hints required (mypy), ruff for linting
- **Definition of Done**: Tests pass, type checking clean, paper trading validation

---

## Research Decisions

### Decision: Use python-telegram-bot library

- **Decision**: python-telegram-bot v20.7 (async wrapper for Telegram Bot API)
- **Rationale**:
  - Mature async library (20.x is latest major version)
  - Non-blocking design fits project architecture (async/await support)
  - Handles retry logic, rate limiting, message formatting automatically
  - Well-documented with extensive examples
- **Alternatives**:
  - Raw requests library: More control but need to implement retry logic, rate limiting manually
  - aiogram: Good async library but less mature than python-telegram-bot
  - telebot (pyTelegramBotAPI): Synchronous only, would block trading operations
- **Source**: python-telegram-bot documentation, tech-stack.md async requirements

### Decision: Async notification delivery with timeout

- **Decision**: Use asyncio.create_task() for fire-and-forget notifications with 5s timeout
- **Rationale**:
  - Non-blocking requirement (FR-001): Trade execution cannot wait for notification
  - Timeout prevents hanging on Telegram API failures
  - asyncio.create_task() runs notification in background, main thread continues immediately
- **Alternatives**:
  - Synchronous requests: Would block trading (violates FR-001)
  - Threading: More complex than asyncio, doesn't fit existing async architecture
  - Message queue (Celery): Overkill for simple notification delivery
- **Source**: system-architecture.md communication patterns, spec.md FR-001

### Decision: Integrate with existing AlertEvaluator

- **Decision**: Extend AlertEvaluator class to call Telegram notification on alert creation
- **Rationale**:
  - AlertEvaluator already monitors performance thresholds (performance/alerts.py)
  - Centralized alert logic (win rate, risk-reward ratio, circuit breakers)
  - Follows DRY principle (Constitution §Code_Quality)
- **Alternatives**:
  - Create separate notification service: Duplicates alert detection logic
  - Modify bot.py directly: Violates single responsibility principle
  - Event-driven pub/sub: Overkill for single subscriber (Telegram)
- **Source**: performance/alerts.py code review, Constitution §Code_Quality

### Decision: Rate limiting in-memory cache

- **Decision**: Use Python dict with timestamp tracking for error notification rate limiting
- **Rationale**:
  - Simple implementation (NFR-004: max 1 per error type per hour)
  - No persistence needed (rate limit resets on bot restart acceptable)
  - Low memory footprint (track ~10-20 error types max)
- **Alternatives**:
  - Redis cache: Adds dependency, overkill for simple rate limiting
  - Database tracking: Violates file-based logging architecture
  - No rate limiting: Would spam notifications during system instability
- **Source**: spec.md NFR-004, capacity-planning.md micro tier constraints

### Decision: Markdown formatting with emoji

- **Decision**: Use Telegram Markdown (parseMode=Markdown) with emoji for visual cues
- **Rationale**:
  - Markdown supported natively by Telegram Bot API
  - Emoji improves readability on mobile (🚨 for alerts, ✅ for wins, ❌ for losses)
  - Configurable via TELEGRAM_INCLUDE_EMOJIS flag
- **Alternatives**:
  - HTML formatting: More complex, Markdown sufficient for needs
  - Plain text only: Less readable, harder to scan visually
  - Rich media (images): Deferred to future (out of scope for MVP)
- **Source**: spec.md FR-008, assumptions section

### Decision: Graceful degradation pattern

- **Decision**: Check TELEGRAM_ENABLED flag at startup, log warning if missing credentials, continue trading
- **Rationale**:
  - Follows existing pattern (PAPER_TRADING, EMOTIONAL_CONTROL_ENABLED flags in .env)
  - Non-blocking requirement (FR-006): Missing config cannot prevent trading
  - Constitution §Safety_First: Fail safe (trading continues) not fail open (crash)
- **Alternatives**:
  - Raise exception on missing config: Would prevent bot startup (violates FR-006)
  - Silently skip notifications: Harder to debug, no visibility into misconfiguration
  - Require credentials always: Not flexible for users who don't want notifications
- **Source**: .env.example patterns, Constitution §Safety_First, spec.md FR-006

---

## Components to Reuse (7 found)

- **src/trading_bot/performance/alerts.py**: AlertEvaluator class - integrate Telegram notification on alert creation (win rate, risk-reward ratio thresholds)
- **src/trading_bot/logging/trade_record.py**: TradeRecord dataclass - extract position entry/exit details for notifications (ticker, price, P&L)
- **src/trading_bot/error_handling/retry.py**: Exponential backoff retry logic - reuse for Telegram API transient errors
- **src/trading_bot/error_handling/circuit_breaker.py**: Circuit breaker events - trigger urgent Telegram alerts on breach
- **src/trading_bot/llm/rate_limiter.py**: Rate limiting pattern - adapt for error notification rate limiting (max 1 per type per hour)
- **python-dotenv**: Environment variable pattern - add TELEGRAM_* variables to .env (follows existing ROBINHOOD_*, ALPACA_* pattern)
- **Python logging module**: Structured logging - add notification success/failure logs to existing logging infrastructure

---

## New Components Needed (5 required)

- **src/trading_bot/notifications/telegram_client.py**: Telegram Bot API wrapper - async send_message() with timeout, retry, error handling
- **src/trading_bot/notifications/message_formatter.py**: Format trade/alert data into Telegram Markdown messages - emoji, truncation (4096 char limit)
- **src/trading_bot/notifications/notification_service.py**: Notification orchestration - check TELEGRAM_ENABLED, call formatter, send via client, log result
- **src/trading_bot/notifications/__init__.py**: Module initialization - expose public API (NotificationService class)
- **tests/notifications/**: Test suite - unit tests for formatter, integration tests for client (mocked Telegram API)

---

## Unknowns & Questions

None - all technical questions resolved via project documentation and codebase research.

