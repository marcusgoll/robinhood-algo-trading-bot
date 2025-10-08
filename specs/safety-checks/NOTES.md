# Feature: safety-checks

## Overview
Pre-trade safety checks and circuit breakers to enforce Constitution §Safety_First and §Risk_Management. Prevents trades that violate risk limits, trading hours, or circuit breaker conditions.

## Research Findings

### Constitution Compliance (§Safety_First, §Risk_Management)
- Source: `.specify/memory/constitution.md`
- Finding: Circuit breakers mandatory, fail-safe required
- Decision: Block all trades on any validation failure (fail-safe)

### Roadmap Context
- Source: `.specify/memory/roadmap.md` (safety-checks)
- Requirements identified:
  1. Buying power verification
  2. Trading hours enforcement (7am-10am EST)
  3. Daily loss circuit breaker
  4. Consecutive loss detector (3 losses)
  5. Position size calculator
  6. Duplicate order prevention
- Blocked by: account-data-module, market-data-module

### Existing Infrastructure
- Source: `src/trading_bot/config.py`
- Finding: Risk parameters already defined:
  - max_daily_loss_pct: 3.0%
  - max_consecutive_losses: 3
  - max_position_pct: 5.0%
- Decision: Reuse config values, no new config needed

- Source: `src/trading_bot/logger.py`
- Finding: Audit logging system with trades.log and errors.log
- Decision: Log all safety check results to errors.log, circuit breakers to trades.log

## Feature Classification
- UI screens: No (backend-only)
- Improvement: No (new feature)
- Measurable: Yes (can track circuit breaker triggers, rejection rates)
- Deployment impact: Yes (requires account-data-module, market-data-module)

## System Dependencies
**Required (blocked by)**:
- account-data-module: For buying power, account balance
- market-data-module: For current time, market hours

**Existing (available now)**:
- config.py: Risk parameters
- logger.py: Audit logging

## Implementation Notes

### Design Decisions
1. **Fail-safe approach**: Any validation failure blocks trade
2. **State persistence**: Circuit breaker state saved to logs/circuit_breaker.json
3. **Trade history**: Load last N trades from logs/trades.log for consecutive loss detection
4. **Performance**: Cache buying power for 30s to avoid API spam

### Risk Mitigation
- Test coverage target: 95% (high-risk safety-critical code)
- Integration tests with mocked APIs (account, market)
- Manual testing of all circuit breaker scenarios before deployment

## Phase 1 Summary
- Research depth: Analyzed 3 existing modules
- Key decisions: 5 architectural decisions documented
- Components to reuse: 5 (config.py, logger.py, bot.CircuitBreaker, trades.log, errors.log)
- New components: 3 (safety_checks.py, time_utils.py, circuit_breaker.json)
- Migration needed: No

## Checkpoints
- Phase 0 (Specify): 2025-10-07
- Phase 1 (Plan): 2025-10-07
  - Artifacts: plan.md, contracts/api.yaml, error-log.md
  - Research decisions: 5
  - Migration required: No
- Phase 2 (Tasks): 2025-10-07
  - Tasks generated: 44
  - TDD coverage: 14 test-first behaviors
  - Ready for: /analyze

## Phase 2 Summary
- Total tasks: 44
- TDD trios: 14 behaviors (RED → GREEN → REFACTOR)
- Setup/config tasks: 3
- Integration tasks: 5
- Error handling tasks: 5
- Deployment prep tasks: 5
- Task file: specs/safety-checks/tasks.md

## Last Updated
2025-10-07T04:55:00Z
