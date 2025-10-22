# Feature Specification: Level 2 Order Flow Integration

**Branch**: `feature/028-level-2-order-flow-i`
**Created**: 2025-10-22
**Status**: Draft

## User Scenarios

### Primary User Story
A day trader running the trading bot wants to monitor real-time order flow to detect large institutional selling pressure (large seller alerts) and sudden volume spikes (red burst patterns) that indicate an imminent price drop, allowing the system to trigger protective exits before significant losses occur.

### Acceptance Scenarios
1. **Given** an active position in a stock, **When** a large sell order appears in the Level 2 order book (>10,000 shares at bid), **Then** the system logs a "large seller alert" with order size, price level, and timestamp
2. **Given** real-time Time & Sales data, **When** volume spikes >300% of 5-minute average with majority sells, **Then** the system logs a "red burst" alert and evaluates exit conditions
3. **Given** multiple large seller alerts within 2 minutes, **When** bid pressure builds (>3 consecutive large sells), **Then** the system triggers an exit signal for risk management evaluation
4. **Given** normal order flow conditions, **When** no large sellers or volume spikes detected, **Then** the system continues monitoring without alerts (no false positives)

### Edge Cases
- What happens when Level 2 data feed is unavailable or delayed?
- How does system handle pre-market or after-hours order flow (different liquidity)?
- What if large orders appear on both bid and ask (institutional accumulation vs distribution)?
- How to distinguish between genuine selling pressure and market maker hedging?
- What happens during market-wide selloffs vs stock-specific events?

## User Stories (Prioritized)

> **Purpose**: Break down feature into independently deliverable stories for MVP-first delivery.
> **Format**: [P1] = MVP (ship first), [P2] = Enhancement, [P3] = Nice-to-have

### Story Prioritization

**Priority 1 (MVP) 🎯**
- **US1** [P1]: As a trading bot, I want to detect large sell orders in the Level 2 order book so that I can identify institutional selling pressure before price drops
  - **Acceptance**:
    - System fetches Level 2 order book data from Robinhood API (or alternative data source)
    - Identifies sell orders >10,000 shares at bid or below
    - Logs alert with symbol, order size, price level, timestamp (UTC)
    - Returns OrderFlowAlert dataclass with alert type and severity
  - **Independent test**: Can fetch Level 2 data and identify large sellers standalone
  - **Effort**: L (8-16 hours) - API research required
  - **[NEEDS CLARIFICATION: Does Robinhood API provide Level 2 order book data? If not, what alternative data sources are available (Polygon.io, Alpaca, IBKR)?]**

- **US2** [P1]: As a trading bot, I want to monitor Time & Sales tape for volume spikes so that I can detect red burst patterns indicating panic selling
  - **Acceptance**:
    - System fetches real-time Time & Sales data (tick-by-tick trades)
    - Calculates 5-minute rolling average volume
    - Detects volume spikes >300% of average with >60% sell-side volume
    - Logs "red burst" alert with magnitude, sell ratio, timestamp
  - **Independent test**: Can analyze Time & Sales data and detect volume spikes independently
  - **Effort**: M (4-8 hours)
  - **[NEEDS CLARIFICATION: Does Robinhood API provide Time & Sales data? If not, what alternative is most cost-effective for retail trader usage?]**

- **US3** [P1]: As a trading bot, I want order flow alerts integrated with risk management so that I can trigger exits when selling pressure is detected
  - **Acceptance**:
    - OrderFlowDetector publishes alerts to risk management module
    - Risk management evaluates alert severity against position (stop loss, unrealized P&L)
    - Triggers exit recommendation when: 3+ large sellers in 2 minutes OR red burst >400%
    - Logs exit recommendation with reasoning (order flow pressure)
  - **Independent test**: Can trigger exit signal based on simulated order flow alerts
  - **Effort**: S (2-4 hours)
  - **Depends on**: US1, US2

**Priority 2 (Enhancement)**
- **US4** [P2]: As a trading bot, I want configurable thresholds for order flow alerts so that I can tune sensitivity based on stock volatility and liquidity
  - **Acceptance**:
    - OrderFlowConfig dataclass with thresholds: large_order_size, volume_spike_threshold, red_burst_threshold, alert_window_seconds
    - Environment variable support: ORDER_FLOW_LARGE_ORDER_SIZE, ORDER_FLOW_VOLUME_SPIKE_THRESHOLD
    - Validation: large_order_size >1000, volume_spike_threshold 1.5-10.0x, alert_window 30-300 seconds
    - Config persisted in config/order_flow_config.json
  - **Depends on**: US1, US2
  - **Effort**: S (2-4 hours)

- **US5** [P2]: As a developer, I want order flow data validated before use so that I ensure data integrity and prevent trading on stale or corrupt data
  - **Acceptance**:
    - OrderFlowValidator validates Level 2 data: timestamp freshness (<10 seconds), price bounds (>$0), order size >0
    - Validates Time & Sales data: timestamp sequence (chronological), trade price within bid-ask spread
    - Raises DataValidationError on invalid data (Constitution §Data_Integrity)
    - Logs validation failures with specific error codes
  - **Depends on**: US1, US2
  - **Effort**: S (2-4 hours)

**Priority 3 (Nice-to-have)**
- **US6** [P3]: As a trader, I want order flow metrics exported to dashboard so that I can visualize selling pressure alongside positions and P&L
  - **Acceptance**:
    - Dashboard displays: active order flow alerts, alert count (last 5 minutes), largest seller detected
    - Color-coded alerts: yellow (single large seller), orange (multiple sellers), red (red burst)
    - Historical alert log (last 30 minutes)
  - **Depends on**: US1, US2, status-dashboard (shipped)
  - **Effort**: M (4-8 hours)

- **US7** [P3]: As a developer, I want order flow detection backtestable so that I can validate effectiveness of exit signals on historical data
  - **Acceptance**:
    - Backtest engine replays historical Level 2 data (if available)
    - Measures: alert accuracy (true positives vs false positives), exit timing improvement, drawdown reduction
    - Reports: average time from alert to price drop, percentage of profitable exits
  - **Depends on**: US1, US2, backtesting-engine (not yet shipped)
  - **Effort**: L (8-16 hours)

**Effort Scale**:
- XS: <2 hours
- S: 2-4 hours
- M: 4-8 hours (½ day)
- L: 8-16 hours (1-2 days)
- XL: 16+ hours (>2 days, consider breaking down)

**MVP Strategy**: Ship US1-US3 first to establish order flow monitoring capability. Validate alert accuracy in paper trading before adding configurability (US4-US5) and visualization (US6).

## Success Metrics (HEART Framework)

> **Purpose**: Define quantified success criteria using Google's HEART framework.
> **Constraint**: All metrics MUST be Claude Code-measurable (SQL, logs, Lighthouse).

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Reduce unexpected losses | Exit before major drops | % positions exited before -5% drop | >60% early exit rate | <10% false positive exits |
| **Engagement** | Active monitoring | Alert frequency | Alerts logged per trading day | 5-15 alerts/day | <50 alerts/day (noise) |
| **Adoption** | Feature utilization | Exit signals triggered | % of exits using order flow data | >30% of exits cite order flow | >0% (feature must be used) |
| **Retention** | Continued use | Feature not disabled | Days feature remains active | 30+ consecutive days | 0 days disabled due to bugs |
| **Task Success** | Profitable exits | P&L improvement | Average exit P&L vs non-order-flow exits | +1.5% better exit timing | No worse than baseline |

**Performance Targets**:
- Alert latency: <2 seconds from data arrival to alert logged
- Data staleness: <10 seconds (fail if >30 seconds old)
- Memory usage: <50MB additional for order flow monitoring

**Measurement Plan**:
- **Logs**: `logs/order_flow/*.jsonl` - Alert counts, exit signals, latency
- **SQL**: `SELECT AVG(exit_pnl) FROM trades WHERE exit_reason='order_flow_alert'`
- **Comparison**: Baseline exits (stop loss only) vs order flow-assisted exits

## Context Strategy & Signal Design

- **System prompt altitude**: High-level strategy context - "Monitor order flow for institutional selling pressure to trigger protective exits"
- **Tool surface**: OrderFlowDetector.detect(), TapeMonitor.analyze_volume_spike(), essential for real-time analysis
- **Examples in scope**: 2 canonical examples (large seller alert, red burst pattern)
- **Context budget**: 8,000 tokens (alert detection is stateless, minimal context needed)
- **Retrieval strategy**: JIT - Fetch Level 2/Tape data only when position is active
- **Memory artifacts**: NOTES.md updated after each alert, logs/order_flow/*.jsonl for historical analysis
- **Compaction cadence**: Every 50 alerts (aggressive - order flow data is high-volume)
- **Sub-agents**: None (simple detector pattern, no sub-agent needed)

## Requirements

### Functional (testable only)

- **FR-001**: System MUST fetch Level 2 order book data from configured data source (Robinhood API or alternative)
- **FR-002**: System MUST identify sell orders exceeding configurable threshold (default: 10,000 shares) at bid or below
- **FR-003**: System MUST log large seller alerts with symbol, order size, price level, timestamp (UTC), alert severity
- **FR-004**: System MUST fetch Time & Sales data (tick-by-tick trades) from configured data source
- **FR-005**: System MUST calculate 5-minute rolling average volume from Time & Sales data
- **FR-006**: System MUST detect volume spikes exceeding configurable threshold (default: 300% of 5-min average) with >60% sell-side volume
- **FR-007**: System MUST log red burst alerts with symbol, magnitude, sell ratio, timestamp (UTC)
- **FR-008**: System MUST trigger exit signal when 3+ large seller alerts detected within configurable time window (default: 2 minutes)
- **FR-009**: System MUST trigger exit signal when red burst exceeds critical threshold (default: 400% volume spike)
- **FR-010**: System MUST validate Level 2 data freshness (timestamp <10 seconds old) before processing
- **FR-011**: System MUST validate Time & Sales data sequence (chronological order) and price bounds
- **FR-012**: System MUST gracefully degrade when Level 2/Tape data unavailable (log gap, continue with reduced monitoring)

*Mark ambiguities:*
- **FR-013**: [NEEDS CLARIFICATION: Should order flow monitoring be active only during active positions, or continuously for watchlist symbols?]

### Non-Functional

- **NFR-001**: Performance: Alert latency <2 seconds from data arrival to alert logged (P95)
- **NFR-002**: Reliability: Data validation errors MUST halt order flow monitoring (Constitution §Safety_First)
- **NFR-003**: Observability: All alerts MUST be logged to structured JSONL with UTC timestamps (Constitution §Audit_Everything)
- **NFR-004**: Configurability: Thresholds MUST be configurable via environment variables and config file
- **NFR-005**: Rate Limiting: API calls MUST respect data provider rate limits with exponential backoff (Constitution §Risk_Management)
- **NFR-006**: Memory Efficiency: Order flow monitoring MUST not exceed 50MB additional memory usage

### Key Entities (if data involved)

- **OrderFlowAlert**: Alert dataclass with fields: symbol, alert_type (large_seller|red_burst), severity (warning|critical), order_size, price_level, volume_ratio, timestamp_utc
- **OrderBookSnapshot**: Level 2 data with fields: symbol, bids (list of [price, size]), asks (list of [price, size]), timestamp_utc
- **TimeAndSalesRecord**: Tick data with fields: symbol, price, size, side (buy|sell), timestamp_utc
- **OrderFlowConfig**: Configuration with fields: large_order_size_threshold, volume_spike_threshold, red_burst_threshold, alert_window_seconds, data_source

## Deployment Considerations

> **Purpose**: Document deployment constraints and dependencies for planning phase.

### Platform Dependencies

**Vercel** (marketing/app):
- None (backend-only feature)

**Railway** (API):
- None (local Python execution, not Railway-hosted)

**Dependencies**:
- **CRITICAL**: robin_stocks library (check if Level 2/Tape supported)
- **Alternative**: Polygon.io SDK (polygon-api-client), Alpaca SDK (alpaca-trade-api), or IBKR API
- **New**: pandas-market-calendars (for market hours validation)

### Environment Variables

**New Required Variables**:
- `ORDER_FLOW_DATA_SOURCE`: Data provider (robinhood|polygon|alpaca|ibkr) - default: robinhood
- `ORDER_FLOW_API_KEY`: API key for Level 2/Tape data provider (if not Robinhood)
- `ORDER_FLOW_LARGE_ORDER_SIZE`: Threshold for large order detection (default: 10000 shares)
- `ORDER_FLOW_VOLUME_SPIKE_THRESHOLD`: Multiplier for volume spike detection (default: 3.0x)
- `ORDER_FLOW_RED_BURST_THRESHOLD`: Critical volume spike threshold (default: 4.0x)
- `ORDER_FLOW_ALERT_WINDOW_SECONDS`: Time window for consecutive alert detection (default: 120 seconds)

**Changed Variables**:
- None

**Schema Update Required**: Yes - Add order_flow section to config/config.schema.json in /plan phase

### Breaking Changes

**API Contract Changes**:
- No (new feature, no existing API to break)

**Database Schema Changes**:
- No (uses file-based logging, no DB schema)

**Auth Flow Modifications**:
- No (uses existing RobinhoodAuth)

**Client Compatibility**:
- Backward compatible (new module, opt-in feature)

### Migration Requirements

**Database Migrations**:
- No (no database schema)

**Data Backfill**:
- Not required (real-time monitoring only)

**RLS Policy Changes**:
- No (no database)

**Reversibility**:
- Fully reversible (remove ORDER_FLOW_* env vars, module gracefully skips when not configured)

### Rollback Considerations

**Standard Rollback**:
- Yes: 3-command rollback via git revert

**Special Rollback Needs**:
- None (stateless monitoring, no persistent state to rollback)

**Deployment Metadata**:
- Deploy IDs tracked in specs/028-level-2-order-flow-i/NOTES.md (Deployment Metadata section)

---

## Measurement Plan

> **Purpose**: Define how success will be measured using Claude Code-accessible sources.
> **Sources**: SQL queries, structured logs, Lighthouse CI, database aggregates.

### Data Collection

**Analytics Events** (dual instrumentation):
- PostHog (dashboards): N/A (backend-only)
- Structured logs (Claude measurement): `logger.info({ event: "order_flow_alert", ...props })`
- Database (A/B tests): N/A (no database)

**Key Events to Track**:
1. `order_flow.large_seller_detected` - Large order detection
2. `order_flow.red_burst_detected` - Volume spike detection
3. `order_flow.exit_signal_triggered` - Exit recommendation
4. `order_flow.data_validation_error` - Data quality issue
5. `order_flow.alert_window_expired` - Alert cooldown

### Measurement Queries

**Logs** (`logs/order_flow/*.jsonl`):
- Alert frequency: `grep '"event":"order_flow_alert"' logs/order_flow/*.jsonl | wc -l`
- Exit signal count: `grep '"event":"order_flow.exit_signal_triggered"' logs/order_flow/*.jsonl | wc -l`
- False positive rate: `grep '"alert_followed_by_drop":false' logs/order_flow/*.jsonl | wc -l` / total alerts
- Alert latency P95: `jq -r '.latency_ms' logs/order_flow/*.jsonl | sort -n | awk '{a[NR]=$1} END {print a[int(NR*0.95)]}'`

**Trade Logs** (`logs/trades.log`):
- Order flow exits: `grep '"exit_reason":"order_flow_alert"' logs/trades.log | wc -l`
- Average P&L: `grep '"exit_reason":"order_flow_alert"' logs/trades.log | jq -r '.exit_pnl' | awk '{sum+=$1; count++} END {print sum/count}'`
- Comparison baseline: `grep '"exit_reason":"stop_loss"' logs/trades.log | jq -r '.exit_pnl' | awk '{sum+=$1; count++} END {print sum/count}'`

**Performance**:
- Memory usage: `ps aux | grep trading_bot | awk '{print $6}'` (before and after feature)
- Latency: Extract from `logs/order_flow/*.jsonl` field `latency_ms`

### Experiment Design (A/B Test)

**Variants**:
- Control: Exit on stop loss only (current behavior)
- Treatment: Exit on order flow alerts + stop loss (new behavior)

**Ramp Plan**:
1. Paper Trading (Days 1-7): Validate alert accuracy, zero false positives tolerance
2. Single Symbol (Days 8-14): Live trading on one symbol, monitor closely
3. Full Watchlist (Days 15+): Apply to all positions if P&L improvement >1%

**Kill Switch**: False positive rate >20% OR alert latency >10 seconds → instant disable

**Sample Size**: 30+ trades per variant (minimum for statistical validity)

---

## Quality Gates *(Must pass before `/plan`)*

### Core (Always Required)
- [ ] Requirements testable, max 3 [NEEDS CLARIFICATION] markers (currently 3 markers)
- [ ] Constitution aligned (§Data_Integrity, §Audit_Everything, §Safety_First, §Risk_Management)
- [ ] No implementation details (tech stack, APIs, code)

### Conditional: Success Metrics (Required - measurable feature)
- [ ] HEART metrics defined with Claude Code-measurable sources (logs, trade data)
- [ ] Hypothesis N/A (new feature, not improvement)

### Conditional: UI Features (Skipped - backend-only)
- N/A

### Conditional: Deployment Impact (Required - new dependencies)
- [ ] Breaking changes identified (None - backward compatible)
- [ ] Environment variables documented (6 new ORDER_FLOW_* variables)
- [ ] Rollback plan specified (standard 3-command rollback)

## Assumptions

1. **Data Availability**: Assumes Level 2 and Time & Sales data available from Robinhood API or alternative provider. If Robinhood does not support, will use Polygon.io or Alpaca.
2. **Latency Tolerance**: Assumes 2-second alert latency acceptable for day trading use case (sub-second not required).
3. **Position Context**: Assumes order flow monitoring active only during active positions (not continuous watchlist monitoring).
4. **Market Hours**: Assumes order flow detection operates during regular trading hours (7am-10am EST per Constitution).
5. **Exit Authority**: Assumes order flow alerts are recommendations to risk management, not automatic exits (human-in-loop for now).
