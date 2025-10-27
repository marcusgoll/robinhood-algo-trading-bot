# API Strategy

**Last Updated**: 2025-10-26
**Related Docs**: See `system-architecture.md` for API architecture, `tech-stack.md` for framework choice

## API Style

**Choice**: REST over HTTPS
**Rationale**:
- Simple, universally understood
- Good for CRUD operations (bot status, trades, commands)
- HTTP caching works out of box
- Easy to test (curl, Postman)
- LLM-friendly (Claude/GPT can easily call REST APIs)
- No need for GraphQL complexity (no deep nesting, over-fetching not a problem)

---

## API Categories

### Category: Bot Status & Monitoring

**Purpose**: Query bot state, positions, performance
**Base Path**: `/api/v1/status`
**Authentication**: Required (Bearer token)
**Authorization**: Single user (no multi-user support)

**Endpoints**:

- `GET /api/v1/status` - Get bot status
  - Response: `{ status: "trading" | "paused" | "stopped", uptime_seconds: number, circuit_breaker_tripped: boolean }`
  - Use case: Health check, dashboard

- `GET /api/v1/positions` - List open positions
  - Response: `{ positions: [{ symbol, quantity, entry_price, current_price, unrealized_pnl, stop_loss, target }] }`
  - Use case: Monitor open trades

- `GET /api/v1/performance` - Performance metrics
  - Query params: `?window=20` (rolling window size)
  - Response: `{ win_rate, profit_factor, max_drawdown, consecutive_losses, total_trades }`
  - Use case: LLM analysis, dashboard

---

### Category: Trade History

**Purpose**: Query historical trades
**Base Path**: `/api/v1/trades`
**Authentication**: Required

**Endpoints**:

- `GET /api/v1/trades` - List trades
  - Query params: `?limit=100&offset=0&symbol=AAPL&start_date=2025-10-01`
  - Response: `{ data: Trade[], total: number, has_more: boolean }`
  - Use case: Retrieve trade log for analysis

- `GET /api/v1/trades/{order_id}` - Get trade details
  - Response: Full TradeRecord (27 fields)
  - Use case: Detailed inspection of specific trade

---

### Category: Bot Commands

**Purpose**: Send commands to bot (pause, resume, close position)
**Base Path**: `/api/v1/commands`
**Authentication**: Required

**Endpoints**:

- `POST /api/v1/commands/pause` - Pause trading
  - Body: `{ reason: "manual intervention" }`
  - Response: `{ success: true, message: "Trading paused" }`
  - Use case: Emergency stop

- `POST /api/v1/commands/resume` - Resume trading
  - Body: `{}`
  - Response: `{ success: true, message: "Trading resumed" }`
  - Use case: Resume after manual pause

- `POST /api/v1/commands/close-position` - Close position manually
  - Body: `{ symbol: "AAPL", reason: "manual exit" }`
  - Response: `{ success: true, order_id: "xyz" }`
  - Use case: Manual override

---

### Category: LLM Analysis

**Purpose**: LLM-powered pattern analysis and insights
**Base Path**: `/api/v1/analysis`
**Authentication**: Required

**Endpoints**:

- `POST /api/v1/analysis/pattern` - Analyze chart pattern
  - Body: `{ symbol: "AAPL", timeframe: "1h", bars: 50 }`
  - Response: `{ pattern: "bull-flag", confidence: 0.85, reasoning: "...", entry_price: 150.25, stop_loss: 148.50, target: 155.00 }`
  - Use case: LLM validation of pattern before entry
  - Cache: 1-hour TTL in Redis

- `POST /api/v1/analysis/trade-review` - Review trade outcome
  - Body: `{ order_id: "abc-123" }`
  - Response: `{ analysis: "...", lessons_learned: "...", improvement_suggestions: [...] }`
  - Use case: Post-trade learning

---

## Versioning Strategy

**Approach**: URL-based (`/api/v1/`, `/api/v2/`)
**Current Version**: v1
**Migration Policy**:
- Maintain backward compatibility within major version (v1.x)
- Breaking changes = new major version
- Deprecation warnings in response headers: `Deprecation: true`, `Sunset: 2026-01-01`
- Support old version for 6 months after new version released

**When to Bump Version**:
- Breaking change: Remove field, change data type, change auth
- Breaking change: Change error response format
- Non-breaking: Add optional field, add new endpoint (no version bump)

---

## Authentication

**Method**: Bearer token (simple API key)
**Provider**: Self-managed (env variable)
**Token Lifetime**: No expiration (static token)

**How it Works**:
1. Generate secure token: `openssl rand -hex 32`
2. Store in `.env`: `BOT_API_AUTH_TOKEN=abc123...`
3. Client sends token in `Authorization: Bearer abc123...` header
4. API validates token matches env variable

**Token Validation**:
```python
# FastAPI middleware
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def validate_token(token: str = Security(security)):
    if token.credentials != os.getenv("BOT_API_AUTH_TOKEN"):
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Rotation**: Manual (update `.env`, restart API)

---

## Authorization

**Model**: Single-user (no RBAC)
**Enforcement**: Token validation only (no role checking)

**Future**: If expanding to multi-user, add role-based permissions:
```python
# Example: Admin-only endpoint
@require_role("admin")
async def emergency_stop():
    ...
```

---

## Request/Response Format

### Request Format

**Content-Type**: `application/json` (default)
**Encoding**: UTF-8

**Request Body Structure**:
```json
{
  "field1": "value",
  "field2": 123,
  "nested": {
    "field3": true
  }
}
```

**Validation**:
- Pydantic schemas validate all inputs
- Reject unknown fields
- Type coercion where safe (string "123" → int 123)

### Response Format

**Success Response**:
```json
{
  "data": { ... }
}
```

**List Response** (with pagination):
```json
{
  "data": [ ... ],
  "pagination": {
    "total": 100,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

**Error Response** (RFC 7807 Problem Details):
```json
{
  "type": "https://docs.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "Request body failed validation",
  "errors": [
    {
      "field": "symbol",
      "message": "Symbol must be 1-5 uppercase characters"
    }
  ],
  "request_id": "req_abc123"
}
```

---

## Pagination

**Strategy**: Offset-based (simple, works for < 100K records)
**Default Limit**: 100
**Max Limit**: 1000

**Query Parameters**:
- `?limit=100` - Items per page
- `?offset=0` - Starting position
- `?sort_by=timestamp&order=desc` - Sorting

**Response**:
```json
{
  "data": [...],
  "pagination": {
    "total": 500,
    "limit": 100,
    "offset": 0,
    "has_more": true
  }
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | When to Use |
|------|---------|-------------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST (created resource) |
| 204 | No Content | Successful DELETE, command accepted |
| 400 | Bad Request | Validation error, malformed request |
| 401 | Unauthorized | Missing/invalid auth token |
| 403 | Forbidden | Valid token, but operation not allowed (e.g., bot in paper mode) |
| 404 | Not Found | Resource doesn't exist (e.g., order_id not found) |
| 422 | Unprocessable Entity | Business logic violation (e.g., circuit breaker tripped) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Bot stopped, maintenance |

### Error Response Structure

**Format**: RFC 7807 Problem Details

**Example** (Validation Error):
```json
{
  "type": "https://docs.tradingbot.com/errors/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "Invalid symbol format",
  "errors": [
    {
      "field": "symbol",
      "code": "invalid_format",
      "message": "Symbol must be 1-5 uppercase letters"
    }
  ],
  "request_id": "req_abc123"
}
```

**Example** (Circuit Breaker):
```json
{
  "type": "https://docs.tradingbot.com/errors/circuit-breaker-tripped",
  "title": "Circuit Breaker Tripped",
  "status": 422,
  "detail": "Trading paused due to daily loss limit exceeded",
  "instance": "/api/v1/commands/close-position",
  "request_id": "req_xyz789",
  "context": {
    "daily_pnl_pct": -3.2,
    "limit_pct": -3.0
  }
}
```

---

## Rate Limiting

**Strategy**: Per IP (for now, single user = no strict limits)
**Limits**:
- Authenticated: 100 requests/minute per IP
- Future: Per-user limits if multi-user

**Implementation**: Redis + sliding window (future)

**Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 73
X-RateLimit-Reset: 1677721600
```

**429 Response**:
```json
{
  "type": "https://docs.tradingbot.com/errors/rate-limit",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "Too many requests. Try again in 45 seconds.",
  "retry_after": 45
}
```

---

## Caching

**Strategy**: Server-side (Redis) for LLM responses
**Client-Side**: No caching (real-time data needed)

**Server-Side**:
- LLM pattern analysis: 1-hour TTL
- Performance metrics: 10-minute TTL
- Bot status: No cache (always fresh)

**Cache Keys**:
- `llm:pattern:{symbol}:{timeframe}:{timestamp_hour}` → Pattern analysis
- `perf:summary:{window}` → Performance metrics

**Cache-Control Headers**:
```http
# Real-time data (no cache)
Cache-Control: no-store

# LLM analysis (cacheable)
Cache-Control: private, max-age=3600
```

---

## API Documentation

**Tool**: OpenAPI 3.0 (Swagger UI)
**Auto-Generated**: Yes (FastAPI generates from Pydantic schemas)
**Location**: `http://localhost:8000/docs` (dev), `https://api.tradingbot.com/docs` (prod)

**What's Documented**:
- All endpoints with request/response examples
- Authentication requirements
- Error responses
- Rate limits
- Pagination details

**Additional Docs**:
- Getting started guide: `docs/api/getting-started.md`
- Authentication tutorial: `docs/api/authentication.md`
- Postman collection: `docs/api/trading-bot.postman_collection.json`

---

## Webhook Strategy

**Not Implemented**: No webhooks currently (future feature)

**Future Use Case**: Notify external systems when trades execute
- Event: `trade.executed`, `position.closed`, `alert.triggered`
- Payload: JSON with trade details
- Security: HMAC signature verification

---

## CORS Policy

**Allowed Origins**:
- `http://localhost:3000` (local development)
- `https://api.tradingbot.com` (production)
- `*` (development only - disable in production)

**Allowed Methods**: GET, POST, PUT, DELETE, OPTIONS
**Allowed Headers**: Authorization, Content-Type
**Credentials**: Allowed (cookies, auth headers)
**Max Age**: 3600 (cache preflight for 1 hour)

**Implementation** (FastAPI):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

## API Lifecycle

### Deprecation Process

1. **Announce**: 3 months notice (GitHub release notes)
2. **Mark**: Add deprecation headers
   ```http
   Deprecation: true
   Sunset: Fri, 01 Jan 2026 00:00:00 GMT
   Link: <https://docs.tradingbot.com/migration/v1-to-v2>; rel="alternate"
   ```
3. **Support**: 6 months minimum
4. **Sunset**: Remove endpoint, return 410 Gone

### Breaking Changes

**What Counts as Breaking**:
- Remove endpoint
- Remove field from response
- Change field type (string → int)
- Make optional field required
- Change auth method

**How to Handle**:
- Breaking changes → new major version (`/api/v2/`)
- Run v1 and v2 in parallel for 6 months

---

## Testing Strategy

**Unit Tests**: Business logic (pattern analysis, validation)
**Integration Tests**: Full request → response cycle (with test DB)
**Contract Tests**: Request/response schemas match OpenAPI spec

**Tools**:
- pytest for backend tests
- Postman/Newman for API contract tests
- httpx for async client testing

**Coverage Target**: 80% for API code

**Example Test**:
```python
def test_get_positions_success(client):
    response = client.get(
        "/api/v1/positions",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "positions" in data
    assert isinstance(data["positions"], list)
```

---

## Performance Targets

| Endpoint | P50 Target | P95 Target | P99 Target |
|----------|------------|------------|------------|
| GET /status | < 50ms | < 100ms | < 200ms |
| GET /positions | < 100ms | < 200ms | < 500ms |
| GET /trades | < 200ms | < 500ms | < 1s |
| POST /commands/* | < 100ms | < 300ms | < 500ms |
| POST /analysis/pattern (uncached) | < 2s | < 5s | < 10s (LLM call) |
| POST /analysis/pattern (cached) | < 50ms | < 100ms | < 200ms |

**How Measured**: FastAPI middleware logs per-request timing

**Violations**:
- P95 > 1s → Investigate (slow query, external API)
- P99 > 5s → Alert to logs

---

## External API Integrations

### Robinhood API

**Type**: Unofficial REST API
**Authentication**: pyotp (MFA/2FA)
**Rate Limit**: 60 req/min (enforced by Robinhood)
**Error Handling**: Exponential backoff retry (3 attempts)
**Failure Mode**: Queue orders, retry later

### Alpaca Markets API

**Type**: Official REST API
**Authentication**: API key + secret
**Rate Limit**: 200 req/min
**Error Handling**: Retry with backoff
**Failure Mode**: Fallback to Yahoo Finance (delayed data)

### Polygon.io API

**Type**: WebSocket + REST
**Authentication**: API key
**Rate Limit**: Per plan (Starter: limited)
**Error Handling**: Reconnect on disconnect
**Failure Mode**: Continue without L2 data (degrade to L1)

### OpenAI API

**Type**: REST API
**Authentication**: API key
**Rate Limit**: Per tier (default: 3 req/min for GPT-4o)
**Error Handling**: Retry once, then cache miss
**Failure Mode**: Skip LLM validation (use rule-based only)
**Budget**: $100/mo (alert at 80%)

---

## Change Log

| Date | Change | Reason | Impact |
|------|--------|--------|--------|
| 2025-10-26 | Initial API strategy | Document REST API design | Foundation for FastAPI implementation |
| 2025-10-01 | Added LLM analysis endpoints | Feature 029: LLM integration | New category, 2 endpoints |
| 2025-09-20 | Added bearer token auth | Security baseline | All endpoints require auth |
| 2025-09-15 | Defined RFC 7807 error format | Industry standard | Better error handling |
