# Feature: LLM-Friendly Bot Operations and Monitoring

## Overview

This feature transforms the trading bot from a "black box" into an observable, controllable system that LLMs can effectively operate. By implementing structured interfaces, comprehensive observability, and semantic APIs, we enable LLMs to understand bot state, monitor performance, diagnose issues, execute maintenance tasks, and assist with configuration changes.

The implementation builds on existing infrastructure (dashboard, logging, performance tracking) and adds an API layer optimized for LLM consumption.

## Research Findings

- Finding 1: Existing dashboard at src/trading_bot/dashboard/ provides CLI visualization
  Source: Glob src/trading_bot/dashboard/
  Files: dashboard.py, metrics_calculator.py, models.py
  Decision: Build LLM API layer on top of existing data models

- Finding 2: Structured logging already exists at src/trading_bot/logging/
  Source: Glob src/trading_bot/logging/
  Files: structured_logger.py, trade_record.py, query_helper.py
  Decision: Extend with semantic context and explanations for LLM consumption

- Finding 3: Performance tracking module at src/trading_bot/performance/
  Source: Glob src/trading_bot/performance/
  Files: tracker.py, models.py, cli.py, alerts.py
  Decision: Expose via JSON API with LLM-optimized summaries

- Finding 4: Similar feature exists: specs/019-status-dashboard/spec.md
  Source: Existing spec review
  Pattern: CLI dashboard with metrics refresh, export capabilities
  Decision: Extend with API endpoints and natural language interface

- Finding 5: Bot architecture has health monitoring at src/trading_bot/health/
  Source: Directory structure scan
  Implication: Health checks already implemented, need API exposure

- Finding 6: Error handling infrastructure exists at src/trading_bot/error_handling/
  Source: Glob src/trading_bot/error_handling/
  Files: exceptions.py, circuit_breaker.py, retry.py, policies.py
  Decision: Extend exceptions with semantic error messages (cause, impact, remediation)

## System Components Analysis

**Reusable (from existing codebase)**:
- Dashboard data models (src/trading_bot/dashboard/models.py)
- Structured logger (src/trading_bot/logging/structured_logger.py)
- Performance tracker (src/trading_bot/performance/tracker.py)
- Health monitor (src/trading_bot/health/)
- Error handling (src/trading_bot/error_handling/)

**New Components Needed**:
- FastAPI REST API service (separate process)
- State aggregator (combines dashboard, performance, health into single response)
- Semantic error formatter (extends existing exceptions with LLM fields)
- Natural language command parser (intent extraction and routing)
- Configuration validator (JSON schema validation)
- Workflow executor (YAML-based workflow engine)
- OpenAPI spec generator (auto-documentation)

**Rationale**: Leverage existing observability infrastructure and add API layer for LLM access. Separate API service ensures bot core remains unaffected by API queries.

## Feature Classification

- UI screens: true (API documentation, config editor, error inspector - primarily for developers)
- Improvement: true (improving bot observability and operability)
- Measurable: false (operational metrics, not user behavior metrics)
- Deployment impact: true (new API service, environment variables, auth tokens)

## Key Decisions

1. **API Architecture**: Separate FastAPI service running alongside bot (not embedded) to ensure bot trading logic remains isolated and performant

2. **Authentication Model**: Token-based auth initially (OAuth2 deferred); sufficient for single-operator scenarios and LLM access patterns

3. **State Caching**: 60-second TTL on cached state to balance freshness vs performance; stale indicators shown when cache used

4. **Error Format**: Standardized semantic error structure (error_code, type, message, cause, impact, remediation, context) across all APIs and logs

5. **Context Window Optimization**: Summary endpoint <10KB (<2500 tokens) by prioritizing critical state and limiting recent errors to 3

6. **Workflow Scope**: Linear workflows only in MVP (sequential steps); parallel execution and conditionals deferred to future

7. **Natural Language Scope**: Limited to status/performance queries initially; complex commands (trade execution) explicitly out of scope for safety

8. **Documentation Strategy**: Auto-generate OpenAPI spec from code to prevent drift; CI validation planned

## Checkpoints

- Phase 0 (Spec): 2025-10-24
- Requirements checklist: Complete (16/16)
- Research phase: Complete
- Classification: Complete
- Validation: Complete
- Phase 1 (Plan): 2025-10-24
  - Research decisions: 8
  - Components to reuse: 9
  - New components: 11
  - Migration required: No

## Phase Summaries

### Phase 1: Planning
- Research depth: 1847 lines
- Key decisions: 8 (FastAPI architecture, data model reuse, semantic logging extension)
- Components to reuse: 9 (dashboard models, structured logging, performance tracking, error handling, FastAPI infrastructure)
- New components: 11 (API routes, services, schemas, WebSocket manager, middleware)
- Migration needed: No (file-based storage for workflows and config history)
- Artifacts: research.md, data-model.md, quickstart.md, plan.md, contracts/api.yaml, error-log.md

## Artifacts Created

- specs/029-llm-friendly-bot-operations/spec.md (full specification)
- specs/029-llm-friendly-bot-operations/design/screens.yaml (6 screens)
- specs/029-llm-friendly-bot-operations/design/copy.md (UI copy + API examples)
- specs/029-llm-friendly-bot-operations/checklists/requirements.md (quality validation)
- specs/029-llm-friendly-bot-operations/research.md (8 decisions, component reuse analysis)
- specs/029-llm-friendly-bot-operations/data-model.md (6 entities, Mermaid ERD)
- specs/029-llm-friendly-bot-operations/quickstart.md (6 integration scenarios)
- specs/029-llm-friendly-bot-operations/plan.md (consolidated architecture)
- specs/029-llm-friendly-bot-operations/contracts/api.yaml (OpenAPI 3.0 spec)
- specs/029-llm-friendly-bot-operations/error-log.md (initialized tracking)
- specs/029-llm-friendly-bot-operations/NOTES.md (this file)

## Last Updated

2025-10-24T21:45:00

## Phase 4: Implementation (2025-10-24)

**Batch 1: Setup** (Complete)
- T001: Install FastAPI dependencies in requirements.txt
- T002: Create directory structure for new modules
- T003: Add new environment variables to .env.example

**Batch 2: Foundational** (Complete)
- T005: Create SemanticError dataclass in src/trading_bot/logging/semantic_error.py
- T006: Create error formatter in src/trading_bot/logging/error_formatter.py
- T007: Extend API key auth in api/app/core/auth.py (verify_api_key function)

**Batch 3: US1 State API** (Complete)
- T010: Create BotStateResponse schema in api/app/schemas/state.py
- T011: Create state aggregator service in api/app/services/state_aggregator.py
- T012: Create state routes in api/app/routes/state.py (GET /state, /summary, /health)
- T013: Register state routes in api/app/main.py

**Batch 4: US2 Semantic Logging** (Complete)
- T020: Extend structured logger with log_semantic_error method
- T021: Create semantic error handler middleware in api/app/middleware/semantic_error_handler.py

**Batch 5: OpenAPI Metadata** (Complete - Commit ecb7106)
- T030: Add OpenAPI tags and enhanced description
- T031: Schema examples (already present in all models)
- T033: OpenAPI smoke tests (6 tests, all passing <1s)

**Batch 6: US4 Summary Endpoint** (Complete)
- T040: BotSummaryResponse schema created (already in state.py)
- T041: GET /summary endpoint implemented (already in state.py routes)
- T043: Unit test for summary size validation (<10KB) - 8 tests, all passing
- Fixes: Field name typo (positions_count → position_count), added missing data_age_seconds and warnings fields

**Implementation Progress Summary**:
- Completed: 19 tasks across 6 batches (MVP core + OpenAPI docs + Summary endpoint)
- Remaining: 28 tasks across 6 batches (critical tests, enhancements, polish)
- Files created: 8 new files (schemas, services, routes, middleware, logging, unit tests)
- Files modified: 7 files (requirements.txt, .env.example, auth.py, main.py, structured_logger.py, state.py, state_aggregator.py)
- Commits: 5 (batches 1-2, batch 3, batch 4, batch 5, batch 6)

## Phase 2: Tasks (2025-10-24)

**Summary**:
- Total tasks: 47
- User story tasks: 41 (organized by priority P1, P2, P3)
- Parallel opportunities: 29 tasks marked [P]
- Setup tasks: 3
- Foundational tasks: 3
- MVP tasks (US1-US4): 18
- Enhancement tasks (US5-US8): 20
- Polish tasks: 9
- Task file: specs/029-llm-friendly-bot-operations/tasks.md

**Task Breakdown by Story**:
- US1 (State API): 7 tasks
- US2 (Semantic Logging): 6 tasks
- US3 (OpenAPI Docs): 4 tasks
- US4 (Summary <10KB): 4 tasks
- US5 (NL Commands): 4 tasks
- US6 (Config Management): 6 tasks
- US7 (Workflows): 6 tasks
- US8 (Observability/WebSocket): 5 tasks
- US10 (Testing): 3 tasks

**Checkpoint**:
- ✅ Tasks generated: 47
- ✅ User story organization: Complete (organized by dependency graph)
- ✅ Dependency graph: Created (11 phases with clear progression)
- ✅ MVP strategy: Defined (Phases 1-6: US1-US4 only)
- ✅ Parallel execution: 29 tasks identified [P]
- ✅ REUSE analysis: 13 existing modules identified
- 📋 Ready for: /analyze

**Implementation Strategy**:
- MVP Scope: Phases 1-6 (Setup → Foundational → US1-US4)
- Incremental delivery: MVP → staging validation → Enhancements (US5-US8) → Final testing
- Testing approach: Unit tests for services, integration tests for routes, smoke tests for critical paths
- Coverage targets: 100% new code, ≥80% unit, ≥60% integration, ≥90% critical path

