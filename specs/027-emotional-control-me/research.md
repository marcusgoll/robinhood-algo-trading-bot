# Research & Discovery: emotional-control-me

## Research Decisions

### Decision: Follow DailyProfitTracker pattern for state management

- **Decision**: Use DailyProfitTracker (v1.5.0) as architectural template
- **Rationale**: Recently shipped feature with proven patterns for state persistence, JSONL logging, and Decimal precision. Similar domain (profit tracking vs loss tracking).
- **Alternatives**:
  - Circuit breaker pattern: Too binary (trip/reset), doesn't support gradual recovery
  - Custom implementation: Reinventing persistence/logging patterns
- **Source**: `src/trading_bot/profit_goal/tracker.py:1-410`

### Decision: Extend RiskManager with EmotionalControl module

- **Decision**: Create `EmotionalControl` class that integrates with `RiskManager.calculate_position_plan()`
- **Rationale**: RiskManager already orchestrates position sizing. Emotional control is a risk multiplier (0.25x or 1.0x).
- **Alternatives**:
  - Modify RiskManager directly: Violates Single Responsibility Principle
  - Separate position calculator: Duplicates position sizing logic
- **Source**: `src/trading_bot/risk_management/manager.py:39-384`

### Decision: Use JSONL event logging with daily rotation

- **Decision**: Log emotional control events to `logs/emotional_control/events-YYYY-MM-DD.jsonl`
- **Rationale**: Matches existing logging patterns (DailyProfitTracker, RiskManager), enables audit trail, supports analytics
- **Alternatives**:
  - Database storage: Overkill for this use case, adds dependency
  - Single JSON file: No rotation, grows unbounded
- **Source**: `src/trading_bot/profit_goal/tracker.py:257-296`

### Decision: Thread-safe atomic file writes for state persistence

- **Decision**: Use temp file + rename pattern for state.json writes
- **Rationale**: Prevents state corruption on crash (atomic operation), proven in DailyProfitTracker
- **Alternatives**:
  - Direct writes: Risk of partial writes on crash
  - Database: Overkill for single-file state
- **Source**: `src/trading_bot/profit_goal/tracker.py:298-336`

### Decision: Fail-safe default to ACTIVE state on corruption

- **Decision**: If state file corrupted or unreadable, default to emotional control ACTIVE (25% sizing)
- **Rationale**: Conservative approach prevents large position sizes after crashes. Aligns with §Safety_First.
- **Alternatives**:
  - Default to INACTIVE: Risk of large loss if crash occurred during active period
  - Crash on corruption: Prevents trading entirely, too aggressive
- **Source**: Constitution §Safety_First: "Fail safe, not fail open"

### Decision: No UI - CLI status command only

- **Decision**: Expose emotional control status via CLI command, no web dashboard
- **Rationale**: Backend-only feature, rapid development, matches project scope
- **Alternatives**:
  - Web dashboard: Out of scope for v1.0, future enhancement
  - Email/SMS alerts: Not specified in requirements
- **Source**: spec.md FR-011, Out of Scope section

---

## Components to Reuse (8 found)

- **src/trading_bot/profit_goal/tracker.py:32-410** - DailyProfitTracker class (state persistence, JSONL logging, update_state pattern)
- **src/trading_bot/risk_management/manager.py:39-384** - RiskManager class (position sizing orchestration, JSONL audit logging)
- **src/trading_bot/error_handling/circuit_breaker.py:19-100** - CircuitBreaker class (sliding window tracking, threshold detection)
- **src/trading_bot/account/account_data.py:91-100** - AccountData class (account balance retrieval for loss percentage calculation)
- **src/trading_bot/logging/structured_logger.py** - Structured logging patterns (JSONL format, daily rotation)
- **src/trading_bot/performance/tracker.py** - PerformanceTracker (trade outcome tracking for win/loss streaks)
- **Decimal precision patterns** - All financial calculations use Decimal type (Constitution §Code_Quality)
- **Atomic file writes pattern** - Temp file + rename for crash-safe persistence

---

## New Components Needed (5 required)

- **src/trading_bot/emotional_control/tracker.py** - EmotionalControl class (loss detection, position size multiplier, state management)
- **src/trading_bot/emotional_control/models.py** - Data models (EmotionalControlState, ActivationEvent, DeactivationEvent)
- **src/trading_bot/emotional_control/config.py** - Configuration model (EmotionalControlConfig with enabled flag, thresholds)
- **logs/emotional_control/state.json** - State persistence file (is_active, consecutive counters, trigger history)
- **logs/emotional_control/events-YYYY-MM-DD.jsonl** - Daily event log (activation/deactivation audit trail)

---

## Unknowns & Questions

None - all technical questions resolved during specification and research phases.

---

## Architecture Notes

**Integration Flow:**

1. **Loss Detection**: After each trade, EmotionalControl.update_state() checks:
   - AccountData.get_portfolio_value() for current balance
   - Trade P&L for single loss threshold (≥3%)
   - PerformanceTracker streak counters for consecutive losses (≥3)

2. **Position Size Adjustment**: RiskManager.calculate_position_plan() calls:
   - EmotionalControl.get_position_multiplier() → returns 0.25 or 1.0
   - Applies multiplier to calculated position size

3. **Recovery Detection**: EmotionalControl.update_state() checks:
   - PerformanceTracker consecutive win counter (≥3 wins)
   - Manual reset command (admin authorization)

4. **State Persistence**: After every state change:
   - Write to temp file: `state.tmp`
   - Atomic rename: `state.tmp` → `state.json`
   - Log event: `events-YYYY-MM-DD.jsonl`

**Performance Characteristics:**
- State update: <10ms (in-memory operation + file write)
- Position multiplier lookup: <1ms (in-memory check)
- Event logging: <50ms (append-only JSONL write)
- Recovery checks: <5ms (counter comparisons)

**Error Handling:**
- State file corruption → Default to ACTIVE (fail-safe)
- Logging failure → Continue operation, log error to stderr
- AccountData unavailable → Maintain previous state, skip update
- PerformanceTracker unavailable → Skip streak detection, log warning
