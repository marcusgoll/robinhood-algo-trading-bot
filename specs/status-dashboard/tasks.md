# Tasks: CLI Status Dashboard & Performance Metrics

## [CODEBASE REUSE ANALYSIS]

Scanned: src/trading_bot/**/*.py, tests/**/*.py

### [EXISTING - REUSE]
- ✅ AccountData (src/trading_bot/account/account_data.py) - 60s TTL cache, provides account status
- ✅ TradeQueryHelper (src/trading_bot/logging/query_helper.py) - <15ms JSONL queries
- ✅ TradeRecord (src/trading_bot/logging/trade_record.py) - 27-field dataclass with P&L calculation
- ✅ time_utils (src/trading_bot/utils/time_utils.py) - pytz timezone handling
- ✅ Structured logging pattern (src/trading_bot/logger.py) - JSONL event tracking
- ✅ rich library (v13.8.0) - Already installed, Table/Panel/Live components

### [NEW - CREATE]
- 🆕 dashboard.py (no existing) - Main orchestrator with polling loop
- 🆕 display_renderer.py (no existing) - Rich UI rendering
- 🆕 metrics_calculator.py (no existing) - Performance metric aggregation
- 🆕 export_generator.py (no existing) - JSON + Markdown export
- 🆕 is_market_open() function (extend time_utils.py) - Market hours detection

---

## Phase 3.1: Setup & Dependencies

### T001 [P] Add PyYAML dependency for targets configuration
- **File**: pyproject.toml or requirements.txt
- **Add**: PyYAML==6.0.1
- **Verify**: pip install -e . succeeds without conflicts
- **Pattern**: Existing dependency declarations in pyproject.toml
- **From**: plan.md [CI/CD IMPACT] - New dependencies

### T002 [P] Create dashboard module directory structure
- **Create**: src/trading_bot/dashboard/__init__.py
- **Export**: Main classes (DashboardState, AccountStatus, PositionDisplay, PerformanceMetrics)
- **Pattern**: src/trading_bot/account/__init__.py (module exports)
- **From**: plan.md [STRUCTURE]

### T003 [P] Create example targets configuration file
- **File**: config/dashboard-targets.yaml.example
- **Content**: From plan.md [SCHEMA] - targets section with comments
- **Note**: Example only (users copy to dashboard-targets.yaml)
- **Pattern**: config/config.json.example pattern
- **From**: plan.md [SCHEMA] - Configuration Schema

---

## Phase 3.2: RED - Write Failing Tests

### T004 [RED] Write test: is_market_open() detects market hours correctly
- **File**: tests/unit/utils/test_time_utils_market_hours.py
- **Test cases**:
  - Market open (Mon-Fri 9:30 AM - 4:00 PM ET)
  - Market closed (weekends)
  - Market closed (before 9:30 AM)
  - Market closed (after 4:00 PM)
  - DST transitions
- **Pattern**: tests/unit/utils/test_time_utils.py (existing time tests)
- **From**: plan.md [ARCHITECTURE DECISIONS] - Market Hours Detection

### T005 [RED] Write test: MetricsCalculator computes win rate from trade logs
- **File**: tests/unit/dashboard/test_metrics_calculator.py
- **Test cases**:
  - Win rate with all wins (100%)
  - Win rate with all losses (0%)
  - Win rate with mixed outcomes (realistic)
  - Empty trade log (0% or None)
- **Mock**: TradeQueryHelper returns controlled trade data
- **Pattern**: tests/unit/logging/test_query_helper.py
- **From**: plan.md [SCHEMA] - PerformanceMetrics dataclass

### T006 [RED] Write test: MetricsCalculator computes current streak
- **File**: tests/unit/dashboard/test_metrics_calculator.py
- **Test cases**:
  - Win streak (3 consecutive wins)
  - Loss streak (2 consecutive losses)
  - No trades (streak = 0)
  - Single trade (streak = 1)
- **Verify**: Streak type (WIN/LOSS) and count
- **Pattern**: Pytest parametrize for multiple scenarios
- **From**: plan.md [SCHEMA] - PerformanceMetrics.current_streak

### T007 [RED] Write test: MetricsCalculator aggregates total P&L correctly
- **File**: tests/unit/dashboard/test_metrics_calculator.py
- **Test cases**:
  - Realized P&L only (no positions)
  - Unrealized P&L only (open positions, no closed trades)
  - Combined realized + unrealized
  - Decimal precision preserved
- **Mock**: AccountData.get_positions() + TradeQueryHelper results
- **Pattern**: Decimal comparison with quantize
- **From**: plan.md [SCHEMA] - PerformanceMetrics.total_pl

### T008 [RED] Write test: DisplayRenderer formats positions table correctly
- **File**: tests/unit/dashboard/test_display_renderer.py
- **Test cases**:
  - Empty positions (show "No positions" message)
  - Single position with profit (green P&L)
  - Single position with loss (red P&L)
  - Multiple positions (sorted by symbol)
  - Decimal formatting ($150.25, +1.17%)
- **Verify**: Rich Table structure, color coding
- **Pattern**: Test rich Table.columns and Table.rows
- **From**: plan.md [STRUCTURE] - DisplayRenderer responsibilities

### T009 [RED] Write test: DisplayRenderer formats account status panel
- **File**: tests/unit/dashboard/test_display_renderer.py
- **Test cases**:
  - All account fields present
  - Market status (OPEN/CLOSED) color coded
  - Timestamp formatted (ISO 8601)
  - Day trade count shows remaining (2/3)
- **Verify**: Rich Panel title and content
- **Pattern**: Rich Panel rendering tests
- **From**: plan.md [SCHEMA] - AccountStatus dataclass

### T010 [RED] Write test: DisplayRenderer formats performance metrics panel
- **File**: tests/unit/dashboard/test_display_renderer.py
- **Test cases**:
  - Win rate with target comparison (green if meeting)
  - Win rate without target (no comparison)
  - Current streak display (3 wins / 2 losses)
  - Total P&L color coded (green profit, red loss)
- **Verify**: Target comparison indicators (✓/✗)
- **Pattern**: Rich Text markup for colors
- **From**: plan.md [SCHEMA] - PerformanceMetrics + DashboardTargets

### T011 [RED] Write test: ExportGenerator creates valid JSON export
- **File**: tests/unit/dashboard/test_export_generator.py
- **Test cases**:
  - JSON structure matches DashboardState schema
  - Decimal values serialized correctly
  - Timestamp in ISO 8601 format
  - File written to logs/ with date in filename
- **Verify**: json.loads() succeeds, schema validation
- **Pattern**: JSON schema validation tests
- **From**: plan.md [STRUCTURE] - ExportGenerator responsibilities

### T012 [RED] Write test: ExportGenerator creates readable Markdown export
- **File**: tests/unit/dashboard/test_export_generator.py
- **Test cases**:
  - Markdown headers and sections present
  - Positions table formatted as markdown table
  - Metrics formatted with bullet points
  - Target comparison included (if targets exist)
- **Verify**: File written, markdown valid (no broken syntax)
- **Pattern**: Markdown generation tests
- **From**: plan.md [ARCHITECTURE DECISIONS] - Export Format

### T013 [RED] Write test: Dashboard loads targets file gracefully
- **File**: tests/unit/dashboard/test_dashboard.py
- **Test cases**:
  - Targets file exists and valid (loaded successfully)
  - Targets file missing (None, no crash)
  - Targets file invalid YAML (None, warning logged)
  - Targets file missing required fields (None, warning logged)
- **Verify**: Graceful degradation, warning logged once
- **Pattern**: Configuration loading with error handling
- **From**: plan.md [ARCHITECTURE DECISIONS] - Configuration

### T014 [RED] Write test: Dashboard aggregates DashboardState correctly
- **File**: tests/unit/dashboard/test_dashboard.py
- **Test cases**:
  - All components assembled (account + positions + metrics)
  - Market status determined (OPEN/CLOSED)
  - Timestamp set to current UTC time
  - Targets loaded if available
- **Mock**: AccountData, TradeQueryHelper, time_utils.is_market_open()
- **Pattern**: Integration test with multiple mocks
- **From**: plan.md [SCHEMA] - DashboardState dataclass

### T015 [RED] Write test: Dashboard polling loop refreshes at 5s interval
- **File**: tests/unit/dashboard/test_dashboard.py
- **Test cases**:
  - Refresh called after 5 seconds
  - Manual refresh (R key) bypasses timer
  - Quit (Q key) exits loop cleanly
- **Mock**: time.sleep(), keyboard input
- **Pattern**: Polling loop with timer mocks
- **From**: plan.md [ARCHITECTURE DECISIONS] - Refresh Strategy

### T016 [RED] Write test: Dashboard keyboard handler processes commands
- **File**: tests/unit/dashboard/test_dashboard.py
- **Test cases**:
  - R key triggers manual refresh
  - E key triggers export
  - Q key exits dashboard
  - H key shows help overlay
  - Invalid key ignored (no crash)
- **Mock**: Keyboard input events
- **Pattern**: Event handler testing
- **From**: plan.md [STRUCTURE] - dashboard.py keyboard handling

---

## Phase 3.3: GREEN - Minimal Implementation

### T017 [GREEN→T004] Implement is_market_open() in time_utils.py
- **File**: src/trading_bot/utils/time_utils.py
- **Function**: is_market_open(check_time: datetime | None = None) -> bool
- **Logic**: 9:30 AM - 4:00 PM ET, Mon-Fri, DST-aware using pytz
- **REUSE**: Existing pytz import, timezone conversion pattern
- **Pattern**: Existing is_trading_hours() function in same file
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] - time_utils extension

### T018 [GREEN→T005,T006,T007] Implement MetricsCalculator class
- **File**: src/trading_bot/dashboard/metrics_calculator.py
- **Class**: MetricsCalculator
- **Methods**:
  - calculate_win_rate(trades: list[TradeRecord]) -> float
  - calculate_avg_risk_reward(trades: list[TradeRecord]) -> float
  - calculate_current_streak(trades: list[TradeRecord]) -> tuple[int, str]
  - calculate_total_pl(trades: list[TradeRecord], positions: list) -> tuple[Decimal, Decimal, Decimal]
  - aggregate_metrics(trades, positions) -> PerformanceMetrics
- **REUSE**: TradeRecord dataclass, TradeQueryHelper pattern
- **Pattern**: Service class with static methods
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] - metrics_calculator.py

### T019 [GREEN→T008,T009,T010] Implement DisplayRenderer class
- **File**: src/trading_bot/dashboard/display_renderer.py
- **Class**: DisplayRenderer
- **Methods**:
  - render_account_status(account: AccountStatus, market_status: str) -> Panel
  - render_positions_table(positions: list[PositionDisplay]) -> Table
  - render_performance_metrics(metrics: PerformanceMetrics, targets: DashboardTargets | None) -> Panel
  - render_full_dashboard(state: DashboardState) -> Layout
- **REUSE**: rich.table.Table, rich.panel.Panel, rich.layout.Layout
- **Pattern**: Renderer class with composition
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] - display_renderer.py

### T020 [GREEN→T011,T012] Implement ExportGenerator class
- **File**: src/trading_bot/dashboard/export_generator.py
- **Class**: ExportGenerator
- **Methods**:
  - export_to_json(state: DashboardState, filepath: Path) -> None
  - export_to_markdown(state: DashboardState, filepath: Path) -> None
  - generate_exports(state: DashboardState) -> tuple[Path, Path]
- **Logic**: Generate logs/dashboard-export-YYYY-MM-DD.{json,md}
- **REUSE**: json.dumps() with Decimal encoder, datetime.now()
- **Pattern**: File writing with error handling
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] - export_generator.py

### T021 [GREEN→T013] Implement targets configuration loader
- **File**: src/trading_bot/dashboard/dashboard.py
- **Function**: load_targets(config_path: Path = Path("config/dashboard-targets.yaml")) -> DashboardTargets | None
- **Logic**: PyYAML safe_load, schema validation, graceful fallback on error
- **REUSE**: yaml.safe_load pattern
- **Pattern**: Configuration loading with try/except
- **From**: plan.md [ARCHITECTURE DECISIONS] - Configuration

### T022 [GREEN→T014] Implement DashboardState aggregation
- **File**: src/trading_bot/dashboard/dashboard.py
- **Function**: fetch_dashboard_state(account_data: AccountData, trade_helper: TradeQueryHelper, targets: DashboardTargets | None) -> DashboardState
- **Logic**: Aggregate account status, positions, metrics, market status
- **REUSE**: AccountData methods, TradeQueryHelper.query_by_date_range()
- **Pattern**: Service orchestration pattern
- **From**: plan.md [SCHEMA] - DashboardState dataclass

### T023 [GREEN→T015,T016] Implement dashboard polling loop with keyboard input
- **File**: src/trading_bot/dashboard/dashboard.py
- **Function**: run_dashboard_loop(account_data: AccountData, trade_helper: TradeQueryHelper, targets: DashboardTargets | None) -> None
- **Logic**: rich.live.Live context, 5s polling with keyboard.on_press handlers
- **Keys**: R=refresh, E=export, Q=quit, H=help
- **REUSE**: rich.live.Live for flicker-free updates
- **Pattern**: Event loop with keyboard input (pynput or readchar)
- **From**: plan.md [STRUCTURE] - dashboard.py main loop

### T024 [P] Implement DashboardState and related dataclasses
- **File**: src/trading_bot/dashboard/models.py
- **Dataclasses**: DashboardState, AccountStatus, PositionDisplay, PerformanceMetrics, DashboardTargets
- **Fields**: From plan.md [SCHEMA] section
- **Pattern**: @dataclass with type hints, similar to TradeRecord
- **From**: plan.md [SCHEMA] - All dataclass definitions

### T025 [P] Implement dashboard entry point
- **File**: src/trading_bot/dashboard/dashboard.py
- **Function**: main() -> None
- **Logic**:
  1. Initialize AccountData service
  2. Initialize TradeQueryHelper
  3. Load targets (optional)
  4. Log dashboard.launched event
  5. Run dashboard loop
  6. Log dashboard.exited event on quit
- **REUSE**: Existing service initialization patterns
- **Pattern**: CLI entry point with setup/teardown
- **From**: plan.md [STRUCTURE] - dashboard.py main entry point

### T026 [P] Add dashboard module support to __main__.py
- **File**: src/trading_bot/__main__.py
- **Add**: Argument parser option for `dashboard` subcommand
- **Logic**: if args.mode == 'dashboard': run dashboard.main()
- **Pattern**: Existing __main__.py argparse pattern
- **From**: plan.md [STRUCTURE] - __main__.py update

---

## Phase 3.4: REFACTOR - Clean Up & Optimize

### T027 [REFACTOR] Extract color coding logic to ColorScheme utility
- **File**: src/trading_bot/dashboard/display_renderer.py
- **Refactor**: Extract hardcoded colors to ColorScheme class
- **Benefits**: Centralized color definitions, easier theming
- **Tests**: All existing tests stay green (no behavior change)
- **Pattern**: Constants class with semantic naming
- **From**: Code smell - magic color strings in DisplayRenderer

### T028 [REFACTOR] Add type hints to all dashboard functions
- **Files**: All src/trading_bot/dashboard/*.py
- **Add**: Complete type annotations (PEP 484)
- **Verify**: mypy passes with no errors
- **Pattern**: Existing type hint usage in codebase
- **From**: plan.md [SUCCESS CRITERIA] - NFR-005 type hints

### T029 [REFACTOR] Extract dashboard event logging to logger utility
- **File**: src/trading_bot/dashboard/dashboard.py
- **Refactor**: Create log_dashboard_event() helper function
- **Benefits**: DRY principle, consistent event structure
- **Tests**: All existing tests stay green
- **Pattern**: src/trading_bot/logger.py structured logging
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE] - Logging pattern

---

## Phase 3.5: Integration & Testing

### T030 [P] Write integration test: Full dashboard with live data
- **File**: tests/integration/dashboard/test_dashboard_integration.py
- **Test**: End-to-end dashboard launch with AccountData + TradeQueryHelper
- **Mock**: API responses (avoid live Robinhood calls in CI)
- **Verify**:
  - Dashboard state aggregates correctly
  - DisplayRenderer produces valid output
  - No crashes with realistic data
- **Pattern**: Integration test with service mocks
- **From**: plan.md [TESTING STRATEGY] - Integration Tests

### T031 [P] Write integration test: Export generates valid files
- **File**: tests/integration/dashboard/test_export_integration.py
- **Test**: Full export flow from DashboardState to files
- **Verify**:
  - JSON file valid and parseable
  - Markdown file formatted correctly
  - Files written to logs/ directory
  - Filenames include date
- **Cleanup**: Remove test files after assertions
- **Pattern**: File I/O integration tests
- **From**: plan.md [TESTING STRATEGY] - Integration Tests

### T032 [P] Write integration test: Graceful degradation scenarios
- **File**: tests/integration/dashboard/test_dashboard_error_handling.py
- **Test cases**:
  - Missing trade logs (show warning, no crash)
  - API error from AccountData (show cached data + warning)
  - Invalid targets file (degrade gracefully)
  - No positions (display empty positions table)
- **Verify**: Warnings logged, dashboard continues
- **Pattern**: Error injection testing
- **From**: plan.md [ARCHITECTURE DECISIONS] - Graceful degradation

---

## Phase 3.6: Error Handling & Resilience

### T033 [RED] Write test: Dashboard logs usage events correctly
- **File**: tests/unit/dashboard/test_dashboard_logging.py
- **Test cases**:
  - dashboard.launched event on startup
  - dashboard.refreshed event on manual refresh
  - dashboard.exported event on export
  - dashboard.exited event on quit
- **Verify**: JSONL format, correct event structure
- **Pattern**: Structured logging tests
- **From**: plan.md [SCHEMA] - Usage Event Schema

### T034 [GREEN→T033] Add usage event logging throughout dashboard
- **File**: src/trading_bot/dashboard/dashboard.py
- **Add**: log_dashboard_event() calls at key points
- **Events**: launched, refreshed, exported, exited, error
- **REUSE**: src/trading_bot/logger.py structured logging pattern
- **Pattern**: logger.info() with structured data
- **From**: plan.md [SCHEMA] - logs/dashboard-usage.jsonl

### T035 [REFACTOR] Add error tracking with session_id
- **File**: src/trading_bot/dashboard/dashboard.py
- **Refactor**: Generate UUID session_id on startup, include in all events
- **Benefits**: Correlate events for single dashboard session
- **Tests**: Verify session_id consistent across events
- **Pattern**: UUID generation with uuid.uuid4()
- **From**: plan.md [SCHEMA] - Usage Event Schema session_id field

---

## Phase 3.7: Performance & Optimization

### T036 [P] Benchmark dashboard startup time
- **File**: tests/performance/test_dashboard_performance.py
- **Test**: Measure cold start time (<2s target)
- **Method**: time.perf_counter() before/after main()
- **Verify**: Startup time consistently <2s (NFR-001)
- **Pattern**: Performance benchmark tests
- **From**: plan.md [PERFORMANCE TARGETS] - NFR-001

### T037 [P] Benchmark dashboard refresh cycle time
- **File**: tests/performance/test_dashboard_performance.py
- **Test**: Measure refresh cycle time (<500ms target)
- **Method**: time.perf_counter() before/after fetch_dashboard_state()
- **Verify**: Refresh time consistently <500ms (NFR-001)
- **Pattern**: Performance benchmark tests
- **From**: plan.md [PERFORMANCE TARGETS] - NFR-001

### T038 [P] Benchmark export generation time
- **File**: tests/performance/test_dashboard_performance.py
- **Test**: Measure export generation time (<1s target)
- **Method**: time.perf_counter() before/after generate_exports()
- **Verify**: Export time consistently <1s (NFR-001)
- **Pattern**: Performance benchmark tests
- **From**: plan.md [PERFORMANCE TARGETS] - NFR-001

---

## Phase 3.8: Documentation & Polish

### T039 [P] Add docstrings to all dashboard public functions
- **Files**: All src/trading_bot/dashboard/*.py
- **Format**: Google-style docstrings with Args, Returns, Raises
- **Verify**: pydocstyle passes with no errors
- **Pattern**: Existing docstring format in codebase
- **From**: plan.md [SUCCESS CRITERIA] - Code quality

### T040 [P] Document dashboard usage in NOTES.md
- **File**: specs/status-dashboard/NOTES.md
- **Add**: Implementation notes section
- **Content**:
  - How to run dashboard (python -m trading_bot.dashboard)
  - Keyboard shortcuts (R/E/Q/H)
  - Performance benchmarks achieved
  - Known limitations
- **Pattern**: NOTES.md checkpoint format
- **From**: plan.md [DEPLOYMENT ACCEPTANCE] - Rollback Plan

### T041 [P] Create dashboard usage example in README
- **File**: README.md or docs/dashboard-usage.md
- **Content**:
  - Quick start guide
  - Screenshot/example output
  - Configuration (targets.yaml)
  - Troubleshooting
- **Pattern**: Existing README sections
- **From**: plan.md [INTEGRATION SCENARIOS] - Production Use

---

## Phase 3.9: Validation & Acceptance

### T042 [P] Run manual acceptance tests checklist
- **Checklist**: From plan.md [TESTING STRATEGY] - Manual Tests
- **Tests**:
  - [ ] Dashboard launches <2s with live data
  - [ ] Positions display correctly with color-coded P&L
  - [ ] Performance metrics calculate accurately from logs
  - [ ] Export (E key) creates valid JSON + Markdown files
  - [ ] Manual refresh (R key) updates display immediately
  - [ ] Help overlay (H key) shows keyboard shortcuts
  - [ ] Quit (Q key) exits cleanly without errors
  - [ ] Staleness indicator appears after 60s without API update
  - [ ] Market status (OPEN/CLOSED) displays correctly
  - [ ] Missing targets file degrades gracefully
- **Record**: Results in NOTES.md
- **From**: plan.md [TESTING STRATEGY] - Manual Tests

### T043 [P] Verify test coverage meets thresholds
- **Run**: pytest --cov=src/trading_bot/dashboard --cov-report=term-missing
- **Verify**:
  - Overall coverage ≥90% (NFR-006)
  - No critical paths uncovered
  - Coverage report in NOTES.md
- **Pattern**: Coverage verification in CI
- **From**: plan.md [TESTING STRATEGY] - Unit Tests

### T044 [P] Run full test suite and verify all pass
- **Run**: pytest tests/ -v
- **Verify**: 0 failures, 0 errors, all tests green
- **Verify**: Test execution time <6 minutes (NFR-006)
- **Record**: Test results in NOTES.md
- **Pattern**: Pre-merge validation checklist
- **From**: plan.md [SUCCESS CRITERIA] - Quality Acceptance

---

## Summary

**Total Tasks**: 44
**TDD Breakdown**:
- Setup: 3 tasks (T001-T003)
- RED (failing tests): 13 tasks (T004-T016)
- GREEN (implementation): 10 tasks (T017-T026)
- REFACTOR (cleanup): 3 tasks (T027-T029)
- Integration: 3 tasks (T030-T032)
- Error handling: 3 tasks (T033-T035)
- Performance: 3 tasks (T036-T038)
- Documentation: 3 tasks (T039-T041)
- Validation: 3 tasks (T042-T044)

**Parallelization**: Tasks marked [P] can run in parallel (different files, no dependencies)
**Dependencies**: Tasks marked [GREEN→TNN] or [REFACTOR] depend on prior tests passing

**Next Phase**: After completion → `/analyze` (validate architecture, identify risks)
