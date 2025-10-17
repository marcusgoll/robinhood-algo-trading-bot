# Feature: Technical indicators module

Context from roadmap:
- Title: Technical indicators module
- Area: api
- Role: all
- Impact: 5 | Effort: 3 | Confidence: 0.9 | Score: 1.50
- Status: Backlog → In Progress
- Requirements:
  - VWAP monitor: Fetch current VWAP for symbol, verify price above VWAP for longs, reject entries below VWAP, use VWAP as dynamic support level, update VWAP intraday
  - EMA calculator: Calculate 9-period and 20-period EMAs, detect EMA crossovers, identify when price near 9 EMA (optimal entry), visualize trend angle from EMAs
  - MACD indicator: Calculate MACD line and signal line, verify MACD is positive for longs, detect divergence (lines moving apart), trigger exit when MACD crosses negative
- Blocked by: market-data-module (which is shipped)
- Note: [MERGED: vwap-monitor, ema-calculator, macd-indicator]

## Overview

Technical indicators module provides VWAP, EMA, and MACD calculations for trade entry validation and position management. Integrates with market-data-module (shipped) for OHLCV data fetching and follows Constitution Risk_Management principles for entry/exit validation.

## Research Findings

### Finding 1: Market Data Integration Pattern
Source: `src/trading_bot/market_data/market_data_service.py`
Integration: TechnicalIndicatorsService will consume MarketDataService.get_historical_data() for OHLCV data
Decision: Use existing MarketDataService for all data fetching (no direct robin_stocks calls)
Implication: Must handle DataValidationError, TradingHoursError from market data layer

### Finding 2: Similar Technical Analysis Pattern
Source: `src/trading_bot/momentum/bull_flag_detector.py`
Reusable pattern: Service class with config + market_data_service + logger dependencies
Decision: Follow same architecture for TechnicalIndicatorsService
Implication: Use dataclasses for results, async scan pattern optional, graceful degradation on API errors

### Finding 3: Constitution Requirements
Source: `.spec-flow/memory/constitution.md`
Requirements: Data_Integrity (validate all data, use Decimal), Risk_Management (fail safe), Audit_Everything (log all calculations)
Decision: Use Decimal for all financial calculations, validate inputs, log all indicator values
Implication: ~90% test coverage required, mypy strict mode, bandit security scan

### Finding 4: Project Structure Convention
Source: `D:/Coding/Stocks/src/trading_bot/`
Structure: Service modules in `src/trading_bot/<service_name>/` with __init__.py, config.py, models.py pattern
Decision: Create `src/trading_bot/indicators/` directory with vwap_calculator.py, ema_calculator.py, macd_calculator.py
Implication: Facade pattern via __init__.py for clean imports

### Finding 5: Performance Benchmarks
Source: Existing services (market-data ~2s, screener ~110ms P95)
Target: VWAP <500ms, EMA <500ms, MACD <1s, batch <2s
Decision: Use pandas vectorized operations for calculations (avoid Python loops)
Implication: Add numpy dependency for efficient array math

## System Components Analysis

**Reusable (from existing codebase)**:
- MarketDataService (market_data/market_data_service.py) - OHLCV data fetching
- TradingLogger (logger.py) - Audit logging
- Error handling framework (error_handling/) - @with_retry, exceptions
- Dataclass patterns (momentum/schemas/) - Result models

**New Components Needed**:
- VWAPCalculator (indicators/vwap_calculator.py)
- EMACalculator (indicators/ema_calculator.py)
- MACDCalculator (indicators/macd_calculator.py)
- TechnicalIndicatorsService (indicators/__init__.py) - Facade
- IndicatorConfig (indicators/config.py)
- Result dataclasses (VWAPResult, EMAResult, MACDResult, etc.)

**Rationale**: System-first approach reduces implementation time by reusing market data and logging infrastructure. New indicator calculators are self-contained with clear single responsibilities (KISS principle).

## Feature Classification

- UI screens: False (backend API module, no UI)
- Improvement: False (new feature addition, not optimizing existing)
- Measurable: False (internal technical module, no direct user metrics)
- Deployment impact: False (additive module, no breaking changes, no env vars, no migrations)

## Key Decisions

1. **Calculator Architecture**: Separate calculator classes (VWAP, EMA, MACD) instead of monolithic indicator class
   - Rationale: Single responsibility principle, easier testing, independent evolution
   - Trade-off: More files but better maintainability

2. **Data Source**: Use MarketDataService exclusively, no direct robin_stocks calls
   - Rationale: Centralized data validation, rate limit protection, consistent error handling
   - Trade-off: Dependency on market-data-module but better consistency

3. **Precision**: Use Decimal for all financial calculations (VWAP, EMA, MACD values)
   - Rationale: Avoid float rounding errors (Constitution Data_Integrity requirement)
   - Trade-off: Slightly slower but accurate calculations

4. **Entry Validation Logic**: Both VWAP and MACD checks must pass for entry (conservative AND logic)
   - Rationale: Risk_Management principle - multiple confirmation required
   - Trade-off: Fewer trades but higher quality entries

5. **Intraday Refresh**: 5-minute interval for indicator updates during trading hours
   - Rationale: Balance freshness vs API load (market data may rate-limit)
   - Trade-off: Indicators lag by up to 5 minutes but sustainable

6. **VWAP Calculation Method**: Typical price (H+L+C)/3 instead of close-only
   - Rationale: Industry standard VWAP formula captures intraday range
   - Trade-off: Standard practice, no trade-off

7. **EMA Initialization**: SMA for first value, then exponential smoothing
   - Rationale: Standard practice for EMA calculation
   - Trade-off: Standard practice, no trade-off

8. **Historical Data Requirement**: Minimum 50 days for EMA/MACD
   - Rationale: 20-period EMA needs 40+ bars for accuracy, MACD needs 35+ bars
   - Trade-off: Can't calculate for new stocks with <50 days history

## Phase 1 Summary (Planning)

**Research depth**: 133 lines (research.md)
**Key decisions**: 7 (architecture, data source, precision, validation logic, refresh, VWAP method, historical data)
**Components to reuse**: 5 (MarketDataService, TradingLogger, error_handling, dataclass patterns)
**New components**: 4 (VWAPCalculator, EMACalculator, MACDCalculator, TechnicalIndicatorsService)
**Migration needed**: No (stateless calculations, no database persistence)

**Artifacts created**:
- research.md: 7 research decisions, component reuse analysis
- data-model.md: 10 entity definitions (VWAPResult, EMAResult, MACDResult, CrossoverSignal, DivergenceSignal, ExitSignal, EntryValidation, IndicatorSet, IndicatorConfig)
- plan.md: Comprehensive architecture, calculation flows, testing strategy
- contracts/api.yaml: Internal API specifications for service and calculators
- quickstart.md: 9 integration scenarios with expected outputs
- error-log.md: Initialized for error tracking

**Architecture highlights**:
- Facade pattern: TechnicalIndicatorsService delegates to specialized calculators
- Decimal precision: All financial calculations use Decimal (Constitution §Data_Integrity)
- Conservative validation: AND logic for entry (price > VWAP AND MACD > 0)
- Stateless design: No database persistence, calculations on-demand
- Reuse pattern: MarketDataService for data, TradingLogger for audit trail

## Phase 2: Tasks (2025-10-17T05:30:00Z)

**Summary**:
- Total tasks: 38
- User story tasks: 14 (organized by US1-US12)
- Parallel opportunities: 31 (marked with [P])
- Setup tasks: 3 (Phase 1)
- VWAP tasks: 5 (Phase 2)
- EMA tasks: 5 (Phase 3)
- MACD tasks: 6 (Phase 4)
- Service facade tasks: 6 (Phase 5)
- Testing/validation tasks: 13 (Phase 6)
- Task file: specs/technical-indicators/tasks.md

**Checkpoint**:
- ✅ Tasks generated: 38
- ✅ User story organization: Complete (14 US-labeled tasks)
- ✅ Dependency graph: Created (6 phases with clear ordering)
- ✅ Parallel opportunities: 31 tasks can run in parallel
- ✅ REUSE analysis: 5 existing components identified
- ✅ NEW components: 4 calculators + service facade
- ✅ TDD approach: Tests written before implementation
- ✅ Performance targets: Benchmarked (VWAP <500ms, EMA <500ms, MACD <1s, batch <2s)
- 📋 Ready for: /analyze

**Task Breakdown by Phase**:
- Phase 1 (Setup): 3 tasks - Module structure, config, exceptions
- Phase 2 (VWAP): 5 tasks - Tests + implementation for US1, US2, US3, US11
- Phase 3 (EMA): 5 tasks - Tests + implementation for US4, US5, US6
- Phase 4 (MACD): 6 tasks - Tests + implementation for US7, US8, US9, US10
- Phase 5 (Service): 6 tasks - Integration tests + facade for US11, US12
- Phase 6 (Validation): 13 tasks - Coverage, manual validation, type safety, performance

## Checkpoints

- Phase 0 (Spec-flow): 2025-10-17
- Phase 1 (Plan): 2025-10-17
  - Artifacts: research.md, data-model.md, quickstart.md, plan.md, contracts/api.yaml, error-log.md
  - Research decisions: 7
  - Migration required: No
  - Agent context: Updated (if applicable)
- Phase 2 (Tasks): 2025-10-17
  - Artifacts: tasks.md
  - Total tasks: 38
  - User story tasks: 14
  - Parallel opportunities: 31
  - TDD approach: Yes

## Last Updated

2025-10-17T05:30:00Z
