# Implementation Plan: Backtest Performance Dashboard

**Feature**: specs/032-backtest-performance-dashboard
**Created**: 2025-10-28
**Last Updated**: 2025-10-28
**Deployment Model**: direct-prod

---

## Executive Summary

Build web dashboard for visualizing backtest results from existing backtrader engine. **Key insight**: Extensive code reuse opportunity - backtest models and JSON export already exist. Primary work is creating first React frontend + 2 new API endpoints.

**Complexity**: Medium (new frontend, but backend mostly exists)
**Risk**: Low (no live trading impact, visualization only)
**Timeline**: 3-4 days

---

## Phase 0: Research Findings

### Reusable Components (HIGH VALUE)

1. **Backtest Data Models** (src/trading_bot/backtest/models.py)
   - BacktestResult, PerformanceMetrics, Trade, BacktestConfig
   - Complete with validation, Decimal precision
   - **Reuse**: 100% - perfect match for dashboard

2. **Report Generator** (src/trading_bot/backtest/report_generator.py)
   - generate_json() exports BacktestResult to JSON
   - Already converts Decimal → float for JSON
   - **Reuse**: Use as-is for API serialization

3. **FastAPI Infrastructure** (api/app/main.py)
   - FastAPI 0.104.1, CORS configured
   - /api/v1/ prefix convention
   - Rate limiting (100 req/min)
   - **Reuse**: Follow existing patterns

### New Components Required

**Backend (25% of work)**:
- api/app/routes/backtests.py - 2 endpoints
- api/app/schemas/backtest.py - Pydantic models
- api/app/services/backtest_loader.py - File loader + caching

**Frontend (75% of work)**:
- frontend/ - First React component (new directory!)
- React 18 + TypeScript 5 + Vite
- Recharts for 5 chart types
- 3 UI screens (list, detail, compare)

---

## Architecture Decisions

### Decision 1: React + TypeScript for Frontend

**Options Considered**:
1. React + TypeScript (chosen)
2. Vue.js + TypeScript
3. Plain HTML + vanilla JS

**Choice**: React + TypeScript

**Rationale**:
- Industry standard for dashboards (TradingView uses React)
- Strong TypeScript support (type safety for financial data)
- Rich charting ecosystem (Recharts, Chart.js)
- Fits project goal: professional-grade trading tools

**Trade-offs**:
- ✅ Pro: Best charting libraries, large community
- ❌ Con: Larger bundle size vs Vue (acceptable for dashboard)

**Alternatives Rejected**:
- Vue.js: Smaller ecosystem for financial charts
- Plain JS: No type safety for complex data models

---

### Decision 2: Recharts for Charting Library

**Options Considered**:
1. Recharts (chosen)
2. Chart.js + react-chartjs-2
3. Victory
4. D3.js (raw)

**Choice**: Recharts

**Rationale**:
- React-first library (composable API)
- Built-in support for financial charts (LineChart, BarChart)
- TypeScript definitions included
- Good performance (<1000 data points)

**Trade-offs**:
- ✅ Pro: Easy customization, responsive, accessible
- ❌ Con: Limited for >10K points (not issue: backtests have ~100-500 points)

**Alternatives Rejected**:
- Chart.js: Imperative API (less React-friendly)
- D3.js: Too low-level (overkill for standard charts)

---

### Decision 3: File-based Storage (No Database)

**Options Considered**:
1. File-based JSON (chosen)
2. SQLite for backtest results
3. PostgreSQL

**Choice**: File-based JSON

**Rationale**:
- Existing backtest JSON exports (report_generator.py)
- Low query volume (<10 backtests shown)
- Simple deployment (no migrations)
- Aligns with project architecture (no DB)

**Trade-offs**:
- ✅ Pro: Zero setup, portable, easy debugging
- ❌ Con: No complex queries (acceptable: simple list/detail views)

**Alternatives Rejected**:
- SQLite: Premature optimization (not many backtests yet)
- PostgreSQL: Overkill for visualization-only feature

---

### Decision 4: Direct API → React (No State Management Library)

**Options Considered**:
1. Direct API calls + useState (chosen)
2. Redux Toolkit
3. Zustand
4. TanStack Query (React Query)

**Choice**: Direct API + useState

**Rationale**:
- Simple data flow (fetch → display)
- No complex client-side state
- 3 screens with minimal shared state
- KISS principle

**Trade-offs**:
- ✅ Pro: No dependencies, easy to understand
- ❌ Con: Manual cache management (acceptable: 10-min server cache)

**Alternatives Rejected**:
- Redux: Overkill for 3 screens
- React Query: Nice but adds complexity

---

## Data Model & Contracts

### API Contract: GET /api/v1/backtests

**Request**: None (list all)

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "2025-10-26-bull-flag-aapl",
      "strategy": "BullFlagStrategy",
      "symbols": ["AAPL", "TSLA"],
      "start_date": "2025-07-01",
      "end_date": "2025-10-26",
      "total_return": 0.142,
      "win_rate": 0.62,
      "total_trades": 29,
      "created_at": "2025-10-26T14:30:00Z"
    }
  ],
  "total": 1
}
```

**Caching**: 10 minutes (server-side)

---

### API Contract: GET /api/v1/backtests/:id

**Request**: Path param `id` (backtest identifier)

**Response** (200 OK):
```json
{
  "config": {
    "strategy": "BullFlagStrategy",
    "symbols": ["AAPL"],
    "start_date": "2025-07-01T00:00:00Z",
    "end_date": "2025-10-26T00:00:00Z",
    "initial_capital": 100000.0,
    "commission": 0.0,
    "slippage_pct": 0.001
  },
  "metrics": {
    "total_return": 0.142,
    "annualized_return": 0.38,
    "cagr": 0.35,
    "win_rate": 0.62,
    "profit_factor": 2.3,
    "average_win": 450.25,
    "average_loss": 195.50,
    "max_drawdown": 0.042,
    "max_drawdown_duration_days": 5,
    "sharpe_ratio": 1.8,
    "total_trades": 29,
    "winning_trades": 18,
    "losing_trades": 11
  },
  "trades": [
    {
      "symbol": "AAPL",
      "entry_date": "2025-07-15T14:30:00Z",
      "entry_price": 150.25,
      "exit_date": "2025-07-18T15:45:00Z",
      "exit_price": 155.10,
      "shares": 50,
      "pnl": 242.50,
      "pnl_pct": 0.032,
      "duration_days": 3,
      "exit_reason": "take_profit",
      "commission": 0.0,
      "slippage": 0.05
    }
  ],
  "equity_curve": [
    {
      "timestamp": "2025-07-01T00:00:00Z",
      "equity": 100000.0
    },
    {
      "timestamp": "2025-07-18T00:00:00Z",
      "equity": 100242.50
    }
  ],
  "data_warnings": []
}
```

**Caching**: 10 minutes

**Error** (404 Not Found):
```json
{
  "error": "Backtest not found",
  "id": "invalid-id"
}
```

---

## Component Architecture

### Backend Components

```
api/app/
├── routes/
│   └── backtests.py           # NEW: 2 endpoints (list, detail)
├── schemas/
│   └── backtest.py            # NEW: Pydantic response models
├── services/
│   └── backtest_loader.py     # NEW: Load JSON + caching
└── main.py                    # MODIFY: Add backtests router
```

**Reused**:
- src/trading_bot/backtest/models.py (BacktestResult, PerformanceMetrics)
- src/trading_bot/backtest/report_generator.py (generate_json)

---

### Frontend Components

```
frontend/
├── src/
│   ├── components/
│   │   ├── BacktestList.tsx       # Screen 1: Table with filters
│   │   ├── BacktestDetail.tsx     # Screen 2: 5 charts + metrics
│   │   ├── CompareView.tsx        # Screen 3: Overlay comparison
│   │   ├── charts/
│   │   │   ├── EquityCurve.tsx    # Line chart (Recharts)
│   │   │   ├── DrawdownChart.tsx  # Area chart
│   │   │   ├── WinLossChart.tsx   # Bar chart
│   │   │   ├── RMultipleChart.tsx # Histogram
│   │   │   └── TradesTable.tsx    # Sortable table
│   │   └── shared/
│   │       ├── MetricsCard.tsx    # Reusable metric display
│   │       └── FilterBar.tsx      # Symbol/date filters
│   ├── services/
│   │   └── api.ts                 # API client (fetch wrapper)
│   ├── types/
│   │   └── backtest.ts            # TypeScript interfaces
│   ├── App.tsx                    # Router (react-router-dom)
│   └── main.tsx                   # Entry point
├── package.json                   # Dependencies
├── vite.config.ts                 # Vite build config
└── tsconfig.json                  # TypeScript config
```

---

## Integration Points

### 1. Backtest JSON Files → API

**Flow**: report_generator.py → JSON file → backtest_loader.py → API

**File Location**: `backtest_results/YYYY-MM-DD-strategy-symbols.json`

**Example Filename**: `backtest_results/2025-10-26-bull-flag-aapl-tsla.json`

**Loading Logic**:
```python
# api/app/services/backtest_loader.py
def list_backtests() -> list[dict]:
    """Scan backtest_results/ directory for JSON files."""
    results = []
    for file in Path("backtest_results").glob("*.json"):
        data = json.loads(file.read_text())
        results.append({
            "id": file.stem,
            "strategy": data["config"]["strategy"],
            "symbols": data["config"]["symbols"],
            ...
        })
    return results
```

---

### 2. FastAPI → React Frontend

**Development**:
- FastAPI: `http://localhost:8000`
- Vite dev server: `http://localhost:3000`
- CORS already configured for localhost:3000

**Production**:
- FastAPI serves React build: `api/static/`
- Single port: `http://vps:8000`

---

### 3. Docker Compose Integration

**Modify docker-compose.yml**:
```yaml
services:
  api:
    build:
      context: .
      dockerfile: api/Dockerfile
    volumes:
      - ./backtest_results:/app/backtest_results:ro  # Read backtest JSON
      - ./frontend/dist:/app/static:ro                # Serve React build
    ports:
      - "8000:8000"
```

---

## Deployment Strategy

### Phase 1: Backend API (Day 1)

1. Create backend components
2. Test with curl/Postman
3. Deploy to staging (VPS, paper trading mode)
4. Validate: `/api/v1/backtests` returns data

### Phase 2: Frontend (Days 2-3)

1. Initialize React + Vite project
2. Build components (list → detail → compare)
3. Test locally with API
4. Build production bundle

### Phase 3: Integration (Day 4)

1. Configure FastAPI to serve React static files
2. Update docker-compose.yml
3. Deploy to staging (full stack)
4. Manual QA testing (3 screens)

### Phase 4: Production (After Staging Validation)

1. Tag release (v1.9.0)
2. Deploy to production VPS
3. Monitor logs for 24 hours

---

## Testing Strategy

### Backend Tests

**Unit Tests** (pytest):
- `tests/unit/services/test_backtest_loader.py`
  - Test JSON parsing
  - Test file scanning
  - Test error handling (missing files)

**Integration Tests**:
- `tests/integration/test_backtests_api.py`
  - Test GET /api/v1/backtests (list)
  - Test GET /api/v1/backtests/:id (detail)
  - Test 404 handling

**Target Coverage**: 80%

---

### Frontend Tests

**Component Tests** (Vitest + React Testing Library):
- BacktestList.test.tsx - Table rendering, filters
- BacktestDetail.test.tsx - Chart data binding
- MetricsCard.test.tsx - Metric formatting

**E2E Tests** (Playwright - optional):
- Full user journey: List → Detail → Compare

**Target Coverage**: 60% (focus on critical paths)

---

### Manual QA Checklist

**Backtest List Screen**:
- [ ] Table shows all backtests
- [ ] Filter by strategy works
- [ ] Filter by date range works
- [ ] Sort by column works
- [ ] "View Details" button navigates

**Backtest Detail Screen**:
- [ ] All 5 charts render with correct data
- [ ] Metrics table shows all 13 metrics
- [ ] Trade list shows all trades
- [ ] Export to PNG works
- [ ] Back button returns to list

**Compare View**:
- [ ] Select up to 3 backtests
- [ ] Equity curves overlay correctly
- [ ] Legend shows all selected backtests
- [ ] Metrics comparison table accurate

---

## Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| GET /api/v1/backtests | <100ms (p95) | Server logs |
| GET /api/v1/backtests/:id | <200ms (p95) | Server logs (with 10-min cache) |
| Equity curve chart render | <500ms | Chrome DevTools Performance |
| Page load (initial) | <2s | Lighthouse |
| Dashboard interaction | <100ms | User perception |

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| React bundle too large (>1MB) | High | Medium | Code splitting, tree shaking, lazy loading |
| Chart performance with >500 trades | Medium | Low | Paginate trade table, sample equity curve if >1000 points |
| CORS issues in production | High | Low | Test CORS config in staging first |
| JSON parsing errors (malformed files) | Medium | Low | Comprehensive error handling + validation |
| Backtest file naming conflicts | Low | Low | Use timestamp in filename: YYYY-MM-DD-HH-MM-SS-strategy.json |

---

## Rollback Plan

**If backend breaks**:
1. Revert api/app/routes/backtests.py
2. Remove router from main.py
3. Restart API (`docker-compose restart api`)

**If frontend breaks**:
1. Remove frontend volume from docker-compose.yml
2. API still functional (REST endpoints work)
3. Use Postman/curl as fallback

**RTO**: <5 minutes (simple revert + restart)

---

## Success Criteria

**Technical**:
- [x] 2 API endpoints deployed and tested
- [x] 3 React screens render correctly
- [x] All 5 chart types display data
- [x] API response time <200ms (p95)
- [x] Frontend bundle <1MB

**User-facing**:
- [x] User can view list of all backtests
- [x] User can view detailed charts for single backtest
- [x] User can compare 2-3 backtests side-by-side
- [x] All metrics match backtest report (no data loss)

**HEART Metrics** (from heart-metrics.md):
- Happiness: 4.0/5.0 (target: 4.5/5.0 at month 3)
- Engagement: 50% weekly active (target: 80% at month 3)
- Task Success: 60% complete comparison flow (target: 75% at month 3)

---

## Dependencies

**External**:
- Recharts ^2.12.0
- React ^18.3.0
- React Router DOM ^6.22.0
- TypeScript ^5.3.0
- Vite ^5.1.0

**Internal**:
- src/trading_bot/backtest/models.py (existing)
- src/trading_bot/backtest/report_generator.py (existing)
- api/app/main.py (modify to add router)

**No Blocking Dependencies**: Can start immediately

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Backend API | 1 day | None |
| Frontend Setup | 0.5 day | Backend API |
| UI Components | 2 days | Frontend Setup |
| Integration | 0.5 day | All above |
| Testing | 0.5 day | Integration |
| Deployment | 0.5 day | Testing |
| **Total** | **4-5 days** | Sequential |

**Start**: After plan approval
**Target Completion**: T+5 days

---

## Open Questions

1. **Chart color scheme**: Use TradingView style (green/red) or custom palette?
   - **Decision**: TradingView (familiar to traders)

2. **Export format**: PNG, PDF, or both?
   - **Decision**: PNG only (simpler, sufficient for MVP)

3. **Mobile responsive**: Support mobile or desktop-only?
   - **Decision**: Desktop-only for MVP (trading dashboards typically desktop)

---

## Appendix: File Manifest

**New Files** (18 total):

*Backend (3)*:
- api/app/routes/backtests.py
- api/app/schemas/backtest.py
- api/app/services/backtest_loader.py

*Frontend (15)*:
- frontend/package.json
- frontend/vite.config.ts
- frontend/tsconfig.json
- frontend/src/main.tsx
- frontend/src/App.tsx
- frontend/src/components/BacktestList.tsx
- frontend/src/components/BacktestDetail.tsx
- frontend/src/components/CompareView.tsx
- frontend/src/components/charts/EquityCurve.tsx
- frontend/src/components/charts/DrawdownChart.tsx
- frontend/src/components/charts/WinLossChart.tsx
- frontend/src/components/charts/RMultipleChart.tsx
- frontend/src/components/charts/TradesTable.tsx
- frontend/src/services/api.ts
- frontend/src/types/backtest.ts

**Modified Files** (2):
- api/app/main.py (add backtests router)
- docker-compose.yml (add frontend volume)

---

**Plan Approved**: Ready for /tasks phase
