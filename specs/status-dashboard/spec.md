# Feature Specification: CLI Status Dashboard & Performance Metrics

**Branch**: `status-dashboard`
**Created**: 2025-10-09
**Status**: Draft

## User Scenarios

### Primary User Story
As a trading bot operator, I need a real-time CLI dashboard displaying account status, current positions, and performance metrics so I can quickly assess session health, identify opportunities, and ensure I'm meeting performance targets without manually querying logs or APIs.

### Acceptance Scenarios

1. **Given** the bot is running and authenticated, **When** I run `python -m trading_bot.dashboard`, **Then** the CLI displays current buying power, account balance, open positions with P&L, and today's performance metrics refreshed every 5 seconds

2. **Given** I have open positions, **When** the dashboard refreshes, **Then** I see each position's symbol, quantity, entry price, current price, unrealized P&L ($), and P&L percentage (%) with color coding (green for profit, red for loss)

3. **Given** I've executed trades today, **When** I view performance metrics, **Then** I see win rate, average risk-reward ratio, total P&L (realized + unrealized), current win/loss streak, trades executed today, and total session count

4. **Given** I've configured performance targets, **When** the dashboard displays metrics, **Then** I see actual values compared to targets with variance indicators (e.g., "Win Rate: 65% [Target: 60%] ✓")

5. **Given** I want to export today's summary, **When** I press `E` key, **Then** the dashboard exports a JSON file and Markdown report with timestamp, all metrics, position snapshots, and target comparisons to `logs/dashboard-export-YYYY-MM-DD.{json,md}`

6. **Given** the account data becomes stale (>60s), **When** the dashboard displays data, **Then** a staleness indicator appears (e.g., "Last updated: 45s ago") to avoid acting on outdated information

### Edge Cases

- What happens when no positions are open?
  - Display "No open positions" with account cash balance and buying power only
- What happens when no trades executed today?
  - Show 0 trades today, display cumulative stats from trade history
- What happens if trade log file is missing or corrupted?
  - Gracefully handle error, display account data only, show warning message
- What happens during market hours vs after hours?
  - Display market status indicator (OPEN/CLOSED based on current time)
- What happens if targets file is missing?
  - Display metrics without target comparison, log warning about missing config
- What happens if account data API call fails?
  - Display cached data with stale indicator, retry on next refresh cycle

## Visual References

N/A - No web UI components (CLI-only feature using `rich` library for terminal rendering)

## Success Metrics (HEART Framework)

> **Purpose**: Define quantified success criteria using Google's HEART framework.
> **Constraint**: All metrics MUST be Claude Code-measurable (SQL, logs, Lighthouse).

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Reduce frustration from manual status checks | Dashboard launch frequency | Daily dashboard sessions | 5+ sessions/day | Min 3/day |
| **Engagement** | Increase monitoring of trading performance | Session duration | Avg time viewing dashboard | 2-5 min/session | <10 min (not distracting) |
| **Adoption** | Replace manual log parsing | % of trading days using dashboard | Dashboard usage rate | 90% of trading days | Min 70% |
| **Retention** | Maintain dashboard as primary monitoring tool | Consecutive days of usage | 7-day usage retention | 80% weekly use | Min 50% |
| **Task Success** | Enable quick session health assessment | Time to answer "Am I meeting targets?" | Time-to-insight | <10 seconds | P95 <15s |

**Performance Targets** (from `design/systems/budgets.md`):
- Dashboard startup: <2 seconds (cold start)
- Refresh cycle: <500ms (account data + trade log read)
- Export generation: <1 second
- Memory footprint: <50MB (long-running CLI tool)

See `.spec-flow/templates/heart-metrics-template.md` for full measurement plan.

## Screens Inventory (UI Features Only)

N/A - No UI screens (CLI-only feature)

## Hypothesis

> **Purpose**: State the problem, solution, and predicted improvement.
> **Format**: Problem → Solution → Prediction (with magnitude)

**Problem**: Bot operators manually check account status via multiple API calls and parse trade logs using grep/jq to assess session performance, taking 3-5 minutes per check and performed 5-10 times per trading day
- Evidence: No unified monitoring tool, manual queries documented in trade-logging spec (15-20 min daily analysis)
- Impact: Context switching disrupts focus, delayed reaction to performance issues
- Gap: Cannot quickly answer "Am I meeting targets today?" or "What's my current risk exposure?"

**Solution**: Real-time CLI dashboard aggregating account data, position P&L, and performance metrics with target comparison in single view
- Change: Unified dashboard replaces manual API calls and log queries
- Mechanism: Polls account-data-module (leveraging 60s cache) and reads trade logs, displays in formatted sections with color coding
- Components: DashboardDisplay (rich rendering), MetricsCalculator (performance stats), TargetComparison (variance analysis), ExportGenerator (daily summaries)

**Prediction**: Unified dashboard will reduce session health assessment time from 3-5 minutes to <10 seconds
- Primary metric: Time-to-insight <10s (currently 3-5 minutes)
- Expected improvement: -96% reduction in assessment time
- Confidence: High (eliminates manual context assembly, industry-standard CLI dashboard pattern)

## Context Strategy & Signal Design

- **System prompt altitude**: Feature-level - "Build CLI dashboard displaying account + performance metrics"
- **Tool surface**: `rich` library for CLI rendering, account-data-module API, trade log file reader
- **Examples in scope**: 3 canonical examples (positions table, metrics panel, export output)
- **Context budget**: <15k tokens (moderate complexity: data aggregation + formatting + live refresh)
- **Retrieval strategy**: JIT - Load account data and trade logs on each refresh cycle, no persistent state
- **Memory artifacts**: NOTES.md updated after implementation, no TODO tracking (single-phase feature)
- **Compaction cadence**: Not needed (moderate feature scope)
- **Sub-agents**: Not used (cohesive single-purpose tool)

## Requirements

### Functional (testable only)

- **FR-001**: System MUST display account status section with: buying power, account balance (cash + positions), day trade count, last update timestamp
- **FR-002**: System MUST display positions section with table columns: Symbol, Quantity, Entry Price, Current Price, P&L ($), P&L (%), sorted by P&L descending
- **FR-003**: System MUST display performance metrics section with: win rate (%), avg risk-reward ratio, total P&L (realized + unrealized), current streak (wins/losses), trades today (count), session count (total trading days)
- **FR-004**: System MUST refresh display every 5 seconds automatically, showing "Refreshing..." indicator during data fetch
- **FR-005**: System MUST load performance targets from `config/dashboard-targets.yaml` if present, comparing actual vs target for: win_rate, daily_pl, trades_per_day, max_drawdown
- **FR-006**: System MUST provide keyboard controls: `R` (manual refresh), `E` (export daily summary), `Q` (quit), `H` (help overlay)
- **FR-007**: System MUST export daily summary when `E` pressed, generating both JSON (`logs/dashboard-export-YYYY-MM-DD.json`) and Markdown (`logs/dashboard-export-YYYY-MM-DD.md`) files
- **FR-008**: System MUST color-code P&L values (green for positive, red for negative, yellow for zero) and target comparisons (green if meeting target, red if not)
- **FR-009**: System MUST display market status indicator (OPEN/CLOSED) based on current time (9:30 AM - 4:00 PM ET, Mon-Fri)
- **FR-010**: System MUST show data staleness indicator when last account data fetch >60 seconds ago (e.g., "⚠️ Data may be stale: last updated 75s ago")
- **FR-011**: System MUST calculate win rate from trade logs: (winning trades / total closed trades) × 100
- **FR-012**: System MUST calculate average R:R from trade logs: average of (target - entry) / (entry - stop_loss) for all trades with risk_params
- **FR-013**: System MUST calculate total P&L as: sum of realized P&L from closed trades (action=SELL) + sum of unrealized P&L from current positions
- **FR-014**: System MUST calculate current streak: consecutive wins or losses from most recent closed trades
- **FR-015**: System MUST handle missing trade log gracefully: display account data only with warning message "Trade log not found, performance metrics unavailable"
- **FR-016**: System MUST handle missing targets file gracefully: display metrics without target comparison, log warning once

### Non-Functional

- **NFR-001**: Performance: Dashboard startup <2s (cold start), refresh cycle <500ms
- **NFR-002**: Reliability: Dashboard must not crash on API errors, stale data, or missing files (graceful degradation)
- **NFR-003**: Usability: Display must fit standard terminal (80x24 minimum) with responsive layout for larger sizes
- **NFR-004**: Data Integrity: All timestamps in UTC (Constitution §Data_Integrity), display in local time with timezone indicator
- **NFR-005**: Type Safety: All functions must use type hints (Constitution §Code_Quality)
- **NFR-006**: Test Coverage: ≥90% code coverage for dashboard logic (Constitution §Testing_Requirements)
- **NFR-007**: Auditability: Log all export events with timestamp and file paths (Constitution §Audit_Everything)
- **NFR-008**: Memory Efficiency: Dashboard process <50MB memory footprint for long-running sessions

### Key Entities (if data involved)

- **AccountStatus**: Current account snapshot
  - Purpose: Display real-time account health
  - Key attributes: buying_power (Decimal), account_balance (Decimal), cash_balance (Decimal), day_trade_count (int), last_updated (datetime)
  - Relationships: Fetched from AccountData module

- **PositionDisplay**: Position with calculated P&L for display
  - Purpose: Show current holdings with profit/loss
  - Key attributes: symbol (str), quantity (int), entry_price (Decimal), current_price (Decimal), unrealized_pl (Decimal), unrealized_pl_pct (Decimal)
  - Relationships: Derived from AccountData.get_positions()

- **PerformanceMetrics**: Aggregated trading performance
  - Purpose: Track trading effectiveness
  - Key attributes: win_rate (float), avg_risk_reward (float), total_realized_pl (Decimal), total_unrealized_pl (Decimal), current_streak (int), streak_type (Literal["WIN", "LOSS"]), trades_today (int), session_count (int)
  - Relationships: Calculated from trade logs (trades-structured.jsonl)

- **DashboardTargets**: Performance targets for comparison
  - Purpose: Define success criteria for trading
  - Key attributes: win_rate_target (float), daily_pl_target (Decimal), trades_per_day_target (int), max_drawdown_target (Decimal)
  - Relationships: Loaded from config/dashboard-targets.yaml

## Deployment Considerations

> **Purpose**: Document deployment constraints and dependencies for planning phase.
> **Skip if**: Purely cosmetic UI changes or documentation-only changes.

### Platform Dependencies

**Vercel** (marketing/app): None

**Railway** (API): None

**Dependencies**:
- New: `rich==13.7.0` (CLI rendering, tables, panels, live refresh)
- Existing: Uses account-data-module (already in codebase)
- Existing: Reads trade logs from trade-logging module (already in codebase)

### Environment Variables

**New Required Variables**: None

**Changed Variables**: None

**Schema Update Required**: No

### Breaking Changes

**API Contract Changes**: No

**Database Schema Changes**: No (file-based only)

**Auth Flow Modifications**: No

**Client Compatibility**: Not applicable (standalone CLI tool)

### Migration Requirements

**Database Migrations**: Not applicable

**Data Backfill**: Not required

**RLS Policy Changes**: Not applicable

**Reversibility**: Fully reversible - can remove dashboard module without affecting other components

### Rollback Considerations

**Standard Rollback**: Yes - 3-command rollback via runbook/rollback.md

**Special Rollback Needs**: None - dashboard is read-only (no data mutations), removal has no side effects

**Deployment Metadata**: Deploy IDs tracked in specs/status-dashboard/NOTES.md (Deployment Metadata section)

---

## Measurement Plan

> **Purpose**: Define how success will be measured using Claude Code-accessible sources.
> **Sources**: SQL queries, structured logs, Lighthouse CI, database aggregates.

### Data Collection

**Analytics Events** (dual instrumentation):
- PostHog (dashboards): Not applicable (internal CLI tool, no user-facing web analytics)
- Structured logs (Claude measurement): All usage metrics logged to `logs/dashboard-usage.jsonl`
- Database (A/B tests): Not applicable

**Key Events to Track**:
1. `dashboard.launched` - Dashboard startup (timestamp, user)
2. `dashboard.refreshed` - Manual refresh via `R` key (timestamp)
3. `dashboard.exported` - Daily summary export via `E` key (timestamp, file_path)
4. `dashboard.session_duration` - Time from launch to quit (duration_seconds)
5. `dashboard.error` - Any errors during operation (error_type, context)

### Measurement Queries

**Logs** (`logs/dashboard-usage.jsonl`):

```bash
# Daily dashboard sessions
jq -r 'select(.event == "dashboard.launched") | .timestamp' logs/dashboard-usage.jsonl | \
  cut -d'T' -f1 | sort | uniq -c

# Average session duration
jq -r 'select(.event == "dashboard.session_duration") | .duration_seconds' logs/dashboard-usage.jsonl | \
  awk '{sum+=$1; count++} END {print sum/count " seconds avg"}'

# Export frequency
jq -r 'select(.event == "dashboard.exported")' logs/dashboard-usage.jsonl | wc -l

# Error rate
jq -s 'map(select(.event == "dashboard.error")) | length' logs/dashboard-usage.jsonl

# Usage retention (7-day)
# Count unique days with dashboard.launched in last 7 days
jq -r 'select(.event == "dashboard.launched") | .timestamp' logs/dashboard-usage.jsonl | \
  cut -d'T' -f1 | sort -u | tail -7 | wc -l
```

**Dashboard Performance** (log timestamps):
```bash
# Startup time (dashboard.launched to first dashboard.refreshed)
jq -r 'select(.event == "dashboard.launched" or .event == "dashboard.refreshed")' logs/dashboard-usage.jsonl | \
  jq -s 'group_by(.session_id) | map({startup: .[1].timestamp - .[0].timestamp})'

# Refresh cycle time
jq -r 'select(.event == "dashboard.refresh_completed") | .duration_ms' logs/dashboard-usage.jsonl | \
  sort -n | awk '{a[NR]=$1} END {print "P95: " a[int(NR*0.95)] "ms"}'
```

**Lighthouse**: Not applicable (CLI tool, no web UI)

### Experiment Design (A/B Test)

Not applicable - this is an internal CLI tool, not user-facing feature. Success measured by:
- Adoption rate (% of trading days with dashboard usage)
- Time-to-insight reduction (time to assess session health)
- Export usage (indicating value for retrospective analysis)

---

## Quality Gates *(all must pass before `/plan`)*

### Core Requirements
- [x] No implementation details (tech stack, APIs, code) - Specification focuses on requirements only
- [x] Requirements testable and unambiguous - All FR/NFR have clear acceptance criteria
- [x] Context strategy documented - Token budget, retrieval strategy, signal design specified
- [x] No [NEEDS CLARIFICATION] markers - All requirements clear
- [x] Constitution aligned (performance, UX, data, access) - Enforces §Audit_Everything, §Risk_Management, §Data_Integrity, §Safety_First

### Success Metrics (HEART)
- [x] All 5 HEART dimensions have targets defined
- [x] Metrics are Claude Code-measurable (SQL, logs, Lighthouse) - All metrics from structured logs (jq/awk)
- [x] Hypothesis is specific and testable - 96% reduction in assessment time (3-5 min → <10s)
- [x] Performance targets from budgets.md specified - <2s startup, <500ms refresh, <50MB memory

### Screens (UI Features Only)
- [x] Skip - No web UI components (CLI-only feature)

### Measurement Plan
- [x] Analytics events defined (PostHog + logs + DB) - All metrics from dashboard-usage.jsonl
- [x] SQL queries drafted for key metrics - Bash/jq queries for sessions, duration, exports, errors
- [x] Experiment design complete (control, treatment, ramp) - Not applicable (internal tool, not A/B test)
- [x] Measurement sources are Claude Code-accessible - All logs accessible via jq/awk

### Deployment Considerations
- [x] Platform dependencies documented (Vercel, Railway, build tools) - Only `rich` library dependency
- [x] Environment variables listed (new/changed, with staging/production values) - None required
- [x] Breaking changes identified (API, schema, auth, client compatibility) - None (additive module)
- [x] Migration requirements documented (database, backfill, RLS, reversibility) - Fully reversible
- [x] Rollback plan specified (standard or special considerations) - Standard 3-command rollback
- [x] Skip if purely cosmetic UI changes or docs-only - Not skipped (new functional module)
