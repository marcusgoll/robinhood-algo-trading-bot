# Research & Discovery: level-2-order-flow-i

## Research Decisions

### Decision: Polygon.io API for Level 2 and Time & Sales Data
- **Decision**: Use Polygon.io API ($99/month starter plan) for both Level 2 order book and Time & Sales data
- **Rationale**: Robinhood API confirmed NOT to support Level 2/Time & Sales data. Polygon.io provides professional-grade market data with good documentation, retail accessibility, and bundles both data types in single subscription
- **Alternatives**:
  - Alpaca Markets API (Level 2 requires premium tier >$99/month)
  - IEX Cloud (Limited Level 2 depth, higher costs for full order book)
  - TD Ameritrade API (Requires brokerage account, complex authentication)
- **Source**: spec.md clarifications (Q1-Q2), Polygon.io pricing documentation

### Decision: Detector Pattern Architecture
- **Decision**: Follow existing detector pattern (CatalystDetector, BullFlagDetector) for OrderFlowDetector
- **Rationale**: Existing codebase has proven pattern for real-time scanning with alerts. Provides structured JSONL logging, graceful degradation, retry logic, and Constitution compliance built-in
- **Alternatives**:
  - Event-driven streaming architecture (over-engineered for MVP)
  - Polling-based service (inconsistent latency, higher resource usage)
  - WebSocket integration (added complexity, Polygon.io REST API sufficient for 2s latency target)
- **Source**: src/trading_bot/momentum/catalyst_detector.py:29-478, spec.md NFR-001 (2s latency target)

### Decision: Monitor Active Positions Only
- **Decision**: Order flow monitoring active ONLY for symbols with active positions (not continuous watchlist)
- **Rationale**: Reduces API costs (Polygon.io charges per request), aligns with defensive risk management strategy (exits over entries), simplifies implementation
- **Alternatives**:
  - Watchlist monitoring for entry signals (higher costs, deferred to P2 enhancement)
  - Full market scanning (prohibitively expensive, out of scope)
- **Source**: spec.md clarification Q3, FR-013

### Decision: Configuration via Dataclass + Environment Variables
- **Decision**: Use frozen dataclass pattern with from_env() class method, following MomentumConfig pattern
- **Rationale**: Existing codebase standard. Provides validation, immutability, environment variable loading, and sensible defaults
- **Alternatives**:
  - JSON config file (less flexible, requires file management)
  - YAML config (additional dependency, overkill for simple config)
  - Direct env var access (no validation, error-prone)
- **Source**: src/trading_bot/momentum/config.py:16-102

### Decision: File-Based JSONL Logging (No Database)
- **Decision**: Use structured JSONL logs in logs/order_flow/*.jsonl, no database schema
- **Rationale**: Constitution §Audit_Everything requires logging. File-based approach simpler for MVP, avoids database migration complexity, sufficient for measurement queries
- **Alternatives**:
  - PostgreSQL table (over-engineered for alert logging)
  - SQLite (unnecessary persistence layer for stateless monitoring)
  - In-memory only (loses audit trail, violates Constitution)
- **Source**: spec.md deployment considerations (no database schema), Constitution §Audit_Everything

### Decision: Python 3.11+ Type Hints with Dataclasses
- **Decision**: Use dataclasses for data models (OrderFlowAlert, OrderBookSnapshot, TimeAndSalesRecord, OrderFlowConfig) with full type hints
- **Rationale**: Constitution §Code_Quality requires type hints. Dataclasses provide automatic __init__, __repr__, immutability (frozen=True), and validation
- **Alternatives**:
  - Pydantic models (additional dependency, overkill for internal data models)
  - NamedTuples (less flexible, no validation)
  - Plain classes (verbose, error-prone)
- **Source**: Constitution §Code_Quality, src/trading_bot/market_data/data_models.py:24-25 (Quote dataclass pattern)

---

## Components to Reuse (5 found)

- **src/trading_bot/market_data/market_data_service.py**: MarketDataService class with @with_retry decorator, validation patterns, logging integration, and _determine_market_state() method
- **src/trading_bot/error_handling/retry.py**: @with_retry decorator with exponential backoff, jitter, rate limit detection (HTTP 429), and retry callbacks
- **src/trading_bot/error_handling/policies.py**: DEFAULT_POLICY (3 retries, 1s/2s/4s delays), RetryPolicy dataclass for custom retry behavior
- **src/trading_bot/logger.py**: TradingLogger.get_logger() for structured JSONL logging with UTC timestamps
- **src/trading_bot/momentum/config.py**: Config pattern with frozen dataclass, from_env() class method, __post_init__ validation

---

## New Components Needed (6 required)

- **src/trading_bot/order_flow/order_flow_detector.py**: OrderFlowDetector class - Analyzes Level 2 order book for large seller alerts (>10k shares at bid), calculates alert severity, publishes alerts
- **src/trading_bot/order_flow/tape_monitor.py**: TapeMonitor class - Tracks Time & Sales data, calculates 5-minute rolling average volume, detects red burst patterns (>300% volume spike with >60% sells)
- **src/trading_bot/order_flow/config.py**: OrderFlowConfig dataclass - Configuration with thresholds (large_order_size, volume_spike_threshold, red_burst_threshold, alert_window_seconds, data_source)
- **src/trading_bot/order_flow/validators.py**: Validation functions - validate_level2_data() (timestamp freshness, price bounds), validate_tape_data() (chronological sequence, price within spread)
- **src/trading_bot/order_flow/data_models.py**: Data models - OrderFlowAlert, OrderBookSnapshot, TimeAndSalesRecord dataclasses with type hints
- **src/trading_bot/order_flow/polygon_client.py**: PolygonClient class - Wrapper for Polygon.io API with authentication, Level 2 order book fetching, Time & Sales fetching, error handling

---

## Unknowns & Questions

None - all technical questions resolved via clarification phase (spec.md Session 2025-10-22)
