# Tasks: Enhanced Trade Logging

## [CODEBASE REUSE ANALYSIS]

Scanned: src/trading_bot/**/*.py

**[EXISTING - REUSE]**
- TradingLogger (src/trading_bot/logger.py) - base logging framework, UTC timestamps
- UTCFormatter (src/trading_bot/logger.py) - UTC timestamp formatting
- TradingBot.log_trade() (src/trading_bot/bot.py) - integration hook

**[NEW - CREATE]**
- TradeRecord dataclass (no existing structured trade model)
- StructuredTradeLogger (no existing JSON logging)
- TradeQueryHelper (no existing analytics interface)

---

## Phase 3.0: Setup & Infrastructure

T001 [P] Create logging package structure
- **Files**: src/trading_bot/logging/__init__.py
- **Exports**: TradeRecord, StructuredTradeLogger, TradeQueryHelper
- **Pattern**: src/trading_bot/ (existing package structure)
- **From**: plan.md [STRUCTURE] section

T002 [P] Create logs/trades directory with correct permissions
- **Command**: mkdir -p logs/trades && chmod 700 logs/trades
- **Validation**: Directory exists and is owner-only (700)
- **Pattern**: logs/ directory (existing log storage)
- **From**: plan.md [SECURITY] section

T003 [P] Add test fixtures for trade data
- **File**: tests/fixtures/trade_fixtures.py
- **Fixtures**: sample_buy_trade, sample_sell_trade, sample_trade_sequence
- **Pattern**: tests/fixtures/ (existing test fixtures)
- **From**: plan.md [SCHEMA] TradeRecord structure

---

## Phase 3.1: RED - Write Failing Tests (Core Data Model)

T004 [RED] Write test: TradeRecord validates required fields
- **File**: tests/unit/test_trade_record.py
- **Test**: test_trade_record_requires_core_fields()
- **Assert**: Missing timestamp/symbol/action/quantity/price raises TypeError
- **Pattern**: tests/unit/test_config.py (validation tests)
- **From**: plan.md [SCHEMA] TradeRecord dataclass

T005 [RED] Write test: TradeRecord validates symbol format
- **File**: tests/unit/test_trade_record.py
- **Test**: test_trade_record_validates_symbol_format()
- **Assert**: Invalid symbols (lowercase, >5 chars, special chars) raise ValueError
- **Pattern**: tests/unit/test_trading_bot.py (input validation)
- **From**: plan.md [SECURITY] Input Validation

T006 [RED] Write test: TradeRecord validates numeric constraints
- **File**: tests/unit/test_trade_record.py
- **Test**: test_trade_record_validates_numeric_constraints()
- **Assert**: Negative quantity/price raises ValueError, quantity >10000 raises ValueError
- **Pattern**: tests/unit/test_config.py (constraint validation)
- **From**: plan.md [SECURITY] Input Validation

T007 [RED] Write test: TradeRecord serializes to JSON correctly
- **File**: tests/unit/test_trade_record.py
- **Test**: test_trade_record_to_json_handles_decimals()
- **Assert**: Decimal fields serialized as strings, dict has all 30+ fields
- **Pattern**: tests/unit/ (serialization tests)
- **From**: plan.md [SCHEMA] to_json() method

T008 [RED] Write test: TradeRecord serializes to JSONL format
- **File**: tests/unit/test_trade_record.py
- **Test**: test_trade_record_to_jsonl_is_single_line()
- **Assert**: Output is single line, no whitespace, parseable by jq
- **Pattern**: tests/unit/ (serialization tests)
- **From**: plan.md [SCHEMA] to_jsonl_line() method

---

## Phase 3.2: GREEN - Implement Core Data Model

T009 [GREEN->T004] Implement TradeRecord dataclass with required fields
- **File**: src/trading_bot/logging/trade_record.py
- **Fields**: timestamp, symbol, action, quantity, price, total_value (core 6 fields)
- **Fields**: order_id, execution_mode, account_id (execution 3 fields)
- **Fields**: strategy_name, entry_type, stop_loss, target (strategy 4 fields)
- **Fields**: decision_reasoning, indicators_used, risk_reward_ratio (decision 3 fields)
- **Fields**: outcome, profit_loss, hold_duration_seconds, exit_timestamp, exit_reasoning (outcome 5 fields)
- **Fields**: slippage, commission, net_profit_loss (performance 3 fields)
- **Fields**: session_id, bot_version, config_hash (audit 3 fields)
- **Total**: 27 fields as per plan.md [SCHEMA]
- **Pattern**: Use @dataclass decorator, Optional[] for nullable fields
- **From**: plan.md [SCHEMA] TradeRecord dataclass

T010 [GREEN->T005] Add symbol validation to TradeRecord
- **File**: src/trading_bot/logging/trade_record.py
- **Method**: __post_init__() with symbol validation
- **Logic**: Uppercase only, 1-5 chars, alphanumeric only, raise ValueError
- **Pattern**: Config validation in src/trading_bot/config.py
- **From**: plan.md [SECURITY] Input Validation

T011 [GREEN->T006] Add numeric constraint validation
- **File**: src/trading_bot/logging/trade_record.py
- **Method**: __post_init__() with quantity/price validation
- **Logic**: quantity > 0, quantity <= 10000, price > 0, raise ValueError
- **Pattern**: Config validation in src/trading_bot/config.py
- **From**: plan.md [SECURITY] Input Validation

T012 [GREEN->T007] Implement to_json() method
- **File**: src/trading_bot/logging/trade_record.py
- **Method**: to_json() -> dict
- **Logic**: asdict() + convert Decimal to str, handle None values
- **Pattern**: JSON serialization in existing codebase
- **From**: plan.md [SCHEMA] to_json() method

T013 [GREEN->T008] Implement to_jsonl_line() method
- **File**: src/trading_bot/logging/trade_record.py
- **Method**: to_jsonl_line() -> str
- **Logic**: json.dumps(self.to_json(), separators=(',', ':'))
- **Pattern**: Compact JSON formatting
- **From**: plan.md [SCHEMA] to_jsonl_line() method

---

## Phase 3.3: RED - Write Failing Tests (Structured Logger)

T014 [RED] Write test: StructuredTradeLogger creates daily JSONL files
- **File**: tests/unit/test_structured_logger.py
- **Test**: test_logger_creates_daily_jsonl_file()
- **Assert**: File created at logs/trades/YYYY-MM-DD.jsonl
- **Pattern**: tests/unit/test_logger.py (file handling tests)
- **From**: plan.md [STRUCTURE] Directory Layout

T015 [RED] Write test: StructuredTradeLogger appends records without overwriting
- **File**: tests/unit/test_structured_logger.py
- **Test**: test_logger_appends_to_existing_file()
- **Assert**: Multiple log_trade() calls append, not overwrite
- **Pattern**: tests/unit/test_logger.py (append tests)
- **From**: plan.md FR-001 (all trades logged)

T016 [RED] Write test: StructuredTradeLogger handles concurrent writes safely
- **File**: tests/unit/test_structured_logger.py
- **Test**: test_logger_handles_concurrent_writes()
- **Assert**: 10 threads writing simultaneously, no data corruption
- **Pattern**: tests/unit/ (concurrency tests)
- **From**: plan.md NFR-003 (non-blocking I/O)

T017 [RED] Write test: StructuredTradeLogger write latency <5ms
- **File**: tests/unit/test_structured_logger.py
- **Test**: test_logger_write_performance()
- **Assert**: log_trade() completes in <5ms (average over 100 calls)
- **Pattern**: tests/unit/ (performance tests)
- **From**: plan.md [PERFORMANCE TARGETS] NFR-003

---

## Phase 3.4: GREEN - Implement Structured Logger

T018 [GREEN->T014] Implement StructuredTradeLogger class with file creation
- **File**: src/trading_bot/logging/structured_logger.py
- **Class**: StructuredTradeLogger(logs_dir: Path)
- **Method**: _get_daily_file_path() -> Path (returns logs/trades/YYYY-MM-DD.jsonl)
- **Method**: log_trade(record: TradeRecord) -> None
- **Pattern**: TradingLogger in src/trading_bot/logger.py (file handling)
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE]

T019 [GREEN->T015] Add append-mode file writing
- **File**: src/trading_bot/logging/structured_logger.py
- **Method**: log_trade() implementation
- **Logic**: Open file in 'a' mode, write record.to_jsonl_line() + '\n'
- **Pattern**: Append mode in existing logger
- **From**: plan.md FR-001 (append all trades)

T020 [GREEN->T016] Add file locking for concurrent writes
- **File**: src/trading_bot/logging/structured_logger.py
- **Import**: import fcntl (POSIX) or msvcrt (Windows)
- **Method**: log_trade() with file lock
- **Logic**: Acquire exclusive lock, write, release lock
- **Pattern**: File locking patterns in stdlib
- **From**: plan.md NFR-003 (non-blocking I/O)

T021 [GREEN->T017] Optimize write performance with buffering
- **File**: src/trading_bot/logging/structured_logger.py
- **Method**: log_trade() with buffered I/O
- **Logic**: Use buffering=8192 in open(), flush after write
- **Pattern**: Performance optimization patterns
- **From**: plan.md [PERFORMANCE TARGETS] NFR-003

---

## Phase 3.5: RED - Write Failing Tests (Query Helper)

T022 [RED] Write test: TradeQueryHelper queries by date range
- **File**: tests/unit/test_query_helper.py
- **Test**: test_query_by_date_range()
- **Assert**: Query returns only trades between start_date and end_date
- **Pattern**: tests/unit/ (query tests)
- **From**: plan.md FR-006 (query capabilities)

T023 [RED] Write test: TradeQueryHelper queries by symbol
- **File**: tests/unit/test_query_helper.py
- **Test**: test_query_by_symbol()
- **Assert**: Query returns only trades for specified symbol (e.g., "AAPL")
- **Pattern**: tests/unit/ (filter tests)
- **From**: plan.md [INTEGRATION SCENARIOS] Analytics Queries

T024 [RED] Write test: TradeQueryHelper calculates win rate
- **File**: tests/unit/test_query_helper.py
- **Test**: test_calculate_win_rate()
- **Assert**: Win rate = (wins / total_closed_trades) * 100
- **Pattern**: tests/unit/ (calculation tests)
- **From**: plan.md FR-007 (performance metrics)

T025 [RED] Write test: TradeQueryHelper query performance <500ms for 1000 trades
- **File**: tests/unit/test_query_helper.py
- **Test**: test_query_performance_at_scale()
- **Assert**: Query 1000-trade JSONL file in <500ms
- **Pattern**: tests/unit/ (performance tests)
- **From**: plan.md [PERFORMANCE TARGETS] NFR-005

---

## Phase 3.6: GREEN - Implement Query Helper

T026 [GREEN->T022] Implement TradeQueryHelper.query_by_date_range()
- **File**: src/trading_bot/logging/query_helper.py
- **Class**: TradeQueryHelper(logs_dir: Path)
- **Method**: query_by_date_range(start: str, end: str) -> list[TradeRecord]
- **Logic**: Read JSONL files for date range, parse JSON, filter by timestamp
- **Pattern**: File reading patterns in existing codebase
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE]

T027 [GREEN->T023] Implement TradeQueryHelper.query_by_symbol()
- **File**: src/trading_bot/logging/query_helper.py
- **Method**: query_by_symbol(symbol: str, start_date: str = None) -> list[TradeRecord]
- **Logic**: grep-like filter on symbol field in JSONL
- **Pattern**: Filter patterns in existing code
- **From**: plan.md [INTEGRATION SCENARIOS] Analytics Queries

T028 [GREEN->T024] Implement TradeQueryHelper.calculate_win_rate()
- **File**: src/trading_bot/logging/query_helper.py
- **Method**: calculate_win_rate(trades: list[TradeRecord]) -> float
- **Logic**: wins = filter(outcome="win"), total = filter(outcome in ["win","loss","breakeven"]), return wins/total
- **Pattern**: Calculation helpers in existing code
- **From**: plan.md FR-007 (performance metrics)

T029 [GREEN->T025] Optimize query performance with streaming
- **File**: src/trading_bot/logging/query_helper.py
- **Method**: _read_jsonl_stream() generator
- **Logic**: Yield one line at a time, no full file read
- **Pattern**: Generator patterns for large files
- **From**: plan.md [PERFORMANCE TARGETS] NFR-005

---

## Phase 3.7: Integration & Testing

T030 [P] Integrate StructuredTradeLogger into TradingBot.log_trade()
- **File**: src/trading_bot/bot.py
- **Import**: from trading_bot.logging import StructuredTradeLogger, TradeRecord
- **Init**: self.structured_logger = StructuredTradeLogger(Path("logs"))
- **Hook**: In log_trade(), call structured_logger.log_trade(record)
- **REUSE**: Existing log_trade() hook (line ~215)
- **Pattern**: Existing TradingLogger integration
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE]

T031 [RED] Write integration test: Full trade execution logs to JSONL
- **File**: tests/integration/test_trade_logging_integration.py
- **Test**: test_trade_execution_creates_structured_log()
- **Given**: TradingBot initialized with config
- **When**: bot.execute_trade('AAPL', 'BUY', 100, 150.50)
- **Then**: JSONL record exists in logs/trades/YYYY-MM-DD.jsonl with correct data
- **Pattern**: tests/integration/ (end-to-end tests)
- **From**: plan.md [DEPLOYMENT ACCEPTANCE] smoke tests

T032 [GREEN->T031] Ensure execute_trade() creates TradeRecord with all fields
- **File**: src/trading_bot/bot.py
- **Method**: execute_trade() implementation
- **Logic**: Build TradeRecord from trade params + context (strategy, session_id, etc.)
- **REUSE**: Existing execute_trade() parameters
- **Pattern**: Data model construction in existing code
- **From**: plan.md [SCHEMA] TradeRecord fields

T033 [RED] Write integration test: Backwards compatibility with text logs
- **File**: tests/integration/test_trade_logging_integration.py
- **Test**: test_text_logging_still_works()
- **Given**: TradingBot initialized
- **When**: bot.execute_trade() called
- **Then**: Both logs/trades.log (text) AND logs/trades/YYYY-MM-DD.jsonl (JSON) created
- **Pattern**: tests/integration/ (compatibility tests)
- **From**: plan.md [DEPLOYMENT ACCEPTANCE] production invariants

T034 [GREEN->T033] Ensure dual logging (text + JSON) works in parallel
- **File**: src/trading_bot/bot.py
- **Method**: log_trade() implementation
- **Logic**: Call existing text logger + new structured logger
- **REUSE**: TradingLogger.log_trade() (existing)
- **Pattern**: Dual-stream logging pattern
- **From**: plan.md [RESEARCH DECISIONS] Dual Logging Strategy

---

## Phase 3.8: Error Handling & Resilience

T035 [RED] Write test: StructuredTradeLogger gracefully handles missing directory
- **File**: tests/unit/test_structured_logger.py
- **Test**: test_logger_handles_missing_directory()
- **Assert**: If logs/trades/ missing, log_trade() creates it or fails gracefully
- **Pattern**: tests/unit/ (error handling tests)
- **From**: plan.md [DEPLOYMENT ACCEPTANCE] graceful degradation

T036 [GREEN->T035] Add directory creation to StructuredTradeLogger
- **File**: src/trading_bot/logging/structured_logger.py
- **Method**: __init__() implementation
- **Logic**: logs_dir.mkdir(parents=True, exist_ok=True)
- **Pattern**: Directory creation in existing logger
- **From**: plan.md [DEPLOYMENT ACCEPTANCE] graceful degradation

T037 [RED] Write test: StructuredTradeLogger handles disk full error
- **File**: tests/unit/test_structured_logger.py
- **Test**: test_logger_handles_disk_full()
- **Assert**: OSError caught, logged, doesn't crash bot
- **Pattern**: tests/unit/ (error handling tests)
- **From**: plan.md NFR-003 (non-blocking I/O)

T038 [GREEN->T037] Add error handling with fallback logging
- **File**: src/trading_bot/logging/structured_logger.py
- **Method**: log_trade() with try/except
- **Logic**: Catch OSError, log to stderr, continue execution
- **Pattern**: Error handling in existing logger
- **From**: plan.md NFR-003 (non-blocking I/O)

---

## Phase 3.9: Documentation & Polish

T039 [P] Add docstrings to all public methods
- **Files**: trade_record.py, structured_logger.py, query_helper.py
- **Format**: Google-style docstrings with Args, Returns, Raises
- **Examples**: Include usage examples in module docstrings
- **Pattern**: Existing docstrings in src/trading_bot/
- **From**: Constitution v1.0.0 Code Quality

T040 [P] Create smoke test script
- **File**: tests/smoke/test_trade_logging_smoke.py
- **Test**: test_end_to_end_trade_logging_workflow()
- **Steps**: Create trade -> Log -> Query -> Validate
- **Expected**: <90s execution time
- **Pattern**: tests/smoke/ (smoke tests)
- **From**: plan.md [CI/CD IMPACT] smoke tests

T041 [P] Update NOTES.md with implementation summary
- **File**: specs/trade-logging/NOTES.md
- **Section**: Phase 3 Implementation Complete
- **Content**: Task completion summary, test results, performance metrics
- **Pattern**: NOTES.md updates in other features
- **From**: Workflow standard practice

---

## Task Summary

**Total**: 41 tasks
- Setup: 3 tasks (T001-T003)
- TDD Cycles: 32 tasks (T004-T036, 8 RED-GREEN-REFACTOR trios)
- Integration: 5 tasks (T030-T034)
- Polish: 3 tasks (T039-T041)

**TDD Breakdown**:
- RED (failing tests): 14 tasks
- GREEN (minimal implementation): 14 tasks
- REFACTOR: 4 tasks
- Parallel: 6 tasks

**Dependencies**:
- T009-T013 must complete before T030 (TradeRecord required for integration)
- T018-T021 must complete before T030 (StructuredTradeLogger required)
- T030 must complete before T031-T034 (integration requires bot changes)

**Estimated Completion**: 8-12 hours (serial), 4-6 hours (with parallelization)
