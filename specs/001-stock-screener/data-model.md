# Data Model: Stock Screener

## Entities

### ScreenerQuery (Request Contract)
**Purpose**: Encapsulates all filter parameters for a screener request; validated at entry point

**Fields**:
- `min_price`: Decimal | None - Minimum bid price (e.g., 2.00)
- `max_price`: Decimal | None - Maximum bid price (e.g., 20.00)
- `relative_volume`: float | None - Volume multiplier vs 100-day avg (e.g., 5.0 = 5x average)
- `float_max`: int | None - Maximum public float in millions (e.g., 20 = under 20M shares)
- `min_daily_change`: float | None - Minimum daily % move (e.g., 10.0 = ±10%)
- `limit`: int = 500 - Results per page
- `offset`: int = 0 - Pagination offset
- `query_id`: str (UUID) - For audit trail correlation

**Validation Rules**:
- `min_price` and `max_price` (if both set): min_price < max_price (FR-002, FR-011)
- `relative_volume` (if set): > 1.0 (1x minimum doesn't filter)
- `float_max` (if set): > 0 (positive integer)
- `min_daily_change` (if set): >= 0 (absolute value, can be 0)
- `limit`: 1-500 (max 500 per page per FR-012)
- `offset`: >= 0

**Default Behaviors**:
- All filter parameters optional (None = skip that filter, apply others)
- Filters combined with AND logic (all must pass)
- Results sorted by volume descending

**State Transitions** (immutable):
- Created → Validated → Logged → Executed

---

### StockScreenerMatch (Result Item)
**Purpose**: Single stock that matched screener filters

**Fields**:
- `symbol`: str - Stock ticker (e.g., "TSLA")
- `bid_price`: Decimal - Current bid price (from MarketDataService.Quote.bid)
- `volume`: int - Current session volume (shares traded)
- `volume_avg_100d`: int | None - 100-day average volume (None if unavailable, e.g., IPO)
- `float_shares`: int | None - Public float in shares (None if unavailable)
- `daily_open`: Decimal - Day's opening price
- `daily_close`: Decimal - Current price (for daily change calc)
- `daily_change_pct`: float - Daily change percent (abs value)
- `daily_change_direction`: str - "up" or "down"
- `matched_filters`: list[str] - Filters this stock passed (e.g., ["price_range", "volume_spike", "daily_movers"])
- `data_gaps`: list[str] - Fields unavailable (e.g., ["float"] if skipped during float filter)
- `timestamp`: datetime - Quote timestamp (UTC)

**Relationships**:
- Belongs to: ScreenerResult (one result contains many matches)
- Sourced from: MarketDataService.Quote + AccountData (stock context)

**Validation Rules**:
- `symbol`: Uppercase alphanumeric, 1-5 chars (stock ticker format)
- `bid_price`: Decimal(10, 2), > 0
- `volume`: int >= 0
- `float_shares`: int | None, if not None then > 0
- `daily_change_pct`: float, 0-1000 (allows extreme movers, capped at 1000%)

---

### ScreenerResult (Response Contract)
**Purpose**: Complete screener query result with metadata

**Fields**:
- `query_id`: str (UUID) - Matches ScreenerQuery.query_id for audit trail
- `stocks`: list[StockScreenerMatch] - Matched stocks (0-500 per page)
- `query_timestamp`: datetime - When query was executed (UTC)
- `query_params_echo`: ScreenerQuery - Echo back filters applied (for audit)
- `result_count`: int - Number of stocks in this page
- `total_count`: int - Total matches across all pages (before pagination)
- `execution_time_ms`: float - Query execution time (for perf monitoring)
- `page_info`: PageInfo - Pagination metadata
- `errors`: list[str] - Data gaps encountered (e.g., ["3 stocks missing float data"])
- `api_calls_made`: int - Total MarketDataService calls (for cost tracking)
- `cache_hit`: bool - Whether result was cached (Future: for P2 caching)

**Relationships**:
- Contains: 0-500 StockScreenerMatch items
- References: ScreenerQuery (echo for audit)

**Validation Rules**:
- `result_count`: 0 <= result_count <= limit
- `total_count`: >= result_count (always true, except on empty result)
- `execution_time_ms`: > 0, typically < 500ms per NFR-001

**State Invariants**:
- If result_count == 0: stocks = [], errors = [] (no matches possible)
- If total_count == 0: No pagination needed (has_more = false)
- execution_time_ms should be < 500ms (95th percentile per NFR-001)

---

### PageInfo
**Purpose**: Pagination metadata for large result sets

**Fields**:
- `offset`: int - Current offset in results
- `limit`: int - Page size (1-500)
- `has_more`: bool - True if total_count > offset + limit
- `next_offset`: int | None - Suggested offset for next page (or None if has_more=false)
- `page_number`: int - 1-indexed current page

**Calculations**:
- `has_more` = (total_count > offset + limit)
- `next_offset` = offset + limit (if has_more, else None)
- `page_number` = floor(offset / limit) + 1

**Example**:
- offset=0, limit=500, total_count=1250
  - has_more: true
  - next_offset: 500
  - page_number: 1
- offset=500, limit=500, total_count=1250
  - has_more: true
  - next_offset: 1000
  - page_number: 2
- offset=1000, limit=500, total_count=1250
  - has_more: false
  - next_offset: None
  - page_number: 3

---

### ScreenerQueryLog (Audit Record)
**Purpose**: JSONL audit trail for all screener operations

**Fields** (JSONL format):
- `timestamp`: datetime (ISO 8601, UTC, Z suffix)
- `event`: str - Event type ("screener.query_submitted", "screener.query_completed", "screener.error")
- `query_id`: str (UUID) - Trace across related events
- `session_id`: str (UUID) - Trading bot session ID
- `query_params`: dict - Filter parameters (min_price, max_price, etc.)
- `result_count`: int - Number of matches
- `total_count`: int - Total matches across all pages
- `execution_time_ms`: float - Query latency
- `api_calls`: int - Market data API calls made
- `data_gaps`: list[str] - Missing data encountered
- `error`: str | None - Error message if failed
- `retry_count`: int - If error, how many retries attempted
- `user_id`: str | None - Trader identifier (future: multi-user support)
- `filters_active`: list[str] - Which filters were applied

**Location**: `logs/screener/YYYY-MM-DD.jsonl`

**Example Entry**:
```json
{
  "timestamp": "2025-10-16T14:32:15.234Z",
  "event": "screener.query_completed",
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "query_params": {
    "min_price": 2.0,
    "max_price": 20.0,
    "relative_volume": 5.0,
    "float_max": 20,
    "min_daily_change": null,
    "limit": 500,
    "offset": 0
  },
  "result_count": 42,
  "total_count": 42,
  "execution_time_ms": 187.5,
  "api_calls": 3,
  "data_gaps": ["AKTR: float unavailable"],
  "error": null,
  "retry_count": 0,
  "user_id": null,
  "filters_active": ["price_range", "relative_volume", "float_size"]
}
```

---

## Database Schema (In-Memory MVP)

**MVP Note**: No database tables for initial release. All processing in-memory.

**Future Enhancement** (P2): Optional tables for caching + analytics:

```sql
-- Optional: Cache screener results for 60-second TTL
CREATE TABLE screener_results_cache (
    id UUID PRIMARY KEY,
    query_hash VARCHAR(64) UNIQUE NOT NULL,  -- Hash of query params for lookup
    result_json JSONB NOT NULL,              -- Cached ScreenerResult
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,           -- TTL expiry
    hits INT DEFAULT 0                       -- Cache hit counter
);

-- Optional: Query audit trail (for analytics)
CREATE TABLE screener_queries_log (
    id UUID PRIMARY KEY,
    query_id UUID NOT NULL,
    session_id UUID NOT NULL,
    query_params JSONB NOT NULL,
    result_count INT NOT NULL,
    total_count INT NOT NULL,
    execution_time_ms FLOAT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

---

## API Schemas

### Request Schema (OpenAPI 3.0)

```yaml
ScreenerQuery:
  type: object
  properties:
    min_price:
      type: number
      format: decimal
      nullable: true
      example: 2.0
    max_price:
      type: number
      format: decimal
      nullable: true
      example: 20.0
    relative_volume:
      type: number
      format: float
      nullable: true
      example: 5.0
    float_max:
      type: integer
      nullable: true
      example: 20
    min_daily_change:
      type: number
      format: float
      nullable: true
      example: 10.0
    limit:
      type: integer
      minimum: 1
      maximum: 500
      default: 500
    offset:
      type: integer
      minimum: 0
      default: 0
```

### Response Schema (OpenAPI 3.0)

```yaml
ScreenerResult:
  type: object
  required:
    - query_id
    - stocks
    - query_timestamp
    - result_count
    - total_count
    - execution_time_ms
    - page_info
    - errors
  properties:
    query_id:
      type: string
      format: uuid
    stocks:
      type: array
      items:
        $ref: '#/components/schemas/StockScreenerMatch'
      minItems: 0
      maxItems: 500
    query_timestamp:
      type: string
      format: date-time
    result_count:
      type: integer
      minimum: 0
    total_count:
      type: integer
      minimum: 0
    execution_time_ms:
      type: number
      format: float
      minimum: 0
    page_info:
      $ref: '#/components/schemas/PageInfo'
    errors:
      type: array
      items:
        type: string

StockScreenerMatch:
  type: object
  required:
    - symbol
    - bid_price
    - volume
    - daily_open
    - daily_close
    - daily_change_pct
    - matched_filters
  properties:
    symbol:
      type: string
      pattern: '^[A-Z]{1,5}$'
    bid_price:
      type: number
      format: decimal
    volume:
      type: integer
      minimum: 0
    volume_avg_100d:
      type: integer
      nullable: true
    float_shares:
      type: integer
      nullable: true
    daily_open:
      type: number
      format: decimal
    daily_close:
      type: number
      format: decimal
    daily_change_pct:
      type: number
      format: float
    daily_change_direction:
      type: string
      enum: ['up', 'down']
    matched_filters:
      type: array
      items:
        type: string
    data_gaps:
      type: array
      items:
        type: string
    timestamp:
      type: string
      format: date-time
```

---

## State Shape (Python)

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
import uuid

@dataclass
class ScreenerQuery:
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    relative_volume: Optional[float] = None
    float_max: Optional[int] = None
    min_daily_change: Optional[float] = None
    limit: int = 500
    offset: int = 0
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        if self.min_price and self.max_price and self.min_price >= self.max_price:
            raise ValueError("min_price must be < max_price")
        if self.limit < 1 or self.limit > 500:
            raise ValueError("limit must be 1-500")
        if self.offset < 0:
            raise ValueError("offset must be >= 0")

@dataclass
class StockScreenerMatch:
    symbol: str
    bid_price: Decimal
    volume: int
    daily_open: Decimal
    daily_close: Decimal
    daily_change_pct: float
    matched_filters: List[str]
    volume_avg_100d: Optional[int] = None
    float_shares: Optional[int] = None
    daily_change_direction: str = field(default="")
    data_gaps: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class PageInfo:
    offset: int
    limit: int
    has_more: bool
    next_offset: Optional[int] = None
    page_number: int = 1

@dataclass
class ScreenerResult:
    query_id: str
    stocks: List[StockScreenerMatch]
    query_timestamp: datetime
    query_params_echo: ScreenerQuery
    result_count: int
    total_count: int
    execution_time_ms: float
    page_info: PageInfo
    errors: List[str] = field(default_factory=list)
    api_calls_made: int = 0
    cache_hit: bool = False
```

---

## Summary

- **Entities**: 5 core classes (ScreenerQuery, StockScreenerMatch, ScreenerResult, PageInfo, ScreenerQueryLog)
- **Relationships**: Linear (Query → Result contains Matches)
- **Migrations**: None for MVP (in-memory only)
- **Validation**: Pydantic dataclasses with @post_init__ checks
- **Audit Trail**: JSONL logging via ScreenerLogger (logs/screener/YYYY-MM-DD.jsonl)
- **Pagination**: Offset-based, 500 max per page, has_more flag
