# Feature Specification: LLM-Friendly Bot Operations and Monitoring

**Branch**: `feature/029-llm-friendly-bot-operations`
**Created**: 2025-10-24
**Status**: Draft
**Area**: api, infra
**From Roadmap**: No (GitHub Issue #34)
**Priority**: medium
**ICE Score**: 1.00 (Impact: 5, Confidence: 0.8, Effort: 4)
**Size**: large (2-4 weeks)

## User Scenarios

### Primary User Story
As an LLM assistant helping to operate the trading bot, I need structured interfaces, semantic APIs, and comprehensive observability so that I can understand current bot state, monitor performance, diagnose issues, execute maintenance tasks, and assist with configuration changes without requiring deep technical expertise or manual log investigation.

### Acceptance Scenarios

1. **Given** the bot is running, **When** an LLM queries the state API endpoint, **Then** it receives a JSON response (<10KB) containing current positions, orders, P&L, configuration summary, and health metrics with human-readable explanations

2. **Given** an error occurs in the bot, **When** the error is logged, **Then** the log entry includes semantic fields (error_type, cause, impact, recommended_action) that an LLM can parse and act upon without code inspection

3. **Given** an operator asks "show today's performance", **When** the natural language CLI processes the command, **Then** it extracts intent, queries appropriate APIs, and returns formatted performance metrics with context

4. **Given** the bot has API endpoints, **When** an LLM accesses the OpenAPI documentation, **Then** it finds complete endpoint descriptions, request/response examples, error codes, and usage scenarios sufficient to make API calls without trial-and-error

5. **Given** the observability dashboard is running, **When** an LLM queries the summary endpoint, **Then** it receives real-time metrics (health status, active positions, recent trades, circuit breaker state) optimized for LLM context windows

6. **Given** a configuration change is needed, **When** an LLM submits a config update via the management API, **Then** the system validates the change against schema, shows a diff, applies the change safely, and provides rollback capability if validation fails

7. **Given** common maintenance tasks are documented, **When** an LLM executes a workflow (e.g., "restart bot safely"), **Then** the system tracks workflow progress, validates each step, and reports completion status with any issues encountered

### Edge Cases

- What happens when the bot is not running?
  - State API returns cached last-known state with staleness timestamp, health status shows "offline"
- What happens when logs are missing or corrupted?
  - Error explainability falls back to generic error messages, logs warning about missing semantic context
- What happens when natural language command is ambiguous?
  - CLI returns clarifying questions with multiple interpretation options
- What happens when API rate limits are hit?
  - Semantic error response explains rate limit, provides retry-after time, suggests alternative endpoints
- What happens when configuration validation fails?
  - API returns detailed validation errors with field-level explanations and valid value examples
- What happens during maintenance windows?
  - System status indicates maintenance mode, provides estimated completion time, queues non-urgent requests

## User Stories (Prioritized)

### Story Prioritization

**Priority 1 (MVP) 🎯**

- **US1** [P1]: As an LLM, I want to query current bot state via JSON API so that I can understand positions, orders, and account status without log parsing
  - **Acceptance**: GET /api/v1/state returns JSON with positions (symbol, qty, entry, current, pnl), orders (id, symbol, side, status), account (buying_power, balance), health (status, last_update)
  - **Independent test**: Start bot → curl /api/v1/state → verify complete state in <10KB response
  - **Effort**: M (4-8 hours)

- **US2** [P1]: As an LLM, I want semantic error logging so that I can diagnose issues from structured error context
  - **Acceptance**: All exceptions logged with JSONL format including: timestamp, error_type, message, cause, impact, recommended_action, context (trade_id, symbol, etc.)
  - **Independent test**: Trigger error → parse log entry → verify all semantic fields present
  - **Effort**: M (4-8 hours)

- **US3** [P1]: As an LLM, I want OpenAPI documentation for all endpoints so that I can discover and use APIs without guessing
  - **Acceptance**: /api/docs serves interactive Swagger UI with all endpoints, request/response schemas, examples, error codes
  - **Independent test**: Load /api/docs → verify coverage of all implemented endpoints with examples
  - **Effort**: S (2-4 hours)

- **US4** [P1]: As an LLM, I want a compressed state summary endpoint so that I can fit bot context into limited token windows
  - **Acceptance**: GET /api/v1/summary returns <10KB JSON with essential state: health (status), positions_count, open_orders_count, daily_pnl, recent_errors (last 3), circuit_breaker_status
  - **Independent test**: Query summary → verify response <10KB → validate contains critical state
  - **Effort**: S (2-4 hours)

**Priority 2 (Enhancement)**

- **US5** [P2]: As an LLM, I want natural language command processing so that I can execute queries using operator's phrasing
  - **Acceptance**: CLI accepts commands like "show today's performance", "what positions are open", "check bot health" and routes to appropriate API endpoints
  - **Independent test**: Input NL command → verify intent extraction → verify correct API called → verify formatted response
  - **Depends on**: US1
  - **Effort**: L (8-16 hours)

- **US6** [P2]: As an LLM, I want configuration management API with validation so that I can safely update bot parameters
  - **Acceptance**: POST /api/v1/config with schema validation, GET /api/v1/config/diff shows changes, PUT /api/v1/config/rollback reverts to previous
  - **Independent test**: Submit config → verify validation → apply change → verify active → rollback → verify reverted
  - **Depends on**: US1, US3
  - **Effort**: L (8-16 hours)

- **US7** [P2]: As an LLM, I want documented maintenance workflows so that I can execute common tasks step-by-step
  - **Acceptance**: Workflow definitions in YAML (restart-bot, update-targets, export-logs) with execution tracking via POST /api/v1/workflows/{id}/execute
  - **Independent test**: Load workflow → execute steps → verify progress tracking → verify completion
  - **Depends on**: US1, US6
  - **Effort**: M (4-8 hours)

- **US8** [P2]: As an LLM, I want real-time observability dashboard API so that I can monitor bot health continuously
  - **Acceptance**: WebSocket /api/v1/stream pushes updates (positions, orders, health) every 5s, HTTP /api/v1/metrics provides current snapshot
  - **Independent test**: Subscribe to stream → verify updates received → disconnect → query metrics endpoint → verify current state
  - **Depends on**: US1
  - **Effort**: M (4-8 hours)

**Priority 3 (Nice-to-have)**

- **US9** [P3]: As an LLM, I want historical performance query API so that I can analyze trends and patterns
  - **Acceptance**: GET /api/v1/performance?start=YYYY-MM-DD&end=YYYY-MM-DD returns aggregated metrics (daily_pnl, win_rate, avg_rr, trade_count)
  - **Independent test**: Query date range → verify metrics calculated from trade logs
  - **Depends on**: US1, US2
  - **Effort**: M (4-8 hours)

- **US10** [P3]: As an LLM, I want automated testing validation so that I can verify bot behavior without manual intervention
  - **Acceptance**: Integration tests for all API endpoints, response validation fixtures, performance benchmarks (<100ms P95)
  - **Independent test**: Run test suite → verify coverage >80% → verify performance benchmarks pass
  - **Depends on**: US1-US8
  - **Effort**: L (8-16 hours)

**Effort Scale**:
- XS: <2 hours
- S: 2-4 hours
- M: 4-8 hours (½ day)
- L: 8-16 hours (1-2 days)
- XL: 16+ hours (>2 days, consider breaking down)

**MVP Strategy**: Ship US1-US4 first (core state exposure + documentation), validate LLM can understand and query bot state, then add US5-US8 (interactivity + workflows) based on usage patterns.

## Success Criteria

> **Technology-agnostic, measurable, user-focused outcomes**

1. **LLM State Comprehension**: An LLM can determine current bot state (positions, health, P&L) from API responses alone without accessing logs or source code

2. **Operational Task Coverage**: LLMs can successfully execute 90% of common maintenance tasks (check status, analyze performance, adjust parameters) via APIs or CLI

3. **Error Diagnosis Efficiency**: Time to diagnose errors reduced by 70% through semantic error reporting (from 15 minutes average log investigation to <5 minutes API query)

4. **Non-Technical Accessibility**: Non-technical stakeholders can query bot status via natural language and receive understandable responses

5. **API Documentation Quality**: Complete API documentation passes accessibility audit (all endpoints documented, examples provided, no undocumented parameters)

6. **Context Window Efficiency**: Bot state summary fits within 10KB (<2500 tokens), enabling LLMs to maintain full context across interactions

7. **Configuration Safety**: 100% of configuration changes validated against schema before application, with zero breaking changes from invalid configs

8. **Workflow Automation**: Common maintenance workflows (bot restart, target updates, log exports) executable via API with <5% failure rate

## Hypothesis

> Improving observability and operability of existing bot infrastructure

**Problem**: Trading bot operations require significant technical expertise due to opaque state, scattered logs, and manual intervention requirements
- Evidence: Average 15 minutes to diagnose errors through log investigation; configuration changes require code inspection; status checks need multiple API calls
- Impact: All operators (technical and non-technical); every operational session

**Solution**: Structured APIs, semantic logging, and natural language interface that expose bot internals in LLM-consumable format
- Change: Add JSON state API, extend logs with semantic fields, implement NL command processing, provide OpenAPI documentation
- Mechanism: LLMs can parse structured data more reliably than logs; semantic context reduces ambiguity; documentation enables self-service

**Prediction**: Error diagnosis time reduced from 15min to <5min (-67%) through semantic error queries; LLM operational task coverage increases from 30% to 90% (+200%)
- Primary metric: Time-to-diagnosis <5min (currently 15min)
- Expected improvement: -67% time, +200% LLM task coverage
- Confidence: High (similar patterns in observability tools like Datadog, New Relic semantic error tracking)

## Context Strategy & Signal Design

- **System prompt altitude**: Mid-level (operator assistant) - knows bot capabilities but not implementation details
- **Tool surface**: State API (read-only), workflow execution API (write), documentation browser
- **Examples in scope**: 3 canonical queries (check status, analyze today, diagnose error)
- **Context budget**: 2500 tokens (10KB JSON) per query via /api/v1/summary
- **Retrieval strategy**: JIT (pull latest state on-demand); identifiers: position_id, order_id, trade_id
- **Memory artifacts**: NOTES.md (operational decisions), error-log.md (incident tracking)
- **Compaction cadence**: Summarize every 10 interactions (preserve: critical errors, config changes, performance anomalies)
- **Sub-agents**: None (single API interface for all operations)

## Requirements

### Functional Requirements

**R1: Structured State Exposure**
- **FR-001**: System MUST provide GET /api/v1/state endpoint returning JSON with positions, orders, account balance, buying power, configuration summary, health metrics
- **FR-002**: System MUST provide GET /api/v1/summary endpoint returning <10KB JSON with essential state (health, position count, order count, daily P&L, circuit breaker status, recent errors)
- **FR-003**: State API responses MUST include human-readable explanation fields for each metric (e.g., "circuit_breaker_status": "active", "circuit_breaker_reason": "Daily loss limit exceeded (-$1250)")

**R2: Semantic Logging**
- **FR-004**: System MUST log all errors in JSONL format with required fields: timestamp, level, error_type, message, cause, impact, recommended_action, context
- **FR-005**: Context field MUST include relevant identifiers (trade_id, symbol, order_id) for correlation
- **FR-006**: Recommended_action field MUST provide actionable next steps (e.g., "Check API credentials", "Retry with smaller position size", "Contact support if persists")

**R3: Natural Language Commands**
- **FR-007**: CLI MUST accept natural language queries and extract intent (status, performance, positions, health, errors)
- **FR-008**: CLI MUST route extracted intent to appropriate API endpoints
- **FR-009**: CLI MUST format API responses in human-readable text with context
- **FR-010**: CLI MUST return clarifying questions when command intent is ambiguous (e.g., "show performance" → "Today, this week, or this month?")

**R4: Self-Documenting APIs**
- **FR-011**: System MUST serve OpenAPI 3.0 specification at /api/docs
- **FR-012**: OpenAPI spec MUST include all endpoints with request/response schemas, examples, error codes, descriptions
- **FR-013**: Each endpoint MUST include usage scenario documentation (when to use, what data it returns, example use cases)

**R5: Observability Dashboard API**
- **FR-014**: System MUST provide GET /api/v1/metrics endpoint with current health status, positions, orders, performance metrics
- **FR-015**: System MUST provide WebSocket /api/v1/stream for real-time updates (5-second push interval)
- **FR-016**: Dashboard metrics MUST include: account status, open positions (with live P&L), today's performance, circuit breaker state, recent errors

**R6: Error Explainability**
- **FR-017**: All HTTP error responses MUST include semantic error format: {error_code, error_type, message, cause, impact, remediation, context}
- **FR-018**: Error codes MUST follow consistent scheme (e.g., BOT_001 for trading errors, API_001 for API errors, CFG_001 for config errors)
- **FR-019**: Remediation field MUST provide specific steps to resolve error

**R7: Maintenance Workflows**
- **FR-020**: System MUST define workflows in YAML format with steps, validation, rollback procedures
- **FR-021**: System MUST provide POST /api/v1/workflows/{id}/execute endpoint with progress tracking
- **FR-022**: Workflow execution MUST validate each step before proceeding and report failures with semantic errors
- **FR-023**: Workflows MUST include: restart-bot, update-targets, export-logs, check-health

**R8: Configuration Management**
- **FR-024**: System MUST provide GET /api/v1/config endpoint returning current configuration
- **FR-025**: System MUST provide POST /api/v1/config/validate endpoint for schema validation before applying changes
- **FR-026**: System MUST provide GET /api/v1/config/diff?proposed={...} showing changes between current and proposed config
- **FR-027**: System MUST provide PUT /api/v1/config/rollback endpoint to revert to previous configuration
- **FR-028**: Configuration changes MUST be validated against JSON schema before application

**R9: LLM Context Window Optimization**
- **FR-029**: Summary endpoint response MUST be <10KB (<2500 tokens)
- **FR-030**: Summary MUST prioritize critical information: health status, position count, order count, daily P&L, active alerts, recent errors (max 3)
- **FR-031**: All API responses MUST include Cache-Control headers for efficient caching

**R10: Testing & Validation**
- **FR-032**: System MUST include integration tests for all API endpoints
- **FR-033**: System MUST validate API response schemas against fixtures
- **FR-034**: System MUST benchmark API performance with P95 latency <100ms
- **FR-035**: System MUST include smoke tests for critical paths (state query, error logging, workflow execution)

### Non-Functional Requirements

**NFR-001**: Performance: API endpoints MUST respond within 100ms P95 latency under normal load (10 concurrent requests)

**NFR-002**: Availability: State API MUST return cached state if live data unavailable, with staleness indicator

**NFR-003**: Security: API endpoints MUST require authentication token; configuration changes MUST be logged with user audit trail

**NFR-004**: Error Handling: All API errors MUST return semantic error responses; HTTP status codes MUST follow RFC 7231

**NFR-005**: Compatibility: APIs MUST follow semantic versioning; breaking changes MUST increment major version

**NFR-006**: Documentation: OpenAPI spec MUST be auto-generated from code to prevent drift

**NFR-007**: Logging: Structured logs MUST be parseable by standard JSONL tools (jq, grep, Python json module)

**NFR-008**: Extensibility: New workflow types MUST be addable via YAML without code changes

### Key Entities

**BotState**
- Purpose: Represents current bot operational state
- Key attributes: positions (List[Position]), orders (List[Order]), account (AccountInfo), health (HealthStatus), config_summary (Dict), timestamp
- Relationships: Contains Position, Order, AccountInfo, HealthStatus

**Position**
- Purpose: Represents open trading position
- Key attributes: symbol, quantity, entry_price, current_price, unrealized_pnl, pnl_percent
- Relationships: Part of BotState

**SemanticError**
- Purpose: LLM-consumable error representation
- Key attributes: error_code, error_type, message, cause, impact, remediation, context, timestamp
- Relationships: Logged to error_log.jsonl, returned in API error responses

**Workflow**
- Purpose: Automated maintenance task definition
- Key attributes: id, name, steps (List[WorkflowStep]), validation_rules, rollback_procedure
- Relationships: Contains WorkflowStep

**WorkflowStep**
- Purpose: Single action in workflow
- Key attributes: id, description, action_type, parameters, validation, success_criteria
- Relationships: Part of Workflow

## Deployment Considerations

### Platform Dependencies
- New FastAPI application for REST API endpoints (separate from bot process)
- WebSocket support for real-time streaming
- JSON schema validation library (pydantic or jsonschema)

### Environment Variables
- New: `BOT_API_PORT` (default: 8000)
- New: `BOT_API_AUTH_TOKEN` (required for API access)
- New: `BOT_API_CORS_ORIGINS` (comma-separated allowed origins)
- New: `BOT_STATE_CACHE_TTL` (seconds, default: 60)

### Breaking Changes
- No breaking changes to existing bot functionality
- Additive only: new API layer on top of existing modules
- Existing CLI dashboard and logging remain unchanged

### Migration Required
- No database migrations
- No data backfill
- Configuration: Add API auth token to deployment environment

### Rollback Considerations
- Standard rollback: stop API service, revert code
- Bot core functionality unaffected by API service status
- Feature flag: `ENABLE_API_SERVICE` (default: true)

## Assumptions

1. **Authentication**: Bot operators have access to generate/manage API tokens; assume token-based auth sufficient (OAuth2 not required initially)

2. **Deployment Model**: API service runs as separate process alongside bot (not embedded); assume sufficient resources for second process

3. **Network Access**: Operators can access API via HTTP; assume no complex firewall/VPN requirements for initial rollout

4. **Log Storage**: Existing JSONL logs stored on filesystem; assume sufficient disk space for semantic log expansion (~30% increase in log volume)

5. **Query Volume**: LLM queries expected <100/hour during normal operations; assume no need for rate limiting beyond basic protection

6. **Natural Language Scope**: Initial NL command set limited to status/performance queries; complex commands (e.g., "place order") deferred to future iterations

7. **Documentation Maintenance**: OpenAPI spec auto-generated from code; assume development workflow includes spec regeneration step

8. **Workflow Complexity**: Initial workflows are linear (sequential steps); parallel execution and conditional logic deferred to future enhancements

## Out of Scope

- LLM-initiated trade execution (read-only operations only in MVP)
- Multi-bot orchestration (single bot instance only)
- Historical data visualization UI (API provides data, visualization is consumer responsibility)
- Advanced NL command parsing (complex multi-clause queries)
- Real-time strategy adjustment via LLM
- Automated anomaly detection (manual query-based analysis only)
- Multi-tenancy (single operator/bot pairing)

## Risks & Mitigations

**Risk 1**: API token exposure leads to unauthorized access
- **Mitigation**: Document secure token storage practices; implement rate limiting; log all API access with audit trail

**Risk 2**: Semantic error context increases log volume significantly
- **Mitigation**: Implement log rotation; make semantic fields optional via configuration; monitor disk usage

**Risk 3**: Natural language parsing ambiguity causes incorrect API calls
- **Mitigation**: Return clarifying questions when confidence <80%; log all NL interpretations for debugging

**Risk 4**: API service failure impacts bot operations
- **Mitigation**: Decouple API from bot core; bot continues trading if API down; implement health checks

**Risk 5**: OpenAPI spec drift from actual implementation
- **Mitigation**: Auto-generate spec from code; CI validation step to check spec accuracy

## References

- Existing dashboard: specs/019-status-dashboard/spec.md
- Structured logging: src/trading_bot/logging/
- Performance tracking: src/trading_bot/performance/
- Error handling: src/trading_bot/error_handling/
- GitHub Issue: #34
- Similar tools: Datadog semantic error tracking, New Relic observability APIs
