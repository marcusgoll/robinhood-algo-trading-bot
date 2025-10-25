# Copy: LLM-Friendly Bot Operations and Monitoring

## Screen: API Documentation (Swagger UI)

**Heading**: Trading Bot API Documentation
**Subheading**: Comprehensive REST API reference for bot operations and monitoring
**CTA Primary**: Try API Endpoint
**Help Text**: Explore endpoints, test requests, and view response schemas

**Section Labels**:
- Bot State & Monitoring
- Performance & Metrics
- Configuration Management
- Workflow Execution
- Error & Diagnostics

**Info Messages**:
- API_AUTH_REQUIRED: "Authentication token required. Add 'Authorization: Bearer {token}' header to all requests."
- RATE_LIMITED: "Request rate limited. Maximum 100 requests per hour per token."

## Screen: Dashboard Metrics

**Heading**: Bot Status Dashboard
**Subheading**: Real-time operational metrics and health monitoring
**CTA Primary**: Refresh Now
**Help Text**: Auto-refreshes every 5 seconds. Manual refresh available.

**Status Labels**:
- HEALTHY: "Bot is operational and trading normally"
- DEGRADED: "Bot operational but some features unavailable"
- OFFLINE: "Bot is not running or unreachable"
- CIRCUIT_BREAKER: "Trading halted by circuit breaker"

**Metric Labels**:
- Health Status: "Current operational state"
- Active Positions: "Open positions with unrealized P&L"
- Pending Orders: "Orders awaiting execution"
- Daily P&L: "Today's realized and unrealized profit/loss"
- Circuit Breaker: "Safety system status"

**Empty States**:
- NO_POSITIONS: "No open positions"
- NO_ORDERS: "No pending orders"
- NO_ERRORS: "No recent errors"

## Screen: State Summary

**Heading**: Bot State Summary
**Subheading**: Compressed status optimized for LLM context (<10KB)
**CTA Primary**: Get JSON Summary
**Help Text**: Use this endpoint for LLM queries to minimize token usage

**Summary Fields**:
- health_status: "HEALTHY | DEGRADED | OFFLINE | CIRCUIT_BREAKER"
- positions_count: "Number of open positions"
- orders_count: "Number of pending orders"
- daily_pnl: "Today's P&L in dollars"
- circuit_breaker_active: "true/false"
- recent_errors: "Last 3 errors (if any)"

**Example Response**:
```json
{
  "health_status": "HEALTHY",
  "health_reason": "All systems operational",
  "positions_count": 3,
  "orders_count": 1,
  "daily_pnl": 125.50,
  "circuit_breaker_active": false,
  "recent_errors": [],
  "timestamp": "2025-10-24T20:30:00Z",
  "staleness_seconds": 2
}
```

## Screen: Configuration Management

**Heading**: Bot Configuration
**Subheading**: View and update bot parameters with schema validation
**CTA Primary**: Apply Changes
**CTA Secondary**: Rollback to Previous
**Help Text**: All changes validated against schema before application. Rollback available for 24 hours.

**Section Labels**:
- Risk Management: "Position limits, stop losses, circuit breaker thresholds"
- Trading Parameters: "Symbols, timeframes, strategy settings"
- Operational Settings: "Logging level, refresh intervals, API timeouts"

**Validation Messages**:
- VALIDATION_SUCCESS: "Configuration is valid and ready to apply"
- VALIDATION_ERROR: "Configuration contains errors (see details below)"
- SCHEMA_VIOLATION: "Field '{field}' must be {constraint}"

**Error Messages**:
- INVALID_PERCENTAGE: "Percentage values must be between 0 and 100"
- INVALID_DOLLAR_AMOUNT: "Dollar amounts must be positive numbers"
- REQUIRED_FIELD: "Field '{field}' is required and cannot be empty"
- OUT_OF_RANGE: "Value '{value}' is outside allowed range {min}-{max}"

**Success Messages**:
- CONFIG_APPLIED: "Configuration updated successfully at {timestamp}"
- CONFIG_ROLLED_BACK: "Configuration reverted to previous state from {timestamp}"

## Screen: Workflow Execution

**Heading**: Maintenance Workflows
**Subheading**: Automated task execution with progress tracking
**CTA Primary**: Execute Workflow
**CTA Secondary**: Cancel Execution
**Help Text**: Workflows execute sequentially with validation at each step. Rollback available if failures occur.

**Workflow Names**:
- restart-bot: "Safely Restart Trading Bot"
- update-targets: "Update Performance Targets"
- export-logs: "Export Trading Logs"
- check-health: "Comprehensive Health Check"

**Status Messages**:
- WORKFLOW_QUEUED: "Workflow queued for execution"
- WORKFLOW_RUNNING: "Executing step {current} of {total}"
- WORKFLOW_VALIDATING: "Validating step '{step_name}'"
- WORKFLOW_COMPLETE: "All steps completed successfully"
- WORKFLOW_FAILED: "Step '{step_name}' failed: {reason}"
- WORKFLOW_ROLLED_BACK: "Workflow reverted due to failure"

**Step Status Labels**:
- PENDING: "Waiting to execute"
- VALIDATING: "Checking prerequisites"
- EXECUTING: "In progress"
- COMPLETED: "Successfully finished"
- FAILED: "Execution failed"
- SKIPPED: "Skipped due to previous failure"

## Screen: Error Inspector

**Heading**: Semantic Error Log
**Subheading**: Browse and analyze errors with LLM-friendly context
**CTA Primary**: View Details
**CTA Secondary**: Export Errors
**Help Text**: Errors logged with semantic fields (cause, impact, remediation) for easier diagnosis

**Column Headers**:
- Timestamp: "When error occurred"
- Error Type: "Category (trading, api, config, system)"
- Message: "Brief description"
- Impact: "Severity and affected operations"
- Status: "Resolved/Unresolved"

**Error Type Labels**:
- TRADING_ERROR: "Trading operation failed"
- API_ERROR: "External API call failed"
- CONFIG_ERROR: "Configuration issue"
- SYSTEM_ERROR: "Internal system error"
- VALIDATION_ERROR: "Input validation failed"

**Detail Panel Labels**:
- Error Code: "Unique error identifier"
- Cause: "Root cause explanation"
- Impact: "What was affected"
- Remediation: "Steps to resolve"
- Context: "Related entities (trade_id, symbol, etc.)"
- Stack Trace: "Technical details (expandable)"

**Empty States**:
- NO_ERRORS: "No errors logged in selected time range. Bot is operating normally."

**Error Messages**:
- LOG_FETCH_FAILED: "Unable to load error logs. Check file permissions and log file location."
- EXPORT_FAILED: "Error export failed. Ensure sufficient disk space and write permissions."

## Natural Language Command Examples

**Command**: "show today's performance"
**Response Format**:
```
Today's Performance Summary:
- Total P&L: $125.50 (+2.3%)
- Win Rate: 66.7% (4 wins, 2 losses)
- Avg Risk-Reward: 1.8:1
- Trades Executed: 6
- Current Streak: 2 wins
```

**Command**: "what positions are open"
**Response Format**:
```
Open Positions (3):
1. AAPL: 10 shares @ $150.00, Current: $152.50, P&L: +$25.00 (+1.67%)
2. MSFT: 5 shares @ $300.00, Current: $298.00, P&L: -$10.00 (-0.67%)
3. GOOGL: 8 shares @ $125.00, Current: $127.50, P&L: +$20.00 (+2.00%)

Total Unrealized P&L: +$35.00
```

**Command**: "check bot health"
**Response Format**:
```
Bot Health Status: HEALTHY ✓

System Status:
- Trading: Active
- Circuit Breaker: Not tripped
- API Connection: Connected
- Last Trade: 5 minutes ago
- Buying Power: $5,432.10

No issues detected.
```

**Command**: "show recent errors"
**Response Format**:
```
Recent Errors (Last 3):
1. [10:23 AM] API_ERROR: Rate limit exceeded on market data API
   → Impact: Order delayed by 2 seconds
   → Remediation: Retry successful, no action needed

2. [09:45 AM] VALIDATION_ERROR: Invalid quantity for order
   → Impact: Order rejected
   → Remediation: Fixed order size, resubmitted successfully

3. [09:12 AM] TRADING_ERROR: Insufficient buying power
   → Impact: Order canceled
   → Remediation: Waiting for settled funds
```

## API Error Response Format

```json
{
  "error_code": "BOT_001",
  "error_type": "INSUFFICIENT_BUYING_POWER",
  "message": "Cannot place order: insufficient buying power",
  "cause": "Requested trade requires $500.00 but only $350.00 available",
  "impact": "Order was not submitted to market",
  "remediation": "Wait for pending trades to settle or reduce position size",
  "context": {
    "symbol": "AAPL",
    "requested_amount": 500.00,
    "available_amount": 350.00,
    "order_id": null
  },
  "timestamp": "2025-10-24T20:30:15Z"
}
```
