# Research & Discovery: technical-indicators

## Research Decisions

### Decision: Market Data Integration Pattern
**Decision**: Use MarketDataService exclusively for all OHLCV data fetching
**Rationale**:
- MarketDataService already implements retry logic (@with_retry), rate limit handling, and data validation
- Provides consistent error handling (DataValidationError, RateLimitError, TradingHoursError)
- Centralizes robin_stocks API calls, preventing duplicate API request patterns
- Follows existing pattern used in BullFlagDetector (momentum module)
**Alternatives**:
- Direct robin_stocks calls: Rejected - would duplicate retry/validation logic and violate DRY principle
- Separate indicator data fetcher: Rejected - unnecessary abstraction layer
**Source**: src/trading_bot/market_data/market_data_service.py (lines 117-164)

### Decision: Service Architecture Pattern
**Decision**: Separate calculator classes (VWAPCalculator, EMACalculator, MACDCalculator) with facade service
**Rationale**:
- Single Responsibility Principle - each calculator has one clear purpose
- Easier unit testing - can test VWAP, EMA, MACD calculations independently
- Independent evolution - can modify one indicator without affecting others
- Follows existing pattern in momentum module (BullFlagDetector as specialized service)
**Alternatives**:
- Monolithic TechnicalIndicators class: Rejected - violates SRP, harder to test
- Free functions: Rejected - no state management, harder dependency injection
**Source**: src/trading_bot/momentum/bull_flag_detector.py (service class pattern)

### Decision: Decimal Precision for Calculations
**Decision**: Use Decimal type for all financial calculations (VWAP, EMA, MACD values)
**Rationale**:
- Constitution §Data_Integrity requires accurate financial calculations
- Avoids float rounding errors (e.g., 0.1 + 0.2 != 0.3 in float)
- Industry best practice for financial calculations
- Matches pattern in MarketDataService (Quote uses Decimal for current_price)
**Alternatives**:
- Python float: Rejected - rounding errors violate Data_Integrity principle
- Fixed-point integers: Rejected - unnecessary complexity
**Source**: .spec-flow/memory/constitution.md (§Data_Integrity), market_data/data_models.py (Quote model)

### Decision: Entry Validation Logic (AND gate)
**Decision**: Both VWAP and MACD checks must pass for entry (conservative AND logic)
**Rationale**:
- Constitution §Risk_Management requires multiple confirmation for entries
- Reduces false positives - both price structure (VWAP) and momentum (MACD) must align
- Bot fails safe - if either check fails, entry blocked
- Prevents entry on weak signals
**Alternatives**:
- OR logic (either check passes): Rejected - too permissive, increases risk
- Weighted scoring: Rejected - adds complexity without clear benefit for v1
**Source**: .spec-flow/memory/constitution.md (§Risk_Management, §Safety_First)

### Decision: Intraday Refresh Interval (5 minutes)
**Decision**: Update indicators every 5 minutes during trading hours
**Rationale**:
- Balances data freshness vs API load (robin_stocks may rate-limit frequent requests)
- VWAP changes intraday as new bars arrive, 5min is reasonable lag
- EMA/MACD are slower indicators, 5min update sufficient for entry timing
- MarketDataService has retry logic to handle rate limits gracefully
**Alternatives**:
- 1-minute refresh: Rejected - may hit rate limits, marginal freshness benefit
- 15-minute refresh: Rejected - too stale for VWAP support level tracking
**Source**: Existing service patterns, market_data retry policies

### Decision: VWAP Calculation Method (Typical Price)
**Decision**: Use typical price formula: (high + low + close) / 3 for VWAP
**Rationale**:
- Industry standard VWAP calculation (Investopedia, TradingView)
- Captures intraday price range better than close-only
- Weighted by volume for accurate "average transaction price"
- No alternatives - this is the canonical formula
**Alternatives**: None - standard practice
**Source**: https://www.investopedia.com/terms/v/vwap.asp

### Decision: Historical Data Requirement (50 days minimum)
**Decision**: Require minimum 50 trading days of historical data for EMA/MACD
**Rationale**:
- 20-period EMA needs ~40 bars for accurate convergence (2x period rule)
- MACD needs 26-period slow EMA + 9-period signal = 35 bars minimum
- 50 days provides safety margin for accurate calculations
- Prevents unreliable indicators on newly listed stocks
**Alternatives**:
- 35 days (theoretical minimum): Rejected - insufficient warmup for EMA convergence
- 100 days: Rejected - unnecessarily restrictive, reduces coverage
**Source**: Standard technical analysis practice, pandas.ewm() documentation

---

## Components to Reuse (5 found)

- src/trading_bot/market_data/market_data_service.py: OHLCV data fetching with retry/validation
- src/trading_bot/logger.py: TradingLogger for audit logging (§Audit_Everything)
- src/trading_bot/error_handling/retry.py: @with_retry decorator for resilience
- src/trading_bot/error_handling/exceptions.py: Custom exceptions (DataValidationError, etc.)
- src/trading_bot/momentum/schemas/: Dataclass pattern for result models

---

## New Components Needed (4 required)

- src/trading_bot/indicators/vwap_calculator.py: VWAP calculation and entry validation
- src/trading_bot/indicators/ema_calculator.py: EMA calculation, crossover detection, proximity checks
- src/trading_bot/indicators/macd_calculator.py: MACD calculation, divergence detection, exit signals
- src/trading_bot/indicators/__init__.py: TechnicalIndicatorsService facade for clean API

---

## Unknowns & Questions

None - all technical questions resolved during research phase
