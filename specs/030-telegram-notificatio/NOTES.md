# Feature: telegram-notifications

## Overview
Telegram notification system for trading bot alerts and updates.

## Research Findings
[Populated during research phase]

## System Components Analysis
[Populated during system component check]

## Feature Classification
- UI screens: false (backend notification system)
- Improvement: false (new feature addition)
- Measurable: true (notification delivery metrics)
- Deployment impact: true (requires Telegram API credentials)

## Checkpoints
- Phase 0 (Spec): 2025-10-27
- Phase 1 (Plan): 2025-10-27

## Last Updated
2025-10-27T14:35:00

## Research Findings

### Finding 1: No existing notification system
Source: Grep search across codebase
- No Telegram integration found
- No centralized notification service
- Performance alerts exist (src/trading_bot/performance/alerts.py) but likely console-only
Decision: Build from scratch, integrate with existing alert systems

### Finding 2: Environment variable pattern established
Source: .env.example
- Clear section-based organization (Robinhood, Trading, Logging, Performance, Features)
- Comment-based documentation with security warnings
- Feature-specific sections (Momentum, Emotional Control, Order Flow, Bot API)
Decision: Add TELEGRAM section following existing pattern

### Finding 3: Deployment environment
Source: .env.example, requirements.txt
- Python-based trading bot (robin-stocks, pandas, numpy)
- Direct production deployment (PAPER_TRADING flag for safety)
- No staging environment mentioned
Decision: Deployment impact = true (requires Telegram Bot Token + Chat ID)

### Finding 4: Existing alert system in performance module
Source: Performance tracking section in .env.example
- PERFORMANCE_ALERT_ROLLING_WINDOW configuration
- PERFORMANCE_SUMMARY_TIMEZONE for time-based alerts
Decision: Integrate Telegram notifications with existing alert triggers

### Finding 5: Multi-feature trading bot with real-time monitoring
Source: Codebase structure and .env.example
- Features: Momentum detection, emotional control, order flow monitoring
- Real-time data streams (Alpaca, Polygon)
- Critical timing for day trading (pre-market 4-9:30 AM EST)
Decision: Notification system must support real-time delivery for time-sensitive alerts

### Finding 6: Recent LLM integration (Feature 029)
Source: .env.example BOT_API section, src/trading_bot/llm/
- FastAPI service for bot state access
- LLM-friendly operations
- OpenAI client integration
Decision: Telegram notifications can enhance observability for LLM-driven workflows

## Overview (Final)
Telegram notification system for real-time trading bot alerts. Provides mobile notifications for position entries/exits, risk circuit breakers, system errors, and performance summaries. Non-blocking design ensures trading operations continue regardless of notification delivery status.

## Key Decisions

1. **Non-blocking Architecture**: Notification failures must not prevent trade execution (FR-001)
   - Rationale: Trading operations take priority over observability
   - Implementation: Async delivery with timeout, catch all exceptions

2. **Environment-based Configuration**: TELEGRAM_ENABLED flag with graceful degradation (FR-006)
   - Rationale: Follows existing pattern from .env.example (PAPER_TRADING, EMOTIONAL_CONTROL_ENABLED)
   - Implementation: Check credentials at startup, log warning if missing, continue trading

3. **Rate Limiting for Errors**: Max 1 notification per error type per hour (NFR-004)
   - Rationale: Prevent notification spam during system instability
   - Implementation: In-memory cache of recent error notifications with timestamp

4. **Markdown Formatting**: Default message format with emoji support (FR-008)
   - Rationale: Rich text improves readability on mobile devices
   - Implementation: Telegram parseMode=Markdown, configurable to HTML or None

5. **MVP Scope**: Position notifications + risk alerts only (US1-US3)
   - Rationale: Core value = real-time trade awareness and risk intervention
   - Deferred: Error notifications (US4), performance summaries (US5), momentum signals (US6), bidirectional commands (US7)

## System Components (Not Applicable)
Backend-only feature with no UI components.

## Artifacts Created
- spec.md: Full feature specification (User Stories, Requirements, Success Criteria)
- design/heart-metrics.md: Measurable outcomes (delivery reliability, adoption, retention)
- checklists/requirements.md: Specification quality validation (16/16 checks passed)
- NOTES.md: Research findings and key decisions

## Specification Quality
- Zero [NEEDS CLARIFICATION] markers (all ambiguities resolved with informed guesses)
- 10 functional requirements + 6 non-functional requirements (all testable)
- 8 success criteria (all measurable and technology-agnostic)
- 7 user stories (P1: US1-US3, P2: US4-US5, P3: US6-US7)

## Next Phase
Ready for /plan - specification is complete, validated, and unambiguous.

## Phase 1 Summary (Planning)

### Metrics
- Research depth: 152 lines (research.md)
- Key decisions: 6 (python-telegram-bot library, async delivery, AlertEvaluator integration, in-memory rate limiting, Markdown formatting, graceful degradation)
- Components to reuse: 7 (AlertEvaluator, TradeRecord, retry.py, circuit_breaker.py, rate_limiter.py pattern, python-dotenv, logging module)
- New components: 5 (telegram_client.py, message_formatter.py, notification_service.py, __init__.py, tests/)
- Migration needed: No (file-based logs, no database schema changes)

### Architecture Highlights
- **Stack**: Python 3.11, python-telegram-bot v20.7 (async), asyncio for non-blocking delivery
- **Pattern**: Fire-and-forget async with 5s timeout (FR-001 non-blocking requirement)
- **Integration**: Extend AlertEvaluator, integrate with CircuitBreaker, reuse TradeRecord logging
- **Security**: Environment-based credentials (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID in .env)
- **Performance**: <10s delivery latency (P95), >99% delivery success rate, <5% CPU usage

### Artifacts Created
- research.md: Project docs integration (8 docs), research decisions, component reuse analysis
- data-model.md: TelegramNotification entity (9 fields), Pydantic message schemas, log format
- plan.md: Comprehensive architecture, stack decisions, implementation phases, risk mitigation
- contracts/telegram-api.yaml: OpenAPI spec for Telegram Bot API sendMessage endpoint
- quickstart.md: 5 integration scenarios (setup, testing, debugging, rollback, production deployment)
- error-log.md: Initialized error tracking template

## Phase 2: Tasks (2025-10-27 00:25)

**Summary**:
- Total tasks: 28
- User story tasks: 11 (US1: 2, US2: 2, US3: 3, Polish: 4, Deployment: 2)
- Parallel opportunities: 20 tasks marked [P]
- Setup tasks: 3
- Task file: specs/030-telegram-notificatio/tasks.md

**Task Breakdown**:
- Phase 1 (Setup): 3 tasks - Module structure, dependencies, environment config
- Phase 2 (Foundational): 3 tasks - TelegramClient, MessageFormatter, NotificationService
- Phase 3 (US1): 2 tasks - Position entry notifications
- Phase 4 (US2): 2 tasks - Position exit notifications with P&L
- Phase 5 (US3): 3 tasks - Risk alert notifications (circuit breaker + performance alerts)
- Phase 6 (Polish): 8 tasks - Error handling, rate limiting, testing (3 test files)
- Documentation: 1 task - NOTES.md update

**Dependency Graph**:
1. Setup tasks (T001-T003) → Foundational (T010-T012) → User stories (T020-T042)
2. Critical path: T010 (TelegramClient) → T020 (US1) → T030 (US2)
3. Parallel paths: US3 (T040-T042) independent of US1/US2

**REUSE Opportunities**:
- 7 existing components: TradeRecord, AlertEvaluator, CircuitBreaker, retry.py, logging, dotenv, Pydantic
- 5 new components: TelegramClient, MessageFormatter, NotificationService, tests/, validate_config.py

**MVP Strategy**: Implement US1-US3 (position entry/exit + risk alerts), validate delivery reliability >99%, then deploy to production. Defer US4-US7 based on usage feedback.

**Checkpoint**:
- ✅ Tasks generated: 28 concrete tasks
- ✅ User story organization: Complete (organized by phase and priority)
- ✅ Dependency graph: Created (setup → foundational → stories → polish)
- ✅ Parallel execution opportunities: 20 tasks marked [P]
- ✅ MVP strategy: Defined (US1-US3 only for first release)
- 📋 Ready for: /analyze

**Testing Strategy**:
- Unit tests: test_message_formatter.py, test_telegram_client.py (T053, T054)
- Integration tests: test_notification_service.py (T055)
- Manual tests: validate_config.py CLI tool (T056), test_telegram_notification.py script (T057)
- Coverage target: >90% (Constitution requirement)

## Phase 4: Implementation (2025-10-27)

### Batch 1: Setup (Completed)
- ✅ T001: Created notifications module structure (src/trading_bot/notifications/__init__.py)
- ✅ T002: Added python-telegram-bot==20.7 to requirements.txt
- ✅ T003: Added TELEGRAM_* environment variables to .env.example (8 config variables)

**Status**: 3/3 tasks complete, ready for Batch 2

### Batch 2: Foundational Infrastructure (Completed)
- ✅ T010: Implemented TelegramClient (async send_message, timeout, error handling, validate_credentials)
- ✅ T011: Implemented MessageFormatter (position entry/exit, risk alerts, emoji, Markdown escaping, truncation)
- ✅ T012: Implemented NotificationService (config validation, orchestration, rate limiting, JSONL logging)

**Key Implementation Details**:
- TelegramClient: 5s timeout, HTTPXRequest async handler, TelegramResponse dataclass for delivery status
- MessageFormatter: 4096 char limit, duration formatting (2h 15m), P&L percentage calculation, escape special chars
- NotificationService: Fire-and-forget pattern with asyncio.create_task(), error_cache dict for rate limiting, graceful degradation

**Status**: 6/6 tasks complete (Batch 1+2), ready for US1 implementation

### Batch 3: US1 Position Entry (Completed)
- ✅ T020: Added position entry notification to bot.py (after trade logging, fire-and-forget async)
- ✅ T021: Created notification log file logs/telegram-notifications.jsonl

**Integration Points**:
- bot.py line 646-654: Send notification after BUY orders with asyncio.create_task()
- bot.py line 261-271: Initialize NotificationService in __init__ with graceful degradation
- Non-blocking: Notification failures never block trade execution (wrapped in try/except)

**Status**: 8/8 tasks complete (Batch 1+2+3), ready for US2 implementation

### Batch 4: US2 Position Exit (Completed)
- ✅ T030: Added position exit notification to bot.py (after SELL orders, fire-and-forget async)
- ✅ T031: Format position exit message with P&L calculation (implemented in MessageFormatter.format_position_exit)

**Integration Points**:
- bot.py line 668-676: Send notification after SELL orders with asyncio.create_task()
- MessageFormatter: P&L percentage calc, duration formatting, profit/loss emoji (✅/❌)

**Status**: 10/10 tasks complete (Batch 1+2+3+4), ready for US3 implementation
