# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2025-10-16

### Added
- **ATR-based Dynamic Stop-Loss Adjustment**: Volatility-adaptive stop-loss calculation
  - ATRCalculator class implementing Wilder's 14-period ATR formula
  - Dynamic stop distances using ATR multipliers (e.g., 2.0x ATR)
  - Automatic stop recalculation when ATR changes >20% (default threshold)
  - Configuration: `atr_enabled`, `atr_period`, `atr_multiplier`, `atr_recalc_threshold`
- Graceful fallback to pullback/percentage stops when ATR unavailable
- Comprehensive ATR validation (price bar integrity, stop distance bounds 0.7%-10%)
- ATR exception hierarchy: `ATRCalculationError`, `ATRValidationError`, `StaleDataError`
- 6 smoke tests for CI/CD integration (<1s execution time)
- ATR configuration guide in README.md with parameter tables and examples

### Changed
- Calculator.calculate_position_plan() now accepts optional `atr_data` parameter
- StopAdjuster.calculate_adjustment() supports dynamic ATR-based stop recalculation
- RiskManagementConfig extended with 4 ATR configuration fields (opt-in design)

### Performance
- ATR calculation: <1ms (50x faster than 50ms target)
- Position planning with ATR: <5ms (50x faster than 250ms target)

### Security
- Input validation for negative prices, non-sequential timestamps, stale data (>15min)
- Stop distance validation enforces 0.7%-10% bounds for risk management
- No new credentials or environment variables required

### Documentation
- Complete feature specification: specs/atr-stop-adjustment/spec.md
- Architecture plan with reuse analysis: specs/atr-stop-adjustment/plan.md
- 37 TDD tasks breakdown: specs/atr-stop-adjustment/tasks.md
- Optimization report: 50x performance, APPROVED code review
- Error documentation: 6 ATR-specific error codes with monitoring procedures
- Rollback procedures: 4 rollback strategies (emergency, gradual, code, partial)
- Production ship report with quality metrics and monitoring checklist

### Testing
- 20 tests passing (100% success rate)
- Test coverage: ~95% of ATR code paths
- Type safety: 100% (mypy strict: 0 errors)
- Linting: Clean (ruff: 0 errors, 22 deprecated typing imports fixed)

### Backward Compatibility
- ✅ Opt-in design (atr_enabled=false by default)
- ✅ Zero production impact
- ✅ All existing tests passing
- ✅ No breaking API changes

### Risk Assessment
- **Level**: LOW (instant rollback via config.json)
- **Confidence**: HIGH (comprehensive testing, code review approved)
- **Impact**: ZERO (backward compatible, opt-in)

## [Unreleased] - Previous Features

### Added
- Startup sequence with orchestrated component initialization
  - StartupOrchestrator class coordinates dependency-ordered initialization
  - StartupStep and StartupResult dataclasses for observable state tracking
  - Fail-fast error handling for safety-first approach
- Startup validation with comprehensive configuration checks
  - Credentials validation (ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD)
  - Configuration parameter validation (percentages, position sizes, trading hours)
  - Phase-mode conflict detection (blocks live trading in experience phase)
  - Component health verification before trading begins
- CLI flags for flexible startup modes
  - `--dry-run` flag for configuration validation without entering trading loop
  - `--json` flag for machine-readable status output (CI/CD integration)
  - Exit codes for automation (0=success, 1=config error, 2=validation error, 3=init failure, 130=interrupted)
- Dedicated startup logging system
  - `logs/startup.log` for startup audit trail
  - Startup-specific logger with TradingLogger.get_startup_logger()
  - Structured logging with ISO 8601 UTC timestamps
- Visual progress indicators for user feedback
  - Startup banner with mode and phase information
  - Startup summary with configuration details and circuit breaker status
  - Unicode progress indicators (checkmarks, warnings, errors)
- Comprehensive documentation
  - README.md Usage section with startup instructions
  - README.md Troubleshooting section with common errors and remediation
  - Error log with 5 common startup error scenarios (ERR-001 through ERR-005)
  - Docstrings for all StartupOrchestrator methods (Google-style format)

### Changed
- Updated README.md structure to include Usage and Troubleshooting sections
- Enhanced error messages with specific remediation steps

### Security
- Credentials never logged or exposed in startup output (Constitution Safety_First)
- Phase-mode conflict validation enforces safe trading progression

## [Previous Releases]

See git history for previous changes before CHANGELOG.md was created.
