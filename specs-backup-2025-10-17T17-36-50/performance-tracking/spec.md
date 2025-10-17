# Feature Specification: Performance Tracking & Analytics

**Branch**: `performance-tracking`
**Created**: 2025-10-10
**Status**: Draft
**Area**: infra
**From Roadmap**: Yes (Impact: 4, Effort: 2, Confidence: 1.0, Score: 2.00)

## User Scenarios

### Primary User Story
As a trading bot operator, I need automated performance tracking that summarizes daily, weekly, and
monthly results, compares them to my targets, and alerts me when I fall behind so I can react
without manually combing through JSONL logs.

### Acceptance Scenarios
1. **Given** trades are logged throughout the session, **When** the daily summary job runs at market
   close, **Then** it produces `logs/performance/2025-10-10-summary.json` and `.md` files containing
   win rate, total wins/losses, streak, average win/loss, risk-reward ratio, and P&L for the day.
2. **Given** I invoke `uv run python -m trading_bot.performance --window weekly`, **When** seven days
   of trade records exist, **Then** the CLI prints aggregated metrics (win rate, average R:R, avg
   win/loss values, trades executed) and highlights variance against configured targets.
3. **Given** my configured minimum win rate target is 60%, **When** the current rolling 20-trade win
   rate drops to 55%, **Then** the system emits a structured alert event (`performance.alert`) to
   `logs/performance-alerts.jsonl` with context (window, metric, actual, target) and surfaces a WARN
   log entry for the operator console.
4. **Given** the current average risk-reward ratio falls below 1.0 for the last 10 closed trades,
   **When** the alert evaluator runs, **Then** it raises a `risk_reward_breach` alert and the CLI
   command returns exit code 2 to signal degraded performance.
5. **Given** a weekly summary already exists, **When** new trades are logged mid-week, **Then** the
   next refresh reuses cached aggregates but recomputes only the incremental day, keeping refresh
   latency under 300 ms for 1,000 trade records.
6. **Given** no trades were executed during the selected window, **When** the summary is generated,
   **Then** metrics fall back to zeros, alerts are suppressed, and the report records "No trades in
   window" instead of failing.

### Edge Cases
- What happens when log files are missing or partially written? → Skip missing days, log warning,
  mark report as partial but keep processing remaining records.
- How are timezone boundaries handled for daily/weekly windows? → Normalize timestamps to UTC and
  treat trading days as 00:00-23:59 UTC with configurable market timezone offset.
- What happens if Decimal fields are stored as strings? → Convert back to Decimal before arithmetic
  to prevent float rounding errors.
- How are open trades treated? → Exclude from win/loss metrics but include in unrealized P&L totals.
- How do we prevent duplicate summaries? → Idempotent job writes by overwriting same-day files only
  if source logs changed (checksum comparison).

## Visual References

N/A – backend analytics feature (no UI components).

## Success Metrics (HEART Framework)

> **Purpose**: Define quantified success criteria using Google's HEART framework.  
> **Constraint**: All metrics MUST be Claude Code-measurable (SQL, logs, Lighthouse).

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Reduce manual log crunching | Summary generation feedback | Operator survey in `performance-alerts.jsonl` (ack events) | ≥80% positive | <60% triggers UX review |
| **Engagement** | Encourage routine performance reviews | CLI/automation usage | `performance.summary_generated` events per week | ≥10/week | <5/week triggers reminder |
| **Adoption** | Make summaries the canonical source | Dashboard pulls using new API | `dashboard.performance_fetch` rate vs manual jq scripts | ≥90% automated | <75% triggers enablement |
| **Retention** | Sustain alert responsiveness | Alert acknowledge latency | Median time from alert to ack | ≤15 min | P95 ≤30 min |
| **Task Success** | Deliver summaries quickly | Summary duration in logs | `generation_duration_ms` per window | ≤500 ms (daily) | P95 ≤750 ms |

**Performance Targets**:
- Daily summary generation ≤500 ms for 1,000 trades (streaming JSONL read).
- Weekly/monthly summary ≤1.5 s with cache warm, ≤2.5 s cold.
- Alert evaluation loop runs every 60 s with <150 ms execution time.
- Storage footprint for derived metrics <5 MB/day (JSON + Markdown).

## Hypothesis

**Problem**: Operators currently rely on manual jq/grep scripts to compute win rate, streaks, and P&L,
consuming 10-15 minutes per session and delaying reactions to performance slumps.
- Evidence: trade-logging spec highlights manual log parsing (specs/trade-logging/spec.md:22-47).
- Evidence: status-dashboard shows metrics only for "now" without historical context or alerts.
- Impact: Missed drawdowns and slow interventions reduce profitability and increase risk.

**Solution**: Introduce a performance analytics service that aggregates trade logs into persistent
daily/weekly/monthly summaries, exposes a CLI/API for consumers, and emits alerts when targets are
breached.
- Change: New `trading_bot.performance` package with summary builder, alert evaluator, and storage.
- Mechanism: Reuse TradeQueryHelper + MetricsCalculator formulas, layer caching, and alert targets.

**Prediction**: Automated summaries will cut daily performance review effort from ~12 minutes to <1
minute and reduce average alert response time to ≤15 minutes for 90% of incidents.
- Primary metric: Median manual analysis time (self-reported) drops by 90%.
- Expected improvement: -90% manual effort, -70% alert response time.
- Confidence: Medium (depends on operator adoption + alert routing).

## Context Strategy & Signal Design

- **System prompt altitude**: Service-level specification focused on analytics workflows and alerting
  contracts to guide backend implementation.
- **Tool surface**: Python analytics (TradeQueryHelper, MetricsCalculator), structured logging, and
  CLI entrypoints via `uv run python -m trading_bot.performance`.
- **Examples in scope**: (1) Daily summary generation, (2) Weekly alert breach log, (3) Dashboard
  integration fetching cached metrics.
- **Context budget**: Target ≤35k tokens for implementation discussions; compact NOTES.md after each
  major research block.
- **Retrieval strategy**: Pull TradeRecord schemas and dashboard models on demand; avoid loading full
  roadmap once spec finalized.
- **Memory artifacts**: Use NOTES.md for findings/decisions; store summary format samples in
  `artifacts/`.
- **Compaction cadence**: Summarize progress every 3-4 turns during implementation to control tokens.
- **Sub-agents**: Optional data analyst sub-agent to validate aggregation formulas before coding.

## Requirements

### Functional (testable only)

- **FR-001**: System MUST aggregate trade metrics for daily, weekly, and monthly windows using UTC
  boundaries and TradeRecord data.
- **FR-002**: System MUST compute total wins, total losses, win rate, current streak, average profit
  per win, and average loss per loss for each window.
- **FR-003**: System MUST calculate average risk-reward ratio for each window and flag when <1.0.
- **FR-004**: System MUST persist summaries to `logs/performance/{window}-summary-YYYY-MM-DD.json`
  and `.md`, overwriting safely when recomputed.
- **FR-005**: System MUST expose a CLI command (`python -m trading_bot.performance`) with options
  `--window`, `--start`, `--end`, and `--export` to generate or display summaries on demand.
- **FR-006**: System MUST emit structured alert events (`performance.alert`) when win rate or average
  risk-reward fall below targets defined in configuration.
- **FR-007**: System MUST provide an API (e.g., `PerformanceTracker.get_summary(window)`) that returns
  cached metrics for reuse by the dashboard without re-reading JSONL files.
- **FR-008**: System MUST maintain incremental caches (e.g., `performance-index.json`) to avoid full
  rescans when generating rolling windows larger than one day.
- **FR-009**: System MUST document schema for summary/alert outputs in `specs/performance-tracking/artifacts/`.
- **FR-010**: Alerts MUST remain log-only in v1, emitting structured events and WARN log entries without external channel integrations.

### Non-Functional

- **NFR-001**: Accuracy: Metrics MUST match manual calculations within 0.01 for win rate and 0.001
  for risk-reward ratios (validated via tests).
- **NFR-002**: Performance: Daily summary generation MUST complete ≤500 ms for 1,000 trades on the
  reference dev machine (Intel i7 / SSD).
- **NFR-003**: Reliability: Summary generation MUST be idempotent and safe to run multiple times per
  day without producing duplicate artifacts.
- **NFR-004**: Observability: All summaries and alerts MUST log duration, trade count processed, and
  cache hits/misses to `trading_bot.logger`.
- **NFR-005**: Maintainability: Module MUST include unit tests covering aggregation math, alert
  thresholds, and CLI parsing with ≥90% coverage.
- **NFR-006**: Security: Summaries MUST not leak credentials; paths restricted to `logs/performance`.

### Key Entities (if data involved)

- **PerformanceSummary**: Aggregated metrics per window (daily/weekly/monthly) including counts,
  win rate, streak, avg win/loss, average risk-reward, realized/unrealized P&L, and alert statuses.
- **AlertEvent**: Structure with fields (`id`, `window`, `metric`, `actual`, `target`, `severity`,
  `raised_at`, `acknowledged_at`).
- **RollingWindowCache**: Metadata on JSONL files processed, `last_offset`, and `checksum` to support
  incremental updates.

## Deployment Considerations

> **Purpose**: Document deployment constraints and dependencies for planning phase.

### Platform Dependencies

**Vercel** (marketing/app): None (backend-only feature).

**Railway** (API): Possible scheduled job runner or cron entry; ensure container has write access to
`/app/logs/performance`.

**Dependencies**:
- Optional: evaluate `pendulum` or `python-dateutil` for timezone-aware window partitioning. Default
  plan is to rely on stdlib `datetime`.

### Environment Variables

**New Required Variables**:
- `PERFORMANCE_ALERT_ROLLING_WINDOW` (default 20 trades) – controls alert window size.
- `PERFORMANCE_SUMMARY_TIMEZONE` (default `UTC`) – timezone for daily cutoffs.

**Changed Variables**:
- None (targets pulled from existing `config/dashboard-targets.yaml`, may require new fields).

**Schema Update Required**: Yes – extend `config/dashboard-targets.yaml` schema to include
`alert_channels` (optional) and `min_avg_win`/`max_avg_loss` thresholds if required in implementation.

### Breaking Changes

**API Contract Changes**: No external API changes; new internal service only.

**Database Schema Changes**: No database; file-based outputs only.

**Auth Flow Modifications**: None.

**Client Compatibility**: Backward compatible; dashboard consumers get new optional API.

### Migration Requirements

**Database Migrations**: Not applicable.

**Data Backfill**: Required – provide CLI flag `--backfill N` to rebuild summaries for the last `N`
days using existing JSONL logs.

**RLS Policy Changes**: Not applicable.
