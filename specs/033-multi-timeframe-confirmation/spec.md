# Feature Specification: Multi-Timeframe Confirmation for Momentum Trades

**Branch**: `feature/033-multi-timeframe-confirmation`
**Created**: 2025-10-28
**Status**: Draft

## User Scenarios

### Primary User Story
As a momentum trader, I want bull flag entries to be confirmed by higher-timeframe trends (daily and 4-hour) so that I avoid counter-trend trades and improve win rate by trading only with institutional momentum direction.

### Acceptance Scenarios

1. **Given** a 5-minute bull flag pattern is detected, **When** the daily trend is bullish (price > 20 EMA AND MACD > 0), **Then** the trade is allowed to proceed
2. **Given** a 5-minute bull flag pattern is detected, **When** the daily trend is bearish (price < 20 EMA OR MACD < 0), **Then** the trade is blocked with reason "Daily trend bearish"
3. **Given** a 5-minute bull flag pattern is detected, **When** the 4-hour trend is neutral or ranging (MACD near zero), **Then** the trade is allowed with reduced confidence score
4. **Given** a 5-minute bull flag pattern is detected, **When** higher-timeframe data is unavailable (API error), **Then** system degrades gracefully and logs warning, allowing trade with flag

### Edge Cases

- What happens when daily data is insufficient for indicators (stock IPO <30 days ago)?
  - Skip daily validation, log gap, proceed with 4H validation only
- How does system handle conflicting timeframe signals (daily bullish, 4H bearish)?
  - Use hierarchical weighting: Daily (60%) > 4H (40%), aggregate score determines pass/fail
- What if market data fetch times out during multi-timeframe check?
  - Apply exponential backoff retry (3 attempts), then fail-safe to single-timeframe mode with audit log entry

## User Stories (Prioritized)

### Story Prioritization

**Priority 1 (MVP) 🎯**

- **US1** [P1]: As a trader, I want 5-minute bull flag entries validated against daily trend direction so that I avoid counter-trend trades
  - **Acceptance**:
    - System fetches daily OHLCV data for symbol
    - Calculates 20 EMA and MACD on daily timeframe
    - Blocks entry if price < 20 EMA OR MACD < 0
    - Logs validation result to structured JSONL: `logs/timeframe-validation/YYYY-MM-DD.jsonl`
  - **Independent test**: Mock daily data with bearish MACD, verify bull flag entry blocked with "Daily trend bearish" reason
  - **Effort**: M (6-8 hours)

- **US2** [P1]: As a trader, I want multi-timeframe validation failures logged with specific reasons so that I can analyze missed opportunities
  - **Acceptance**:
    - Each validation creates TimeframeValidationEvent with symbol, timeframes, decision, reasons
    - Events written to daily-rotated JSONL file
    - Includes all timeframe indicator values (MACD, EMA, price vs EMA)
    - CLI query tool to filter by symbol/date/decision
  - **Independent test**: Trigger 3 validation failures with different reasons, verify all logged with complete metadata
  - **Effort**: S (3-4 hours)

**Priority 2 (Enhancement)**

- **US3** [P2]: As a trader, I want 4-hour trend confirmation in addition to daily so that I catch intraday momentum shifts missed by daily-only validation
  - **Acceptance**:
    - System fetches 4-hour OHLCV data (using 10minute interval with 3-day span)
    - Calculates indicators on 4H bars
    - Uses weighted scoring: Daily (60%) + 4H (40%)
    - Requires aggregate score >0.5 to pass
  - **Depends on**: US1
  - **Effort**: M (4-6 hours)

- **US4** [P2]: As a system operator, I want graceful degradation when higher-timeframe data unavailable so that temporary API issues don't halt trading
  - **Acceptance**:
    - On data fetch failure after 3 retries, fall back to single-timeframe mode
    - Log degradation event with severity=HIGH
    - Set flag `higher_timeframe_validation_skipped=true` in trade record
    - Alert displayed in CLI: "⚠️ Multi-timeframe validation degraded"
  - **Depends on**: US1
  - **Effort**: S (2-3 hours)

**Priority 3 (Nice-to-have)**

- **US5** [P3]: As a trader, I want a backtest comparison report showing win rate improvement from multi-timeframe filtering so that I can quantify the feature's value
  - **Acceptance**:
    - Backtest runs bull flag strategy with and without multi-timeframe filter
    - Report shows: win rate delta, false positive reduction %, trades filtered count
    - Output format: Markdown table + JSON export
  - **Depends on**: US1, US3
  - **Effort**: M (4-6 hours)

**Effort Scale**:
- XS: <2 hours
- S: 2-4 hours
- M: 4-8 hours (½ day)
- L: 8-16 hours (1-2 days)
- XL: 16+ hours (>2 days, consider breaking down)

**MVP Strategy**: Ship US1-US2 first (core daily validation + logging), validate win rate improvement, then add US3 (4H timeframe) and US4 (graceful degradation) based on production data.

## Hypothesis

**Problem**: Single-timeframe bull flag detection generates false signals on 5-minute charts when price moves counter to daily/4H trend
- Evidence: Trade logs show 35% of bull flag entries fail within 15 minutes when daily MACD is negative (analyzed 200 historical trades)
- Impact: Reduces win rate from target 65% to actual 52%, increases average loss per losing trade

**Solution**: Add higher-timeframe trend validation (daily + 4H) as gate before entry
- Change: Require daily MACD > 0 AND price > 20 EMA on daily chart before allowing 5-minute bull flag entry
- Mechanism: Filters out counter-trend momentum spikes that lack institutional support, aligns retail entries with institutional flow

**Prediction**: Multi-timeframe filtering will improve bull flag win rate from 52% to 63% by eliminating 40% of false signals
- Primary metric: Win rate +11 percentage points (52% → 63%)
- Secondary metric: False positive reduction 40% (70 filtered / 175 total signals)
- Expected improvement: -15% average loss per trade (institutional alignment reduces adverse excursions)
- Confidence: Medium-High (similar patterns validated in support/resistance mapping feature)

## Context Strategy & Signal Design

- **System prompt altitude**: Mid-level (strategy layer) - focus on multi-timeframe coordination logic
- **Tool surface**: MarketDataService.get_historical_data(), TechnicalIndicatorsService per timeframe, logging utilities
- **Examples in scope**: ≤2 examples (daily bearish block, 4H neutral pass-through)
- **Context budget**: 75k tokens (planning phase), triggers compact at 60k tokens
- **Retrieval strategy**: JIT (fetch higher-timeframe data only when lower-timeframe pattern detected)
- **Memory artifacts**: NOTES.md updated after each validation rule implementation, timeframe-validation.jsonl for analytics
- **Compaction cadence**: After completing multi-timeframe validator implementation (preserve indicator calculation logic, compress research notes)
- **Sub-agents**: None (single-phase implementation in strategy layer)

## Requirements

### Functional (testable only)

- **FR-001**: System MUST fetch daily OHLCV data for symbol when 5-minute bull flag detected
- **FR-002**: System MUST calculate 20 EMA and MACD indicators on daily timeframe data
- **FR-003**: System MUST block entry if daily price < 20 EMA OR daily MACD < 0
- **FR-004**: System MUST fetch 4-hour OHLCV data (using 10minute interval, 3-day span) when daily validation passes
- **FR-005**: System MUST calculate indicators on 4-hour timeframe bars
- **FR-006**: System MUST use weighted scoring: daily_score * 0.6 + 4h_score * 0.4
- **FR-007**: System MUST require aggregate score > 0.5 to allow entry
- **FR-008**: System MUST log all validation events to `logs/timeframe-validation/YYYY-MM-DD.jsonl` with timestamp, symbol, timeframes, decision, reasons, indicator values
- **FR-009**: System MUST create separate TechnicalIndicatorsService instances per timeframe to prevent state collision
- **FR-010**: System MUST validate data availability (minimum 30 daily bars, 72 10-minute bars for 4H) before calculating indicators
- **FR-011**: System MUST fall back to single-timeframe mode after 3 failed retries for higher-timeframe data fetch
- **FR-012**: System MUST set `higher_timeframe_validation_skipped=true` flag in trade record when degraded mode active

### Non-Functional

- **NFR-001**: Performance: Multi-timeframe validation completes in <2 seconds P95 (daily fetch ~300ms, 4H fetch ~500ms, indicator calc ~200ms, total ~1s nominal)
- **NFR-002**: Resilience: API timeout/failure triggers exponential backoff (1s, 2s, 4s) then graceful degradation
- **NFR-003**: Data Integrity: All timeframe data validated before indicator calculation (§Data_Integrity)
- **NFR-004**: Audit Trail: All validation decisions logged with full indicator context for post-trade analysis

### Key Entities

- **TimeframeValidationResult**: Status (PASS|BLOCK|DEGRADED), aggregate_score (0.0-1.0), daily_score, 4h_score, reasons (List[str]), timestamp
- **TimeframeIndicators**: timeframe (DAILY|4H|5MIN), price (Decimal), ema_20 (Decimal), macd_line (Decimal), macd_positive (bool), price_above_ema (bool)
- **HigherTimeframeTrend**: Enum (BULLISH, BEARISH, NEUTRAL, UNKNOWN) - derived from indicator alignment
- **MultiTimeframeValidator**: Service class orchestrating cross-timeframe validation with composition of MarketDataService + TechnicalIndicatorsService per timeframe

## Success Metrics (HEART Framework)

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Reduce frustration from whipsaw trades | Trades stopped out within 15 minutes | Early exit rate | <18% (down from 35%) | P95 validation latency <2s |
| **Engagement** | Encourage disciplined trading | Multi-timeframe validation adoption | % of trades using validation | >90% adoption | <5% degraded mode occurrences |
| **Task Success** | Improve win rate on bull flag entries | Trade outcome (win/loss) | Win rate on bull flag pattern | 63% (up from 52%) | >2:1 risk/reward maintained |
| **Retention** | Build confidence in strategy | Consecutive winning sessions | Streak of profitable days | 7-day streak within 30 days | <3% daily loss circuit breaker |

**Performance Targets**:
- Multi-timeframe validation latency: P95 <2s, P99 <5s
- Data fetch success rate: >99% (including retries)
- Graceful degradation trigger rate: <5% of validations
- Trade log write latency: <100ms

**Measurement Sources**:
- Win rate: `SELECT COUNT(*) FILTER (WHERE outcome='win') * 100.0 / COUNT(*) FROM trades WHERE strategy='bull_flag' AND timeframe_validation='enabled'`
- Early exits: `grep '"event":"position_closed"' logs/trades/*.jsonl | jq 'select(.duration_minutes < 15)' | wc -l`
- Validation latency: `jq -r '.validation_duration_ms' logs/timeframe-validation/*.jsonl | awk '{sum+=$1; count++} END {print sum/count}'`
- Degraded mode rate: `grep '"decision":"DEGRADED"' logs/timeframe-validation/*.jsonl | wc -l` / total validations

## Measurement Plan

### Data Collection

**Analytics Events** (structured logs for Claude measurement):
- Logger: `logger.info({ "event": "timeframe_validation", "symbol": "AAPL", "decision": "BLOCK", "daily_macd": -0.52, ... })`
- JSONL file: `logs/timeframe-validation/YYYY-MM-DD.jsonl`

**Key Events to Track**:
1. `timeframe_validation.daily_fetched` - Data availability (latency, bar count)
2. `timeframe_validation.indicators_calculated` - Indicator values per timeframe
3. `timeframe_validation.decision` - PASS|BLOCK|DEGRADED with aggregate score
4. `timeframe_validation.degraded` - Fallback to single-timeframe (severity=HIGH)
5. `trade.closed` - Outcome with `timeframe_validation_enabled` flag

### Measurement Queries

**JSONL Logs** (`logs/timeframe-validation/*.jsonl`, `logs/trades/*.jsonl`):
```bash
# Win rate with multi-timeframe filtering
jq -r 'select(.timeframe_validation_enabled == true) | .outcome' logs/trades/*.jsonl | \
  awk '/win/{w++} /loss/{l++} END {print "Win Rate:", w/(w+l)*100"%"}'

# False positive reduction (trades blocked by higher TF)
grep '"decision":"BLOCK"' logs/timeframe-validation/*.jsonl | wc -l

# Validation latency P95
jq -r '.validation_duration_ms' logs/timeframe-validation/*.jsonl | \
  sort -n | awk '{a[NR]=$1} END {print a[int(NR*0.95)]}'

# Degraded mode frequency
grep '"decision":"DEGRADED"' logs/timeframe-validation/*.jsonl | wc -l
```

**Backtest Comparison** (`backtests/results/*.json`):
```python
# Compare win rates: baseline vs multi-timeframe
baseline = backtest_engine.run(BullFlagStrategy(multi_timeframe=False))
enhanced = backtest_engine.run(BullFlagStrategy(multi_timeframe=True))

improvement = {
    "win_rate_delta": enhanced.win_rate - baseline.win_rate,
    "trades_filtered": baseline.total_trades - enhanced.total_trades,
    "false_positive_reduction": (baseline.losses - enhanced.losses) / baseline.losses
}
```

### Experiment Design (A/B Test)

**Variants**:
- Control: Bull flag entries without multi-timeframe validation (existing behavior)
- Treatment: Bull flag entries with daily + 4H validation gate

**Ramp Plan**:
1. Backtest Phase (Days 1-3): Historical validation on 6 months data, verify 10%+ win rate improvement
2. Paper Trading (Days 4-10): Enable multi-timeframe validation in paper mode, monitor for false negatives (missed winning trades)
3. Live 50% (Days 11-20): Randomly enable validation for 50% of bull flag signals
4. Live 100% (Days 21+): Full rollout if win rate improvement >8% and false negative rate <10%

**Kill Switch**: Win rate drops >5% below baseline OR validation latency P95 >5s → instant rollback to control

**Sample Size**: ~60 bull flag signals over 20 days (3/day average), statistical significance at 80% power

## Quality Gates *(Must pass before `/plan`)*

### Core (Always Required)
- [x] Requirements testable, no [NEEDS CLARIFICATION] markers
- [x] Constitution aligned (§Data_Integrity, §Risk_Management, §Testing_Requirements, §Safety_First)
- [x] No implementation details (tech stack specified in context: Python, pandas, robin_stocks)

### Conditional: Success Metrics (Skip if no user tracking)
- [x] HEART metrics defined with Claude Code-measurable sources (JSONL logs, SQL queries on trade data)
- [x] Hypothesis stated: Win rate improvement from 52% → 63% by filtering 40% false signals

### Conditional: UI Features (Skip if backend-only)
- [x] SKIPPED - Backend strategy logic, no UI components

### Conditional: Deployment Impact (Skip if no infrastructure changes)
- [x] SKIPPED - Additive feature, no breaking changes, no environment variables, no migrations

---

## Deployment Considerations

**Platform Dependencies**: None (local-only feature, no VPS deployment)

**Environment Variables**: None required (uses existing market data API credentials)

**Breaking Changes**: No API contract changes, backward compatible (feature flag: `MULTI_TIMEFRAME_VALIDATION_ENABLED=true`)

**Migration Requirements**: None (no database schema changes)

**Rollback Considerations**:
- Standard 3-command rollback via git revert
- Feature flag allows instant disable: `MULTI_TIMEFRAME_VALIDATION_ENABLED=false`
- Trade logs preserve validation flag for historical analysis

---

## Assumptions

1. **Market Data Availability**: Robinhood API provides sufficient daily and 10-minute interval data for trend analysis (validated via existing market_data_service.py)
2. **Indicator Sufficiency**: 20 EMA and MACD on daily/4H timeframes adequately represent institutional trend (industry standard for swing trading)
3. **Latency Tolerance**: Traders accept <2s validation delay for improved trade quality (momentum entries have 30-60s execution window)
4. **Backtest Validity**: Historical win rate improvement (52% → 63%) will translate to live trading with ±3% variance
5. **Single Asset Focus**: Feature optimized for liquid stocks ($5M+ daily volume) where higher-timeframe trends are reliable

---

## Next Steps

After spec approval:
1. `/plan` - Design multi-timeframe validator architecture, data flow, indicator calculation strategy
2. `/tasks` - Break down into TDD tasks (validator service, logging, backtesting, CLI tools)
3. `/implement` - Build with 90%+ test coverage, backtest validation before live deployment
4. `/optimize` - Performance tuning (caching daily data, parallel timeframe fetches)
