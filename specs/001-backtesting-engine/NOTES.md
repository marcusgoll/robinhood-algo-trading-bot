# Feature: Backtesting Engine

## Overview
Implementation of a comprehensive backtesting engine to validate trading strategies against historical market data before deployment to paper or live trading. This critical safety feature enables strategy validation and performance analysis without risking capital.

## Research Findings

### Constitution Compliance
From `.specify/memory/constitution.md`:
- **§Testing_Requirements**: "Backtesting - Strategy validation against historical data" is explicitly required
- **§Safety_First**: "Never trade with real money until fully tested" - backtesting is the validation gate
- **§Code_Quality**: Must maintain 90% test coverage, type hints required
- **§Risk_Management**: Backtesting validates stop losses, position sizing, and risk controls
- **§Data_Integrity**: Must handle missing data, validate timestamps (UTC), ensure data completeness

### Existing Project Structure
From codebase analysis:
- Project uses Python 3.11+ with `robin_stocks` library
- Type checking with `mypy`, testing with `pytest`
- Configuration in `config.json` for trading parameters
- Existing modules: market_data, order_management, performance tracking, risk management
- No existing backtest module found - this is net new capability

### Similar Features
From roadmap and specs:
- `002-momentum-detection`: Backend trading logic, similar testing requirements
- `performance tracking`: Existing module for trade analysis that can be leveraged
- Template available: `.spec-flow/templates/backtest-report-template.md` for output format

### Key Decisions Required
1. Historical data source: Use existing market_data module or dedicated backtest data provider?
2. Execution model: Event-driven simulation or vectorized backtesting?
3. Slippage/commission modeling: Simple fixed cost or realistic market impact?
4. Output format: JSON, CSV, or rich HTML reports?
5. Strategy interface: How do strategies plug into backtest engine?

## System Components Analysis
Backend-only feature - no UI components.

Potential reuse from existing codebase:
- `src/trading_bot/market_data/`: Market data fetching and validation
- `src/trading_bot/performance/`: Performance tracking and metrics
- `src/trading_bot/order_management/`: Order execution logic (can be simulated)
- `src/trading_bot/risk_management/`: Risk controls to validate in backtest

New components needed:
- Backtest engine core
- Historical data manager
- Simulated broker/executor
- Performance analyzer
- Backtest report generator

## Feature Classification
- UI screens: false (backend-only)
- Improvement: false (new capability)
- Measurable: false (internal tooling, not user-facing metrics)
- Deployment impact: false (no infrastructure changes, new Python module only)

## Checkpoints
- Phase 0 (Specification): 2025-10-19
- Phase 1 (Planning): 2025-10-19

## Phase Summaries

### Phase 1: Planning
- Research depth: 150 lines (6 key decisions documented)
- Key decisions: Event-driven execution, Alpaca+Yahoo data sources, Protocol interface, next-bar-open fills, file-based reports, disk caching
- Components to reuse: 7 (market data service, validators, performance models, retry, auth, logging, data models)
- New components: 5 (engine, historical data manager, strategy protocol, performance calculator, report generator)
- Migration needed: No

**Artifacts Generated**:
- research.md: Research decisions + component reuse analysis
- data-model.md: 5 entity definitions + ER diagram + validation rules
- quickstart.md: 6 integration scenarios (setup, run, custom strategy, validation, comparison, manual tests)
- plan.md: Consolidated architecture + 7-phase implementation roadmap
- contracts/api.yaml: Python API schemas (OpenAPI format)
- error-log.md: Initialized for error tracking

## Last Updated
2025-10-19T19:58:00Z

### Phase 2: Tasks (2025-10-19)

**Summary**:
- Total tasks: 61
- User story tasks: 39 (US1: 8, US2: 12, US3: 10, US4: 9)
- Parallel opportunities: 40 tasks marked [P]
- Setup tasks: 3 (Phase 1)
- Foundational tasks: 3 (Phase 2)
- Integration tasks: 5 (Phase 7)
- Polish tasks: 11 (Phase 8)
- Task file: specs/001-backtesting-engine/tasks.md

**Checkpoint**:
- ✅ Tasks generated: 61 concrete tasks
- ✅ User story organization: Complete (US1-US4 phases)
- ✅ Dependency graph: Created (US1 → US2 → US3 → US4)
- ✅ MVP strategy: Defined (US1-US4 only, defer US5-US9)
- ✅ REUSE markers: 7 existing modules identified
- ✅ NEW components: 5 to create
- ✅ Parallel execution: 40 tasks can run in parallel
- ✅ TDD approach: Tests before implementation for each story
- 📋 Ready for: /analyze

**Task Breakdown by Phase**:
- Phase 1 (Setup): T001-T003 (3 tasks)
- Phase 2 (Foundational): T005-T007 (3 tasks)
- Phase 3 (US1 - Historical Data): T010-T018 (9 tasks)
- Phase 4 (US2 - Backtest Engine): T020-T031 (12 tasks)
- Phase 5 (US3 - Performance Metrics): T035-T045 (11 tasks)
- Phase 6 (US4 - Report Generation): T050-T059 (10 tasks)
- Phase 7 (Integration): T070-T075 (6 tasks)
- Phase 8 (Polish): T080-T092 (13 tasks)
✅ T003 [P]: Added .backtest_cache/ to .gitignore for historical data caching
  - Evidence: .gitignore updated with comment explaining cache purpose
  - Committed: 9d077eb

✅ T002 [P]: Added yfinance==0.2.36 and pyarrow==15.0.0 to requirements.txt with explanatory comments
  - Evidence: Dependencies added following existing format in Data analysis section
  - Committed: 9d077eb

✅ T001: Created backtest project structure (backtest/, tests/backtest/, examples/)
  - Evidence: Directories created successfully
  - Committed: 35617ae

✅ T006 [P]: Created 4 backtest exception classes following established patterns
  - Evidence: Exception hierarchy: BacktestException, DataQualityError, InsufficientDataError, StrategyError
  - Committed: 5301396

✅ T007 [P]: Created 3 date/validation utility functions with 100% test coverage
  - Evidence: 32 tests passing, handles weekends/holidays/edge cases, full type hints
  - Committed: f8b0937

✅ T005: Created 7 backtest data models with comprehensive validation
  - Models: BacktestConfig, HistoricalDataBar, Trade, PerformanceMetrics, BacktestResult, Position, BacktestState
  - Evidence: All models use Decimal for money fields, UTC-only timestamps, full __post_init__ validation
  - Validation: Positive prices/capital, valid date ranges, commission/slippage [0,1], P&L calculations, chronological ordering
  - Committed: 5301396

✅ T013 [P]: Test for parquet caching written (RED phase - failing)
  - Evidence: pytest: 3/3 tests FAILED (expected - HistoricalDataManager not implemented)
  - Committed: 78c5384

✅ T010 [P]: Test for Alpaca data fetching written (RED phase - failing as expected)
  - Evidence: pytest: FAILED - ModuleNotFoundError: No module named 'src.trading_bot.backtest.historical_data_manager'
  - Committed: 5b473fa

✅ T012 [P]: Test for data validation written (RED phase - failing as expected)
  - Evidence: pytest: 7 FAILED - ModuleNotFoundError (HistoricalDataManager.validate_data not implemented)
  - Committed: f76fa14

✅ T016 [US1]: Implemented Alpaca historical data API integration with proper error handling and data transformation
  - Evidence: pytest: TestAlpacaFetch all 6 tests passing
  - Committed: 207ad34

✅ T020 [P]: Test for IStrategy protocol compliance written (RED phase)
  - Evidence: pytest: FAILED (ModuleNotFoundError - strategy_protocol module does not exist)
  - Committed: e24f924

✅ T021 [P]: Test for chronological execution written (RED phase)
  - Evidence: pytest: FAILED (ModuleNotFoundError - BacktestEngine not implemented)
  - Committed: b268119

✅ T024 [P]: Test for reproducibility written (TDD RED phase)
  - Evidence: pytest: FAILED (ModuleNotFoundError - BacktestEngine not implemented)
  - Committed: 25ca8fa

✅ T023 [P]: Test for insufficient capital validation written (TDD RED phase). Two tests added: test_insufficient_capital() and test_insufficient_capital_with_logging(). Both verify that BacktestEngine rejects trades when capital is too low.
  - Evidence: pytest: ModuleNotFoundError - src.trading_bot.backtest.engine doesn't exist yet (expected in RED phase)
  - Committed: 99e0a00

✅ T022 [P]: Test for buy-and-hold strategy written (TDD RED phase). Test fails with ModuleNotFoundError as expected because BacktestEngine.run() doesn't exist yet.
  - Evidence: pytest: FAILED - ImportError: ModuleNotFoundError: No module named 'src.trading_bot.backtest.engine'
  - Committed: d9548b9

✅ T025 [US2]: Implemented IStrategy protocol with runtime checking and updated Position model
  - Evidence: pytest: tests/backtest/test_strategy_protocol.py ALL PASSING (9/9 tests)
  - Committed: 600998b

✅ T026 [P]: Created BuyAndHoldStrategy and MomentumStrategy examples with full protocol compliance
  - Evidence: Examples created in examples/, protocol compliance verified via tests, all strategies implement IStrategy correctly
  - Committed: f2fb645

✅ T015 [US1]: HistoricalDataManager implemented with Alpaca/Yahoo sources and Parquet caching
  - Evidence: pytest: tests/backtest/test_historical_data_manager.py - 18/18 tests passing
  - Committed: f2fb645

