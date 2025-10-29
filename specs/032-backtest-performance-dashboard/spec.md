# Specification: Backtest Performance Dashboard

**Feature**: Backtest Performance Dashboard with Equity Curves
**Slug**: `backtest-performance-dashboard`
**Created**: 2025-10-28
**Status**: Specification Phase
**GitHub Issue**: #42

---

## Executive Summary

Web dashboard for visualizing backtest results from the existing backtrader engine. Traders currently analyze backtests through console logs and markdown reports, making it difficult to spot patterns, compare strategies, or share results. This dashboard provides interactive charts (equity curve, drawdown, win/loss distribution, R-multiple histogram) and a performance metrics table, reducing strategy optimization time by 50%.

**User Value**: Visual feedback accelerates strategy refinement from hours to minutes.

**Technical Approach**: FastAPI backend endpoints serving JSON-serialized backtest data, React frontend with Recharts for interactive visualizations.

---

## Problem Statement

### Current Pain Points

1. **No visual feedback during strategy optimization**
   - Traders iterate through console logs showing only numeric metrics
   - Hard to spot equity curve patterns (smooth vs choppy growth)
   - Miss correlation between drawdown periods and market events

2. **Difficult to compare strategies side-by-side**
   - Must open multiple markdown reports in separate windows
   - No overlay of equity curves for visual comparison
   - Can't quickly identify which parameter changes improved performance

3. **Inefficient workflow for sharing results**
   - Copy/paste markdown reports into Slack/Discord
   - No easy way to export comparison reports
   - Stakeholders struggle to interpret raw text metrics

### Evidence of Problem

- **User feedback**: "I spend 30 minutes analyzing console output per backtest run"
- **Existing pattern**: QuantConnect, TradingView Strategy Tester provide visual dashboards as core value prop
- **Opportunity cost**: Manual log analysis delays strategy deployment by 2-3 days

---

## Goals & Success Criteria

### Goals

1. **Reduce strategy optimization time by 50%** (from 30 min to 15 min per backtest analysis)
2. **Enable side-by-side strategy comparison** (overlay 2-3 equity curves)
3. **Provide shareable reports** (PNG/PDF export for stakeholders)

### Success Criteria

**Must Have** (MVP):
- Users can view equity curve for any completed backtest
- Users can see drawdown chart showing peak-to-trough drops
- Users can browse win/loss trade distribution
- Users can access performance metrics table (win rate, Sharpe ratio, max drawdown)
- Dashboard loads backtest data in under 2 seconds

**Should Have** (Post-MVP):
- Users can compare 2-3 backtests on same equity curve chart
- Users can filter trade list by symbol, date range, or win/loss
- Users can export dashboard to PNG or PDF

**Could Have** (Future):
- Real-time backtest progress streaming (WebSocket)
- Historical trend line showing strategy performance over time
- Alerts when backtest metrics fall below thresholds

### Measurable Outcomes (HEART Metrics)

- **Happiness**: 4.5/5.0 dashboard satisfaction rating
- **Engagement**: 80% of traders use dashboard weekly
- **Adoption**: 60% run first backtest within 7 days of bot activation
- **Retention**: 70% return to dashboard within 30 days
- **Task Success**: 75% complete backtest comparison workflow

See `design/heart-metrics.md` for detailed measurement plan.

---

## User Scenarios

### Scenario 1: Strategy Optimization Iteration

**Given**: Trader has run 5 backtests with different parameter combinations
**When**: Trader opens backtest list and selects "Momentum Bull Flag v1.2"
**Then**:
- Dashboard loads in <2 seconds
- Equity curve shows clear upward trend with minimal drawdown
- Win/loss histogram shows 60% win rate
- Trader identifies this as best-performing variant

**Acceptance**:
- All 5 charts render without errors
- Metrics match console log output exactly
- Page loads in under 2 seconds (P95)

### Scenario 2: Comparing Two Strategies

**Given**: Trader wants to compare "Bull Flag" vs "Zone Breakout" strategies
**When**: Trader navigates to `/backtests/compare`, selects both backtests, and overlays equity curves
**Then**:
- Both equity curves render on same chart with different colors
- Legend shows strategy names
- Metrics comparison table shows side-by-side win rates, Sharpe ratios
- Trader exports comparison as PNG to share with team

**Acceptance**:
- Maximum 3 backtests can be compared simultaneously
- Color legend clearly distinguishes each strategy
- Export generates valid PNG file

### Scenario 3: Analyzing Worst Drawdown Period

**Given**: Trader sees -15% max drawdown in metrics table
**When**: Trader inspects drawdown chart to identify period
**Then**:
- Chart highlights worst drawdown period with date range
- Trader correlates dates with market events (e.g., Fed announcement)
- Trader decides to add volatility filter to strategy

**Acceptance**:
- Drawdown chart shows peak-to-trough drops accurately
- Date labels match trade timestamps
- Tooltip shows exact drawdown percentage on hover

---

## Requirements

### Functional Requirements (FR)

**FR-001**: System shall export backtest results to JSON format
- **Details**: Use existing `report_generator.py` to serialize `BacktestResult` to JSON
- **Data fields**: strategy, parameters, equity_curve, trades, metrics
- **Validation**: JSON must include all fields from `BacktestResult` model

**FR-002**: API shall provide GET /api/v1/backtests endpoint
- **Response**: List of all backtests with summary metadata (id, strategy, date range, total return)
- **Filters**: Optional query params for date range, strategy name
- **Pagination**: Limit 50 results per page

**FR-003**: API shall provide GET /api/v1/backtests/{id} endpoint
- **Response**: Full backtest result (equity curve data, trades list, metrics)
- **Format**: JSON following `BacktestResult` schema
- **Error handling**: 404 if backtest ID not found

**FR-004**: Dashboard shall display equity curve chart
- **Chart type**: Line chart (X=date, Y=account balance)
- **Data source**: `equity_curve` array from API response
- **Interaction**: Tooltip on hover showing date and balance

**FR-005**: Dashboard shall display drawdown chart
- **Chart type**: Area chart (X=date, Y=drawdown %)
- **Calculation**: (peak - current) / peak * 100
- **Color**: Red fill to emphasize losses

**FR-006**: Dashboard shall display win/loss distribution
- **Chart type**: Bar chart (X=P&L buckets, Y=trade count)
- **Buckets**: [-$500+, -$400 to -$300, ..., $0 to $100, $100+]
- **Colors**: Red for losses, green for wins

**FR-007**: Dashboard shall display R-multiple histogram
- **Chart type**: Histogram (X=R-multiple buckets, Y=frequency)
- **Definition**: R-multiple = (exit - entry) / (entry - stop_loss)
- **Buckets**: [-2R, -1R, 0R, 1R, 2R, 3R+]

**FR-008**: Dashboard shall display performance metrics table
- **Metrics**: Win rate, profit factor, Sharpe ratio, max drawdown, total return
- **Source**: `metrics` object from API response
- **Format**: Currency ($X,XXX.XX), percentages (XX.XX%), ratios (X.XX)

**FR-009**: Users shall filter trade list by symbol, date, or outcome
- **Filters**: Dropdown for symbol, date range picker, win/loss toggle
- **Behavior**: Client-side filtering of trades array
- **UI**: Show "X of Y trades" count

**FR-010**: Users shall compare up to 3 backtests on same equity curve
- **Interaction**: Multi-select dropdown to choose backtests
- **Chart**: Overlay equity curves with distinct colors
- **Legend**: Show strategy names with color swatches
- **Limitation**: Maximum 3 backtests to avoid cluttered chart

**FR-011**: Users shall export dashboard to PNG or PDF
- **Method**: Use html2canvas or similar library
- **Content**: Full dashboard including all 5 charts and metrics
- **Filename**: `backtest_{strategy}_{date}.png`

### Non-Functional Requirements (NFR)

**NFR-001**: API response time shall be <200ms P95
- **Rationale**: Fast feedback during strategy optimization
- **Measurement**: Prometheus metrics on `/api/v1/backtests/{id}` endpoint

**NFR-002**: Dashboard initial load shall be <2 seconds P95
- **Rationale**: Reduce waiting time between backtest runs
- **Measurement**: Lighthouse performance score >90

**NFR-003**: Charts shall be interactive with hover tooltips
- **Rationale**: Allow traders to inspect exact values without cluttering UI
- **Library**: Recharts or Plotly with built-in interactivity

**NFR-004**: Dashboard shall be accessible (WCAG 2.1 Level AA)
- **Requirements**: Keyboard navigation, screen reader support, color contrast
- **Testing**: axe DevTools scan with 0 violations

**NFR-005**: Backtest data shall persist across bot restarts
- **Storage**: Save JSON exports to `logs/backtests/` directory
- **Filename format**: `backtest_{timestamp}_{strategy}.json`
- **Retention**: Keep last 100 backtests (auto-delete oldest)

**NFR-006**: Dashboard shall handle missing data gracefully
- **Behavior**: Show "No data" message if equity_curve is empty
- **Error states**: Display user-friendly error if API fails

---

## Technical Constraints

### Existing Architecture

1. **Backend**: FastAPI 0.104.1 with existing `/api/v1/*` routes
   - Source: `api/app/routes/*.py` (state, config, metrics, workflows)
   - Pattern: Follow existing route structure (auth, error handling, response models)

2. **Backtesting Engine**: backtrader 1.9.78.123
   - Source: `src/trading_bot/backtest/` module
   - Models: `BacktestResult`, `BacktestConfig`, `PerformanceMetrics`, `Trade`
   - Exporter: `report_generator.py` with `generate_json()` method

3. **Data Models**: Decimal-based money fields, UTC timestamps
   - Source: `src/trading_bot/backtest/models.py:1-80`
   - Validation: Comprehensive `__post_init__` checks

### Technology Decisions

**Backend**:
- Language: Python 3.11
- Framework: FastAPI (reuse existing API structure)
- Serialization: Pydantic models for response validation
- Storage: Filesystem (JSON files in `logs/backtests/`)

**Frontend** (NEW - this is first frontend component):
- Framework: React 18 (industry standard, rich ecosystem)
- Build tool: Vite (fast dev server, optimized builds)
- Charts: Recharts 2.x (React-native, composable, responsive)
- Styling: Tailwind CSS (utility-first, rapid development)
- HTTP client: Axios or fetch API

**Alternatives Rejected**:
- **Vue.js**: Less widespread adoption in trading tools space
- **Plotly.js**: Heavy bundle size (~3MB), overkill for 5 charts
- **D3.js**: Too low-level, requires custom chart building

### Integration Points

1. **Backtest Orchestrator** (existing):
   - Location: `src/trading_bot/backtest/orchestrator.py`
   - Trigger: After backtest completes, call `report_generator.generate_json()`
   - Output: Save JSON to `logs/backtests/backtest_{timestamp}_{strategy}.json`

2. **API Routes** (new):
   - Location: `api/app/routes/backtests.py` (new file)
   - Pattern: Follow `api/app/routes/state.py` structure
   - Authentication: Reuse existing `verify_api_key` dependency

3. **Frontend Build** (new):
   - Location: `web/` directory (new)
   - Serve: Static files via FastAPI StaticFiles middleware
   - Development: Vite dev server on port 5173, proxy API calls to :8000

---

## API Contract

### GET /api/v1/backtests

**Purpose**: List all backtest runs with summary metadata

**Request**:
```http
GET /api/v1/backtests?limit=50&offset=0&strategy=momentum HTTP/1.1
Host: localhost:8000
X-API-Key: your-token
```

**Query Parameters**:
- `limit` (int, optional): Results per page (default: 50, max: 100)
- `offset` (int, optional): Pagination offset (default: 0)
- `strategy` (str, optional): Filter by strategy name (case-insensitive partial match)
- `start_date` (ISO date, optional): Filter backtests after this date
- `end_date` (ISO date, optional): Filter backtests before this date

**Response** (200 OK):
```json
{
  "backtests": [
    {
      "id": "backtest_2025-10-28_momentum-bull-flag",
      "strategy": "momentum_bull_flag",
      "parameters": {
        "pole_min_gain": 8.0,
        "flag_range": [3.0, 5.0]
      },
      "date_range": {
        "start": "2025-01-01T00:00:00Z",
        "end": "2025-10-28T00:00:00Z"
      },
      "metrics": {
        "total_return": 15.3,
        "win_rate": 58.5,
        "max_drawdown": -8.2
      },
      "created_at": "2025-10-28T19:15:00Z"
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

**Errors**:
- `401 Unauthorized`: Missing or invalid API key
- `422 Unprocessable Entity`: Invalid query parameters

---

### GET /api/v1/backtests/{id}

**Purpose**: Get full backtest result with equity curve and trade details

**Request**:
```http
GET /api/v1/backtests/backtest_2025-10-28_momentum-bull-flag HTTP/1.1
Host: localhost:8000
X-API-Key: your-token
```

**Response** (200 OK):
```json
{
  "id": "backtest_2025-10-28_momentum-bull-flag",
  "strategy": "momentum_bull_flag",
  "parameters": {
    "pole_min_gain": 8.0,
    "flag_range": [3.0, 5.0]
  },
  "date_range": {
    "start": "2025-01-01T00:00:00Z",
    "end": "2025-10-28T00:00:00Z"
  },
  "equity_curve": [
    {"date": "2025-01-01T00:00:00Z", "balance": 100000.0},
    {"date": "2025-01-02T00:00:00Z", "balance": 100250.0},
    {"date": "2025-01-03T00:00:00Z", "balance": 100180.0}
  ],
  "trades": [
    {
      "symbol": "TSLA",
      "entry_date": "2025-01-02T14:30:00Z",
      "exit_date": "2025-01-03T15:45:00Z",
      "entry_price": 250.0,
      "exit_price": 258.0,
      "shares": 10,
      "pnl": 80.0,
      "r_multiple": 2.0,
      "outcome": "win"
    }
  ],
  "metrics": {
    "total_return": 15.3,
    "sharpe_ratio": 1.8,
    "max_drawdown": -8.2,
    "win_rate": 58.5,
    "profit_factor": 1.9,
    "total_trades": 127,
    "winning_trades": 74,
    "losing_trades": 53,
    "avg_win": 125.50,
    "avg_loss": -82.30
  },
  "created_at": "2025-10-28T19:15:00Z"
}
```

**Errors**:
- `401 Unauthorized`: Missing or invalid API key
- `404 Not Found`: Backtest ID does not exist
- `500 Internal Server Error`: Failed to read backtest file

---

## Data Model

### Backtest Export JSON Schema

```typescript
interface BacktestExport {
  id: string;                      // "backtest_{timestamp}_{strategy}"
  strategy: string;                // Strategy class name
  parameters: Record<string, any>; // Strategy-specific parameters
  date_range: {
    start: string;                 // ISO 8601 UTC timestamp
    end: string;
  };
  equity_curve: EquityPoint[];
  trades: Trade[];
  metrics: PerformanceMetrics;
  created_at: string;              // ISO 8601 UTC timestamp
}

interface EquityPoint {
  date: string;    // ISO 8601 UTC timestamp
  balance: number; // Account balance in USD
}

interface Trade {
  symbol: string;
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  shares: number;
  pnl: number;         // Profit/loss in USD
  r_multiple: number;  // (exit - entry) / (entry - stop_loss)
  outcome: "win" | "loss";
}

interface PerformanceMetrics {
  total_return: number;      // Percentage
  sharpe_ratio: number;
  max_drawdown: number;      // Percentage (negative)
  win_rate: number;          // Percentage
  profit_factor: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  avg_win: number;           // Average winning trade P&L
  avg_loss: number;          // Average losing trade P&L
}
```

---

## Assumptions

1. **Backtest frequency**: Users run 1-5 backtests per day (low volume, simple filesystem storage sufficient)
2. **Data size**: Average backtest has 50-200 trades, equity curve with 200-500 data points (~50KB JSON)
3. **Retention**: Last 100 backtests kept (auto-delete oldest to prevent disk bloat)
4. **Browser support**: Modern browsers (Chrome 90+, Firefox 88+, Safari 14+) with ES2020 support
5. **Network**: Users access dashboard over local network or VPN (no public internet exposure)

---

## Out of Scope

1. **Real-time backtest streaming**: Showing progress bar during backtest execution (future feature)
2. **Monte Carlo analysis**: Randomized parameter testing (separate feature)
3. **Walk-forward optimization**: Rolling window backtests (complex, future phase)
4. **User authentication**: Currently single-user bot (API key auth only)
5. **Multi-currency support**: USD-only trading (bot constraint)
6. **Mobile-responsive UI**: Desktop-first (trading analysis on large screens)

---

## Dependencies

### External Dependencies
- **React 18**: Frontend framework
- **Recharts 2.x**: Charting library
- **Tailwind CSS 3.x**: Styling framework
- **Vite 5.x**: Build tool and dev server
- **Axios 1.x**: HTTP client (optional, can use fetch)

### Internal Dependencies
- **Backtest Engine** (`src/trading_bot/backtest/`): Generates results
- **Report Generator** (`src/trading_bot/backtest/report_generator.py`): JSON serialization
- **FastAPI Backend** (`api/app/`): API routing and auth

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Large backtest files slow dashboard | High | Medium | Implement pagination for trades list (show 50 at a time) |
| Chart library bundle size bloats frontend | Medium | Low | Use Recharts (lightweight, tree-shakeable) instead of Plotly |
| Filesystem storage doesn't scale | Medium | Low | Design JSON schema to support future migration to SQLite/PostgreSQL |
| No frontend developer on team | High | Medium | Use create-react-app or Vite starter template, minimal custom code |
| API auth bypass if key leaked | High | Low | Document .env security, recommend rotating keys monthly |

---

## Open Questions

*None - all decisions finalized based on existing codebase patterns and industry standards.*

---

## Appendix

### References

- **QuantConnect Strategy Tester**: Industry pattern for backtest visualization
- **TradingView Backtesting UI**: Equity curve and metrics table layout inspiration
- **Existing Backtest Engine Spec**: `specs/001-backtesting-engine/spec.md` for data model context

### Related Specs

- `specs/001-backtesting-engine/` - Foundation backtest engine implementation
- `specs/029-llm-friendly-bot-operations/` - FastAPI v1.8.0 architecture

### Glossary

- **Equity Curve**: Chart of account balance over time
- **Drawdown**: Peak-to-trough decline in account value (measures risk)
- **R-Multiple**: Risk-adjusted return metric (trade P&L / initial risk)
- **Sharpe Ratio**: Risk-adjusted return metric (higher = better risk/reward)
- **Profit Factor**: Gross profit / gross loss (>1.0 = profitable strategy)
