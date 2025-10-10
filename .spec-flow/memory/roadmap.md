# Robinhood Trading Bot Roadmap

**Last updated**: 2025-10-10 (order management foundation ready for staging)
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

### market-data-module
- **Title**: Market data and trading hours module
- **Area**: api
- **Role**: all
- **Intra**: No
- **Date**: 2025-10-08
- **Commit**: 597ed84
- **Delivered**:
  - MarketDataService class with real-time quote retrieval
  - Historical OHLCV data fetching (for backtesting)
  - Market hours status checking (is_market_open)
  - Market state detection (pre, regular, post, closed)
  - Trading hours enforcement (7am-10am EST window)
  - Data validation pipeline (price, timestamp, quote, historical data)
  - Rate limit protection with @with_retry decorator
  - Custom exceptions (DataValidationError, TradingHoursError)
  - Immutable dataclasses (Quote, MarketStatus, MarketDataConfig)
  - 46 unit + integration tests (100% pass rate)
  - 93.08% test coverage (exceeds 90% target)
  - 100% contract compliance with OpenAPI specification
  - Zero security vulnerabilities
  - Full Constitution v1.0.0 compliance (§Data_Integrity, §Safety_First, §Audit_Everything)
  - Code quality: A (95/100) from senior code review
  - Documentation: spec, plan, tasks, analysis-report, optimization-report, code-review-report

### startup-sequence
- **Title**: Bot startup and initialization
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Date**: 2025-10-08
- **Commit**: b5a73f4
- **Spec**: specs/startup-sequence/
- **Delivered**:
  - StartupOrchestrator class with dependency-ordered initialization
  - Startup banner display (PAPER/LIVE mode indicators)
  - Configuration loading and validation (§Pre_Deploy)
  - Logging system initialization with dedicated startup.log
  - Mode switcher initialization (paper/live mode management)
  - Circuit breaker initialization and health verification
  - Trading bot initialization with component health checks
  - Comprehensive status summary before trading begins
  - --dry-run flag for validation-only mode
  - --json flag for machine-readable status output
  - Fail-fast error handling with clear remediation guidance
  - Automatic directory creation (logs/, data/, backtests/results/)
  - Exit codes (0=success, 1=config error, 2=validation error, 3=init failure)
  - Startup duration tracking (131ms, 97.4% under 5s target)
  - 16 unit tests + 4 integration tests (100% pass rate)
  - Type safety: mypy errors reduced 25 → 1
  - Full Constitution v1.0.0 compliance (§Safety_First, §Pre_Deploy, §Audit_Everything)
  - Documentation: spec, plan, tasks, analysis-report, optimization-report

### error-handling-framework
- **Title**: API error handling framework
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Date**: 2025-10-08
- **Spec**: specs/error-handling-framework/
- **Delivered**:
  - Exception hierarchy (RetriableError, NonRetriableError, RateLimitError)
  - RetryPolicy configuration system with validation
  - @with_retry decorator with exponential backoff (1s, 2s, 4s) + jitter
  - Rate limit detection (HTTP 429 with Retry-After header support)
  - Circuit breaker with sliding window (5 failures in 60s triggers shutdown)
  - Callbacks (on_retry, on_exhausted) for custom handling
  - Integration with existing TradingLogger (§Audit_Everything)
  - Exception chaining preservation for debugging
  - Predefined policies (DEFAULT, AGGRESSIVE, CONSERVATIVE)
  - 27 unit tests (100% pass rate)
  - Test coverage: 87-96% per module
  - Type safety: mypy --strict passes (100% type coverage)
  - Security audit: 0 vulnerabilities
  - Performance: <100ms overhead per retry
  - Senior code review: 8.5/10 (APPROVED)
  - Full Constitution v1.0.0 compliance (§Risk_Management, §Safety_First, §Audit_Everything)
  - Production-ready, available for immediate use
  - Documentation: spec, plan, tasks, analysis, optimization-report, code-review-report

### credentials-manager
- **Title**: Secure credentials management
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Date**: 2025-10-09
- **Commit**: e1114ed
- **Spec**: specs/credentials-manager/
- **Delivered**:
  - utils/security.py module with 4 credential masking functions (100% coverage)
  - Device token persistence via dotenv.set_key() to .env file
  - MFA secret format validation (16-char base32 regex: ^[A-Z2-7]{16}$)
  - Device token optional validation in ConfigValidator
  - RobinhoodAuth.save_device_token_to_env() method
  - RobinhoodAuth.login_with_device_token() with automatic MFA fallback
  - Updated login() to try device token first (reduces MFA fatigue)
  - Credential masking in all logs (username, password, MFA secret, device token)
  - DEVICE_TOKEN field in Config and .env.example
  - 40 unit + integration + performance tests (100% pass rate)
  - Test coverage: 85.57% (robinhood_auth), 100% (security)
  - Validation performance: <500ms (actual ~5-10ms)
  - Full Constitution v1.0.0 compliance (§Security, §Code_Quality, §Audit_Everything)
  - Production-ready with comprehensive documentation
  - Documentation: spec, plan, tasks, analysis-report, README credentials section

### trade-logging
- **Title**: Enhanced trade logging with structured JSONL format
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Date**: 2025-10-09
- **Commit**: 7c685bd
- **Spec**: specs/trade-logging/
- **Delivered**:
  - TradeRecord dataclass with 27 fields (core data, strategy metadata, decision audit, outcome tracking, performance metrics, compliance)
  - StructuredTradeLogger class with daily JSONL file rotation (logs/trades/YYYY-MM-DD.jsonl)
  - TradeQueryHelper class with analytics queries (date range, symbol filtering, win rate calculation)
  - Thread-safe concurrent writes with file locking (0.405ms write latency, 10 threads verified)
  - Streaming I/O with generator pattern for memory efficiency (O(1) per record)
  - Dual logging: Backwards-compatible text logs + new structured JSONL logs
  - Field validation in TradeRecord.__post_init__() (symbol format, numeric constraints, required fields)
  - Graceful error degradation (OSError caught, logged to stderr, bot continues)
  - TradingBot integration with all 27 fields populated (session_id, bot_version, config_hash, order_id)
  - Decimal precision preservation (string serialization in JSON)
  - ISO 8601 UTC timestamps with 'Z' suffix
  - Compact JSONL format (~709KB for 1000 trades)
  - 20 tests (5 unit trade_record, 6 unit structured_logger, 4 unit query_helper, 3 integration, 2 smoke) - 100% pass rate
  - Test coverage: 95.89% (query_helper 89.47%, structured_logger 100%, trade_record 98.21%)
  - Performance: Write 0.405ms (12.3x faster than 5ms target), Query 15.17ms for 1000 trades (32.9x faster than 500ms target)
  - Security: 0 vulnerabilities (bandit scan 607 lines), Windows ACL file permissions (owner-only)
  - Senior code review: GOOD (0 critical, 0 important, 30 minor auto-fixed)
  - Contract compliance: 100% (27 fields, 10 methods verified)
  - KISS/DRY: No violations
  - Full Constitution v1.0.0 compliance (§Audit_Everything, §Data_Integrity, §Safety_First, §Testing)
  - Production-ready, local-only feature (no staging/production deployment needed)
  - Documentation: spec, plan, tasks, contracts/api.yaml, analysis-report, optimization-report, code-review-report

### order-management
- **Title**: Order management foundation
- **Area**: api
- **Role**: all
- **Intra**: No
- **Date**: 2025-10-10
- **Spec**: specs/order-management/
- **Delivered**:
  - Limit-order submission/cancel/status gateway with `with_retry` resilience
  - OrderManager service coordinating SafetyChecks, AccountData, and JSONL audit logging
  - TradingBot integration (live path delegates to OrderManager with limit-only enforcement)
  - Order management configuration block (offsets, slippage guard, strategy overrides)
  - Structured order log runbook (`logs/orders.jsonl`) + dry-run evidence
  - 39 test cases across order management + trading bot (95.03 % module coverage)
  - Documentation: spec, plan, tasks, optimization-report, code-review

## In Progress

<!-- Currently implementing -->

## Next

<!-- Top 5-10 prioritized features (sorted by score) -->

## Later

<!-- Future features (10-20 items, sorted by score) -->

## Backlog

<!-- All ideas sorted by ICE score (Impact × Confidence ÷ Effort) -->
<!-- Higher score = higher priority -->

### status-dashboard
- **Title**: CLI status dashboard & performance metrics
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Impact**: 4 | **Effort**: 2 | **Confidence**: 0.9 | **Score**: 1.80
- **Requirements**:
  - Display current positions
  - Show today's P&L
  - Track number of trades executed
  - Show remaining buying power
  - Display active orders
  - **Performance metrics display**: All key stats (win rate, avg R:R, total P&L, current streak, trades today, session count)
  - Update real-time
  - Export daily summary
  - Compare against targets
  - [UNBLOCKED: account-data-module shipped, performance-tracking ready (trade-logging provides data)]
  - [MERGED: performance-metrics-dashboard]

### health-check
- **Title**: Session health monitoring
- **Area**: api
- **Role**: all
- **Intra**: Yes
- **Impact**: 4 | **Effort**: 2 | **Confidence**: 0.9 | **Score**: 1.80
- **Requirements**:
  - Ping API every 5 minutes to maintain session
  - Verify authentication status
  - Log session duration
  - Auto-reauth if token expires
  - [UNBLOCKED: authentication-module shipped]

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
  - [UNBLOCKED: trade-logging shipped - provides TradeQueryHelper with win rate calculation]
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
  - [BLOCKED: market-data-module]

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
  - [BLOCKED: market-data-module, technical-indicators]

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
  - [BLOCKED: market-data-module]
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
  - [BLOCKED: market-data-module]
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
  - [BLOCKED: market-data-module, technical-indicators]
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
