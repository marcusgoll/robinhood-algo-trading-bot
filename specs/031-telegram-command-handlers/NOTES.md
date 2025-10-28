# Feature: Telegram Command Handlers for Bot Control and Reporting

## Overview
Interactive command handlers for the Telegram bot to enable remote control and monitoring of the trading bot via Telegram messages. Builds on existing Telegram notification infrastructure (Feature #030) and REST API endpoints (Feature #029).

## Research Findings

### Existing Infrastructure Analysis

**Feature #030 - Telegram Notifications** (D:\Coding\Stocks\src\trading_bot\notifications\telegram_client.py):
- TelegramClient class with async message sending
- python-telegram-bot library v20.7 already in requirements.txt
- Timeout handling (5s default), retry logic, error handling
- Non-blocking delivery mechanism established
- Bot token and chat ID from environment variables

**Feature #029 - LLM-Friendly Bot Operations** (D:\Coding\Stocks\api\app\routes\state.py):
- REST API endpoints available:
  - GET /api/v1/state - Complete bot state
  - GET /api/v1/summary - Compressed summary
  - GET /api/v1/health - Health status
- Auth via X-API-Key header
- StateAggregator service for state retrieval
- FastAPI running on port 8000 (BOT_API_PORT)

**Environment Configuration** (.env.example):
- TELEGRAM_BOT_TOKEN - Already exists
- TELEGRAM_CHAT_ID - Already exists
- TELEGRAM_ENABLED - Already exists
- BOT_API_AUTH_TOKEN - Already exists for API access

### Technical Decisions

1. **Architecture Pattern**: Extend TelegramClient class vs. Create new CommandHandler
   - Decision: Create new TelegramCommandHandler class
   - Rationale: Separation of concerns - TelegramClient handles message sending, CommandHandler handles command processing and routing

2. **API Integration**: Direct database access vs. REST API calls
   - Decision: Use REST API endpoints via internal HTTP client
   - Rationale: Leverage existing API abstraction, maintain consistency, benefit from caching and validation logic

3. **Authentication**: Store user IDs in .env vs. database
   - Decision: Store in .env (TELEGRAM_AUTHORIZED_USER_IDS comma-separated)
   - Rationale: Simple deployment, aligns with existing config pattern, adequate for single-user/small team use

4. **Rate Limiting**: Per-command vs. global cooldown
   - Decision: Per-user global cooldown (5 seconds between any commands)
   - Rationale: Prevents spam, simpler implementation, protects both Telegram and REST API

5. **Command Framework**: Manual if/else vs. python-telegram-bot command handlers
   - Decision: Use python-telegram-bot Application framework with CommandHandler
   - Rationale: Built-in command routing, argument parsing, error handling, better maintainability

## System Components Analysis

**Reusable Components**:
- TelegramClient (message sending)
- StateAggregator (bot state retrieval)
- REST API endpoints (all operations)
- Environment configuration patterns

**New Components Needed**:
- TelegramCommandHandler (command routing and execution)
- CommandAuthMiddleware (user ID validation)
- CommandRateLimiter (cooldown tracking)
- ResponseFormatter (emoji + markdown formatting)

**Integration Points**:
- TelegramClient.send_message() for responses
- Internal HTTP client to call localhost:8000/api/v1/*
- Environment variables for config
- Logging infrastructure

## Feature Classification
- UI screens: false
- Improvement: false
- Measurable: true (command execution metrics)
- Deployment impact: true (new environment variables)

## Deployment Considerations

**Environment Variables** (new):
- TELEGRAM_AUTHORIZED_USER_IDS - Comma-separated list of authorized Telegram user IDs
- TELEGRAM_COMMAND_COOLDOWN_SECONDS - Rate limit cooldown (default: 5)

**Breaking Changes**:
- None - additive feature only

**Migration Required**:
- No database changes needed

**Security**:
- User ID authentication before command execution
- Log all command executions with user ID and timestamp
- Rate limiting to prevent abuse

## Key Decisions
1. Extend existing TelegramClient with new CommandHandler class for separation of concerns
2. Call REST API endpoints internally rather than direct database access for consistency
3. Store authorized user IDs in environment variables (TELEGRAM_AUTHORIZED_USER_IDS)
4. Implement per-user global cooldown (5 seconds) to prevent spam
5. Use python-telegram-bot Application framework for command routing and handling
6. Format responses with emoji and markdown for enhanced mobile UX
7. All commands are async and non-blocking (matches existing notification pattern)

## Checkpoints
- Phase 0 (Specification): 2025-10-27
- Phase 1 (Planning): 2025-10-27
  - Artifacts: research.md, data-model.md, quickstart.md, plan.md, contracts/api.yaml, error-log.md
  - Research decisions: 6 (documented in research.md)
  - Components to reuse: 7 (TelegramClient, StateAggregator, REST API endpoints)
  - New components: 5 (TelegramCommandHandler, auth/rate limiting middleware, formatters, API client)
  - Missing dependency: Control endpoints (POST /pause, POST /resume) need to be added to Feature #029 API

## Phase Summaries

### Phase 1 (Planning) - 2025-10-27
- Research depth: Comprehensive (read 8 project docs + existing code)
- Key decisions: 6 architectural decisions documented
- Components to reuse: 7 (TelegramClient, python-telegram-bot v20.7, REST API endpoints, StateAggregator, env config patterns)
- New components: 5 (TelegramCommandHandler, CommandAuthMiddleware, CommandRateLimiter, ResponseFormatter, InternalAPIClient)
- Migration needed: No (stateless feature, no database changes)
- Blockers identified: Control endpoints missing from Feature #029 API (will add in tasks phase)

## Phase 2: Tasks (2025-10-27)

**Summary**:
- Total tasks: 36
- Setup tasks: 3 (Phase 1)
- Foundational tasks: 6 (Phase 2 - control endpoints and API client)
- Infrastructure tasks: 7 (Phase 3 - handler framework)
- Command implementation tasks: 14 (Phase 4 - 7 command handlers + tests)
- Polish tasks: 6 (Phase 5 - deployment, docs, validation)
- Parallel opportunities: 20 tasks marked [P]
- Test tasks: 8 (unit tests, integration tests, E2E tests)
- Task file: specs/031-telegram-command-handlers/tasks.md

**Checkpoint**:
- ✅ Tasks generated: 36
- ✅ Dependency graph: 5 phases (setup → foundational → infrastructure → commands → polish)
- ✅ Parallel execution plan: 20 tasks can run in parallel across phases
- ✅ MVP strategy: Phase 4 Group 1 (read-only commands T017-T023) → Phase 4 Group 2 (control commands T024-T026)
- ✅ Test coverage targets: Unit 80%, Integration 60%, E2E 90%
- ✅ Reuse analysis: 9 existing components identified
- ✅ Critical path: T004-T009 (control endpoints) block T024-T025 (pause/resume commands)
- 📋 Ready for: /analyze

**Task Breakdown by Category**:
- Backend API tasks: 4 (T004-T007: control endpoints and schemas)
- Backend command handler tasks: 18 (T008-T016, T017-T030: API client, handlers, middleware)
- Test tasks: 8 (T009, T011, T014, T016, T023, T026, T030, T031)
- Deployment tasks: 6 (T031-T036: smoke tests, docs, integration, validation)

**Key Decisions**:
1. Dependency order: Control endpoints (T004-T007) must complete before pause/resume commands (T024-T025)
2. Parallel groups: Read-only commands (T017-T023) can be implemented in parallel
3. Test strategy: Unit tests (80% coverage) accompany each component, integration tests cover command flow, E2E test covers complete workflow
4. MVP scope: Read-only commands first (faster delivery, lower risk), control commands second
5. Blocker resolution: T004-T007 add missing control endpoints identified in planning phase

## Phase 4: Implementation (2025-10-27)

### Batch 1: Setup (T001-T003) - COMPLETED
- ✅ T001: Added httpx==0.25.0 to requirements.txt
- ✅ T002: Added TELEGRAM_AUTHORIZED_USER_IDS and TELEGRAM_COMMAND_COOLDOWN_SECONDS to .env.example
- ✅ T003: Created src/trading_bot/telegram/ module structure with __init__.py

**Key Decisions**:
- httpx 0.25.0 selected for async HTTP client (compatible with Python 3.11)
- Environment variables follow existing TELEGRAM_* naming pattern
- Module structure mirrors existing notifications/ module pattern

## Last Updated
2025-10-27T22:45:00Z
