# Quickstart: llm-friendly-bot-operations

## Scenario 1: Initial Setup

### Install Dependencies

```bash
# Install FastAPI and dependencies
pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 pydantic==2.5.0 websockets==12.0 jsonschema==4.20.0

# Or using uv (if in project)
uv add fastapi uvicorn websockets jsonschema
```

### Configure API Token

```bash
# Add to .env file
echo "BOT_API_PORT=8000" >> .env
echo "BOT_API_AUTH_TOKEN=your-secure-token-here" >> .env
echo "BOT_API_CORS_ORIGINS=*" >> .env  # Restrict in production
echo "BOT_STATE_CACHE_TTL=60" >> .env
```

### Start Services

```bash
# Terminal 1: Start trading bot
python -m src.trading_bot.main

# Terminal 2: Start API service
cd api
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Verify both services running
curl http://localhost:8000/api/v1/health/healthz
# Expected: {"status": "healthy", "timestamp": "..."}
```

---

## Scenario 2: Validation

### Test Endpoints

```bash
# Set API token
export API_TOKEN="your-secure-token-here"

# 1. Test authentication (should fail without token)
curl http://localhost:8000/api/v1/summary
# Expected: 401 Unauthorized with SemanticError

# 2. Test authentication (should succeed with token)
curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/summary
# Expected: 200 OK with BotSummary JSON <10KB

# 3. Test complete state endpoint
curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/state
# Expected: 200 OK with full BotState (account, positions, performance, health, config)

# 4. Test metrics endpoint
curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/metrics
# Expected: 200 OK with MetricsSnapshot

# 5. Test OpenAPI documentation
curl http://localhost:8000/api/docs
# Expected: HTML Swagger UI page (no auth required for docs)
```

### Check Types and Schemas

```bash
# Validate response schemas match OpenAPI spec
cd specs/029-llm-friendly-bot-operations

# Install validation tools
pip install openapi-spec-validator

# Validate OpenAPI spec
openapi-spec-validator contracts/api.yaml
# Expected: No validation errors

# Test Pydantic models
cd ../../api
python -c "from app.schemas.state import BotSummaryResponse; print('✓ Schemas valid')"
```

### Run Tests

```bash
# Run unit tests for state aggregation
pytest tests/unit/services/test_state_aggregator.py -v

# Run integration tests for API endpoints
pytest tests/integration/routes/test_state_routes.py -v

# Run performance benchmarks
pytest tests/acceptance/test_api_performance.py -v --benchmark-only
# Expected: All endpoints <100ms P95

# Check summary endpoint size constraint
pytest tests/acceptance/test_summary_size.py -v
# Expected: Response <10KB (<2500 tokens)
```

### Lint and Type Check

```bash
# Type check with mypy
mypy api/app/routes/state.py api/app/services/state_aggregator.py

# Lint with ruff
ruff check api/app/

# Format code
ruff format api/app/
```

---

## Scenario 3: Manual Testing

### Query Bot State

```bash
# 1. Get compressed summary (LLM context optimization)
curl -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/summary | jq

# Expected output:
# {
#   "health_status": "healthy",
#   "position_count": 2,
#   "open_order_count": 0,
#   "daily_pnl": "345.67",
#   "circuit_breaker_active": false,
#   "recent_errors": [],
#   "last_trade_time": "2025-10-24T13:45:32Z",
#   "generated_at": "2025-10-24T14:32:00Z"
# }

# 2. Get full state with all details
curl -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/state | jq '.positions'

# Expected: Array of positions with symbol, quantity, unrealized_pl

# 3. Check specific fields
curl -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/state | jq '.performance.win_rate'

# Expected: 0.65 (or current win rate)
```

### Test Error Handling

```bash
# 1. Trigger validation error (invalid config)
curl -X POST -H "X-API-Key: $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"max_position_size_pct": 25}' \
  http://localhost:8000/api/v1/config/validate

# Expected: 400 Bad Request with SemanticError
# {
#   "error_code": "CFG_001",
#   "error_type": "ValidationError",
#   "message": "Invalid configuration: max_position_size_pct must be between 1 and 10",
#   "cause": "Attempted to set max_position_size_pct to 25",
#   "impact": "Configuration change rejected",
#   "remediation": "Set max_position_size_pct to value between 1 and 10",
#   "context": {"field": "max_position_size_pct", "attempted_value": 25},
#   "timestamp": "...",
#   "severity": "medium"
# }

# 2. Test authentication error (missing token)
curl http://localhost:8000/api/v1/state

# Expected: 401 Unauthorized with SemanticError
# {
#   "error_code": "AUTH_001",
#   "error_type": "AuthenticationError",
#   "message": "Invalid or missing API key",
#   "cause": "X-API-Key header not provided",
#   "impact": "API access denied",
#   "remediation": "Provide valid API key in X-API-Key header",
#   ...
# }
```

### Test Configuration Management

```bash
# 1. Get current configuration
curl -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/config | jq

# 2. Validate proposed config
curl -X POST -H "X-API-Key: $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"max_position_size_pct": 3.0, "daily_loss_limit": -300}' \
  http://localhost:8000/api/v1/config/validate

# Expected: {"valid": true, "errors": []}

# 3. Preview config diff
curl -H "X-API-Key: $API_TOKEN" \
  "http://localhost:8000/api/v1/config/diff?proposed=%7B%22max_position_size_pct%22%3A3.0%7D" | jq

# Expected:
# {
#   "changed_fields": [
#     {
#       "field": "max_position_size_pct",
#       "current_value": "5.0",
#       "proposed_value": "3.0"
#     }
#   ],
#   "no_changes": false
# }

# 4. Apply configuration change
curl -X PUT -H "X-API-Key: $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"max_position_size_pct": 3.0}' \
  http://localhost:8000/api/v1/config/apply

# Expected: {"success": true, "change_id": "...", "timestamp": "...", "applied_config": {...}}

# 5. Rollback if needed
curl -X PUT -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/config/rollback

# Expected: Configuration reverted to previous state
```

### Test Workflow Execution

```bash
# 1. List available workflows
curl -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/workflows | jq

# Expected:
# [
#   {"id": "restart-bot", "name": "Restart Bot", "description": "..."},
#   {"id": "update-targets", "name": "Update Targets", "description": "..."},
#   {"id": "export-logs", "name": "Export Logs", "description": "..."},
#   {"id": "check-health", "name": "Check Health", "description": "..."}
# ]

# 2. Execute workflow
curl -X POST -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/workflows/check-health/execute

# Expected: {"workflow_id": "check-health", "status": "IN_PROGRESS", "current_step": 1, ...}

# 3. Check workflow status
curl -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/workflows/check-health/status | jq

# Expected: {"workflow_id": "check-health", "status": "COMPLETED", "current_step": 3, "total_steps": 3, ...}
```

### Test WebSocket Streaming

```bash
# Install wscat for WebSocket testing
npm install -g wscat

# Connect to WebSocket stream
wscat -c "ws://localhost:8000/api/v1/stream?token=$API_TOKEN"

# Expected: Real-time updates every 5 seconds
# > {"health_status": "healthy", "position_count": 2, "daily_pnl": "345.67", ...}
# > {"health_status": "healthy", "position_count": 2, "daily_pnl": "350.12", ...}
# > ...

# Disconnect with Ctrl+C
```

---

## Scenario 4: LLM Integration Examples

### Python LLM Integration

```python
import requests
import json

# Configuration
API_BASE_URL = "http://localhost:8000"
API_TOKEN = "your-secure-token-here"
HEADERS = {"X-API-Key": API_TOKEN}

def get_bot_summary():
    """Get compressed bot state for LLM context window."""
    response = requests.get(f"{API_BASE_URL}/api/v1/summary", headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_full_state():
    """Get complete bot state for detailed analysis."""
    response = requests.get(f"{API_BASE_URL}/api/v1/state", headers=HEADERS)
    response.raise_for_status()
    return response.json()

def execute_workflow(workflow_id: str):
    """Execute maintenance workflow."""
    response = requests.post(
        f"{API_BASE_URL}/api/v1/workflows/{workflow_id}/execute",
        headers=HEADERS
    )
    response.raise_for_status()
    return response.json()

def check_workflow_status(workflow_id: str):
    """Check workflow execution status."""
    response = requests.get(
        f"{API_BASE_URL}/api/v1/workflows/{workflow_id}/status",
        headers=HEADERS
    )
    response.raise_for_status()
    return response.json()

# Example usage
if __name__ == "__main__":
    # Get summary for LLM context
    summary = get_bot_summary()
    print(f"Bot Health: {summary['health_status']}")
    print(f"Daily P&L: ${summary['daily_pnl']}")
    print(f"Positions: {summary['position_count']}")

    # Check for errors
    if summary['recent_errors']:
        print("\nRecent Errors:")
        for error in summary['recent_errors']:
            print(f"  [{error['error_code']}] {error['message']}")
            print(f"  Remediation: {error['remediation']}")

    # Execute health check workflow
    execution = execute_workflow("check-health")
    print(f"\nWorkflow Status: {execution['status']}")

    # Wait for completion
    import time
    while True:
        status = check_workflow_status("check-health")
        if status['status'] in ['COMPLETED', 'FAILED']:
            break
        time.sleep(1)

    print(f"Workflow Completed: {status['status']}")
```

### Natural Language Query Examples

```python
import anthropic
import requests

# LLM integration
client = anthropic.Anthropic(api_key="your-anthropic-api-key")

def query_bot_with_llm(natural_language_query: str):
    """Use LLM to interpret query and fetch relevant bot data."""

    # Get bot state
    summary = get_bot_summary()

    # Ask LLM to interpret query and respond
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        system=f"""You are a trading bot operator assistant. Current bot state:
{json.dumps(summary, indent=2)}

Answer operator questions based on this state data.""",
        messages=[
            {"role": "user", "content": natural_language_query}
        ]
    )

    return message.content[0].text

# Example queries
print(query_bot_with_llm("What's my current daily profit?"))
# Expected: "Your current daily P&L is $345.67 in profit."

print(query_bot_with_llm("Do I have any open positions?"))
# Expected: "Yes, you have 2 open positions."

print(query_bot_with_llm("Is the bot healthy?"))
# Expected: "Yes, the bot is healthy with no active circuit breakers."

print(query_bot_with_llm("Any recent errors I should know about?"))
# Expected: "No recent errors detected. The bot is operating normally."
```

---

## Scenario 5: Debugging

### Check Logs

```bash
# API service logs (uvicorn output)
# Look for request logs, error traces, semantic error formatting

# Bot structured logs (JSONL format)
tail -f logs/$(date +%Y-%m-%d).jsonl | jq 'select(.level == "ERROR")'

# Filter semantic error logs
tail -f logs/$(date +%Y-%m-%d).jsonl | jq 'select(.error_code != null)'

# Check specific error codes
grep "BOT_001" logs/*.jsonl | jq
```

### Verify State Caching

```bash
# Query state twice, check response time difference
time curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/summary > /dev/null
# First request: ~50-100ms (aggregates data)

time curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/summary > /dev/null
# Second request: ~10-20ms (cached, faster)

# Wait for cache expiry (60s default)
sleep 61

time curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/v1/summary > /dev/null
# After expiry: ~50-100ms (re-aggregates)
```

### Monitor WebSocket Connections

```bash
# Check active WebSocket connections
curl -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/metrics | jq '.websocket_connections'

# Expected: Number of active clients
```

### Validate Summary Size Constraint

```bash
# Get summary and check size
curl -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/summary | wc -c

# Expected: <10240 bytes (<10KB)

# Check token count estimate
curl -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/summary | \
  python -c "import sys, json; print(len(json.load(sys.stdin)['generated_at']) * 4)"

# Expected: <2500 tokens (rough estimate)
```

---

## Scenario 6: Production Deployment

### Pre-Deployment Checklist

```bash
# 1. Set production API token
export BOT_API_AUTH_TOKEN=$(openssl rand -hex 32)
echo "BOT_API_AUTH_TOKEN=$BOT_API_AUTH_TOKEN" >> .env.production

# 2. Configure CORS for production
echo "BOT_API_CORS_ORIGINS=https://your-frontend.com,https://api.your-domain.com" >> .env.production

# 3. Verify environment variables
grep BOT_API .env.production

# 4. Run smoke tests
pytest tests/smoke/ -v

# 5. Check dependencies installed
pip list | grep -E "fastapi|uvicorn|pydantic|websockets"
```

### Start Production Services

```bash
# Option 1: systemd service (Linux)
sudo systemctl start trading-bot-api
sudo systemctl status trading-bot-api

# Option 2: Docker (if containerized)
docker-compose up -d api-service

# Option 3: Manual start with production settings
BOT_API_PORT=8000 \
BOT_API_AUTH_TOKEN=$BOT_API_AUTH_TOKEN \
BOT_API_CORS_ORIGINS="https://your-frontend.com" \
uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Verify Production Deployment

```bash
# 1. Health check
curl https://api.your-domain.com/api/v1/health/healthz

# 2. Authenticated request
curl -H "X-API-Key: $BOT_API_AUTH_TOKEN" \
  https://api.your-domain.com/api/v1/summary

# 3. Check OpenAPI docs
curl https://api.your-domain.com/api/docs

# 4. Monitor logs for errors
tail -f /var/log/trading-bot-api/error.log
```

---

## Common Issues & Solutions

### Issue 1: 401 Unauthorized

**Problem**: All API requests return 401

**Solution**:
```bash
# Check API token is set
echo $BOT_API_AUTH_TOKEN

# Verify header format
curl -v -H "X-API-Key: $BOT_API_AUTH_TOKEN" http://localhost:8000/api/v1/summary
# Look for "X-API-Key: your-token-here" in request headers

# Check .env file loaded
grep BOT_API_AUTH_TOKEN .env
```

### Issue 2: Summary exceeds 10KB

**Problem**: GET /api/v1/summary returns >10KB response

**Solution**:
```bash
# Check recent errors count (should be max 3)
curl -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/summary | jq '.recent_errors | length'

# If >3, check error formatting
grep "recent_errors" api/app/services/state_aggregator.py

# Verify truncation logic in SemanticError formatter
```

### Issue 3: WebSocket disconnects immediately

**Problem**: WebSocket connection closes right after connecting

**Solution**:
```bash
# Check token in query string
wscat -c "ws://localhost:8000/api/v1/stream?token=$API_TOKEN"

# Verify WebSocket authentication middleware
grep "websocket" api/app/core/auth.py

# Check connection manager logs
tail -f logs/api.log | grep "WebSocket"
```

### Issue 4: Workflow execution hangs

**Problem**: Workflow status stays IN_PROGRESS indefinitely

**Solution**:
```bash
# Check workflow execution logs
tail -f logs/workflow_execution.jsonl | jq 'select(.workflow_id == "restart-bot")'

# Verify step timeout configuration
cat config/workflows/restart-bot.yaml | grep timeout

# Check for failed step
curl -H "X-API-Key: $API_TOKEN" \
  http://localhost:8000/api/v1/workflows/restart-bot/status | jq '.error'
```
