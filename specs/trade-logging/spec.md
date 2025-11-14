# Feature Specification: Enhanced Trade Logging System

**Branch**: `trade-logging`
**Created**: 2025-10-09
**Status**: Draft

## User Scenarios

### Primary User Story
As a trading bot operator, I need a structured, queryable trade logging system that captures all trade decisions with reasoning, enabling performance analysis, strategy comparison, and compliance auditing without manual log parsing.

### Acceptance Scenarios

1. **Given** the bot executes a trade, **When** the trade completes, **Then** a structured JSON log entry is written with symbol, action, quantity, price, timestamp, strategy, reasoning, and risk parameters
2. **Given** trades have been logged, **When** I query using grep/jq, **Then** I can extract win rate, average profit/loss, and strategy performance metrics
3. **Given** a regulatory audit is required, **When** I review trade logs, **Then** I can see the complete decision trail including entry signals, risk calculations, and exit reasoning
4. **Given** backtests complete, **When** I compare live trades to backtest predictions, **Then** I can measure strategy drift and live performance vs historical results
5. **Given** the bot encounters an error during trade execution, **When** the error occurs, **Then** the failure is logged with context including attempted action, error type, and system state

### Edge Cases

- What happens when log directory is full or permissions are denied?
  - Fallback to console logging with error notification, never fail trade execution
- How does system handle concurrent writes from multiple strategies?
  - Use thread-safe file handlers with atomic writes
- What happens to logs during log rotation?
  - No data loss, rotation handled by RotatingFileHandler with 10MB threshold
- How are partial trades logged (e.g., partially filled orders)?
  - Log both the intended and actual quantities, mark as partial fill
- What happens when JSON serialization fails (e.g., non-serializable data)?
  - Fallback to string representation, log warning, never block trade execution

## Visual References

N/A - No UI components (backend-only feature)

## Success Metrics (HEART Framework)

> **Purpose**: Define quantified success criteria using Google's HEART framework.
> **Constraint**: All metrics MUST be Claude Code-measurable (SQL, logs, Lighthouse).

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Reduce time spent on manual log analysis | Query execution time | Time to extract performance metrics | <30s for daily analysis | P95 <60s |
| **Engagement** | Increase usage of trade analytics | Query frequency | Analytics queries per week | 5+ queries/week | Min 1/week |
| **Adoption** | Enable strategy performance tracking | Backtest comparison usage | % of backtests validated against live | 80% comparison rate | Min 50% |
| **Retention** | Maintain audit trail for compliance | Log retention completeness | % of trades with full reasoning | 100% logged trades | Min 98% |
| **Task Success** | Enable actionable insights from logs | Successful query rate | % of queries returning valid results | 95% success rate | P95 <5% errors |

**Performance Targets** (from `design/systems/budgets.md`):
- Log write latency: <10ms P95 (non-blocking)
- Log file size: <100MB per month (with compression)
- Query execution: <30s for 1 month of data
- No impact on trade execution timing

See `.spec-flow/templates/heart-metrics-template.md` for full measurement plan.

## Screens Inventory (UI Features Only)

N/A - No UI components (backend-only feature)

## Hypothesis

> **Purpose**: State the problem, solution, and predicted improvement.
> **Format**: Problem → Solution → Prediction (with magnitude)

**Problem**: Current text-based trade logging requires manual parsing and custom scripts to extract performance metrics, strategy comparison data, and compliance audit trails
- Evidence: No structured query capability, log analysis requires custom Python scripts
- Impact: Bot operators spend 15-20 minutes per day manually analyzing trade logs
- Gap: Cannot easily measure win rate, profit/loss by strategy, or validate backtest predictions against live trades

**Solution**: Dual logging system with human-readable text (backwards compatible) + machine-readable JSON (structured queries)
- Change: Extend `log_trade()` to write both text and JSON formats
- Mechanism: Structured JSON enables grep/jq queries for instant analytics
- Components: TradeRecord dataclass, StructuredTradeLogger, TradeQueryHelper

**Prediction**: Structured logging will reduce trade analysis time from 15-20 minutes to <30 seconds
- Primary metric: Time-to-insight <30s (currently 15-20 minutes)
- Expected improvement: -97% reduction in analysis time
- Confidence: High (industry standard pattern, zero learning curve for grep/jq users)

## Context Strategy & Signal Design

- **System prompt altitude**: Task-level - "Log this trade with reasoning" (clear, atomic operations)
- **Tool surface**: Python logging library + JSON serialization (standard library, zero token overhead)
- **Examples in scope**: 3 canonical examples (buy with stop loss, sell on target, error case)
- **Context budget**: <5k tokens (simple data transformation, no complex logic)
- **Retrieval strategy**: JIT - Load log schema only when needed, no upfront context
- **Memory artifacts**: NOTES.md updated after each implementation task, no TODO tracking (single-phase feature)
- **Compaction cadence**: Not needed (small feature scope)
- **Sub-agents**: Not used (single-responsibility implementation)

## Requirements

### Functional (testable only)

- **FR-001**: System MUST write structured JSON log entry for every trade execution (buy, sell, error) to `logs/trades-structured.jsonl`
- **FR-002**: System MUST log all fields: timestamp (UTC ISO8601), symbol, action (BUY/SELL/ERROR), quantity_intended, quantity_actual, price, mode (PAPER/LIVE), strategy, reasoning, risk_params (stop_loss, target, position_size_pct), execution_id (unique)
- **FR-003**: System MUST maintain backwards compatibility with existing `logs/trades.log` text format
- **FR-004**: System MUST use `.jsonl` format (newline-delimited JSON) for append-only writes and parallel query safety
- **FR-005**: System MUST include reasoning field documenting why trade was executed (entry signal, exit trigger, error context)
- **FR-006**: System MUST log partial fills with both intended and actual quantities marked as `partial: true`
- **FR-007**: System MUST provide query helper functions for common analytics: win_rate(), avg_profit_loss(), trades_by_strategy(), backtest_comparison()
- **FR-008**: System MUST handle JSON serialization failures gracefully (fallback to string representation, log warning, never block execution)
- **FR-009**: System MUST use thread-safe file handlers for concurrent writes from multiple strategies
- **FR-010**: System MUST validate all logged data against TradeRecord schema before writing

### Non-Functional

- **NFR-001**: Performance: Log write latency <10ms P95 (non-blocking, async where possible)
- **NFR-002**: Reliability: 100% of trade executions logged (no silent failures, fallback to console on file errors)
- **NFR-003**: Data Integrity: All timestamps in UTC (Constitution §Data_Integrity), ISO8601 format
- **NFR-004**: Auditability: Complete decision trail for every trade (Constitution §Audit_Everything)
- **NFR-005**: Type Safety: All logging functions must use type hints (Constitution §Code_Quality)
- **NFR-006**: Test Coverage: ≥90% code coverage for all logging functions (Constitution §Testing_Requirements)
- **NFR-007**: Error Handling: Never fail trade execution due to logging errors (fail safe, not fail open)
- **NFR-008**: Log Rotation: Automatic rotation at 10MB with 5 backups (consistent with existing logging system)

### Key Entities (if data involved)

- **TradeRecord**: Complete trade execution record
  - Purpose: Type-safe structure for all trade data
  - Key attributes: execution_id (UUID), timestamp (datetime), symbol (str), action (Literal["BUY", "SELL", "ERROR"]), quantity_intended (int), quantity_actual (int), price (Decimal), mode (Literal["PAPER", "LIVE"]), strategy (str), reasoning (str), risk_params (dict[str, float]), partial (bool), error_context (Optional[dict])
  - Relationships: Links to strategy configuration, backtest results (via strategy name + timestamp range)

- **QueryResult**: Analytics query result
  - Purpose: Structured output from TradeQueryHelper functions
  - Key attributes: metric_name (str), value (Union[float, int, dict]), timestamp_range (tuple[datetime, datetime]), trade_count (int)
  - Relationships: Aggregates TradeRecord data

## Deployment Considerations

> **Purpose**: Document deployment constraints and dependencies for planning phase.
> **Skip if**: Purely cosmetic UI changes or documentation-only changes.

### Platform Dependencies

**Vercel** (marketing/app): None

**Railway** (API): None

**Dependencies**: None (uses Python standard library only: logging, json, dataclasses, pathlib, uuid, decimal)

### Environment Variables

**New Required Variables**: None

**Changed Variables**: None

**Schema Update Required**: No

### Breaking Changes

**API Contract Changes**: No

**Database Schema Changes**: No (file-based logging only)

**Auth Flow Modifications**: No

**Client Compatibility**: Backward compatible - adds new log file, maintains existing text log format

### Migration Requirements

**Database Migrations**: Not applicable (no database)

**Data Backfill**: Not required - new logs only (no retroactive parsing of existing text logs)

**RLS Policy Changes**: Not applicable

**Reversibility**: Fully reversible - can delete structured logs without affecting existing system

### Rollback Considerations

**Standard Rollback**: Yes - 3-command rollback via runbook/rollback.md

**Special Rollback Needs**: None - new log files can be deleted, no data dependencies

**Deployment Metadata**: Deploy IDs tracked in specs/trade-logging/NOTES.md (Deployment Metadata section)

---

## Measurement Plan

> **Purpose**: Define how success will be measured using Claude Code-accessible sources.
> **Sources**: SQL queries, structured logs, Lighthouse CI, database aggregates.

### Data Collection

**Analytics Events** (dual instrumentation):
- PostHog (dashboards): Not applicable (internal tooling, no user-facing analytics)
- Structured logs (Claude measurement): All metrics extracted from `logs/trades-structured.jsonl`
- Database (A/B tests): Not applicable (no A/B testing for logging infrastructure)

**Key Events to Track**:
1. `trade.executed` - Every trade execution (logged to trades-structured.jsonl)
2. `trade.partial_fill` - Partial order fills (logged with partial: true)
3. `trade.error` - Failed trade attempts (logged with error_context)
4. `log.query` - Analytics query executions (logged to queries.log for optimization)
5. `log.rotation` - Log file rotations (logged to trading_bot.log for monitoring)

### Measurement Queries

**Logs** (`logs/trades-structured.jsonl`):

```bash
# Win rate (trades with profit)
grep '"action":"SELL"' logs/trades-structured.jsonl | \
  jq -s 'map(select(.profit > 0)) | length / (input | length) * 100'

# Average profit/loss by strategy
grep '"action":"SELL"' logs/trades-structured.jsonl | \
  jq -s 'group_by(.strategy) | map({strategy: .[0].strategy, avg_pl: (map(.profit) | add / length)})'

# Trades per day
jq -r '.timestamp' logs/trades-structured.jsonl | \
  cut -d'T' -f1 | sort | uniq -c

# Strategy performance comparison
jq -s 'group_by(.strategy) | map({
  strategy: .[0].strategy,
  total_trades: length,
  wins: map(select(.profit > 0)) | length,
  avg_profit: (map(.profit) | add / length),
  max_drawdown: ([.[].profit] | min)
})' logs/trades-structured.jsonl

# Error rate
jq -s 'map(select(.action == "ERROR")) | length' logs/trades-structured.jsonl

# Partial fill rate
jq -s 'map(select(.partial == true)) | length / (. | length) * 100' logs/trades-structured.jsonl
```

**Query Performance** (`logs/queries.log`):
```bash
# Query execution time P95
jq -r '.duration' logs/queries.log | sort -n | awk '{a[NR]=$1} END {print a[int(NR*0.95)]}'

# Query success rate
jq -s 'map(select(.status == "success")) | length / (. | length) * 100' logs/queries.log
```

**Lighthouse**: Not applicable (no UI)

### Experiment Design (A/B Test)

Not applicable - this is infrastructure improvement, not user-facing feature. Success measured by:
- Reduction in manual log parsing time (baseline: 15-20 min/day)
- Query execution time (target: <30s for daily analysis)
- Log completeness (target: 100% of trades logged)

---

## Quality Gates *(all must pass before `/plan`)*

### Core Requirements
- [x] No implementation details (tech stack, APIs, code) - Specification focuses on requirements only
- [x] Requirements testable and unambiguous - All FR/NFR have clear acceptance criteria
- [x] Context strategy documented - Token budget, retrieval strategy, signal design specified
- [x] No [NEEDS CLARIFICATION] markers - All requirements clear
- [x] Constitution aligned (performance, UX, data, access) - Enforces §Audit_Everything, §Data_Integrity, §Code_Quality

### Success Metrics (HEART)
- [x] All 5 HEART dimensions have targets defined
- [x] Metrics are Claude Code-measurable (SQL, logs, Lighthouse) - All metrics from structured logs (grep/jq)
- [x] Hypothesis is specific and testable - 97% reduction in analysis time (15-20 min → <30s)
- [x] Performance targets from budgets.md specified - <10ms log write, <30s query execution

### Screens (UI Features Only)
- [x] Skip - No UI components (backend-only feature)

### Measurement Plan
- [x] Analytics events defined (PostHog + logs + DB) - All metrics from structured logs
- [x] SQL queries drafted for key metrics - Bash/jq queries provided for win rate, avg P/L, strategy comparison
- [x] Experiment design complete (control, treatment, ramp) - Not applicable (infrastructure, not A/B test)
- [x] Measurement sources are Claude Code-accessible - All logs accessible via grep/jq

### Deployment Considerations
- [x] Platform dependencies documented (Vercel, Railway, build tools) - None (standard library only)
- [x] Environment variables listed (new/changed, with staging/production values) - None required
- [x] Breaking changes identified (API, schema, auth, client compatibility) - Backward compatible
- [x] Migration requirements documented (database, backfill, RLS, reversibility) - No migration, fully reversible
- [x] Rollback plan specified (standard or special considerations) - Standard 3-command rollback
- [x] Skip if purely cosmetic UI changes or docs-only - Not skipped (infrastructure change with deployment impact)
