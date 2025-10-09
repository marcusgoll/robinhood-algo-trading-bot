# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
