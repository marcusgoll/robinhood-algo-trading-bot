# Quickstart: 019-status-dashboard

## Prerequisites

- Trading bot installed and configured
- Authenticated session (credentials configured)
- Account data module operational
- Trade logging enabled (optional but recommended for metrics)

## Scenario 1: Launch Dashboard (First-Time User)

**Goal**: Start the dashboard and view real-time trading data

```bash
# Ensure bot is authenticated (one-time setup)
# This is handled by main bot authentication flow

# Launch dashboard (from repo root)
python -m trading_bot.dashboard

# Expected output:
# Trading dashboard started
# Controls: type R/E/H/Q then press Enter • Refreshed automatically every 5s
#
# ━━━━ Account Status ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Buying Power:  $10,000.00
# Balance:       $12,345.67 (Cash: $5,000.00)
# Day Trades:    0 / 3
# Last Updated:  2025-01-15 14:30:15 UTC
#
# ━━━━ Open Positions ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Symbol  Qty   Entry    Current   P&L $    P&L %
# AAPL    10    150.00   155.00    +50.00   +3.33%  [green]
# TSLA    5     200.00   195.00    -25.00   -2.50%  [red]
#
# ━━━━ Performance Metrics ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Win Rate:       65.0%
# Avg R:R:        2.5
# Total P&L:      +$125.00 (Realized: +$100.00, Unrealized: +$25.00)
# Streak:         3 WIN
# Trades Today:   5
# Sessions:       12
# Max Drawdown:   -$50.00
#
# Market Status: OPEN 🟢
# Refreshing in 5s...
```

**Validation**:
- ✅ Dashboard renders within 2 seconds (NFR-001)
- ✅ Account status shows buying power, balance, day trades (FR-001)
- ✅ Positions table displays with color-coded P&L (FR-002, FR-008)
- ✅ Performance metrics calculated correctly (FR-003)
- ✅ Auto-refresh indicator appears (FR-004)

---

## Scenario 2: Interactive Controls

**Goal**: Use keyboard commands to interact with dashboard

### Manual Refresh (R key)
```bash
# While dashboard is running, type 'R' and press Enter
R

# Expected output:
# Manual refresh queued (R)
# [Dashboard refreshes immediately, bypassing 5s timer]
```

### Export Summary (E key)
```bash
# While dashboard is running, type 'E' and press Enter
E

# Expected output:
# Exported dashboard summary
#   JSON: logs/dashboard-export-2025-01-15-143045.json
#   Markdown: logs/dashboard-export-2025-01-15-143045.md
```

### Show Help (H key)
```bash
# While dashboard is running, type 'H' and press Enter
H

# Expected output:
# Dashboard Controls
#   R — Manual refresh (bypass timer)
#   E — Export JSON + Markdown summary to logs/
#   Q — Quit dashboard
#   H — Show this help
```

### Quit Dashboard (Q key)
```bash
# While dashboard is running, type 'Q' and press Enter
Q

# Expected output:
# Quit requested (Q)
# Dashboard stopped
```

**Validation**:
- ✅ R key triggers immediate refresh (FR-006)
- ✅ E key generates export files (FR-006, FR-007)
- ✅ H key displays help overlay (FR-006)
- ✅ Q key exits cleanly (FR-006)

---

## Scenario 3: Configure Performance Targets

**Goal**: Set performance targets for comparison

### Create targets file
```bash
# Create config directory if not exists
mkdir -p config

# Create dashboard-targets.yaml
cat > config/dashboard-targets.yaml <<EOF
# Dashboard Performance Targets
# These values are compared against actual metrics in dashboard

win_rate_target: 60.0                # Target win rate percentage
daily_pl_target: 200.00              # Target daily profit/loss in dollars
trades_per_day_target: 5             # Target number of trades per day
max_drawdown_target: -100.00         # Maximum acceptable drawdown (negative value)
avg_risk_reward_target: 2.0          # Optional: Target R:R ratio
EOF

# Launch dashboard to see target comparison
python -m trading_bot.dashboard

# Expected output (in Performance Metrics section):
# Win Rate:       65.0% [Target: 60.0%] ✓  [green]
# Avg R:R:        2.5   [Target: 2.0]   ✓  [green]
# Total P&L:      +$125.00 [Target: $200.00] ✗  [red]
```

**Validation**:
- ✅ Targets loaded from config/dashboard-targets.yaml (FR-005)
- ✅ Actual vs target comparison displayed (FR-005)
- ✅ Variance indicators shown (✓/✗ with color coding) (FR-008)

---

## Scenario 4: Inspect Export Files

**Goal**: Verify exported data for record-keeping and analysis

### Export dashboard snapshot
```bash
# Launch dashboard
python -m trading_bot.dashboard

# Press 'E' key to export
E

# Inspect JSON export (machine-readable)
cat logs/dashboard-export-2025-01-15-143045.json | jq .

# Expected JSON structure:
# {
#   "generated_at": "2025-01-15T14:30:45Z",
#   "account_status": {
#     "buying_power": "10000.00",
#     "account_balance": "12345.67",
#     "cash_balance": "5000.00",
#     "day_trade_count": 0,
#     "last_updated": "2025-01-15T14:30:15Z"
#   },
#   "positions": [
#     {
#       "symbol": "AAPL",
#       "quantity": 10,
#       "entry_price": "150.00",
#       "current_price": "155.00",
#       "unrealized_pl": "50.00",
#       "unrealized_pl_pct": "3.33"
#     }
#   ],
#   "performance_metrics": {
#     "win_rate": 65.0,
#     "avg_risk_reward": 2.5,
#     "total_pl": "125.00",
#     "streak": {"count": 3, "type": "WIN"},
#     "trades_today": 5,
#     "session_count": 12
#   },
#   "market_status": "OPEN",
#   "warnings": []
# }

# Inspect Markdown export (human-readable)
cat logs/dashboard-export-2025-01-15-143045.md

# Expected Markdown structure:
# # Dashboard Export
# **Generated**: 2025-01-15 14:30:45 UTC
# **Market Status**: OPEN
#
# ## Account Status
# - Buying Power: $10,000.00
# - Balance: $12,345.67 (Cash: $5,000.00)
# - Day Trades: 0 / 3
#
# ## Open Positions
# | Symbol | Qty | Entry | Current | P&L $ | P&L % |
# |--------|-----|-------|---------|-------|-------|
# | AAPL   | 10  | 150.00 | 155.00 | +50.00 | +3.33% |
#
# ## Performance Metrics
# - Win Rate: 65.0%
# - Avg R:R: 2.5
# - Total P&L: +$125.00
# - Streak: 3 WIN
# - Trades Today: 5
# - Sessions: 12
```

**Validation**:
- ✅ JSON file contains complete snapshot data (FR-007)
- ✅ Markdown file provides human-readable summary (FR-007)
- ✅ Export event logged for audit trail (NFR-007)

---

## Scenario 5: Handle Edge Cases

### No open positions
```bash
# Launch dashboard when no positions are open
python -m trading_bot.dashboard

# Expected output (in Open Positions section):
# ━━━━ Open Positions ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# No open positions
```

### No trades today
```bash
# Launch dashboard before any trades executed
python -m trading_bot.dashboard

# Expected output (in Performance Metrics section):
# Trades Today:   0
# [Other metrics show cumulative stats from historical trades]
```

### Missing trade log
```bash
# Launch dashboard when trade log file doesn't exist
python -m trading_bot.dashboard

# Expected output (in warnings):
# ⚠️  Trade log not found, performance metrics unavailable
# [Account status and positions still displayed]
```

### Stale account data
```bash
# Launch dashboard when account data is >60 seconds old
# (Simulated by network delay or API throttling)
python -m trading_bot.dashboard

# Expected output (in warnings):
# ⚠️  Data may be stale: last updated 75s ago (TTL=60s)
# [Dashboard continues to display cached data]
```

**Validation**:
- ✅ Graceful degradation on missing data (FR-015, FR-016)
- ✅ Warnings displayed prominently (FR-010)
- ✅ Dashboard remains functional (NFR-002)

---

## Scenario 6: Troubleshooting

### Dashboard won't start
```bash
# Check authentication status
python -m trading_bot.auth.check_auth

# If authentication failed, re-authenticate
python -m trading_bot.auth.login

# Retry dashboard launch
python -m trading_bot.dashboard
```

### Performance metrics show 0.0
```bash
# Verify trade log exists
ls -lh logs/*.jsonl

# Check trade log format
head -1 logs/2025-01-15.jsonl | jq .

# Expected: Valid JSON with required fields (symbol, action, price, timestamp)
```

### Export files not found
```bash
# Check logs directory exists
ls -ld logs/

# Check file permissions
ls -lh logs/dashboard-export-*.json

# Verify export event logged
grep "dashboard.exported" logs/dashboard-events.log
```

### Dashboard refresh slow (>500ms)
```bash
# Run performance tests
pytest tests/performance/test_dashboard_performance.py -v

# Check network latency to Robinhood API
# (Dashboard inherits account data cache, should be <500ms)

# Verify trade log size (large logs may slow down parsing)
wc -l logs/*.jsonl
```

**Validation**:
- ✅ Authentication issues identified and resolved
- ✅ Trade log format validated
- ✅ Export file permissions checked
- ✅ Performance benchmarks executed (NFR-001)

---

## Scenario 7: Automation & Scripting

### Daily export automation (cron job)
```bash
# Create export script
cat > scripts/daily_dashboard_export.sh <<'EOF'
#!/bin/bash
# Export dashboard snapshot at market close (4:00 PM ET)

set -e

# Activate virtual environment
source .venv/bin/activate

# Launch dashboard, wait 10s for initial refresh, then export and quit
(
  echo "E"  # Export
  sleep 2
  echo "Q"  # Quit
) | timeout 15s python -m trading_bot.dashboard

echo "Daily dashboard export completed: $(date)"
EOF

chmod +x scripts/daily_dashboard_export.sh

# Schedule cron job (run at 4:05 PM ET daily)
crontab -e
# Add line: 5 16 * * 1-5 cd /path/to/trading_bot && ./scripts/daily_dashboard_export.sh
```

### Parse exported JSON for analysis
```bash
# Extract today's total P&L from latest export
jq -r '.performance_metrics.total_pl' logs/dashboard-export-*.json | tail -1

# Calculate weekly win rate from all exports
jq -r '.performance_metrics.win_rate' logs/dashboard-export-*.json | \
  awk '{sum+=$1; count++} END {print sum/count "%"}'

# List all exported snapshots with timestamps
jq -r '"\(.generated_at) - Total P&L: \(.performance_metrics.total_pl)"' \
  logs/dashboard-export-*.json
```

**Validation**:
- ✅ Dashboard supports non-interactive automation
- ✅ Export files parseable by standard tools (jq, awk)
- ✅ Cron scheduling tested

---

## Scenario 8: Development & Testing

### Run unit tests
```bash
# Run all dashboard unit tests
pytest tests/unit/test_dashboard/ -v

# Run specific test module
pytest tests/unit/test_dashboard/test_dashboard_orchestration.py -v

# Check code coverage
pytest tests/unit/test_dashboard/ --cov=src.trading_bot.dashboard --cov-report=term-missing

# Expected: ≥90% coverage (NFR-006)
```

### Run integration tests
```bash
# Run E2E dashboard integration tests
pytest tests/integration/dashboard/ -v

# Run error handling tests
pytest tests/integration/dashboard/test_dashboard_error_handling.py -v
```

### Run performance benchmarks
```bash
# Run performance tests (startup, refresh, export, memory)
pytest tests/performance/test_dashboard_performance.py -v

# Expected results:
# - Startup time: <2s (NFR-001)
# - Refresh cycle: <500ms (NFR-001)
# - Export generation: <1s
# - Memory footprint: <50MB (NFR-008)
```

### Type checking
```bash
# Run mypy type checker (Constitution §Code_Quality)
mypy src/trading_bot/dashboard/

# Expected: No type errors
```

### Linting
```bash
# Run ruff linter
ruff check src/trading_bot/dashboard/

# Expected: No linting errors
```

**Validation**:
- ✅ All tests pass (Constitution §Testing_Requirements)
- ✅ Code coverage ≥90% (NFR-006)
- ✅ Performance benchmarks meet targets (NFR-001, NFR-008)
- ✅ Type hints verified (NFR-005)
- ✅ Code quality checks pass (Constitution §Code_Quality)

---

## Common Pitfalls

1. **Dashboard hangs on startup**
   - Cause: Network timeout or authentication failure
   - Fix: Check internet connection, re-authenticate, verify API credentials

2. **Metrics show 0.0 despite trades**
   - Cause: Trade log file missing or corrupted
   - Fix: Verify logs/*.jsonl exists and contains valid JSON

3. **Positions table empty despite open positions**
   - Cause: Account data cache stale or API error
   - Fix: Press 'R' for manual refresh, check account-data-module logs

4. **Export fails with permission error**
   - Cause: logs/ directory not writable
   - Fix: `chmod 755 logs/` or run dashboard with appropriate permissions

5. **Color coding not visible**
   - Cause: Terminal doesn't support ANSI colors
   - Fix: Use modern terminal (iTerm2, Windows Terminal, etc.)

---

## Quick Reference

**Keyboard Commands** (type letter + Enter):
- `R` — Manual refresh (bypass 5s timer)
- `E` — Export snapshot (JSON + Markdown)
- `H` — Show help
- `Q` — Quit dashboard

**File Locations**:
- Trade logs: `logs/YYYY-MM-DD.jsonl`
- Exports: `logs/dashboard-export-YYYY-MM-DD-HHmmss.{json,md}`
- Targets config: `config/dashboard-targets.yaml`
- Source code: `src/trading_bot/dashboard/`
- Tests: `tests/{unit,integration,performance}/dashboard/`

**Performance Targets** (from NFRs):
- Startup: <2s
- Refresh: <500ms
- Export: <1s
- Memory: <50MB
- Coverage: ≥90%

**Dependencies**:
- account-data-module (required)
- performance-tracking (optional, for TradeQueryHelper)
- trade-logging (optional, for metrics)

**Support**:
- Logs: Check `logs/dashboard-events.log` for audit trail
- Issues: Review `specs/019-status-dashboard/error-log.md`
- Spec: See `specs/019-status-dashboard/spec.md`
