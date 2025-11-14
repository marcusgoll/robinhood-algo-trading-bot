# Tasks: CLI Status Dashboard & Performance Metrics

## [CODEBASE REUSE ANALYSIS]
Scanned: src/trading_bot/**/*.py, tests/**/*.py

[EXISTING - REUSE]
- ✅ AccountData (src/trading_bot/account/account_data.py)
- ✅ TradeQueryHelper (src/trading_bot/logging/query_helper.py)
- ✅ MetricsCalculator (src/trading_bot/dashboard/metrics_calculator.py)
- ✅ DashboardDataProvider (src/trading_bot/dashboard/data_provider.py)
- ✅ DisplayRenderer (src/trading_bot/dashboard/display_renderer.py)
- ✅ ExportGenerator (src/trading_bot/dashboard/export_generator.py)
- ✅ DashboardSnapshot (src/trading_bot/dashboard/models.py)
- ✅ is_market_open() (src/trading_bot/utils/time_utils.py)
- ✅ log_dashboard_event() (src/trading_bot/logger.py)

[NEW - CREATE]
- 🆕 None required (full implementation exists at src/trading_bot/dashboard/)

## [DEPENDENCY GRAPH]
Story completion order:
1. Phase 2: Foundational (validation setup - blocks all stories)
2. Phase 3: US1 [P1] - View account status (independent)
3. Phase 4: US2 [P1] - View positions with P&L (depends on US1 data)
4. Phase 5: US3 [P1] - View performance metrics (depends on US1, US2)
5. Phase 6: US4 [P2] - Auto-refresh every 5s (depends on US1-US3)
6. Phase 7: US5 [P2] - Target comparison (depends on US3)
7. Phase 8: US6 [P2] - Export summaries (depends on US1-US5)
8. Phase 9: US7 [P3] - Keyboard controls (depends on US4, US6)
9. Phase 10: US8 [P3] - Market status indicator (independent)

## [PARALLEL EXECUTION OPPORTUNITIES]
- US1: T010, T011, T012 (different test files, no dependencies)
- US2: T020, T021 (different test files, no dependencies)
- US3: T030, T031 (different test files, no dependencies)
- US4: T040, T041 (different test files, no dependencies)
- US7+US8: T070, T080 (independent stories, can run in parallel)

## [IMPLEMENTATION STRATEGY]
**Status**: Full implementation exists at src/trading_bot/dashboard/
**Task Focus**: Validation, testing, documentation, edge case verification
**MVP Scope**: Verify US1-US3 (core display), then validate US4-US6 (automation), finally US7-US8 (polish)
**Testing approach**: Three-tier validation (unit + integration + performance)

---

## Phase 1: Setup

- [ ] T001 Verify project structure matches plan.md specification
  - Files: src/trading_bot/dashboard/, tests/, config/
  - Validate: 9 Python files in dashboard module, 11 test files
  - Pattern: Existing structure documented in plan.md [STRUCTURE]
  - From: plan.md [STRUCTURE]

- [ ] T002 [P] Verify dependencies installed and compatible
  - Files: pyproject.toml
  - Libraries: rich>=13.0.0, pyyaml>=6.0
  - Check: Import statements work without errors
  - From: plan.md [ARCHITECTURE DECISIONS]

- [ ] T003 [P] Validate dashboard-targets.yaml config schema
  - File: config/dashboard-targets.yaml
  - Schema: target_win_rate, target_daily_pl, target_trades_per_day, max_drawdown
  - Validate: YAML loads without errors, all required fields present
  - Pattern: FR-005 specification
  - From: spec.md FR-005

---

## Phase 2: Foundational (validation setup)

**Goal**: Establish test infrastructure and baseline verification

- [ ] T005 [P] Run type checking on all dashboard modules
  - Command: mypy src/trading_bot/dashboard/
  - Validate: No type errors, all functions have type hints (NFR-005)
  - Pattern: Constitution §Code_Quality
  - From: plan.md [ARCHITECTURE DECISIONS]

- [ ] T006 [P] Establish baseline code coverage measurement
  - Command: pytest --cov=src/trading_bot/dashboard --cov-report=term-missing
  - Target: ≥90% coverage (NFR-006)
  - Files: All dashboard modules
  - From: plan.md [TESTING STRATEGY]

- [ ] T007 Verify all data models use Decimal for monetary values
  - Files: src/trading_bot/dashboard/models.py
  - Check: PositionDisplay.unrealized_pl, PerformanceMetrics.total_realized_pl use Decimal
  - Pattern: Constitution §Safety_First
  - From: plan.md [DATA MODEL]

---

## Phase 3: User Story 1 [P1] - View real-time account status

**Story Goal**: Dashboard displays buying power, balance, day trade count

**Independent Test Criteria**:
- [ ] Launch dashboard → Account section renders with current data
- [ ] Account data fetched → Values match AccountData service
- [ ] Last update timestamp shown → Displays UTC time with timezone indicator

### Tests

- [ ] T010 [P] [US1] Verify account status section rendering
  - File: tests/unit/test_dashboard/test_display_renderer.py
  - Test: Account status panel shows buying_power, account_balance, day_trade_count
  - Mock: DashboardSnapshot with known account values
  - Pattern: Existing test_render_account_section() test
  - From: spec.md Scenario 1

- [ ] T011 [P] [US1] Test account data staleness detection
  - File: tests/integration/dashboard/test_dashboard_error_handling.py
  - Test: Display stale indicator when last_updated >60s (FR-010)
  - Real data: Mock timestamp >60s in past
  - Pattern: test_stale_data_warning() test
  - From: spec.md Scenario 6

- [ ] T012 [P] [US1] Validate UTC timestamp handling
  - File: tests/unit/test_dashboard/test_dashboard_additional.py
  - Test: Timestamps stored in UTC, displayed in local time with TZ indicator (NFR-004)
  - Pattern: Constitution §Data_Integrity
  - From: plan.md [DATA MODEL]

### Validation

- [ ] T015 [US1] Manual test: Launch dashboard with real account data
  - Command: python -m trading_bot.dashboard
  - Verify: Account section displays current buying power, balance, day trade count
  - Verify: Last update timestamp shows recent time (<5s old)
  - From: spec.md Scenario 1

---

## Phase 4: User Story 2 [P1] - View positions with live P&L

**Story Goal**: Dashboard displays all open positions with unrealized P&L

**Independent Test Criteria**:
- [ ] Open positions exist → Table renders with Symbol, Qty, Entry, Current, P&L $, P&L %
- [ ] P&L calculations verified → Match manual calculation (current - entry) * quantity
- [ ] Color coding verified → Green for profit, red for loss, yellow for zero

### Tests

- [ ] T020 [P] [US2] Verify positions table rendering
  - File: tests/unit/test_dashboard/test_display_renderer.py
  - Test: Positions table shows all columns with correct data
  - Mock: DashboardSnapshot with 3 positions (profit, loss, breakeven)
  - Pattern: Existing test_render_positions_table() test
  - From: spec.md Scenario 2

- [ ] T021 [P] [US2] Test P&L calculation accuracy
  - File: tests/unit/test_dashboard/test_metrics_calculator.py
  - Test: calculate_position_pl() returns correct dollar and percentage values
  - Given: Position(qty=100, entry=50.00, current=52.50)
  - When: Calculate P&L → Then: $250.00, +5.00%
  - Pattern: Existing test_calculate_position_pl() test
  - From: spec.md FR-002

- [ ] T022 [P] [US2] Verify color coding logic
  - File: tests/unit/test_dashboard/test_display_renderer.py
  - Test: P&L values styled with correct colors (green/red/yellow)
  - Pattern: src/trading_bot/dashboard/color_scheme.py
  - From: spec.md FR-008

### Validation

- [ ] T025 [US2] Manual test: Verify positions display with real trades
  - Prerequisite: Have open positions in account
  - Command: python -m trading_bot.dashboard
  - Verify: Each position shows correct symbol, quantity, entry price
  - Verify: Current price matches market data
  - Verify: P&L calculation matches broker's reported P&L
  - Verify: Color coding correct (green for profit, red for loss)
  - From: spec.md Scenario 2

- [ ] T026 [US2] Edge case: No open positions
  - Prerequisite: Close all positions
  - Command: python -m trading_bot.dashboard
  - Verify: Display shows "No open positions" message
  - Verify: Account section still displays buying power and cash balance
  - From: spec.md Edge Cases

---

## Phase 5: User Story 3 [P1] - View performance metrics

**Story Goal**: Dashboard displays win rate, R:R, P&L, streak, trades today, session count

**Independent Test Criteria**:
- [ ] Trades executed today → Metrics calculate correctly from trade logs
- [ ] Win rate calculation → (winning trades / total trades) × 100
- [ ] Streak detection → Consecutive wins or losses from recent trades

### Tests

- [ ] T030 [P] [US3] Verify win rate calculation
  - File: tests/unit/dashboard/test_metrics_calculator.py
  - Test: calculate_win_rate() with known trade set (7 wins, 3 losses → 70%)
  - Pattern: Existing test_calculate_win_rate() test
  - From: spec.md FR-011

- [ ] T031 [P] [US3] Verify average risk-reward calculation
  - File: tests/unit/dashboard/test_metrics_calculator.py
  - Test: calculate_avg_risk_reward() with trades containing target/stop_loss
  - Given: Trades with R:R ratios [2.5, 3.0, 1.8] → Avg 2.43
  - Pattern: Existing test_calculate_avg_risk_reward() test
  - From: spec.md FR-012

- [ ] T032 [P] [US3] Verify streak calculation
  - File: tests/unit/dashboard/test_metrics_calculator.py
  - Test: calculate_current_streak() with win/loss sequences
  - Given: [W, W, L, W, W, W] → Streak: 3 wins
  - Pattern: Existing test_calculate_current_streak() test
  - From: spec.md FR-014

- [ ] T033 [P] [US3] Verify total P&L aggregation
  - File: tests/unit/dashboard/test_metrics_calculator.py
  - Test: calculate_total_pl() combines realized + unrealized P&L
  - Given: Realized: $500, Unrealized: -$200 → Total: $300
  - Pattern: Existing test_calculate_total_pl() test
  - From: spec.md FR-013

### Integration

- [ ] T035 [US3] Integration test: Metrics from real trade logs
  - File: tests/integration/dashboard/test_dashboard_integration.py
  - Test: Load real trade log JSONL → Calculate all metrics → Verify accuracy
  - Real data: Sample trades-structured.jsonl with known outcomes
  - Pattern: Existing test_dashboard_integration_full_flow() test
  - From: plan.md [TESTING STRATEGY]

### Validation

- [ ] T038 [US3] Manual test: Verify metrics with known trade history
  - Prerequisite: Have trade logs from at least one session
  - Command: python -m trading_bot.dashboard
  - Verify: Win rate matches manual count of wins/total
  - Verify: Total P&L matches sum from trade logs
  - Verify: Trades today count matches today's log entries
  - From: spec.md Scenario 3

- [ ] T039 [US3] Edge case: No trades today
  - Prerequisite: Fresh trading day with no executions
  - Command: python -m trading_bot.dashboard
  - Verify: Shows "0 trades today"
  - Verify: Cumulative stats show historical data
  - From: spec.md Edge Cases

- [ ] T040 [US3] Edge case: Missing trade log
  - Prerequisite: Temporarily rename/move trade log file
  - Command: python -m trading_bot.dashboard
  - Verify: Dashboard shows account data only
  - Verify: Warning message displayed: "Trade log not found, performance metrics unavailable"
  - Verify: No crash (graceful degradation per FR-015)
  - From: spec.md Edge Cases, plan.md [ARCHITECTURE DECISIONS]

---

## Phase 6: User Story 4 [P2] - Auto-refresh every 5 seconds

**Story Goal**: Dashboard updates automatically without manual intervention

**Independent Test Criteria**:
- [ ] Dashboard launches → Auto-refresh starts immediately
- [ ] Every 5 seconds → Display updates with fresh data
- [ ] During refresh → "Refreshing..." indicator appears

### Tests

- [ ] T041 [P] [US4] Test refresh loop timing
  - File: tests/unit/test_dashboard/test_dashboard_orchestration.py
  - Test: Verify refresh triggered every 5 seconds (FR-004)
  - Mock: time.sleep(), verify call count over 30s
  - Pattern: Existing test_dashboard_refresh_loop() test
  - From: spec.md FR-004

- [ ] T042 [P] [US4] Verify refresh indicator display
  - File: tests/unit/test_dashboard/test_display_renderer.py
  - Test: "Refreshing..." message shown during data fetch
  - Pattern: Existing test_render_refresh_indicator() test
  - From: spec.md FR-004

### Performance

- [ ] T045 [US4] Performance test: Refresh cycle latency
  - File: tests/performance/test_dashboard_performance.py
  - Test: Measure refresh cycle time (target <500ms per NFR-001)
  - Real data: 100 trades, 10 positions
  - Pattern: Existing test_dashboard_refresh_performance() test
  - From: plan.md [PERFORMANCE TARGETS]

### Validation

- [ ] T048 [US4] Manual test: Observe auto-refresh behavior
  - Command: python -m trading_bot.dashboard
  - Verify: Dashboard updates every 5 seconds automatically
  - Verify: Last update timestamp increments
  - Verify: "Refreshing..." indicator appears briefly during refresh
  - From: spec.md Scenario 1

---

## Phase 7: User Story 5 [P2] - Target comparison

**Story Goal**: Display performance vs configured targets with variance indicators

**Independent Test Criteria**:
- [ ] Targets file exists → Load and parse successfully
- [ ] Metrics displayed → Show actual vs target with variance
- [ ] Meeting target → Green indicator, not meeting → Red indicator

### Tests

- [ ] T050 [P] [US5] Test target loading from YAML
  - File: tests/unit/test_dashboard/test_dashboard_additional.py
  - Test: DashboardDataProvider.load_targets() parses YAML correctly
  - Config: config/dashboard-targets.yaml
  - Pattern: Existing test_load_targets() test
  - From: spec.md FR-005

- [ ] T051 [P] [US5] Verify target comparison rendering
  - File: tests/unit/test_dashboard/test_display_renderer.py
  - Test: Display shows "Win Rate: 65% [Target: 60%] ✓" format
  - Mock: Metrics above and below targets
  - Pattern: Existing test_render_target_comparison() test
  - From: spec.md Scenario 4

### Validation

- [ ] T055 [US5] Manual test: Target comparison display
  - Prerequisite: Ensure config/dashboard-targets.yaml exists with targets
  - Command: python -m trading_bot.dashboard
  - Verify: Each metric shows target comparison
  - Verify: Green checkmark when meeting/exceeding target
  - Verify: Red X when below target
  - From: spec.md Scenario 4

- [ ] T056 [US5] Edge case: Missing targets file
  - Prerequisite: Temporarily rename config/dashboard-targets.yaml
  - Command: python -m trading_bot.dashboard
  - Verify: Metrics displayed without target comparison
  - Verify: Warning logged once about missing config (FR-016)
  - Verify: No crash (graceful degradation)
  - From: spec.md Edge Cases

---

## Phase 8: User Story 6 [P2] - Export daily summaries

**Story Goal**: Generate JSON + Markdown export files with all metrics

**Independent Test Criteria**:
- [ ] Press 'E' key → Export triggered
- [ ] Files generated → JSON and Markdown in logs/ directory
- [ ] Export content → Contains all account, position, and performance data
- [ ] Audit logged → Export event recorded with timestamp and file paths

### Tests

- [ ] T060 [P] [US6] Test JSON export format
  - File: tests/unit/test_dashboard/test_export_generator.py
  - Test: ExportGenerator.generate_exports() creates valid JSON
  - Validate: All DashboardSnapshot fields serialized correctly
  - Pattern: Existing test_generate_json_export() test
  - From: spec.md FR-007

- [ ] T061 [P] [US6] Test Markdown export format
  - File: tests/unit/test_dashboard/test_export_generator.py
  - Test: ExportGenerator.generate_exports() creates readable Markdown
  - Validate: Contains formatted tables for positions and metrics
  - Pattern: Existing test_generate_markdown_export() test
  - From: spec.md FR-007

- [ ] T062 [P] [US6] Verify export audit logging
  - File: tests/unit/dashboard/test_dashboard_logging.py
  - Test: log_dashboard_event() called with export details (NFR-007)
  - Validate: Log contains timestamp, file paths, snapshot metadata
  - Pattern: Existing test_log_export_event() test
  - From: plan.md [SECURITY]

### Integration

- [ ] T065 [US6] Integration test: Full export workflow
  - File: tests/integration/dashboard/test_export_integration.py
  - Test: Generate snapshot → Export to files → Verify files exist and are valid
  - Real data: Complete DashboardSnapshot with positions and metrics
  - Pattern: Existing test_export_full_workflow() test
  - From: plan.md [TESTING STRATEGY]

### Performance

- [ ] T068 [US6] Performance test: Export generation time
  - File: tests/performance/test_dashboard_performance.py
  - Test: Measure export duration (target <1s from spec.md)
  - Real data: Realistic snapshot (10 positions, 100 trades)
  - Pattern: Existing test_export_generation_time() test
  - From: plan.md [PERFORMANCE TARGETS]

### Validation

- [ ] T069 [US6] Manual test: Export functionality
  - Command: python -m trading_bot.dashboard → Press 'E'
  - Verify: Two files created in logs/ directory
  - Verify: Files named dashboard-export-YYYY-MM-DD-HHmmss.json|.md
  - Verify: JSON contains all snapshot data
  - Verify: Markdown is human-readable with formatted tables
  - Verify: Export event logged in logs/
  - From: spec.md Scenario 5

---

## Phase 9: User Story 7 [P3] - Keyboard controls

**Story Goal**: Interactive controls for manual refresh, export, help, quit

**Independent Test Criteria**:
- [ ] Press 'R' → Manual refresh triggered
- [ ] Press 'E' → Export triggered
- [ ] Press 'H' → Help overlay displayed
- [ ] Press 'Q' → Dashboard exits cleanly

### Tests

- [ ] T070 [P] [US7] Test keyboard command handling
  - File: tests/unit/test_dashboard/test_dashboard_orchestration.py
  - Test: Command reader thread processes R/E/H/Q keys (FR-006)
  - Mock: stdin input simulation
  - Pattern: Existing test_keyboard_commands() test
  - From: spec.md FR-006

- [ ] T071 [P] [US7] Verify help overlay rendering
  - File: tests/unit/test_dashboard/test_display_renderer.py
  - Test: Help overlay shows all commands and descriptions
  - Pattern: Existing test_render_help_overlay() test
  - From: spec.md FR-006

### Validation

- [ ] T075 [US7] Manual test: Keyboard controls
  - Command: python -m trading_bot.dashboard
  - Test 'R': Press R → Verify manual refresh triggered immediately
  - Test 'E': Press E → Verify export files generated
  - Test 'H': Press H → Verify help overlay appears, press H again to close
  - Test 'Q': Press Q → Verify dashboard exits cleanly
  - From: spec.md FR-006

---

## Phase 10: User Story 8 [P3] - Market status indicator

**Story Goal**: Display OPEN/CLOSED based on market hours

**Independent Test Criteria**:
- [ ] During market hours (9:30 AM - 4:00 PM ET Mon-Fri) → Shows "OPEN"
- [ ] Outside market hours → Shows "CLOSED"
- [ ] Weekends → Shows "CLOSED"

### Tests

- [ ] T080 [P] [US8] Test market status detection
  - File: tests/unit/test_dashboard/test_dashboard_additional.py
  - Test: is_market_open() returns correct status for various times
  - Mock: datetime with specific times (10:00 AM ET, 6:00 PM ET, Saturday)
  - Pattern: Existing test_market_status_detection() test
  - From: spec.md FR-009

### Validation

- [ ] T085 [US8] Manual test: Market status display
  - Command: python -m trading_bot.dashboard
  - Verify: Market status indicator shows OPEN or CLOSED
  - Verify: Status matches current time and day (market hours: 9:30 AM - 4:00 PM ET, Mon-Fri)
  - From: spec.md FR-009, Edge Cases

---

## Phase 11: Performance Validation

**Goal**: Verify all performance targets from NFR-001, NFR-008

- [ ] T090 [P] Run startup time benchmark
  - File: tests/performance/test_dashboard_performance.py
  - Test: test_dashboard_startup_time()
  - Target: <2 seconds cold start (NFR-001)
  - Method: Measure time from launch to first render
  - From: plan.md [PERFORMANCE TARGETS]

- [ ] T091 [P] Run memory footprint test
  - File: tests/performance/test_dashboard_performance.py
  - Test: test_memory_usage()
  - Target: <50MB for long-running session (NFR-008)
  - Method: Monitor process memory over 5-minute session
  - From: plan.md [PERFORMANCE TARGETS]

- [ ] T092 Document performance benchmark results
  - File: specs/019-status-dashboard/NOTES.md
  - Content: Record actual startup time, refresh latency, export time, memory usage
  - Compare: Actual vs targets (NFR-001, NFR-008)
  - From: plan.md [PERFORMANCE TARGETS]

---

## Phase 12: Error Handling & Edge Cases

**Goal**: Verify graceful degradation for all edge cases from spec.md

- [ ] T095 [P] Test API failure graceful degradation
  - File: tests/integration/dashboard/test_dashboard_error_handling.py
  - Test: AccountData.get_account_balance() raises exception → Show cached data with stale indicator
  - Validate: No crash, warning displayed (FR-010, NFR-002)
  - Pattern: Existing test_api_failure_handling() test
  - From: spec.md Edge Cases

- [ ] T096 [P] Test corrupted trade log handling
  - File: tests/integration/dashboard/test_dashboard_error_handling.py
  - Test: Trade log contains invalid JSON → Display account data only with warning
  - Validate: No crash, graceful fallback (FR-015, NFR-002)
  - Pattern: Existing test_corrupted_log_handling() test
  - From: spec.md Edge Cases

- [ ] T097 Verify error log documentation
  - File: specs/019-status-dashboard/error-log.md
  - Validate: Document all handled error scenarios (API failures, missing files, corrupted data)
  - Pattern: Constitution §Safety_First audit requirements
  - From: plan.md [KNOWN ISSUES & LIMITATIONS]

---

## Phase 13: Documentation & Finalization

- [ ] T100 Update implementation notes in NOTES.md
  - File: specs/019-status-dashboard/NOTES.md
  - Content: Final test results, coverage report, performance benchmarks
  - Include: Task completion summary, validation outcomes
  - From: plan.md [NEXT STEPS]

- [ ] T101 Verify README.md or quickstart.md exists
  - File: specs/019-status-dashboard/quickstart.md or README.md
  - Content: Usage instructions, command-line examples, troubleshooting
  - Pattern: plan.md [INTEGRATION SCENARIOS]
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

- [ ] T102 Run final code coverage report
  - Command: pytest --cov=src/trading_bot/dashboard --cov-report=html --cov-report=term
  - Target: ≥90% coverage (NFR-006)
  - Validate: All modules meet coverage threshold
  - From: plan.md [TESTING STRATEGY]

- [ ] T103 Generate final test report
  - Command: pytest --junitxml=test-results.xml --html=test-report.html
  - Validate: All tests passing, no skipped tests without tickets
  - From: plan.md [TESTING STRATEGY]

---

## [TEST GUARDRAILS]

**Speed Requirements:**
- Unit tests: <2s each
- Integration tests: <10s each
- Performance tests: <30s each
- Full suite: <6 min total

**Coverage Requirements:**
- New code: 100% coverage (all dashboard modules are existing code, verify ≥90%)
- Unit tests: ≥90% line coverage
- Integration tests: ≥60% line coverage
- Modified code: Coverage cannot decrease

**Measurement:**
- Python: `pytest --cov=src/trading_bot/dashboard --cov-report=term-missing`
- Coverage enforced in CI (if applicable)

**Quality Gates:**
- All tests must pass before marking complete
- Coverage thresholds enforced (≥90% for dashboard modules)
- No skipped tests without documented reason

**Clarity Requirements:**
- One behavior per test
- Descriptive names: `test_dashboard_displays_stale_indicator_when_data_older_than_60s()`
- Given-When-Then structure in test body

**Anti-Patterns:**
- ❌ NO UI snapshots (not applicable for CLI tool)
- ❌ NO "prop-mirror" tests (test behavior, not implementation)
- ✅ USE explicit assertions on rendered output
- ✅ USE mocks for external dependencies (AccountData, TradeQueryHelper)

**Reference**: `.spec-flow/templates/test-patterns.md` for copy-paste templates
