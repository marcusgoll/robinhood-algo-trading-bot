# Feature Specification: Backtesting Engine

**Branch**: `feature/001-backtesting-engine`
**Created**: 2025-10-19
**Status**: Draft

## User Scenarios

### Primary User Story
A strategy developer wants to validate trading algorithms against historical market data to measure performance metrics (win rate, profit/loss, drawdown) and verify risk controls before deploying to paper or live trading.

### Acceptance Scenarios
1. **Given** a trading strategy implementation, **When** the backtest engine runs against historical data, **Then** it executes the strategy's entry/exit logic chronologically and records all simulated trades
2. **Given** completed backtest results, **When** the performance analyzer processes trade history, **Then** it calculates key metrics: total return, win rate, profit factor, maximum drawdown, Sharpe ratio, and average trade duration
3. **Given** a strategy with stop-loss and take-profit rules, **When** the backtest executes, **Then** it enforces risk management rules and exits positions when limits are hit
4. **Given** historical price data with gaps or missing values, **When** the backtest runs, **Then** it handles data quality issues gracefully by skipping invalid periods and logging warnings
5. **Given** multiple strategy variants, **When** the comparison report is generated, **Then** it ranks strategies by risk-adjusted returns and highlights best performers

### Edge Cases
- What happens when historical data is missing for specific time periods?
- How does system handle strategies that never generate signals?
- What if a strategy tries to trade during market holidays or outside trading hours?
- How to simulate order fills when historical data only has daily candles (no intraday)?
- What happens when a position size exceeds available capital in simulation?
- How to handle dividend adjustments and stock splits in historical data?

## User Stories (Prioritized)

> **Purpose**: Break down feature into independently deliverable stories for MVP-first delivery.
> **Format**: [P1] = MVP (ship first), [P2] = Enhancement, [P3] = Nice-to-have

### Story Prioritization

**Priority 1 (MVP) 🎯**
- **US1** [P1]: As a developer, I want to load historical price data for backtesting so that I can simulate strategy performance across different time periods
  - **Acceptance**:
    - Fetches daily OHLCV (Open, High, Low, Close, Volume) data for specified symbols and date range
    - Validates data completeness and identifies gaps
    - Adjusts prices for splits and dividends
    - Caches historical data to avoid redundant API calls
    - Supports multiple data sources (Alpaca, Yahoo Finance fallback)
  - **Independent test**: Can load and validate historical data standalone
  - **Effort**: M (4-8 hours)

- **US2** [P1]: As a developer, I want to execute a strategy against historical data chronologically so that I can simulate realistic trading conditions
  - **Acceptance**:
    - Iterates through historical data in time order (no look-ahead bias)
    - Calls strategy's `should_enter()` method on each bar
    - Calls strategy's `should_exit()` method for open positions
    - Simulates order fills at next bar's open price (conservative assumption)
    - Tracks portfolio cash and positions throughout backtest
    - Prevents trading when insufficient capital
  - **Independent test**: Can execute simple buy-hold strategy and track positions
  - **Effort**: L (8-16 hours)

- **US3** [P1]: As a developer, I want to calculate performance metrics from backtest results so that I can evaluate strategy quality
  - **Acceptance**:
    - Calculates total return, annualized return, CAGR
    - Calculates win rate, profit factor, average win/loss
    - Calculates maximum drawdown and drawdown duration
    - Calculates Sharpe ratio (risk-adjusted return)
    - Generates equity curve (portfolio value over time)
    - Outputs metrics in structured format (JSON or dataclass)
  - **Independent test**: Can calculate metrics from sample trade history
  - **Effort**: M (4-8 hours)

- **US4** [P1]: As a developer, I want to generate a backtest report so that I can review results and share findings
  - **Acceptance**:
    - Uses backtest-report-template.md format
    - Includes all performance metrics
    - Lists all trades with entry/exit prices, P&L, duration
    - Shows equity curve data (for plotting)
    - Includes data quality warnings (gaps, invalid bars)
    - Saves report to feature directory
  - **Independent test**: Can generate report from sample backtest results
  - **Effort**: S (2-4 hours)

**Priority 2 (Enhancement)**
- **US5** [P2]: As a developer, I want to simulate realistic trading costs so that backtest results reflect actual trading conditions
  - **Acceptance**:
    - Applies commission per trade (configurable, default $0 for Robinhood)
    - Applies slippage as percentage of fill price (configurable, default 0.1%)
    - Accounts for bid-ask spread
    - Includes these costs in P&L calculations
  - **Depends on**: US2, US3
  - **Effort**: S (2-4 hours)

- **US6** [P2]: As a developer, I want to compare multiple strategy variants so that I can identify best-performing configurations
  - **Acceptance**:
    - Runs multiple strategies against same historical data
    - Generates comparison table with key metrics
    - Ranks strategies by Sharpe ratio or other criteria
    - Highlights statistical significance of differences
    - Exports comparison to CSV or markdown table
  - **Depends on**: US1, US2, US3, US4
  - **Effort**: M (4-8 hours)

- **US7** [P2]: As a developer, I want to validate risk controls in backtest so that I verify strategy follows constitution requirements
  - **Acceptance**:
    - Verifies no position exceeds 5% of portfolio (§Risk_Management)
    - Verifies all positions have stop losses
    - Checks maximum daily loss limits
    - Validates maximum number of trades per day
    - Reports any risk violations in backtest report
  - **Depends on**: US2
  - **Effort**: M (4-8 hours)

**Priority 3 (Nice-to-have)**
- **US8** [P3]: As a developer, I want to visualize backtest results so that I can intuitively understand strategy performance
  - **Acceptance**:
    - Generates equity curve plot (matplotlib)
    - Generates drawdown chart
    - Generates monthly returns heatmap
    - Saves plots to feature directory
  - **Depends on**: US3
  - **Effort**: M (4-8 hours)

- **US9** [P3]: As a developer, I want to run walk-forward analysis so that I can test strategy robustness and avoid overfitting
  - **Acceptance**:
    - Splits historical data into training and testing periods
    - Optimizes strategy parameters on training data
    - Validates on out-of-sample testing data
    - Reports in-sample vs out-of-sample performance degradation
  - **Depends on**: US1, US2, US3
  - **Effort**: XL (16+ hours, consider as separate feature)

**Effort Scale**:
- XS: <2 hours
- S: 2-4 hours
- M: 4-8 hours (½ day)
- L: 8-16 hours (1-2 days)
- XL: 16+ hours (>2 days, consider breaking down)

**MVP Strategy**: Ship US1-US4 first (load data, execute strategy, calculate metrics, generate report). This provides complete end-to-end backtesting workflow. Add trading costs (US5), comparison tools (US6), and risk validation (US7) based on usage feedback. Defer visualization (US8) and walk-forward analysis (US9) to future iterations.

## Visual References

Not applicable - backend/API feature with no UI components.

## Success Metrics (HEART Framework)

> **SKIP METRICS**: This is an internal development tool with no direct user behavior to track. Success is measured by accuracy of backtest simulations and developer adoption rather than user engagement.

## Screens Inventory (UI Features Only)

> **SKIP SCREENS**: Backend-only feature (no UI components). Outputs are structured reports (markdown/JSON) and optional matplotlib plots for local analysis.

## Hypothesis

> **Not an improvement feature**: This is a new capability addition required by constitution (§Testing_Requirements), not improving an existing flow.

## Context Strategy & Signal Design

- **System prompt altitude**: Detailed technical context for trading domain (OHLCV data, performance metrics, risk controls)
- **Tool surface**: Essential tools - historical data API, strategy interface, performance calculator, report generator
- **Examples in scope**:
  1. Simple buy-and-hold strategy implementation
  2. Momentum strategy with moving average crossover
  3. Risk management rules enforcement example
- **Context budget**: Target 30k tokens (backtests generate verbose trade logs)
- **Retrieval strategy**: JIT for historical data (fetch on demand), upfront for strategy definitions
- **Memory artifacts**: NOTES.md with backtest configurations, backtest reports in feature directory
- **Compaction cadence**: Summarize every 100 trades to avoid token overflow
- **Sub-agents**: None - single-agent implementation

## Requirements

### Functional (testable only)

- **FR-001**: System MUST load historical OHLCV data for specified symbols and date ranges from at least one data source (Alpaca or Yahoo Finance)
- **FR-002**: System MUST validate historical data for completeness and identify gaps or missing periods
- **FR-003**: System MUST adjust historical prices for stock splits and dividend payments
- **FR-004**: System MUST iterate through historical data in chronological order without look-ahead bias
- **FR-005**: System MUST call strategy's entry logic method on each time period
- **FR-006**: System MUST call strategy's exit logic method for all open positions
- **FR-007**: System MUST simulate order fills using next bar's open price (conservative fill assumption)
- **FR-008**: System MUST track portfolio cash balance and prevent trades when insufficient capital
- **FR-009**: System MUST record all simulated trades with entry/exit timestamps, prices, shares, and P&L
- **FR-010**: System MUST calculate total return, annualized return, and CAGR
- **FR-011**: System MUST calculate win rate, profit factor, average win, and average loss
- **FR-012**: System MUST calculate maximum drawdown and maximum drawdown duration
- **FR-013**: System MUST calculate Sharpe ratio using risk-free rate from config (default 0.02)
- **FR-014**: System MUST generate equity curve showing portfolio value over time
- **FR-015**: System MUST generate backtest report using backtest-report-template.md format
- **FR-016**: System MUST include data quality warnings in report (gaps, invalid bars, skipped periods)
- **FR-017**: System MUST cache historical data to avoid redundant API calls during repeated backtests
- **FR-018**: System MUST handle missing data gracefully by skipping invalid periods and logging warnings

### Non-Functional

- **NFR-001**: Performance: Backtest of 252 trading days (1 year) MUST complete within 30 seconds for single stock
- **NFR-002**: Performance: Historical data fetch and cache MUST complete within 60 seconds for 10 stocks
- **NFR-003**: Accuracy: Backtest results MUST match manual calculations within 0.01% for simple buy-and-hold strategy
- **NFR-004**: Reliability: System MUST handle data source failures gracefully with fallback to alternative source
- **NFR-005**: Data Quality: All timestamps MUST be in UTC and validated for market hours
- **NFR-006**: Error Handling: All errors MUST be logged with context (symbol, date, error type)
- **NFR-007**: Maintainability: All backtest logic MUST be unit tested with ≥90% coverage
- **NFR-008**: Security: API keys MUST be stored in environment variables, never in code
- **NFR-009**: Auditability: All backtest runs MUST log configuration, data range, and results to persistent storage
- **NFR-010**: Reproducibility: Backtests with same inputs MUST produce identical results (deterministic execution)

### Key Entities (if data involved)

- **BacktestConfig**: Configuration for backtest run with attributes:
  - strategy_class (Type): Strategy class to instantiate and test
  - symbols (List[str]): Stock symbols to backtest
  - start_date (datetime): Start of historical data range
  - end_date (datetime): End of historical data range
  - initial_capital (float): Starting portfolio value
  - commission (float): Commission per trade (default 0.0 for Robinhood)
  - slippage_pct (float): Slippage as percentage (default 0.001 for 0.1%)
  - risk_free_rate (float): Annual risk-free rate for Sharpe ratio (default 0.02)

- **BacktestResult**: Complete backtest output with attributes:
  - config (BacktestConfig): Configuration used for this run
  - trades (List[Trade]): All simulated trades
  - equity_curve (List[Tuple[datetime, float]]): Portfolio value over time
  - metrics (PerformanceMetrics): Calculated performance statistics
  - data_warnings (List[str]): Data quality issues encountered
  - execution_time_seconds (float): Time taken to run backtest

- **Trade**: Individual simulated trade with attributes:
  - symbol (str): Stock ticker
  - entry_date (datetime): When position opened
  - entry_price (float): Fill price for entry
  - exit_date (datetime): When position closed
  - exit_price (float): Fill price for exit
  - shares (int): Number of shares traded
  - pnl (float): Profit/loss for this trade
  - pnl_pct (float): Return percentage
  - duration_days (int): Holding period
  - exit_reason (str): Why position closed (stop_loss, take_profit, strategy_signal, end_of_data)

- **PerformanceMetrics**: Calculated statistics with attributes:
  - total_return (float): Total percentage return
  - annualized_return (float): Annualized percentage return
  - cagr (float): Compound annual growth rate
  - win_rate (float): Percentage of profitable trades
  - profit_factor (float): Gross profit / gross loss
  - average_win (float): Average profit on winning trades
  - average_loss (float): Average loss on losing trades
  - max_drawdown (float): Maximum peak-to-trough decline
  - max_drawdown_duration_days (int): Longest drawdown period
  - sharpe_ratio (float): Risk-adjusted return metric
  - total_trades (int): Number of completed trades
  - winning_trades (int): Number of profitable trades
  - losing_trades (int): Number of unprofitable trades

- **HistoricalDataBar**: OHLCV data for single time period with attributes:
  - symbol (str): Stock ticker
  - timestamp (datetime): Bar timestamp (UTC)
  - open (float): Opening price
  - high (float): Highest price
  - low (float): Lowest price
  - close (float): Closing price
  - volume (int): Trading volume
  - split_adjusted (bool): Whether prices are split-adjusted
  - dividend_adjusted (bool): Whether prices are dividend-adjusted

## Deployment Considerations

> Backend-only feature with no infrastructure changes required.

### Platform Dependencies

**None** - Uses existing Python runtime and dependencies. May add optional dependencies:
- `yfinance` for Yahoo Finance data source (fallback)
- `matplotlib` for visualization (P3 feature)

### Environment Variables

**New Required Variables**:
- `BACKTEST_DATA_SOURCE`: Primary historical data source (default: "alpaca")
  - Staging: "alpaca"
  - Production: "alpaca"
- `BACKTEST_CACHE_DIR`: Directory for cached historical data (default: ".backtest_cache/")
  - Staging: ".backtest_cache/"
  - Production: ".backtest_cache/"

**New Optional Variables**:
- `YAHOO_FINANCE_ENABLED`: Enable Yahoo Finance fallback (default: "true")
  - Set to "false" to disable fallback and only use primary source

**Changed Variables**:
- None

**Schema Update Required**: Yes - Update `secrets.schema.json` in `/plan` phase

### Breaking Changes

**API Contract Changes**:
- No breaking changes - new module only

**Database Schema Changes**:
- No database changes required (uses in-memory processing and file-based reports)

**Auth Flow Modifications**:
- No auth changes

**Client Compatibility**:
- Backward compatible - new module only

### Migration Requirements

**Database Migrations**:
- Not required

**Data Backfill**:
- Not required

**RLS Policy Changes**:
- Not applicable

**Reversibility**:
- Fully reversible - can remove module without affecting existing functionality

### Rollback Considerations

**Standard 3-command rollback**:
```bash
git revert <commit>
git push
# No database migrations to reverse
# Delete .backtest_cache/ directory if needed
```

## Dependencies and Blockers

### Dependencies
- **market-data-module**: Provides market data fetching infrastructure
  - Status: Partially implemented (exists in codebase)
  - Current capabilities: Real-time data fetching
  - Needed enhancement: Historical data fetching with date ranges
  - Critical path: Yes - needed for US1

- **performance tracking module**: Provides performance metric calculations
  - Status: Implemented (src/trading_bot/performance/)
  - Current capabilities: Trade tracking, metrics calculation
  - Potential reuse: PerformanceMetrics calculations
  - Critical path: No - can implement independently if needed

### Blockers
- **Historical data API access**: Requires Alpaca API key with historical data access
  - Resolution: User must have Alpaca account with market data subscription
  - Impact: Cannot run backtests without historical data access
  - Mitigation: Provide Yahoo Finance fallback (free but less reliable)

- **Strategy interface definition**: Need standard interface for strategies to implement
  - Resolution: Define IStrategy protocol in planning phase
  - Impact: Cannot test strategies without standard interface
  - Critical: Yes - blocks US2

### Assumptions
- User has Alpaca API access for historical data (or accepts Yahoo Finance quality)
- Strategies implement standard interface with `should_enter()` and `should_exit()` methods
- Daily OHLCV data is sufficient for MVP (no intraday backtesting)
- Backtest runs are local/synchronous (no distributed backtesting needed)
- Results are stored as markdown/JSON files (no database persistence for MVP)
- Order fills at next bar's open price is acceptable simulation (no sophisticated fill model)
- Commission is $0 for Robinhood (can be configured for other brokers)

## Constitution Compliance

This feature adheres to Constitution v1.0.0:

- **§Safety_First**: Enables "never trade with real money until fully tested" by providing validation mechanism
- **§Code_Quality**: Will implement with type hints, ≥90% test coverage, single-purpose functions
- **§Risk_Management**: Validates stop losses, position sizing, and risk limits in simulation
- **§Security**: API keys in environment variables only, no sensitive data in reports
- **§Data_Integrity**: Validates timestamps (UTC), handles missing data, adjusts for splits/dividends
- **§Testing_Requirements**: This IS the backtesting requirement - enables strategy validation before deployment

## Success Criteria

The backtesting engine feature is successful when:

1. **Data Loading**: System loads 1 year of daily OHLCV data for 10 stocks in under 60 seconds with 100% data validation
2. **Execution Accuracy**: Backtest of simple buy-and-hold strategy matches manual calculations within 0.01% error margin
3. **Performance Metrics**: All standard metrics (return, win rate, drawdown, Sharpe ratio) calculate correctly and match industry-standard definitions
4. **Reproducibility**: Running same backtest configuration produces identical results across multiple executions (deterministic)
5. **Data Quality**: System detects and reports 100% of data gaps, invalid prices, and missing periods
6. **Performance**: Backtest of 1 year (252 trading days) completes in under 30 seconds for single stock strategy
7. **Constitution Validation**: System correctly enforces and reports violations of risk management rules (position sizing, stop losses)
8. **Report Quality**: Generated backtest reports include all required sections from template and are human-readable
9. **Robustness**: System handles API failures gracefully and falls back to alternative data source with zero crashes over 30 days
10. **Developer Adoption**: At least 2 trading strategies successfully validated using backtest engine before paper trading deployment

## Out of Scope

The following are explicitly NOT included in this feature:

- Intraday backtesting with minute/tick data (MVP uses daily bars only)
- Walk-forward analysis and parameter optimization (deferred to P3/future feature)
- Monte Carlo simulation for confidence intervals
- Transaction cost analysis beyond simple commission and slippage
- Market microstructure modeling (order book, market impact)
- Multi-asset portfolio backtesting (MVP is single-stock per run)
- Real-time strategy execution (this is simulation only)
- Web UI or dashboard for backtest management
- Database persistence for backtest results (file-based reports only)
- Distributed/parallel backtesting infrastructure
- Options, futures, or crypto backtesting (stocks only)
- Fundamental data integration (price/volume only)
- Machine learning model backtesting framework

## Next Steps

After specification approval:
1. Run `/clarify` if ambiguities remain (see Key Decisions in NOTES.md)
2. Run `/plan` to create technical design including:
   - Strategy interface definition (IStrategy protocol)
   - Historical data manager architecture
   - Backtest execution engine design
   - Performance calculator implementation
   - Report generator structure
3. Run `/tasks` to break down into implementation tasks
4. Implement US1 (historical data loading) first, validate data quality
5. Implement US2 (backtest execution) second, test with simple strategy
6. Implement US3 (performance metrics) third, validate calculations
7. Implement US4 (report generation) fourth, verify report format
8. Validate with multiple real strategies against known historical periods
9. Ship to main branch for team use
