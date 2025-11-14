# Feature Specification: Stock Screener

**Branch**: `001-stock-screener`
**Created**: 2025-10-16
**Status**: Draft
**Area**: api
**Role**: all (traders)

---

## User Scenarios

### Primary User Story

As a trader, I want to filter stocks by technical criteria (price, volume, float, performance) so that I can identify high-probability setups that meet my trading rules without manually scanning hundreds of stocks.

### Acceptance Scenarios

1. **Given** the market data module is running, **When** I request screener results with price range $2-$20, **Then** the system returns stocks matching exactly those criteria (bid price between $2.00-$20.00)

2. **Given** a stock with 100-day average volume of 2M shares, **When** I request relative volume filter 5x+, **Then** the system includes the stock only if current volume exceeds 10M shares

3. **Given** a stock with 50M shares outstanding, **When** I request float size filter under 20M, **Then** the system excludes the stock (public float too large)

4. **Given** the market is open and real-time quotes available, **When** I request daily performance filter 10%+ movers, **Then** the system returns stocks with |daily change| ≥ 10% (open to close)

5. **Given** screener runs during pre-market (4am-7am EST), **When** market opens, **Then** screener automatically updates with real-time data and continues filtering

6. **Given** invalid filter parameters (e.g., min price > max price), **When** I submit the request, **Then** the system rejects with clear error message indicating the constraint violation

### Edge Cases

- What happens when a stock gaps below $2.00 mid-session? (Exclude from subsequent screens until it returns above range)
- How does the system handle market halts for a stock in results? (Mark as halted, exclude from new scans, retain in history)
- What if float data is unavailable for a stock? (Skip float filter, apply other filters, log missing data)
- How does relative volume work for IPO stocks with no historical volume baseline? (Use 1M shares as default baseline; document assumption)
- What if screener result is 10,000+ stocks? (Return paginated results, max 500 per page; include total count)

---

## User Stories (Prioritized)

> **Priority Format**: [P1] = MVP (ship first), [P2] = Enhancement, [P3] = Nice-to-have

### Story Prioritization

**Priority 1 (MVP) 🎯**

- **US1** [P1]: As a trader, I want to filter stocks by price range ($2-$20) so that I can focus on penny stocks within my trading strategy
  - **Acceptance**: Screener accepts min_price/max_price parameters; filters by bid price; returns stocks with bid >= min AND bid <= max
  - **Independent test**: `test_price_range_filter_basic` - Verify 5 stocks across range boundaries
  - **Effort**: S (2-4 hours)

- **US2** [P1]: As a trader, I want to filter stocks by relative volume (5x+ average) so that I can identify stocks with abnormal trading activity
  - **Acceptance**: Accepts relative_volume parameter (default 5.0); calculates vs 100-day avg; returns stocks where current_volume >= (avg_volume * multiplier)
  - **Independent test**: `test_relative_volume_filter` - 3 test cases (below, at, above threshold)
  - **Effort**: S (2-4 hours)

- **US3** [P1]: As a trader, I want to filter stocks by float size (under 20M shares) so that I can find tightly-held stocks with higher volatility
  - **Acceptance**: Accepts float_max parameter; filters by public float; returns stocks where float < float_max
  - **Independent test**: `test_float_size_filter` - Verify 4 stocks at boundaries
  - **Effort**: S (2-4 hours)

- **US4** [P1]: As a trader, I want to filter stocks by daily performance (10%+ movers) so that I can capture momentum setups
  - **Acceptance**: Accepts min_daily_change parameter (percent); calculates |(current price - open price) / open price * 100|; returns stocks where abs(change) >= threshold
  - **Independent test**: `test_daily_performance_filter` - Up movers, down movers, exact threshold
  - **Effort**: S (2-4 hours)

- **US5** [P1]: As a trader, I want to combine multiple filters in a single scan so that I can apply my complete trading rules at once
  - **Acceptance**: Screener accepts dict of filter params; applies all non-null filters; returns intersection of results; order by volume descending
  - **Independent test**: `test_combined_filters` - 5+ combinations tested
  - **Effort**: M (4-8 hours)

**Priority 2 (Enhancement)**

- **US6** [P2]: As a trader, I want screener results cached for 60 seconds so that rapid successive queries don't hammer the API
  - **Acceptance**: Stores result with timestamp; within 60s window returns cached; after 60s expires and refreshes
  - **Depends on**: US1-US5
  - **Effort**: S (2-4 hours)

- **US7** [P2]: As a trader, I want export screener results to CSV so that I can analyze results in Excel and archive results
  - **Acceptance**: Exports symbol, price, volume, float, daily_change, timestamp; UTF-8 encoded; includes header row
  - **Depends on**: US5
  - **Effort**: S (2-4 hours)

**Priority 3 (Nice-to-have)**

- **US8** [P3]: As a trader, I want real-time alerts when screener criteria change so that I can capture opportunities mid-session
  - **Acceptance**: Periodic scan every 15 minutes; logs new matches; optional Slack/email notification hook
  - **Depends on**: US1-US5
  - **Effort**: M (4-8 hours)

---

## Visual References

N/A - Backend API feature (no UI screens)

---

## Success Metrics (HEART Framework)

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Screener produces high-confidence setups (low false positives) | Filter accuracy | Setup success rate (% of screener results that lead to profitable trades) | ≥65% (vs 50% baseline) | <3% API error rate |
| **Engagement** | Traders use screener regularly to support strategy | Usage frequency | Scans per day (avg across trading sessions) | ≥2 scans/session | Latency P95 <500ms |
| **Adoption** | Feature is adopted by traders to augment manual scanning | First-time usage | % of traders running 1+ scan | ≥80% (within 2 weeks of launch) | N/A |
| **Retention** | Traders continue using screener over time | Repeat usage | % of traders with 10+ scans in last 30 days | ≥60% | N/A |
| **Task Success** | Screener returns relevant results in acceptable time | Completion | Query latency P50 | <200ms | P95 <500ms |

---

## Context Strategy & Signal Design

- **System prompt altitude**: Trader-focused feature for pre-trade setup identification
- **Tool surface**: MarketDataService (quote retrieval), AccountData (buying power context optional), StructuredTradeLogger (audit trailing)
- **Examples in scope**: ≤3 example filter combos (penny_moonshot, volume_spike, breakout_candidate)
- **Context budget**: ~25k tokens (research + plan phases); compaction not required for this scope
- **Retrieval strategy**: JIT - Fetch current quotes on each request (freshness > caching tradeoffs for trading)
- **Memory artifacts**: NOTES.md update per major test milestone; error-log.md for API failures
- **Compaction cadence**: Post-implementation (100% task completion)
- **Sub-agents**: None (backend-only, no UI or deployment agents needed)

---

## Requirements

### Functional (Testable)

- **FR-001**: System MUST accept filter parameters: min_price, max_price, relative_volume, float_max, min_daily_change
- **FR-002**: System MUST validate all filter parameters before querying (type checking, range bounds)
- **FR-003**: System MUST filter stocks by price range using bid price (filter: bid >= min_price AND bid <= max_price)
- **FR-004**: System MUST filter stocks by relative volume (filter: current_volume >= (avg_volume_100d * relative_volume_multiplier))
- **FR-005**: System MUST filter stocks by float size (filter: public_float < float_max)
- **FR-006**: System MUST filter stocks by daily performance (filter: abs((close - open) / open * 100) >= min_daily_change)
- **FR-007**: System MUST return intersection of all applied filters (AND logic, not OR)
- **FR-008**: System MUST handle missing data gracefully (skip field if data unavailable, log event, continue)
- **FR-009**: System MUST return results sorted by volume descending (highest volume first)
- **FR-010**: System MUST include metadata in response (query timestamp, filter params, result count, execution latency)
- **FR-011**: System MUST reject queries with invalid parameters and return error with remediation guidance
- **FR-012**: System MUST support pagination for large result sets (max 500 per page, cursor-based or offset-based)

### Non-Functional

- **NFR-001**: Performance: Query latency P50 <200ms, P95 <500ms (including API calls)
- **NFR-002**: Resilience: Handle Robinhood API rate limiting with exponential backoff (existing @with_retry decorator)
- **NFR-003**: Availability: Function during market hours (7am-10am EST pre-market/regular trading); N/A outside hours
- **NFR-004**: Data freshness: Real-time quotes (max 1min staleness for close/volume)
- **NFR-005**: Error handling: All API failures logged with context; user-facing errors include remediation (§Audit_Everything, §Error_Handling_Framework)
- **NFR-006**: Type safety: 100% type hints; mypy strict mode passes (§Code_Quality)
- **NFR-007**: Test coverage: ≥90% (§Testing_Requirements)
- **NFR-008**: Logging: All screener requests logged to JSONL (timestamp, params, result_count, latency, errors)

### Key Entities

- **Stock**: Symbol, current price (bid), avg volume (100d), public float, daily open/close
- **ScreenerResult**: Stocks[], query_timestamp, params_used, result_count, execution_time_ms, page_info
- **ScreenerQuery**: min_price, max_price, relative_volume, float_max, min_daily_change, limit, offset

---

## Hypothesis

**Not applicable** - This is a new feature addition, not an improvement to existing functionality. No baseline to compare against.

---

## Deployment Considerations

### Platform Dependencies

**Vercel** (if API is web-based):
- None (backend API, no edge middleware changes)

**Railway** (Python trading bot backend):
- None (no new dependencies, pure Python using existing robin_stocks)

**Dependencies**:
- Existing: `robin_stocks`, `pandas`, `numpy`
- New: None (leverage existing libraries)

### Environment Variables

**New Required Variables**:
- None (uses existing ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD, MFA_SECRET already configured)

**Changed Variables**:
- None

**Schema Update Required**: No

### Breaking Changes

**API Contract Changes**:
- New endpoints: `POST /api/screener/filter` or module function `ScreenerService.filter()`
- Backward compatible (additive only)

**Database Schema Changes**:
- No (in-memory processing only; optional: add screener_results table for audit trail)

**Client Compatibility**:
- Backward compatible (new feature, no changes to existing APIs)

### Migration Requirements

**Database Migrations**:
- Optional: Add `screener_queries` table (audit trail of all screener runs)
- Optional: Add `screener_results` table (cache filtered stocks for replay)

**Data Backfill**:
- Not required (net new feature)

**RLS Policy Changes**:
- Not applicable (trading bot is single-user)

### Rollback Considerations

**Standard Rollback**:
- Yes: Simply remove ScreenerService import/class; existing code unaffected

**Special Rollback Needs**:
- None (no infrastructure changes, no migrations required for MVP)

**Deployment Metadata**:
- Track screener-service.py SHA and version in NOTES.md

---

## Measurement Plan

### Data Collection

**Analytics Events** (structured logs):
- `screener.query` - Timestamp, filter params, result count, execution time
- `screener.filter_applied` - Which filters active (price, volume, float, daily_change)
- `screener.error` - API error type, retry count, resolution

**Key Events to Track**:
1. `screener.query_submitted` - Every screener request
2. `screener.query_completed` - Successful completion (result_count, execution_time_ms)
3. `screener.query_cached` - Cache hit (latency benefit tracked)
4. `screener.query_error` - API/validation failures (error type, recoverable?)
5. `screener.filter_usage` - Which filters most commonly used (insights for refinement)

### Measurement Queries

**Logs** (`logs/screener/*.jsonl`):
- Query count: `grep '"event":"screener.query_completed"' logs/screener/*.jsonl | wc -l`
- Avg latency: `jq -r '.execution_time_ms' logs/screener/*.jsonl | awk '{sum+=$1; count++} END {print sum/count}'`
- Error rate: `errors / total_queries * 100` where errors from screener.query_error events
- Result counts: `jq -r '.result_count' | sort -n | awk '{a[NR]=$1} END {print a[int(NR*0.50)], a[int(NR*0.95)]}'` (P50, P95)

**Backtesting** (optional):
- Run historical market data through screener filters (e.g., last 50 trading days)
- Calculate % of screener matches that preceded +5% moves (setup success rate)
- Calculate false positive rate (% that moved <2% next day)

### Experiment Design (A/B Test)

**Not applicable for MVP** - This is an additive feature, not replacing existing functionality. Measurement is observational only.

---

## Quality Gates *(Must pass before `/plan`)*

### Core (Always Required)
- [x] Requirements testable, no ambiguity (max 3 clarification markers)
- [x] Constitution aligned (§Safety_First: paper trading compatible, §Code_Quality: type hints, §Testing_Requirements: 90% coverage target)
- [x] No implementation details (tech-agnostic requirements, no "python", "robin_stocks", "REST API" leaking in)

### Conditional: Success Metrics (Skip if no user tracking)
- [x] HEART metrics defined with measurable signals
- [x] No hypothesis section (new feature, not improvement)

### Conditional: UI Features (Skip if backend-only)
- [x] N/A - Backend API feature only

### Conditional: Deployment Impact (Skip if no infrastructure changes)
- [x] No breaking changes, backward compatible
- [x] No migrations required for MVP
- [x] No new environment variables

---

## Summary

The Stock Screener feature enables traders to rapidly identify setup candidates by combining technical filters (price, volume, float, daily performance) without manual scanning. MVP focuses on core filtering capability; enhancements (caching, export, alerts) follow post-launch feedback.

**Blockers**: None (depends on shipped market-data-module)
**Unblocked**: Ready for planning phase

---

**Next Phase**: `/plan` (architecture, component breakdown, technical approach)
