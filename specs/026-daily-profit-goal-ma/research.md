# Research & Discovery: daily-profit-goal-ma

## Research Decisions

### Decision: Use existing PerformanceTracker for P&L aggregation
- **Decision**: Reuse `PerformanceTracker` class from `src/trading_bot/performance/tracker.py` for daily P&L calculation
- **Rationale**: Already implements realized and unrealized P&L calculation using `MetricsCalculator.calculate_total_pl()`. Provides proven pattern for aggregating trade data from JSONL logs. No need to duplicate P&L logic.
- **Alternatives**:
  - Create new PnLCalculator → Rejected (duplicate logic, violates §Code_Quality DRY principle)
  - Calculate P&L directly in profit goal module → Rejected (poor separation of concerns)
- **Source**: `src/trading_bot/performance/tracker.py:85` (calculate_total_pl implementation)

### Decision: Integrate with SafetyChecks for trade blocking
- **Decision**: Extend `SafetyChecks.validate_trade()` to check profit protection status before allowing new entries
- **Rationale**: SafetyChecks already implements circuit breaker pattern (line 194-199) and trade validation orchestration. Profit protection is conceptually another circuit breaker condition. Reuses existing fail-safe architecture.
- **Alternatives**:
  - Create separate ProfitProtectionGuard → Rejected (duplicates circuit breaker logic)
  - Modify order management directly → Rejected (violates single responsibility)
- **Source**: `src/trading_bot/safety_checks.py:100-226` (SafetyChecks.validate_trade pattern)

### Decision: Follow TradeRecord dataclass pattern for state model
- **Decision**: Create `DailyProfitState` dataclass similar to `TradeRecord` with `__post_init__` validation
- **Rationale**: TradeRecord demonstrates proven pattern for financial data with Decimal precision, validation, and JSON serialization. Profit goal state has similar requirements (monetary values, persistence, validation).
- **Alternatives**:
  - Use plain dict → Rejected (no type safety or validation)
  - Use SQLite database → Rejected (overkill for single-row state, adds dependency)
- **Source**: `src/trading_bot/logging/trade_record.py:20-131` (dataclass + validation pattern)

### Decision: Use file-based state persistence with JSON
- **Decision**: Store profit goal state in `logs/profit-goal-state.json` following circuit breaker pattern
- **Rationale**: SafetyChecks uses `logs/circuit_breaker.json` for persistent state (line 410). Same pattern ensures crash recovery while avoiding database overhead. UTC timestamps with pytz for timezone safety.
- **Alternatives**:
  - In-memory only → Rejected (loses state on bot restart, violates NFR-002 reliability)
  - SQLite database → Rejected (excessive for single-row state)
- **Source**: `src/trading_bot/safety_checks.py:402-413` (circuit breaker state persistence)

### Decision: JSONL event logging for profit protection triggers
- **Decision**: Create `logs/profit-protection/YYYY-MM-DD.jsonl` following StructuredTradeLogger pattern
- **Rationale**: StructuredTradeLogger implements daily rotation, thread-safe writes, and JSONL format for grep-friendly analytics (line 93-94). Profit protection events need same audit trail and query capabilities.
- **Alternatives**:
  - Log to same file as trades → Rejected (mixes event types, harder to query)
  - CSV format → Rejected (JSONL better for grep, jq, and partial records)
- **Source**: `src/trading_bot/logging/structured_logger.py:23-95` (daily JSONL pattern)

### Decision: Reset timing using market open detection
- **Decision**: Reset daily state at 4:00 AM EST using pytz timezone conversion
- **Rationale**: Spec.md line 273 assumes existing time utilities. SafetyChecks uses `is_trading_hours()` with pytz (line 263). Market open at 4:00 AM EST gives 5.5 hour buffer before trading starts at 9:30 AM EST.
- **Alternatives**:
  - Reset at midnight UTC → Rejected (doesn't align with US trading day)
  - Reset on first trade → Rejected (doesn't handle overnight gaps correctly)
- **Source**: spec.md:273 (assumption), `src/trading_bot/safety_checks.py:263` (pytz pattern)

---

## Components to Reuse (6 found)

- `src/trading_bot/performance/tracker.py:PerformanceTracker` - Daily P&L aggregation (realized + unrealized)
- `src/trading_bot/performance/models.py:PerformanceSummary` - Dataclass pattern with Decimal fields
- `src/trading_bot/safety_checks.py:SafetyChecks` - Circuit breaker integration point for trade blocking
- `src/trading_bot/logging/structured_logger.py:StructuredTradeLogger` - Daily JSONL logging pattern
- `src/trading_bot/logging/trade_record.py:TradeRecord` - Dataclass validation pattern
- `src/trading_bot/config.py:Config` - Configuration loading from .env and config.json

---

## New Components Needed (5 required)

- `src/trading_bot/profit_goal/models.py` - ProfitGoalConfig, DailyProfitState, ProfitProtectionEvent dataclasses
- `src/trading_bot/profit_goal/tracker.py` - DailyProfitTracker class (orchestrates P&L tracking + protection triggers)
- `src/trading_bot/profit_goal/logger.py` - ProfitProtectionLogger class (JSONL event logging)
- `src/trading_bot/profit_goal/config.py` - Configuration loading for PROFIT_TARGET_DAILY and PROFIT_GIVEBACK_THRESHOLD
- `tests/unit/profit_goal/` - Unit tests for all profit goal components (≥90% coverage per §Testing_Requirements)

---

## Unknowns & Questions

None - all technical questions resolved during research phase.
