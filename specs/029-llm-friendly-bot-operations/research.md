# Research & Discovery: llm-friendly-bot-operations

## Research Decisions

### Decision: Separate FastAPI service architecture
- **Decision**: Run LLM API as separate FastAPI application alongside bot (not embedded)
- **Rationale**:
  - Isolates bot trading logic from observability queries
  - Prevents API request load from affecting trading performance
  - Enables independent scaling and deployment
  - Existing api/ directory already uses FastAPI pattern
- **Alternatives**:
  - Embedded in bot process: Rejected due to potential performance impact on trading
  - Separate Flask/Django: Rejected, FastAPI already used in api/app/main.py
- **Source**: api/app/main.py:17-21 (existing FastAPI application pattern)

### Decision: Reuse existing data models from dashboard and performance modules
- **Decision**: Build API layer on top of existing DashboardSnapshot, PerformanceMetrics, AccountStatus models
- **Rationale**:
  - Dashboard already aggregates positions, account, performance data
  - Prevents duplication of data collection logic
  - Ensures consistency between CLI dashboard and API responses
- **Alternatives**:
  - Create new data collection layer: Rejected, duplicates working code
  - Directly query trading bot internals: Rejected, violates separation of concerns
- **Source**: src/trading_bot/dashboard/models.py:67-84 (DashboardSnapshot)

### Decision: Extend structured logging with semantic error context
- **Decision**: Add semantic fields (cause, impact, remediation) to existing JSONL logs
- **Rationale**:
  - Structured logger already writes JSONL format (easy parsing)
  - Thread-safe logging already implemented
  - Daily file rotation pattern established
  - Only need to add LLM-optimized fields
- **Alternatives**:
  - Replace with new logging system: Rejected, existing system works well
  - Separate error log: Rejected, fragments observability data
- **Source**: src/trading_bot/logging/structured_logger.py:23-95

### Decision: FastAPI with Pydantic validation and OpenAPI auto-generation
- **Decision**: Use FastAPI request/response models with automatic OpenAPI schema generation
- **Rationale**:
  - Existing api/app/ uses FastAPI + Pydantic pattern
  - Auto-generates OpenAPI spec (prevents drift)
  - Built-in validation reduces boilerplate
- **Alternatives**:
  - Manual OpenAPI spec: Rejected due to drift risk
  - Flask with manual validation: Rejected, FastAPI already in use
- **Source**: api/app/schemas/order.py:15-71 (Pydantic schema pattern), api/app/main.py:17-21 (FastAPI app)

### Decision: WebSocket for real-time streaming, HTTP for queries
- **Decision**: Implement WebSocket /api/v1/stream for push updates, HTTP GET for snapshot queries
- **Rationale**:
  - FastAPI supports WebSocket out of box
  - LLMs can subscribe to WebSocket for real-time monitoring
  - HTTP endpoints serve point-in-time queries
- **Alternatives**:
  - Server-Sent Events (SSE): Considered, WebSocket more flexible
  - Polling only: Rejected, inefficient for real-time updates
- **Source**: FastAPI WebSocket documentation, existing HTTP pattern in api/app/routes/orders.py

### Decision: YAML-based workflow definitions for maintenance tasks
- **Decision**: Define workflows (restart-bot, update-targets, export-logs) in YAML files
- **Rationale**:
  - YAML already used for dashboard targets (config/dashboard-targets.yaml)
  - Non-developers can modify workflows without code changes
  - Easy for LLMs to parse and understand
- **Alternatives**:
  - Python code-based workflows: Rejected, requires code changes
  - JSON workflow definitions: Considered, YAML more human-readable
- **Source**: Dashboard targets use YAML (spec.md references config/dashboard-targets.yaml)

### Decision: Token-based authentication with API key
- **Decision**: Simple API token authentication initially (defer OAuth2)
- **Rationale**:
  - Single-operator use case doesn't need complex auth
  - LLM integrations easier with API key than OAuth flows
  - Existing api/app/core/auth.py provides pattern
- **Alternatives**:
  - OAuth2: Deferred to future, overkill for MVP
  - No auth: Rejected, security risk
- **Source**: api/app/core/auth.py:12 (get_current_trader_id pattern), Spec assumption #1

### Decision: <10KB JSON response optimization via selective field inclusion
- **Decision**: Summary endpoint returns only critical fields, detailed endpoint returns full state
- **Rationale**:
  - 10KB = ~2500 tokens fits in LLM context window
  - Most queries need summary, not full state
  - Detailed endpoint available when needed
- **Alternatives**:
  - Single endpoint with field filtering: Considered, adds complexity
  - GraphQL: Rejected, adds dependency and learning curve
- **Source**: Spec FR-029, FR-030 (context window optimization requirements)

---

## Components to Reuse (9 found)

- **src/trading_bot/dashboard/models.py** - DashboardSnapshot, AccountStatus, PositionDisplay, PerformanceMetrics (complete data aggregation layer)
- **src/trading_bot/dashboard/data_provider.py** - Data collection from bot internals (account, positions, performance)
- **src/trading_bot/dashboard/metrics_calculator.py** - Performance calculations (win rate, avg R:R, streak, drawdown)
- **src/trading_bot/logging/structured_logger.py** - Thread-safe JSONL logging with daily rotation
- **src/trading_bot/logging/trade_record.py** - TradeRecord model for trade logging
- **src/trading_bot/performance/tracker.py** - Performance metric tracking and aggregation
- **src/trading_bot/performance/models.py** - PerformanceSummary, AlertEvent models
- **src/trading_bot/error_handling/exceptions.py** - RetriableError, NonRetriableError, CircuitBreakerTripped exception hierarchy
- **api/app/** - FastAPI application structure (main.py, routes/, schemas/, core/)

---

## New Components Needed (11 required)

- **api/app/routes/state.py** - State API endpoints (GET /api/v1/state, GET /api/v1/summary)
- **api/app/routes/metrics.py** - Observability endpoints (GET /api/v1/metrics, WebSocket /api/v1/stream)
- **api/app/routes/config.py** - Configuration management endpoints (GET/POST /api/v1/config, rollback)
- **api/app/routes/workflows.py** - Workflow execution endpoints (POST /api/v1/workflows/{id}/execute)
- **api/app/schemas/state.py** - Pydantic schemas for state responses (BotStateResponse, SummaryResponse)
- **api/app/schemas/errors.py** - Semantic error response schemas (SemanticError with cause/impact/remediation)
- **api/app/services/state_aggregator.py** - Service to combine dashboard, performance, health data into unified state
- **api/app/services/workflow_executor.py** - YAML workflow parser and execution engine
- **api/app/services/config_validator.py** - JSON schema validation for configuration changes
- **api/app/core/websocket.py** - WebSocket connection manager for real-time streaming
- **api/app/middleware/semantic_error_handler.py** - Global exception handler that converts errors to semantic format

---

## Unknowns & Questions

None - all technical questions resolved during spec phase. Key decisions documented above.
