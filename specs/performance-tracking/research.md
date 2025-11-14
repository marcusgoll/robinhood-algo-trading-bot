# Research Brief: Performance Tracking & Analytics

**Date**: 2025-10-10  
**Feature**: `performance-tracking`  
**Spec**: `specs/performance-tracking/spec.md`

## Objectives

- Validate existing analytics infrastructure (TradeQueryHelper, MetricsCalculator) as foundations for
  automated performance tracking.
- Define caching and windowing approach that keeps summary generation under required latency caps.
- Confirm alert delivery scope (log-only) and identify reuse points for structured logging.
- Document dependencies, risks, and measurement strategy ahead of design contracts.

## Existing Capabilities (Reuse)

| Asset | Path | Relevance |
|-------|------|-----------|
| `TradeQueryHelper` | `src/trading_bot/logging/query_helper.py` | Streams JSONL trade logs with date and symbol filters; ideal ingestion layer for summaries. |
| `MetricsCalculator` | `src/trading_bot/dashboard/metrics_calculator.py` | Implements win rate, streak, risk-reward, drawdown, and P&L calculations; can be wrapped for windowed analytics. |
| `DashboardTargets` & related models | `src/trading_bot/dashboard/models.py` | Data structures for operator-defined targets; integrate directly with alert evaluator. |
| `ExportGenerator` | `src/trading_bot/dashboard/export_generator.py` | Markdown/JSON export pattern we can adapt for daily/weekly/monthly summaries. |
| Logging infrastructure | `src/trading_bot/logger.py` | Provides structured logging + log file locations (`logs/` hierarchy). |
| Target configuration | `config/dashboard-targets.yaml` | Existing config surface with win rate, drawdown, and P&L targets. |

## Gaps & Requirements

1. **Rolling Window Aggregation**
   - Need ability to aggregate per window (daily | weekly | monthly) without re-reading entire trade
     history each time.
   - Solution direction: Maintain lightweight cache index (file checksums, last processed offsets per
     day) under `logs/performance/performance-index.json`.

2. **Summary Persistence**
   - Requirement to emit JSON + Markdown summaries per window. `ExportGenerator` handles formatting
     but expects dashboard snapshot data models.
   - Plan: Introduce `PerformanceSummary` dataclass and adapt export generator for analytics context.

3. **Alert Evaluation**
   - Alerts must trigger when metrics fall below targets. Currently no module encapsulates this.
   - Implement `AlertEvaluator` that compares summaries against targets and writes to
     `logs/performance-alerts.jsonl` (log-only per FR-010).

4. **Timezone Handling**
   - TradeRecord timestamps stored as ISO (UTC/Z). Daily windows should default to UTC but allow
     configurable timezone offset for local trading sessions.
   - Approach: Use stdlib `datetime` with `timezone.utc` plus optional `zoneinfo` if operator sets
     `PERFORMANCE_SUMMARY_TIMEZONE`. No third-party dependency required initially.

5. **Backfill & CLI Experience**
   - Need CLI tool for generating summaries on demand (`python -m trading_bot.performance`), with
     backfill/fetch/export options.
   - Evaluate Typer vs argparse; prefer argparse to avoid new dependency (aligns with existing CLI
     patterns in repo).

## Caching Strategy Evaluation

- **Option A: Per-window recompute only** – Simple but violates NFR for weekly/monthly when trade
  volume grows; rejected.
- **Option B: Rolling daily aggregates stored as JSON** – Each day summary stored once; weekly/monthly
  recombine per-day summaries (fast). Chosen approach.
- **Option C: SQLite/embedded DB** – Overkill for current scale; introduces new dependency.

Chosen plan: Maintain one JSON file per day with core aggregates (counts, sums), enabling weekly and
monthly summaries via simple accumulation plus recalculation of rate-based metrics. Store metadata in
`performance-index.json` to detect when a daily file needs refresh.

## Performance Benchmarks

- Trade logs ~1,000 entries/day (estimated from roadmap). Streaming read via TradeQueryHelper in
  local tests: ~15 ms / 1,000 trades (observed in T029 benchmark). 
- Aggregations largely arithmetic on Decimal fields; weekly 7-day summary should stay <350 ms if
  composed from precomputed daily aggregates.
- Backfill worst-case: 30 days × 1,000 trades ≈ 30k records; streaming read ~0.5 s; acceptable for
  cold backfill.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Missing or corrupted daily log files | Alerts/summary gaps | Log warning, mark summary partial, continue processing remaining files. |
| Decimal serialization errors | Incorrect metrics | Use `Decimal` restoration logic from TradeQueryHelper, ensure tests cover conversions. |
| Configuration drift (new targets) | Alert misfires | Validate config schema on load; log explicit message when fields missing. |
| Cache staleness | Outdated metrics | Include checksums + last modified timestamps; refresh when source file hash changes. |

## Open Questions

- None. All clarifications resolved (alerts remain log-only in v1).

## Next Steps

1. Draft `data-model.md` using findings above (PerformanceSummary, AlertEvent, DailyAggregate).
2. Design cache + alert contracts in `contracts/` directory.
3. Prepare `quickstart.md` outlining CLI usage scenarios and expected outputs.
