# Tasks: Momentum and Catalyst Detection

## [CODEBASE REUSE ANALYSIS]
Scanned: D:\Coding\Stocks\src\trading_bot/**/*.py

[EXISTING - REUSE]
- ✅ MarketDataService (src/trading_bot/market_data/market_data_service.py) - get_quote(), get_historical_data(), @with_retry
- ✅ StructuredTradeLogger (src/trading_bot/logging/structured_logger.py) - Daily JSONL rotation, thread-safe logging
- ✅ @with_retry decorator (src/trading_bot/error_handling/retry.py) - Exponential backoff with circuit breaker
- ✅ RetryPolicy (src/trading_bot/error_handling/policies.py) - DEFAULT_POLICY with 3 retries
- ✅ RobinhoodAuth (src/trading_bot/auth/robinhood_auth.py) - API authentication

[NEW - CREATE]
- 🆕 CatalystDetector - No existing news detection pattern
- 🆕 PreMarketScanner - No existing pre-market monitoring
- 🆕 BullFlagDetector - No existing pattern detection
- 🆕 MomentumRanker - No existing signal aggregation

## [DEPENDENCY GRAPH]
Story completion order:
1. Phase 1: Setup (project structure)
2. Phase 2: Foundational (schemas, logging, config)
3. Phase 3: US1 [P1] - Catalyst detection (independent)
4. Phase 4: US2 [P1] - Pre-market scanner (independent)
5. Phase 5: US3 [P1] - Bull flag detection (independent)
6. Phase 6: US4 [P2] - Composite scoring (depends on US1-US3)

## [PARALLEL EXECUTION OPPORTUNITIES]
- Phase 2: T005, T006, T007 (different files, no dependencies)
- Phase 3 (US1): T011, T012 (tests can run parallel)
- Phase 4 (US2): T021, T022 (tests can run parallel)
- Phase 5 (US3): T031, T032 (tests can run parallel)
- Phase 6 (US4): T041 (single task)

## [IMPLEMENTATION STRATEGY]
**MVP Scope**: Phase 3-5 (US1-US3) independently testable
**Incremental delivery**: US1 → US2 → US3 → US4
**Testing approach**: Unit tests required (≥90% coverage per spec NFR-006)

---

## Phase 1: Setup

- [ ] T001 Create project structure per plan.md tech stack
  - Files: src/trading_bot/momentum/__init__.py, src/trading_bot/momentum/schemas/__init__.py, src/trading_bot/momentum/logging/__init__.py
  - Pattern: src/trading_bot/market_data/ structure
  - From: plan.md [PROJECT STRUCTURE]

- [ ] T002 [P] Create test directory structure
  - Files: tests/unit/services/momentum/, tests/integration/momentum/, tests/unit/services/momentum/conftest.py
  - Pattern: tests/unit/services/ existing structure
  - From: plan.md [PROJECT STRUCTURE]

- [ ] T003 [P] Create documentation structure
  - Files: specs/002-momentum-detection/docs/momentum-architecture.md, specs/002-momentum-detection/docs/momentum-api.md, specs/002-momentum-detection/docs/momentum-examples.md
  - From: plan.md [PROJECT STRUCTURE]

---

## Phase 2: Foundational (blocking prerequisites)

**Goal**: Infrastructure that blocks all user stories

- [ ] T005 [P] Create data model schemas in src/trading_bot/momentum/schemas/momentum_signal.py
  - Classes: SignalType(Enum), CatalystType(Enum), MomentumSignal(dataclass), CatalystEvent(dataclass), PreMarketMover(dataclass), BullFlagPattern(dataclass)
  - Fields: From data-model.md entity definitions
  - Validation: __post_init__ methods for field validation per data-model.md rules
  - Pattern: src/trading_bot/market_data/data_models.py (MarketDataConfig, Quote, MarketStatus)
  - From: data-model.md [Entities]

- [ ] T006 [P] Create MomentumConfig dataclass in src/trading_bot/momentum/config.py
  - Fields: news_api_key (str), market_data_source (str), min_catalyst_strength (float), min_premarket_change_pct (float), min_volume_ratio (float), pole_min_gain_pct (float), flag_range_pct_min (float), flag_range_pct_max (float)
  - Defaults: From spec.md requirements (5%, 200%, 8%, 3%, 5%)
  - ENV vars: NEWS_API_KEY, MARKET_DATA_SOURCE
  - Pattern: src/trading_bot/market_data/data_models.py MarketDataConfig
  - From: plan.md [ARCHITECTURE DECISIONS]

- [ ] T007 [P] Create MomentumLogger wrapper in src/trading_bot/momentum/logging/momentum_logger.py
  - Class: MomentumLogger wrapping StructuredTradeLogger
  - Methods: log_signal(signal: MomentumSignal), log_scan_event(event_type, metadata), log_error(error, context)
  - JSONL format: From plan.md [Logging Strategy]
  - REUSE: StructuredTradeLogger (src/trading_bot/logging/structured_logger.py)
  - Pattern: src/trading_bot/logging/structured_logger.py
  - From: plan.md [Logging Strategy]

---

## Phase 3: User Story 1 [P1] - Catalyst Detection

**Story Goal**: Identify stocks with breaking news catalysts (last 24 hours)

**Independent Test Criteria**:
- [ ] User requests catalyst scan → returns CatalystEvent objects with valid catalyst_type
- [ ] News published >24 hours ago → excluded from results
- [ ] News API failure → graceful degradation (log error, return empty list)

### Tests

- [ ] T011 [P] [US1] Write test: CatalystDetector.categorize() classifies news headlines correctly
  - File: tests/unit/services/momentum/test_catalyst_detector.py
  - Test cases: Earnings ("Q4 earnings beat"), FDA ("FDA approval"), Merger ("Merger announced"), Product Launch ("New product"), Analyst ("Upgraded to Buy")
  - Fixtures: Mock headlines with expected catalyst types
  - Pattern: tests/unit/services/test_market_data_service.py
  - Coverage: ≥90% for categorize() method

- [ ] T012 [P] [US1] Write test: CatalystDetector.scan() fetches and filters news within 24 hours
  - File: tests/unit/services/momentum/test_catalyst_detector.py
  - Mock: Alpaca API response with news items (some stale, some fresh)
  - Assert: Only news within 24 hours returned, correct MomentumSignal structure
  - Pattern: tests/unit/services/test_market_data_service.py
  - Coverage: ≥90% for scan() method

### Implementation

- [ ] T015 [US1] Create CatalystDetector service in src/trading_bot/momentum/catalyst_detector.py
  - Methods: async scan(symbols: List[str]) -> List[MomentumSignal], categorize(headline: str) -> CatalystType
  - Logic: Fetch news from Alpaca, filter last 24h, categorize catalyst type, build MomentumSignal
  - Catalyst keywords: {"earnings": ["earnings", "EPS", "revenue"], "FDA": ["FDA", "approval"], "merger": ["merger", "acquisition"], "product": ["launch", "unveil"], "analyst": ["upgrade", "downgrade", "initiated"]}
  - REUSE: @with_retry decorator, MomentumLogger
  - Pattern: src/trading_bot/market_data/market_data_service.py (API calls with @with_retry)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] CatalystDetector

- [ ] T016 [US1] Add error handling for missing NEWS_API_KEY
  - Logic: Check config.news_api_key, if None log warning and return empty list (graceful degradation)
  - From: spec.md Dependencies and Blockers (API access blocker)

### Integration

- [ ] T017 [US1] Write integration test for CatalystDetector with mocked Alpaca API
  - File: tests/integration/momentum/test_catalyst_detector_integration.py
  - Mock: Alpaca news API response with realistic data
  - Assert: End-to-end scan returns valid signals, logs to MomentumLogger
  - Pattern: tests/integration/ existing structure
  - Coverage: ≥90% critical path

---

## Phase 4: User Story 2 [P1] - Pre-Market Scanner

**Story Goal**: Identify stocks with >5% pre-market price change and >200% volume

**Independent Test Criteria**:
- [ ] Stock has >5% pre-market change and >200% volume → PreMarketMover signal created
- [ ] Stock has >5% change but <200% volume → excluded from results
- [ ] Scan called outside pre-market hours (9:30 AM - 4 PM EST) → returns empty list with log

### Tests

- [ ] T021 [P] [US2] Write test: PreMarketScanner.is_premarket_hours() detects pre-market window correctly
  - File: tests/unit/services/momentum/test_premarket_scanner.py
  - Test cases: 4:00 AM EST (true), 9:29 AM EST (true), 9:31 AM EST (false), 3:00 PM EST (false), Saturday (false)
  - Timezone: Mock datetime.now() with different UTC times
  - Pattern: tests/unit/services/test_market_data_service.py
  - Coverage: ≥90% for timezone logic

- [ ] T022 [P] [US2] Write test: PreMarketScanner.scan() identifies movers with >5% and >200% volume
  - File: tests/unit/services/momentum/test_premarket_scanner.py
  - Mock: MarketDataService.get_quote() with pre-market data
  - Test cases: >5% and >200% volume (signal), >5% but <200% volume (no signal), <5% (no signal)
  - Pattern: tests/unit/services/test_market_data_service.py
  - Coverage: ≥90% for scan() method

### Implementation

- [ ] T025 [US2] Create PreMarketScanner service in src/trading_bot/momentum/premarket_scanner.py
  - Methods: async scan(symbols: List[str]) -> List[MomentumSignal], is_premarket_hours() -> bool
  - Logic: Check time window (4-9:30 AM EST), fetch quotes, calculate price_change_pct and volume_ratio, filter thresholds
  - Timezone: pytz or zoneinfo for EST conversion (use zoneinfo like MarketDataService)
  - REUSE: MarketDataService.get_quote(), @with_retry, MomentumLogger
  - Pattern: src/trading_bot/market_data/market_data_service.py (_determine_market_state)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] PreMarketScanner

- [ ] T026 [US2] Calculate 10-day average pre-market volume baseline
  - Logic: Use MarketDataService.get_historical_data() for last 10 days, aggregate pre-market volume (4-9:30 AM bars), calculate average
  - Fallback: If no historical data, assume avg_volume = current volume (ratio = 1.0)
  - From: spec.md FR-005 (unusual volume calculation)

- [ ] T027 [US2] Add timestamp validation for pre-market window (UTC storage, EST comparison)
  - Logic: Convert current time to EST, validate 4:00-9:30 AM range, log all timestamps in UTC
  - From: spec.md NFR-004 (UTC timestamps)

### Integration

- [ ] T028 [US2] Write integration test for PreMarketScanner with real market data
  - File: tests/integration/momentum/test_premarket_scanner_integration.py
  - Mock: MarketDataService with realistic pre-market quotes
  - Assert: Correct signal generation, volume calculation, timezone handling
  - Pattern: tests/integration/ existing structure
  - Coverage: ≥90% critical path

---

## Phase 5: User Story 3 [P1] - Bull Flag Pattern Detection

**Story Goal**: Detect bull flag chart patterns (pole + consolidation)

**Independent Test Criteria**:
- [ ] Stock with >8% pole gain and 3-5% flag range → BullFlagPattern signal created
- [ ] Stock with pole but flag range >5% → pattern_valid=false, no signal
- [ ] Stock with upward flag slope → pattern_valid=false, no signal

### Tests

- [ ] T031 [P] [US3] Write test: BullFlagDetector._detect_pole() identifies >8% gain in 1-3 days
  - File: tests/unit/services/momentum/test_bull_flag_detector.py
  - Test cases: 10% gain in 2 days (valid), 5% gain in 2 days (invalid), 10% gain in 5 days (invalid)
  - Mock: OHLCV candles with synthetic price data
  - Pattern: tests/unit/services/test_market_data_service.py
  - Coverage: ≥90% for pole detection

- [ ] T032 [P] [US3] Write test: BullFlagDetector._detect_flag() validates consolidation criteria
  - File: tests/unit/services/momentum/test_bull_flag_detector.py
  - Test cases: 3-5% range, 2-5 days duration, downward slope (valid), 6% range (invalid), upward slope (invalid)
  - Mock: OHLCV candles after pole
  - Pattern: tests/unit/services/test_market_data_service.py
  - Coverage: ≥90% for flag detection

- [ ] T033 [P] [US3] Write test: BullFlagDetector._calculate_targets() computes breakout price and target
  - File: tests/unit/services/momentum/test_bull_flag_detector.py
  - Test case: Pole from $100 to $120 (+20%), flag at $115-$118, breakout = $118, target = $138 (pole height $20 projected)
  - Pattern: tests/unit/services/test_market_data_service.py
  - Coverage: ≥90% for target calculation

### Implementation

- [ ] T035 [US3] Create BullFlagDetector service in src/trading_bot/momentum/bull_flag_detector.py
  - Methods: async scan(symbols: List[str]) -> List[MomentumSignal], _detect_pattern(ohlcv: pd.DataFrame) -> Optional[BullFlagPattern]
  - Internal methods: _detect_pole(), _detect_flag(), _calculate_targets(), _validate_slope()
  - Pattern logic: From spec.md FR-006 (pole >8%, 1-3 days; flag 3-5% range, 2-5 days, downward/flat slope)
  - REUSE: MarketDataService.get_historical_data(), @with_retry, MomentumLogger
  - Pattern: src/trading_bot/market_data/market_data_service.py (DataFrame handling)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] BullFlagDetector

- [ ] T036 [US3] Implement pole detection logic (_detect_pole)
  - Logic: Scan last 100 days for consecutive 1-3 day periods with >8% gain (high_price - low_price) / low_price
  - Return: pole_start, pole_end, pole_gain_pct, pole_high_price, pole_low_price
  - From: spec.md FR-006 pole criteria

- [ ] T037 [US3] Implement flag detection logic (_detect_flag)
  - Logic: After pole, scan next 2-5 days for consolidation with price range 3-5%
  - Calculate flag_range_pct: (flag_high - flag_low) / flag_low
  - Calculate flag_slope_pct: (flag_close - flag_open) / flag_open (must be ≤0 for downward/flat)
  - Return: flag_start, flag_end, flag_high_price, flag_low_price, flag_range_pct, flag_slope_pct
  - From: spec.md FR-006 flag criteria

- [ ] T038 [US3] Implement breakout target calculation (_calculate_targets)
  - Logic: breakout_price = flag_high_price, price_target = breakout_price + pole_height
  - pole_height = pole_high_price - pole_low_price
  - From: spec.md FR-007 (price target calculation)

- [ ] T039 [US3] Add pattern validation (pattern_valid flag)
  - Logic: pattern_valid = (pole_gain_pct >= 8%) AND (3% <= flag_range_pct <= 5%) AND (flag_slope_pct <= 0) AND (pole duration 1-3 days) AND (flag duration 2-5 days)
  - From: data-model.md BullFlagPattern.pattern_valid

### Integration

- [ ] T040 [US3] Write integration test for BullFlagDetector with historical data
  - File: tests/integration/momentum/test_bull_flag_detector_integration.py
  - Mock: MarketDataService with realistic 100-day OHLCV data
  - Test cases: Valid bull flag, invalid pattern (flag too wide), no pattern found
  - Pattern: tests/integration/ existing structure
  - Coverage: ≥90% critical path

---

## Phase 6: User Story 4 [P2] - Composite Scoring

**Story Goal**: Aggregate signals across all detectors and rank by composite strength

**Independent Test Criteria**:
- [ ] Stock with catalyst + pre-market + pattern → composite score calculated (weighted average)
- [ ] Stock with only catalyst → composite score based on catalyst strength alone
- [ ] Stocks ranked by composite score descending

### Tests

- [ ] T041 [P] [US4] Write test: MomentumRanker.score_composite() calculates weighted average correctly
  - File: tests/unit/services/momentum/test_momentum_ranker.py
  - Test case: catalyst=80, premarket=60, pattern=90 → composite = 0.25*80 + 0.35*60 + 0.40*90 = 77.0
  - Test case: catalyst=80, premarket=0, pattern=0 → composite = 20.0 (only catalyst contributes)
  - Pattern: tests/unit/services/ existing structure
  - Coverage: ≥90% for scoring logic

### Implementation

- [ ] T045 [US4] Create MomentumRanker service in src/trading_bot/momentum/momentum_ranker.py
  - Methods: rank(signals: List[MomentumSignal]) -> List[MomentumSignal], score_composite(catalyst_score, premarket_score, pattern_score) -> float
  - Scoring: Linear weighted average (25% catalyst, 35% pre-market, 40% pattern) per plan.md
  - Group signals by symbol, aggregate scores, update MomentumSignal.strength
  - REUSE: MomentumLogger
  - Pattern: Simple aggregation logic (no external pattern to follow)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] MomentumRanker

- [ ] T046 [US4] Add signal aggregation by symbol
  - Logic: Group MomentumSignal objects by symbol, extract scores per signal_type, compute composite
  - Handle missing signals: If symbol has no catalyst, use 0 for catalyst_score
  - From: spec.md US4 acceptance criteria

### Integration

- [ ] T047 [US4] Write integration test for MomentumRanker with mixed signals
  - File: tests/integration/momentum/test_momentum_ranker_integration.py
  - Test: Create signals from all 3 detectors, rank, verify composite scores and ordering
  - Pattern: tests/integration/ existing structure
  - Coverage: ≥90% critical path

---

## Phase 7: Composition Root & API

**Goal**: Orchestrate all detectors via MomentumEngine and expose API endpoints

- [ ] T050 [P] Create MomentumEngine composition root in src/trading_bot/momentum/__init__.py
  - Class: MomentumEngine with __init__(config: MomentumConfig)
  - Initialize: CatalystDetector, PreMarketScanner, BullFlagDetector, MomentumRanker
  - Method: async scan(symbols: List[str]) -> List[MomentumSignal]
  - Parallel execution: asyncio.gather() for independent detectors
  - Pattern: From plan.md [ARCHITECTURE DECISIONS] Composition Root example
  - From: plan.md [ARCHITECTURE DECISIONS]

- [ ] T051 [P] Create FastAPI routes in src/trading_bot/momentum/routes/signals.py
  - Endpoint: GET /api/v1/momentum/signals (query params: symbols, signal_type, min_strength, start_time, end_time, sort_by, limit, offset)
  - Response: List of MomentumSignal objects from JSONL logs
  - Pattern: src/trading_bot/api/ existing routes (if any)
  - From: data-model.md [API Endpoints]

- [ ] T052 [P] Create scan endpoint in src/trading_bot/momentum/routes/scan.py
  - Endpoint: POST /api/v1/momentum/scan (body: {symbols: List[str], scan_types: List[str]})
  - Response: 202 Accepted with scan_id and status
  - Async execution: Queue scan task, return immediately
  - Pattern: src/trading_bot/api/ existing routes (if any)
  - From: data-model.md [API Endpoints]

---

## Phase 8: Polish & Cross-Cutting Concerns

### Error Handling & Resilience

- [ ] T055 [P] Add comprehensive error handling to all detectors
  - Logic: Wrap all API calls with try/except, log to MomentumLogger.log_error(), return empty list on failure
  - Graceful degradation: Continue processing other symbols if one fails
  - From: spec.md FR-010 (handle missing data gracefully)

- [ ] T056 [P] Add input validation to all scan() methods
  - Validate: symbols list non-empty, symbols match regex ^[A-Z]{1,5}$
  - Raise: ValueError with descriptive message if validation fails
  - From: spec.md FR-011 (validate input data)

- [ ] T057 [P] Add API rate limit handling
  - Logic: Use @with_retry with RateLimitError detection (already in DEFAULT_POLICY)
  - Exponential backoff: 2s, 4s, 8s (max 3 retries)
  - From: spec.md FR-012 (respect rate limits)

### Deployment Preparation

- [ ] T060 Document usage examples in specs/002-momentum-detection/docs/momentum-examples.md
  - Examples: CatalystDetector standalone, PreMarketScanner standalone, BullFlagDetector standalone, MomentumEngine full scan, API usage
  - From: plan.md [INTEGRATION SCENARIOS]

- [ ] T061 [P] Add health check logic (optional Phase 2)
  - Logic: Verify NEWS_API_KEY set, MarketDataService accessible, JSONL log directory writable
  - Return: {"status": "ok", "dependencies": {"news_api": "ok", "market_data": "ok", "logging": "ok"}}
  - From: plan.md [CI/CD IMPACT] Smoke Tests

- [ ] T062 [P] Update .env.example with new environment variables
  - Variables: NEWS_API_KEY, MARKET_DATA_SOURCE
  - Defaults: MARKET_DATA_SOURCE="alpaca"
  - From: spec.md Deployment Considerations

### Testing & Validation

- [ ] T065 Run full test suite and verify ≥90% coverage
  - Command: pytest tests/unit/services/momentum/ --cov=src/trading_bot/momentum --cov-report=term-missing
  - Target: ≥90% line coverage per spec.md NFR-006
  - Fix: Any uncovered code paths

- [ ] T066 [P] Add E2E test for complete momentum scan workflow
  - File: tests/integration/momentum/test_momentum_engine_e2e.py
  - Mock: All API calls (Alpaca news, market data)
  - Test: MomentumEngine.scan() with realistic data, verify signals ranked correctly
  - Coverage: ≥90% critical path

---

## [TEST GUARDRAILS]

**Speed Requirements:**
- Unit tests: <2s each
- Integration tests: <10s each
- Full suite: <6 min total

**Coverage Requirements:**
- New code: 100% coverage (no untested lines in new features)
- Unit tests: ≥90% line coverage (per spec.md NFR-006)
- Integration tests: ≥60% line coverage
- Critical path: ≥90% coverage

**Measurement:**
- Python: `pytest --cov=src/trading_bot/momentum --cov-report=term-missing`

**Quality Gates:**
- All tests must pass before merge
- Coverage thresholds enforced manually
- No skipped tests without documented reason

**Clarity Requirements:**
- One behavior per test
- Descriptive names: `test_catalyst_detector_categorizes_earnings_news_correctly()`
- Given-When-Then structure in test body

**Anti-Patterns:**
- ❌ NO snapshot tests (not applicable for backend)
- ❌ NO "prop-mirror" tests (test behavior, not implementation)
- ✅ USE mocked API responses (no real API calls in tests)
- ✅ USE dataclass validation (test __post_init__ checks)

**Examples:**
```python
# ❌ Bad: Testing implementation detail
def test_catalyst_detector_has_categorize_method():
    assert hasattr(CatalystDetector, 'categorize')

# ✅ Good: Testing behavior
def test_catalyst_detector_categorizes_earnings_news_as_earnings_type():
    detector = CatalystDetector()
    result = detector.categorize("Company announces Q4 earnings beat")
    assert result == CatalystType.EARNINGS
```
