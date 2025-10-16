# Feature: Stock Screener

## Overview

Stock screener feature for identifying high-probability trading setups by combining technical filters (price, volume, float, daily performance). Addresses roadmap item with score 1.33 (Impact 5, Confidence 0.8, Effort 3).

## Research Findings

### Market Data Module Availability
- ✅ Shipped: market-data-module (v1.0.0) provides real-time quotes, historical data, market hours detection
- ✅ Available: MarketDataService.get_quote(symbol) for bid/ask/volume
- ✅ Available: MarketDataService.get_historical_ohlcv() for 100-day average volume baseline
- ✅ Blocked dependencies: None (market-data-module is shipped and stable)

### Similar Patterns in Codebase
- ✅ Pattern: SafetyChecks module demonstrates multi-criteria validation (buying power, hours, circuit breaker)
- ✅ Pattern: AccountData module shows data aggregation + caching approach (TTL-based)
- ✅ Pattern: TradingLogger shows JSONL audit trail for all trading decisions
- Decision: No new patterns needed; reuse existing safety-check validation and logger patterns

### Reusable Components
- ✅ MarketDataService: Core quote fetching with @with_retry resilience
- ✅ TradingLogger: Structured JSONL logging for all screener queries + results
- ✅ @with_retry decorator: Automatic exponential backoff for Robinhood API rate limiting
- ✅ error-handling-framework: Exception hierarchy (RetriableError, RateLimitError) ready to use
- Decision: No new utilities needed; screener will delegate API calls to MarketDataService

### Performance Targets
- From design/systems/budgets.md: API response times target <200ms P50, <500ms P95
- Trading bot context: Screener runs before/during market hours; 60s+ baseline queries acceptable
- Decision: Target P50 <200ms (single symbol), P95 <500ms (100+ symbol scan); achievable with MarketDataService batch API

### Constitution Compliance Check
- ✅ §Safety_First: Screener is tool-only (identifies candidates); no trades executed; paper-trading compatible
- ✅ §Code_Quality: Type hints enforced (100% coverage target); KISS principle (simple filters, no ML/ML complexity)
- ✅ §Risk_Management: Screener is passive (no position changes); traders apply own risk rules to results
- ✅ §Testing_Requirements: 90% test coverage target; backtesting possible (historical filter simulation)
- ✅ §Audit_Everything: All screener queries logged to JSONL with params, results, latency

## Feature Classification

- **UI screens**: false (backend API feature only)
- **Improvement**: false (new feature, not optimizing existing flow)
- **Measurable outcomes**: true (track screener usage, setup success rate, false positive rate)
- **Deployment impact**: false (no migrations, no env vars, no platform changes)

## System Components Analysis

**Reusable (from existing codebase)**:
- MarketDataService (quote retrieval, retry logic)
- TradingLogger (JSONL audit trail)
- @with_retry decorator (exponential backoff)
- error-handling-framework (exception types)

**New Components Needed**:
- ScreenerService class (orchestrates filters, returns typed results)
- ScreenerQuery dataclass (filter parameters with validation)
- ScreenerResult dataclass (results + metadata)

**Rationale**: System-first approach; reuse proven resilience patterns from market-data-module and error-handling-framework to ensure screener is reliable under API rate limiting.

## Deployment Model

Project type: `local-only` (no remote staging/production deployment)

Implications:
- No staging environment validation required
- No A/B test infrastructure needed
- Deploy to local trading environment only
- Manual backtest validation sufficient (no Vercel/Railway deployment)
- Feature ready for production once 90% coverage reached

---

## Checkpoints

- Phase 0 (Specification): 2025-10-16 ✅ Draft spec complete
  - Requirements validated against Constitution v1.0.0 (all sections passed)
  - No ambiguities marked (clear requirements, informed defaults for edge cases)
  - Quality gates checked (requirements testable, Constitution aligned, no tech leakage)

- Phase 1 (Planning): [Pending]
  - Architecture design (ScreenerService structure)
  - Component breakdown (filters, query validation, result pagination)
  - Reuse decisions (MarketDataService, TradingLogger integration)

- Phase 2 (Tasks): [Pending]
  - Task breakdown (20-30 TDD tasks)
  - User story mapping (P1 to T001-T015, P2 to T016-T020, P3 to T021+)
  - Dependencies documented

- Phase 3 (Analysis): [Pending]
  - Cross-artifact consistency check
  - Risk identification + mitigation
  - Critical path analysis

- Phase 4 (Implementation): [Pending]
  - TDD task execution (all 90%+ coverage)
  - Integration with MarketDataService
  - JSONL logging verification

- Phase 5 (Optimization): [Pending]
  - Code review (senior review: KISS/DRY compliance)
  - Performance profiling (latency, memory)
  - Security audit (API key handling, input validation)

## Last Updated

2025-10-16T15:32:00Z (Specification phase complete)
