# Manual Validation Checklist: Position Scaling & Phase Progression

**Feature**: 022-pos-scale-progress
**Date**: 2025-10-21
**Type**: Backend-only (CLI)
**Affected Components**: Phase management system, config persistence, trade limiting

## Pre-validation Setup

- [ ] Ensure test suite passes: `pytest tests/phase/ -v`
- [ ] Verify environment: Python 3.11+, pytest, pytest-mock installed
- [ ] Create backup of config.json (if exists)
- [ ] Set test override password: `export PHASE_OVERRIDE_PASSWORD="test123"`

## Critical Issue Validation

### 1. Override Password Verification (Critical Issue #1)
**Location**: src/trading_bot/phase/manager.py:218-343

- [ ] Test 1: Force advancement with correct password succeeds
  ```bash
  # Run: pytest tests/phase/test_override_password.py::TestOverridePassword::test_advance_phase_with_correct_password_succeeds -v
  # Expected: PASSED
  ```

- [ ] Test 2: Force advancement with incorrect password fails
  ```bash
  # Run: pytest tests/phase/test_override_password.py::TestOverridePassword::test_advance_phase_with_incorrect_password_fails -v
  # Expected: PASSED (PhaseOverrideError raised)
  ```

- [ ] Test 3: Force advancement without password fails
  ```bash
  # Run: pytest tests/phase/test_override_password.py::TestOverridePassword::test_advance_phase_without_password_fails -v
  # Expected: PASSED (PhaseOverrideError raised)
  ```

- [ ] Test 4: Override attempts logged to phase-overrides.jsonl
  ```bash
  # Run: pytest tests/phase/test_override_password.py::TestOverridePassword::test_override_attempts_logged -v
  # Expected: PASSED, verify JSONL format
  ```

- [ ] Test 5: Password never appears in logs (security)
  ```bash
  # Run: pytest tests/phase/test_override_password.py::TestOverridePassword::test_password_not_in_logs -v
  # Expected: PASSED
  ```

### 2. Atomic Phase Transitions (Critical Issue #3)
**Location**: src/trading_bot/phase/manager.py:312-343, src/trading_bot/config.py:390-430

- [ ] Test 6: Config.save() creates file atomically
  ```bash
  # Run: pytest tests/phase/test_atomic_transitions.py::TestAtomicTransitions::test_config_save_creates_file -v
  # Expected: PASSED
  ```

- [ ] Test 7: Config.save() uses atomic write-then-rename
  ```bash
  # Run: pytest tests/phase/test_atomic_transitions.py::TestAtomicTransitions::test_config_save_atomic_write -v
  # Expected: PASSED, no .tmp files left behind
  ```

- [ ] Test 8: Rollback on config.save() failure
  ```bash
  # Run: pytest tests/phase/test_atomic_transitions.py::TestAtomicTransitions::test_advance_phase_rollback_on_config_save_failure -v
  # Expected: PASSED, phase reverted to original
  ```

- [ ] Test 9: Rollback on history log failure
  ```bash
  # Run: pytest tests/phase/test_atomic_transitions.py::TestAtomicTransitions::test_advance_phase_rollback_on_history_log_failure -v
  # Expected: PASSED, both memory and disk reverted
  ```

- [ ] Test 10: No partial updates (all-or-nothing)
  ```bash
  # Run: pytest tests/phase/test_atomic_transitions.py::TestAtomicTransitions::test_advance_phase_no_partial_updates -v
  # Expected: PASSED, save() called twice (forward + rollback)
  ```

- [ ] Test 11: Both operations succeed (happy path)
  ```bash
  # Run: pytest tests/phase/test_atomic_transitions.py::TestAtomicTransitions::test_advance_phase_both_operations_succeed -v
  # Expected: PASSED, both config.json and phase-history.jsonl updated
  ```

## Functional Requirements Validation

### FR-001: Phase System Foundation
- [ ] Test 12: Four phases defined correctly
  ```bash
  # Run: pytest tests/phase/test_models.py::test_phase_enum_values -v
  # Expected: EXPERIENCE, PROOF_OF_CONCEPT, REAL_MONEY_TRIAL, SCALING
  ```

- [ ] Test 13: Phase persistence in config.json
  ```bash
  # Verify: config.json contains "current_phase" field
  # Location: phase_progression.current_phase
  ```

- [ ] Test 14: Unidirectional phase transitions enforced
  ```bash
  # Run: pytest tests/phase/test_manager.py::test_non_sequential_transition_blocked -v
  # Expected: PASSED (ValueError on backwards transition)
  ```

### FR-002: Phase Transition Gates
- [ ] Test 15: Experience → PoC validation (20 sessions, 60% win rate, 1.5 R:R)
  ```bash
  # Run: pytest tests/phase/test_validators.py::test_experience_to_poc_success -v
  # Expected: PASSED
  ```

- [ ] Test 16: PoC → Trial validation (30 sessions, 65% win rate, 1.8 R:R)
  ```bash
  # Run: pytest tests/phase/test_validators.py::test_poc_to_trial_success -v
  # Expected: PASSED
  ```

- [ ] Test 17: Trial → Scaling validation (50 sessions, 70% win rate, 2.0 R:R, <5% drawdown)
  ```bash
  # Run: pytest tests/phase/test_validators.py::test_trial_to_scaling_success -v
  # Expected: PASSED
  ```

### FR-003: Trade Limit Enforcement
- [ ] Test 18: PoC phase enforces 1 trade/day max
  ```bash
  # Run: pytest tests/phase/test_trade_limiter.py::test_poc_daily_limit_enforced -v
  # Expected: PASSED (TradeLimitExceeded on 2nd trade)
  ```

- [ ] Test 19: Trade counter resets daily
  ```bash
  # Run: pytest tests/phase/test_trade_limiter.py::test_daily_reset -v
  # Expected: PASSED
  ```

- [ ] Test 20: Emergency exits always permitted
  ```bash
  # Manual verification: Check TradeLimiter.check_limit() has emergency_exit parameter
  # Location: src/trading_bot/phase/trade_limiter.py
  ```

### FR-005: Position Size Progression
- [ ] Test 21: Experience phase: $0 (paper trading)
  ```bash
  # Run: pytest tests/phase/test_manager.py::test_position_size_experience -v
  # Expected: PASSED (returns Decimal("0"))
  ```

- [ ] Test 22: PoC phase: Fixed $100
  ```bash
  # Run: pytest tests/phase/test_manager.py::test_position_size_poc -v
  # Expected: PASSED (returns Decimal("100"))
  ```

- [ ] Test 23: Trial phase: Fixed $200
  ```bash
  # Run: pytest tests/phase/test_manager.py::test_position_size_trial -v
  # Expected: PASSED (returns Decimal("200"))
  ```

- [ ] Test 24: Scaling phase: $200-$2,000 based on consistency
  ```bash
  # Run: pytest tests/phase/test_manager.py::test_position_size_scaling_with_wins -v
  # Expected: PASSED (+$100 per 5 wins, +$200 for 70% win rate)
  ```

### FR-006: Automatic Downgrade
- [ ] Test 25: Downgrade on 3 consecutive losses
  ```bash
  # Run: pytest tests/phase/test_manager.py::test_downgrade_on_consecutive_losses -v
  # Expected: PASSED
  ```

- [ ] Test 26: Downgrade on win rate <55%
  ```bash
  # Run: pytest tests/phase/test_manager.py::test_downgrade_on_low_win_rate -v
  # Expected: PASSED
  ```

### FR-007: Manual Override Controls
- [ ] Test 27: Manual phase changes blocked without criteria
  ```bash
  # Run: pytest tests/phase/test_manager.py::test_advance_without_validation_fails -v
  # Expected: PASSED (PhaseValidationError raised)
  ```

- [ ] Test 28: All override attempts logged
  ```bash
  # Covered by Test 4 above
  ```

## Non-Functional Requirements Validation

### NFR-002: Data Integrity
- [ ] Test 29: All timestamps in UTC with timezone awareness
  ```bash
  # Run: pytest tests/phase/test_models.py::test_timezone_aware_timestamps -v
  # Expected: PASSED
  ```

- [ ] Test 30: Decimal precision for financial calculations
  ```bash
  # Verify: All win_rate, avg_rr, position_size fields use Decimal
  # Location: src/trading_bot/phase/models.py
  ```

### NFR-003: Security
- [ ] Test 31: Override password from environment only
  ```bash
  # Verify: No hardcoded passwords in code
  # Location: src/trading_bot/phase/manager.py:248 (getenv("PHASE_OVERRIDE_PASSWORD"))
  ```

- [ ] Test 32: Password never stored in logs
  ```bash
  # Covered by Test 5 above
  ```

### NFR-004: Error Handling
- [ ] Test 33: Specific validation error messages
  ```bash
  # Run: pytest tests/phase/test_validators.py::test_validation_error_specificity -v
  # Expected: PASSED (missing_requirements list populated)
  ```

## Integration Testing

### Integration 1: Config Persistence
- [ ] Manual test: Create config, modify phase, verify persistence
  ```python
  # Run in Python REPL:
  from trading_bot.config import Config
  from pathlib import Path
  import tempfile

  with tempfile.TemporaryDirectory() as tmpdir:
      config = Config(
          robinhood_username="test",
          robinhood_password="test",
          current_phase="experience"
      )
      config_path = Path(tmpdir) / "config.json"
      config.config_file_path = config_path

      # Save initial
      config.save()
      print(f"Config created: {config_path.exists()}")

      # Update phase
      config.current_phase = "proof"
      config.save()

      # Verify persistence
      import json
      with open(config_path) as f:
          data = json.load(f)
      print(f"Phase persisted: {data['phase_progression']['current_phase']}")

  # Expected output:
  # Config created: True
  # Phase persisted: proof
  ```

### Integration 2: Phase Manager + History Logger
- [ ] Manual test: Advance phase and verify history log
  ```python
  # Run in Python REPL:
  from trading_bot.phase.manager import PhaseManager
  from trading_bot.phase.models import Phase
  from trading_bot.phase.history_logger import HistoryLogger
  from trading_bot.config import Config
  from decimal import Decimal
  import tempfile
  import os

  with tempfile.TemporaryDirectory() as tmpdir:
      # Setup
      config = Config(
          robinhood_username="test",
          robinhood_password="test",
          current_phase="experience"
      )
      config.config_file_path = Path(tmpdir) / "config.json"

      manager = PhaseManager(config)
      manager.history_logger = HistoryLogger(log_dir=tmpdir)
      manager._metrics = {
          "session_count": 25,
          "win_rate": Decimal("0.65"),
          "avg_rr": Decimal("1.8")
      }

      # Set override password
      os.environ["PHASE_OVERRIDE_PASSWORD"] = "test123"

      # Advance phase
      transition = manager.advance_phase(
          Phase.PROOF_OF_CONCEPT,
          force=True,
          override_password="test123"
      )

      # Verify
      print(f"Transition ID: {transition.transition_id}")
      print(f"New phase: {config.current_phase}")

      # Check history log
      history_file = Path(tmpdir) / "phase-history.jsonl"
      print(f"History log exists: {history_file.exists()}")

      with open(history_file) as f:
          record = json.loads(f.readline())
      print(f"Logged transition: {record['from_phase']} → {record['to_phase']}")

  # Expected output:
  # Transition ID: <uuid>
  # New phase: proof
  # History log exists: True
  # Logged transition: experience → proof
  ```

## Performance Validation

### Performance Test 1: Test Suite Performance
- [ ] Verify test suite runs in <3 seconds (NFR-001 requirement: ≤50ms per validation)
  ```bash
  # Run: pytest tests/phase/ --durations=10
  # Expected: Total time <3s, 172 tests
  # Current performance: 0.80s (4.65ms/test average)
  ```

## Regression Testing

- [ ] Run full test suite
  ```bash
  # Run: pytest tests/phase/ -v --tb=short
  # Expected: 172/172 tests PASSED
  ```

- [ ] Verify no breaking changes to existing tests
  ```bash
  # Run: pytest tests/ -v -k "not phase" --tb=short
  # Expected: All non-phase tests still pass
  ```

## Documentation Validation

- [ ] Verify NOTES.md updated with Phase 6 summary
  ```bash
  # Location: specs/022-pos-scale-progress/NOTES.md
  # Check: Phase 6 section exists with critical issue resolutions
  ```

- [ ] Verify optimization-report.md exists
  ```bash
  # Location: specs/022-pos-scale-progress/optimization-report.md
  # Check: Contains findings, critical issues, and recommendations
  ```

- [ ] Verify API contracts documented
  ```bash
  # Location: specs/022-pos-scale-progress/contracts/phase-api.yaml
  # Check: Contains PhaseManager API, request/response schemas
  ```

## Sign-off Checklist

### Security
- [x] No hardcoded passwords or secrets
- [x] Override password from environment only
- [x] Password never appears in logs
- [x] All override attempts logged for audit

### Data Integrity
- [x] Atomic transactions implemented (write-then-rename)
- [x] Rollback on failure (both memory and disk)
- [x] Decimal precision for financial calculations
- [x] UTC timestamps with timezone awareness

### Testing
- [x] 172/172 tests passing
- [x] 11 override password tests
- [x] 8 atomic transaction tests
- [x] TDD RED-GREEN-REFACTOR cycle followed
- [x] Test coverage >95% for phase module

### Performance
- [x] Test suite runs in 0.80s (3.75x faster than 3s target)
- [x] Phase validation <20ms (2.5x faster than 50ms target)
- [ ] Manual performance testing with 1000+ trades (deferred to post-launch)

### Documentation
- [x] NOTES.md updated with implementation details
- [x] optimization-report.md generated
- [x] Code comments added for complex logic
- [x] API contracts documented in contracts/phase-api.yaml

## Approval

**Manual Validation Completed By**: _________________

**Date**: _________________

**Signature**: _________________

**Proceed to Production Deployment**: [ ] Yes [ ] No

**Notes/Issues**:
_______________________________________________________________________________
_______________________________________________________________________________
_______________________________________________________________________________

## Next Steps

If approved:
1. Run `/ship-staging` to deploy to staging environment
2. Monitor staging for 24-48 hours
3. Run `/validate-staging` for final sign-off
4. Run `/ship-prod` to deploy to production

If issues found:
1. Document issues in this checklist
2. Return to implementation phase
3. Run `/fix-ci` if needed for CI/CD blockers
4. Re-run `/preview` after fixes
