# Quickstart: 033-multi-timeframe-confirmation

## Scenario 1: Local Development Setup

### Prerequisites
- Python 3.12+
- Robinhood API credentials configured

### Setup Steps

```bash
# Navigate to project root
cd /d/Coding/Stocks

# Install dependencies (if not already installed)
# (No new dependencies required - reuses existing infrastructure)

# Verify existing services work
python -c "from src.trading_bot.market_data.market_data_service import MarketDataService; print('✓ MarketDataService')"
python -c "from src.trading_bot.indicators.service import TechnicalIndicatorsService; print('✓ TechnicalIndicatorsService')"
python -c "from src.trading_bot.patterns.bull_flag import BullFlagDetector; print('✓ BullFlagDetector')"

# Run tests to validate environment
pytest tests/unit/test_market_data/ -v
pytest tests/indicators/ -v
pytest tests/patterns/test_bull_flag.py -v
```

---

## Scenario 2: Unit Testing Multi-Timeframe Validator

### Test: Daily Bearish Blocks Entry

```bash
# Run specific test
pytest tests/unit/validation/test_multi_timeframe_validator.py::test_validate_daily_bearish_blocks_entry -v

# Test validates:
# - Daily MACD negative → daily_score < 0.5
# - Aggregate score < threshold → status = BLOCK
# - Reasons populated with blocking factors
```

### Test: Graceful Degradation on API Failure

```bash
# Run degradation test
pytest tests/unit/validation/test_multi_timeframe_validator.py::test_validate_data_fetch_failure_degrades_gracefully -v

# Test validates:
# - 3 retry attempts with exponential backoff
# - Status = DEGRADED after retries exhausted
# - Warning logged with severity=HIGH
```

### Run All Validation Tests

```bash
# Run full validation test suite
pytest tests/unit/validation/ -v --cov=src/trading_bot/validation

# Expected output:
# - 12+ tests passing
# - 90%+ code coverage
# - <5s total execution time
```

---

## Scenario 3: Integration Testing with Real Market Data

### Test: End-to-End Bull Flag with Multi-Timeframe

```bash
# Run integration test (uses paper trading credentials)
pytest tests/integration/test_bull_flag_multi_timeframe.py::test_e2e_bull_flag_with_timeframe_validation -v

# Test flow:
# 1. Fetch real 5-minute data for AAPL
# 2. Detect bull flag pattern
# 3. Validate against real daily + 4H data
# 4. Verify validation result logged to JSONL
# 5. Check latency < 2s P95
```

### Test: Concurrent Validations (No State Collision)

```bash
# Run concurrency test
pytest tests/integration/test_multi_timeframe_concurrency.py::test_concurrent_validations_no_collision -v

# Test validates:
# - 10 parallel validations for different symbols
# - Each uses isolated TechnicalIndicatorsService instances
# - No state pollution between validations
```

---

## Scenario 4: Manual Testing with CLI

### Enable Multi-Timeframe Validation

```bash
# Set feature flag (default: enabled)
export MULTI_TIMEFRAME_VALIDATION_ENABLED=true

# Run trading bot with multi-timeframe validation
python -m src.trading_bot.main --symbol AAPL --strategy bull_flag --paper-trading

# Expected output:
# [INFO] Multi-timeframe validation enabled
# [INFO] Detected bull flag: AAPL at $150.25
# [INFO] Validating against daily + 4H timeframes...
# [INFO] Daily trend: BULLISH (MACD: 0.82, Price > EMA)
# [INFO] 4H trend: BULLISH (MACD: 0.35, Price > EMA)
# [INFO] Aggregate score: 1.0 (0.6*1.0 + 0.4*1.0) - PASS
# [INFO] Entry allowed: AAPL at $150.25
```

### Test Graceful Degradation

```bash
# Simulate API failure by temporarily disabling network
# (or mock MarketDataService to raise exception)

python -m src.trading_bot.main --symbol TSLA --strategy bull_flag --paper-trading

# Expected output:
# [INFO] Detected bull flag: TSLA at $245.80
# [INFO] Validating against daily + 4H timeframes...
# [ERROR] Failed to fetch daily data: HTTP 503 (attempt 1/3)
# [WARN] Retrying in 1s...
# [ERROR] Failed to fetch daily data: HTTP 503 (attempt 2/3)
# [WARN] Retrying in 2s...
# [ERROR] Failed to fetch daily data: HTTP 503 (attempt 3/3)
# [WARN] Retrying in 4s...
# [WARN] ⚠️  Multi-timeframe validation degraded - proceeding with single-timeframe
# [INFO] Entry allowed (DEGRADED mode): TSLA at $245.80
```

---

## Scenario 5: Analyzing Validation Logs

### Query JSONL Logs

```bash
# View today's validation events
cat logs/timeframe-validation/$(date +%Y-%m-%d).jsonl | jq .

# Count PASS vs BLOCK decisions
cat logs/timeframe-validation/2025-10-28.jsonl | jq -r '.decision' | sort | uniq -c

# Find all BLOCK events with reasons
cat logs/timeframe-validation/*.jsonl | jq 'select(.decision=="BLOCK") | {symbol, reasons, aggregate_score}'

# Calculate average validation latency
cat logs/timeframe-validation/*.jsonl | jq -r '.validation_duration_ms' | awk '{sum+=$1; count++} END {print "Avg latency:", sum/count, "ms"}'

# Find P95 latency
cat logs/timeframe-validation/*.jsonl | jq -r '.validation_duration_ms' | sort -n | awk '{a[NR]=$1} END {print "P95 latency:", a[int(NR*0.95)], "ms"}'

# Count degraded mode occurrences
cat logs/timeframe-validation/*.jsonl | jq 'select(.degraded_mode==true)' | wc -l
```

### Filter by Symbol

```bash
# Get all validation events for AAPL
cat logs/timeframe-validation/*.jsonl | jq 'select(.symbol=="AAPL")'

# Calculate AAPL-specific win rate after multi-timeframe filtering
# (requires correlating with trade outcome logs)
cat logs/trades/*.jsonl | jq 'select(.symbol=="AAPL" and .timeframe_validation_enabled==true) | .outcome' | sort | uniq -c
```

---

## Scenario 6: Backtest Comparison

### Run Baseline (No Multi-Timeframe)

```bash
# Backtest bull flag strategy without multi-timeframe validation
python -m src.trading_bot.backtest \
  --strategy bull_flag \
  --symbols AAPL,TSLA,NVDA \
  --start-date 2024-05-01 \
  --end-date 2024-10-28 \
  --multi-timeframe false \
  --output backtests/results/baseline.json

# Expected output:
# Total trades: 175
# Win rate: 52%
# Avg profit per trade: $82.50
```

### Run Enhanced (With Multi-Timeframe)

```bash
# Backtest bull flag strategy WITH multi-timeframe validation
python -m src.trading_bot.backtest \
  --strategy bull_flag \
  --symbols AAPL,TSLA,NVDA \
  --start-date 2024-05-01 \
  --end-date 2024-10-28 \
  --multi-timeframe true \
  --output backtests/results/enhanced.json

# Expected output:
# Total trades: 105 (70 filtered out)
# Win rate: 63%
# Avg profit per trade: $124.30
```

### Generate Comparison Report

```bash
# Compare baseline vs enhanced
python -m src.trading_bot.backtest.compare \
  --baseline backtests/results/baseline.json \
  --enhanced backtests/results/enhanced.json \
  --output backtests/reports/multi-timeframe-improvement.md

# Report includes:
# - Win rate delta: +11 percentage points (52% → 63%)
# - False positive reduction: 40% (70 filtered / 175 total)
# - Avg profit improvement: +$41.80 per trade
# - Statistical significance: p < 0.05
```

---

## Scenario 7: Disable Multi-Timeframe Validation

### Rollback via Feature Flag

```bash
# Disable multi-timeframe validation without code changes
export MULTI_TIMEFRAME_VALIDATION_ENABLED=false

# Run trading bot (falls back to single-timeframe)
python -m src.trading_bot.main --symbol AAPL --strategy bull_flag --paper-trading

# Expected output:
# [INFO] Multi-timeframe validation disabled (feature flag)
# [INFO] Detected bull flag: AAPL at $150.25
# [INFO] Entry allowed (single-timeframe mode): AAPL at $150.25
```

---

## Troubleshooting

### Issue: Validation Latency > 2s

**Symptom**: Logs show validation_duration_ms > 2000

**Diagnosis**:
```bash
# Check individual data fetch times
cat logs/timeframe-validation/*.jsonl | jq '{symbol, daily_fetch_ms: .daily_fetch_duration_ms, 4h_fetch_ms: .4h_fetch_duration_ms}'
```

**Resolution**:
- Daily fetch >500ms: Check Robinhood API rate limits
- 4H fetch >1000ms: Reduce bar count (use 2-day span instead of 3-day)
- Indicator calc >200ms: Verify pandas DataFrame size (should be <100 bars)

### Issue: High Degraded Mode Rate

**Symptom**: >5% of validations have status=DEGRADED

**Diagnosis**:
```bash
# Count degradation events
cat logs/timeframe-validation/*.jsonl | jq 'select(.degraded_mode==true)' | wc -l

# Check retry reasons
cat logs/timeframe-validation/*.jsonl | jq 'select(.degraded_mode==true) | .reasons'
```

**Resolution**:
- HTTP 429 (rate limit): Increase backoff delay or reduce validation frequency
- HTTP 503 (service unavailable): Temporary API issue, monitor and escalate if persistent
- Data unavailable (<30 bars): Stock IPO or delisting, expected behavior

### Issue: False Negatives (Missing Winning Trades)

**Symptom**: Backtest shows lower trade count, some winning trades filtered

**Diagnosis**:
```bash
# Find trades blocked that would have been winners
# (requires manual review of historical data)
cat logs/timeframe-validation/*.jsonl | jq 'select(.decision=="BLOCK")' > blocked_trades.jsonl
# Compare against historical outcomes
```

**Resolution**:
- Review aggregate_threshold (default 0.5): Lower to 0.4 if too strict
- Adjust daily/4H weighting: Increase 4H weight if daily too dominant
- Check for data quality issues (e.g., stale daily data)
