# Tasks: Backtest Performance Dashboard

**Feature**: specs/032-backtest-performance-dashboard
**Created**: 2025-10-28
**Total Tasks**: 28

---

## [CODEBASE REUSE ANALYSIS]

**Scanned**: D:/Coding/Stocks (api/, src/, frontend/)

### [EXISTING - REUSE]

✅ **Backend Models** (src/trading_bot/backtest/models.py):
- BacktestResult - Complete backtest output with metrics, trades, equity curve
- PerformanceMetrics - Win rate, profit factor, max drawdown, Sharpe ratio
- Trade - Individual trade records with entry/exit, P&L
- BacktestConfig - Configuration for backtest runs

✅ **Report Generator** (src/trading_bot/backtest/report_generator.py):
- generate_json() - Exports BacktestResult to JSON (perfect for API!)
- generate_markdown() - Creates formatted reports

✅ **FastAPI Patterns** (api/app/):
- main.py - FastAPI 0.104.1, CORS configured, /api/v1/ prefix
- routes/state.py - REST router pattern
- services/state_aggregator.py - Service layer pattern
- schemas/state.py - Pydantic response models

### [NEW - CREATE]

🆕 **Backend API**:
- api/app/routes/backtests.py - 2 endpoints (list, detail)
- api/app/schemas/backtest.py - Pydantic models for responses
- api/app/services/backtest_loader.py - File loader + caching

🆕 **Frontend** (First React component!):
- frontend/ - React 18 + TypeScript 5 + Vite
- 3 UI screens (BacktestList, BacktestDetail, CompareView)
- 5 chart types (Recharts library)

---

## [DEPENDENCY GRAPH]

**Story completion order:**
1. Phase 1: Setup (T001-T003) - project structure
2. Phase 2: Backend API (T004-T009) - blocks frontend
3. Phase 3: US1 [P1] - View single backtest (T010-T019)
4. Phase 4: US2 [P2] - Compare strategies (T020-T023) - depends on US1 complete
5. Phase 5: Polish (T024-T028) - cross-cutting concerns

---

## [PARALLEL EXECUTION OPPORTUNITIES]

**Phase 1 (Setup):**
- T002, T003 can run in parallel (different package managers)

**Phase 2 (Backend):**
- T005, T006, T007 can run in parallel (different files)
- T008, T009 block on T004-T007 (need API to test)

**Phase 3 (US1):**
- T011, T012, T013 can run in parallel (different chart components)
- T014 blocks on T011-T013 (integrates charts)
- T017, T018, T019 can run in parallel (different screens)

**Phase 4 (US2):**
- T020, T021 can run in parallel (different components)

**Phase 5 (Polish):**
- T024, T025, T026, T027 can run in parallel (independent concerns)

---

## [IMPLEMENTATION STRATEGY]

**MVP Scope**: Phase 3 (US1) only - single backtest view

**Incremental delivery**:
1. Backend API (T004-T009) → test with curl
2. US1 (T010-T019) → manual QA → staging validation
3. US2 (T020-T023) → post-MVP iteration
4. Polish (T024-T028) → production readiness

**Testing approach**: Integration tests only (no unit tests requested in spec)
- Backend: Test 2 API endpoints
- Frontend: Manual QA checklist (no automated UI tests)

---

## Phase 1: Setup

**Goal**: Initialize project structure for React + FastAPI dashboard

- [ ] T001 Create frontend directory structure
  - Directories: frontend/src/{components,services,types,assets}
  - Files: package.json, tsconfig.json, vite.config.ts, .gitignore
  - Pattern: Modern React + Vite structure (see React docs)
  - From: plan.md "Frontend Components"

- [ ] T002 [P] Install frontend dependencies
  - File: frontend/package.json
  - Dependencies: react@18.3.0, react-dom@18.3.0, react-router-dom@6.22.0, recharts@2.12.0, @types/react@18.3.0, typescript@5.3.0, vite@5.1.0
  - Dev dependencies: @vitejs/plugin-react, eslint, prettier
  - From: plan.md "Dependencies"

- [ ] T003 [P] Configure Vite build system
  - File: frontend/vite.config.ts
  - Settings: React plugin, port 3000, proxy API requests to localhost:8000
  - Bundle target: <1MB (code splitting enabled)
  - From: plan.md "Architecture Decisions - React + TypeScript"

---

## Phase 2: Backend API (blocking prerequisites)

**Goal**: Create 2 FastAPI endpoints serving backtest JSON data

- [ ] T004 [P] Create Pydantic response schemas in api/app/schemas/backtest.py
  - Models: BacktestListResponse, BacktestDetailResponse, BacktestSummary
  - Fields: Match BacktestResult from src/trading_bot/backtest/models.py
  - Validation: Email format, date ranges, non-negative numbers
  - REUSE: Pattern from api/app/schemas/state.py
  - From: plan.md "API Contract"

- [ ] T005 [P] Create backtest loader service in api/app/services/backtest_loader.py
  - Methods: list_backtests(), get_backtest(id), scan_directory()
  - Logic: Read JSON files from backtest_results/ directory
  - Caching: 10-minute TTL using @lru_cache decorator
  - Error handling: FileNotFoundError → 404, JSONDecodeError → 500
  - REUSE: Pattern from api/app/services/state_aggregator.py
  - From: plan.md "Integration Points - Backtest JSON Files → API"

- [ ] T006 [P] Create GET /api/v1/backtests endpoint in api/app/routes/backtests.py
  - Response: List[BacktestSummary] with pagination (limit 50)
  - Query params: strategy (optional), start_date (optional), end_date (optional)
  - HTTP codes: 200 OK, 400 Bad Request (invalid dates)
  - REUSE: Pattern from api/app/routes/state.py
  - From: plan.md "API Contract: GET /api/v1/backtests"

- [ ] T007 [P] Create GET /api/v1/backtests/:id endpoint in api/app/routes/backtests.py
  - Response: BacktestDetailResponse with full equity curve, trades, metrics
  - HTTP codes: 200 OK, 404 Not Found (invalid ID)
  - Caching: Server-side 10-minute cache
  - REUSE: Pattern from api/app/routes/state.py
  - From: plan.md "API Contract: GET /api/v1/backtests/:id"

- [ ] T008 Register backtests router in api/app/main.py
  - Code: app.include_router(backtests.router, prefix="/api/v1")
  - OpenAPI tag: "backtests" with description
  - REUSE: Pattern from api/app/main.py (state, metrics routers)
  - From: plan.md "Component Architecture - Backend"

- [ ] T009 Write integration test for backtest API endpoints
  - File: api/tests/integration/test_backtests_api.py
  - Tests: GET /api/v1/backtests (200, empty list), GET /api/v1/backtests/:id (200, 404)
  - Setup: Create fixture JSON file in backtest_results/
  - Pattern: api/tests/integration/test_status_orchestrator_integration.py
  - Coverage: ≥80% for new endpoints
  - From: plan.md "Testing Strategy - Backend Tests"

---

## Phase 3: User Story 1 [P1] - View Single Backtest

**Story Goal**: Traders can visualize backtest results with 5 interactive charts

**Independent Test Criteria** (from spec.md Scenario 1):
- [ ] Dashboard loads in <2 seconds (P95)
- [ ] All 5 charts render without errors
- [ ] Metrics match console log output exactly

### Frontend Core Setup

- [ ] T010 Create TypeScript type definitions in frontend/src/types/backtest.ts
  - Interfaces: BacktestResult, PerformanceMetrics, Trade, EquityCurvePoint
  - Match API response schema from api/app/schemas/backtest.py
  - Export types for components
  - From: plan.md "Data Model & Contracts"

- [ ] T011 [P] [US1] Create EquityCurve chart component in frontend/src/components/charts/EquityCurve.tsx
  - Chart: Recharts LineChart (X=date, Y=equity)
  - Props: data: EquityCurvePoint[], loading: boolean
  - Interaction: Tooltip shows date + balance on hover
  - Color: Green line (#10b981), white background
  - REUSE: Recharts library patterns
  - From: spec.md FR-004 "Dashboard shall display equity curve chart"

- [ ] T012 [P] [US1] Create DrawdownChart component in frontend/src/components/charts/DrawdownChart.tsx
  - Chart: Recharts AreaChart (X=date, Y=drawdown %)
  - Calculation: (peak - current) / peak * 100
  - Color: Red fill (#ef4444) to emphasize losses
  - Tooltip: Show date + drawdown percentage
  - REUSE: Recharts library patterns
  - From: spec.md FR-005 "Dashboard shall display drawdown chart"

- [ ] T013 [P] [US1] Create WinLossChart component in frontend/src/components/charts/WinLossChart.tsx
  - Chart: Recharts BarChart (X=P&L buckets, Y=trade count)
  - Buckets: [-$500+, -$400 to -$300, ..., $0 to $100, $100+]
  - Colors: Red bars for losses, green for wins
  - Tooltip: Show bucket range + trade count
  - REUSE: Recharts library patterns
  - From: spec.md FR-006 "Dashboard shall display win/loss distribution"

- [ ] T014 [US1] Create RMultipleChart component in frontend/src/components/charts/RMultipleChart.tsx
  - Chart: Recharts Histogram (X=R-multiple buckets, Y=frequency)
  - Buckets: [-2R, -1R, 0R, 1R, 2R, 3R+]
  - Definition: R-multiple = (exit - entry) / (entry - stop_loss)
  - Tooltip: Show bucket + trade frequency
  - REUSE: Recharts library patterns
  - From: spec.md FR-007 "Dashboard shall display R-multiple histogram"

- [ ] T015 [US1] Create MetricsTable component in frontend/src/components/MetricsTable.tsx
  - Data: PerformanceMetrics (win rate, profit factor, Sharpe ratio, max drawdown, total return)
  - Format: Currency ($X,XXX.XX), percentages (XX.XX%), ratios (X.XX)
  - Layout: 2-column table (metric name | value)
  - REUSE: Standard HTML table with Tailwind CSS
  - From: spec.md FR-008 "Dashboard shall display performance metrics table"

- [ ] T016 [US1] Create TradesTable component in frontend/src/components/TradesTable.tsx
  - Columns: Symbol, Entry Date, Entry Price, Exit Date, Exit Price, Shares, P&L, P&L %, Duration, Exit Reason
  - Sorting: Click column header to sort
  - Filtering: Search by symbol, date range picker, win/loss toggle
  - Pagination: 20 trades per page
  - REUSE: Standard HTML table with Tailwind CSS
  - From: spec.md FR-009 "Users shall filter trade list"

### API Client

- [ ] T017 [P] [US1] Create API client service in frontend/src/services/api.ts
  - Methods: fetchBacktests(), fetchBacktestDetail(id)
  - Base URL: http://localhost:8000 (dev), process.env.VITE_API_URL (prod)
  - Error handling: Throw on non-200, parse JSON error messages
  - Types: Use BacktestResult types from frontend/src/types/backtest.ts
  - From: plan.md "Frontend Components - services/api.ts"

### Main Screens

- [ ] T018 [P] [US1] Create BacktestDetail screen in frontend/src/components/BacktestDetail.tsx
  - Route: /backtests/:id
  - Layout: Header (strategy name, date range, metrics) + 5 charts + trades table
  - State: useState for loading, error, data
  - API call: useEffect(() => fetchBacktestDetail(id), [id])
  - Loading: Skeleton loaders for charts
  - Error: Show error message + retry button
  - From: design/screens.yaml "backtest_detail"

- [ ] T019 [P] [US1] Create BacktestList screen in frontend/src/components/BacktestList.tsx
  - Route: /backtests
  - Layout: Header + search/filter bar + table (strategy, date range, win rate, total return)
  - Action: "View Details" button navigates to /backtests/:id
  - State: useState for backtests list, loading, filters
  - API call: useEffect(() => fetchBacktests(), [])
  - Empty state: "No backtests yet. Run your first backtest to see performance data."
  - From: design/screens.yaml "backtest_list"

---

## Phase 4: User Story 2 [P2] - Compare Multiple Strategies

**Story Goal**: Traders can overlay 2-3 equity curves for side-by-side comparison

**Depends on**: Phase 3 complete (US1 components)

**Independent Test Criteria** (from spec.md Scenario 2):
- [ ] Maximum 3 backtests can be compared simultaneously
- [ ] Color legend clearly distinguishes each strategy
- [ ] Export generates valid PNG file

### Implementation

- [ ] T020 [P] [US2] Create CompareView screen in frontend/src/components/CompareView.tsx
  - Route: /backtests/compare
  - Layout: MultiSelect dropdown (select up to 3 backtests) + overlaid equity curve chart + metrics comparison table
  - State: useState for selected backtests (max 3), loading, comparison data
  - API calls: Fetch multiple backtests in parallel (Promise.all)
  - Overlay: Different colors per backtest (blue, green, orange)
  - Legend: Show strategy names with color indicators
  - From: design/screens.yaml "compare_view"

- [ ] T021 [P] [US2] Add export to PNG functionality
  - Library: html2canvas to capture chart as image
  - Button: "Export Comparison" triggers download
  - Filename: backtest-comparison-YYYY-MM-DD.png
  - From: spec.md Scenario 2 "Trader exports comparison as PNG"

### Routing

- [ ] T022 [US2] Create App router in frontend/src/App.tsx
  - Library: react-router-dom v6
  - Routes: / (redirect to /backtests), /backtests (BacktestList), /backtests/:id (BacktestDetail), /backtests/compare (CompareView)
  - Nav: Header with links to List and Compare
  - From: plan.md "Frontend Components - App.tsx"

- [ ] T023 [US2] Create main entry point in frontend/src/main.tsx
  - Setup: ReactDOM.render(<App />)
  - Providers: React Router BrowserRouter
  - Global styles: Import Tailwind CSS
  - From: plan.md "Frontend Components - main.tsx"

---

## Phase 5: Polish & Cross-Cutting Concerns

**Goal**: Production readiness - error handling, deployment, documentation

### Error Handling

- [ ] T024 [P] Add global error boundary in frontend/src/components/ErrorBoundary.tsx
  - Catch: React component errors
  - Display: Friendly error message + "Refresh page" button
  - Logging: console.error with stack trace
  - Pattern: React Error Boundary docs
  - From: plan.md "Risks & Mitigations - React bundle too large"

- [ ] T025 [P] Add API error handling with retry logic
  - Decorator: Retry on 5xx errors (max 3 attempts, exponential backoff)
  - Timeout: 5s per request
  - User feedback: Toast notification for errors
  - From: plan.md "Risks & Mitigations - JSON parsing errors"

### Deployment

- [ ] T026 [P] Update docker-compose.yml to serve React build
  - Volumes: ./backtest_results:/app/backtest_results:ro, ./frontend/dist:/app/static:ro
  - FastAPI: Serve static files from /app/static (StaticFiles mount)
  - Pattern: docker-compose.yml existing volumes
  - From: plan.md "Integration Points - FastAPI → React Frontend"

- [ ] T027 [P] Add build script to frontend/package.json
  - Script: "build": "vite build"
  - Output: frontend/dist/ (optimized bundle)
  - Target: <1MB bundle size (check with vite-bundle-visualizer)
  - From: plan.md "Performance Targets"

### Documentation

- [ ] T028 Document rollback procedure in specs/032-backtest-performance-dashboard/NOTES.md
  - Procedure: Remove frontend volume from docker-compose.yml, restart API
  - Fallback: API endpoints still work (use Postman/curl)
  - RTO: <5 minutes (simple revert + restart)
  - From: plan.md "Rollback Plan"

---

## Manual QA Checklist (Post-Implementation)

**Run after Phase 5 complete, before deployment:**

### Backtest List Screen
- [ ] Table shows all backtests
- [ ] Filter by strategy works
- [ ] Filter by date range works
- [ ] Sort by column works (click header)
- [ ] "View Details" button navigates to detail page

### Backtest Detail Screen
- [ ] All 5 charts render with correct data
- [ ] Equity curve shows upward trend (sample data)
- [ ] Drawdown chart shows red fill
- [ ] Win/loss distribution shows green (wins) + red (losses) bars
- [ ] R-multiple histogram shows frequency distribution
- [ ] Metrics table shows all 13 metrics formatted correctly
- [ ] Trade list shows all trades
- [ ] Trade list filter by symbol works
- [ ] Back button returns to list

### Compare View
- [ ] Select up to 3 backtests from dropdown
- [ ] Equity curves overlay correctly with different colors
- [ ] Legend shows all selected backtests
- [ ] Metrics comparison table shows side-by-side data
- [ ] Export to PNG downloads valid image file

### Performance
- [ ] Dashboard loads in <2 seconds (P95) - test with Chrome DevTools Network
- [ ] Charts render in <500ms - test with Chrome DevTools Performance
- [ ] API responses <200ms (P95) - test with server logs

---

**Total**: 28 tasks
- Phase 1 (Setup): 3 tasks
- Phase 2 (Backend): 6 tasks
- Phase 3 (US1): 10 tasks
- Phase 4 (US2): 4 tasks
- Phase 5 (Polish): 5 tasks

**MVP Scope**: Phases 1-3 (19 tasks) for first release
**Post-MVP**: Phase 4 (comparison feature)
**Production Ready**: Phase 5 (error handling + deployment)
