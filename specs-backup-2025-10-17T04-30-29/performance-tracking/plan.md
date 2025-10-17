# Implementation Plan: Performance Tracking & Analytics

**Branch**: `performance-tracking`
**Date**: 2025-10-10
**Spec**: `specs/performance-tracking/spec.md`

## Summary

Automate trade performance tracking by building a backend analytics service that reads structured
trade logs, computes rolling daily/weekly/monthly metrics, caches results for fast reuse, exposes a
CLI/API surface for dashboards and operators, and emits log-only alerts when targets fall below
thresholds defined in configuration.

## Technical Context

**Language/Version**: Python 3.11 (per `pyproject.toml`)  
**Dependencies**: Standard library (`datetime`, `decimal`, `json`, `pathlib`), existing `TradeQueryHelper`, `MetricsCalculator`, `PyYAML`, `rich` logging utilities; evaluate `python-dateutil` only if stdlib timezone math proves insufficient.  
**Storage**: File-based artifacts (`logs/performance/*.json`, `logs/performance/*.md`, `logs/performance-alerts.jsonl`), optional cache index file.  
**Testing**: `pytest` via `uv run pytest`, with new unit tests under `tests/performance_tracking/` and integration-style CLI tests.  
**Platform**: Local development + Railway deployment (containerized CLI/cron), logging to mounted volume.  
**Project Type**: Single backend project (`src/`, `tests/`).  
**Performance**: Summaries ≤500 ms (daily) / ≤1.5 s warm weekly / ≤2.5 s cold; alert evaluator <150 ms per run.  
**Constraints**: Maintain Decimal precision, keep cache footprint <5 MB/day, no external network calls.  
**Scale**: Designed for ~1,000 trades/day, rolling windows up to 30 days, alerts evaluated every 60 seconds.

## Constitution Check

**Trading Bot Constitution Alignment**:
- [x] §Safety_First: No live trading mutations; alerts help enforce circuit breakers.
- [x] §Code_Quality: Plan mandates type hints, DRY reuse (TradeQueryHelper, MetricsCalculator) and ≥90% test coverage.
- [x] §Risk_Management: Rolling metrics and alerts reinforce loss limits and duplicate prevention.
- [x] §Security: Outputs remain in logs with no credential exposure; honors config-driven secrets.
- [x] §Data_Integrity: UTC handling, Decimal math, validation of JSONL inputs baked into design.
- [ ] §Audit_Everything follow-up: Add alert + summary schemas to artifacts (planned in FR-009).

## Project Structure

**Documentation** (`specs/performance-tracking/`):
- `plan.md` – This plan.
- `research.md` – To be generated in Phase 0 (reuse vs new analytics patterns).
- `data-model.md`, `quickstart.md`, `contracts/`, `error-log.md` – Produced in subsequent phases.
- `artifacts/` – Store summary + alert schema examples.
- `tasks.md` – Created via `/tasks` after design.

**Source Code**:

```
src/
  trading_bot/
    performance/            # New package (tracker, models, cache, cli)
tests/
  performance_tracking/     # Unit + integration tests
logs/performance/           # Generated artifacts (already gitignored)
```

**Structure Decision**: Option 1 (single backend project) — aligns with existing repository layout.

## Context Engineering Plan

- **Context budget**: Target ≤35k tokens; compact NOTES.md after each major research/design update.
- **Token triage**: Keep spec, plan, NOTES excerpts resident; pull code files (query_helper, metrics_calculator, dashboard models) on demand.
- **Retrieval strategy**: Use `rg` with explicit paths; fetch trade log schema (`trade_record.py`) whenever metrics math evolves.
- **Memory artifacts**: Update `NOTES.md` at the end of each phase; store schema samples and CLI usage in `artifacts/`.
- **Compaction & resets**: Summarize research.md findings; truncate verbose command outputs before sharing.
- **Sub-agent handoffs**: If data analyst agent engaged, provide trade log schema + target config summary; require return payload referencing FR-XXX identifiers.

## Phase 0: Codebase Scan & Research

### Existing Infrastructure – Reuse
- ✅ `TradeQueryHelper` (`src/trading_bot/logging/query_helper.py`) for streaming JSONL ingestion.
- ✅ `MetricsCalculator` (`src/trading_bot/dashboard/metrics_calculator.py`) for core formulas (win rate, streak, P&L, drawdown).
- ✅ `DashboardTargets` & related models (`src/trading_bot/dashboard/models.py`) for target comparison structure.
- ✅ `ExportGenerator` (`src/trading_bot/dashboard/export_generator.py`) for Markdown/JSON rendering patterns.
- ✅ Logging + configuration patterns (`trading_bot.logger`, `config/dashboard-targets.yaml`) already support structured outputs.

### New Infrastructure – Create
- 🆕 `PerformanceTracker` service orchestrating aggregation, caching, and summary generation.
- 🆕 `performance.cache` helper (checksum + incremental window index).
- 🆕 `performance.alerts` evaluator writing to `logs/performance-alerts.jsonl`.
- 🆕 CLI entrypoint `python -m trading_bot.performance` with argparse/Typer-style interface.
- 🆕 Summary + alert schema artifacts (JSON examples) and associated tests.

### Research Focus
- Validate stdlib timezone handling vs `dateutil` for rolling windows; document choice in `research.md`.
- Investigate caching strategies (per-day cache file vs aggregated index) for fast weekly/monthly recompute.
- Define summary/alert JSON schema consistent with existing logging conventions.
- Benchmark TradeQueryHelper streaming performance to ensure NFR-002 feasibility.

**Output**: `research.md` outlining reuse vs new components, cache strategy decision, timezone handling approach, and any dependency evaluations.

## Phase 1: Design & Contracts

### Architecture Decisions
- Layered analytics module (`performance/`) housing tracker, cache, alerts, and CLI interfaces.
- Reuse `TradeQueryHelper` + `MetricsCalculator` underneath to avoid duplicate math; add wrapper logic for rolling windows.
- Maintain log-based persistence (no DB); rely on deterministic filenames + checksums for idempotency.
- Alerts remain internal (log-only) per FR-010; design for future extensibility (publish hook interface).

### Structure
```
src/trading_bot/performance/
  __init__.py
  models.py             # PerformanceSummary, AlertEvent dataclasses
  tracker.py            # PerformanceTracker aggregation API
  cache.py              # Incremental cache utilities
  alerts.py             # AlertEvaluator logic
  cli.py                # CLI command wiring
tests/performance_tracking/
  test_tracker.py
  test_alerts.py
  test_cli.py
```

### Schema
- No DB tables. Define JSON schema documents for summaries (`artifacts/performance-summary.schema.json`) and alerts (`artifacts/performance-alert.schema.json`). Include Markdown export template snippet.

### Performance Targets
- Daily summary ≤500 ms (measure via unit/perf test with synthetic 1k trade file).
- Weekly summary ≤1.5 s warm (cache hit) / ≤2.5 s cold (document measurement).
- Alert evaluator <150 ms per run; ensure loops avoid redundant file scans.

### Security
- Ensure generated files reside under `logs/performance/`.
- Sanitize filenames (slugify window + dates).
- Avoid printing sensitive config details; log high-level metrics only.

### Artifacts Generated
1. `data-model.md` capturing PerformanceSummary + AlertEvent fields and cache metadata.
2. `contracts/performance-summary.schema.json` & `contracts/performance-alert.schema.json`.
3. Failing contract tests (Pytest) verifying schema adherence + CLI interface.
4. `quickstart.md` describing CLI usage (`uv run python -m trading_bot.performance --window daily`) and expected artifacts.

## Phase 2: Task Planning Approach

- **Task Generation Strategy**: Derive tasks from design artifacts—tests first (cache, aggregation, alerts, CLI), followed by implementation steps, configuration updates, docs, and benchmarks.
- **Ordering Strategy**: 
  1. Build models + schemas.
  2. Write failing tests for tracker + alerts.
  3. Implement cache + tracker.
  4. Integrate CLI + logging.
  5. Add documentation + example exports.
- **Estimated Output**: 25–30 tasks; mark analytics vs CLI tasks for potential parallel work.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected |
|-----------|------------|------------------------------|
| _None_ | – | – |

## Progress Tracking

**Phase Gates**:
- [ ] Phase 0: Research complete → `research.md`
- [ ] Phase 1: Design complete → `data-model.md`, `contracts/`, `quickstart.md`
- [ ] Phase 2: Task approach documented → ready for `/tasks`
- [ ] Error ritual entry added after latest failure (not yet applicable)
- [ ] Context plan documented (this plan section complete)

**Quality Gates**:
- [ ] Constitution check finalized post-design
- [ ] All clarifications resolved (FR-010 captured; confirm others during research)
- [ ] Complexity policy reviewed (none so far)
- [ ] Stack alignment validated (reuse existing modules)
- [ ] Testing strategy logged (Pytest suites + benchmarks)
