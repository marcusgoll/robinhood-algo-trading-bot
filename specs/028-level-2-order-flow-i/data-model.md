# Data Model: level-2-order-flow-i

## Entities

### OrderFlowAlert
**Purpose**: Represents a detected order flow alert (large seller or red burst pattern)

**Fields**:
- `symbol`: str - Stock ticker symbol (e.g., "AAPL", "TSLA")
- `alert_type`: Literal["large_seller", "red_burst"] - Type of alert detected
- `severity`: Literal["warning", "critical"] - Alert severity level
- `order_size`: int | None - Size of large order in shares (None for red_burst)
- `price_level`: Decimal | None - Price level of large order (None for red_burst)
- `volume_ratio`: float | None - Volume spike ratio (e.g., 3.5 = 350% of average, None for large_seller)
- `timestamp_utc`: datetime - When alert was detected (UTC timezone)

**Relationships**:
- Published to: Risk management module (for exit signal evaluation)
- Logged to: logs/order_flow/{date}.jsonl

**Validation Rules**:
- `symbol`: Non-empty string, uppercase (from requirement FR-003, FR-007)
- `order_size`: >0 if alert_type="large_seller" (from requirement FR-002)
- `volume_ratio`: >=3.0 if alert_type="red_burst" (from requirement FR-006)
- `timestamp_utc`: Must be timezone-aware UTC (Constitution §Data_Integrity)

**State Transitions**: N/A (immutable alert record)

---

### OrderBookSnapshot
**Purpose**: Level 2 order book snapshot with bid/ask depth

**Fields**:
- `symbol`: str - Stock ticker symbol
- `bids`: list[tuple[Decimal, int]] - List of (price, size) bid orders, sorted by price descending
- `asks`: list[tuple[Decimal, int]] - List of (price, size) ask orders, sorted by price ascending
- `timestamp_utc`: datetime - Snapshot timestamp from API (UTC)

**Relationships**:
- Consumed by: OrderFlowDetector.detect_large_sellers()
- Source: Polygon.io Level 2 API

**Validation Rules**:
- `bids`: Each price >$0, each size >0 shares (from requirement FR-010)
- `asks`: Each price >$0, each size >0 shares (from requirement FR-010)
- `timestamp_utc`: Freshness <10 seconds (fail if >30 seconds old) (from requirement FR-010)
- `bids` sorted descending, `asks` sorted ascending (data integrity)

**State Transitions**: N/A (snapshot data, no state)

---

### TimeAndSalesRecord
**Purpose**: Individual tick from Time & Sales tape (executed trade)

**Fields**:
- `symbol`: str - Stock ticker symbol
- `price`: Decimal - Trade execution price
- `size`: int - Trade size in shares
- `side`: Literal["buy", "sell"] - Trade side (buyer-initiated or seller-initiated)
- `timestamp_utc`: datetime - Trade execution timestamp (UTC)

**Relationships**:
- Consumed by: TapeMonitor.analyze_volume_spike()
- Source: Polygon.io Time & Sales API

**Validation Rules**:
- `price`: >$0 (from requirement FR-011)
- `size`: >0 shares (from requirement FR-011)
- `timestamp_utc`: Chronological sequence (later ticks must have later timestamps) (from requirement FR-011)
- `side`: Must be "buy" or "sell" (data integrity)

**State Transitions**: N/A (immutable trade record)

---

### OrderFlowConfig
**Purpose**: Configuration dataclass for order flow detection thresholds

**Fields**:
- `large_order_size_threshold`: int - Minimum order size for large seller alert (default: 10000 shares)
- `volume_spike_threshold`: float - Minimum volume ratio for red burst detection (default: 3.0x)
- `red_burst_threshold`: float - Critical volume spike threshold for exit signal (default: 4.0x)
- `alert_window_seconds`: int - Time window for consecutive alert detection (default: 120 seconds)
- `data_source`: str - Data provider ("polygon" only for MVP)
- `polygon_api_key`: str - API key for Polygon.io (required)
- `monitoring_mode`: Literal["positions_only", "watchlist"] - Monitoring scope (default: "positions_only")

**Relationships**:
- Loaded by: OrderFlowDetector, TapeMonitor
- Source: Environment variables (ORDER_FLOW_*)

**Validation Rules**:
- `large_order_size_threshold`: >=1000 shares (from requirement FR-002, spec US4)
- `volume_spike_threshold`: 1.5-10.0x (from spec US4)
- `red_burst_threshold`: >=volume_spike_threshold (logic constraint)
- `alert_window_seconds`: 30-300 seconds (from spec US4)
- `data_source`: Must be "polygon" (from clarification decision)
- `polygon_api_key`: Non-empty string if data_source="polygon"
- `monitoring_mode`: Must be "positions_only" or "watchlist" (from clarification Q3)

**State Transitions**: N/A (immutable configuration)

---

## Database Schema (Mermaid)

N/A - This feature uses file-based JSONL logging, no database schema required.

**Rationale**: Order flow alerts are stateless events logged for audit and measurement. No persistent storage, relationships, or queries needed beyond log analysis.

---

## API Schemas

**Request/Response Schemas**: N/A - Internal Python module, no REST API exposure

**State Shape** (internal Python):
```python
# OrderFlowDetector state (in-memory only)
class OrderFlowDetector:
    alert_history: deque[OrderFlowAlert]  # Last N alerts (bounded queue)
    last_check_timestamp: datetime | None  # For rate limiting API calls

# TapeMonitor state (in-memory only)
class TapeMonitor:
    tape_buffer: deque[TimeAndSalesRecord]  # Rolling 5-minute window
    volume_history: deque[float]  # 5-minute rolling averages
```

**External API Contracts**: See contracts/polygon-api.yaml for Polygon.io API integration
