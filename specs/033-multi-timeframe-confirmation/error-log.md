# Error Log: Multi-Timeframe Confirmation for Momentum Trades

## Planning Phase (Phase 0-2)
None yet.

## Implementation Phase (Phase 3-4)
[Populated during /tasks and /implement]

## Testing Phase (Phase 5)
[Populated during /debug and /preview]

## Deployment Phase (Phase 6-7)
N/A - Local-only feature, no deployment pipeline

---

## Error Template

**Error ID**: ERR-033-[NNN]
**Phase**: [Planning/Implementation/Testing/Deployment]
**Date**: YYYY-MM-DD HH:MM
**Component**: [validation/patterns/indicators/market_data]
**Severity**: [Critical/High/Medium/Low]

**Description**:
[What happened - be specific with error messages and stack traces]

**Root Cause**:
[Why it happened - trace back to design decision or code logic]

**Resolution**:
[How it was fixed - include code changes or configuration updates]

**Prevention**:
[How to prevent in future - add tests, validation, documentation]

**Related**:
- Spec: [link to requirement, e.g., FR-003]
- Code: [file:line, e.g., src/trading_bot/validation/multi_timeframe_validator.py:145]
- Commit: [sha if fixed]
- Test: [test file that catches regression]

---

## Known Issues / Technical Debt

### Issue 1: State Collision Risk in TechnicalIndicatorsService
**Component**: src/trading_bot/indicators/service.py
**Severity**: High (mitigated by design)
**Description**: TechnicalIndicatorsService maintains state (_last_ema_9, _last_macd, etc.). If single instance shared across timeframes, state collision occurs.
**Mitigation**: Create separate service instances per timeframe in MultiTimeframeValidator
**Prevention**: Add integration test test_concurrent_validations_no_state_collision
**Status**: Mitigated by design, verified by test

### Issue 2: Robinhood API Rate Limiting
**Component**: src/trading_bot/market_data/market_data_service.py
**Severity**: Medium
**Description**: Robinhood API has rate limits (~100 req/min). Multi-timeframe validation doubles data fetch calls (daily + 4H).
**Mitigation**: @with_retry decorator handles HTTP 429 with exponential backoff
**Future Enhancement**: Implement caching for daily data (1-day TTL) to reduce API calls
**Status**: Known limitation, graceful degradation implemented

### Issue 3: 4H Data Aggregation from 10-Minute Intervals
**Component**: src/trading_bot/validation/multi_timeframe_validator.py
**Severity**: Low
**Description**: Robinhood API doesn't have native 4H interval. Must fetch 10-minute bars and aggregate manually (3 days * 144 bars/day = 432 bars → 18 4H bars).
**Impact**: Increased fetch latency (~500ms for 10min vs ~300ms for daily)
**Alternative**: Use 1-hour interval (closer to 4H), but not available in robin_stocks
**Status**: Accepted trade-off, within performance budget (<2s P95)

### Issue 4: IPO Stocks with <30 Days History
**Component**: src/trading_bot/validation/multi_timeframe_validator.py
**Severity**: Low
**Description**: Stocks with IPO <30 days ago have insufficient daily bars for MACD calculation (requires 26 bars minimum).
**Mitigation**: Validate bar count before indicator calculation, skip daily validation if insufficient, log warning
**Fallback**: Use 4H validation only for new IPOs
**Status**: Expected behavior, documented in quickstart.md troubleshooting

---

## Error Log Entries

[Entries will be added during implementation/testing phases]

### Example Entry Format:

**Error ID**: ERR-033-001
**Phase**: Implementation
**Date**: 2025-10-29 14:32
**Component**: validation/multi_timeframe_validator.py
**Severity**: High

**Description**:
Daily indicator calculation fails with "KeyError: 'close'" when processing DataFrame from MarketDataService. Stack trace shows error in TechnicalIndicatorsService.get_macd() line 45.

**Root Cause**:
MarketDataService.get_historical_data() returns DataFrame with column names normalized to lowercase ('close_price' → 'close'), but a bug in the normalization logic only renames columns if they exist in raw data. When Robinhood API returns sparse data (missing some fields), columns are not renamed.

**Resolution**:
Added defensive check in MultiTimeframeValidator._fetch_daily_indicators():
```python
# Ensure required columns exist
required_cols = {'close', 'high', 'low', 'volume'}
if not required_cols.issubset(df.columns):
    raise InsufficientDataError(
        symbol=symbol,
        required_bars=30,
        available_bars=len(df),
        message=f"Missing required columns: {required_cols - set(df.columns)}"
    )
```

**Prevention**:
- Added unit test: test_validate_missing_columns_raises_error
- Updated data-model.md to document required DataFrame schema
- Added schema validation to MarketDataService.get_historical_data() (separate PR)

**Related**:
- Spec: FR-010 (validate data availability before calculation)
- Code: src/trading_bot/validation/multi_timeframe_validator.py:78
- Commit: abc123f (add schema validation)
- Test: tests/unit/validation/test_multi_timeframe_validator.py::test_validate_missing_columns_raises_error
