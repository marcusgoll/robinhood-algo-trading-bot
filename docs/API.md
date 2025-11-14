# Trading Bot API Documentation

**Version**: v1.8.0
**Base URL**: `http://localhost:8000`
**Authentication**: API Key (X-API-Key header)

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [State Endpoints](#state-endpoints)
  - [Configuration Endpoints](#configuration-endpoints)
  - [Workflow Endpoints](#workflow-endpoints)
  - [Observability Endpoints](#observability-endpoints)
- [WebSocket Streaming](#websocket-streaming)
- [Natural Language CLI](#natural-language-cli)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

---

## Overview

The Trading Bot API provides comprehensive monitoring and control capabilities for AI assistants and operators. Built with FastAPI, it offers:

- **State Monitoring**: Real-time bot state, positions, performance metrics
- **Configuration Management**: Validate, diff, apply, and rollback configuration changes
- **Workflow Automation**: Execute predefined maintenance workflows
- **WebSocket Streaming**: Real-time metrics updates every 5 seconds
- **Natural Language Interface**: Conversational CLI for common operations
- **OpenAPI Documentation**: Interactive Swagger UI at `/api/docs`

### Key Features

- **<10KB Summary**: Optimized for LLM context windows
- **Semantic Errors**: Structured error responses with cause, impact, remediation
- **100% Contract Compliance**: All responses match OpenAPI specification
- **<100ms P95 Latency**: Fast response times for all endpoints

---

## Quick Start

### 1. Start the API Server

```bash
# Set API token
echo "BOT_API_AUTH_TOKEN=your-secure-token-here" >> .env

# Start API service
bash scripts/start_api.sh

# Verify service is running
curl http://localhost:8000/api/v1/health/healthz
```

### 2. Access Swagger UI

Open `http://localhost:8000/api/docs` in your browser for interactive API documentation.

### 3. Make Your First Request

```bash
# Set your API token
export API_TOKEN="your-secure-token-here"

# Get bot summary (<10KB response)
curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/summary

# Get complete bot state
curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/state
```

---

## Authentication

All API endpoints (except `/api/docs` and `/health/healthz`) require authentication via API key.

### Configuration

Set the API token in your `.env` file:

```bash
BOT_API_AUTH_TOKEN=your-secure-random-token
```

### Usage

Include the API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-token" http://localhost:8000/api/v1/summary
```

### Error Responses

**Missing Token**:
```json
{
  "error_code": "AUTH_001",
  "error_type": "AuthenticationError",
  "message": "API key required",
  "cause": "No X-API-Key header provided",
  "impact": "Request rejected",
  "remediation": "Add X-API-Key header with valid token",
  "severity": "high",
  "context": {},
  "timestamp": "2025-10-26T12:00:00Z"
}
```

**Invalid Token**:
```json
{
  "error_code": "AUTH_002",
  "error_type": "AuthenticationError",
  "message": "Invalid API key",
  "cause": "Provided API key does not match configured token",
  "impact": "Request rejected",
  "remediation": "Check BOT_API_AUTH_TOKEN in .env file",
  "severity": "high",
  "context": {},
  "timestamp": "2025-10-26T12:00:00Z"
}
```

---

## Endpoints

### State Endpoints

#### GET /api/v1/state

Returns complete bot state including positions, orders, account status, health metrics, and performance data.

**Response** (BotStateResponse):
```json
{
  "positions": [
    {
      "symbol": "AAPL",
      "quantity": 100,
      "entry_price": "150.00",
      "current_price": "155.50",
      "unrealized_pl": "550.00",
      "unrealized_pl_pct": "3.67",
      "last_updated": "2025-10-26T10:30:00Z"
    }
  ],
  "orders": [],
  "account": {
    "buying_power": "50000.00",
    "account_balance": "100000.00",
    "cash_balance": "75000.00",
    "day_trade_count": 2,
    "last_updated": "2025-10-26T10:30:00Z"
  },
  "health": {
    "status": "healthy",
    "circuit_breaker_active": false,
    "api_connected": true,
    "last_trade_timestamp": "2025-10-26T10:25:00Z",
    "last_heartbeat": "2025-10-26T10:30:00Z",
    "error_count_last_hour": 0
  },
  "performance": {
    "win_rate": 0.65,
    "avg_risk_reward": 2.5,
    "total_realized_pl": "5000.00",
    "total_unrealized_pl": "550.00",
    "total_pl": "5550.00",
    "current_streak": 3,
    "streak_type": "WIN",
    "trades_today": 5,
    "session_count": 15,
    "max_drawdown": "-800.00"
  },
  "config_summary": {
    "max_position_pct": 5.0,
    "max_daily_loss_pct": 3.0,
    "paper_trading": true
  },
  "market_status": "OPEN",
  "timestamp": "2025-10-26T10:30:00Z",
  "data_age_seconds": 0.5,
  "warnings": []
}
```

**Cache Control**:
- Default TTL: 60 seconds
- Bypass cache: Add `Cache-Control: no-cache` header

**Use Cases**:
- Monitor current positions and P&L
- Check bot health status
- Analyze performance metrics
- Verify configuration

---

#### GET /api/v1/summary

Returns compressed bot summary optimized for LLM context windows (<10KB response).

**Response** (BotSummaryResponse):
```json
{
  "health_status": "healthy",
  "position_count": 1,
  "open_orders_count": 0,
  "daily_pnl": "550.00",
  "circuit_breaker_status": "inactive",
  "recent_errors": [],
  "timestamp": "2025-10-26T10:30:00Z"
}
```

**Response Size**: ~8KB (target <10KB)

**Use Cases**:
- Quick health check
- LLM context-aware monitoring
- Dashboard overview
- Alerting systems

---

#### GET /api/v1/health

Returns health check status.

**Response** (HealthStatus):
```json
{
  "status": "healthy",
  "circuit_breaker_active": false,
  "api_connected": true,
  "last_trade_timestamp": "2025-10-26T10:25:00Z",
  "last_heartbeat": "2025-10-26T10:30:00Z",
  "error_count_last_hour": 0
}
```

**Status Values**:
- `healthy`: All systems operational
- `degraded`: Some issues detected (e.g., API disconnected, errors present)
- `offline`: Bot not running or critical failures

**Use Cases**:
- Monitoring/alerting
- Pre-trade validation
- Debugging connectivity issues

---

### Configuration Endpoints

#### GET /api/v1/config

Returns current bot configuration.

**Response**:
```json
{
  "max_position_pct": 5.0,
  "max_daily_loss_pct": 3.0,
  "paper_trading": true,
  "trading_hours": {
    "start": "07:00",
    "end": "10:00",
    "timezone": "EST"
  },
  "risk_management": {
    "atr_enabled": false,
    "atr_period": 14,
    "atr_multiplier": 2.0
  }
}
```

**Use Cases**:
- Review current settings
- Audit configuration
- Backup configuration

---

#### POST /api/v1/config/validate

Validates proposed configuration changes without applying them.

**Request Body**:
```json
{
  "max_position_pct": 10.0,
  "max_daily_loss_pct": 5.0
}
```

**Response**:
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    "max_position_pct increased from 5.0% to 10.0% - higher risk"
  ]
}
```

**Use Cases**:
- Pre-validate changes
- Safety check before applying
- Identify configuration errors

---

#### GET /api/v1/config/diff

Shows difference between current and proposed configuration.

**Query Parameters**:
- `proposed`: URL-encoded JSON of proposed config

**Response**:
```json
{
  "changes": [
    {
      "field": "max_position_pct",
      "current": 5.0,
      "proposed": 10.0,
      "impact": "Doubles maximum position size - increases risk"
    }
  ],
  "summary": "1 field changed"
}
```

**Use Cases**:
- Review changes before applying
- Understand impact of changes
- Audit configuration history

---

#### PUT /api/v1/config/rollback

Reverts configuration to previous version.

**Request Body**:
```json
{
  "version": "previous",
  "confirm": true
}
```

**Response**:
```json
{
  "success": true,
  "message": "Configuration rolled back to version from 2025-10-26T09:00:00Z",
  "current_config": { /* ... */ }
}
```

**Use Cases**:
- Undo bad configuration changes
- Recover from errors
- Emergency rollback

---

### Workflow Endpoints

#### GET /api/v1/workflows

Lists available workflows.

**Response**:
```json
{
  "workflows": [
    {
      "id": "check-health",
      "name": "Health Check Workflow",
      "description": "Comprehensive bot health validation",
      "steps": 5
    },
    {
      "id": "export-logs",
      "name": "Export Logs Workflow",
      "description": "Export logs for analysis",
      "steps": 3
    },
    {
      "id": "restart-bot",
      "name": "Safe Bot Restart",
      "description": "Gracefully restart trading bot",
      "steps": 7
    },
    {
      "id": "update-targets",
      "name": "Update Profit Targets",
      "description": "Modify daily profit targets",
      "steps": 4
    }
  ]
}
```

---

#### GET /api/v1/workflows/{workflow_id}

Returns workflow definition.

**Response**:
```yaml
id: check-health
name: Health Check Workflow
description: Comprehensive bot health validation
steps:
  - name: Check API Connection
    action: verify_api_connection
    validation: connection_established
  - name: Verify Account Access
    action: check_account_status
    validation: account_accessible
  # ... more steps
```

---

#### POST /api/v1/workflows/{workflow_id}/execute

Executes a workflow.

**Request Body**:
```json
{
  "parameters": {},
  "dry_run": false
}
```

**Response**:
```json
{
  "execution_id": "wf-exec-12345",
  "workflow_id": "check-health",
  "status": "running",
  "started_at": "2025-10-26T10:30:00Z",
  "progress": {
    "completed_steps": 2,
    "total_steps": 5,
    "current_step": "Verify Account Access"
  }
}
```

**Use Cases**:
- Automate maintenance tasks
- Execute complex procedures
- Ensure step-by-step validation

---

### Observability Endpoints

#### GET /api/v1/metrics

Returns real-time metrics snapshot.

**Response**:
```json
{
  "timestamp": "2025-10-26T10:30:00Z",
  "positions": {
    "count": 1,
    "total_value": "15550.00",
    "unrealized_pl": "550.00"
  },
  "orders": {
    "open": 0,
    "filled_today": 5
  },
  "performance": {
    "daily_pnl": "550.00",
    "win_rate": 0.65,
    "trades_today": 5
  },
  "health": {
    "status": "healthy",
    "uptime_seconds": 14400,
    "errors_last_hour": 0
  }
}
```

**Use Cases**:
- Real-time monitoring
- Dashboard integration
- Performance tracking
- Alerting thresholds

---

## WebSocket Streaming

Real-time metrics streaming via WebSocket connection.

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/stream');

// Authentication (send API key after connection)
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    api_key: 'your-api-token'
  }));
};

// Receive updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Metrics update:', data);
};
```

### Update Frequency

- Default: Every 5 seconds
- Configurable via `stream_interval` parameter

### Message Format

```json
{
  "type": "metrics_update",
  "timestamp": "2025-10-26T10:30:00Z",
  "data": {
    "positions": [ /* ... */ ],
    "health": { /* ... */ },
    "performance": { /* ... */ }
  }
}
```

### Use Cases

- Live dashboards
- Real-time alerts
- Streaming analytics
- Monitoring systems

---

## Natural Language CLI

Execute commands using conversational language.

### Usage

```bash
# Using the CLI module
python -m src.trading_bot.cli.nl_commands "show today's performance"

# Sample commands
python -m src.trading_bot.cli.nl_commands "check bot health"
python -m src.trading_bot.cli.nl_commands "what positions are open?"
python -m src.trading_bot.cli.nl_commands "how much buying power do I have?"
```

### Supported Commands

| Intent | Example Commands | API Called |
|--------|-----------------|------------|
| Performance | "show today's performance", "how am I doing?" | GET /api/v1/state |
| Health | "check bot health", "is the bot running?" | GET /api/v1/health |
| Positions | "what positions are open?", "show my trades" | GET /api/v1/state |
| Account | "how much buying power?", "account balance" | GET /api/v1/state |
| Summary | "quick status", "give me a summary" | GET /api/v1/summary |

### Response Format

```
Bot Health: ✅ Healthy
Positions: 1 open (AAPL: +$550)
Performance: 5 trades today, 65% win rate
Daily P&L: +$550 (+0.55%)
```

---

## Error Handling

All errors return semantic error format with HTTP status codes.

### Semantic Error Structure

```json
{
  "error_code": "ERR_CODE",
  "error_type": "ErrorType",
  "message": "Human-readable message",
  "cause": "Why this happened",
  "impact": "What this affects",
  "remediation": "How to fix it",
  "severity": "low|medium|high|critical",
  "context": {},
  "timestamp": "2025-10-26T10:30:00Z"
}
```

### Common Error Codes

| Code | Type | HTTP Status | Description |
|------|------|-------------|-------------|
| AUTH_001 | AuthenticationError | 401 | Missing API key |
| AUTH_002 | AuthenticationError | 401 | Invalid API key |
| BOT_001 | BotOfflineError | 503 | Trading bot not running |
| BOT_002 | BotDegradedError | 503 | Bot in degraded state |
| CFG_001 | ConfigValidationError | 400 | Invalid configuration |
| WF_001 | WorkflowNotFoundError | 404 | Workflow does not exist |
| WF_002 | WorkflowExecutionError | 500 | Workflow execution failed |

### Example Error Responses

**Bot Offline**:
```json
{
  "error_code": "BOT_001",
  "error_type": "BotOfflineError",
  "message": "Trading bot is not running",
  "cause": "No heartbeat received in last 5 minutes",
  "impact": "State data may be stale, no trades can be executed",
  "remediation": "Start the trading bot: python -m src.trading_bot",
  "severity": "high",
  "context": {
    "last_heartbeat": "2025-10-26T10:20:00Z",
    "time_since_heartbeat_seconds": 600
  },
  "timestamp": "2025-10-26T10:30:00Z"
}
```

---

## Rate Limiting

API implements rate limiting to prevent abuse.

### Limits

- **Default**: 100 requests per minute per API key
- **Burst**: 10 requests per second

### Headers

Response includes rate limit headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1698345600
```

### Exceeded Response

**HTTP 429 Too Many Requests**:
```json
{
  "error_code": "RATE_001",
  "error_type": "RateLimitExceeded",
  "message": "Rate limit exceeded",
  "cause": "Too many requests in short time period",
  "impact": "Request rejected",
  "remediation": "Wait 60 seconds before retrying",
  "severity": "medium",
  "context": {
    "limit": 100,
    "window_seconds": 60,
    "retry_after_seconds": 45
  },
  "timestamp": "2025-10-26T10:30:00Z"
}
```

---

## Examples

### Python Client

```python
import requests

class TradingBotClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}

    def get_summary(self):
        """Get bot summary (<10KB response)."""
        response = requests.get(
            f"{self.base_url}/api/v1/summary",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_state(self):
        """Get complete bot state."""
        response = requests.get(
            f"{self.base_url}/api/v1/state",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def check_health(self):
        """Check bot health."""
        response = requests.get(
            f"{self.base_url}/api/v1/health",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage
client = TradingBotClient(
    base_url="http://localhost:8000",
    api_key="your-api-token"
)

# Get summary
summary = client.get_summary()
print(f"Health: {summary['health_status']}")
print(f"Daily P&L: ${summary['daily_pnl']}")

# Check health
health = client.check_health()
print(f"Status: {health['status']}")
```

### Bash/cURL Examples

```bash
#!/bin/bash

API_TOKEN="your-api-token"
BASE_URL="http://localhost:8000"

# Get summary
curl -s -H "X-API-Key: $API_TOKEN" \
  $BASE_URL/api/v1/summary | jq '.'

# Get state
curl -s -H "X-API-Key: $API_TOKEN" \
  $BASE_URL/api/v1/state | jq '.performance'

# Check health
curl -s -H "X-API-Key: $API_TOKEN" \
  $BASE_URL/api/v1/health | jq '.status'

# Execute workflow
curl -s -X POST \
  -H "X-API-Key: $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}' \
  $BASE_URL/api/v1/workflows/check-health/execute | jq '.'
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

class TradingBotClient {
  constructor(baseURL, apiKey) {
    this.client = axios.create({
      baseURL,
      headers: { 'X-API-Key': apiKey }
    });
  }

  async getSummary() {
    const response = await this.client.get('/api/v1/summary');
    return response.data;
  }

  async getState() {
    const response = await this.client.get('/api/v1/state');
    return response.data;
  }

  async streamMetrics(callback) {
    const ws = new WebSocket('ws://localhost:8000/api/v1/stream');

    ws.onopen = () => {
      ws.send(JSON.stringify({
        type: 'auth',
        api_key: this.apiKey
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      callback(data);
    };

    return ws;
  }
}

// Usage
const client = new TradingBotClient(
  'http://localhost:8000',
  'your-api-token'
);

// Get summary
const summary = await client.getSummary();
console.log(`Health: ${summary.health_status}`);
console.log(`Daily P&L: $${summary.daily_pnl}`);

// Stream metrics
client.streamMetrics((data) => {
  console.log('Metrics update:', data);
});
```

---

## Configuration

### Environment Variables

```bash
# Required
BOT_API_AUTH_TOKEN=your-secure-random-token

# Optional (with defaults)
BOT_API_PORT=8000                    # API service port
BOT_API_HOST=0.0.0.0                 # Bind address
BOT_API_CORS_ORIGINS=*               # CORS allowed origins (configure for production)
BOT_STATE_CACHE_TTL=60               # State cache TTL in seconds
BOT_API_RATE_LIMIT=100               # Requests per minute
```

### Production Recommendations

1. **CORS**: Set specific allowed origins instead of `*`
   ```bash
   BOT_API_CORS_ORIGINS=https://dashboard.example.com,https://admin.example.com
   ```

2. **Authentication**: Use strong random tokens (32+ characters)
   ```bash
   BOT_API_AUTH_TOKEN=$(openssl rand -hex 32)
   ```

3. **Rate Limiting**: Tune based on usage patterns
   ```bash
   BOT_API_RATE_LIMIT=200  # Increase for heavy usage
   ```

4. **HTTPS**: Use reverse proxy (nginx, Caddy) for TLS termination
   ```nginx
   location /api/ {
       proxy_pass http://localhost:8000;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header Host $host;
   }
   ```

---

## Support

- **Interactive Documentation**: http://localhost:8000/api/docs
- **Issues**: https://github.com/marcusgoll/robinhood-algo-trading-bot/issues
- **Quickstart Guide**: `specs/029-llm-friendly-bot-operations/quickstart.md`
- **Feature Spec**: `specs/029-llm-friendly-bot-operations/spec.md`

---

**Last Updated**: 2025-10-26
**API Version**: v1.8.0
**Feature**: LLM-Friendly Bot Operations and Monitoring
