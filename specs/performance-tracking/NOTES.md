# Feature: Performance tracking

## Overview
- Roadmap feature to add multi-interval trading analytics, alerting, and historical summaries leveraging structured trade logs.
- Builds on trade-logging win-rate helpers and status-dashboard metrics but introduces persistent aggregates and thresholds.

## Feature Classification
- UI screens: false (service layer feeding dashboard/export consumers)
- Improvement: true (extends existing logging data into actionable insights)
- Measurable: true (alerts and KPIs sourced from JSONL trade logs + config targets)
- Deployment impact: true (new scheduled job/CLI command plus config surface)

## Research Findings
**Finding 1**: TradeQueryHelper only exposes ad-hoc win rate helpers  
- Source: src/trading_bot/logging/query_helper.py:23-213  
- Observation: Provides date/symbol filters and single win rate calculation but no rolling windows, aggregates, or alert thresholds.  
- Implication: Performance tracking must wrap this helper (or extend it) with summary pipelines and caching to avoid N² file scans.

**Finding 2**: MetricsCalculator already computes immediate metrics for dashboard refreshes  
- Source: src/trading_bot/dashboard/metrics_calculator.py:19-213  
- Observation: Aggregates streaks, P&L, and max drawdown each poll but it is stateless (no history persisted) and scoped to "right now".  
- Implication: Reuse formulas where possible yet add persistence (daily/weekly/monthly snapshots) so alerts can compare against targets.

**Finding 3**: Dashboard targets config lacks automated alerting hooks  
- Source: src/trading_bot/dashboard/dashboard.py & models.py  
- Observation: Targets influence display/export only; no notifications when metrics fall below thresholds.  
- Implication: Performance tracking should emit structured alert events (logs + optional webhook/email placeholder) and integrate with existing logging.

**Finding 4**: Trade logs live in `logs/YYYY-MM-DD.jsonl` with TradeRecord fields  
- Source: src/trading_bot/logging/trade_record.py:15-161  
- Observation: Rich metadata (net P&L, risk_reward_ratio, timestamps) already captured for each trade.  
- Implication: Analytics should leverage these fields instead of re-fetching external market data; ensure Decimal precision maintained.

## System Components Analysis
- `TradeQueryHelper` (src/trading_bot/logging/query_helper.py): Primary ingestion for trade history; needs batching and memoization for rolling windows.
- `MetricsCalculator` (src/trading_bot/dashboard/metrics_calculator.py): Provides formulas for win rate, streaks, P&L, and drawdown—candidate for refactor into shared analytics core.
- `DashboardTargets` (src/trading_bot/dashboard/models.py): Defines thresholds; performance tracking should centralize comparisons against these targets.
- `ExportGenerator` (src/trading_bot/dashboard/export_generator.py): Produces daily summaries—can be augmented to include new analytics exports.
- `config/dashboard-targets.yaml` (examples/run_dashboard.py references): Input surface for operator-defined goals; may need schema update for alert channels.

## Decisions
- v1 alerting remains log-only (structured events + WARN logs), no external notification channels.

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-10
- Phase 3.1 (Setup & Scaffolding): 2025-10-15

## Implementation Progress

### Batch 1: Setup & Scaffolding (T001-T003) ✅
**Completed**: 2025-10-15

✅ **T001**: Create `performance` package scaffolding
  - Created: `src/trading_bot/performance/__init__.py` (exports PerformanceSummary, AlertEvent)
  - Created: `src/trading_bot/performance/models.py` (dataclasses for PerformanceSummary, AlertEvent)
  - Created: `src/trading_bot/performance/tracker.py` (PerformanceTracker with get_summary stub)
  - Created: `src/trading_bot/performance/cache.py` (cache utilities with stubs)
  - Created: `src/trading_bot/performance/alerts.py` (AlertEvaluator with evaluate stub)
  - Created: `src/trading_bot/performance/cli.py` (argparse CLI with --window, --start, --end, --export, --backfill)
  - Created: `src/trading_bot/performance/__main__.py` (module entrypoint)
  - Evidence: CLI entrypoint functional (`python -m trading_bot.performance --help`)

✅ **T002**: Ensure log directories ignored & documented
  - Verified: `logs/` already in `.gitignore` (line 88) → covers `logs/performance/`
  - Created: `logs/performance/README.md` with structure documentation
  - Evidence: Directory created, documentation in place

✅ **T003**: Add config placeholders for performance env vars
  - Updated: `.env.example` with PERFORMANCE_ALERT_ROLLING_WINDOW=20
  - Updated: `.env.example` with PERFORMANCE_SUMMARY_TIMEZONE=UTC
  - Evidence: Config section added with comments

## Last Updated
2025-10-15T14:30:00+00:00
