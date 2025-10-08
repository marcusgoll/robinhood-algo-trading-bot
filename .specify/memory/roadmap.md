# Robinhood Trading Bot Roadmap

**Last updated**: 2025-10-07 (mode-switcher implementation)
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

## In Progress

<!-- Currently implementing -->

## Next

<!-- Top 5-10 prioritized features (sorted by score) -->

## Later

<!-- Future features (10-20 items, sorted by score) -->

## Backlog

<!-- All ideas sorted by ICE score (Impact × Confidence ÷ Effort) -->
<!-- Higher score = higher priority -->

### safety-checks
- **Title**: Pre-trade safety checks & risk management
- **Area**: api
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 2 | **Confidence**: 1.0 | **Score**: 2.50
- **Requirements**:
  - Verify sufficient buying power before order (§Risk_Management)
  - Block orders outside allowed hours (7am-10am EST)
  - Check if max daily loss already hit (circuit breaker)
  - Position size calculator based on account balance
  - **Consecutive loss detector**: Track last 3 trades
  - Stop all trading after 3 consecutive losses (§Safety_First)
  - Require manual restart
  - Log circuit breaker events
  - Prevent duplicate orders
  - [BLOCKED: account-data-module, market-data-module]
  - [MERGED: risk-management, consecutive-loss-detector]

### authentication-module
- **Title**: Robinhood authentication with MFA
- **Area**: api
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 2 | **Confidence**: 0.9 | **Score**: 2.25
- **Requirements**:
  - Login with MFA support using pyotp
  - Session pickle file storage
  - Auto-refresh token
  - Logout handler
  - Authentication error recovery
  - [BLOCKED: environment-config]

### account-data-module
- **Title**: Account data fetching
- **Area**: api
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 2 | **Confidence**: 0.9 | **Score**: 2.25
- **Requirements**:
  - Fetch current buying power
  - Get all positions with current P&L
  - Retrieve account balance
  - Check day trade count (§Risk_Management)
  - [BLOCKED: authentication-module]

### error-handling-framework
- **Title**: API error handling framework
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 2 | **Confidence**: 0.9 | **Score**: 2.25
- **Requirements**:
  - Retry logic for API failures (§Risk_Management)
  - Rate limit detection and exponential backoff
  - Network error recovery
  - Graceful shutdown on critical errors
  - [PIGGYBACK: bot.py has basic error handling]

### market-data-module
- **Title**: Market data and trading hours
- **Area**: api
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 2 | **Confidence**: 0.9 | **Score**: 2.25
- **Requirements**:
  - Get real-time stock quotes
  - Fetch historical price data (for backtesting)
  - Check if market is open
  - Enforce 7am-10am EST trading window (block trades outside peak volatility)
  - [BLOCKED: authentication-module]
  - [MERGED: trading-hours-restriction]

### startup-sequence
- **Title**: Bot startup and initialization
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 2 | **Confidence**: 0.9 | **Score**: 2.25
- **Requirements**:
  - Validate environment (§Pre_Deploy)
  - Authenticate with MFA
  - Load config
  - Check market status
  - Verify account access
  - Display dashboard
  - Enter main loop
  - [BLOCKED: authentication-module, configuration-validator, status-dashboard]

### credentials-manager
- **Title**: Secure credentials management
- **Area**: infra
- **Role**: all
- **Intra**: No
- **Impact**: 5 | **Effort**: 2 | **Confidence**: 0.9 | **Score**: 2.25
- **Requirements**:
  - Secure storage of credentials (§Security)
  - Validate MFA secret format
  - Test authentication on first run
  - Store device token for faster subsequent logins
  - [BLOCKED: environment-config]

### trade-logging
- **Title**: Trade history database/CSV
- **Area**: infra
- **Role**: all
- **Intra**: Yes
- **Impact**: 4 | **Effort**: 2 | **Confidence**: 1.0 | **Score**: 2.00
- **Requirements**:
  - Save all trades to CSV (timestamp, symbol, action, quantity, price, P&L)
  - Track daily performance metrics (§Audit_Everything)
  - Export trade history
  - [BLOCKED: logging-system]

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
  - [BLOCKED: account-data-module, performance-tracking]
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
  - [BLOCKED: authentication-module]

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
  - [BLOCKED: authentication-module, safety-checks]

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
  - [BLOCKED: trade-logging]
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
