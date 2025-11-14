# Implementation Plan: Enhanced Trade Logging

## [RESEARCH DECISIONS]

### Decision: Build on Existing Logging Framework
- **Decision**: Extend existing TradingLogger class with structured JSON logging capability
- **Rationale**: Maintains backwards compatibility, reuses proven UTC timestamp handling, integrates with existing audit trail
- **Alternatives**: Create separate logging system (rejected - would duplicate infrastructure and break existing integrations)
- **Source**: src/trading_bot/logger.py (lines 1-89)

### Decision: Dual Logging Strategy
- **Decision**: Maintain human-readable text logs + add machine-readable JSON logs
- **Rationale**: Text logs required for §Audit_Everything compliance and human review; JSON logs enable Claude Code-measurable analytics via grep/jq
- **Alternatives**: JSON-only (rejected - harder for human audit); Text-only (rejected - not queryable)
- **Source**: Constitution v1.0.0 §Audit_Everything, spec.md NFR-001

### Decision: File-Based Storage (v1)
- **Decision**: Use .jsonl (JSON Lines) files for structured trade data storage
- **Rationale**: No database dependency, version-controllable, grep/jq queryable, simple deployment
- **Alternatives**: PostgreSQL (rejected - adds infrastructure complexity); SQLite (rejected - not as grep-friendly)
- **Source**: spec.md NFR-006 (Claude Code-measurable requirement)

### Decision: Incremental Enhancement Pattern
- **Decision**: Add new TradeRecord dataclass and StructuredTradeLogger without modifying existing TradingBot.execute_trade()
- **Rationale**: Non-breaking change, existing code continues to work, new functionality opt-in via configuration
- **Alternatives**: Replace existing logging (rejected - breaking change); Separate module (rejected - duplicates infrastructure)
- **Source**: Constitution v1.0.0 §Code_Quality (backwards compatibility)

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Backend: Python 3.11+ (existing)
- Logging: Built-in logging module + json module (stdlib only, no new dependencies)
- Storage: JSONL files in logs/trades/ directory
- Analytics: grep/jq/Python scripts (Claude Code-measurable)
- Testing: pytest with fixtures for log validation

**Patterns**:
- **Dataclass-based Records**: TradeRecord dataclass for type-safe trade data modeling
- **Dual-Stream Logging**: Parallel text + JSON logging to separate files/handlers
- **Decorator Pattern**: @log_structured_trade decorator for automatic trade capture
- **Builder Pattern**: TradeRecordBuilder for flexible record construction
- **Repository Pattern**: TradeQueryHelper for encapsulated query logic

**Dependencies** (new packages required):
- None (stdlib only - json, logging, dataclasses, pathlib, datetime)

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── logging/
│   ├── __init__.py
│   ├── trade_record.py          # TradeRecord dataclass
│   ├── structured_logger.py      # StructuredTradeLogger class
│   └── query_helper.py           # TradeQueryHelper for analytics
├── logger.py                     # Existing TradingLogger (unchanged)
└── bot.py                        # TradingBot (minimal integration)

logs/
├── trading_bot.log              # Existing general logs
├── trades.log                    # Existing human-readable trade log
└── trades/                       # NEW: Structured trade logs
    ├── 2025-01-09.jsonl         # Daily JSONL files
    ├── 2025-01-10.jsonl
    └── ...

tests/
└── unit/
    ├── test_trade_record.py
    ├── test_structured_logger.py
    └── test_query_helper.py
```

**Module Organization**:
- **trade_record.py**: TradeRecord dataclass, TradeOutcome enum, validation logic
- **structured_logger.py**: StructuredTradeLogger class, JSON formatting, file rotation
- **query_helper.py**: TradeQueryHelper class with query methods (by date, symbol, outcome, strategy)
- **bot.py integration**: Call structured_logger.log_trade() from existing log_trade() hook

---

## [SCHEMA]

**Trade Record Schema** (TradeRecord dataclass):

```python
@dataclass
class TradeRecord:
    """Structured trade execution record (FR-001)."""

    # Core Trade Data (FR-002)
    timestamp: str              # ISO 8601 UTC (e.g., "2025-01-09T14:32:15.123Z")
    symbol: str                 # Stock ticker (e.g., "AAPL")
    action: str                 # "BUY" | "SELL"
    quantity: int               # Number of shares
    price: Decimal              # Execution price
    total_value: Decimal        # quantity * price

    # Execution Context (FR-003)
    order_id: str               # Unique order identifier
    execution_mode: str         # "PAPER" | "LIVE"
    account_id: Optional[str]   # Robinhood account ID (if live)

    # Strategy Metadata (FR-004)
    strategy_name: str          # "bull-flag-breakout" | "manual" | etc.
    entry_type: str             # "breakout" | "pullback" | "reversal" | etc.
    stop_loss: Optional[Decimal]  # Stop loss price (if set)
    target: Optional[Decimal]    # Profit target price (if set)

    # Decision Audit Trail (FR-005, §Audit_Everything)
    decision_reasoning: str     # Why this trade was taken
    indicators_used: list[str]  # ["VWAP", "EMA-9", "MACD"] etc.
    risk_reward_ratio: Optional[float]  # Planned R:R (e.g., 2.0 for 2:1)

    # Outcome Tracking (FR-006)
    outcome: Optional[str]      # "win" | "loss" | "breakeven" | "open"
    profit_loss: Optional[Decimal]  # Realized P&L (if closed)
    hold_duration_seconds: Optional[int]  # Time in trade
    exit_timestamp: Optional[str]  # When position closed (ISO 8601 UTC)
    exit_reasoning: Optional[str]   # Why position was exited

    # Performance Metrics (FR-007)
    slippage: Optional[Decimal]     # Difference from expected price
    commission: Optional[Decimal]   # Trading fees
    net_profit_loss: Optional[Decimal]  # P&L - commission

    # Compliance & Audit (NFR-002, §Audit_Everything)
    session_id: str             # Links to trading session
    bot_version: str            # Software version for reproducibility
    config_hash: str            # Hash of config at trade time

    def to_json(self) -> dict:
        """Serialize to JSON-safe dict."""
        return {k: str(v) if isinstance(v, Decimal) else v
                for k, v in asdict(self).items()}

    def to_jsonl_line(self) -> str:
        """Serialize to JSONL format (one line, no pretty print)."""
        return json.dumps(self.to_json(), separators=(',', ':'))
```

**JSONL File Format** (logs/trades/YYYY-MM-DD.jsonl):
```jsonl
{"timestamp":"2025-01-09T14:32:15.123Z","symbol":"AAPL","action":"BUY","quantity":100,"price":"150.50","total_value":"15050.00","order_id":"ORD123","execution_mode":"PAPER","account_id":null,"strategy_name":"bull-flag-breakout","entry_type":"breakout","stop_loss":"148.00","target":"156.00","decision_reasoning":"Bull flag breakout above $150 resistance with volume confirmation","indicators_used":["VWAP","EMA-9","Volume"],"risk_reward_ratio":2.2,"outcome":"open","profit_loss":null,"hold_duration_seconds":null,"exit_timestamp":null,"exit_reasoning":null,"slippage":"0.02","commission":"0.00","net_profit_loss":null,"session_id":"SES-20250109-001","bot_version":"1.0.0","config_hash":"abc123"}
{"timestamp":"2025-01-09T14:45:30.456Z","symbol":"AAPL","action":"SELL","quantity":100,"price":"152.75","total_value":"15275.00","order_id":"ORD124","execution_mode":"PAPER","account_id":null,"strategy_name":"bull-flag-breakout","entry_type":"breakout","stop_loss":"148.00","target":"156.00","decision_reasoning":"Target reached at $152.75 (partial profit taking)","indicators_used":["VWAP","EMA-9"],"risk_reward_ratio":2.2,"outcome":"win","profit_loss":"225.00","hold_duration_seconds":795,"exit_timestamp":"2025-01-09T14:45:30.456Z","exit_reasoning":"Target hit, price stalling at resistance","slippage":"0.03","commission":"0.00","net_profit_loss":"225.00","session_id":"SES-20250109-001","bot_version":"1.0.0","config_hash":"abc123"}
```

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-003: Log write latency <5ms (non-blocking I/O)
- NFR-004: File rotation completes <50ms
- NFR-005: Query performance <500ms for 1000 trades
- NFR-006: Disk space <1MB per 100 trades (compact JSON)

**Query Performance Targets** (grep/jq on JSONL):
- Daily summary: `grep "2025-01-09" | jq -s 'map(.profit_loss | tonumber) | add'` <500ms
- Win rate: `jq -s 'map(select(.outcome=="win")) | length'` <500ms
- Symbol filter: `grep '"symbol":"AAPL"'` <100ms

---

## [SECURITY]

**Data Protection**:
- PII handling: No PII in trade logs (account_id optional, hashed if present)
- File permissions: logs/trades/ directory 700 (owner-only access)
- Sensitive data: Decision reasoning scrubbed of credentials/tokens

**Input Validation**:
- Symbol: Uppercase 1-5 chars, alphanumeric only
- Quantity: Positive integer, max 10,000 shares
- Price: Positive Decimal, max 2 decimal places
- Timestamps: ISO 8601 UTC format validation

**Audit Trail** (§Audit_Everything):
- Every trade logged with complete decision context
- Config hash for reproducibility
- Session ID for correlation
- Bot version for debugging

---

## [EXISTING INFRASTRUCTURE - REUSE] (3 components)

**Services/Modules**:
- `src/trading_bot/logger.py`: TradingLogger class (base framework, UTC timestamps)
- `src/trading_bot/bot.py`: TradingBot.log_trade() hook (integration point)

**Utilities**:
- `logging.UTCFormatter`: UTC timestamp formatting (reuse for JSON logs)

---

## [NEW INFRASTRUCTURE - CREATE] (3 components)

**Backend**:
- `src/trading_bot/logging/trade_record.py`: TradeRecord dataclass, validation, serialization
- `src/trading_bot/logging/structured_logger.py`: StructuredTradeLogger class, JSONL file handling, rotation
- `src/trading_bot/logging/query_helper.py`: TradeQueryHelper with analytics methods

**Testing**:
- `tests/unit/test_trade_record.py`: TradeRecord validation, serialization tests
- `tests/unit/test_structured_logger.py`: Logging, rotation, file handling tests
- `tests/unit/test_query_helper.py`: Query methods, performance tests

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Local Python bot (no web platform)
- Env vars: None (file-based configuration)
- Breaking changes: No (backwards compatible enhancement)
- Migration: No (new feature, no schema changes)

**Build Commands**:
- No changes (Python module import)

**Environment Variables**:
- No new variables required

**Database Migrations**:
- N/A (file-based storage)

**Smoke Tests**:
- Test: Create TradeRecord, log to JSONL, query back
- Expected: Record retrieved with all fields intact
- Script: tests/smoke/test_trade_logging_smoke.py

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants**:
- Existing text logging continues to work unchanged
- No breaking changes to TradingBot.execute_trade() signature
- JSONL files created only if directory exists (graceful degradation)
- All timestamps in UTC (§Data_Integrity)

**Local Smoke Tests** (Given/When/Then):
```gherkin
Given bot executes a paper trade
When trade completes
Then structured log appears in logs/trades/YYYY-MM-DD.jsonl
  And text log appears in logs/trades.log (unchanged)
  And grep query returns correct trade data
  And jq query calculates correct P&L
```

**Rollback Plan**:
- Remove structured logging imports from bot.py
- Existing text logging continues unchanged
- No data loss (JSONL files preserved for manual review)

---

## [INTEGRATION SCENARIOS]

**From quickstart perspective:**

### Scenario 1: Initial Setup
```bash
# No additional setup required (stdlib only)
# Ensure logs directory exists
mkdir -p logs/trades

# Verify permissions
chmod 700 logs/trades
```

### Scenario 2: Validation
```bash
# Run tests
pytest tests/unit/test_trade_record.py -v
pytest tests/unit/test_structured_logger.py -v
pytest tests/unit/test_query_helper.py -v

# Check types
mypy src/trading_bot/logging/

# Lint
ruff check src/trading_bot/logging/
```

### Scenario 3: Manual Testing
```bash
# Execute a test trade (paper mode)
python -c "
from src.trading_bot.bot import TradingBot
from src.trading_bot.config import Config

config = Config.from_env_and_json()
bot = TradingBot(config)
bot.execute_trade('AAPL', 'BUY', 100, 150.50)
"

# Verify structured log created
ls -lh logs/trades/$(date +%Y-%m-%d).jsonl

# Query with jq
jq -s '.' logs/trades/$(date +%Y-%m-%d).jsonl

# Calculate daily P&L
jq -s 'map(.profit_loss | tonumber) | add' logs/trades/$(date +%Y-%m-%d).jsonl
```

### Scenario 4: Analytics Queries
```bash
# Win rate for today
jq -s 'map(select(.outcome=="win")) | length' logs/trades/$(date +%Y-%m-%d).jsonl

# Average hold duration
jq -s 'map(.hold_duration_seconds | tonumber) | add / length' logs/trades/$(date +%Y-%m-%d).jsonl

# Total P&L by symbol
jq -s 'group_by(.symbol) | map({symbol: .[0].symbol, total_pl: map(.profit_loss | tonumber) | add})' logs/trades/*.jsonl

# Strategy performance comparison
jq -s 'group_by(.strategy_name) | map({strategy: .[0].strategy_name, win_rate: (map(select(.outcome=="win")) | length) / length})' logs/trades/*.jsonl
```
