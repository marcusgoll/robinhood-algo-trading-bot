# Manual Acceptance Testing Checklist

**Feature**: status-dashboard
**Version**: 1.0.0
**Date**: 2025-10-16
**Tester**: _________________
**Environment**: _________________

## Test Environment Setup

- [ ] Python 3.11+ installed
- [ ] Repository cloned and up-to-date
- [ ] Package installed in development mode (`pip install -e .`)
- [ ] Robinhood credentials available (ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD)
- [ ] Trading account has at least one open position (for position display testing)
- [ ] At least one trade executed today (for performance metrics testing)

## Test Execution Instructions

1. Set environment variables before each test session
2. Launch dashboard using `python -m trading_bot dashboard`
3. Record observations in "Actual Result" column
4. Mark pass/fail in "Status" column (✅/❌)
5. Note any issues in "Notes" section

---

## Test Suite

### Section 1: Dashboard Startup (NFR-001)

**Target**: Dashboard launches within 2 seconds

| Test ID | Test Case | Expected Result | Actual Result | Status | Notes |
|---------|-----------|-----------------|---------------|--------|-------|
| TC001 | Launch dashboard with valid credentials | Dashboard displays within 2s, shows account data | | | |
| TC002 | Launch dashboard without credentials | Error message shown, graceful exit | | | |
| TC003 | Launch dashboard with invalid credentials | Authentication error shown, retry prompt | | | |
| TC004 | Launch dashboard with expired session | Auto re-authentication triggered, push notification sent | | | |

**Performance Measurement**:
```bash
time python -m trading_bot dashboard
```
Expected: <2s total startup time
Actual: _________ seconds

---

### Section 2: Account Status Display (FR-001)

**Target**: All account fields display correctly

| Test ID | Test Case | Expected Result | Actual Result | Status | Notes |
|---------|-----------|-----------------|---------------|--------|-------|
| TC005 | Verify buying power display | Buying power shows correct value with $ formatting | | | |
| TC006 | Verify account balance display | Account balance matches broker website | | | |
| TC007 | Verify cash balance display | Cash balance shown separately from positions | | | |
| TC008 | Verify day trade count display | Day trade count shows X/3 format | | | |
| TC009 | Verify timestamp display | Timestamp in UTC, ISO 8601 format | | | |
| TC010 | Verify market status | Shows OPEN (9:30 AM-4 PM ET) or CLOSED correctly | | | |

**Manual Verification**:
- [ ] Cross-check buying power with Robinhood mobile app
- [ ] Verify account balance matches broker website
- [ ] Confirm day trade count accuracy

---

### Section 3: Positions Display (FR-002)

**Target**: All open positions display with correct P&L calculation

| Test ID | Test Case | Expected Result | Actual Result | Status | Notes |
|---------|-----------|-----------------|---------------|--------|-------|
| TC011 | Display single position | Position shows: symbol, qty, entry, current, P&L% | | | |
| TC012 | Display multiple positions | All positions shown in table format | | | |
| TC013 | Display empty positions | "No positions" message shown when account has 0 holdings | | | |
| TC014 | P&L color coding | Green for profit (>0%), red for loss (<0%) | | | |
| TC015 | Position sorting | Positions sorted by unrealized P&L (descending) | | | |
| TC016 | Decimal precision | Prices show 2 decimal places ($150.25 format) | | | |

**Manual Verification**:
- [ ] Cross-check position quantities with broker
- [ ] Verify entry prices match actual purchase prices
- [ ] Calculate P&L manually: ((current - entry) / entry) * 100
- [ ] Confirm P&L matches broker's calculation

---

### Section 4: Performance Metrics (FR-003)

**Target**: Accurate metric calculation from trade logs

| Test ID | Test Case | Expected Result | Actual Result | Status | Notes |
|---------|-----------|-----------------|---------------|--------|-------|
| TC017 | Win rate calculation | Win rate = (winning trades / total trades) * 100 | | | |
| TC018 | Average R:R calculation | Avg R:R = mean of all trade risk-reward ratios | | | |
| TC019 | Total P&L calculation | Total P&L = realized P&L + unrealized P&L | | | |
| TC020 | Realized P&L display | Realized P&L matches sum of closed trade profits | | | |
| TC021 | Unrealized P&L display | Unrealized P&L matches open position P&L sum | | | |
| TC022 | Current streak display | Streak shows consecutive wins or losses | | | |
| TC023 | Trades today count | Trades today matches entries in today's log file | | | |
| TC024 | Max drawdown display | Max drawdown shows largest peak-to-trough decline | | | |
| TC025 | Session count display | Sessions counted correctly from distinct dates | | | |

**Manual Verification**:
- [ ] Count trades in `logs/YYYY-MM-DD.jsonl`
- [ ] Calculate win rate manually from log entries
- [ ] Verify P&L calculations match trade records

---

### Section 5: Auto-Refresh (FR-004)

**Target**: Dashboard refreshes every 5 seconds automatically

| Test ID | Test Case | Expected Result | Actual Result | Status | Notes |
|---------|-----------|-----------------|---------------|--------|-------|
| TC026 | Auto-refresh timing | Dashboard updates every 5 seconds | | | |
| TC027 | Timestamp updates | "Last Updated" timestamp increments with each refresh | | | |
| TC028 | Position price updates | Current prices update when market moves | | | |
| TC029 | No screen flicker | Display updates smoothly without flicker (Rich Live) | | | |
| TC030 | Refresh during typing | Typing commands not interrupted by auto-refresh | | | |

**Manual Verification**:
- [ ] Watch dashboard for 30 seconds, observe auto-refresh behavior
- [ ] Use stopwatch to time refresh interval
- [ ] Verify no visual artifacts or flicker during refresh

---

### Section 6: Manual Refresh (FR-005)

**Target**: R key triggers immediate refresh, bypassing timer

| Test ID | Test Case | Expected Result | Actual Result | Status | Notes |
|---------|-----------|-----------------|---------------|--------|-------|
| TC031 | Press R key | Dashboard refreshes immediately | | | |
| TC032 | Refresh performance | Refresh completes within 500ms (NFR-001) | | | |
| TC033 | Multiple rapid R presses | Dashboard handles rapid refresh requests without errors | | | |
| TC034 | Refresh confirmation | "Manual refresh queued (R)" message shown | | | |
| TC035 | Timestamp update after R | "Last Updated" timestamp changes to current time | | | |

**Performance Measurement**:
- Measure time from pressing R to display update
- Expected: <500ms
- Actual: _________ milliseconds

---

### Section 7: Export Functionality (FR-007)

**Target**: E key generates JSON + Markdown exports in <1 second

| Test ID | Test Case | Expected Result | Actual Result | Status | Notes |
|---------|-----------|-----------------|---------------|--------|-------|
| TC036 | Press E key | Export confirmation message shown | | | |
| TC037 | JSON export created | JSON file created in `logs/dashboard-export-*.json` | | | |
| TC038 | Markdown export created | Markdown file created in `logs/dashboard-export-*.md` | | | |
| TC039 | Export filename format | Filename includes date and timestamp | | | |
| TC040 | JSON content validity | JSON parseable, contains all dashboard data | | | |
| TC041 | Markdown content validity | Markdown formatted correctly, readable | | | |
| TC042 | Export performance | Export completes within 1 second (NFR-001) | | | |
| TC043 | Export without data | "Cannot export yet" message if no data loaded | | | |

**Manual Verification**:
- [ ] Open exported JSON file, verify structure
- [ ] Open exported Markdown file, verify formatting
- [ ] Confirm all data fields present in exports
- [ ] Check file permissions (should be readable)

**Performance Measurement**:
- Measure time from pressing E to export confirmation
- Expected: <1s
- Actual: _________ milliseconds

---

### Section 8: Help Display (FR-008)

**Target**: H key shows keyboard shortcuts overlay

| Test ID | Test Case | Expected Result | Actual Result | Status | Notes |
|---------|-----------|-----------------|---------------|--------|-------|
| TC044 | Press H key | Help overlay displays | | | |
| TC045 | Help content | Shows all commands: R, E, Q, H with descriptions | | | |
| TC046 | Help formatting | Text clear and readable | | | |
| TC047 | Continue after help | Dashboard continues normal operation after showing help | | | |

---

### Section 9: Quit Function (FR-009)

**Target**: Q key exits dashboard cleanly

| Test ID | Test Case | Expected Result | Actual Result | Status | Notes |
|---------|-----------|-----------------|---------------|--------|-------|
| TC048 | Press Q key | Dashboard exits within 1 second | | | |
| TC049 | Quit confirmation | "Quit requested (Q)" message shown | | | |
| TC050 | Clean exit | No error messages on exit | | | |
| TC051 | Event logging | `dashboard.exited` event written to logs | | | |
| TC052 | Ctrl+C quit | Dashboard exits cleanly on Ctrl+C interrupt | | | |

**Manual Verification**:
- [ ] Check `logs/dashboard-usage.jsonl` for `dashboard.exited` event
- [ ] Verify no orphaned processes after quit

---

### Section 10: Target Comparison (FR-005)

**Target**: Dashboard shows target comparison when config file exists

| Test ID | Test Case | Expected Result | Actual Result | Status | Notes |
|---------|-----------|-----------------|---------------|--------|-------|
| TC053 | Create targets.yaml | Dashboard loads targets on startup | | | |
| TC054 | Win rate target comparison | Shows actual vs target with ✓/✗ indicator | | | |
| TC055 | Daily P&L target comparison | Shows actual vs target with color coding | | | |
| TC056 | Trades per day target comparison | Shows actual vs target | | | |
| TC057 | Missing targets file | Dashboard works without targets, no crash | | | |
| TC058 | Invalid targets file | Warning logged, dashboard continues | | | |

**Manual Verification**:
- [ ] Create `config/dashboard-targets.yaml` with test values
- [ ] Restart dashboard, verify targets loaded
- [ ] Delete targets file, verify graceful degradation

---

### Section 11: Staleness Indicator (FR-016)

**Target**: Warning appears when data >60s old

| Test ID | Test Case | Expected Result | Actual Result | Status | Notes |
|---------|-----------|-----------------|---------------|--------|-------|
| TC059 | Wait 61+ seconds | "Data may be stale" warning appears | | | |
| TC060 | Warning message content | Shows seconds since last update | | | |
| TC061 | Press R to clear | Manual refresh clears staleness warning | | | |
| TC062 | Auto-refresh clears | Warning clears automatically on next refresh | | | |

**Manual Verification**:
- [ ] Note timestamp after launch
- [ ] Wait 65 seconds without pressing R
- [ ] Observe staleness warning appearance
- [ ] Press R to verify warning clears

---

### Section 12: Error Handling & Resilience

**Target**: Dashboard handles errors gracefully, no crashes

| Test ID | Test Case | Expected Result | Actual Result | Status | Notes |
|---------|-----------|-----------------|---------------|--------|-------|
| TC063 | Missing trade logs | Warning shown, metrics show 0% | | | |
| TC064 | API error during refresh | Error logged, last known data shown | | | |
| TC065 | Session expiry during operation | Auto re-authentication triggered | | | |
| TC066 | Network interruption | Error message shown, retries with backoff | | | |
| TC067 | Insufficient disk space | Export fails gracefully with error message | | | |
| TC068 | Windows console encoding | Plain text used instead of emojis (no crash) | | | |

**Negative Testing**:
- [ ] Disconnect network, observe error handling
- [ ] Fill disk to capacity, try export
- [ ] Force session expiry (wait 24+ hours)

---

### Section 13: Performance Benchmarks

**Target**: All operations meet performance targets (NFR-001, NFR-008)

| Test ID | Metric | Target | Measured | Status | Notes |
|---------|--------|--------|----------|--------|-------|
| TC069 | Dashboard startup time | <2s | | | |
| TC070 | Dashboard refresh cycle | <500ms | | | |
| TC071 | Export generation time | <1s | | | |
| TC072 | Memory footprint (1 hour operation) | <50MB | | | |
| TC073 | Rapid refresh performance (10x R key) | All <500ms | | | |

**Performance Measurement**:
```bash
# Startup time
time python -m trading_bot dashboard

# Memory footprint (in dashboard session)
# Windows: Task Manager → trading_bot process
# Linux/macOS: top -p <pid>

# Export timing: observe confirmation message latency
```

---

### Section 14: Platform Compatibility

**Target**: Dashboard works on Windows, Linux, macOS

| Test ID | Platform | Python Version | Status | Notes |
|---------|----------|----------------|--------|-------|
| TC074 | Windows 10/11 | 3.11+ | | |
| TC075 | Ubuntu 20.04+ | 3.11+ | | |
| TC076 | macOS 12+ | 3.11+ | | |
| TC077 | Terminal size 80x24 | Minimum viable | | |
| TC078 | Terminal size 100x30 | Optimal display | | |

---

## Summary

**Total Test Cases**: 78
**Passed**: _______
**Failed**: _______
**Skipped**: _______
**Pass Rate**: _______% (target: >95%)

## Critical Issues Found

| Issue ID | Severity | Description | Steps to Reproduce | Workaround |
|----------|----------|-------------|-------------------|------------|
| | | | | |
| | | | | |
| | | | | |

## Non-Critical Issues Found

| Issue ID | Severity | Description | Impact | Recommendation |
|----------|----------|-------------|--------|----------------|
| | | | | |
| | | | | |
| | | | | |

## Test Environment Details

- **OS**: _________________
- **Python Version**: _________________
- **Package Version**: _________________
- **Terminal**: _________________
- **Terminal Size**: _________________
- **Robinhood Account Type**: (Cash/Margin) _________________
- **Number of Open Positions**: _________________
- **Trades Executed Today**: _________________

## Tester Sign-Off

**Tester Name**: _________________
**Date**: _________________
**Signature**: _________________

**Recommendation**: (Pass/Fail/Conditional Pass)

**Comments**:
_________________
_________________
_________________

---

## Acceptance Criteria

Dashboard is considered ready for production deployment if:

✅ **Functional Requirements**: All FR-001 to FR-016 test cases pass (100%)
✅ **Performance Requirements**: All NFR-001, NFR-008 test cases pass (100%)
✅ **Error Handling**: All error scenarios handled gracefully (no crashes)
✅ **Platform Compatibility**: Works on at least 2 of 3 platforms (Windows/Linux/macOS)
✅ **Critical Issues**: Zero critical bugs found
✅ **Non-Critical Issues**: <5 minor issues acceptable (documented with workarounds)

**Overall Status**: (Pass/Fail) _________________

---

**Document Version**: 1.0
**Last Updated**: 2025-10-16
