# Tasks: LLM-Friendly Bot Operations and Monitoring

## [CODEBASE REUSE ANALYSIS]
Scanned: D:/Coding/Stocks/api/app/**/*.py, D:/Coding/Stocks/src/trading_bot/**/*.py

[EXISTING - REUSE]
- ✅ FastAPI app setup (api/app/main.py)
- ✅ Authentication pattern (api/app/core/auth.py)
- ✅ Database session management (api/app/core/database.py)
- ✅ Event bus (api/app/core/events.py)
- ✅ Repository pattern (api/app/repositories/order_repository.py)
- ✅ Route pattern (api/app/routes/orders.py)
- ✅ Schema pattern (api/app/schemas/order.py)
- ✅ Service pattern (api/app/services/order_executor.py)
- ✅ DashboardSnapshot model (src/trading_bot/dashboard/models.py)
- ✅ PerformanceMetrics model (src/trading_bot/performance/models.py)
- ✅ Structured logger (src/trading_bot/logging/structured_logger.py)
- ✅ Error handling hierarchy (src/trading_bot/error_handling/exceptions.py)
- ✅ Test patterns (tests/unit/test_*.py, tests/integration/test_*.py)

[NEW - CREATE]
- 🆕 WebSocket connection manager (no existing pattern)
- 🆕 State aggregator service (aggregates dashboard + performance + health)
- 🆕 Workflow executor service (YAML workflow parser and runner)
- 🆕 Config validator service (JSON schema validation)
- 🆕 Semantic error handler middleware (global exception converter)
- 🆕 Semantic error dataclass and formatter
- 🆕 State API routes (GET /state, GET /summary)
- 🆕 Metrics API routes (GET /metrics, WebSocket /stream)
- 🆕 Config API routes (config management with validation)
- 🆕 Workflow API routes (workflow execution and tracking)
- 🆕 YAML workflow definitions (restart-bot, update-targets, etc.)

## [DEPENDENCY GRAPH]
Story completion order:
1. Phase 2: Foundational (semantic logging + auth - blocks all stories)
2. Phase 3: US1 [P1] - State API (independent)
3. Phase 4: US2 [P1] - Semantic Logging Extension (independent)
4. Phase 5: US3 [P1] - OpenAPI Docs (depends on US1 routes)
5. Phase 6: US4 [P1] - Summary Endpoint (depends on US1)
6. Phase 7: US6 [P2] - Config Management (depends on US1, US3)
7. Phase 8: US8 [P2] - Observability/WebSocket (depends on US1)
8. Phase 9: US7 [P2] - Workflows (depends on US1, US6)
9. Phase 10: US5 [P2] - NL Commands (depends on US1)
10. Phase 11: Polish & Testing (US10)

## [PARALLEL EXECUTION OPPORTUNITIES]
- Phase 3: T010, T011, T012, T013 (different files, no dependencies)
- Phase 4: T020, T021 (different modules)
- Phase 6: T040, T041 (routes + tests)
- Phase 7: T050, T051, T052 (routes, service, middleware)
- Phase 8: T060, T061, T062 (routes, service, tests)
- Phase 9: T070, T071, T072 (routes, service, YAML definitions)
- Phase 10: T080, T081 (CLI + tests)

## [IMPLEMENTATION STRATEGY]
**MVP Scope**: Phases 3-6 (US1-US4: State API, Semantic Logging, OpenAPI, Summary)
**Incremental delivery**: MVP → staging validation → Enhancements (US5-US8) → Final testing
**Testing approach**: Unit tests for services, integration tests for API routes, smoke tests for critical paths

---

## Phase 1: Setup

- [ ] T001 Install FastAPI dependencies in requirements.txt
  - Packages: fastapi==0.104.1, uvicorn[standard]==0.24.0, pydantic==2.5.0, websockets==12.0, jsonschema==4.20.0
  - REUSE: Existing requirements.txt pattern
  - From: plan.md [ARCHITECTURE DECISIONS]

- [ ] T002 [P] Create directory structure for new modules
  - Directories: api/app/routes/{state,metrics,config,workflows}.py, api/app/services/{state_aggregator,workflow_executor,config_validator}.py, api/app/schemas/{state,errors,config,workflows}.py, api/app/core/websocket.py, api/app/middleware/semantic_error_handler.py, src/trading_bot/logging/{semantic_error,error_formatter}.py, config/workflows/
  - From: plan.md [STRUCTURE]

- [ ] T003 [P] Add new environment variables to .env.example
  - Variables: BOT_API_PORT=8000, BOT_API_AUTH_TOKEN=<generate>, BOT_API_CORS_ORIGINS=*, BOT_STATE_CACHE_TTL=60
  - Pattern: Existing .env.example
  - From: plan.md [CI/CD IMPACT]

---

## Phase 2: Foundational (blocking prerequisites)

**Goal**: Infrastructure that blocks all user stories

- [ ] T005 [P] Create SemanticError dataclass in src/trading_bot/logging/semantic_error.py
  - Fields: error_code (str), error_type (str), message (str), cause (str), impact (str), remediation (str), context (Dict), timestamp (datetime)
  - Pattern: src/trading_bot/logging/trade_record.py (dataclass pattern)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T006 [P] Create error formatter in src/trading_bot/logging/error_formatter.py
  - Function: format_exception(exc: Exception) -> SemanticError
  - Logic: Extract error type, message, traceback → semantic fields
  - REUSE: Exception hierarchy from src/trading_bot/error_handling/exceptions.py
  - Pattern: src/trading_bot/logging/structured_logger.py (logging utilities)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T007 Extend API key auth in api/app/core/auth.py
  - Function: verify_api_key(api_key: str = Header(..., alias="X-API-Key")) -> bool
  - Logic: Compare against BOT_API_AUTH_TOKEN env var
  - REUSE: Existing auth.py JWT pattern
  - Pattern: api/app/core/auth.py (dependency injection with Depends)
  - From: plan.md [SECURITY]

---

## Phase 3: User Story 1 [P1] - State API

**Story Goal**: LLMs can query current bot state via JSON API

**Independent Test Criteria**:
- [ ] Start bot → curl /api/v1/state → verify complete state in response
- [ ] State response includes positions, orders, account, health, config_summary
- [ ] Response time <200ms P95

### Implementation

- [ ] T010 [P] [US1] Create BotStateResponse schema in api/app/schemas/state.py
  - Fields: positions (List[PositionDisplay]), orders (List[OrderSummary]), account (AccountStatus), health (HealthStatus), config_summary (Dict), timestamp (datetime)
  - REUSE: DashboardSnapshot from src/trading_bot/dashboard/models.py
  - Pattern: api/app/schemas/order.py (Pydantic schema with examples)
  - From: data-model.md BotState entity

- [ ] T011 [P] [US1] Create state aggregator service in api/app/services/state_aggregator.py
  - Class: StateAggregator
  - Methods: get_bot_state() -> BotStateResponse, get_health_status() -> HealthStatus
  - Logic: Aggregate DashboardSnapshot + PerformanceSummary + health check
  - REUSE: DashboardSnapshot (src/trading_bot/dashboard/models.py), PerformanceSummary (src/trading_bot/performance/models.py)
  - Pattern: api/app/services/order_executor.py (service class pattern)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T012 [P] [US1] Create state routes in api/app/routes/state.py
  - Endpoint: GET /api/v1/state returns BotStateResponse
  - Dependencies: StateAggregator (Depends), verify_api_key (Depends)
  - REUSE: Route pattern from api/app/routes/orders.py
  - Pattern: api/app/routes/orders.py (FastAPI router, dependency injection)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T013 [P] [US1] Register state routes in api/app/main.py
  - Import: from api.app.routes import state
  - Registration: app.include_router(state.router, prefix="/api/v1", tags=["state"])
  - REUSE: Existing main.py router registration pattern
  - Pattern: api/app/main.py (FastAPI app setup)
  - From: plan.md [STRUCTURE]

### Tests

- [ ] T015 [P] [US1] Write unit test for state aggregator in tests/unit/services/test_state_aggregator.py
  - Test: test_get_bot_state_aggregates_dashboard_and_performance
  - Mock: DashboardSnapshot, PerformanceSummary
  - Assert: BotStateResponse contains all required fields
  - Pattern: tests/unit/services/test_screener_service.py
  - Coverage: ≥80% (new code must be 100%)

- [ ] T016 [P] [US1] Write integration test for state API in tests/integration/services/test_state_api.py
  - Test: test_state_endpoint_returns_complete_state
  - Given-When-Then: Start API → GET /api/v1/state → verify 200 + schema
  - Real: FastAPI TestClient with dependency overrides
  - Pattern: tests/integration/momentum/test_api_routes.py
  - Coverage: ≥60% integration paths

---

## Phase 4: User Story 2 [P1] - Semantic Logging Extension

**Story Goal**: All errors logged with semantic fields for LLM parsing

**Independent Test Criteria**:
- [ ] Trigger error → parse log entry → verify all semantic fields present
- [ ] Semantic fields include: error_code, cause, impact, remediation, context

### Implementation

- [ ] T020 [P] [US2] Extend structured logger with semantic fields in src/trading_bot/logging/structured_logger.py
  - Method: log_semantic_error(error: SemanticError)
  - Logic: Write SemanticError to JSONL with all fields
  - REUSE: Existing StructuredLogger class
  - Pattern: src/trading_bot/logging/structured_logger.py (thread-safe JSONL logging)
  - From: plan.md [EXISTING INFRASTRUCTURE - REUSE]

- [ ] T021 [P] [US2] Create semantic error handler middleware in api/app/middleware/semantic_error_handler.py
  - Handler: global_exception_handler(request, exc) -> SemanticErrorResponse
  - Logic: Catch all exceptions → convert to SemanticError → return JSON
  - REUSE: error_formatter.format_exception()
  - Pattern: FastAPI exception handler pattern
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

### Tests

- [ ] T023 [US2] Write unit test for error formatter in tests/unit/logging/test_error_formatter.py
  - Test: test_format_exception_creates_semantic_error
  - Input: RetriableError, NonRetriableError, generic Exception
  - Assert: All semantic fields populated correctly
  - Pattern: tests/unit/logging/test_screener_logger.py
  - Coverage: ≥80%

---

## Phase 5: User Story 3 [P1] - OpenAPI Documentation

**Story Goal**: Complete API documentation auto-generated from routes

**Independent Test Criteria**:
- [ ] Load /api/docs → verify Swagger UI loads
- [ ] Verify all endpoints documented with examples

### Implementation

- [ ] T030 [US3] Add OpenAPI metadata to FastAPI app in api/app/main.py
  - Metadata: title="Trading Bot API", version="1.0.0", description="LLM-friendly operations API"
  - OpenAPI tags: state, metrics, config, workflows
  - REUSE: Existing main.py FastAPI app
  - Pattern: FastAPI OpenAPI configuration
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T031 [P] [US3] Add examples to all schema models
  - Files: api/app/schemas/state.py, api/app/schemas/order.py
  - Add: Config.schema_extra with example dict
  - Pattern: api/app/schemas/order.py (Pydantic Config with examples)
  - From: spec.md [SELF-DOCUMENTING APIS]

### Tests

- [ ] T033 [US3] Write smoke test for OpenAPI spec in tests/smoke/test_openapi.py
  - Test: test_openapi_spec_includes_all_endpoints
  - Verify: /api/docs accessible, spec.json contains all routes
  - Pattern: tests/smoke/test_trade_logging_smoke.py
  - Coverage: Critical path only

---

## Phase 6: User Story 4 [P1] - Summary Endpoint

**Story Goal**: Compressed state summary <10KB for LLM context windows

**Independent Test Criteria**:
- [ ] Query summary → verify response <10KB
- [ ] Summary contains: health status, position count, daily P&L, recent errors (max 3)

### Implementation

- [ ] T040 [P] [US4] Create BotSummaryResponse schema in api/app/schemas/state.py
  - Fields: health_status (str), positions_count (int), open_orders_count (int), daily_pnl (float), circuit_breaker_status (str), recent_errors (List[SemanticError], max 3)
  - Size optimization: Selective fields only, truncate error messages if needed
  - Pattern: api/app/schemas/order.py (Pydantic schema)
  - From: data-model.md BotSummary entity

- [ ] T041 [P] [US4] Add GET /api/v1/summary endpoint in api/app/routes/state.py
  - Endpoint: GET /api/v1/summary returns BotSummaryResponse
  - Logic: Query StateAggregator → select critical fields → limit recent_errors to 3
  - Cache: 60s TTL via Cache-Control header
  - REUSE: StateAggregator.get_bot_state()
  - Pattern: api/app/routes/orders.py (FastAPI route with caching)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

### Tests

- [ ] T043 [US4] Write unit test for summary size validation in tests/unit/services/test_state_aggregator.py
  - Test: test_summary_response_under_10kb
  - Assert: json.dumps(summary).encode().sizeof() < 10240
  - Pattern: tests/unit/test_validator.py (size validation)
  - Coverage: ≥80%

---

## Phase 7: User Story 6 [P2] - Configuration Management

**Story Goal**: Safe config changes with validation and rollback

**Independent Test Criteria**:
- [ ] Submit config → verify validation → apply change → verify active → rollback → verify reverted
- [ ] Invalid config rejected with detailed errors

### Implementation

- [ ] T050 [P] [US6] Create config schemas in api/app/schemas/config.py
  - Models: BotConfigRequest, ValidationResult, ConfigDiff, ConfigChangeResult
  - Fields: BotConfigRequest (risk_per_trade, max_position_size, circuit_breaker_thresholds), ValidationResult (valid, errors), ConfigDiff (changes, old_values, new_values)
  - Pattern: api/app/schemas/order.py (Pydantic request/response schemas)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T051 [P] [US6] Create config validator service in api/app/services/config_validator.py
  - Class: ConfigValidator
  - Methods: validate(config) -> ValidationResult, generate_diff(old, new) -> ConfigDiff, apply(config), rollback()
  - Logic: JSON schema validation, audit trail in config/config_history.jsonl
  - REUSE: Structured logger for audit trail
  - Pattern: api/app/services/order_validator.py (validation service)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T052 [P] [US6] Create config routes in api/app/routes/config.py
  - Endpoints: GET /api/v1/config, POST /api/v1/config/validate, GET /api/v1/config/diff, PUT /api/v1/config/rollback
  - Dependencies: ConfigValidator (Depends), verify_api_key (Depends)
  - Pattern: api/app/routes/orders.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T053 [US6] Create JSON schema for bot config in config/config.schema.json
  - Schema: Define risk_per_trade (0.01-0.05), max_position_size (100-10000), circuit_breaker_thresholds
  - From: spec.md [CONFIGURATION MANAGEMENT]

### Tests

- [ ] T055 [P] [US6] Write integration test for config management in tests/integration/services/test_config_api.py
  - Test: test_config_validation_and_rollback
  - Given-When-Then: Submit valid config → apply → rollback → verify reverted
  - Pattern: tests/integration/test_auth_integration.py
  - Coverage: ≥60%

---

## Phase 8: User Story 8 [P2] - Observability & Streaming

**Story Goal**: Real-time bot monitoring via WebSocket and HTTP endpoints

**Independent Test Criteria**:
- [ ] Subscribe to WebSocket → verify updates received every 5s
- [ ] Query metrics endpoint → verify current snapshot
- [ ] Disconnect → verify clean connection closure

### Implementation

- [ ] T060 [P] [US8] Create WebSocket connection manager in api/app/core/websocket.py
  - Class: ConnectionManager
  - Methods: connect(websocket), disconnect(websocket), broadcast(message)
  - Logic: Maintain active connections list, handle heartbeat, broadcast updates
  - Pattern: FastAPI WebSocket pattern
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T061 [P] [US8] Create metrics routes in api/app/routes/metrics.py
  - Endpoints: GET /api/v1/metrics (snapshot), WebSocket /api/v1/stream (5s updates)
  - Logic: GET returns current state, WebSocket broadcasts every 5s
  - REUSE: StateAggregator.get_bot_state()
  - Pattern: api/app/routes/orders.py + FastAPI WebSocket
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T062 [P] [US8] Add WebSocket broadcast loop in api/app/main.py
  - Startup event: Background task that broadcasts state every 5s
  - Logic: while True: sleep(5), get_state(), broadcast to all WebSocket clients
  - REUSE: ConnectionManager.broadcast()
  - Pattern: FastAPI lifespan events
  - From: plan.md [PERFORMANCE TARGETS]

### Tests

- [ ] T064 [US8] Write integration test for WebSocket streaming in tests/integration/services/test_metrics_api.py
  - Test: test_websocket_stream_pushes_updates
  - Given-When-Then: Connect WebSocket → wait 10s → verify ≥2 updates received
  - Pattern: FastAPI WebSocket testing pattern
  - Coverage: ≥60%

---

## Phase 9: User Story 7 [P2] - Workflows

**Story Goal**: Execute maintenance tasks via YAML workflow definitions

**Independent Test Criteria**:
- [ ] Load workflow → execute steps → verify progress tracking → verify completion
- [ ] Failed step halts workflow and logs error

### Implementation

- [ ] T070 [P] [US7] Create workflow schemas in api/app/schemas/workflows.py
  - Models: WorkflowListResponse, WorkflowExecutionRequest, WorkflowStatusResponse, WorkflowStep
  - Fields: WorkflowStep (id, description, action_type, parameters, validation, success_criteria)
  - Pattern: api/app/schemas/order.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T071 [P] [US7] Create workflow executor service in api/app/services/workflow_executor.py
  - Class: WorkflowExecutor
  - Methods: load_workflow(id) -> Workflow, execute(workflow_id) -> WorkflowStatusResponse, get_status(workflow_id)
  - Logic: Parse YAML, execute steps sequentially, validate success, handle rollback
  - REUSE: Structured logger for execution logging
  - Pattern: api/app/services/order_executor.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T072 [P] [US7] Create workflow routes in api/app/routes/workflows.py
  - Endpoints: GET /api/v1/workflows (list), POST /api/v1/workflows/{id}/execute, GET /api/v1/workflows/{id}/status
  - Dependencies: WorkflowExecutor (Depends), verify_api_key (Depends)
  - Pattern: api/app/routes/orders.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T073 [P] [US7] Create YAML workflow definitions in config/workflows/
  - Files: restart-bot.yaml, update-targets.yaml, export-logs.yaml, check-health.yaml
  - Structure: name, steps (id, description, action_type, parameters, validation)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

### Tests

- [ ] T075 [US7] Write integration test for workflow execution in tests/integration/services/test_workflows_api.py
  - Test: test_workflow_execution_tracks_progress
  - Given-When-Then: Execute check-health workflow → verify each step completes → verify final status
  - Pattern: tests/integration/test_startup_flow.py
  - Coverage: ≥60%

---

## Phase 10: User Story 5 [P2] - Natural Language Commands

**Story Goal**: Process natural language queries and route to API endpoints

**Independent Test Criteria**:
- [ ] Input NL command → verify intent extraction → verify correct API called → verify formatted response
- [ ] Ambiguous command returns clarifying questions

### Implementation

- [ ] T080 [P] [US5] Create NL command CLI in src/trading_bot/cli/nl_commands.py
  - Functions: extract_intent(command) -> Intent, route_to_api(intent) -> Response, format_response(response) -> str
  - Intent types: status, performance, positions, health, errors
  - Pattern: Simple keyword matching (upgrade to LLM later)
  - From: spec.md [NATURAL LANGUAGE COMMANDS]

- [ ] T081 [P] [US5] Add CLI entry point in src/trading_bot/main.py
  - Command: python -m src.trading_bot.cli.nl_commands "show today's performance"
  - Logic: Parse command → extract intent → call API → format response
  - REUSE: API client for /api/v1/* endpoints
  - Pattern: src/trading_bot/main.py (CLI entry point)
  - From: plan.md [IMPLEMENTATION SEQUENCE]

### Tests

- [ ] T083 [US5] Write unit test for intent extraction in tests/unit/cli/test_nl_commands.py
  - Test: test_extract_intent_from_status_query
  - Input: "show bot status", "what positions are open", "check health"
  - Assert: Correct intent extracted
  - Pattern: tests/unit/test_query_helper.py
  - Coverage: ≥80%

---

## Phase 11: Polish & Cross-Cutting Concerns

### Error Handling & Resilience

- [ ] T090 Register semantic error handler in api/app/main.py
  - Exception handler: app.add_exception_handler(Exception, global_exception_handler)
  - REUSE: api/app/middleware/semantic_error_handler.py
  - Pattern: FastAPI exception handler registration
  - From: plan.md [ARCHITECTURE DECISIONS]

- [ ] T091 [P] Add API rate limiting middleware in api/app/middleware/rate_limiter.py
  - Limit: 100 requests/minute per API token
  - Logic: Track requests by token, return 429 with Retry-After header
  - Pattern: FastAPI middleware pattern
  - From: plan.md [SECURITY]

- [ ] T092 [P] Add CORS configuration in api/app/main.py
  - Middleware: CORSMiddleware with BOT_API_CORS_ORIGINS env var
  - REUSE: Existing CORS pattern in main.py
  - From: plan.md [SECURITY]

### Deployment Preparation

- [ ] T095 Add health check endpoint in api/app/routes/state.py
  - Endpoint: GET /api/v1/health/healthz
  - Check: API server alive, bot reachable
  - Return: {"status": "healthy", "timestamp": "..."}
  - Pattern: Standard health check pattern
  - From: plan.md [CI/CD IMPACT]

- [ ] T096 [P] Create startup script for API service in scripts/start_api.sh
  - Command: uvicorn api.app.main:app --host 0.0.0.0 --port ${BOT_API_PORT}
  - Environment: Load .env variables
  - From: plan.md [CI/CD IMPACT]

- [ ] T097 [P] Update NOTES.md with deployment instructions
  - Sections: API service startup, environment variables, smoke tests
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

### Testing & Validation

- [ ] T100 Write smoke test for all API endpoints in tests/smoke/test_api_smoke.py
  - Tests: GET /api/v1/state, GET /api/v1/summary, GET /api/v1/health/healthz
  - Assert: 200 response, valid JSON schema
  - Pattern: tests/smoke/test_trade_logging_smoke.py
  - Coverage: Critical path only (<90s total)

- [ ] T101 [P] Add performance benchmark tests in tests/performance/test_api_performance.py
  - Test: test_api_response_time_under_100ms
  - Load: 10 concurrent requests to /api/v1/summary
  - Assert: P95 latency <100ms
  - Pattern: tests/performance/test_dashboard_performance.py
  - From: spec.md NFR-001

- [ ] T102 [P] Add integration test for summary size in tests/integration/services/test_state_api.py
  - Test: test_summary_endpoint_returns_under_10kb
  - Assert: len(json.dumps(response.json()).encode()) < 10240
  - From: spec.md FR-029

---

## [TEST GUARDRAILS]

**Speed Requirements:**
- Unit tests: <2s each
- Integration tests: <10s each
- Smoke tests: <30s total
- Full suite: <6 min total

**Coverage Requirements:**
- New code: 100% coverage (no untested lines in new features)
- Unit tests: ≥80% line coverage
- Integration tests: ≥60% line coverage
- Critical path: ≥90% smoke test coverage

**Measurement:**
- Python: `pytest --cov=api --cov=src --cov-report=term-missing`
- Coverage threshold enforced in CI

**Quality Gates:**
- All tests must pass before merge
- Coverage thresholds enforced
- No skipped tests without documented reason

**Clarity Requirements:**
- One behavior per test
- Descriptive names: `test_state_endpoint_returns_complete_bot_state_with_all_fields()`
- Given-When-Then structure in integration tests

**Anti-Patterns:**
- ❌ NO mocking entire StateAggregator in integration tests (use real service with test data)
- ❌ NO testing implementation details (test behavior and contracts)
- ✅ USE TestClient for API route testing
- ✅ USE dependency overrides for test isolation

**Examples:**
```python
# ❌ Bad: Testing implementation
assert state_aggregator._cache is not None

# ✅ Good: Testing behavior
response = client.get("/api/v1/state")
assert response.status_code == 200
assert "positions" in response.json()

# ✅ Good: Given-When-Then structure
def test_summary_endpoint_caches_state():
    # Given: API is running with state data
    # When: Client queries summary twice within cache TTL
    response1 = client.get("/api/v1/summary")
    response2 = client.get("/api/v1/summary")
    # Then: Both responses identical and served from cache
    assert response1.json() == response2.json()
```

---

## Task Breakdown Summary

**Total Tasks**: 47
**MVP Tasks (US1-US4)**: 18 (Phases 1-6)
**Enhancement Tasks (US5-US8)**: 20 (Phases 7-10)
**Polish Tasks**: 9 (Phase 11)

**Parallel Execution**: 29 tasks marked [P] (different files, no blocking dependencies)

**User Story Mapping**:
- US1 (State API): T010-T016 (7 tasks)
- US2 (Semantic Logging): T005-T006, T020-T023 (6 tasks)
- US3 (OpenAPI): T030-T033 (4 tasks)
- US4 (Summary): T040-T043 (4 tasks)
- US5 (NL Commands): T080-T083 (4 tasks)
- US6 (Config Mgmt): T050-T055 (6 tasks)
- US7 (Workflows): T070-T075 (6 tasks)
- US8 (Observability): T060-T064 (5 tasks)
- US10 (Testing): T100-T102 (3 tasks)

**Implementation Order**:
1. Setup (T001-T003): Install dependencies, create structure
2. Foundational (T005-T007): Semantic errors, auth
3. MVP (T010-T043): State API, logging, OpenAPI, summary
4. Enhancements (T050-T083): Config, workflows, metrics, NL commands
5. Polish (T090-T102): Error handling, deployment, testing
