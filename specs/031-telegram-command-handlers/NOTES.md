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

## Last Updated
2025-10-27T21:00:00Z
