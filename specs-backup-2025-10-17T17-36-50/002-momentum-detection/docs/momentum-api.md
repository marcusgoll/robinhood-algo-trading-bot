# Momentum Detection API Reference

**Feature**: 002-momentum-detection
**Created**: 2025-10-16
**Status**: Draft

## Purpose

This document provides comprehensive API reference for the momentum detection endpoints, request/response schemas, error handling, and authentication requirements.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
4. [Request Schemas](#request-schemas)
5. [Response Schemas](#response-schemas)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)

---

## Overview

*To be populated with API overview*

**Base URL**: `http://localhost:8000/api/v1/momentum`

**Supported Operations**:
- Get momentum signals (query)
- Trigger momentum scan (manual)

**Related Sections**:
- See [spec.md](../spec.md#requirements) for API functional requirements
- See [plan.md](../plan.md#project-structure) for route definitions

---

## Authentication

*To be populated with authentication details*

**Method**: Bearer token (inherited from trading_bot auth)

**Headers Required**:
```http
Authorization: Bearer <token>
```

**Reference**: [plan.md](../plan.md#authentication-strategy) for auth details

---

## Endpoints

### GET /api/v1/momentum/signals

*To be populated with endpoint details*

**Purpose**: Query historical momentum signals

**Query Parameters**:
- `symbol` (optional): Filter by stock symbol
- `signal_type` (optional): Filter by signal type (catalyst, premarket_mover, bull_flag)
- `min_strength` (optional): Minimum signal strength (0-100)
- `start_date` (optional): ISO 8601 UTC timestamp
- `end_date` (optional): ISO 8601 UTC timestamp
- `limit` (optional): Max results (default: 50, max: 500)
- `offset` (optional): Pagination offset (default: 0)

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/v1/momentum/signals?min_strength=70&limit=10" \
  -H "Authorization: Bearer <token>"
```

**Example Response**:
```json
{
  "signals": [],
  "total": 0,
  "count": 0,
  "has_more": false
}
```

---

### POST /api/v1/momentum/scan

*To be populated with endpoint details*

**Purpose**: Trigger manual momentum scan

**Request Body**:
```json
{
  "symbols": ["AAPL", "GOOGL", "TSLA"],
  "scan_types": ["catalyst", "premarket", "bull_flag"]
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/momentum/scan" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL"], "scan_types": ["catalyst"]}'
```

**Example Response**:
```json
{
  "scan_id": "uuid-here",
  "status": "started",
  "symbols": ["AAPL"],
  "scan_types": ["catalyst"],
  "started_at": "2025-10-16T14:30:00Z"
}
```

**Reference**: [plan.md](../plan.md#integration-scenarios) for complete usage examples

---

## Request Schemas

*To be populated with detailed request schemas*

**MomentumQuery**:
- symbol: string (regex: `^[A-Z]{1,5}$`)
- signal_type: enum (catalyst, premarket_mover, bull_flag)
- min_strength: float (0-100)
- start_date: ISO 8601 UTC
- end_date: ISO 8601 UTC

**ScanRequest**:
- symbols: list of strings (1-100 symbols)
- scan_types: list of enums (at least one required)

**Reference**: [plan.md](../plan.md#project-structure) for schema file locations

---

## Response Schemas

*To be populated with detailed response schemas*

**MomentumSignal**:
```json
{
  "id": "uuid",
  "symbol": "AAPL",
  "signal_type": "bull_flag",
  "timestamp": "2025-10-16T14:30:00Z",
  "strength": 85.5,
  "metadata": {}
}
```

**CatalystEvent**:
```json
{
  "symbol": "AAPL",
  "catalyst_type": "earnings",
  "headline": "Apple reports record Q4 earnings",
  "published_at": "2025-10-16T13:00:00Z",
  "source": "NewsAPI"
}
```

**Reference**: [plan.md](../plan.md#data-model) for complete entity definitions

---

## Error Handling

*To be populated with error response formats*

**Error Response Format**:
```json
{
  "error": {
    "code": "INVALID_SYMBOL",
    "message": "Symbol must be 1-5 uppercase letters",
    "details": {}
  }
}
```

**HTTP Status Codes**:
- 200: Success
- 400: Bad request (invalid parameters)
- 401: Unauthorized (missing/invalid token)
- 422: Validation error
- 429: Rate limit exceeded
- 500: Internal server error

**Reference**: [plan.md](../plan.md#input-validation) for validation rules

---

## Rate Limiting

*To be populated with rate limiting details*

**Limits**:
- GET /signals: 60 req/min per user
- POST /scan: 10 req/min per user

**Headers**:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1697472000
```

**Reference**: [plan.md](../plan.md#input-validation) for rate limit details

---

## Related Documentation

- [momentum-architecture.md](./momentum-architecture.md) - System architecture
- [momentum-examples.md](./momentum-examples.md) - Usage examples
- [spec.md](../spec.md) - Feature specification
- [plan.md](../plan.md) - Implementation plan
