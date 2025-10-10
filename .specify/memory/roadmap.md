# Robinhood Trading Bot Roadmap

**Last updated**: 2025-10-10 (status-dashboard shipped)
**Constitution**: v1.0.0

> Features from brainstorm → shipped. Managed via `/roadmap`

## Shipped

<!-- Released and operational -->

### project-setup
- **Title**: Project setup
- **Area**: infra
- **Role**: all
- **Date**: 2025-10-07
- **Release**: v0.1.0 - Initial project structure with Constitution v1.0.0
- **Delivered**:
  - Created folder structure (src/, config/, logs/, data/)
  - requirements.txt with robin-stocks and pyotp dependencies
  - .gitignore for credentials

### environment-config
- **Title**: Environment configuration
- **Area**: infra
- **Role**: all
- **Intra**: Yes
- **Date**: 2025-10-07
- **Commit**: 0b0833b
- **Delivered**:
  - .env.example with credentials (username, password, MFA secret, device token)
  - config.example.json with trading parameters (risk limits, hours, phase progression)
  - Config.from_env_and_json() dual-source loader
  - test_config.py verification script

### configuration-validator
- **Title**: Configuration validator
- **Area**: infra
- **Role**: all
- **Intra**: Yes
- **Date**: 2025-10-07
- **Commit**: 7d269ca
- **Delivered**:
  - ConfigValidator class with credential, config, and safety checks
  - 15 unit tests covering all validation scenarios
  - validate_startup.py pre-deploy validation script
  - Blocks startup if validation fails (§Pre_Deploy)

### mode-switcher
- **Title**: Paper/live trading mode switcher
- **Area**: infra
- **Role**: all
- **Intra**: Yes
- **Date**: 2025-10-07
- **Commit**: fb93eea
- **Delivered**:
  - ModeSwitcher class for mode management
  - Phase-based safety controls (blocks live in experience phase)
  - Visual mode banners (paper vs live)
  - Mode indicators ([PAPER] vs [⚠️  LIVE ⚠️])
  - 20 unit tests covering all scenarios

### logging-system
- **Title**: Structured logging system
- **Area**: infra
- **Role**: all
- **Intra**: Yes
- **Date**: 2025-10-07
- **Commit**: 5ba3ca6
- **Delivered**:
  - TradingLogger class with structured logging
  - Separate log files: trading_bot.log, trades.log, errors.log (§Audit_Everything)
  - UTC timestamps on all logs (§Data_Integrity)
  - Automatic log rotation (10MB max, 5 backups)
  - Convenience functions: log_trade(), log_error()
  - 25 unit tests covering all scenarios

### safety-checks
- **Title**: Pre-trade safety checks & risk management
- **Area**: api
- **Role**: all
- **Intra**: No
- **Date**: 2025-10-08
- **Commit**: 7ce2d5c
- **Delivered**:
  - SafetyChecks module with comprehensive pre-trade validation
  - Buying power validation (blocks insufficient funds)
  - Trading hours enforcement (7am-10am EST with DST support)
  - Daily loss circuit breaker (3% threshold)
  - Consecutive loss detection (3 losses triggers halt)
  - Position size calculator (5% portfolio max)
  - Duplicate order prevention
  - Circuit breaker management (trigger/reset)
  - Fail-safe error handling (corrupt state trips breaker)
  - Input validation (ValueError on invalid trades)
  - Integrated into TradingBot.execute_trade()
  - 16 unit tests + 11 integration tests (100% pass rate)
  - 85.86% code coverage
  - Full Constitution v1.0.0 compliance

### authentication-module
- **Title**: Robinhood authentication with MFA
- **Area**: api
- **Role**: all
- **Intra**: No
- **Date**: 2025-01-08
- **Release**: v1.0.0 - Full authentication with MFA, session management, token refresh
- **Spec**: specs/authentication-module/
- **Delivered**:
  - RobinhoodAuth service with login/logout/refresh
  - MFA support via pyotp TOTP
  - Device token support (skip MFA)
  - Session persistence (.robinhood.pickle with 600 permissions)
  - Token refresh on 401 errors
  - Exponential backoff retry logic (1s, 2s, 4s)
  - Corrupt pickle fallback to re-authentication
  - Credential masking in logs (§Security compliance)
  - Bot integration (start/stop with auth)
  - 16 unit tests + 3 integration tests (100% pass rate)
  - Security audit passed (no HIGH/CRITICAL issues)
  - Full Constitution v1.0.0 compliance
  - Documentation: spec, plan, tasks, security-audit, deployment guide

### account-data-module
- **Title**: Account data fetching
- **Area**: api
- **Role**: all
- **Intra**: No
- **Date**: 2025-01-08
- **Release**: v1.1.0 - Real-time account data with TTL caching
- **Spec**: specs/account-data-module/
- **Delivered**:
  - AccountData service with buying power, positions, balance, day trade count
  - TTL-based caching (60s volatile, 300s stable)
  - Exponential backoff retry logic (1s, 2s, 4s)
  - Position dataclass with automatic P&L calculation
  - TradingBot integration (get_buying_power replacement)
  - SafetyChecks integration (real buying power validation)
  - Cache invalidation after trades
  - 17 unit tests (100% pass rate)
  - 90.24% test coverage (exceeds 90% target)
  - Full Constitution v1.0.0 compliance (§Security, §Audit_Everything, §Risk_Management)
  - Production ready with linting fixes applied
  - Backward compatible (fallback to $10k mock)
  - Documentation: spec, plan, tasks, optimization-report, code-review-report

### error-handling-framework
- **Title**: API error handling framework
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Date**: 2025-10-08
- **Commit**: 7e11412
- **Spec**: specs/error-handling-framework/
- **Delivered**:
  - RetryPolicy dataclass with default/aggressive/conservative presets and validation
  - `with_retry` decorator with jittered exponential backoff, RateLimitError support, and circuit breaker telemetry
  - CircuitBreaker singleton coordinating failure thresholds across services
  - Comprehensive unit suite (`tests/unit/test_error_handling/*`) plus market data integration coverage

### market-data-module
- **Title**: Market data and trading hours
- **Area**: api
- **Role**: all
- **Intra**: No
- **Date**: 2025-10-08
- **Commit**: 98a88b1
- **Spec**: specs/market-data-module/
- **Delivered**:
  - MarketDataService with quote, historical OHLCV, and market status endpoints guarded by retry policy
  - Quote/MarketStatus/MarketDataConfig dataclasses with configurable trading window enforcement
  - Validation stack for prices, timestamps, trading hours, and historical continuity
  - Unit + integration tests (tests/unit/test_market_data/*, tests/integration/test_market_data_integration.py)

### startup-sequence
- **Title**: Bot startup and initialization
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Date**: 2025-10-08
- **Commit**: b5a73f4
- **Spec**: specs/startup-sequence/
- **Delivered**:
  - StartupOrchestrator coordinating 8-step initialization with StartupStep/StartupResult dataclasses
  - `--dry-run` and `--json` CLI flows with structured exit codes for automation
  - Dedicated startup logger writing to `logs/startup.log` with Constitution-compliant messaging
  - Unit/integration coverage (tests/unit/test_startup.py, tests/integration/test_startup_flow.py) including failure diagnostics

### credentials-manager
- **Title**: Secure credentials management
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Date**: 2025-10-09
- **Commit**: fe4d55b
- **Spec**: specs/credentials-manager/
- **Delivered**:
  - Credential masking helpers for username, password, MFA secret, and device token (`src/trading_bot/utils/security.py`, tests/unit/test_utils/test_security.py)
  - ConfigValidator MFA format enforcement with base32 + length checks (tests/unit/test_validator.py:T008-T010)
  - RobinhoodAuth device-token reuse with MFA fallback and .env persistence (tests/integration/test_credentials_flow.py)
  - Full task suite complete (specs/credentials-manager/NOTES.md#L341) with supporting docs, contracts, and analysis reports

### trade-logging
- **Title**: Trade history database/CSV
- **Area**: infra
- **Role**: all
- **Intra**: Yes
- **Date**: 2025-10-09
- **Commit**: 7c685bd
- **Spec**: specs/trade-logging/
- **Delivered**:
  - TradeRecord dataclass (27 audited fields) with validation and JSON serialization helpers
  - StructuredTradeLogger writing daily JSONL ledgers with thread-safe rotation
  - TradeQueryHelper for date/symbol filtering, analytics, and win-rate calculations
  - Smoke, unit, and integration test suite plus review artifacts (specs/trade-logging/, tests/{unit,integration,smoke}/test_trade_logging_*.py)

### status-dashboard
- **Title**: CLI status dashboard & performance metrics
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Date**: 2025-10-10
- **Commit**: 73b85f6
- **Spec**: specs/status-dashboard/
- **Delivered**:
  - Dashboard orchestrator loop with Rich-based live display and keyboard controls (R/E/H/Q)
  - MetricsCalculator, ExportGenerator, and DashboardTargets for targets/exports and analytics
  - Usage telemetry to `logs/dashboard-usage.jsonl` plus JSON/Markdown export pipeline
  - Example runner and unit coverage (`examples/run_dashboard.py`, tests/unit/test_dashboard/test_dashboard_orchestration.py)

## In Progress

<!-- Currently implementing -->

### health-check
- **Title**: Session health monitoring
- **Area**: api
- **Role**: all
- **Intra**: Yes
- **Branch**: health-check
- **Updated**: 2025-10-10
- **Impact**: 4 | **Effort**: 2 | **Confidence**: 0.9 | **Score**: 1.80
- **Progress**:
  - SessionHealthMonitor + HealthCheckLogger implemented (`src/trading_bot/health/`)
  - TradingBot integrates pre-trade health checks and periodic monitoring
  - Startup orchestrator bootstraps health monitor (`component_states["trading_bot"].health_monitor`)
- **Remaining**:
  - Integration tests covering bot startup/run with mocked robin_stocks
  - CLI/config documentation updates explaining health-check usage
  - Confirm log rotation and dashboard surfacing of health metrics

## Next

<!-- Top 5-10 prioritized features (sorted by score) -->

## Later

<!-- Future features (10-20 items, sorted by score) -->

## Backlog

<!-- All ideas sorted by ICE score (Impact × Confidence ÷ Effort) -->
<!-- Higher score = higher priority -->

### order-management
- **Title**: Order management foundation
- **Area**: api
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 3 | **Confidence**: 0.8 | **Score**: 1.33
- **Requirements**:
  - Place limit buy orders with offset
  - Place limit sell orders with offset
  - Cancel all open orders function
  - Get order status and fill info
  - [UNBLOCKED: authentication-module shipped, safety-checks shipped]

### performance-tracking
- **Title**: Performance tracking and analytics
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Impact**: 4 | **Effort**: 2 | **Confidence**: 1.0 | **Score**: 2.00
- **Requirements**:
  - Win/loss ratio calculator (daily/weekly/monthly)
  - Track total wins vs losses
  - Display current streak (wins/losses)
  - Alert when below target win rate
  - Average profit per winning trade
  - Average loss per losing trade
  - Calculate and display current risk-reward ratio
  - Alert if R:R falls below 1:1
  - Daily trade log with timestamps and P&L
  - [UNBLOCKED: trade-logging shipped (2025-10-09)]
  - [PIGGYBACK: extends trade-logging with analytics]
  - [MERGED: win-rate-tracking, avg-win-loss-calculator]

### stock-screener
- **Title**: Stock screener and filtering
- **Area**: api
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 3 | **Confidence**: 0.8 | **Score**: 1.33
- **Requirements**:
  - Filter by price range ($2-$20)
  - Relative volume filter (5x+ average)
  - Float size filter (under 20M shares)
  - Daily performance filter (10%+ movers)
  - [UNBLOCKED: market-data-module shipped (2025-10-08)]

### momentum-detection
- **Title**: Momentum and catalyst detection
- **Area**: api
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 3 | **Confidence**: 0.7 | **Score**: 1.17
- **Requirements**:
  - Identify stocks with breaking news catalysts
  - Track pre-market movers
  - Scan for bull flag patterns
  - [BLOCKED: technical-indicators; UNBLOCKED: market-data-module shipped (2025-10-08)]

### technical-indicators
- **Title**: Technical indicators module
- **Area**: api
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 3 | **Confidence**: 0.9 | **Score**: 1.50
- **Requirements**:
  - **VWAP monitor**: Fetch current VWAP for symbol
  - Verify price is above VWAP for longs
  - Reject entries below VWAP
  - Use VWAP as dynamic support level
  - Update VWAP intraday
  - **EMA calculator**: Calculate 9-period and 20-period EMAs
  - Detect EMA crossovers
  - Identify when price near 9 EMA (optimal entry)
  - Visualize trend angle from EMAs
  - **MACD indicator**: Calculate MACD line and signal line
  - Verify MACD is positive for longs
  - Detect divergence (lines moving apart)
  - Trigger exit when MACD crosses negative
  - [UNBLOCKED: market-data-module shipped (2025-10-08)]
  - [MERGED: vwap-monitor, ema-calculator, macd-indicator]

### entry-logic-bull-flag
- **Title**: Bull flag entry logic
- **Area**: strategy
- **Role**: all
- **Intra**: No
- **Impact**: 4 | **Effort**: 2 | **Confidence**: 0.8 | **Score**: 1.60
- **Requirements**:
  - **Bull flag detector**: Identify strong upward move, detect 1-3 red candle pullback
  - Verify pullback is less than 1/3 of move
  - Confirm orderly pattern (no gaps/wicks)
  - Flag valid setups for entry
  - **Breakout entry trigger**: Monitor for first green candle after pullback
  - Detect new high above pullback range
  - Verify volume confirmation
  - Auto-place limit order at breakout level
  - [BLOCKED: technical-indicators, momentum-detection]
  - [MERGED: bull-flag-detector, breakout-entry-trigger]

### stop-loss-automation
- **Title**: Automated stop loss and targets
- **Area**: api
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 2 | **Confidence**: 0.9 | **Score**: 2.25
- **Requirements**:
  - **Stop loss calculator**: Identify pullback low as invalidation point
  - Auto-place stop at pullback low
  - Calculate position size based on stop distance
  - Adjust for account risk limit
  - **Risk-reward target setter**: Calculate 2:1 target from entry and stop
  - Set limit sell order at target price
  - Track progress to target
  - Auto-adjust if stop moves
  - Auto-exit on target hit (§Risk_Management)
  - [BLOCKED: order-management]
  - [MERGED: stop-loss-calculator, risk-reward-target-setter]

### order-execution-enhanced
- **Title**: Enhanced order execution
- **Area**: api
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 2 | **Confidence**: 0.9 | **Score**: 2.25
- **Requirements**:
  - Limit order placement (ASK + offset)
  - Avoid market orders (§Risk_Management)
  - Position exit at BID - offset
  - [BLOCKED: order-management]

### emotional-controls
- **Title**: Emotional control mechanisms
- **Area**: strategy
- **Role**: all
- **Intra**: No
- **Impact**: 4 | **Effort**: 2 | **Confidence**: 0.8 | **Score**: 1.60
- **Requirements**:
  - Detect significant loss (define threshold)
  - Auto-reduce position size to 25% of normal
  - Require manual reset after recovery period
  - Log all size adjustments
  - Force simulator mode after daily loss limit hit (§Safety_First)
  - [BLOCKED: safety-checks, mode-switcher]
  - [MERGED: position-size-reducer]

### profit-goal-manager
- **Title**: Daily profit goal management
- **Area**: strategy
- **Role**: all
- **Intra**: No
- **Impact**: 4 | **Effort**: 2 | **Confidence**: 0.8 | **Score**: 1.60
- **Requirements**:
  - Set daily profit target
  - Track progress to goal
  - Detect when half of profit given back
  - Trigger exit rule when threshold hit
  - Reset daily at market open (§Risk_Management)
  - [BLOCKED: performance-tracking, safety-checks]

### support-resistance-mapping
- **Title**: Support/resistance zone mapping
- **Area**: strategy
- **Role**: all
- **Intra**: No
- **Impact**: 4 | **Effort**: 3 | **Confidence**: 0.7 | **Score**: 0.93
- **Requirements**:
  - Identify daily/4H support and resistance levels
  - Track rejection and breakout patterns
  - [BLOCKED: technical-indicators]

### trade-management-rules
- **Title**: Trade management rules
- **Area**: strategy
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 2 | **Confidence**: 0.8 | **Score**: 2.00
- **Requirements**:
  - Prevent early break-even stops
  - Add to winning positions (scaling in)
  - Cut losing trades early (§Risk_Management)
  - [BLOCKED: order-management]

### level2-integration
- **Title**: Level 2 order flow integration
- **Area**: api
- **Role**: all
- **Intra**: No
- **Impact**: 4 | **Effort**: 4 | **Confidence**: 0.6 | **Score**: 0.60
- **Requirements**:
  - Monitor order flow for large seller alerts
  - Track Time & Sales for volume spikes
  - Trigger exits on red burst patterns
  - [UNBLOCKED: market-data-module shipped (2025-10-08)]
  - [CLARIFY: Does Robinhood API provide Level 2 data?]

### backtesting-engine
- **Title**: Strategy backtesting engine
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 4 | **Confidence**: 0.8 | **Score**: 1.00
- **Requirements**:
  - Replay historical data against strategy rules
  - Calculate win rate and R:R over 20+ trades
  - Performance analytics and reporting
  - [BLOCKED: technical-indicators; UNBLOCKED: market-data-module shipped (2025-10-08)]
  - [PIGGYBACK: extends backtest/ structure]

### position-scaling-logic
- **Title**: Position scaling and phase progression
- **Area**: strategy
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 3 | **Confidence**: 0.8 | **Score**: 1.33
- **Requirements**:
  - **Phase mode system**: Experience (sim only) → Proof of Concept (1 trade/day) → Real Money Trial (small size) → Scaling (gradual increases)
  - Prevent mode changes without criteria met
  - Enforce 1 trade per day in Proof phase (§Risk_Management)
  - Block additional trades after limit hit
  - Countdown display for next allowed trade
  - Override option for emergency exits only
  - Log profitability of last 10-20 sessions
  - Verify consistent profitability before scaling (minimum 10-20 profitable sessions)
  - Block scaling if inconsistent results
  - Export session summary
  - Check risk-reward ratio meets targets before phase advancement
  - Block manual override of phases
  - Gradually increase from 100 shares based on consistency metrics
  - Track win streaks and adjust position size
  - [BLOCKED: performance-tracking, safety-checks]
  - [MERGED: consecutive-session-tracker, phase-mode-system, trade-limiter, phase-progression-validator]

## Archive

<!-- Deprecated features -->

---

## Scoring Guide

**ICE** = Impact × Confidence ÷ Effort

- **Impact** (1-5): 1=nice-to-have, 3=useful, 5=critical for trading
- **Effort** (1-5): 1=<1 day, 3=1-2 weeks, 5=4+ weeks
- **Confidence** (0-1): 0.5=uncertain, 0.7=some unknowns, 0.9=high, 1.0=certain

Higher score = higher priority

## Intra Feature Classification

**Intra: Yes** - Small scope change requiring minimal planning
- Simple configuration changes
- Straightforward extensions of existing code
- Clear requirements with no ambiguity
- Can skip `/specify` and implement directly
- Examples: .env setup, logging extensions, CSV exports

**Intra: No** - Full spec-driven development required
- Complex business logic or algorithms
- Risk-critical trading features
- API integrations with error handling
- Architectural decisions needed
- Must use `/specify` → `/plan` → `/tasks` workflow
- Examples: Authentication, order execution, strategy logic

## Status Flow

```
Backlog → Later → Next → In Progress → Shipped
                               ↓
                          Archive
```

## Safety Notes

Per Constitution v1.0.0:
- All features MUST pass §Safety_First gates (paper trading, circuit breakers)
- §Risk_Management: Position limits, stop losses mandatory
- §Testing_Requirements: 90% coverage, backtesting, paper trading before production
