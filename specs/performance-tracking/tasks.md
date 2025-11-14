# Tasks: Performance Tracking & Analytics

## [CODEBASE REUSE ANALYSIS]

Scanned: `src/trading_bot/logging/*.py`, `src/trading_bot/dashboard/*.py`, `tests/**`, `logs/`

### [EXISTING - REUSE]
- ✅ `TradeQueryHelper` (`src/trading_bot/logging/query_helper.py`) – Streaming JSONL ingestion & Decimal restoration
- ✅ `MetricsCalculator` (`src/trading_bot/dashboard/metrics_calculator.py`) – Win rate, streak, P&L computations
- ✅ `DashboardTargets` & models (`src/trading_bot/dashboard/models.py`) – Target comparison structures
- ✅ `ExportGenerator` (`src/trading_bot/dashboard/export_generator.py`) – JSON/Markdown export patterns
- ✅ `trading_bot.logger` (`src/trading_bot/logger.py`) – Structured logging + file rotation
- ✅ Config targets template (`config/dashboard-targets.yaml`) – Existing operator-defined thresholds

### [NEW - CREATE]
- 🆕 `src/trading_bot/performance/` package (tracker, cache, alerts, CLI)
- 🆕 Summary/alert schema artifacts (`specs/performance-tracking/artifacts/`)
- 🆕 `logs/performance/` persistence pattern & index file
- 🆕 `tests/performance_tracking/` test suite covering tracker, alerts, CLI, cache

---

## Phase 3.1: Setup & Scaffolding

### T001 [P] Create `performance` package scaffolding
- Files: `src/trading_bot/performance/__init__.py`, `models.py`, `tracker.py`, `cache.py`, `alerts.py`, `cli.py`
- Export dataclasses (`PerformanceSummary`, `AlertEvent`) from `__init__.py`
- Reference: structure from `src/trading_bot/dashboard/__init__.py`

### T002 [P] Ensure log directories ignored & documented
- Confirm `logs/performance/` path in `.gitignore`; add README stub under `logs/performance/` if missing
- Document operator instructions in `specs/performance-tracking/NOTES.md` “Logs” section

### T003 [P] Add config placeholders for performance env vars
- Update `config/config.example.json` (if applicable) & `docs` references with `PERFORMANCE_ALERT_ROLLING_WINDOW`, `PERFORMANCE_SUMMARY_TIMEZONE`
- Include guidance in README/QUICKSTART if needed

---

## Phase 3.2: RED – Write Failing Tests & Contracts

### T004 [RED] Add schemas + fixtures for summaries/alerts
- Create `specs/performance-tracking/artifacts/performance-summary.schema.json`
- Create `specs/performance-tracking/artifacts/performance-alert.schema.json`
- Provide example JSON in `artifacts/examples/`

### T005 [RED] Test: Daily summary aggregation (1-day window)
- File: `tests/performance_tracking/test_tracker.py`
- Cases: mix of wins/losses, open trades excluded, Decimal precision
- Expected: Metrics match manual calculation; file not written yet (dry run)

### T006 [RED] Test: Weekly summary aggregation uses caches
- File: `tests/performance_tracking/test_tracker.py`
- Arrange: Pre-populate cache index; assert recompute touches only delta files (mock file stats)
- Covers: FR-001, FR-008 performance

### T007 [RED] Test: Monthly summary handles missing days gracefully
- File: `tests/performance_tracking/test_tracker.py`
- Expect: Warning logged, summary flagged partial, continues processing

### T008 [RED] Test: Alert evaluator triggers win rate breach
- File: `tests/performance_tracking/test_alerts.py`
- Inputs: Summary < target; expect alert event emitted + WARN log
- Verify JSONL structure matches schema

### T009 [RED] Test: Alert evaluator suppresses when above targets
- File: `tests/performance_tracking/test_alerts.py`
- Ensure no alert emitted; coverage for FR-006 guardrail

### T010 [RED] Test: CLI `--window daily` generates summary & export files
- File: `tests/performance_tracking/test_cli.py`
- Use `tmp_path` for logs; assert exit code 0, JSON/MD files created, console output summary

### T011 [RED] Test: CLI `--backfill 7` rebuilds missing summaries
- File: `tests/performance_tracking/test_cli.py`
- Validate calls tracker for each day, respects cache skip

### T012 [RED] Test: API `PerformanceTracker.get_summary(window)` caches results
- File: `tests/performance_tracking/test_tracker.py`
- Scenario: Call twice; second call uses cached data without re-reading files (mock TradeQueryHelper)

### T013 [RED] Test: Incremental cache index persists checksums
- File: `tests/performance_tracking/test_cache.py`
- Validate read/write of index file, checksum detection, and stale file invalidation

### T014 [RED] Test: Markdown export formatting for summaries
- File: `tests/performance_tracking/test_export.py`
- Ensure Markdown includes sections (Overview, Metrics, Alerts) and table formatting

### T015 [RED] Test: Schema validation of generated JSON summaries
- File: `tests/performance_tracking/test_contracts.py`
- Validate JSON output against schema using `jsonschema` (add dev dependency if required)

---

## Phase 3.3: GREEN – Implement to Satisfy Tests

### T016 [GREEN->T005/T006/T007/T012] Implement `PerformanceTracker`
- Responsibilities: ingest logs via TradeQueryHelper, compute metrics with MetricsCalculator, build `PerformanceSummary`, manage cache interactions
- Include UTC window calculations & timezone override

### T017 [GREEN->T013] Implement cache utilities
- Functions: `load_index()`, `update_index()`, `needs_refresh(file_path, checksum)`
- Ensure atomic writes (temp file rename) to avoid corruption

### T018 [GREEN->T008/T009] Implement `AlertEvaluator`
- Compare summaries vs targets, write JSONL event, emit WARN log
- Support rolling window size from env/config; ensure log-only delivery (FR-010)

### T019 [GREEN->T010/T011] Implement CLI entrypoint
- Parse args (`--window`, `--start`, `--end`, `--export`, `--backfill`)
- Hook into tracker + alerts; exit codes (0 success, 2 alert breach)
- Register module in `src/trading_bot/performance/__main__.py`

### T020 [GREEN->T014/T015] Implement exports for performance summaries
- Reuse/adapt `ExportGenerator` logic or create `PerformanceExporter`
- Output JSON + Markdown to `logs/performance/` with deterministic filenames

### T021 [GREEN->T004] Wire schemas & artifact generation
- Provide function to write schema examples during implementation
- Update plan/spec references with artifact paths

---

## Phase 3.4: REFACTOR, POLISH & OBSERVABILITY

### T022 [P] Integrate logging hooks & duration metrics
- Add structured logs for summary generation duration, trade count, cache hits/misses (NFR-004)
- Ensure log format respects existing logger conventions

### T023 [P] Update configuration documentation
- Docs: README, `docs/dashboard-orchestration-implementation.md`, new section in `docs/commands.md`
- Include CLI usage examples and environment variable description

### T024 [P] Add sample exports to artifacts
- Generate anonymized sample JSON & Markdown (`artifacts/examples/`)
- Reference in spec + NOTES for QA

### T025 [P] Verify coverage & linting
- Run `uv run pytest tests/performance_tracking`
- Ensure coverage ≥90% for new module; add to coverage config if needed
- Run `uv run ruff check src/trading_bot/performance tests/performance_tracking`

### T026 [P] Update NOTES & plan with implementation progress
- Log key decisions, cache strategy confirmation, performance benchmark results in `NOTES.md`
- Mark Phase gates in `plan.md` progress section

### T027 [P] Prepare optimization follow-ups
- Identify potential future work (external alert channels, DB storage) in `optimization-report.md`
- Capture any residual risks or tech debt tickets

---

## Phase 3.5: Validation & Handoff

### T028 [P] Manual dry run
- Execute CLI against synthetic log dataset (include script in `artifacts/`)
- Verify JSON/MD outputs, alert behavior, logging entries

### T029 [P] Update release artifacts
- Document command in `/preview` readiness checklist if needed
- Ensure roadmap entry moved to “In Progress” → update `.spec-flow/memory/roadmap.md` (if required by workflow)

### T030 [P] Handoff checklist
- Confirm tasks ready for `/implement`
- Ensure research/plan/tasks all reference final schemas & CLI usage
- Notify QA agent path (tests to execute, sample data)
