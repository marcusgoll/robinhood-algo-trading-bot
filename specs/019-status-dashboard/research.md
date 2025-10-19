# Research & Discovery: 019-status-dashboard

## Research Decisions

### Decision: Architecture - Multi-Service Composition Pattern
- **Decision**: Use dependency injection pattern with DashboardDataProvider as orchestrator
- **Rationale**: Separates concerns (data aggregation, rendering, metrics calculation, export) for testability and reusability. Enables future TUI interface (FR-017 mentioned in codebase) to share same data provider
- **Alternatives**: Monolithic dashboard class (rejected - violates KISS and DRY), procedural functions (rejected - harder to test and extend)
- **Source**: src/trading_bot/dashboard/dashboard.py (lines 69-242), Constitution §Code_Quality (one function one purpose)

### Decision: CLI Framework - Rich Library
- **Decision**: Use `rich` library for terminal rendering with Live display mode
- **Rationale**: Industry-standard Python CLI library with advanced features (tables, color, live refresh, progress). Battle-tested, active maintenance, excellent documentation
- **Alternatives**: `blessed` (rejected - lower-level API), `urwid` (rejected - TUI focus, overkill for MVP), raw ANSI codes (rejected - maintenance burden)
- **Source**: src/trading_bot/dashboard/display_renderer.py, spec.md line 103

### Decision: Data Precision - Decimal for Financial Values
- **Decision**: Use `Decimal` type for all monetary values and percentages in calculations
- **Rationale**: Avoids floating-point precision errors in financial calculations. Constitution §Safety_First mandates correctness for financial data
- **Alternatives**: Float (rejected - precision loss unacceptable), integers with basis points (rejected - unnecessarily complex)
- **Source**: Constitution §Safety_First, src/trading_bot/dashboard/models.py (lines 15-53)

### Decision: Refresh Strategy - Polling with Configurable Interval
- **Decision**: 5-second polling loop with manual refresh override (R key)
- **Rationale**: Account data caches for 60s (account-data-module), polling aligns with cache TTL. Simple implementation, predictable behavior
- **Alternatives**: Event-driven updates (rejected - over-engineering for MVP), WebSocket (rejected - no real-time API), 1s refresh (rejected - excessive API calls)
- **Source**: src/trading_bot/dashboard/dashboard.py line 26 (REFRESH_INTERVAL_SECONDS = 5.0)

### Decision: State Management - Stateless with Snapshot Pattern
- **Decision**: DashboardSnapshot immutable dataclass encapsulates all display data
- **Rationale**: Enables easy serialization for export, thread-safe, testable. Snapshot can be passed to multiple renderers (CLI, TUI, JSON exporter)
- **Alternatives**: Mutable state dict (rejected - error-prone), global state (rejected - violates testability), database persistence (rejected - overkill)
- **Source**: src/trading_bot/dashboard/models.py (lines 67-84), FR-017 requirement for reusable payload

### Decision: Error Handling - Graceful Degradation with Warnings
- **Decision**: Show cached/partial data with warning indicators instead of crashing
- **Rationale**: Constitution §Safety_First mandates "fail safe not fail open". Dashboard should remain useful even with stale data or missing trade logs
- **Alternatives**: Crash on error (rejected - violates safety), silent failures (rejected - misleading operator), retry forever (rejected - hangs UI)
- **Source**: Constitution §Safety_First, src/trading_bot/dashboard/data_provider.py (lines 106-125)

### Decision: Export Format - JSON + Markdown Dual Output
- **Decision**: Generate both machine-readable JSON and human-readable Markdown on export
- **Rationale**: JSON for automation/analysis, Markdown for quick visual review. Minimal storage overhead (~2KB per export)
- **Alternatives**: JSON only (rejected - poor readability), Markdown only (rejected - harder to parse), CSV (rejected - nested data awkward)
- **Source**: FR-007 requirement, src/trading_bot/dashboard/export_generator.py

### Decision: Testing Strategy - Unit + Integration + Performance Tiers
- **Decision**: Three test tiers: unit tests (90%+ coverage), integration tests (E2E flow), performance tests (startup/refresh benchmarks)
- **Rationale**: Constitution §Testing_Requirements mandates ≥90% coverage. Performance tests verify NFR-001 (<2s startup, <500ms refresh)
- **Alternatives**: Unit tests only (rejected - misses integration issues), manual testing (rejected - no regression detection)
- **Source**: Constitution §Testing_Requirements, tests/unit/test_dashboard/, tests/integration/dashboard/, tests/performance/test_dashboard_performance.py

---

## Components to Reuse (8 found)

### Core Services (Already Implemented)
- **src/trading_bot/account/account_data.py**: AccountData service for buying power, balance, positions, day trade count (FR-001, FR-002)
- **src/trading_bot/logging/query_helper.py**: TradeQueryHelper for reading structured trade logs (FR-003)
- **src/trading_bot/dashboard/metrics_calculator.py**: MetricsCalculator for win rate, R:R, streaks, P&L aggregation (FR-011 to FR-014)
- **src/trading_bot/dashboard/data_provider.py**: DashboardDataProvider orchestrates account data + trade log + metrics (FR-001 to FR-016)
- **src/trading_bot/dashboard/display_renderer.py**: DisplayRenderer generates Rich layouts for CLI display (FR-008)
- **src/trading_bot/dashboard/export_generator.py**: ExportGenerator creates JSON + Markdown exports (FR-007)
- **src/trading_bot/dashboard/models.py**: Data models (AccountStatus, PositionDisplay, PerformanceMetrics, DashboardTargets, DashboardSnapshot)
- **src/trading_bot/utils/time_utils.py**: is_market_open() for market status indicator (FR-009)

### Supporting Infrastructure
- **src/trading_bot/logger.py**: log_dashboard_event() for audit trail (NFR-007)
- **rich.console.Console**: Terminal rendering library (industry standard)
- **rich.live.Live**: Auto-refresh display context manager

---

## New Components Needed (0 required for MVP)

**Status**: Full implementation already exists at `src/trading_bot/dashboard/`

**Validation**: All 16 functional requirements (FR-001 to FR-016) and 8 non-functional requirements (NFR-001 to NFR-008) covered by existing code:
- FR-001 to FR-003: Account/positions/metrics display → DashboardDataProvider + DisplayRenderer
- FR-004: Auto-refresh → dashboard.py run_dashboard_loop()
- FR-005: Target comparison → DashboardDataProvider.load_targets()
- FR-006: Keyboard controls (R/E/Q/H) → _CommandReader + command polling loop
- FR-007: JSON + Markdown export → ExportGenerator
- FR-008: Color coding → DisplayRenderer with color_scheme.py
- FR-009: Market status → is_market_open() utility
- FR-010: Staleness indicator → DashboardSnapshot.is_data_stale
- FR-011 to FR-014: Metrics calculations → MetricsCalculator
- FR-015 to FR-016: Graceful degradation → DashboardDataProvider error handling

**Test Coverage**: Comprehensive test suite exists:
- Unit tests: tests/unit/test_dashboard/ (dashboard orchestration, additional scenarios)
- Integration tests: tests/integration/dashboard/ (E2E flow, error handling)
- Performance tests: tests/performance/test_dashboard_performance.py
- Logging tests: tests/unit/dashboard/test_dashboard_logging.py

**Gap Analysis**: No missing components identified. Spec-to-implementation alignment verified.

---

## Unknowns & Questions

None - all technical questions resolved through existing implementation review.

**Clarifications from spec.md edge cases**:
- No positions open → Display "No open positions" message (handled by DisplayRenderer)
- No trades today → Show 0 trades, cumulative stats from history (handled by MetricsCalculator)
- Missing trade log → Graceful degradation with warning (handled by DashboardDataProvider)
- Market hours vs after hours → Market status indicator (handled by is_market_open())
- Missing targets file → Display metrics without comparison, log warning (handled by load_targets())
- API call failure → Show cached data with stale indicator (handled by error handling in refresh())

---

## Implementation Status

**Current State**: Feature fully implemented and tested

**Validation Steps**:
1. ✅ All 16 functional requirements mapped to code
2. ✅ All 8 non-functional requirements addressed
3. ✅ Constitution compliance verified (type hints, error handling, Decimal precision, audit logging)
4. ✅ Test coverage exceeds 90% requirement (unit + integration + performance tiers)
5. ✅ Edge cases from spec.md handled gracefully

**Next Phase**: /tasks command will generate task breakdown for:
- Documentation updates (if needed)
- Additional test scenarios (if gaps found)
- Performance optimization (if benchmarks below NFR-001 targets)
- Integration validation (verify dependencies: account-data-module, performance-tracking, trade-logging)
