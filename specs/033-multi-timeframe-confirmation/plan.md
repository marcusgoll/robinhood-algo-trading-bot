# Implementation Plan: Multi-Timeframe Confirmation for Momentum Trades

## [RESEARCH DECISIONS]

See: research.md for full research findings

**Summary**:
- Stack: Python 3.12, pandas, robin_stocks (existing)
- Pattern: Composition pattern extending BullFlagDetector
- Components to reuse: 6 (MarketDataService, TechnicalIndicatorsService, BullFlagDetector, ZoneDetector pattern, @with_retry, logging infrastructure)
- New components needed: 4 (MultiTimeframeValidator, TimeframeIndicators, TimeframeValidationResult, TimeframeValidationLogger)
- Key Decision: Separate TechnicalIndicatorsService instances per timeframe to prevent state collision

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Language: Python 3.12 (existing)
- Data Processing: pandas DataFrame for OHLCV (existing)
- Market Data: robin_stocks API via MarketDataService (existing)
- Indicators: TechnicalIndicatorsService (MACD, EMA) (existing)
- Logging: Structured JSONL with daily rotation (existing pattern)
- Error Handling: @with_retry decorator with exponential backoff (existing)

**Patterns**:
- **Composition over Inheritance**: MultiTimeframeValidator wraps BullFlagDetector, doesn't modify it. Preserves existing behavior, enables feature flag toggle.
- **Facade Pattern**: MultiTimeframeValidator orchestrates MarketDataService + TechnicalIndicatorsService without exposing complexity to BullFlagDetector.
- **Stateless Validation**: Each validation creates fresh service instances to prevent cross-timeframe state pollution.
- **Graceful Degradation**: Retry with exponential backoff (1s, 2s, 4s) then fall back to single-timeframe mode rather than blocking all trades.
- **Weighted Scoring**: Daily (60%) + 4H (40%) allows nuanced decisions when timeframes conflict, prioritizes institutional (daily) over intraday (4H).

**Dependencies** (new packages required):
- None - all dependencies already in requirements.txt

**Configuration** (environment variables):
- `MULTI_TIMEFRAME_VALIDATION_ENABLED=true` (feature flag, default: true)
- `DAILY_WEIGHT=0.6` (default)
- `4H_WEIGHT=0.4` (default)
- `AGGREGATE_THRESHOLD=0.5` (minimum score to PASS)
- `MAX_RETRIES=3` (data fetch retries)
- `RETRY_BACKOFF_BASE_MS=1000` (1s base delay)

---

## [STRUCTURE]

**Directory Layout** (follows existing patterns):

```
src/trading_bot/
├── validation/
│   ├── __init__.py
│   ├── multi_timeframe_validator.py  # NEW - Main validator service
│   ├── models.py                      # NEW - TimeframeIndicators, TimeframeValidationResult, ValidationStatus
│   ├── logger.py                      # NEW - TimeframeValidationLogger
│   └── config.py                      # NEW - MultiTimeframeConfig
├── patterns/
│   └── bull_flag.py                   # MODIFIED - Integrate validator call
└── indicators/
    └── service.py                     # NO CHANGE - Use as-is with multiple instances

tests/
├── unit/
│   └── validation/
│       ├── test_multi_timeframe_validator.py
│       ├── test_models.py
│       └── test_logger.py
├── integration/
│   ├── test_bull_flag_multi_timeframe.py
│   └── test_multi_timeframe_concurrency.py
└── patterns/
    └── test_bull_flag.py              # MODIFIED - Add multi-timeframe test cases

logs/
└── timeframe-validation/
    └── YYYY-MM-DD.jsonl              # NEW - Daily validation event logs
```

**Module Organization**:
- **validation/multi_timeframe_validator.py**: Core orchestration logic, fetches data, calculates scores, returns result
- **validation/models.py**: Immutable dataclasses for type safety (TimeframeIndicators, TimeframeValidationResult, ValidationStatus enum)
- **validation/logger.py**: JSONL logging with daily rotation, follows ZoneLogger pattern
- **validation/config.py**: Configuration dataclass with environment variable loading
- **patterns/bull_flag.py**: Add optional multi-timeframe validation call in detect() method before returning result

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- Entities: 3 (TimeframeValidationResult, TimeframeIndicators, ValidationStatus enum)
- Relationships: TimeframeValidationResult contains 1 daily + 0..1 4H TimeframeIndicators
- Scoring Logic: Per-timeframe score = 0.5 (if MACD > 0) + 0.5 (if price > EMA), range [0.0, 1.0]
- Aggregate Logic: daily_score * 0.6 + 4h_score * 0.4, PASS if > 0.5
- Log Schema: TimeframeValidationEvent with 15 fields for analytics

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: Multi-timeframe validation completes in <2s P95 (daily fetch ~300ms, 4H fetch ~500ms, indicators ~200ms, total ~1s nominal)
- NFR-002: API timeout triggers exponential backoff (1s, 2s, 4s) then graceful degradation
- NFR-003: Data integrity validated before indicator calculation (minimum 30 daily bars, 72 10min bars)
- NFR-004: All validation decisions logged with full indicator context

**Lighthouse Targets**: N/A (backend-only feature)

**Performance Budget Breakdown**:
- Daily data fetch: 200-400ms (robin_stocks API, span=3month, interval=day)
- 4H data fetch: 400-700ms (robin_stocks API, span=week, interval=10minute)
- Daily indicator calculation: 50-100ms (pandas operations on ~60 bars)
- 4H indicator calculation: 100-150ms (pandas operations on ~72 bars)
- Scoring + result creation: <50ms
- JSONL logging: <100ms
- Total nominal: 800-1500ms
- Total P95 (with retry): <2000ms
- Total P99 (with 2 retries): <5000ms

---

## [SECURITY]

**Authentication Strategy**:
- Reuses existing RobinhoodAuth (no changes required)
- MarketDataService already authenticated via self.auth

**Authorization Model**:
- N/A - local-only trading bot, no multi-user concerns

**Input Validation**:
- Symbol: Non-empty string, valid ticker format (alphanumeric, 1-5 chars)
- Current price: Decimal > 0, precision up to 4 decimal places
- Bars: Minimum 30 for daily, 72 for 4H, validated before indicator calculation (FR-010)
- ValueError raised on invalid inputs (fail-fast per constitution §Fail_Safe)

**Data Protection**:
- No PII handling - only public market data (ticker symbols, prices)
- Logs contain no sensitive information
- Credentials managed by existing RobinhoodAuth (not in scope)

---

## [EXISTING INFRASTRUCTURE - REUSE] (6 components)

**Services/Modules**:
- **src/trading_bot/market_data/market_data_service.py**: Fetch daily (interval="day", span="3month") and 4H (interval="10minute", span="week") OHLCV data
  - Method: `get_historical_data(symbol, interval, span) -> pd.DataFrame`
  - Features: @with_retry resilience, data validation, returns normalized DataFrame
- **src/trading_bot/indicators/service.py**: Calculate MACD (12-26-9) and EMA (20) per timeframe
  - Methods: `get_macd(bars)`, `get_emas(bars)`
  - Note: Create separate instances per timeframe to avoid state collision (_last_macd, _last_ema_9, etc.)
- **src/trading_bot/patterns/bull_flag.py**: Lower-timeframe (5min) bull flag pattern detection
  - Integration point: Call MultiTimeframeValidator.validate() before returning BullFlagResult
  - Modification: Add optional multi_timeframe_enabled parameter to detect() method
- **src/trading_bot/support_resistance/zone_detector.py**: Reference for multi-timeframe pattern
  - Provides: Timeframe enum pattern, detect_zones() with timeframe parameter (DAILY | FOUR_HOUR)
  - Reuse: Graceful degradation pattern (missing data → empty results + warning)

**Utilities**:
- **src/trading_bot/error_handling/retry.py**: @with_retry decorator for exponential backoff
  - Pattern: `@with_retry(policy=DEFAULT_POLICY)` on data fetch methods
  - DEFAULT_POLICY: 3 retries, exponential backoff (1s, 2s, 4s)
- **src/trading_bot/support_resistance/zone_logger.py**: JSONL logging pattern
  - Pattern: Daily file rotation (logs/[feature]/YYYY-MM-DD.jsonl), structured events
  - Reuse: TimeframeValidationLogger follows same structure

---

## [NEW INFRASTRUCTURE - CREATE] (4 components)

**Backend Services**:
- **src/trading_bot/validation/multi_timeframe_validator.py**: Core validation orchestration
  - Class: MultiTimeframeValidator
  - Method: `validate(symbol: str, current_price: Decimal, bars_5min: List) -> TimeframeValidationResult`
  - Logic:
    1. Fetch daily data via MarketDataService
    2. Create TechnicalIndicatorsService for daily, calculate MACD + EMA
    3. Compute daily_score (0.0-1.0)
    4. Fetch 4H data (retry with backoff if failure)
    5. Create TechnicalIndicatorsService for 4H, calculate indicators
    6. Compute 4h_score (0.0-1.0)
    7. Calculate aggregate_score = daily_score * 0.6 + 4h_score * 0.4
    8. Determine status (PASS if score > 0.5, BLOCK otherwise, DEGRADED if data unavailable)
    9. Log event via TimeframeValidationLogger
    10. Return TimeframeValidationResult

- **src/trading_bot/validation/models.py**: Immutable dataclasses for type safety
  - `ValidationStatus(Enum)`: PASS | BLOCK | DEGRADED
  - `TimeframeIndicators(dataclass)`: timeframe, price, ema_20, macd_line, macd_positive, price_above_ema, bar_count, timestamp
  - `TimeframeValidationResult(dataclass)`: status, aggregate_score, daily_score, 4h_score, daily_indicators, 4h_indicators, reasons, timestamp, symbol

- **src/trading_bot/validation/logger.py**: Structured JSONL logging
  - Class: TimeframeValidationLogger
  - Method: `log_validation_event(result: TimeframeValidationResult)`
  - Output: `logs/timeframe-validation/YYYY-MM-DD.jsonl`
  - Schema: 15 fields (event, symbol, timestamp, decision, aggregate_score, daily_macd, 4h_macd, reasons, validation_duration_ms, degraded_mode, etc.)

- **src/trading_bot/validation/config.py**: Configuration management
  - Class: MultiTimeframeConfig
  - Fields: enabled, daily_weight, 4h_weight, aggregate_threshold, max_retries, retry_backoff_base_ms
  - Method: `from_env()` loads from environment variables with defaults

**Integration Point**:
- **src/trading_bot/patterns/bull_flag.py** (MODIFICATION):
  - Add to BullFlagDetector.__init__():
    ```python
    self.multi_timeframe_validator = MultiTimeframeValidator(
        market_data_service=market_data_service,
        config=MultiTimeframeConfig.from_env()
    ) if config.multi_timeframe_enabled else None
    ```
  - Add to BullFlagDetector.detect() before returning result:
    ```python
    if self.multi_timeframe_validator:
        validation_result = self.multi_timeframe_validator.validate(
            symbol=symbol,
            current_price=current_price,
            bars_5min=bars
        )
        if validation_result.status == ValidationStatus.BLOCK:
            return self._create_failed_result(
                symbol,
                f"Multi-timeframe validation blocked: {', '.join(validation_result.reasons)}"
            )
        elif validation_result.status == ValidationStatus.DEGRADED:
            # Log warning but allow trade
            self.logger.warning(f"Multi-timeframe validation degraded for {symbol}")
    ```

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Local-only feature, no VPS deployment required
- Env vars: Add to .env.example: MULTI_TIMEFRAME_VALIDATION_ENABLED=true (default)
- Breaking changes: No - additive feature, backward compatible
- Migration: No database changes

**Build Commands**:
- No changes - uses existing `pytest` and `python -m src.trading_bot.main`

**Environment Variables** (update .env.example):
- New optional: MULTI_TIMEFRAME_VALIDATION_ENABLED=true (default)
- New optional: DAILY_WEIGHT=0.6 (default)
- New optional: 4H_WEIGHT=0.4 (default)
- New optional: AGGREGATE_THRESHOLD=0.5 (default)
- Staging values: Same as production (local-only)
- Production values: Same as staging (local-only)

**Database Migrations**:
- No - no database schema changes

**Smoke Tests**:
- N/A - local-only feature, no deployment pipeline
- Manual validation: Run `pytest tests/integration/test_bull_flag_multi_timeframe.py -v` before using in live trading

**Platform Coupling**:
- None - local Python service, no deployment dependencies

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- No breaking changes to BullFlagDetector public API
- Feature flag allows instant disable (MULTI_TIMEFRAME_VALIDATION_ENABLED=false)
- Graceful degradation ensures trading never fully blocked by validation failures
- All validation decisions logged for post-hoc analysis

**Staging Smoke Tests** (Given/When/Then):
```gherkin
# Test 1: Daily bearish blocks entry
Given a 5-minute bull flag pattern is detected for AAPL
  And daily MACD is negative (-0.52)
  And price is below daily 20 EMA
When multi-timeframe validation runs
Then status is BLOCK
  And reasons include "Daily MACD negative"
  And aggregate_score is < 0.5

# Test 2: Both timeframes bullish passes
Given a 5-minute bull flag pattern is detected for TSLA
  And daily MACD is positive (0.82)
  And 4H MACD is positive (0.35)
  And price is above EMAs on both timeframes
When multi-timeframe validation runs
Then status is PASS
  And aggregate_score is 1.0
  And entry is allowed

# Test 3: Graceful degradation on API failure
Given a 5-minute bull flag pattern is detected for NVDA
  And Robinhood API returns HTTP 503 for daily data
When multi-timeframe validation runs with retries
Then status is DEGRADED after 3 retry attempts
  And warning is logged with severity=HIGH
  And entry is allowed (single-timeframe fallback)
  And latency is < 10s (3 retries with backoff)

# Test 4: Performance target met
Given 100 multi-timeframe validations
When measuring validation_duration_ms
Then P95 latency is < 2000ms
  And P99 latency is < 5000ms
```

**Rollback Plan**:
- Feature flag rollback: `export MULTI_TIMEFRAME_VALIDATION_ENABLED=false` (instant)
- Code rollback: `git revert <commit-sha>` (standard 3-command rollback)
- Special considerations: None - no database migrations, no API contract changes

**Artifact Strategy**:
- N/A - local-only feature, no build artifacts or deployment pipeline

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios

**Summary**:
- Scenario 1: Local development setup and environment validation
- Scenario 2: Unit testing with pytest (12+ tests, 90%+ coverage)
- Scenario 3: Integration testing with real MarketDataService
- Scenario 4: Manual CLI testing with paper trading
- Scenario 5: JSONL log analysis with jq queries
- Scenario 6: Backtest comparison (baseline 52% → enhanced 63% win rate)
- Scenario 7: Feature flag rollback and troubleshooting

---

## [TESTING STRATEGY]

### Unit Tests (tests/unit/validation/)
- **test_multi_timeframe_validator.py** (8 tests):
  - test_validate_daily_bearish_blocks_entry
  - test_validate_both_bullish_passes
  - test_validate_conflicting_signals_uses_weighted_score
  - test_validate_insufficient_daily_bars_raises_error
  - test_validate_insufficient_4h_bars_raises_error
  - test_validate_data_fetch_failure_degrades_gracefully
  - test_validate_logs_event_to_jsonl
  - test_validate_invalid_symbol_raises_valueerror

- **test_models.py** (3 tests):
  - test_timeframe_indicators_immutable
  - test_validation_result_status_transitions
  - test_scoring_logic_0_to_1_range

- **test_logger.py** (2 tests):
  - test_logger_writes_to_daily_file
  - test_logger_rotates_at_midnight

### Integration Tests (tests/integration/)
- **test_bull_flag_multi_timeframe.py** (3 tests):
  - test_e2e_bull_flag_with_timeframe_validation (real MarketDataService)
  - test_latency_under_2s_p95 (100 validations, measure latency)
  - test_validation_result_logged_to_jsonl

- **test_multi_timeframe_concurrency.py** (1 test):
  - test_concurrent_validations_no_state_collision (10 parallel validations for different symbols)

### Modified Existing Tests
- **tests/patterns/test_bull_flag.py**:
  - Add: test_bull_flag_with_multi_timeframe_pass
  - Add: test_bull_flag_with_multi_timeframe_block
  - Add: test_bull_flag_multi_timeframe_disabled_via_flag

**Coverage Target**: 90%+ for new validation module

---

## [BACKTEST VALIDATION PLAN]

### Hypothesis to Test
- Win rate improvement: 52% → 63% (+11 percentage points)
- False positive reduction: 40% (70 filtered / 175 total signals)
- Avg profit improvement: $82.50 → $124.30 (+$41.80 per trade)

### Backtest Parameters
- Symbols: AAPL, TSLA, NVDA (high liquidity)
- Date range: 2024-05-01 to 2024-10-28 (6 months)
- Strategy: Bull flag pattern on 5-minute bars
- Variants:
  - Baseline: multi_timeframe=false (existing behavior)
  - Enhanced: multi_timeframe=true (with daily + 4H validation)

### Success Criteria
- Win rate delta ≥ 8 percentage points (target: 11)
- False positive reduction ≥ 30% (target: 40%)
- Statistical significance: p < 0.05 (chi-square test on win/loss distribution)
- No false negative rate > 15% (missed winning trades)

### Execution
```bash
# Baseline
python -m src.trading_bot.backtest --strategy bull_flag --symbols AAPL,TSLA,NVDA \
  --start-date 2024-05-01 --end-date 2024-10-28 --multi-timeframe false \
  --output backtests/results/baseline.json

# Enhanced
python -m src.trading_bot.backtest --strategy bull_flag --symbols AAPL,TSLA,NVDA \
  --start-date 2024-05-01 --end-date 2024-10-28 --multi-timeframe true \
  --output backtests/results/enhanced.json

# Comparison report
python -m src.trading_bot.backtest.compare --baseline baseline.json --enhanced enhanced.json \
  --output backtests/reports/multi-timeframe-improvement.md
```

---

## [MEASUREMENT PLAN]

### HEART Metrics (from spec.md)

| Metric | Target | Measurement Query |
|--------|--------|-------------------|
| Win rate improvement | 63% (up from 52%) | `cat logs/trades/*.jsonl \| jq 'select(.timeframe_validation_enabled==true) \| .outcome' \| awk '/win/{w++} /loss/{l++} END {print w/(w+l)*100"%"}'` |
| Early exit rate | <18% (down from 35%) | `grep '"event":"position_closed"' logs/trades/*.jsonl \| jq 'select(.duration_minutes < 15) \| select(.timeframe_validation_enabled==true)' \| wc -l` |
| Validation latency P95 | <2s | `jq -r '.validation_duration_ms' logs/timeframe-validation/*.jsonl \| sort -n \| awk '{a[NR]=$1} END {print a[int(NR*0.95)]}'` |
| Degraded mode rate | <5% | `grep '"decision":"DEGRADED"' logs/timeframe-validation/*.jsonl \| wc -l` / total validations |
| False positive reduction | 40% | `grep '"decision":"BLOCK"' logs/timeframe-validation/*.jsonl \| wc -l` |

### Analytics Events
- `timeframe_validation.daily_fetched` - Daily data availability (latency, bar count)
- `timeframe_validation.indicators_calculated` - Indicator values per timeframe
- `timeframe_validation.decision` - PASS|BLOCK|DEGRADED with aggregate score
- `timeframe_validation.degraded` - Fallback to single-timeframe (severity=HIGH)
- `trade.closed` - Outcome with `timeframe_validation_enabled` flag

### Monitoring Dashboard (Manual)
- Daily report: `python scripts/analytics/daily_validation_report.py --date $(date +%Y-%m-%d)`
- Win rate trend: `python scripts/analytics/win_rate_trend.py --lookback-days 30`
- Latency P95 graph: `python scripts/analytics/plot_latency.py --output reports/latency.png`

---

## [NEXT STEPS]

After plan approval:
1. `/tasks` - Break down into 20-30 TDD tasks with acceptance criteria
   - Phase 1: Core validation logic (10-12 tasks)
   - Phase 2: Integration with BullFlagDetector (3-4 tasks)
   - Phase 3: Logging infrastructure (2-3 tasks)
   - Phase 4: Backtest validation (3-4 tasks)
   - Phase 5: Documentation and CLI tools (2-3 tasks)

2. `/implement` - Execute tasks with TDD, 90%+ test coverage
   - Write failing tests first
   - Implement minimum code to pass tests
   - Refactor and optimize
   - Verify no regressions in existing bull_flag tests

3. `/optimize` - Performance tuning and final validation
   - Profile validation latency (target <2s P95)
   - Run concurrency tests (verify no state collision)
   - Execute full backtest comparison (verify win rate improvement)
   - Review code quality (linting, type hints, docstrings)

4. `/preview` - Manual testing before live deployment
   - Paper trading with multi-timeframe validation enabled
   - Monitor degraded mode rate over 7 days
   - Review JSONL logs for data quality issues
   - Final approval before enabling in live trading
