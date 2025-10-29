# Preview Testing Checklist: Backtest Performance Dashboard

**Generated**: 2025-10-28
**Tester**: [Your name]
**Feature**: 032-backtest-performance-dashboard

---

## Testing Instructions

This dashboard requires:
1. **Backend API** running on port 8000
2. **Frontend dev server** running on port 3000
3. **Sample backtest data** in `backtest_results/` directory

### Setup Steps

```bash
# 1. Start backend API
cd api && uvicorn app.main:app --reload

# 2. Start frontend (in new terminal)
cd frontend && npm run dev

# 3. Create sample backtest data (if needed)
mkdir -p backtest_results
# Add sample JSON files or run actual backtest
```

---

## Routes to Test

- [ ] http://localhost:3000/ (Backtest List)
- [ ] http://localhost:3000/backtest/:id (Backtest Detail)

---

## User Scenarios

### Scenario 1: View Backtest List

- [ ] **Test**: Open http://localhost:3000/
- [ ] **Expected**: List of backtests loads in <2 seconds
- [ ] **Expected**: Cards show strategy name, symbols, date range
- [ ] **Expected**: Cards show key metrics (total return, win rate, trades)
- [ ] **Result**: [Pass/Fail]
- [ ] **Notes**: [Any issues]

### Scenario 2: Filter Backtests by Strategy

- [ ] **Test**: Use strategy dropdown filter
- [ ] **Expected**: List updates immediately
- [ ] **Expected**: Only matching backtests shown
- [ ] **Result**: [Pass/Fail]
- [ ] **Notes**: [Any issues]

### Scenario 3: Filter by Date Range

- [ ] **Test**: Select start/end dates
- [ ] **Expected**: List filters correctly
- [ ] **Expected**: Clear filters button appears
- [ ] **Result**: [Pass/Fail]
- [ ] **Notes**: [Any issues]

### Scenario 4: View Backtest Detail

- [ ] **Test**: Click on a backtest card
- [ ] **Expected**: Detail page loads in <2 seconds
- [ ] **Expected**: All 4 charts render: Equity Curve, Drawdown, Win/Loss, R-Multiple
- [ ] **Expected**: Metrics table shows 13 metrics
- [ ] **Expected**: Trades table shows all trades with pagination (20/page)
- [ ] **Result**: [Pass/Fail]
- [ ] **Notes**: [Any issues]

### Scenario 5: Navigate Trades Table

- [ ] **Test**: Click column headers to sort
- [ ] **Expected**: Table sorts by clicked column
- [ ] **Expected**: Arrow indicator shows sort direction
- [ ] **Result**: [Pass/Fail]
- [ ] **Notes**: [Any issues]

### Scenario 6: Paginate Through Trades

- [ ] **Test**: Click "Next" button on trades table
- [ ] **Expected**: Next 20 trades load
- [ ] **Expected**: Page indicator updates
- [ ] **Result**: [Pass/Fail]
- [ ] **Notes**: [Any issues]

### Scenario 7: Return to List

- [ ] **Test**: Click "← Back to list" link
- [ ] **Expected**: Returns to list view
- [ ] **Expected**: Filters preserved (if any)
- [ ] **Result**: [Pass/Fail]
- [ ] **Notes**: [Any issues]

---

## Acceptance Criteria

### Data Loading
- [ ] Backtest list loads in <2 seconds
- [ ] Backtest detail loads in <2 seconds
- [ ] Loading states displayed during fetch
- [ ] Error states shown if API fails

### API Integration
- [ ] GET /api/v1/backtests returns list
- [ ] GET /api/v1/backtests/:id returns detail
- [ ] 404 handling works for missing backtest
- [ ] Retry logic works (check Network tab for 3 attempts on failure)

### Charts
- [ ] Equity curve chart renders with data
- [ ] Drawdown chart shows negative percentages
- [ ] Win/Loss chart colors trades (green/red)
- [ ] R-Multiple histogram shows distribution
- [ ] Charts responsive to window resize

### Metrics Table
- [ ] 13 metrics displayed in grid layout
- [ ] Highlighted metrics visible (Total Return, Win Rate, Sharpe, Max Drawdown)
- [ ] Values formatted correctly (%, $, decimals)

### Trades Table
- [ ] All trades listed
- [ ] Sortable columns work (click header)
- [ ] Pagination works (20 trades per page)
- [ ] P&L colored (green positive, red negative)

---

## Visual Validation

### Layout & Spacing
- [ ] Cards in list view aligned in grid
- [ ] Consistent spacing between sections
- [ ] Charts sized appropriately (no overflow)
- [ ] Tables fit viewport width

### Colors & Typography
- [ ] Dark theme applied (background #0f172a)
- [ ] Text readable (white on dark)
- [ ] Positive values green (#22c55e)
- [ ] Negative values red (#ef4444)
- [ ] Font sizes appropriate

### Interactive Elements
- [ ] Hover states on cards
- [ ] Hover states on buttons/links
- [ ] Click feedback on interactive elements
- [ ] Focus indicators visible (Tab navigation)

### Responsive Design
- [ ] Desktop (1920x1080): All charts visible
- [ ] Laptop (1366x768): No horizontal scroll
- [ ] Tablet (768x1024): Grid adjusts to 1 column
- [ ] Mobile (375x667): Stacked layout, readable text

---

## Browser Testing

- [ ] Chrome (latest) - Version: _____
- [ ] Firefox (latest) - Version: _____
- [ ] Safari (latest) - Version: _____
- [ ] Edge (latest) - Version: _____
- [ ] Mobile Safari (iOS) - Version: _____
- [ ] Chrome Mobile (Android) - Version: _____

**Testing device**: [Device name/OS]

**Primary browser**: [Chrome/Firefox/Safari/Edge]

---

## Accessibility

### Keyboard Navigation
- [ ] Tab through backtest cards (visible focus)
- [ ] Tab through filters (dropdowns, date pickers)
- [ ] Tab through trades table (sortable headers)
- [ ] Enter key activates links/buttons
- [ ] Escape key closes modals (if any)

### Screen Reader
- [ ] Page title announced
- [ ] Chart titles announced
- [ ] Table headers announced
- [ ] Link purposes clear

**Screen reader tested**: [NVDA/VoiceOver/JAWS/None]

### Visual Accessibility
- [ ] Color contrast sufficient (4.5:1 text, 3:1 UI)
- [ ] Positive/negative distinguishable without color
- [ ] Focus indicators visible (at least 2px border)
- [ ] Text readable at 200% zoom

---

## Performance

### Console Checks
- [ ] No JavaScript errors in console
- [ ] No network errors (check 404s, 500s)
- [ ] No React warnings
- [ ] No memory leaks (check after 5 min usage)

### Load Times
- [ ] Initial page load: _____ seconds (target: <2s)
- [ ] Backtest list API: _____ ms (target: <100ms)
- [ ] Backtest detail API: _____ ms (target: <200ms)
- [ ] Chart rendering: _____ ms (target: <500ms)

### Interactions
- [ ] Filter updates feel instant (<100ms)
- [ ] Sorting feels instant (<100ms)
- [ ] Navigation smooth (no janks)
- [ ] Charts render without lag

---

## Error Handling

### API Errors
- [ ] Test: Stop API server, reload page
- [ ] **Expected**: Error message displayed
- [ ] **Expected**: Retry button or instructions shown
- [ ] **Result**: [Pass/Fail]

### Missing Data
- [ ] Test: Navigate to /backtest/invalid-id
- [ ] **Expected**: 404 error shown
- [ ] **Expected**: "Backtest not found" message
- [ ] **Expected**: Link back to list
- [ ] **Result**: [Pass/Fail]

### Empty State
- [ ] Test: Empty backtest_results/ directory
- [ ] **Expected**: "No backtests found" message
- [ ] **Expected**: Instructions or empty state graphic
- [ ] **Result**: [Pass/Fail]

---

## Edge Cases

### Large Dataset
- [ ] Test: Backtest with 500+ trades
- [ ] **Expected**: Pagination works correctly
- [ ] **Expected**: No performance degradation
- [ ] **Result**: [Pass/Fail]

### Long Strategy Names
- [ ] Test: Strategy name >50 characters
- [ ] **Expected**: Text truncates or wraps
- [ ] **Expected**: No layout breaking
- [ ] **Result**: [Pass/Fail]

### Extreme Values
- [ ] Test: Backtest with -99% return (total loss)
- [ ] **Expected**: Charts render correctly
- [ ] **Expected**: Negative values colored red
- [ ] **Result**: [Pass/Fail]

---

## Integration Testing

### Backend API
- [ ] GET /api/v1/backtests returns valid JSON
- [ ] Response matches Pydantic schema
- [ ] Filtering works (strategy, dates, limit)
- [ ] GET /api/v1/backtests/:id returns valid JSON
- [ ] Caching works (check response time on 2nd request)

### Frontend Build
- [ ] Production build succeeds: `npm run build`
- [ ] Bundle size <1MB: _____ KB (target: 573 KB)
- [ ] No build warnings critical
- [ ] Dist files generated correctly

---

## Issues Found

*Document any issues below with format:*

### Issue 1: [Title]
- **Severity**: Critical | High | Medium | Low
- **Location**: [URL or component]
- **Description**: [What's wrong]
- **Expected**: [What should happen]
- **Actual**: [What actually happens]
- **Browser**: [Affected browsers]
- **Screenshot**: [Path if captured]

---

## Test Data Requirements

Minimum test data needed:

```json
// backtest_results/test_001.json
{
  "config": {
    "strategy": "MeanReversion",
    "symbols": ["AAPL", "MSFT"],
    "start_date": "2024-01-01",
    "end_date": "2024-03-31",
    "initial_capital": 100000.0,
    "commission": 0.001,
    "slippage_pct": 0.001
  },
  "metrics": {
    "total_return": 15.5,
    "annualized_return": 62.0,
    "cagr": 58.5,
    "win_rate": 0.65,
    "profit_factor": 2.1,
    "average_win": 450.0,
    "average_loss": -200.0,
    "max_drawdown": -8.5,
    "max_drawdown_duration_days": 12,
    "sharpe_ratio": 1.85,
    "total_trades": 42,
    "winning_trades": 27,
    "losing_trades": 15
  },
  "trades": [
    {
      "symbol": "AAPL",
      "entry_date": "2024-01-05",
      "entry_price": 150.0,
      "exit_date": "2024-01-15",
      "exit_price": 155.0,
      "shares": 100,
      "pnl": 500.0,
      "pnl_pct": 3.33,
      "duration_days": 10,
      "exit_reason": "target",
      "commission": 0.15,
      "slippage": 0.15
    }
  ],
  "equity_curve": [
    {"timestamp": "2024-01-01", "equity": 100000.0},
    {"timestamp": "2024-01-05", "equity": 99500.0},
    {"timestamp": "2024-01-15", "equity": 100000.0}
  ],
  "data_warnings": [],
  "metadata": {"completed_at": "2024-10-28T12:00:00Z"}
}
```

**Create at least 3 sample backtests** for comprehensive testing.

---

## Test Results Summary

**Total scenarios tested**: ___ / 7
**Total criteria validated**: ___ / 50+
**Browsers tested**: ___ / 6
**Issues found**: ___

**Overall status**:
- [ ] ✅ Ready to ship (0 critical issues)
- [ ] ⚠️ Minor issues (document and ship)
- [ ] ❌ Blocking issues (fix before shipping)

**Tester signature**: _______________
**Date**: _______________

**Next step**: [/debug for fixes | /ship-staging for deployment]
