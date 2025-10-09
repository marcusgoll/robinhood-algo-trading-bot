# Feature: status-dashboard

## Overview
CLI status dashboard providing real-time account monitoring and performance tracking for the trading bot. Displays current positions, P&L, trades executed, buying power, active orders, and comprehensive performance metrics. Enables quick visual assessment of trading session health and progress against targets.

## Research Findings

### Finding 1: Dependencies Shipped
- **account-data-module**: ✅ SHIPPED (provides positions, P&L, buying power, account balance)
  - Source: specs/account-data-module/spec.md
  - Available data: `get_positions()`, `get_buying_power()`, `get_account_balance()`, `get_day_trade_count()`
- **trade-logging**: ✅ SHIPPED (provides structured trade history)
  - Source: specs/trade-logging/spec.md
  - Available data: `logs/trades-structured.jsonl` with win rate, avg P/L, strategy performance

### Finding 2: Constitution Alignment
- Source: .spec-flow/memory/constitution.md
- **§Audit_Everything**: Dashboard must display audit trail visibility
- **§Risk_Management**: Show position sizes, day trade count, circuit breaker status
- **§Safety_First**: Visual indicators for risk limits approaching thresholds
- **§Data_Integrity**: All timestamps UTC, real-time updates with staleness indicators

### Finding 3: CLI Dashboard Patterns
- Research: Common CLI dashboard tools (htop, k9s, btop)
- Pattern: Single-screen view with sections, real-time auto-refresh
- Pattern: Color-coded status (green=good, yellow=warning, red=critical)
- Pattern: Compact metrics display with units (e.g., "$5,234.56" not "5234.5567...")

### Finding 4: Performance Metrics Calculation
- Source: trade-logging spec and account-data-module
- **Win rate**: % of trades with profit (from trades-structured.jsonl)
- **Avg R:R**: Average reward-to-risk ratio (target/stop_loss from risk_params)
- **Total P&L**: Sum of realized P&L from closed trades + unrealized P&L from positions
- **Current streak**: Consecutive wins or losses
- **Trades today**: Count of trades with today's date
- **Session count**: Number of trading sessions (days with >0 trades)

### Finding 5: Data Refresh Strategy
- Real-time updates require polling account-data-module and reading trade logs
- Cache TTL in account-data-module: 60 seconds (buying power, positions, balance)
- Trade logs: Read-only, no cache needed (file access <10ms)
- Dashboard refresh rate: 5 seconds (balance API cache efficiency vs real-time feel)

## Feature Classification
- UI screens: false (CLI-only, no web UI)
- Improvement: true (improves visibility into trading operations)
- Measurable: true (reduces time to assess session health)
- Deployment impact: false (pure Python addition, no platform changes)

## System Components Analysis
Not applicable (CLI-only, no reusable UI components)

## Key Decisions

1. **CLI Framework**: Use `rich` library for formatted console output
   - Rationale: Production-grade CLI dashboards (used by many popular tools)
   - Features: Tables, panels, live refresh, color support, layout management

2. **Refresh Strategy**: 5-second polling loop with manual refresh option
   - Rationale: Balances real-time feel with API cache efficiency
   - Account data: Cached for 60s, dashboard refresh triggers cache check
   - Trade data: Read from disk on each refresh (<10ms)

3. **Display Layout**: Three-section design (Account Status / Positions / Performance)
   - Section 1: Account snapshot (buying power, balance, day trades, timestamp)
   - Section 2: Current positions (symbol, qty, entry, current, P&L, P&L%)
   - Section 3: Performance metrics (win rate, avg R:R, total P&L, streak, trades today, sessions)

4. **Export Format**: Daily summary as JSON + Markdown
   - JSON: Machine-readable for analysis (`dashboard-export-YYYY-MM-DD.json`)
   - Markdown: Human-readable report (`dashboard-export-YYYY-MM-DD.md`)
   - Target comparison: Include targets and actual values with variance

5. **Target Comparison**: Load targets from config file
   - File: `config/dashboard-targets.yaml`
   - Metrics: win_rate_target, daily_pl_target, trades_per_day_target, max_drawdown_target
   - Display: Show actual vs target with color-coded variance (green if meeting, red if not)

## Checkpoints
- Phase 0 (Specification): 2025-10-09
- Phase 1 (Planning): 2025-10-09
  - Artifacts: plan.md, error-log.md
  - Research decisions: 6 (CLI framework, data sources, refresh strategy, market hours, config, export format)
  - Reusable components: 5 (AccountData, TradeQueryHelper, TradeRecord, time_utils, logging pattern)
  - New components: 4 (dashboard.py, display_renderer.py, metrics_calculator.py, export_generator.py)
  - Migration required: No

## Phase 1 Summary
Research depth: Comprehensive analysis of existing modules
Key decisions: 6 architectural decisions documented
Components to reuse: 5 existing modules identified
New components: 4 modules to create
Migration needed: No

## Last Updated
2025-10-09T08:30:00Z
