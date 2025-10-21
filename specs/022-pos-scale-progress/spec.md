# Feature Specification: Position Scaling & Phase Progression

**Branch**: `feature/022-pos-scale-progress`
**Created**: 2025-10-21
**Status**: Draft
**Area**: strategy
**From Roadmap**: Yes (Impact: 5, Effort: 3, Confidence: 0.8, Score: 1.33)
**Dependencies**: performance-tracking ✅, safety-checks ✅, backtesting-engine ✅

## User Scenarios

### Primary User Story
As a trading bot operator, I need a phase-based progression system that prevents me from scaling position sizes too quickly, enforces mandatory profitability gates between phases, and tracks my trading consistency so I can safely progress from paper trading to small live positions to full-scale trading.

### Acceptance Scenarios
1. **Given** I'm in Experience phase (paper trading only), **When** I attempt to switch to Proof of Concept phase, **Then** the system blocks the switch until I have completed 20+ profitable simulated sessions with win rate ≥60% and average R:R ≥1.5, and logs the validation result.

2. **Given** I'm in Proof of Concept phase (1 trade/day max, $100 position size), **When** I successfully place a trade, **Then** the system blocks additional trades for 24 hours and logs a countdown message showing when the next trade is allowed.

3. **Given** I'm in Real Money Trial phase with 10 consecutive profitable sessions, **When** the phase progression validator runs, **Then** it automatically suggests advancing to Scaling phase with increased position size ($200 → $500) and logs the recommendation with supporting metrics.

4. **Given** I'm in Scaling phase with gradually increasing position sizes, **When** my rolling 20-trade win rate drops below 55%, **Then** the system automatically downgrades me to Trial phase, reduces position size by 50%, and triggers a circuit breaker requiring manual acknowledgment.

5. **Given** I'm in any phase with active positions, **When** I attempt to manually override the phase restrictions, **Then** the system blocks the override (except for emergency exits), logs the attempt, and displays the current phase constraints.

6. **Given** I complete 100 trades in Scaling phase with consistent profitability (win rate ≥65%, R:R ≥2.0), **When** the phase evaluator runs, **Then** it maintains Scaling phase status and continues gradual position size increases up to configured maximum.

### Edge Cases
- What happens if profitability degrades mid-phase? → Automatic downgrade to previous phase with 50% position size reduction and circuit breaker activation
- How are phase transitions recorded? → Log each transition with timestamp, metrics snapshot, and reason in `logs/phase-history.jsonl`
- What if session count is reset? → Prevent reset without manual override + administrator password confirmation
- How are emergency exits handled? → Always permitted regardless of phase restrictions, logged separately as emergency actions
- What if user tries to skip phases? → Blocked - must progress sequentially through all phases (Experience → PoC → Trial → Scaling)

## User Stories (Prioritized)

> **Purpose**: Break down feature into independently deliverable stories for MVP-first delivery.
> **Format**: [P1] = MVP (ship first), [P2] = Enhancement, [P3] = Nice-to-have

### Story Prioritization

**Priority 1 (MVP) 🎯**

- **US1** [P1]: As a bot operator, I want a phase mode system that enforces Experience (simulator only) → Proof of Concept (1 trade/day) → Real Money Trial (small size) → Scaling (gradual increases) progression so that I cannot prematurely scale before proving consistent profitability
  - **Acceptance**:
    - Phase enum defined (Experience, PoC, Trial, Scaling)
    - Current phase persisted in config/database
    - Phase transition logic with profitability gates
    - Manual phase changes blocked without criteria met
  - **Independent test**: Create bot in Experience phase, attempt to switch to PoC without meeting criteria (20+ sessions, 60% win rate) - should block
  - **Effort**: L (12 hours)

- **US2** [P1]: As a bot operator in Proof of Concept phase, I want the system to enforce 1 trade per day maximum and block additional trades after the daily limit is hit so that I maintain disciplined evaluation of my strategy
  - **Acceptance**:
    - Trade counter resets daily at market open
    - Blocks trades when limit reached
    - Displays countdown to next allowed trade
    - Emergency exit override available
  - **Independent test**: Place 1 trade in PoC phase, attempt second trade - should block with countdown message
  - **Effort**: M (6 hours)

- **US3** [P1]: As a bot operator, I want the system to track profitability of the last 10-20 sessions and verify consistent win rates before allowing phase advancement so that I don't scale during lucky streaks
  - **Acceptance**:
    - Session profitability tracker (P&L, win rate, R:R per session)
    - Rolling window validation (configurable: 10, 20, or 50 sessions)
    - Profitability criteria per phase (Experience: 60%, Trial: 65%, Scaling: 70%)
    - Automated validation report before phase transition
  - **Independent test**: Complete 15 sessions with 65% win rate, request phase advance - should approve; Complete 15 sessions with 50% win rate - should reject
  - **Effort**: L (10 hours)

**Priority 2 (Enhancement)**

- **US4** [P2]: As a bot operator, I want position sizes to gradually increase from 100 shares based on consistency metrics (consecutive wins, streak stability) so that successful strategies can scale naturally
  - **Acceptance**:
    - Position size calculator based on phase and consistency
    - Experience: N/A (paper), PoC: $100, Trial: $200, Scaling: $200-$2000 (gradual)
    - Increase triggers: 5 consecutive wins, 10-session win rate ≥70%
    - Decrease triggers: 3 consecutive losses, win rate <55%
  - **Depends on**: US1, US3
  - **Effort**: M (8 hours)

- **US5** [P2]: As a bot operator, I want automatic phase downgrades when performance degrades (consecutive losses, low win rate) to protect my capital during drawdowns
  - **Acceptance**:
    - Downgrade triggers configurable per phase
    - Automatic rollback: Scaling → Trial → PoC → Experience
    - Circuit breaker activation on downgrade
    - Email/log alert on phase change
  - **Depends on**: US1, US3
  - **Effort**: M (6 hours)

**Priority 3 (Nice-to-have)**

- **US6** [P3]: As a bot operator, I want to export session summary reports showing phase history, win rates, and progression criteria status for manual review and compliance
  - **Acceptance**:
    - CSV export: session date, phase, trades, win rate, R:R, P&L, position size
    - Phase history timeline
    - Progression readiness dashboard
  - **Depends on**: US1, US3
  - **Effort**: S (4 hours)

**Effort Scale**:
- XS: <2 hours
- S: 2-4 hours
- M: 4-8 hours (½ day)
- L: 8-16 hours (1-2 days)
- XL: 16+ hours (>2 days, consider breaking down)

**MVP Strategy**: Ship US1-US3 first (phase system + trade limits + profitability tracking), validate with paper trading for 2 weeks, then incrementally add US4 (gradual scaling) and US5 (auto-downgrade) based on operator feedback.

## Visual References

N/A – backend strategy/risk management feature (no UI components).

## Success Metrics (HEART Framework)

> **Purpose**: Define quantified success criteria using Google's HEART framework.
> **Constraint**: All metrics MUST be measurable via logs, config files, and performance data.

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Prevent premature scaling losses | Capital preservation events | `phase.downgrade` events per month | ≤1/month after stabilization | >3/month triggers strategy review |
| **Engagement** | Encourage long-term discipline | Phase adherence duration | Average days per phase before advancement | Experience: 30 days, PoC: 60 days, Trial: 90 days | <15 days in any phase triggers compliance alert |
| **Adoption** | Enforce phase-based workflow | Manual override attempts | `phase.override_blocked` vs total trades | ≥98% blocked (only emergency exits allowed) | <95% triggers enforcement review |
| **Retention** | Sustain operator confidence | Continued bot usage after losses | Active trading days per month | ≥15 days/month | <10 days/month after losses suggests abandonment |
| **Task Success** | Achieve profitability before scaling | Phase advancement success rate | Operators reaching Scaling phase with profitability | ≥80% reach Scaling without major losses | <60% suggests criteria too lax |

**Performance Targets**:
- Phase validation check ≤50 ms (runs before each trade)
- Session profitability calculation ≤200 ms for 1,000 trades
- Phase history export ≤1 second for full trading history

## Hypothesis

**Problem**: Operators currently lack systematic progression controls, leading to premature scaling during winning streaks followed by capital loss during drawdowns. Manual discipline alone is insufficient.
- Evidence: Constitution §Safety_First emphasizes testing before real money, but no enforcement mechanism exists (specs/safety-checks/spec.md).
- Evidence: Performance tracking spec shows metrics exist but no automated progression gates (specs/performance-tracking/spec.md).
- Impact: Undisciplined operators risk significant capital loss by scaling before strategy validation.

**Solution**: Implement a mandatory four-phase progression system (Experience → PoC → Trial → Scaling) with automated profitability validation, trade limits per phase, and downgrade mechanisms on poor performance.
- Change: New `PhaseManager` service with phase transition logic, profitability validators, and position size calculators
- Mechanism: Enforces Constitution §Safety_First and §Risk_Management through programmatic gates rather than operator discipline

**Prediction**: Phase-based progression will reduce premature scaling incidents from ~40% (estimated) to <5% by enforcing 60+ days of profitable trading before live scaling.
- Primary metric: Percentage of operators losing >10% capital in first 90 days drops from 40% to <5%
- Expected improvement: -87.5% capital loss incidents
- Confidence: High (based on industry best practices for prop trading firms)

## Context Strategy & Signal Design

- **System prompt altitude**: Service-level specification focused on phase state management, profitability validation, and trade enforcement contracts
- **Tool surface**: Python phase manager service, config validation, performance data queries, structured logging
- **Examples in scope**: (1) Phase transition validation, (2) Daily trade limit enforcement, (3) Automatic downgrade on losses
- **Context budget**: Target ≤40k tokens for implementation; compact NOTES.md after research
- **Retrieval strategy**: Upfront - load performance-tracking, safety-checks, backtesting-engine patterns
- **Memory artifacts**: NOTES.md updated after each major decision, TODO.md for task tracking
- **Compaction cadence**: After initial research, before planning phase
- **Sub-agents**: Backend implementation agent for phase logic, QA agent for validation testing

## Requirements

### Functional (testable only)

**FR-001: Phase System Foundation**
- System MUST maintain four distinct phases: Experience (paper only), Proof of Concept (1 trade/day max), Real Money Trial (small size), Scaling (gradual increases)
- Current phase MUST be persisted in configuration and logged on every trade
- Phase transitions MUST be unidirectional (Experience → PoC → Trial → Scaling)
- Manual phase rollbacks MUST require administrator override with password confirmation

**FR-002: Phase Transition Gates**
- Experience → PoC transition MUST require:
  - Minimum 20 profitable simulated sessions
  - Win rate ≥60%
  - Average risk-reward ratio ≥1.5
  - Zero manual override incidents
- PoC → Trial transition MUST require:
  - Minimum 30 trading days in PoC
  - 1 trade executed per day (no missed days >3 in a row)
  - Win rate ≥65% over last 50 trades
  - Average R:R ≥1.8
- Trial → Scaling transition MUST require:
  - Minimum 60 trading days in Trial
  - Win rate ≥70% over last 100 trades
  - Average R:R ≥2.0
  - Maximum drawdown <5%
- All transitions MUST be validated automatically before approval
- Failed validations MUST log specific criteria failures

**FR-003: Trade Limit Enforcement**
- Proof of Concept phase MUST enforce 1 trade per calendar day maximum
- Trade counter MUST reset at market open (7:00 AM EST)
- Additional trades MUST be blocked with countdown to next allowed trade
- Emergency exits MUST be permitted regardless of daily limit
- Override attempts MUST be logged with operator ID and timestamp

**FR-004: Profitability Tracking**
- System MUST track session-level profitability: date, total P&L, trades executed, win rate, average R:R, position sizes
- Rolling window validation MUST support configurable periods: 10, 20, 50, 100 sessions
- Profitability data MUST persist in `logs/phase-history.jsonl` as structured JSONL
- Win rate calculation MUST exclude emergency exits and manual overrides

**FR-005: Position Size Progression**
- Experience phase: Position sizes are simulated (no real money)
- PoC phase: Fixed $100 per position
- Trial phase: Fixed $200 per position
- Scaling phase: $200-$2,000 based on consistency:
  - Start: $200
  - After 5 consecutive wins: +$100
  - After 10-session win rate ≥70%: +$200
  - Maximum: $2,000 or 5% of portfolio (whichever is lower)
- Position size increases MUST log justification (e.g., "5 consecutive wins")

**FR-006: Automatic Downgrade**
- System MUST downgrade phase when:
  - 3 consecutive losses detected
  - Rolling 20-trade win rate <55%
  - Daily loss exceeds 5% in Trial or Scaling phase
- Downgrade MUST reduce position size by 50%
- Downgrade MUST trigger circuit breaker (manual restart required)
- Downgrade events MUST log full context: phase before/after, trigger reason, metrics snapshot

**FR-007: Manual Override Controls**
- Manual phase changes MUST be blocked without profitability criteria met
- Emergency exit override MUST be available in all phases
- Override password MUST be configurable in environment variables
- All override attempts (successful and blocked) MUST be logged to `logs/phase-overrides.jsonl`

**FR-008: Phase History Export**
- System MUST support exporting phase history to CSV
- Export MUST include: date range, phase transitions, session metrics, profitability summary
- Export command: `python -m trading_bot.phase export --start YYYY-MM-DD --end YYYY-MM-DD`

### Non-Functional

**NFR-001: Performance**
- Phase validation check MUST complete in ≤50 ms
- Session profitability calculation MUST complete in ≤200 ms for 1,000 trades
- Phase history export MUST complete in ≤1 second for full trading history
- Phase transition validation MUST complete in ≤500 ms

**NFR-002: Data Integrity**
- All phase transitions MUST be atomic (no partial updates)
- Session profitability data MUST use Decimal for precision (no float rounding)
- Phase history logs MUST be append-only (no edits or deletions)
- Timestamps MUST be UTC with timezone awareness

**NFR-003: Security**
- Override password MUST be stored as environment variable (never in config files)
- Phase history exports MUST redact sensitive data (API keys, passwords)
- Manual overrides MUST require password confirmation (not stored in session)

**NFR-004: Error Handling**
- Phase validation failures MUST return specific error messages (not generic "validation failed")
- Missing profitability data MUST default to conservative assumption (block phase advance)
- Corrupt phase history MUST trigger data recovery from previous checkpoint
- Circuit breaker failures MUST halt all trading (fail-safe)

### Key Entities

**Phase** (enum):
- Values: Experience, ProofOfConcept, RealMoneyTrial, Scaling
- Current phase stored in `Config.trading_phase`
- Phase history logged in `logs/phase-history.jsonl`

**SessionMetrics** (dataclass):
- date: date
- phase: Phase
- trades_executed: int
- win_rate: Decimal
- average_rr: Decimal
- total_pnl: Decimal
- position_sizes: List[Decimal]
- circuit_breaker_trips: int

**PhaseTransition** (dataclass):
- timestamp: datetime (UTC)
- from_phase: Phase
- to_phase: Phase
- trigger: str (auto | manual)
- validation_passed: bool
- criteria: Dict[str, Any] (win_rate, rr, session_count, etc.)

## Deployment Considerations

### Platform Dependencies
None - Local-only feature (no remote services required)

### Environment Variables
```bash
# Phase override password (optional, for emergency manual changes)
PHASE_OVERRIDE_PASSWORD=<secure-password>

# Phase history log directory
PHASE_HISTORY_DIR=logs/phase/
```

### Breaking Changes
None - New feature, no existing phase system to replace

### Migration Required
No database migration - uses config file (`config.json`) and JSONL logs

### Rollback Considerations
Standard 3-command rollback:
```bash
git revert <commit-hash>
git push
# Restart bot
```

Phase history preserved in logs - rollback does not delete historical data

## Dependencies

**Completed Dependencies**:
- ✅ **performance-tracking**: Provides session metrics calculation (win rate, R:R, P&L)
- ✅ **safety-checks**: Provides circuit breaker infrastructure
- ✅ **backtesting-engine**: Provides historical validation for Experience phase

**Integration Points**:
- `TradingBot.execute_trade()` - Add phase validation check before trade execution
- `SafetyChecks.validate_trade()` - Integrate phase-specific limits (trade count, position size)
- `PerformanceTracker.generate_summary()` - Add session metrics to phase history
- `ModeSwitcher` - Enforce paper trading in Experience phase

## Success Criteria

> All criteria MUST be measurable, technology-agnostic, user-focused, and verifiable.

1. **Phase Enforcement**: System blocks 100% of out-of-phase trades (measured via logs: `phase.validation_blocked` events)

2. **Profitability Gates**: Operators cannot advance to next phase without meeting criteria (measured via: phase transition rejection rate ≥95% for non-qualifying operators)

3. **Trade Limits**: Proof of Concept phase enforces 1 trade per day with zero violations (measured via: `poc.daily_limit_exceeded` events = 0)

4. **Automatic Downgrade**: System downgrades phase within 1 minute of trigger condition (measured via: phase downgrade latency P95 <60 seconds)

5. **Capital Preservation**: Operators using phase system lose <5% capital in first 90 days vs >10% without system (measured via: P&L analysis in phase history)

6. **Session Tracking**: 100% of trading sessions recorded with profitability metrics (measured via: session count in `phase-history.jsonl` = actual trading days)

7. **Position Size Control**: Scaling phase enforces gradual increases with no sudden jumps >2x (measured via: position size deltas in session metrics)

8. **Override Protection**: Manual phase overrides blocked ≥98% of the time (emergency exits excluded) (measured via: `phase.override_blocked` / total override attempts)

## Assumptions

1. Operators will comply with manual restart requirements after circuit breaker trips
2. Trading sessions are defined as market open (7:00 AM) to market close (4:00 PM EST)
3. Profitability data from performance-tracking module is accurate and complete
4. Emergency exits are rare (<2% of all trades)
5. Operators using phase system will paper trade for minimum 30 days before live trading
6. Win rate and R:R targets are based on industry-standard profitable trading benchmarks
7. Position size increases are conservative enough to avoid significant capital risk

## Out of Scope

- Machine learning-based phase transition predictions
- Multi-strategy phase tracking (assumes single strategy per operator)
- Social comparison features (comparing phase progress across operators)
- Real-time phase progress dashboard (CLI-only in MVP)
- SMS/email alerts on phase transitions (logs only in MVP)
- Gamification features (badges, achievements for phase milestones)

## Appendix

### Phase Progression Timeline (Example)

| Phase | Duration | Max Position | Daily Limit | Win Rate Required | Avg R:R Required |
|-------|----------|--------------|-------------|-------------------|------------------|
| Experience | 30-60 days | Simulated | Unlimited | 60% (20 sessions) | 1.5 |
| Proof of Concept | 30-90 days | $100 | 1 trade/day | 65% (50 trades) | 1.8 |
| Real Money Trial | 60-120 days | $200 | No limit | 70% (100 trades) | 2.0 |
| Scaling | Ongoing | $200-$2,000 | No limit | Maintain 70%+ | Maintain 2.0+ |

### Related Specifications
- `specs/performance-tracking/spec.md` - Session metrics and profitability tracking
- `specs/safety-checks/spec.md` - Circuit breakers and trade validation
- `specs/backtesting-engine/spec.md` - Historical validation for paper trading

### Constitution Compliance
- ✅ §Safety_First - Enforces paper trading before real money (Experience phase)
- ✅ §Risk_Management - Gradual position scaling with profitability gates
- ✅ §Testing_Requirements - Mandatory 60+ days of validated trading before scaling
- ✅ §Audit_Everything - All phase transitions and validations logged
