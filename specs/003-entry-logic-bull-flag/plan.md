# Implementation Plan: Bull Flag Pattern Detection

## [RESEARCH DECISIONS]

See: research.md for full research findings

**Summary**:
- Stack: Python 3.11+, dataclass pattern, Decimal precision
- Components to reuse: 4 (TechnicalIndicatorsService, InsufficientDataError, config/result patterns)
- New components needed: 6 (patterns module with BullFlagDetector, config, models, exceptions, tests)

**Key Research Findings**:
1. Existing TechnicalIndicatorsService provides VWAP/MACD/EMA validation - reuse via composition
2. Dataclass pattern with Decimal precision established in indicators module - follow for consistency
3. Configuration via dataclass with __post_init__ validation matches IndicatorConfig pattern
4. Quality scoring (0-100) differentiates pattern reliability - multi-factor approach
5. Minimum 30 bars required: flagpole + consolidation + MACD (26 bars) + breakout

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Language: Python 3.11+ (existing project standard)
- Data structures: dataclasses with __post_init__ validation
- Numeric precision: Decimal for all financial calculations
- Error handling: Custom exceptions inheriting from Exception
- Testing: pytest with >90% coverage requirement
- Type hints: Full type annotations for all public methods

**Patterns**:
- Composition over modification: BullFlagDetector instantiates TechnicalIndicatorsService rather than modifying it
- Dataclass results: BullFlagResult, FlagpoleData, ConsolidationData follow VWAPResult/MACDResult pattern
- Fail-fast validation: Raise InsufficientDataError when < 30 bars, validate config on initialization
- Multi-phase detection: detect_flagpole() → detect_consolidation() → confirm_breakout() → validate_entry()
- Quality scoring: Multi-factor scoring (0-100) to differentiate pattern reliability

**Dependencies** (existing packages - no new installations required):
- decimal: Decimal precision for financial calculations
- dataclasses: Structured data models
- typing: Type annotations
- datetime: Timestamp handling
- pytest: Testing framework (existing)

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── patterns/                    # NEW: Pattern detection module
│   ├── __init__.py             # Exports BullFlagDetector, BullFlagConfig, BullFlagResult
│   ├── bull_flag.py            # BullFlagDetector class with detection logic
│   ├── config.py               # BullFlagConfig dataclass with validation
│   ├── models.py               # BullFlagResult, FlagpoleData, ConsolidationData
│   └── exceptions.py           # PatternNotFoundError, InvalidConfigurationError
└── indicators/                  # EXISTING: Reuse without modification
    ├── service.py              # TechnicalIndicatorsService (REUSE)
    ├── calculators.py          # VWAP, EMA, MACD calculators (REUSE)
    ├── config.py               # IndicatorConfig pattern (REFERENCE)
    └── exceptions.py           # InsufficientDataError (REUSE)

tests/
├── patterns/                    # NEW: Pattern detection tests
│   ├── __init__.py
│   ├── conftest.py             # Shared fixtures for pattern tests
│   ├── test_bull_flag.py       # Unit tests for BullFlagDetector
│   ├── test_bull_flag_integration.py  # Integration with TechnicalIndicatorsService
│   ├── test_config.py          # Configuration validation tests
│   └── test_models.py          # Data model validation tests
└── indicators/                  # EXISTING: Should pass after integration
    └── test_*.py               # Existing tests (no breaking changes)

specs/003-entry-logic-bull-flag/
├── spec.md                     # Feature specification (EXISTING)
├── plan.md                     # This file
├── research.md                 # Research decisions (CREATED)
├── data-model.md               # Entity definitions (CREATED)
├── quickstart.md               # Integration scenarios (CREATED)
├── contracts/api.yaml          # API contracts (CREATED)
└── error-log.md                # Error tracking (WILL CREATE)
```

**Module Organization**:
- **patterns/bull_flag.py**: Core detection logic with BullFlagDetector class
  - `detect(bars, symbol)`: Main entry point - orchestrates detection phases
  - `_detect_flagpole(bars)`: Identifies upward price movement meeting criteria
  - `_detect_consolidation(bars, flagpole)`: Finds consolidation following flagpole
  - `_confirm_breakout(bars, consolidation)`: Validates breakout above resistance
  - `_calculate_risk_parameters(flagpole, consolidation, breakout_price)`: Stop-loss, target, R/R
  - `_calculate_quality_score(flagpole, consolidation, indicators)`: Multi-factor scoring (0-100)
  - `_validate_with_indicators(bars)`: Call TechnicalIndicatorsService for VWAP/MACD validation

- **patterns/config.py**: BullFlagConfig with validation logic
  - Follows IndicatorConfig pattern: dataclass with __post_init__ validation
  - Default values based on technical analysis standards
  - Validates parameter ranges and logical consistency

- **patterns/models.py**: Result dataclasses
  - BullFlagResult: Complete detection result with all metadata
  - FlagpoleData: Flagpole phase characteristics
  - ConsolidationData: Consolidation phase characteristics

- **patterns/exceptions.py**: Pattern-specific exceptions
  - PatternNotFoundError: Raised when no valid pattern detected
  - InvalidConfigurationError: Raised when config validation fails

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- Entities: 4 (BullFlagResult, FlagpoleData, ConsolidationData, BullFlagConfig)
- Relationships: Composition (BullFlagResult has FlagpoleData and ConsolidationData)
- Migrations required: No (no database changes - pure Python module)

**Key Data Flows**:
1. Input: List[dict] bars (OHLCV format matching TechnicalIndicatorsService)
2. Processing: Multi-phase detection with state tracking
3. Output: BullFlagResult dataclass with all metadata

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: Process 100 stocks for pattern detection in < 5 seconds (50ms per stock)
- NFR-002: False positive rate < 15% (validate with backtesting)
- NFR-003: Test coverage > 90% for pattern detection logic
- NFR-004: Zero breaking changes to TechnicalIndicatorsService

**Optimization Strategies**:
- Early exit: Return immediately if insufficient data or flagpole criteria not met
- Minimize indicator recalculation: Call TechnicalIndicatorsService only once at end
- Use generator expressions for calculations where applicable
- Avoid unnecessary object creation in hot paths

---

## [SECURITY]

**Not Applicable** - This is an internal calculation module with no external interfaces.

**Input Validation** (defensive programming):
- Validate bars parameter is non-empty List[dict]
- Validate all required keys present in bar dictionaries (open, high, low, close, volume)
- Convert string inputs to Decimal with error handling
- Validate symbol parameter is non-empty string
- Raise InsufficientDataError for < 30 bars
- Raise InvalidConfigurationError for invalid BullFlagConfig

**Data Protection**:
- No PII - only stock ticker symbols and price data
- No external data persistence - stateless calculations
- No logging of sensitive data

---

## [EXISTING INFRASTRUCTURE - REUSE] (4 components)

**Services/Modules**:
- src/trading_bot/indicators/service.py: TechnicalIndicatorsService
  - Method: `validate_entry(bars)` - Returns (bool, str) for price > VWAP AND MACD > 0
  - Method: `get_vwap(bars)` - Returns VWAPResult with current VWAP
  - Method: `get_macd(bars)` - Returns MACDResult with MACD values
  - Usage: Instantiate in BullFlagDetector, call for entry validation

**Exceptions**:
- src/trading_bot/indicators/exceptions.py: InsufficientDataError
  - Usage: Raise when len(bars) < 30
  - Pattern: InsufficientDataError(symbol=symbol, required_bars=30, available_bars=len(bars))

**Configuration Pattern**:
- src/trading_bot/indicators/config.py: IndicatorConfig dataclass
  - Reference: Follow __post_init__ validation pattern
  - Reference: Default value pattern with field(default_factory=...)

**Result Pattern**:
- src/trading_bot/indicators/calculators.py: VWAPResult, MACDResult dataclasses
  - Reference: Follow dataclass structure with Decimal fields
  - Reference: Use ROUND_HALF_UP for quantization

---

## [NEW INFRASTRUCTURE - CREATE] (6 components)

**Backend**:
- src/trading_bot/patterns/__init__.py: Package exports
  - Exports: BullFlagDetector, BullFlagConfig, BullFlagResult, FlagpoleData, ConsolidationData
  - Exports: PatternNotFoundError, InvalidConfigurationError

- src/trading_bot/patterns/bull_flag.py: BullFlagDetector class (~300-400 lines)
  - Main method: detect(bars: List[dict], symbol: str) -> BullFlagResult
  - Helper methods: 5 private methods for detection phases
  - Dependencies: TechnicalIndicatorsService, BullFlagConfig, models, exceptions

- src/trading_bot/patterns/config.py: BullFlagConfig dataclass (~80-100 lines)
  - 13 configuration fields with defaults
  - __post_init__ validation for parameter constraints

- src/trading_bot/patterns/models.py: Result dataclasses (~120-150 lines)
  - BullFlagResult: Main result container (15 fields)
  - FlagpoleData: Flagpole metadata (7 fields)
  - ConsolidationData: Consolidation metadata (8 fields)

- src/trading_bot/patterns/exceptions.py: Exception classes (~30-40 lines)
  - PatternNotFoundError: For invalid patterns
  - InvalidConfigurationError: For configuration validation failures

**Testing**:
- tests/patterns/conftest.py: Shared fixtures (~100-150 lines)
  - Fixtures: sample_bars, valid_bull_flag_bars, invalid_pattern_bars
  - Fixtures: default_config, aggressive_config, conservative_config

- tests/patterns/test_bull_flag.py: Unit tests (~500-600 lines)
  - Test categories: flagpole detection, consolidation detection, breakout confirmation
  - Test categories: risk parameter calculation, quality scoring, error handling
  - Coverage target: >90%

- tests/patterns/test_bull_flag_integration.py: Integration tests (~150-200 lines)
  - Integration with TechnicalIndicatorsService
  - End-to-end pattern detection scenarios
  - Verify no breaking changes to indicators module

- tests/patterns/test_config.py: Configuration tests (~100-150 lines)
  - Valid configuration acceptance
  - Invalid configuration rejection
  - Boundary condition validation

- tests/patterns/test_models.py: Data model tests (~80-100 lines)
  - Dataclass instantiation
  - Field validation
  - Serialization/deserialization

**Estimated Total New Code**: ~1500-1800 lines (implementation + tests)

---

## [CI/CD IMPACT]

**From spec.md deployment considerations**:
- Platform: Local-only project (no deployment infrastructure)
- Env vars: None required (no external dependencies)
- Breaking changes: No (new module, no modifications to existing code)
- Migration: No (no database changes)

**Build Commands**:
- No changes to build process
- Standard Python package installation: `pip install -e .`

**Environment Variables**:
- No new environment variables required
- No secrets management needed

**Database Migrations**:
- No database migrations (pure Python calculation module)

**Testing Strategy**:
- Unit tests: pytest tests/patterns/test_bull_flag.py
- Integration tests: pytest tests/patterns/test_bull_flag_integration.py
- Regression tests: pytest tests/indicators/ (verify no breaking changes)
- Coverage: pytest --cov=src.trading_bot.patterns --cov-report=term-missing
- Performance: Custom benchmark script to validate NFR-001 (100 stocks in <5s)

**Quality Gates** (must pass before merge):
1. All unit tests pass (pytest tests/patterns/)
2. All integration tests pass (pytest tests/patterns/test_bull_flag_integration.py)
3. No breaking changes (pytest tests/indicators/ - all existing tests pass)
4. Coverage >90% (pytest --cov=src.trading_bot.patterns)
5. Performance benchmark passes (100 stocks in <5 seconds)
6. Type checking passes (mypy src/trading_bot/patterns/)
7. Linting passes (flake8 src/trading_bot/patterns/)

---

## [DEPLOYMENT ACCEPTANCE]

**Not Applicable** - Local-only project with no deployment infrastructure.

**Merge Acceptance Criteria**:
- All quality gates pass (see above)
- Code review completed
- Documentation updated in module docstrings
- Quickstart.md validated with manual testing

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios

**Summary**:
- Scenario 1: Initial setup and environment validation
- Scenario 2: Development workflow (TDD approach)
- Scenario 3: Integration testing with existing modules
- Scenario 4: Manual pattern detection testing
- Scenario 5: Configuration tuning examples
- Scenario 6: Error handling validation
- Scenario 7: Quality score analysis
- Scenario 8: Pre-merge and pre-deployment checklists

---

## [IMPLEMENTATION SEQUENCE]

**Phase 1: Foundation** (Estimated: 2-3 hours)
1. Create patterns module structure (directories, __init__.py)
2. Implement exceptions.py (PatternNotFoundError, InvalidConfigurationError)
3. Implement models.py (BullFlagResult, FlagpoleData, ConsolidationData)
4. Implement config.py (BullFlagConfig with __post_init__ validation)
5. Write tests for config and models
6. Verify: Configuration validation works, models instantiate correctly

**Phase 2: Core Detection Logic** (Estimated: 4-6 hours)
1. Implement BullFlagDetector.__init__() and detect() entry point
2. Implement _detect_flagpole() method with FR-001 criteria
3. Implement _detect_consolidation() method with FR-002 criteria
4. Implement _confirm_breakout() method with FR-003 criteria
5. Write unit tests for each detection phase
6. Verify: Each phase detects/rejects patterns correctly in isolation

**Phase 3: Risk Parameters and Scoring** (Estimated: 2-3 hours)
1. Implement _calculate_risk_parameters() method (FR-005)
2. Implement _calculate_quality_score() method (FR-006)
3. Write unit tests for risk calculations and scoring
4. Verify: Stop-loss, target, R/R calculated correctly; quality scores reasonable

**Phase 4: Indicator Integration** (Estimated: 2-3 hours)
1. Implement _validate_with_indicators() method (FR-004)
2. Integrate TechnicalIndicatorsService in detect() flow
3. Write integration tests with TechnicalIndicatorsService
4. Verify: Indicator validation works, no breaking changes to indicators module

**Phase 5: End-to-End Testing** (Estimated: 2-3 hours)
1. Write comprehensive end-to-end tests with real-world data patterns
2. Create performance benchmark script (NFR-001)
3. Validate test coverage >90% (NFR-003)
4. Manual testing with quickstart.md scenarios
5. Verify: All acceptance criteria met

**Phase 6: Documentation and Refinement** (Estimated: 1-2 hours)
1. Add comprehensive docstrings to all public methods
2. Update module-level documentation
3. Validate quickstart.md examples work as documented
4. Code review and refinement
5. Final quality gate checks before merge

**Total Estimated Time**: 13-20 hours

---

## [RISK MITIGATION]

**Risk 1: Performance degradation when scanning many stocks**
- Mitigation: Early exit on invalid patterns, minimize indicator recalculation
- Validation: Performance benchmark must show <5s for 100 stocks (NFR-001)

**Risk 2: False positives generating bad entry signals**
- Mitigation: Multi-phase validation, quality scoring, conservative defaults
- Validation: Backtesting shows <15% false positive rate (NFR-002)

**Risk 3: Breaking changes to TechnicalIndicatorsService**
- Mitigation: Use composition (instantiate service), no modifications to existing code
- Validation: All existing indicator tests must pass (NFR-004)

**Risk 4: Insufficient test coverage leading to bugs in production**
- Mitigation: TDD approach, comprehensive test fixtures, >90% coverage requirement
- Validation: pytest coverage report shows >90% (NFR-003)

**Risk 5: Configuration complexity causing user errors**
- Mitigation: Sensible defaults, __post_init__ validation, clear error messages
- Validation: Invalid configs raise helpful ValueError messages

---

## [SUCCESS METRICS]

**Quantitative Metrics** (from spec.md):
1. Pattern detection accuracy: ≥85% true positive rate on manually validated patterns
2. Signal generation speed: <2 seconds per symbol during live scanning
3. Risk management: 100% of signals include stop-loss, target, and ≥2:1 R/R
4. Test coverage: ≥90% for pattern detection module
5. Integration success: 100% of existing indicator tests pass (no breaking changes)

**Qualitative Metrics**:
1. Code maintainability: Clear separation of concerns, well-documented methods
2. Developer experience: Easy to understand and extend for new patterns
3. Configuration flexibility: Users can tune parameters without code changes

---

## [OPEN QUESTIONS]

None - all technical decisions resolved during research phase.

---

## [REFERENCES]

**Existing Codebase**:
- src/trading_bot/indicators/service.py: TechnicalIndicatorsService interface
- src/trading_bot/indicators/calculators.py: Dataclass result pattern, Decimal precision
- src/trading_bot/indicators/config.py: Configuration validation pattern
- src/trading_bot/indicators/exceptions.py: InsufficientDataError exception

**Specifications**:
- specs/003-entry-logic-bull-flag/spec.md: Feature requirements and acceptance criteria
- specs/003-entry-logic-bull-flag/research.md: Research decisions and component reuse analysis

**Technical References**:
- Technical Analysis of Financial Markets (Murphy): Bull flag pattern characteristics
- Python decimal module: Financial calculation precision
- Python dataclasses: Structured data models with validation
