# Feature Specification: CLI Status Dashboard & Performance Metrics

**Branch**: `feature/019-status-dashboard`
**Created**: 2025-10-19
**Status**: Draft
**Area**: infra
**From Roadmap**: Yes (v1.0.0 release)

## User Scenarios

### Primary User Story
As a trading bot operator, I need a real-time CLI dashboard displaying account status, current positions, and performance metrics so I can quickly assess session health, identify opportunities, and ensure I'm meeting performance targets without manually querying logs or APIs.

### Acceptance Scenarios

1. **Given** the bot is running and authenticated, **When** I run `python -m trading_bot.dashboard`, **Then** the CLI displays current buying power, account balance, open positions with P&L, and today's performance metrics refreshed every 5 seconds

2. **Given** I have open positions, **When** the dashboard refreshes, **Then** I see each position's symbol, quantity, entry price, current price, unrealized P&L ($), and P&L percentage (%) with color coding (green for profit, red for loss)

3. **Given** I've executed trades today, **When** I view performance metrics, **Then** I see:
   - Win rate (percentage of winning trades)
   - Average risk-reward ratio
   - Total P&L (realized + unrealized)
   - Current win/loss streak
   - Number of trades executed today
   - Total session count (trading days)

4. **Given** I've configured performance targets, **When** the dashboard displays metrics, **Then** I see actual values compared to targets with variance indicators (e.g., "Win Rate: 65% [Target: 60%] ✓")

5. **Given** I want to export today's summary, **When** I press `E` key, **Then** the dashboard exports a JSON file and Markdown report with timestamp, all metrics, position snapshots, and target comparisons

6. **Given** the account data becomes stale (>60s), **When** the dashboard displays data, **Then** a staleness indicator appears to avoid acting on outdated information

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

## User Stories (Prioritized)

### Story Prioritization

**Priority 1 (MVP) 🎯**

- **US1** [P1]: As a bot operator, I want to view real-time account status (buying power, balance, day trade count) so that I know my current trading capacity
  - **Acceptance**: Dashboard displays account status section with buying power, cash + position value, day trade count, and last update timestamp
  - **Independent test**: Launch dashboard → verify account section renders with correct data from account-data-module
  - **Effort**: S (2-4 hours)

- **US2** [P1]: As a bot operator, I want to view all open positions with live P&L so that I can assess current risk exposure
  - **Acceptance**: Dashboard displays positions table with Symbol, Qty, Entry, Current, P&L $, P&L % columns, color-coded (green/red)
  - **Independent test**: Open positions exist → verify table renders with accurate P&L calculations
  - **Effort**: M (4-8 hours)

- **US3** [P1]: As a bot operator, I want to view today's performance metrics so that I can track session effectiveness
  - **Acceptance**: Dashboard displays win rate, avg R:R, total P&L, streak, trades today, session count
  - **Independent test**: Execute trades → verify metrics calculate correctly from trade logs
  - **Effort**: M (4-8 hours)

**Priority 2 (Enhancement)**

- **US4** [P2]: As a bot operator, I want automatic dashboard refresh every 5 seconds so that I always see current data without manual intervention
  - **Acceptance**: Dashboard auto-refreshes every 5s, shows "Refreshing..." indicator during fetch
  - **Depends on**: US1, US2, US3
  - **Effort**: S (2-4 hours)

- **US5** [P2]: As a bot operator, I want to compare my performance against targets so that I know if I'm meeting goals
  - **Acceptance**: Load targets from config file, display actual vs target with variance indicators
  - **Depends on**: US3
  - **Effort**: S (2-4 hours)

- **US6** [P2]: As a bot operator, I want to export daily summaries so that I can keep records and analyze trends
  - **Acceptance**: Press 'E' key → generate JSON + Markdown files in logs/ directory with all metrics
  - **Depends on**: US1, US2, US3
  - **Effort**: S (2-4 hours)

**Priority 3 (Nice-to-have)**

- **US7** [P3]: As a bot operator, I want keyboard controls (R/E/H/Q) so that I can interact with the dashboard efficiently
  - **Acceptance**: R = manual refresh, E = export, H = help overlay, Q = quit
  - **Depends on**: US1, US4, US6
  - **Effort**: XS (<2 hours)

- **US8** [P3]: As a bot operator, I want market status indication so that I know if the market is currently open
  - **Acceptance**: Display OPEN/CLOSED indicator based on current time (9:30 AM - 4:00 PM ET, Mon-Fri)
  - **Depends on**: US1
  - **Effort**: XS (<2 hours)

**MVP Strategy**: Ship US1-US3 first (core display functionality), validate data accuracy, then add US4-US6 (automation and enhancements), finally US7-US8 (polish).

## Visual References

N/A - No web UI components (CLI-only feature using `rich` library for terminal rendering)

## Success Metrics (HEART Framework)

See `./design/heart-metrics.md` for full HEART framework measurement plan.

**Summary**:
- **Happiness**: 5+ dashboard sessions/day (reduce manual checks)
- **Engagement**: 2-5 min/session (focused monitoring without distraction)
- **Adoption**: 90% of trading days using dashboard
- **Retention**: 80% weekly usage (sustained adoption)
- **Task Success**: <10 seconds time-to-insight (vs 3-5 minutes manual)

**Performance Targets**:
- Dashboard startup: <2 seconds (cold start)
- Refresh cycle: <500ms (account data + trade log read)
- Export generation: <1 second
- Memory footprint: <50MB (long-running CLI tool)

## Screens Inventory (UI Features Only)

N/A - CLI-only feature (no UI screens)

## Hypothesis

**Problem**: Bot operators manually check account status via multiple API calls and parse trade logs using grep/jq to assess session performance, taking 3-5 minutes per check and performed 5-10 times per trading day
- Evidence: No unified monitoring tool, manual queries documented in trade-logging spec
- Impact: Context switching disrupts focus (15-20 min daily analysis), delayed reaction to performance issues
- Gap: Cannot quickly answer "Am I meeting targets today?" or "What's my current risk exposure?"

**Solution**: Real-time CLI dashboard aggregating account data, position P&L, and performance metrics with target comparison in single view
- Change: Unified dashboard replaces manual API calls and log queries
- Mechanism: Polls account-data-module (60s cache) and reads trade logs, displays in formatted sections with color coding

**Prediction**: Unified dashboard will reduce session health assessment time from 3-5 minutes to <10 seconds
- Primary metric: Time-to-insight <10s (currently 3-5 minutes)
- Expected improvement: -96% reduction in assessment time
- Confidence: High (eliminates manual context assembly, proven CLI dashboard pattern)

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
- **FR-005**: System MUST load performance targets from configuration file if present, comparing actual vs target for: win_rate, daily_pl, trades_per_day, max_drawdown
- **FR-006**: System MUST provide keyboard controls: `R` (manual refresh), `E` (export daily summary), `Q` (quit), `H` (help overlay)
- **FR-007**: System MUST export daily summary when `E` pressed, generating both JSON and Markdown files with timestamp
- **FR-008**: System MUST color-code P&L values (green for positive, red for negative, yellow for zero) and target comparisons (green if meeting target, red if not)
- **FR-009**: System MUST display market status indicator (OPEN/CLOSED) based on market hours (9:30 AM - 4:00 PM ET, Mon-Fri)
- **FR-010**: System MUST show data staleness indicator when last account data fetch >60 seconds ago
- **FR-011**: System MUST calculate win rate from trade logs: (winning trades / total closed trades) × 100
- **FR-012**: System MUST calculate average R:R from trade logs: average of (target - entry) / (entry - stop_loss) for all trades with risk parameters
- **FR-013**: System MUST calculate total P&L as: sum of realized P&L from closed trades + sum of unrealized P&L from current positions
- **FR-014**: System MUST calculate current streak: consecutive wins or losses from most recent closed trades
- **FR-015**: System MUST handle missing trade log gracefully: display account data only with warning message "Trade log not found, performance metrics unavailable"
- **FR-016**: System MUST handle missing targets file gracefully: display metrics without target comparison, log warning once

### Non-Functional

- **NFR-001**: Performance: Dashboard startup <2s (cold start), refresh cycle <500ms (Constitution §Data_Integrity - time zone awareness, data validation)
- **NFR-002**: Reliability: Dashboard must not crash on API errors, stale data, or missing files (Constitution §Safety_First - fail safe not fail open)
- **NFR-003**: Usability: Display must fit standard terminal (80x24 minimum) with responsive layout for larger sizes
- **NFR-004**: Data Integrity: All timestamps in UTC (Constitution §Data_Integrity), display in local time with timezone indicator
- **NFR-005**: Type Safety: All functions must use type hints (Constitution §Code_Quality)
- **NFR-006**: Test Coverage: ≥90% code coverage for dashboard logic (Constitution §Testing_Requirements)
- **NFR-007**: Auditability: Log all export events with timestamp and file paths (Constitution §Safety_First - audit everything)
- **NFR-008**: Memory Efficiency: Dashboard process <50MB memory footprint for long-running sessions

### Key Entities (if data involved)

- **AccountStatus**: Current account snapshot
  - Purpose: Display real-time account health
  - Key attributes: buying_power, account_balance, cash_balance, day_trade_count, last_updated
  - Relationships: Fetched from account-data-module

- **PositionDisplay**: Position with calculated P&L for display
  - Purpose: Show current holdings with profit/loss
  - Key attributes: symbol, quantity, entry_price, current_price, unrealized_pl, unrealized_pl_pct
  - Relationships: Derived from account-data-module positions

- **PerformanceMetrics**: Aggregated trading performance
  - Purpose: Track trading effectiveness
  - Key attributes: win_rate, avg_risk_reward, total_realized_pl, total_unrealized_pl, current_streak, streak_type, trades_today, session_count
  - Relationships: Calculated from trade logs (trades-structured.jsonl)

- **DashboardTargets**: Performance targets for comparison
  - Purpose: Define success criteria
  - Key attributes: target_win_rate, target_daily_pl, target_trades_per_day, max_drawdown
  - Relationships: Loaded from config/dashboard-targets.yaml

## Deployment Considerations

N/A - No deployment changes required (CLI tool, no infrastructure modifications)

**Platform Dependencies**: None (pure Python CLI application)

**Environment Variables**: None required (uses existing account-data-module config)

**Breaking Changes**: No (new feature, not modifying existing APIs)

**Migration Required**: No (no database schema changes)

## Assumptions

1. **Account Data Access**: Assumes account-data-module is already configured and authenticated
2. **Trade Log Format**: Assumes trade logs follow structured JSONL format from trade-logging module
3. **Terminal Support**: Assumes terminal supports ANSI color codes and Unicode characters (rich library requirement)
4. **Refresh Interval**: 5-second refresh is reasonable default (not configurable in MVP)
5. **Target File Format**: YAML format for dashboard-targets.yaml (industry standard)
6. **Export Location**: logs/ directory exists and is writable
7. **Time Zone**: Market hours based on US Eastern Time (NYSE/NASDAQ standard)

## Dependencies

**Required Modules** (from roadmap):
- **account-data-module**: Provides buying power, balance, positions, day trade count
- **performance-tracking**: Provides TradeQueryHelper, MetricsCalculator for statistics
- **trade-logging**: Provides structured trade logs (trades-structured.jsonl)

**External Libraries**:
- `rich`: Terminal rendering and formatting (industry-standard CLI UI library)

## Success Criteria

Users can assess session health in under 10 seconds by launching the dashboard and viewing all key metrics (account status, positions, performance) in a single unified display, eliminating the need for manual API calls and log parsing.

**Verification**:
1. Launch dashboard → All sections render with current data within 2 seconds
2. Open positions exist → P&L calculations match manual verification
3. Trades executed → Metrics match TradeQueryHelper calculations
4. Export summary → Files generated in logs/ with complete data
5. API failure → Dashboard shows cached data with stale indicator (no crash)

---

**Implementation Notes**:
- Existing implementation at `src/trading_bot/dashboard/` can be referenced
- Follow Constitution §Code_Quality: Type hints, ≥90% test coverage, KISS, DRY
- Follow Constitution §Safety_First: Fail safe (show cached data on error, never crash)
- Follow Constitution §Testing_Requirements: Unit + integration tests required

**Related Specs**:
- specs/account-data-module/spec.md
- specs/performance-tracking/spec.md
- specs/trade-logging/spec.md
