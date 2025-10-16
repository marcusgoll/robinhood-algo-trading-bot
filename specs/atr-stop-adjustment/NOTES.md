# Feature: ATR-based dynamic stop-loss adjustment

## Overview

Enhancement to existing stop-loss automation that adds ATR (Average True Range) based dynamic stop calculation. ATR is a volatility indicator that adapts stop distances to market conditions - wider stops in volatile markets to avoid premature stop-outs, tighter stops in calm markets for better capital protection.

## Research Findings

### Finding 1: Existing Stop-Loss Infrastructure
- Source: specs/stop-loss-automation/spec.md
- Current implementation supports fixed stop-loss calculation based on pullback lows or percentage-based fallback
- RiskManager, StopAdjuster, and Calculator modules already exist in src/trading_bot/risk_management/
- Current stop logic: Identify pullback low OR use default 2% stop distance
- Limitation: Static stop distances don't adapt to volatility - same 2% stop applies regardless of whether market is calm or volatile

### Finding 2: Current Stop Adjustment Strategy
- Source: src/trading_bot/risk_management/stop_adjuster.py
- StopAdjuster exists with trailing stop logic (activation_pct=10%, trailing_distance_pct=5%)
- Current adjustment: Move to breakeven at 50% target progress
- Limitation: Trailing stops use fixed percentages, not volatility-adjusted

### Finding 3: Position Sizing Foundation
- Source: src/trading_bot/risk_management/calculator.py
- calculate_position_plan() already handles risk-based position sizing
- Validates stop distance bounds (0.5% exact or 0.7%-10% range)
- Calculates risk/reward ratios and validates against minimum thresholds
- Integration point: Can extend to accept ATR-based stops instead of pullback-based stops

### Finding 4: Constitution Risk Management Requirements
- Source: .spec-flow/memory/constitution.md
- §Risk_Management mandates stop losses on every position
- §Safety_First requires fail-safe design - errors must halt trading
- §Data_Integrity requires validation of market data completeness
- §Testing_Requirements demands 90%+ test coverage for financial code
- Compliance: ATR calculation must validate data quality and handle missing data gracefully

### Finding 5: ATR Implementation Strategy
- Decision: ATR (Average True Range) is a volatility indicator that measures price movement
- Calculation: ATR = average of true ranges over N periods (typically 14)
- True Range = max(high - low, |high - previous_close|, |low - previous_close|)
- Application: Use ATR multiplier for stop distance (e.g., 2.0 * ATR for wider stop in volatile markets)
- Benefit: In volatile markets, stops widen automatically to avoid premature stop-outs
- Benefit: In calm markets, stops tighten to protect capital more aggressively

## System Components Analysis

**Existing Components (from risk_management package)**:
- RiskManager (orchestrator) - Entry point for risk planning
- Calculator (position sizing and validation) - Core logic location
- StopAdjuster (trailing stop logic) - Needs ATR integration
- PullbackAnalyzer (swing low detection) - Parallel logic, not replaced
- TargetMonitor (fill detection) - No changes needed

**New Components Needed**:
- ATRCalculator: Calculate ATR from price data (high, low, close over N periods)
- ATRStopStrategy: Determine stop price using ATR multiplier instead of pullback low
- Configuration extension: Add atr_enabled, atr_period, atr_multiplier to RiskManagementConfig

**Integration Strategy**:
- Enhance calculate_position_plan() to accept optional atr_data parameter
- When atr_enabled=true, use ATR-based stop calculation instead of pullback analysis
- Fall back to pullback/percentage stops when ATR data unavailable
- Maintain backward compatibility - existing pullback logic remains default

## Feature Classification
- UI screens: false
- Improvement: true
- Measurable: true
- Deployment impact: false

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-16
- Phase 1 (Plan): 2025-10-16
- Phase 2 (Tasks): 2025-10-16

## Phase 2 Summary: Task Breakdown

**Task Statistics**:
- Total tasks: 37
- TDD coverage: 27/37 tasks (73%) follow RED→GREEN→REFACTOR cycle
- Parallel tasks: 14 tasks marked [P] can run in parallel

**Task Breakdown by Phase**:
- Phase 3.1 Setup: 4 tasks (dataclasses, exceptions, config extension)
- Phase 3.2 RED: 13 tasks (failing tests for ATR calculation, validation, integration)
- Phase 3.3 GREEN: 9 tasks (minimal implementation to pass tests)
- Phase 3.4 REFACTOR: 3 tasks (code quality improvements)
- Phase 3.5 Integration: 4 tasks (end-to-end workflow tests)
- Phase 3.6 Error Handling: 3 tasks (resilience and edge cases)
- Phase 3.7 Deployment: 3 tasks (smoke tests, documentation, rollback)

**Task Breakdown by Category**:
- Backend (risk_management): 26 tasks
- Market data integration: 3 tasks
- Test files: 13 tasks
- Configuration & documentation: 5 tasks

**Key Implementation Decisions**:
- TDD discipline: RED→GREEN→REFACTOR cycle for all core behaviors
- Reuse leverage: 8 existing components (Calculator, StopAdjuster, Config, etc.)
- New components: 5 (ATRCalculator, ATRStopData, PriceBar, 3 exception classes)
- Files modified: 6 existing files
- Files created: 5 new files + 6 test files

**Ready for**: /analyze (cross-artifact consistency analysis)

## Task Completion Log

### Phase 3.1 Setup (Parallel Batch 1)
✅ T001 [P]: Add PriceBar dataclass to src/trading_bot/market_data/data_models.py
✅ T002 [P]: Add ATRStopData dataclass to src/trading_bot/risk_management/models.py
✅ T003 [P]: Add ATR exception classes to src/trading_bot/risk_management/exceptions.py
✅ T004 [P]: Extend RiskManagementConfig with ATR fields in src/trading_bot/risk_management/config.py

### Phase 3.2 RED (Test-Driven Development - Failing Tests)
✅ T005 [RED]: Write test: ATR calculation with valid 14-period data
✅ T006 [RED]: Write test: ATR calculation fails with insufficient data
✅ T007 [RED]: Write test: ATR calculation validates price bar integrity
✅ T008 [RED]: Write test: ATRCalculator.calculate_atr_stop() for long positions
✅ T009 [RED]: Write test: ATRCalculator.validate_atr_stop() checks distance bounds
✅ T010 [RED]: Write test: ATRCalculator.validate_atr_stop() rejects >10% stops
✅ T011 [RED]: Write test: Calculator.calculate_position_plan() with ATR data
✅ T013 [RED]: Write test: ATR calculation performance <50ms

### Phase 3.5 Integration (T028-T031)
✅ T028 [RED]: Write test: End-to-end ATR workflow (test_integration_atr.py)

## Rollback Procedures

### Pre-Deployment Validation
Before enabling ATR in production, verify these prerequisites:
- [ ] All 14 ATR tests passing (8 calculator + 1 calculator integration + 2 stop adjuster + 3 integration)
- [ ] Performance benchmarks met (ATR calculation <50ms, actual: <1ms)
- [ ] Error documentation reviewed by operations team
- [ ] Monitoring alerts configured (P0/P1/P2/P3 as documented in error-log.md)
- [ ] Staging validation completed with real market data

### Emergency Rollback (Same-Day Issues)

**Trigger Conditions**:
- ATR calculation failures >10% of attempts
- Position sizing errors causing incorrect stop placements
- Performance degradation (ATR calculation >100ms consistently)
- Data corruption affecting multiple symbols
- Systematic test failures in production

**Rollback Steps** (15-30 minutes):

1. **Immediate Stop** (0-5 minutes):
   ```bash
   # SSH into production server
   cd /path/to/stocks

   # Disable ATR feature flag
   git checkout config/risk_management.json
   sed -i 's/"atr_enabled": true/"atr_enabled": false/' config/risk_management.json

   # Restart trading service
   systemctl restart trading-bot

   # Verify rollback
   journalctl -u trading-bot -f | grep "ATR: disabled"
   ```

2. **Verify System State** (5-10 minutes):
   - Confirm all open positions using pullback/percentage stops (not ATR)
   - Check error logs for ATR-related errors stopped occurring
   - Verify position planning working with fallback stops
   - Monitor next 3 trade entries to ensure pullback logic active

3. **Preserve Evidence** (10-15 minutes):
   ```bash
   # Capture logs for investigation
   journalctl -u trading-bot --since "1 hour ago" > /tmp/atr-rollback-$(date +%Y%m%d-%H%M).log

   # Export ATR calculation metrics
   sqlite3 trading.db "SELECT * FROM atr_calculations WHERE timestamp > datetime('now', '-1 hour')" > /tmp/atr-data.csv

   # Copy error logs
   cp specs/atr-stop-adjustment/error-log.md /tmp/error-log-rollback.md
   ```

4. **Communication** (within 30 minutes):
   - Notify operations team: "ATR feature rolled back to pullback/percentage stops"
   - Document issue in error-log.md under "Deployment Phase (Phase 6-7)"
   - Create incident report with symptoms, timeline, and rollback actions
   - Schedule postmortem within 24 hours

**Rollback Verification Checklist**:
- [ ] `atr_enabled=false` confirmed in config
- [ ] Service restarted successfully
- [ ] All open positions show pullback_source="pullback" or "manual"
- [ ] Next 3 trades use non-ATR stops successfully
- [ ] No ATR-related errors in logs post-rollback
- [ ] System performance metrics normal (no degradation)

### Gradual Rollback (Multi-Day Issues)

**Trigger Conditions**:
- ATR strategy underperforming pullback stops (based on 7-day backtest)
- Regulatory concerns with dynamic stop methodology
- Operational complexity not justified by risk-adjusted returns
- Strategic decision to simplify risk management

**Rollback Steps** (1-2 weeks):

**Week 1: Disable New ATR Positions**
```bash
# Set atr_enabled=false for new positions only
# Allow existing ATR positions to complete naturally
vim config/risk_management.json
# Change: "atr_enabled": false

# Monitor existing ATR positions
python scripts/monitor_atr_positions.py --report daily
```

**Week 2: Complete Transition**
- Wait for all ATR-based positions to close (stop hit or target reached)
- Archive ATR calculation data for analysis
- Remove ATR configuration from production config
- Update documentation to mark ATR as "deactivated"

### Code Rollback (Critical Bug)

If ATR code contains critical bugs requiring immediate removal:

```bash
# Create rollback branch
git checkout -b rollback-atr-stop-adjustment

# Revert all ATR commits (commits from last stable version to current)
git log --oneline --grep="ATR" --since="2 weeks ago"  # List ATR commits
git revert <commit-sha-range> --no-edit

# Run full test suite
pytest src/trading_bot/risk_management/tests/ -v

# Deploy rollback branch
git push origin rollback-atr-stop-adjustment
# Follow deployment procedure for rollback branch
```

**Note**: Code rollback is extreme measure - prefer feature flag disable first.

### Partial Rollback (Symbol-Specific)

If ATR works for most symbols but fails for specific ones (e.g., low-volume penny stocks):

```python
# Add to config/risk_management.json
{
  "atr_enabled": true,
  "atr_excluded_symbols": ["MEME", "PENNY", "LOWVOL"],
  "atr_min_avg_volume": 1000000,  // Exclude symbols with <1M avg volume
  "atr_min_price": 5.00            // Exclude penny stocks <$5
}
```

Update ATRCalculator to check exclusion list before calculation.

### Recovery Procedures

After rollback and issue resolution:

1. **Root Cause Analysis** (1-3 days):
   - Review error logs and ATR calculation data
   - Reproduce issue in staging environment
   - Identify code fix or configuration adjustment
   - Update error-log.md with new error code if novel issue

2. **Fix Implementation** (1-5 days):
   - Create bugfix branch: `bugfix/atr-<issue-description>`
   - Write failing test that reproduces issue (TDD RED)
   - Implement fix (TDD GREEN)
   - Refactor if needed (TDD REFACTOR)
   - All 14+ tests passing

3. **Staging Re-validation** (3-7 days):
   - Deploy fix to staging
   - Run 3-7 days of live market validation
   - Monitor ATR calculation success rate (target: >95%)
   - Validate stop distance distribution (0.7%-10% range)
   - Compare ATR vs pullback performance metrics

4. **Production Re-deployment**:
   - Schedule deployment during low-volume period (10am-2pm ET)
   - Enable ATR with `atr_enabled=true`
   - Monitor closely for 2-4 hours post-deployment
   - Gradual rollout: Start with 1-2 positions, scale to full if successful

### Rollback Decision Matrix

| Severity | Scope | Response Time | Action |
|----------|-------|---------------|--------|
| **Critical** | System-wide | Immediate (<30 min) | Emergency rollback (feature flag disable) |
| **High** | Multi-symbol | Within 2 hours | Partial rollback (exclude affected symbols) |
| **Medium** | Single symbol | Within 1 day | Symbol-specific exclusion |
| **Low** | Edge case | Within 1 week | Gradual rollback, schedule fix |

### Success Metrics (Post-Rollback)

After rollback, validate these metrics return to baseline:
- [ ] Position entry success rate: >98% (same as pre-ATR)
- [ ] Stop-loss hit rate: 15-25% (historical range)
- [ ] Average stop distance: 1.5-3.0% (pullback/percentage baseline)
- [ ] Position planning latency: <10ms (no ATR overhead)
- [ ] Risk-adjusted return: Sharpe ratio >1.5 (strategy-dependent)

### Lessons Learned Template

After any rollback, document in error-log.md:
- **What went wrong**: Technical root cause
- **Why we didn't catch it**: Gap in testing, staging validation, monitoring
- **What we changed**: Code fix, test addition, process improvement
- **How we prevent it**: New validation, alert, or architectural change

## Phase 5 Checkpoint: Optimization (2025-10-16)

**Status**: ✅ COMPLETE - Production ready

- Performance: ATR calculation <1ms (50x faster than target)
- Security: Zero vulnerabilities, complete input validation
- Code Quality: 20/20 tests passing, 95% coverage, mypy strict clean
- Senior Code Review: APPROVED (HIGH confidence, LOW risk)
- Linting: Clean after auto-fix (22 deprecated typing imports fixed)

## Phase 7 Checkpoint: Ship to Production (2025-10-16)

**Status**: ✅ DEPLOYED TO PRODUCTION

### Release Information
- **Version**: v1.2.0
- **Feature**: ATR-based dynamic stop-loss adjustment
- **Release Date**: 2025-10-16
- **Branch**: atr-stop-adjustment → master
- **Commits**: 32 commits (from 24ef741 to 32c1606)

### Production Deployment
- **Type**: Backend enhancement (no UI)
- **Impact**: Zero (opt-in via atr_enabled=false by default)
- **Rollback**: Instant via config.json
- **Migrations**: None required
- **Env Vars**: None required

### Pre-Deployment Validation
- ✅ All 20 tests passing (100%)
- ✅ Smoke tests: 6/6 passing (0.78s)
- ✅ Performance: 50x faster than target
- ✅ Linting: Clean (ruff: 0 errors)
- ✅ Type safety: 100% (mypy strict: 0 errors)
- ✅ Senior code review: APPROVED

### Quality Metrics
- **Test Coverage**: ~95% of ATR code paths
- **Performance**: <1ms ATR calculation (target: <50ms)
- **Backward Compatibility**: 100% (opt-in design)
- **Risk Level**: LOW (instant rollback, graceful fallback)
- **Confidence**: HIGH (comprehensive testing, code review approved)

### Deployment Strategy
- Feature flag: atr_enabled=false (opt-in)
- Graceful fallback to pullback/percentage stops
- No breaking changes to existing functionality
- Instant rollback capability

### Documentation
- ✅ Optimization report: specs/atr-stop-adjustment/optimization-report.md
- ✅ Code review: specs/atr-stop-adjustment/artifacts/code-review-report.md
- ✅ Error documentation: specs/atr-stop-adjustment/error-log.md
- ✅ Rollback procedures: specs/atr-stop-adjustment/NOTES.md (lines 128-316)
- ✅ Configuration guide: README.md (ATR section)
- ✅ Ship report: specs/atr-stop-adjustment/ship-report.md

### Next Steps
- ✅ Deploy to production (v1.2.0)
- ✅ Run /finalize to update CHANGELOG and docs
- ⏳ Monitor production metrics
- ⏳ Enable ATR for select positions (atr_enabled=true)

## Additional Tasks: Trade Management Rules

### T006 [RED]: Break-even rule activation test
✅ T006 [RED]: Break-even rule activates at 2xATR (failing as expected)
- **File**: tests/risk_management/test_trade_management_rules.py
- **Test**: test_break_even_rule_activates_at_2x_atr()
- **Status**: Test written and failing as expected (ModuleNotFoundError)
- **Scenario**: Position with entry=$100, current_price=$106, current_atr=$3 (2xATR=$6 favorable move)
- **Expected**: RuleActivation with action="move_stop", new_stop_price=$100 (break-even)
- **Actual**: ModuleNotFoundError - evaluate_break_even_rule() doesn't exist yet
- **Commit**: aeba765 - test(red): T006-T007 write failing break-even tests

### T007 [RED]: Break-even idempotency test
✅ T007 [RED]: Break-even idempotency prevents multiple activations (failing as expected)
- **File**: tests/risk_management/test_trade_management_rules.py
- **Test**: test_break_even_rule_prevents_multiple_activations()
- **Status**: Test written and failing as expected (ModuleNotFoundError)
- **Scenario**: Position with break_even_activated=True, current_price=$110 (well above 2xATR)
- **Expected**: RuleActivation with action="hold" (no stop adjustment)
- **Actual**: ModuleNotFoundError - evaluate_break_even_rule() doesn't exist yet
- **Commit**: aeba765 - test(red): T006-T007 write failing break-even tests

### T008 [RED]: Scale-in rule test
✅ T008 [RED]: Write test that scale-in rule adds 50% position at 1.5xATR
- **File**: tests/risk_management/test_trade_management_rules.py
- **Test**: test_scale_in_at_1_5x_atr_above_entry()
- **Status**: Test written and failing as expected (ModuleNotFoundError)
- **Scenario**: Position at entry=$100, current_price=$104.50 (1.5xATR above), current_atr=$3, quantity=100
- **Expected**: RuleActivation with action="add_position", quantity=50 (50% of 100)
- **Actual**: ModuleNotFoundError - evaluate_scale_in_rule() doesn't exist yet
- **Commit**: 2ea71a2 - test(red): T008 write failing scale-in rule test

### T009 [RED]: Scale-in max limit test
✅ T009 [RED]: Write failing test for scale-in rule respects max 3 scale-ins limit
- **File**: tests/risk_management/test_trade_management_rules.py
- **Status**: Test written and failing as expected (ModuleNotFoundError)
- **Scenario**: Position with scale_in_count=3 should NOT allow additional scale-in
- **Expected**: RuleActivation with action="hold" (no add)
- **Commit**: test(red): T009 write failing scale-in max limit test

### T010 [RED]: Scale-in portfolio risk limit test
✅ T010 [RED]: Scale-in blocked by portfolio risk limit (failing as expected)
- **File**: tests/risk_management/test_trade_management_rules.py
- **Test**: test_scale_in_blocked_by_portfolio_risk_limit()
- **Status**: Test written and failing as expected (ModuleNotFoundError)
- **Scenario**: Portfolio at 1.8% risk, scale-in would push to 2.4%, exceeds 2% limit
- **Expected**: RuleActivation with action="hold" (blocked by risk limit)
- **Actual**: ModuleNotFoundError - evaluate_scale_in_rule() doesn't accept portfolio_risk_pct parameter yet
- **Commit**: test(red): T010 write failing scale-in portfolio risk test

### T013 [RED]: Average entry price for partial fills test
✅ T013 [RED]: Average entry price test (failing as expected)
- **File**: tests/risk_management/test_stop_adjuster_atr.py
- **Status**: Test written and failing as expected
- **Scenario**: Position scaled in 3 times (100@$100, 50@$104, 50@$108)
- **Expected**: Average entry $103.00, stop rules evaluate against average not original
- **Actual**: Stop adjustment uses original entry $100.00 instead of average $103.00
- **Commit**: test(red): T013 write failing average entry price test

### T011 [RED]: Catastrophic exit rule test
✅ T011 [RED]: Catastrophic exit test (failing as expected)
- **File**: tests/risk_management/test_trade_management_rules.py
- **Test**: test_catastrophic_exit_triggers_at_3x_atr_adverse_move()
- **Status**: Test written and failing as expected (ModuleNotFoundError)
- **Scenario**: Position with entry=$100, current_price=$91, current_atr=$3 (3xATR=$9 adverse move)
- **Expected**: RuleActivation with action="close_position", quantity=100 (full position)
- **Actual**: ModuleNotFoundError - evaluate_catastrophic_exit_rule() doesn't exist yet
- **Commit**: test(red): T011 write failing catastrophic exit test

## Last Updated
2025-10-16T14:00:00
