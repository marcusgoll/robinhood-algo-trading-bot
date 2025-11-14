# Implementation Plan: Momentum and Catalyst Detection

**Feature Slug**: 002-momentum-detection
**Created**: 2025-10-16
**Status**: Ready for implementation

---

## RESEARCH DECISIONS SUMMARY

See: `research.md` for full research findings

**Key Decisions**:
- News Provider: Alpaca Markets + Finnhub fallback (integrated, cost-effective)
- Pattern Detection: Manual daily candle analysis (no external library dependency)
- Time Zone: EST → UTC conversion (pre-market 4:00-9:30 AM EST logged as UTC)
- Signal Scoring: Linear weighted composite model (0-100 scale)

**Reusable Components**: 3 (MarketDataService, TradingLogger, @with_retry)
**New Components**: 4 (CatalystDetector, PreMarketScanner, BullFlagDetector, MomentumRanker)

---

## ARCHITECTURE DECISIONS

### Stack

- **Language**: Python 3.9+ (existing trading_bot codebase)
- **Framework**: FastAPI (existing routing infrastructure)
- **Scheduler**: APScheduler (periodic momentum scans)
- **Data Storage**: JSONL + PostgreSQL (optional Phase 2)
- **Market Data**: Alpaca API (existing MarketDataService with @with_retry)
- **Logging**: TradingLogger JSONL format (shared infrastructure)

### Design Patterns

**1. Service-Oriented Architecture**
- Three independent detector services (catalyst, pre-market, pattern)
- Each produces MomentumSignal objects
- Composition via MomentumRanker to combine signals
- Benefits: Testable independently, upgradeable separately

**2. Resilience**
- All API calls use @with_retry decorator (exponential backoff, circuit breaker)
- Graceful degradation on missing data (log gap, continue processing)
- No crashes on API failures

**3. Auditability**
- 100% of detected signals logged to JSONL
- Complete metadata preserved for backtesting
- UTC timestamps only (no timezone bugs)

**4. Composition Root**
```python
# api/src/trading_bot/momentum/__init__.py
class MomentumEngine:
    """Main entry point orchestrating all momentum detection"""
    def __init__(self, config: MomentumConfig):
        self.catalyst_detector = CatalystDetector(config)
        self.premarket_scanner = PreMarketScanner(config)
        self.bull_flag_detector = BullFlagDetector(config)
        self.ranker = MomentumRanker(config)

    async def scan(self, symbols: List[str]) -> List[MomentumSignal]:
        """Execute all detection methods and rank results"""
        tasks = [
            self.catalyst_detector.scan(symbols),
            self.premarket_scanner.scan(symbols),
            self.bull_flag_detector.scan(symbols),
        ]
        catalyst_signals, premarket_signals, pattern_signals = await asyncio.gather(*tasks)
        all_signals = catalyst_signals + premarket_signals + pattern_signals
        return self.ranker.rank(all_signals)
```

### Dependencies & Package Management

**New Dependencies** (to add to requirements.txt):
- None required for MVP (all core packages already available)

**Optional Future** (Phase 2+):
- `pandas`: For more efficient OHLCV manipulation
- `ta`: Technical analysis library (replaces manual pattern detection)
- `sqlalchemy`: For optional PostgreSQL integration

### Logging Strategy

**JSONL Structure** (src/trading_bot/logging/momentum_logger.py):
```json
{
  "timestamp": "2025-10-16T14:30:00Z",
  "event_type": "signal_detected|scan_started|scan_completed|error",
  "scan_id": "uuid",
  "symbol": "AAPL",
  "signal_type": "catalyst|premarket_mover|bull_flag",
  "signal_id": "uuid",
  "strength": 85.5,
  "metadata": { "...signal-specific data..." },
  "execution_time_ms": 245
}
```

**Files**:
- `logs/momentum/2025-10-16.jsonl` (rotated daily)
- Include in .gitignore (or archived separately for backtesting)

---

## PROJECT STRUCTURE

```
api/src/trading_bot/momentum/
├── __init__.py                    # MomentumEngine composition root
├── config.py                       # MomentumConfig dataclass (env vars)
├── catalyst_detector.py            # CatalystDetector service (US1)
├── premarket_scanner.py            # PreMarketScanner service (US2)
├── bull_flag_detector.py           # BullFlagDetector service (US3)
├── momentum_ranker.py              # MomentumRanker service (US4)
├── schemas/
│   ├── __init__.py
│   ├── momentum_signal.py          # MomentumSignal, CatalystEvent, etc. dataclasses
│   └── queries.py                  # MomentumQuery, ScanRequest dataclasses
├── logging/
│   ├── __init__.py
│   └── momentum_logger.py          # MomentumLogger (wrapper around TradingLogger)
└── routes/
    ├── __init__.py
    ├── signals.py                  # GET /api/v1/momentum/signals
    └── scan.py                     # POST /api/v1/momentum/scan

tests/unit/services/momentum/
├── test_catalyst_detector.py       # Unit tests for catalyst detection
├── test_premarket_scanner.py       # Unit tests for pre-market scanning
├── test_bull_flag_detector.py      # Unit tests for pattern detection
├── test_momentum_ranker.py         # Unit tests for signal ranking
└── conftest.py                     # Shared fixtures

tests/integration/momentum/
├── test_momentum_engine.py         # Integration test (mock API)
└── conftest.py                     # Integration fixtures

docs/
├── momentum-architecture.md        # Design decisions
├── momentum-api.md                 # API reference
└── momentum-examples.md            # Usage examples
```

---

## DATA MODEL

See: `data-model.md` for complete entity definitions

**Core Entities**:
- **MomentumSignal**: Detected trading opportunity (id, symbol, signal_type, strength, metadata, timestamp)
- **CatalystEvent**: News-driven catalyst (symbol, catalyst_type, headline, published_at, source)
- **PreMarketMover**: Pre-market activity tracking (symbol, price_change_pct, volume_ratio, timestamp)
- **BullFlagPattern**: Technical pattern data (symbol, pole_*, flag_*, breakout_price, price_target)

**Storage**:
- Primary: JSONL logs in `logs/momentum/YYYY-MM-DD.jsonl`
- Optional Phase 2: PostgreSQL tables with indexes on (symbol, signal_type, strength, timestamp)

**No Migrations Required**: MVP uses in-memory processing + JSONL logging

---

## PERFORMANCE TARGETS

**From spec.md NFRs**:
- NFR-001: Pre-market scan <60 seconds for 500 stocks
- NFR-002: Pattern detection <30 seconds for 100 stocks
- NFR-003: API resilience with exponential backoff (max 3 retries)

**Operational Targets**:
- Single symbol analysis: <100ms (catalyst only)
- Single symbol full scan: <500ms (catalyst + pre-market + pattern)
- Batch scan (100 stocks): <30 seconds (pattern detection is most expensive)
- Batch scan (500 stocks): <60 seconds (with parallel execution)

**Optimization Strategy**:
- Phase 1 (MVP): Sequential scans, caching disabled
- Phase 2: Add caching layer (per-symbol 5-minute TTL)
- Phase 3: Parallel async/await for independent detectors

---

## SECURITY

### Authentication Strategy

- **Method**: Inherit from existing trading_bot auth (Robinhood API key)
- **API Keys**: NEWS_API_KEY, MARKET_DATA_API_KEY stored in environment variables only
- **Protected Routes**: All `/api/v1/momentum/` endpoints require valid auth token
- **No New Auth Required**: MVP leverages existing OAuth/JWT infrastructure

### Authorization Model

- **RBAC**: User role from trading_bot auth (single trader MVP)
- **RLS** (Optional Phase 2): Row-level security for multi-user support
- **Scope**: All users can read own signal logs, no cross-user data access

### Input Validation

- **Request Schemas**: Pydantic models with strict validation
  - Symbol: Regex `^[A-Z]{1,5}$` (valid ticker format)
  - Price: Float >= 0
  - Volume: Integer >= 0
  - Dates: ISO 8601 UTC only

- **Rate Limiting**:
  - News API: Cache results (NewsAPI has 500 req/day free tier)
  - Market Data: Use batching and pagination
  - Scan endpoint: 10 req/min per user

- **CORS**: `localhost:3000` in dev, `*.vercel.app` in prod (from env vars)

### Data Protection

- **PII Handling**: No PII collected (only stock symbols, prices, public news)
- **Encryption**: API keys in environment variables (framework-managed)
- **JSONL Logs**: No sensitive data logged (no passwords, tokens, or account info)

### Credential Management

- **News API Key**: Via `NEWS_API_KEY` env var (Alpaca or Finnhub)
- **Market Data API**: Via `MARKET_DATA_API_KEY` (Alpaca)
- **Fallback**: Framework handles missing keys gracefully (skip that detector)

---

## EXISTING INFRASTRUCTURE - REUSE (3 components)

### 1. MarketDataService
**Location**: `src/trading_bot/services/market_data_service.py`
**Purpose**: Fetch quotes, OHLCV data, fundamentals from Alpaca

**Usage in Momentum**:
```python
# Pre-market scanner
quotes = await self.market_data.get_quotes(symbols, pre_market=True)
ohlcv = await self.market_data.get_historical_ohlcv(symbol, days=100)

# Pattern detection
historical_data = await self.market_data.get_ohlcv_range(symbol, start, end)
```

**Integration**: Direct method calls, already handles @with_retry internally

---

### 2. TradingLogger
**Location**: `src/trading_bot/logging/trading_logger.py`
**Purpose**: Structured JSONL logging with daily rotation

**Usage in Momentum**:
```python
logger = TradingLogger("momentum")
logger.log({
    "event_type": "signal_detected",
    "symbol": "AAPL",
    "signal_type": "bull_flag",
    "strength": 85.5,
    "execution_time_ms": 245
})
```

**Integration**: Instantiate in MomentumLogger wrapper class

---

### 3. @with_retry Decorator
**Location**: `src/trading_bot/utils/resilience.py`
**Purpose**: Exponential backoff, circuit breaker, max 3 retries

**Usage in Momentum**:
```python
from src.trading_bot.utils.resilience import with_retry

@with_retry(max_attempts=3, backoff_factor=2)
async def fetch_news(self, symbol: str) -> List[NewsItem]:
    # API call - will retry on failure
    return await self.news_api.search(symbol)
```

**Integration**: Decorate all external API calls (news API, market data if not already wrapped)

---

## NEW INFRASTRUCTURE - CREATE (4 components)

### 1. CatalystDetector (US1)
**File**: `api/src/trading_bot/momentum/catalyst_detector.py`
**Responsibility**: Fetch and categorize news catalysts

**Interface**:
```python
class CatalystDetector:
    async def scan(self, symbols: List[str]) -> List[MomentumSignal]:
        """Find news catalysts for given symbols (last 24h)"""
        # Returns MomentumSignal objects with signal_type="catalyst"

    async def categorize(self, headline: str) -> CatalystType:
        """Classify news into catalyst type"""
        # Enum: EARNINGS, FDA_APPROVAL, MERGER, PRODUCT_LAUNCH, etc.
```

**Dependencies**: Alpaca API, @with_retry, TradingLogger

---

### 2. PreMarketScanner (US2)
**File**: `api/src/trading_bot/momentum/premarket_scanner.py`
**Responsibility**: Monitor pre-market data 4:00-9:30 AM EST

**Interface**:
```python
class PreMarketScanner:
    async def scan(self, symbols: List[str]) -> List[MomentumSignal]:
        """Identify pre-market movers >5% change and >200% volume"""
        # Returns MomentumSignal objects with signal_type="premarket_mover"

    async def is_premarket_hours(self) -> bool:
        """Check if currently in pre-market window (EST timezone)"""
```

**Dependencies**: MarketDataService, @with_retry, TradingLogger, pytz (timezone handling)

---

### 3. BullFlagDetector (US3)
**File**: `api/src/trading_bot/momentum/bull_flag_detector.py`
**Responsibility**: Detect bull flag chart patterns

**Interface**:
```python
class BullFlagDetector:
    async def scan(self, symbols: List[str]) -> List[MomentumSignal]:
        """Find bull flag patterns in historical data"""
        # Returns MomentumSignal objects with signal_type="bull_flag"

    def _detect_pattern(self, ohlcv: List[Candle]) -> Optional[BullFlagPattern]:
        """Analyze candles for pole + flag formation"""
        # Internal method: detects pattern, validates thresholds
```

**Pattern Logic**:
- Pole: >8% gain in 1-3 consecutive days
- Flag: Price range 3-5% for 2-5 consecutive days
- Flag slope: Downward or flat (not upward)
- Result: breakout_price = top of flag range, price_target = pole height projected from breakout

**Dependencies**: MarketDataService (historical data), @with_retry, TradingLogger

---

### 4. MomentumRanker (US4)
**File**: `api/src/trading_bot/momentum/momentum_ranker.py`
**Responsibility**: Aggregate signals and compute composite scores

**Interface**:
```python
class MomentumRanker:
    def rank(self, signals: List[MomentumSignal]) -> List[MomentumSignal]:
        """Compute composite scores and sort by strength"""
        # Returns same signals with updated strength (composite score)

    def score_composite(self, catalyst_score: float, premarket_score: float, pattern_score: float) -> float:
        """Weighted average: catalyst 25%, pre-market 35%, pattern 40%"""
        # Weights tuned for swing trading (patterns stronger than news)
```

**Scoring Model**:
- Linear composite: `score = 0.25*catalyst + 0.35*premarket + 0.40*pattern`
- Each component normalized to 0-100
- Final score: 0-100 (rounded to 1 decimal)

**Dependencies**: TradingLogger

---

## CI/CD IMPACT

### Deployment Model

**Type**: `local-only` (no staging/production infrastructure)

**Implications**:
- Deploy to local trading bot environment only
- No Vercel/Railway infrastructure needed
- Manual deployment via `git pull + python -m trading_bot`

### Environment Variables

**New Required Variables** (update `.env.example`):
- `NEWS_API_KEY`: API key for news provider (NewsAPI, Finnhub, or Alpaca)
  - Staging/Dev: Use free tier API key (500 req/day)
  - Production: Use paid tier key if higher throughput needed
  - Fallback: Code continues if key missing (skips catalyst detection)

- `MARKET_DATA_API_KEY`: Alpaca API key (likely already defined)
  - Staging/Dev: Use sandbox key
  - Production: Use live key

**Changed Variables**: None

**Schema Update Required**: No (local-only deployment, no CI/CD schema needed)

### Build Commands

**No changes required**:
- Existing `python -m trading_bot` works as-is
- No new build steps or Docker changes
- Pure Python package addition

### Database Migrations

**Not required**:
- MVP uses in-memory processing + JSONL logging
- No schema changes to main database
- Optional Phase 2: Add PostgreSQL tables (separate migration)

### Dependencies

**No new external dependencies required**:
- All requirements already in `requirements.txt` (async, dataclasses, etc.)
- Optional future: `pandas`, `ta`, `sqlalchemy` (Phase 2+)

### Smoke Tests

**Optional for local deployment**:
- Manual: Call `/api/v1/momentum/signals` after bot starts
- Verify: Returns valid JSON with empty signals (no data yet)

```bash
# Dev test
curl -s http://localhost:8000/api/v1/momentum/signals | jq .

# Expected response:
# {"signals": [], "total": 0, "count": 0, "has_more": false}
```

### Platform Coupling

- **Local Python runtime**: No changes needed
- **Alpaca integration**: Already implemented in MarketDataService
- **APScheduler**: Already available in trading_bot dependencies
- **No new platform coupling**: Pure Python addition

---

## DEPLOYMENT ACCEPTANCE

### Production Invariants

- All momentum detection logic in `api/src/trading_bot/momentum/`
- All signals logged to JSONL in `logs/momentum/`
- All API keys from environment variables (never hardcoded)
- No database migrations or schema changes
- Backward compatible (new module only, no breaking changes)

### Rollback Plan

**Simple 3-command rollback**:
```bash
# 1. Revert commits
git revert <commit-sha>

# 2. Stop bot
pkill python

# 3. Start bot
python -m trading_bot
```

**Alternative**: Disable via feature flag
```python
# api/src/trading_bot/__init__.py
if os.getenv("ENABLE_MOMENTUM_DETECTION") != "true":
    # Skip momentum engine initialization
```

### Build Artifacts

**Type**: Source code only (no Docker/binary artifacts)
- All changes in source tree
- Deploy via `git pull` on local machine
- Commit SHAs tracked in NOTES.md

---

## INTEGRATION SCENARIOS

See: `quickstart.md` for complete integration scenarios

**Scenario 1: Initial Setup**
```bash
# Install dependencies
pip install -r requirements.txt

# Verify market data works
python -c "from trading_bot.services import MarketDataService; print('✅ OK')"

# Run tests
pytest tests/unit/services/momentum/ -v

# Start bot
python -m trading_bot
```

**Scenario 2: Manual Testing**
```python
# Test catalyst detector
from trading_bot.momentum import CatalystDetector
catalyst = CatalystDetector()
signals = await catalyst.scan(["AAPL", "GOOGL"])
print(f"Found {len(signals)} catalysts")

# Test pattern detector
from trading_bot.momentum import BullFlagDetector
patterns = await patterns.scan(["AAPL"])
print(f"Found {len(patterns)} bull flags")
```

**Scenario 3: Query API**
```python
import requests

# Get all signals from last 24 hours
response = requests.get(
    "http://localhost:8000/api/v1/momentum/signals",
    params={"min_strength": 70}
)
print(response.json())

# Trigger a new scan
response = requests.post(
    "http://localhost:8000/api/v1/momentum/scan",
    json={
        "symbols": ["AAPL", "GOOGL", "TSLA"],
        "scan_types": ["catalyst", "premarket", "bull_flag"]
    }
)
print(f"Scan started: {response.json()['scan_id']}")
```

---

## RISK ASSESSMENT

### Low Risk ✅

- **Pure Python addition**: No breaking changes to existing codebase
- **Reuses proven patterns**: MarketDataService, TradingLogger, @with_retry already battle-tested
- **No database changes**: MVP uses JSONL logging (can always add DB later)
- **Independent module**: Can be disabled/removed without affecting bot core

### Medium Risk ⚠️

- **API dependency**: Requires news API access (may hit rate limits)
- **Market data accuracy**: Relies on Alpaca pre-market data quality
- **Pattern detection tuning**: Bull flag thresholds (8%, 3-5%, etc.) may need adjustment

### Mitigation Strategies

- Add caching to reduce API calls (Phase 2)
- Implement circuit breaker for API failures (@with_retry already handles)
- Backtesting framework to validate pattern thresholds (Phase 3)
- Comprehensive unit tests (90% coverage target)

---

## SUMMARY TABLE

| Category | Decision | Status |
|----------|----------|--------|
| **Stack** | Python 3.9+, FastAPI, APScheduler | Ready ✅ |
| **Storage** | JSONL logs + optional PostgreSQL | Ready ✅ |
| **Market Data** | Alpaca API via MarketDataService | Ready ✅ |
| **Logging** | TradingLogger JSONL format | Ready ✅ |
| **Resilience** | @with_retry decorator | Ready ✅ |
| **Reuse** | 3 components identified | Ready ✅ |
| **New Code** | 4 detector services | Planned |
| **Tests** | 90% coverage target | Planned |
| **Database** | None for MVP | Planned Phase 2 |
| **Deployment** | Local-only, git-based | Ready ✅ |

---

## NEXT STEPS

1. **Run `/tasks`** to break down into concrete implementation tasks (T001-TXX)
2. **Run `/analyze`** to validate cross-artifact consistency
3. **Run `/implement`** to execute development with TDD approach
4. **Run `/optimize`** for code review and production readiness
5. **Run `/preview`** for manual testing and acceptance
6. **Deploy locally** when ready for production use

