# Feature Specification: Daily Profit Goal Management

**Branch**: `feature/026-daily-profit-goal-ma`
**Created**: 2025-10-21
**Status**: Draft
**ICE Score**: 1.60 (Impact: 4, Effort: 2, Confidence: 0.8)

## User Scenarios

### Primary User Story
As a day trader using the bot, I want the system to automatically protect my profits by exiting all positions when I've given back half of my daily gains, so that I preserve capital and avoid giving back hard-earned profits due to overtrading or market reversals.

### Acceptance Scenarios
1. **Given** the bot has a daily profit target of $500 and current profit is $600, **When** profit drops to $300 (half of peak $600), **Then** the system triggers an exit signal and logs the profit protection event.
2. **Given** market opens at 9:30 AM EST, **When** the trading session starts, **Then** the profit goal tracker resets daily P&L to $0 and begins tracking from zero.
3. **Given** the bot has multiple open positions with unrealized profit of $400, **When** the user configures a daily target of $300, **Then** the system tracks progress toward goal (133% of target) and monitors for drawdown threshold.
4. **Given** the profit protection threshold is triggered, **When** the bot attempts to enter a new trade, **Then** the system blocks the trade and logs the blocked attempt with reason "Daily profit protection active".

### Edge Cases
- What happens when market gaps down at open causing immediate profit giveback? System detects peak-to-current drawdown and triggers protection if threshold exceeded.
- How does system handle partial fills that change P&L mid-calculation? Uses atomic state snapshots with timestamp to ensure consistent calculations.
- What if user manually overrides an exit during profit protection? System logs override event and warning, allows manual control but maintains audit trail.
- How does system handle timezone changes or daylight savings? All timestamps in UTC, market open detection uses pytz with DST-aware Eastern timezone conversion.

## User Stories (Prioritized)

### Story Prioritization

**Priority 1 (MVP) 🎯**
- **US1** [P1]: As a trader, I want to set a daily profit target so that the system knows when I've achieved my goal.
  - **Acceptance**:
    - User can configure daily profit target in dollars (e.g., $500)
    - Target persists across bot restarts
    - Validation ensures target is positive number
    - Default target is $0 (feature disabled)
  - **Independent test**: Configure target to $300, verify config loads correctly, restart bot and verify persistence
  - **Effort**: S (2-3 hours)

- **US2** [P1]: As a trader, I want the system to track my realized and unrealized P&L throughout the day so that I know my progress toward my profit goal.
  - **Acceptance**:
    - System queries current positions and calculates unrealized P&L
    - System sums realized P&L from closed trades
    - Daily P&L = realized P&L + unrealized P&L
    - P&L calculation updates on every trade event (entry, exit, price update)
    - Daily peak profit tracked (highest P&L value during session)
  - **Independent test**: Execute 2 trades (1 closed winner +$100, 1 open position +$50), verify daily P&L = $150, verify peak profit = $150
  - **Effort**: M (4-6 hours)

- **US3** [P1]: As a trader, I want the system to detect when I've given back half of my daily profit so that I'm alerted to stop trading and preserve gains.
  - **Acceptance**:
    - System detects peak daily profit (highest value reached)
    - System calculates drawdown from peak: (peak - current) / peak
    - When drawdown ≥ 50%, system triggers profit protection mode
    - System logs profit protection trigger event with timestamp, peak profit, current profit, drawdown percentage
    - Profit protection mode blocks new trade entries
    - Profit protection mode resets at next market open (4:00 AM EST)
  - **Independent test**: Simulate peak profit $600, drop current profit to $300, verify protection triggers, attempt new trade and verify blocked
  - **Effort**: M (5-7 hours)

**Priority 2 (Enhancement)**
- **US4** [P2]: As a trader, I want configurable profit protection thresholds (not just 50%) so that I can customize my risk management strategy.
  - **Acceptance**:
    - User can configure profit giveback threshold (default 50%, range 10%-90%)
    - Threshold validation prevents invalid values
    - System uses custom threshold in drawdown calculation
  - **Depends on**: US1, US2, US3
  - **Effort**: XS (1-2 hours)

- **US5** [P2]: As a trader, I want to see profit goal progress in the status dashboard so that I can monitor my performance at a glance.
  - **Acceptance**:
    - Dashboard displays daily profit target
    - Dashboard displays current P&L (realized + unrealized)
    - Dashboard displays progress percentage (current / target * 100)
    - Dashboard displays peak profit reached today
    - Dashboard displays profit protection status (active/inactive)
    - Updates refresh every 30 seconds
  - **Depends on**: US1, US2, US3
  - **Effort**: S (3-4 hours)

**Priority 3 (Nice-to-have)**
- **US6** [P3]: As a trader, I want historical profit protection events logged so that I can analyze how often this rule saves me from overtrading.
  - **Acceptance**:
    - All profit protection triggers logged to JSONL file (logs/profit-protection/YYYY-MM-DD.jsonl)
    - Log includes: timestamp, peak_profit, current_profit, drawdown_percent, threshold, session_id
    - TradeQueryHelper extended with query_profit_protection_events(date_range)
    - Analytics: count of protection triggers per week/month
  - **Depends on**: US3
  - **Effort**: S (2-3 hours)

**Effort Scale**:
- XS: <2 hours
- S: 2-4 hours
- M: 4-8 hours (½ day)
- L: 8-16 hours (1-2 days)
- XL: 16+ hours (>2 days, consider breaking down)

**MVP Strategy**: Ship US1-US3 first (core profit protection logic), validate with paper trading for 5-10 sessions, then add US4-US6 based on usage patterns and trader feedback.

## Success Metrics (HEART Framework)

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Traders feel confident their profits are protected | Profit protection triggers prevent large drawdowns | `SELECT COUNT(*) FROM profit_protection_events WHERE drawdown_prevented > 0.3` | ≥2 protection events per week | No false triggers (drawdown <40%) |
| **Engagement** | Daily profit target drives focused trading | Target achievement rate improves over time | `SELECT COUNT(*) FILTER (WHERE daily_pnl >= target) * 100.0 / COUNT(*) FROM trading_sessions` | ≥40% target achievement rate | <20% days ending in protection mode |
| **Adoption** | All active traders configure profit targets | Configuration compliance rate | `SELECT COUNT(DISTINCT user_id) FROM profit_goal_config WHERE target > 0` / total_active_traders | 100% of active traders | Target values are realistic ($100-$1000 range) |
| **Retention** | Profit protection reduces consecutive loss days | Fewer 3+ day losing streaks after feature launch | `SELECT AVG(streak_length) FROM losing_streaks WHERE end_date > launch_date` | <2 day average streak (down from 3) | Win rate remains ≥45% |
| **Task Success** | Profit protection activates when needed | Protection trigger accuracy (true positives) | `SELECT COUNT(*) FROM profit_protection_events WHERE peak_profit > target * 1.5` | ≥80% of triggers occur above 1.5x target | <5% false negatives (missed protection opportunities) |

**Measurement Sources**:
- SQL queries on logs/profit-protection/*.jsonl
- SQL queries on logs/trades/*.jsonl (via TradeQueryHelper)
- Aggregated daily session summaries in logs/performance/

## Requirements

### Functional (testable only)

- **FR-001**: System MUST allow configuration of daily profit target in dollars (positive decimal value, default $0)
- **FR-002**: System MUST calculate daily P&L as sum of realized P&L (closed trades) and unrealized P&L (open positions)
- **FR-003**: System MUST track peak daily profit (highest P&L value reached during trading session)
- **FR-004**: System MUST detect profit giveback threshold breach when (peak - current) / peak ≥ 50%
- **FR-005**: System MUST trigger profit protection mode when giveback threshold is breached
- **FR-006**: System MUST block new trade entries when profit protection mode is active
- **FR-007**: System MUST allow manual exits of existing positions when profit protection mode is active
- **FR-008**: System MUST reset daily P&L, peak profit, and profit protection status at market open (4:00 AM EST)
- **FR-009**: System MUST log all profit protection events to structured JSONL file (timestamp, peak, current, drawdown, threshold)
- **FR-010**: System MUST validate profit target configuration (positive number, range $10-$10,000)
- **FR-011**: System MUST persist profit target configuration across bot restarts
- **FR-012**: System MUST expose profit goal status via status dashboard (current P&L, peak, target, protection status)

### Non-Functional

- **NFR-001**: Performance: P&L calculation MUST complete in <100ms per update (real-time requirement)
- **NFR-002**: Reliability: Profit protection state MUST persist across bot crashes (use file-based state)
- **NFR-003**: Accuracy: P&L calculations MUST use Decimal precision to avoid floating-point errors
- **NFR-004**: Auditability: All state changes (target updates, protection triggers, resets) MUST be logged with reasoning
- **NFR-005**: Testability: Code coverage MUST be ≥90% with unit tests for all core logic
- **NFR-006**: Type Safety: All functions MUST use type hints (mypy --strict compliant)

### Key Entities

- **ProfitGoalConfig**: Configuration dataclass (target: Decimal, threshold: Decimal, enabled: bool)
- **DailyProfitState**: State tracking dataclass (daily_pnl: Decimal, peak_profit: Decimal, realized_pnl: Decimal, unrealized_pnl: Decimal, protection_active: bool, last_reset: datetime)
- **ProfitProtectionEvent**: Event log dataclass (timestamp: datetime, peak_profit: Decimal, current_profit: Decimal, drawdown_percent: Decimal, threshold: Decimal, session_id: str)

## Deployment Considerations

### Platform Dependencies

**Railway** (API): None (local-only feature, no platform changes)

**Dependencies**: None (uses existing dependencies: robin_stocks, pandas, pytz)

### Environment Variables

**New Optional Variables**:
- `PROFIT_TARGET_DAILY`: Daily profit target in dollars (optional, defaults to $0 which disables feature)
- `PROFIT_GIVEBACK_THRESHOLD`: Profit drawdown threshold 0-1 (optional, defaults to 0.50 for 50%)

**Schema Update Required**: No (optional configuration, not required for bot operation)

### Breaking Changes

**API Contract Changes**: No (local module, no API surface)

**Database Schema Changes**: No (file-based state and logging, no database)

**Auth Flow Modifications**: No

**Client Compatibility**: N/A (local-only feature)

### Migration Requirements

**Database Migrations**: Not required (uses file-based state)

**Data Backfill**: Not required (starts fresh at next market open)

**RLS Policy Changes**: N/A

**Reversibility**: Fully reversible (delete module files, remove config vars, restart bot)

### Rollback Considerations

**Standard Rollback**: Yes (3-command rollback)
```bash
# 1. Remove feature files
rm -rf src/trading_bot/profit_goal/
# 2. Remove config from .env
sed -i '/PROFIT_TARGET_DAILY/d' .env
# 3. Restart bot
python -m trading_bot.bot
```

**Special Rollback Needs**: None (stateless at startup, no persistent dependencies)

**Deployment Metadata**: Deploy IDs tracked in specs/026-daily-profit-goal-ma/NOTES.md

---

## Measurement Plan

### Data Collection

**Structured Logs** (dual instrumentation):
- Profit protection events: `logs/profit-protection/YYYY-MM-DD.jsonl`
- Trade events: `logs/trades/YYYY-MM-DD.jsonl` (existing)
- Performance events: `logs/performance/performance-alerts.jsonl` (existing)

**Key Events to Track**:
1. `profit_goal.configured` - Adoption (when target is set)
2. `profit_goal.target_achieved` - Task Success (when daily P&L ≥ target)
3. `profit_goal.protection_triggered` - Core metric (when 50% giveback detected)
4. `profit_goal.trade_blocked` - Effectiveness (when protection prevents entry)
5. `profit_goal.daily_reset` - System health (reset at market open)

### Measurement Queries

**Logs** (`logs/profit-protection/*.jsonl`):
```bash
# Protection trigger count per week
grep '"event":"protection_triggered"' logs/profit-protection/*.jsonl | jq -r '.timestamp[:10]' | sort | uniq -c

# Average drawdown at trigger
grep '"event":"protection_triggered"' logs/profit-protection/*.jsonl | jq '.drawdown_percent' | awk '{sum+=$1; n++} END {print sum/n}'

# Profit preserved (peak - trigger level)
grep '"event":"protection_triggered"' logs/profit-protection/*.jsonl | jq '{peak, current, saved: (.peak - .current)}'
```

**Trades** (`logs/trades/*.jsonl` via TradeQueryHelper):
```python
# Target achievement rate
df = query_helper.get_daily_summaries()
achievement_rate = (df['daily_pnl'] >= df['target']).mean() * 100

# Win rate before vs after feature launch
pre_launch_winrate = df[df['date'] < launch_date]['win_rate'].mean()
post_launch_winrate = df[df['date'] >= launch_date]['win_rate'].mean()
```

### Experiment Design

Not applicable (no A/B test needed - feature is opt-in via configuration, default disabled)

---

## Quality Gates *(Must pass before `/plan`)*

### Core (Always Required)
- [x] Requirements testable, no [NEEDS CLARIFICATION] markers
- [x] Constitution aligned (§Risk_Management, §Safety_First, §Audit_Everything, §Testing_Requirements)
- [x] No implementation details (tech stack focused on "what" not "how")

### Conditional: Success Metrics (Skip if no user tracking)
- [x] HEART metrics defined with Claude Code-measurable sources (SQL, JSONL logs)
- [ ] Hypothesis stated - N/A (new feature, not improving existing flow)

### Conditional: UI Features (Skip if backend-only)
- [ ] All screens identified - N/A (backend-only feature, dashboard integration only)
- [ ] System components planned - N/A

### Conditional: Deployment Impact (Skip if no infrastructure changes)
- [x] Breaking changes identified - None (local-only feature)
- [x] Environment variables documented - Optional config vars with defaults
- [x] Rollback plan specified - 3-command rollback documented

## Assumptions

1. **Market open time**: Assumes US Eastern timezone with automatic DST handling via pytz
2. **P&L calculation frequency**: Assumes P&L updates on every trade event and periodic price updates (every 30 seconds)
3. **State persistence**: Uses file-based state persistence (logs/profit-goal-state.json) for crash recovery
4. **Integration point**: Integrates with existing SafetyChecks module for trade blocking
5. **Dashboard display**: Assumes existing status-dashboard feature (shipped) for profit goal display
6. **Performance data**: Reuses existing PerformanceTracker (shipped) for daily P&L aggregation

## Dependencies

**Required (Shipped)**:
- performance-tracking v1.0.0 ✅ (PerformanceTracker, daily aggregation)
- safety-checks ✅ (SafetyChecks module, circuit breaker pattern)
- trade-logging ✅ (TradeRecord, StructuredTradeLogger, JSONL format)
- status-dashboard v1.0.0 ✅ (Dashboard display integration)

**Optional Integration**:
- order-management ✅ (trade blocking integration point)

## Out of Scope

1. **Weekly/Monthly profit targets** - Only daily targets in MVP
2. **Multi-tier targets** (e.g., first target $300, stretch target $500) - Single target only
3. **Profit locking at intervals** (e.g., lock in 50% at 1.5x target) - Only drawdown protection
4. **Machine learning target suggestions** - User-configured targets only
5. **Social sharing of profit milestones** - Internal tracking only
6. **Tax optimization** (realized vs unrealized gains) - Pure P&L tracking, no tax logic
