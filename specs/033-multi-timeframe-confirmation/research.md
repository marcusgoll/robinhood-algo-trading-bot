# Research & Discovery: 033-multi-timeframe-confirmation

## Research Decisions

### Decision: Composition Pattern for Multi-Timeframe Extension
**Decision**: Extend BullFlagDetector through composition rather than inheritance
**Rationale**: Preserves existing single-timeframe detection logic while adding multi-timeframe validation layer. Follows Open/Closed Principle - open for extension, closed for modification.
**Alternatives**:
- Direct modification of BullFlagDetector (rejected: breaks existing tests, increases coupling)
- Decorator pattern (rejected: over-engineered for this use case)
**Source**: D:\Coding\Stocks\src\trading_bot\patterns\bull_flag.py (existing facade pattern with _detect_flagpole, _detect_consolidation, _confirm_breakout phases)

### Decision: Separate TechnicalIndicatorsService Instances Per Timeframe
**Decision**: Create isolated TechnicalIndicatorsService instance for each timeframe (daily, 4H, 5min)
**Rationale**: TechnicalIndicatorsService maintains state (_last_ema_9, _last_ema_20, _last_macd, _last_signal). Reusing single instance across timeframes causes state collision.
**Alternatives**:
- Single service with state dictionary keyed by timeframe (rejected: requires modifying service.py, breaks existing code)
- Stateless service with explicit state passing (rejected: large refactor outside feature scope)
**Source**: D:\Coding\Stocks\src\trading_bot\indicators\service.py:18-22 (state tracking variables)

### Decision: Hierarchical Weighted Scoring (Daily 60% + 4H 40%)
**Decision**: Use weighted aggregate score rather than hard blocking on any single timeframe
**Rationale**: Allows nuanced decision-making when timeframes conflict. Prioritizes daily (institutional) over 4H (intraday) while capturing intraday momentum shifts.
**Alternatives**:
- Hard AND logic (rejected: too rigid, misses valid entries when 4H temporarily bearish during daily uptrend)
- Equal weighting (rejected: daily trend more predictive per hypothesis)
**Source**: specs/033-multi-timeframe-confirmation/spec.md (edge case: conflicting signals handling)

### Decision: Exponential Backoff with Graceful Degradation
**Decision**: 3 retry attempts (1s, 2s, 4s) then fall back to single-timeframe mode
**Rationale**: Balances resilience (retries handle transient API errors) with availability (degraded mode prevents complete trading halt). Aligns with constitution §Fail_Safe.
**Alternatives**:
- Block all trades on data fetch failure (rejected: availability over consistency for this use case)
- No retries, immediate degradation (rejected: too sensitive to transient errors)
**Source**: D:\Coding\Stocks\src\trading_bot\market_data\market_data_service.py:42 (@with_retry(policy=DEFAULT_POLICY) for API calls)

### Decision: Reuse MarketDataService Multi-Interval Capability
**Decision**: Leverage existing get_historical_data() with interval="day" and interval="10minute" parameters
**Rationale**: Infrastructure already exists, tested, and production-ready. No need to implement custom data fetching.
**Alternatives**:
- Direct robin_stocks.robinhood API calls (rejected: bypasses retry logic and validation)
- Custom data aggregation from 5min bars (rejected: unnecessary complexity)
**Source**: D:\Coding\Stocks\src\trading_bot\market_data\market_data_service.py:118-123 (get_historical_data supports multiple intervals)

### Decision: JSONL Logging for Multi-Timeframe Validation Events
**Decision**: Write structured logs to logs/timeframe-validation/YYYY-MM-DD.jsonl
**Rationale**: Enables post-hoc analysis with jq/grep, follows existing logging pattern in zone detection, supports Claude Code measurement plan.
**Alternatives**:
- SQLite database (rejected: over-engineered for read-only analytics)
- CSV files (rejected: harder to query nested data structures)
**Source**: specs/033-multi-timeframe-confirmation/spec.md (measurement plan JSONL queries)

---

## Components to Reuse (6 found)

- **MarketDataService** (D:\Coding\Stocks\src\trading_bot\market_data\market_data_service.py)
  - Purpose: Fetch daily and 4H OHLCV data via get_historical_data()
  - Provides: @with_retry resilience, data validation, multi-interval support

- **TechnicalIndicatorsService** (D:\Coding\Stocks\src\trading_bot\indicators\service.py)
  - Purpose: Calculate MACD and EMA per timeframe
  - Provides: VWAP, EMA (9/20), MACD (12/26/9) with signal detection
  - Note: Must instantiate per timeframe due to state tracking

- **BullFlagDetector** (D:\Coding\Stocks\src\trading_bot\patterns\bull_flag.py)
  - Purpose: Lower-timeframe (5min) pattern detection
  - Provides: Three-phase detection (flagpole/consolidation/breakout), quality scoring
  - Integration point: Call multi-timeframe validator before returning result

- **ZoneDetector Multi-Timeframe Pattern** (D:\Coding\Stocks\src\trading_bot\support_resistance\zone_detector.py)
  - Purpose: Reference implementation for multi-timeframe analysis
  - Provides: Timeframe enum, daily vs 4H handling, graceful degradation patterns
  - Pattern: detect_zones() with timeframe parameter (DAILY | FOUR_HOUR)

- **@with_retry Decorator** (D:\Coding\Stocks\src\trading_bot\error_handling\retry.py)
  - Purpose: Exponential backoff for API calls
  - Provides: Automatic retry with configurable policy (DEFAULT_POLICY has 3 attempts)

- **Existing Logging Infrastructure** (ZoneLogger pattern)
  - Purpose: Structured JSONL logging for analytics
  - Provides: Daily file rotation, structured event schema
  - Pattern: logs/[feature-name]/YYYY-MM-DD.jsonl

---

## New Components Needed (4 required)

- **MultiTimeframeValidator** (src/trading_bot/validation/multi_timeframe_validator.py)
  - Purpose: Orchestrate cross-timeframe validation logic
  - Responsibilities:
    - Fetch daily and 4H data via MarketDataService
    - Calculate indicators per timeframe (separate service instances)
    - Compute weighted aggregate score (daily * 0.6 + 4H * 0.4)
    - Handle graceful degradation on data fetch failure
    - Log validation events to JSONL
  - Dependencies: MarketDataService, TechnicalIndicatorsService (3 instances)

- **TimeframeIndicators Dataclass** (src/trading_bot/validation/models.py)
  - Purpose: Store indicator values for single timeframe
  - Fields: timeframe, price, ema_20, macd_line, macd_positive, price_above_ema
  - Immutable dataclass for type safety

- **TimeframeValidationResult Dataclass** (src/trading_bot/validation/models.py)
  - Purpose: Encapsulate validation decision
  - Fields: status (PASS|BLOCK|DEGRADED), aggregate_score, daily_score, 4h_score, reasons, timestamp
  - Used by BullFlagDetector to decide entry permission

- **TimeframeValidationLogger** (src/trading_bot/validation/logger.py)
  - Purpose: Write structured validation events to JSONL
  - Responsibilities:
    - Daily file rotation (logs/timeframe-validation/YYYY-MM-DD.jsonl)
    - Schema: symbol, timeframes, decision, indicator_values, timestamp
  - Pattern: Follow ZoneLogger implementation

---

## Unknowns & Questions

None - all technical questions resolved through codebase research.

---

## Architecture Constraints

1. **No Breaking Changes**: Must not modify BullFlagDetector's public API or return types
2. **State Isolation**: Each timeframe must have separate TechnicalIndicatorsService instance to prevent state collision
3. **Performance Budget**: Multi-timeframe validation must complete in <2s P95 (per spec NFR-001)
4. **Graceful Degradation**: System must continue functioning (degraded mode) when higher-timeframe data unavailable
5. **Constitution Compliance**:
   - §Data_Integrity: Validate data availability before indicator calculation
   - §Risk_Management: No auto-trading on degraded mode validation
   - §Audit_Everything: All validation decisions logged with full context

---

## Next Steps

Phase 1 (Design) artifacts to generate:
- data-model.md: Entity definitions for validation models
- contracts/api.yaml: Internal service contracts (MultiTimeframeValidator API)
- plan.md: Consolidated architecture plan with integration points
- quickstart.md: Developer integration scenarios
