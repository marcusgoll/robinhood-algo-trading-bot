# Feature Specification: Emotional Control Mechanisms

**Feature**: emotional-control-me
**Version**: 1.0.0
**Created**: 2025-10-22
**Status**: Draft

---

## Executive Summary

Implement automated emotional control safeguards that detect significant trading losses and automatically reduce position sizes to prevent revenge trading and capital destruction during drawdown periods. The system enforces recovery periods requiring either consistent profitability or manual reset before restoring normal position sizing.

**Business Value**: Protects trader psychology and capital during losing streaks by automatically limiting risk exposure when emotional decision-making is most likely.

**Strategic Fit**: Critical safety mechanism aligned with Constitution §Safety_First and §Risk_Management principles.

---

## Problem Statement

Traders experiencing significant losses or consecutive losing streaks often engage in "revenge trading" - increasing position sizes or taking impulsive trades to recover losses quickly. This emotional response typically leads to larger losses and account destruction.

**Current Gap**: While the bot has circuit breakers for consecutive losses and daily loss limits, it lacks automated position size reduction during drawdown periods. Once losses occur, the bot continues trading at full position size until circuit breakers halt all trading.

**Impact**: Risk of accelerated capital erosion during losing streaks when trader discipline is most vulnerable.

---

## User Scenarios

### Scenario 1: Single Large Loss Triggers Protection

**Given** a trader with $100,000 account balance and normal position size of $10,000 (10%)
**When** they execute a trade that loses $3,000 (3% of account)
**Then** the system:
- Detects significant loss event (≥3% account loss)
- Reduces subsequent position sizes to 25% of normal ($2,500 instead of $10,000)
- Logs emotional control activation with timestamp and trigger reason
- Displays warning message: "Position size reduced to 25% due to significant loss. Recovery required: 3 profitable trades or manual reset."

### Scenario 2: Consecutive Loss Streak Triggers Protection

**Given** a trader with $50,000 account balance experiencing consecutive losses
**When** they complete their 3rd consecutive losing trade
**Then** the system:
- Detects consecutive loss streak (≥3 losses)
- Reduces subsequent position sizes to 25% of normal
- Logs emotional control activation with streak count
- Displays warning message: "Position size reduced to 25% due to 3 consecutive losses. Recovery required."

### Scenario 3: Recovery Through Profitable Trading

**Given** emotional control is active (position size at 25%)
**When** trader completes 3 consecutive profitable trades
**Then** the system:
- Detects recovery condition met
- Restores position sizing to 100% of normal
- Logs emotional control deactivation with recovery reason
- Displays success message: "Position size restored to normal after 3 consecutive wins. Trade safely!"

### Scenario 4: Manual Recovery Override

**Given** emotional control is active (position size at 25%)
**When** admin user executes manual reset command with reason "completed review session"
**Then** the system:
- Verifies admin authorization
- Restores position sizing to 100% of normal
- Logs manual override with admin ID, timestamp, and reason
- Displays confirmation: "Emotional control manually reset by admin. Normal position sizing restored."

### Scenario 5: State Persistence Across Sessions

**Given** emotional control was activated in previous trading session
**And** bot was restarted
**When** bot starts up and loads persisted state
**Then** the system:
- Restores emotional control active state from logs
- Continues enforcing 25% position sizing
- Displays startup message: "Emotional control active from previous session. Position size: 25%."

---

## Functional Requirements

### Core Logic (FR-001 through FR-007)

**FR-001**: System SHALL detect significant loss events defined as:
- Single trade loss ≥ 3% of current account balance, OR
- Consecutive loss streak ≥ 3 trades

**FR-002**: System SHALL automatically reduce position sizes to 25% of normal sizing when significant loss event detected

**FR-003**: System SHALL maintain position size reduction until recovery condition met:
- 3 consecutive profitable trades (any profit amount), OR
- Manual admin reset with authorization

**FR-004**: System SHALL log all emotional control events to JSONL audit trail with fields:
- event_id (UUID)
- timestamp (ISO 8601 UTC)
- event_type (ACTIVATION | DEACTIVATION)
- trigger_reason (SINGLE_LOSS | STREAK_LOSS | PROFITABLE_RECOVERY | MANUAL_RESET)
- account_balance (Decimal)
- loss_amount (Decimal, optional)
- consecutive_losses (int, optional)
- consecutive_wins (int, optional)
- admin_id (string, optional)
- reset_reason (string, optional)

**FR-005**: System SHALL persist emotional control state across bot restarts using file-based storage with atomic writes

**FR-006**: System SHALL provide manual reset command requiring:
- Admin authorization (prevent accidental resets)
- Reason text (audit requirement)
- Confirmation prompt

**FR-007**: System SHALL display clear status messages when:
- Emotional control activates (reason, current position size percentage)
- Emotional control deactivates (reason)
- Position sizing is reduced (show normal vs reduced amount)

### Integration Requirements (FR-008 through FR-011)

**FR-008**: System SHALL integrate with RiskManager.calculate_position_plan() to apply position size multiplier (0.25 when active, 1.0 when normal)

**FR-009**: System SHALL integrate with TradeLogger to track win/loss streaks for recovery detection

**FR-010**: System SHALL integrate with AccountData to retrieve current account balance for loss percentage calculation

**FR-011**: System SHALL expose emotional control status via CLI command for monitoring

### Safety Requirements (FR-012 through FR-014)

**FR-012**: System SHALL use Decimal precision for all financial calculations (no float arithmetic)

**FR-013**: System SHALL fail-safe: If state file corrupted, default to emotional control ACTIVE (25% sizing) with alert

**FR-014**: System SHALL prevent concurrent state modifications using file locks or atomic operations

---

## Non-Functional Requirements

**NFR-001 Performance**: Position size calculation with emotional control check SHALL complete in <10ms (no perceptible delay)

**NFR-002 Reliability**: State persistence SHALL use atomic file writes with crash recovery (similar to DailyProfitTracker implementation)

**NFR-003 Maintainability**: Code SHALL follow existing patterns (EmotionalControl class similar to DailyProfitTracker)

**NFR-004 Testability**: All logic SHALL be unit testable with >90% code coverage per Constitution

**NFR-005 Observability**: All emotional control events SHALL be logged to dedicated JSONL file with daily rotation

**NFR-006 Security**: Manual reset SHALL require explicit confirmation to prevent accidental execution

---

## Success Criteria

1. System successfully detects and activates emotional control within 100ms of significant loss event
2. Position sizes reduced to exactly 25% of normal sizing when emotional control active
3. System correctly deactivates after 3 consecutive profitable trades with no manual intervention
4. State persists across bot restarts with 100% accuracy
5. Manual reset command completes successfully with full audit trail
6. Zero false positives (no activation without genuine loss event)
7. Zero false negatives (no missed loss events when thresholds exceeded)
8. Test coverage ≥90% per Constitution §Testing_Requirements

---

## Context Strategy

### Emotional Control State Context

**Scope**: Track current emotional control state (active/inactive), position size multiplier, trigger history, recovery progress

**Sources**:
- Current account balance (from AccountData)
- Recent trade outcomes (from TradeLogger JSONL)
- Last N consecutive trades (for streak detection)
- Persisted state file (logs/emotional_control/state.json)

**Decisions**:
- Activation: Compare loss amount/percentage against thresholds
- Deactivation: Count consecutive profitable trades
- Position sizing: Apply multiplier to RiskManager calculations

**Refresh**:
- After every trade execution (win/loss updates streak counters)
- At bot startup (restore persisted state)
- On manual reset command

### Trade Outcome Context

**Scope**: Win/loss status of recent trades for streak detection

**Sources**:
- TradeLogger JSONL files (logs/trades/*.jsonl)
- In-memory consecutive win/loss counters

**Decisions**:
- Detect 3+ consecutive losses → activate emotional control
- Detect 3+ consecutive wins during active control → deactivate

**Refresh**:
- After each trade execution (real-time)

---

## Signal Design

### Activation Signals

**Signal 1: Significant Single Loss**
- **Trigger**: Trade loss ≥ 3% of account balance
- **Source**: AccountData.get_portfolio_value(), trade P&L calculation
- **Confidence**: High (objective financial threshold)
- **Action**: Activate emotional control, reduce position sizing to 25%

**Signal 2: Consecutive Loss Streak**
- **Trigger**: 3+ consecutive losing trades (any loss amount)
- **Source**: TradeLogger consecutive loss counter
- **Confidence**: High (behavioral pattern indicator)
- **Action**: Activate emotional control, reduce position sizing to 25%

### Deactivation Signals

**Signal 3: Profitable Recovery**
- **Trigger**: 3+ consecutive profitable trades (any profit amount)
- **Source**: TradeLogger consecutive win counter
- **Confidence**: High (demonstrates recovery)
- **Action**: Deactivate emotional control, restore 100% position sizing

**Signal 4: Manual Admin Reset**
- **Trigger**: Admin executes reset command with reason
- **Source**: CLI command with authorization check
- **Confidence**: High (human oversight)
- **Action**: Deactivate emotional control, restore 100% position sizing, log override

---

## Constraints

### Technical Constraints

1. **Python 3.11+**: Use modern Python features (match/case for event types)
2. **Decimal Precision**: All financial calculations use Decimal type per Constitution
3. **Thread Safety**: File locks required for state persistence (concurrent access)
4. **Existing Patterns**: Follow DailyProfitTracker implementation pattern for consistency

### Business Constraints

1. **Conservative Thresholds**: 3% single loss threshold chosen to avoid false positives while catching significant events
2. **25% Position Size**: Based on common risk management best practice (75% reduction from normal)
3. **3-Trade Recovery**: Balances safety (prove consistency) with trader frustration (not too long)

### Design Constraints

1. **No UI Changes**: Backend-only feature, status via CLI commands
2. **Backward Compatible**: Existing trades unaffected, opt-in activation via configuration
3. **Fail-Safe Default**: If uncertainty, default to ACTIVE (more conservative)

---

## Dependencies

### Internal Dependencies (All Shipped)
- **RiskManager** (v1.0.0+): Position sizing calculations - SHIPPED
- **TradeLogger** (v1.0.0+): Trade outcome history - SHIPPED
- **AccountData** (v1.1.0+): Account balance retrieval - SHIPPED
- **SafetyChecks** (v1.0.0+): Integration point for validation - SHIPPED

### External Dependencies
- **python-dotenv**: Configuration loading (already in requirements.txt)
- **pytest**: Testing framework (already in requirements.txt)

---

## Assumptions

1. **Account Balance Accuracy**: AccountData provides accurate real-time balance (validated in v1.1.0)
2. **Trade Outcome Reliability**: TradeLogger accurately records P&L for each trade (validated in v1.0.0)
3. **Admin Authorization**: CLI commands run with appropriate OS-level permissions
4. **File System Reliability**: Atomic file writes succeed on target deployment platform (Windows/Linux)
5. **Recovery Period Validity**: 3 consecutive profitable trades indicate psychological recovery (industry best practice)

---

## Out of Scope

The following are explicitly excluded from this feature:

1. **UI Dashboard**: No web/GUI interface for emotional control status (CLI only)
2. **Configurable Thresholds**: Hardcoded 3% loss / 3 consecutive trades (future enhancement)
3. **Graduated Recovery**: Single-step recovery (25% → 100%), no intermediate stages
4. **Simulator Mode Forcing**: Does not force paper trading mode (covered by existing circuit breakers)
5. **Historical Analysis**: No retrospective analysis of past trades (only forward-looking)
6. **Multi-User Support**: Single-user trading bot, no per-user state tracking
7. **Email/SMS Alerts**: No external notifications (logs only)

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| False positives reduce position size unnecessarily | Medium | Low | Conservative 3% threshold avoids noise |
| Trader manually bypasses system by editing state file | High | Medium | File integrity checks, fail-safe to ACTIVE if corrupted |
| Recovery takes too long, trader frustrated | Medium | Medium | Allow manual reset with admin authorization |
| State file corruption causes bot failure | High | Low | Atomic writes, validation on load, fail-safe default |
| Performance degradation from file I/O | Low | Low | In-memory state with async persistence |

---

## Rollback Strategy

If deployment causes issues:

1. **Disable Feature**: Set environment variable `EMOTIONAL_CONTROL_ENABLED=false` (graceful degradation)
2. **Code Rollback**: Git revert commit, restart bot (state files preserved for analysis)
3. **State Reset**: Delete state file `logs/emotional_control/state.json` to clear persisted state
4. **Manual Override**: Admin can always force reset via CLI command

**Rollback Time**: <2 minutes (configuration change + restart)

---

## Acceptance Criteria

### Activation Tests
- ✅ AC-001: Single loss of 3.0% account balance activates emotional control
- ✅ AC-002: Single loss of 2.9% account balance does NOT activate emotional control
- ✅ AC-003: 3 consecutive losses activate emotional control
- ✅ AC-004: 2 consecutive losses do NOT activate emotional control

### Position Sizing Tests
- ✅ AC-005: When active, position size = normal_size × 0.25
- ✅ AC-006: When inactive, position size = normal_size × 1.0
- ✅ AC-007: Position size calculations use Decimal precision (no floats)

### Recovery Tests
- ✅ AC-008: 3 consecutive profitable trades deactivate emotional control
- ✅ AC-009: 2 consecutive profitable trades do NOT deactivate (control remains active)
- ✅ AC-010: Manual reset with valid admin authorization deactivates emotional control
- ✅ AC-011: Manual reset requires confirmation prompt before execution

### Persistence Tests
- ✅ AC-012: Emotional control state persists across bot restart
- ✅ AC-013: Corrupted state file defaults to ACTIVE (fail-safe) with alert logged
- ✅ AC-014: State file uses atomic writes (no partial writes on crash)

### Integration Tests
- ✅ AC-015: RiskManager applies position size multiplier correctly
- ✅ AC-016: CLI command displays current emotional control status
- ✅ AC-017: All events logged to JSONL with complete audit trail

### Performance Tests
- ✅ AC-018: Emotional control check completes in <10ms (P95)
- ✅ AC-019: State persistence completes in <50ms (P95)

### Quality Gates
- ✅ AC-020: Test coverage ≥90% per Constitution §Testing_Requirements
- ✅ AC-021: MyPy type checking passes with --strict mode
- ✅ AC-022: Bandit security scan shows 0 HIGH/CRITICAL vulnerabilities
- ✅ AC-023: All unit tests pass (100% pass rate)

---

## Configuration

### Environment Variables

```bash
# Enable/disable emotional control (default: true)
EMOTIONAL_CONTROL_ENABLED=true

# Note: Thresholds hardcoded for v1.0 (future enhancement)
# EMOTIONAL_CONTROL_LOSS_PCT=3.0
# EMOTIONAL_CONTROL_STREAK_COUNT=3
# EMOTIONAL_CONTROL_RECOVERY_COUNT=3
```

### File Locations

```
logs/
  emotional_control/
    state.json                  # Current state (active/inactive, counters)
    events-YYYY-MM-DD.jsonl    # Daily event audit trail
```

---

## Implementation Notes

### State File Schema (state.json)

```json
{
  "is_active": true,
  "activated_at": "2025-10-22T14:30:00Z",
  "trigger_reason": "SINGLE_LOSS",
  "account_balance_at_activation": "100000.00",
  "loss_amount": "3000.00",
  "consecutive_losses": 0,
  "consecutive_wins": 2,
  "last_updated": "2025-10-22T16:45:00Z"
}
```

### Event Log Schema (events-YYYY-MM-DD.jsonl)

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-22T14:30:00Z",
  "event_type": "ACTIVATION",
  "trigger_reason": "SINGLE_LOSS",
  "account_balance": "100000.00",
  "loss_amount": "3000.00",
  "consecutive_losses": 0,
  "position_size_multiplier": 0.25
}
```

---

## Related Documentation

- Constitution v1.0.0 - §Safety_First, §Risk_Management
- Roadmap - emotional-controls (ICE score: 1.60)
- DailyProfitTracker implementation (v1.5.0) - reference pattern
- RiskManager documentation - integration point

---

**Next Steps**: Proceed to `/plan` phase for technical design and task breakdown.
