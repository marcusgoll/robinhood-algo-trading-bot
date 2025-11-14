# Research & Discovery: 023-support-resistance-mapping

## Research Decisions

### Decision: Reuse MarketDataService for OHLCV data

- **Decision**: Use existing `MarketDataService` for fetching historical price data
- **Rationale**: Already implements §Data_Integrity validation, retry logic, and UTC timestamp handling. No need to duplicate API integration logic.
- **Alternatives**: Direct robin_stocks calls (rejected - duplicates validation logic), pandas_datareader (rejected - different data source)
- **Source**: `src/trading_bot/market_data/market_data_service.py:1-100`

### Decision: Follow detector service pattern from BullFlagDetector

- **Decision**: Implement `SupportResistanceDetector` following same architecture as `BullFlagDetector`
- **Rationale**: Establishes pattern consistency - both analyze historical data to identify trading signals. Reuses config pattern, logging integration, and validation approach.
- **Alternatives**: Standalone module (rejected - inconsistent with momentum services), integrated into BullFlagDetector (rejected - violates single responsibility)
- **Source**: `src/trading_bot/momentum/bull_flag_detector.py:1-100`

### Decision: Structured JSONL logging via StructuredTradeLogger pattern

- **Decision**: Create dedicated zone logger following `StructuredTradeLogger` architecture
- **Rationale**: Proven thread-safe pattern with daily rotation, <5ms write latency, matches §Audit_Everything requirement
- **Alternatives**: Standard Python logging (rejected - not structured), database storage (rejected - overkill for MVP, adds deployment complexity)
- **Source**: `src/trading_bot/logging/structured_logger.py`

### Decision: Python Decimal for all price calculations

- **Decision**: Use `decimal.Decimal` for zone price levels, proximity calculations, and strength scoring
- **Rationale**: Constitution §Code_Quality + NFR-003 mandates avoiding floating-point errors in financial calculations. Pattern already established across backtest and account modules.
- **Alternatives**: Float (rejected - violates NFR-003), NumPy float64 (rejected - precision loss at extreme values)
- **Source**: Existing usage in `src/trading_bot/backtest/models.py`, `src/trading_bot/account/account_data.py`

### Decision: No UI components - backend/algorithm feature

- **Decision**: Pure Python service implementation, no FastAPI/web layer for MVP
- **Rationale**: Spec indicates backend-only feature. Zone data consumed by bot logic, not exposed via API. Keeps deployment simple (local-only, no staging/production).
- **Alternatives**: REST API endpoints (rejected - adds unnecessary complexity for MVP), dashboard integration (deferred to P3)
- **Source**: spec.md Deployment Considerations section

---

## Components to Reuse (5 found)

- `src/trading_bot/market_data/market_data_service.py`: OHLCV data fetching with validation
- `src/trading_bot/momentum/bull_flag_detector.py`: Service architecture pattern (scan method, config, logging)
- `src/trading_bot/logging/structured_logger.py`: Thread-safe JSONL logging pattern
- `src/trading_bot/momentum/config.py` (MomentumConfig): Configuration pattern for service parameters
- `src/trading_bot/error_handling/retry.py`: Retry decorator for API resilience

---

## New Components Needed (3 required)

- `src/trading_bot/support_resistance/zone_detector.py`: Core detection service (zone identification, strength scoring, proximity alerts)
- `src/trading_bot/support_resistance/models.py`: Zone dataclass, ZoneTouch dataclass, ProximityAlert dataclass
- `src/trading_bot/support_resistance/zone_logger.py`: Structured logger for zone events (extends StructuredTradeLogger pattern)

---

## Unknowns & Questions

None - all technical questions resolved through codebase research.
