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
